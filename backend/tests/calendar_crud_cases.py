"""日历事项与「本周进度」的隔离用例：内存 SQLite + 真实 CRUD/路由逻辑。

对应文档：docs/14_主页仪表盘与待做事项开发方案.md「§2.2 完成与达成的判定 / §8 相关脚本与测试」。
改动 `app/crud/calendar.py`、`app/models/bill.py` 的 CalendarEvent、
或 `app/routers/calendar.py` 时，先复跑本文件。

跑法（需已安装 fastapi 的 desheng 环境）：

    conda activate desheng
    cd backend
    python tests/calendar_crud_cases.py

**不碰真实 MySQL**：全程用内存 SQLite，不写任何业务数据。
被测的是真实的 CRUD 函数与真实的 FastAPI 路由（含 Pydantic 校验），
只把数据库换成内存库。

**这个文件存在的直接原因**：开发期发现过一个语义错误——第一版把
`todo` 过期也计入「本周进度」分子，导致"拖着不做作业反而进度变高"。
下面 `test_todo_overdue_does_not_count_as_progress` 就是那条的固化回归。
"""
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.crud.calendar import (  # noqa: E402
    PENDING_LIMIT,
    archived_events,
    counts_as_progress,
    event_due_at,
    is_overdue,
    pending_bucket,
    pending_events,
    pending_summary,
    week_bounds,
    week_progress,
)
from app.models.bill import Base, CalendarEvent, CalendarEventTone  # noqa: E402

failures = []
checks = 0


def check(condition, label):
    global checks
    checks += 1
    if condition:
        print("PASS", label)
    else:
        failures.append(label)
        print("FAIL", label)


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


# 全部用例使用同一个"现在"，避免跨秒导致 flaky。
NOW = datetime(2026, 10, 6, 12, 0, 0)
# 2026-10-06 是周二，所在日历周为 10-05(周一) ~ 10-11(周日)
ANCHOR = date(2026, 10, 6)
MONDAY = date(2026, 10, 5)
SUNDAY = date(2026, 10, 11)


def ev(event_date, *, tone=CalendarEventTone.todo, event_time=None, completed_at=None,
       archived_at=None, title="t"):
    return CalendarEvent(event_date=event_date, event_time=event_time, title=title,
                         tone=tone, completed_at=completed_at, archived_at=archived_at)


# ---------------------------------------------------------------- 周边界
def test_week_bounds_monday_to_sunday():
    check(week_bounds(ANCHOR) == (MONDAY, SUNDAY), "week_bounds: 周二 -> (周一, 周日)")


def test_week_bounds_on_monday_itself():
    check(week_bounds(MONDAY) == (MONDAY, SUNDAY), "week_bounds: 周一自身 -> 同一周")


def test_week_bounds_on_sunday_stays_in_same_week():
    # 用户明确要求："哪怕今天是周六，本周也是到今天所在周的周日为止"
    check(week_bounds(SUNDAY) == (MONDAY, SUNDAY), "week_bounds: 周日仍属本周（不滚到下周）")


def test_week_bounds_across_month_boundary():
    # 2026-11-01 是周日，所在周的周一是 10-26
    check(week_bounds(date(2026, 11, 1)) == (date(2026, 10, 26), date(2026, 11, 1)),
          "week_bounds: 跨月（11-01 周日 -> 10-26 周一）")


# ---------------------------------------------------------------- 到期时刻合成
def test_due_at_defaults_to_end_of_day_when_time_missing():
    # 用户决定：event_time 为空时兜底当天 23:59:59（避免 0 值）
    check(event_due_at(ev(MONDAY)) == datetime(2026, 10, 5, 23, 59, 59),
          "event_due_at: 空 time -> 当天 23:59:59")


def test_due_at_keeps_seconds():
    # 用户要求精度到秒；MySQL TIME 本身支持 HH:MM:SS
    got = event_due_at(ev(MONDAY, event_time=time(14, 30, 15)))
    check(got == datetime(2026, 10, 5, 14, 30, 15), "event_due_at: 保留到秒")


# ---------------------------------------------------------------- 过期判定（跨天是最易错处）
def test_yesterday_is_overdue():
    # 若误写成 event_time < now.time()，会把"昨天 23:59"判成未过期
    check(is_overdue(ev(date(2026, 10, 5), event_time=time(23, 59, 59)), now=NOW),
          "is_overdue: 昨天 23:59:59 -> 过期（跨天正确）")


def test_today_midnight_is_overdue():
    check(is_overdue(ev(date(2026, 10, 6), event_time=time(0, 0, 0)), now=NOW),
          "is_overdue: 今天 00:00:00 -> 过期")


def test_today_after_now_is_not_overdue():
    check(not is_overdue(ev(date(2026, 10, 6), event_time=time(12, 0, 1)), now=NOW),
          "is_overdue: 今天 12:00:01（晚于 now）-> 未过期")


def test_today_without_time_is_not_overdue():
    check(not is_overdue(ev(date(2026, 10, 6)), now=NOW),
          "is_overdue: 今天无 time -> 未过期（兜底 23:59:59）")


def test_completed_event_is_never_overdue():
    e = ev(date(2026, 10, 1), completed_at=datetime(2026, 10, 1, 9, 0))
    check(not is_overdue(e, now=NOW), "is_overdue: 已完成项永不过期")


# ---------------------------------------------------------------- 达成语义（todo 与 meeting 相反）
def test_todo_incomplete_not_progress():
    check(not counts_as_progress(ev(SUNDAY), now=NOW), "达成: todo 未完成 -> 不算")


def test_todo_overdue_does_not_count_as_progress():
    """核心回归：超期未完成的 todo 是**失败**，不能计入进度分子。

    第一版实现把 todo 过期也算达成，会让"拖着不做"提高进度数字。
    """
    overdue_todo = ev(date(2026, 10, 5), event_time=time(1, 0))
    check(is_overdue(overdue_todo, now=NOW), "达成: 该 todo 确实已过期（前置断言）")
    check(not counts_as_progress(overdue_todo, now=NOW),
          "达成: todo 过期 -> 不算进度（防'拖延反而涨进度'）")


def test_todo_completed_counts_as_progress():
    e = ev(MONDAY, completed_at=datetime(2026, 10, 6, 8, 0))
    check(counts_as_progress(e, now=NOW), "达成: todo 已完成 -> 算")


def test_meeting_overdue_counts_as_progress():
    # 会议开完了就算发生，即使没人手动勾选
    e = ev(date(2026, 10, 5), tone=CalendarEventTone.meeting, event_time=time(10, 0))
    check(counts_as_progress(e, now=NOW), "达成: meeting 已过期 -> 算（会开完即完成）")


def test_meeting_future_not_progress():
    e = ev(SUNDAY, tone=CalendarEventTone.meeting, event_time=time(23, 0))
    check(not counts_as_progress(e, now=NOW), "达成: meeting 未到时间且未勾选 -> 不算")


def test_meeting_completed_counts_as_progress():
    e = ev(SUNDAY, tone=CalendarEventTone.meeting, completed_at=datetime(2026, 10, 6, 9, 0))
    check(counts_as_progress(e, now=NOW), "达成: meeting 已勾选 -> 算")


# ---------------------------------------------------------------- 周汇总
def test_empty_week_ratio_is_none_not_nan():
    """空周必须返回 None，否则 (0/0)*100 = NaN 会让 stroke-dasharray 失效。"""
    result = week_progress(make_session(), anchor=ANCHOR, now=NOW)
    check(result["total"] == 0, "空周: total=0")
    check(result["ratio"] is None, "空周: ratio is None（不是 0/NaN）")
    check(result["start"] == MONDAY.isoformat(), "空周: start 为周一")
    check(result["end"] == SUNDAY.isoformat(), "空周: end 为周日")


def test_week_progress_mixed_counts_and_excludes_other_weeks():
    db = make_session()
    rows = [
        # 本周内，应计入分母
        ev(MONDAY, event_time=time(1, 0)),                                   # 过期 todo（不算分子）
        ev(date(2026, 10, 7), completed_at=datetime(2026, 10, 6, 8, 0)),      # 完成 todo（算）
        ev(date(2026, 10, 5), tone=CalendarEventTone.meeting, event_time=time(10, 0)),  # 过期 meeting（算）
        ev(SUNDAY, tone=CalendarEventTone.meeting, event_time=time(23, 0)),   # 未过期 meeting（不算）
        # 本周外，应被排除
        ev(date(2026, 10, 4)),                                               # 上周日
        ev(date(2026, 10, 12)),                                              # 下周一
    ]
    for r in rows:
        db.add(r)
    db.commit()

    result = week_progress(db, anchor=ANCHOR, now=NOW)
    check(result["total"] == 4, "混合: 分母=4（上周/下周被排除）")
    check(result["done"] == 1, "混合: done=1")
    check(result["numerator"] == 2, "混合: 分子=2（完成的 todo + 过期的 meeting）")
    check(result["ratio"] == 50.0, "混合: ratio=50.0")


def test_ratio_is_rounded_to_one_decimal():
    db = make_session()
    for i in range(3):
        db.add(ev(MONDAY + timedelta(days=i)))
    db.add(ev(MONDAY, completed_at=datetime(2026, 10, 6, 8, 0)))
    db.commit()
    result = week_progress(db, anchor=ANCHOR, now=NOW)
    # 1/4 = 25.0
    check(result["ratio"] == 25.0, "ratio: 1/4 -> 25.0")


def test_week_filter_uses_date_not_time():
    """事项按 event_date 落在本周内即计入，与 event_time 无关。"""
    db = make_session()
    db.add(ev(SUNDAY, event_time=time(0, 0, 1)))   # 周日最早时刻，仍属本周
    db.add(ev(date(2026, 10, 12)))                  # 下周一，不属本周
    db.commit()
    result = week_progress(db, anchor=ANCHOR, now=NOW)
    check(result["total"] == 1, "边界: 周日 00:00:01 计入，下周一不计入")


# ---------------------------------------------------------------- tone 收敛
def test_tone_enum_has_exactly_two_values():
    """C1-b 决策：tone 收敛为 todo/meeting，plan/bill 已删除。"""
    values = {t.value for t in CalendarEventTone}
    check(values == {"todo", "meeting"}, f"tone 枚举恰为两值，实际={sorted(values)}")


def test_plan_tone_is_rejected_by_schema():
    """旧值 plan 必须被拒绝，否则收敛没生效。"""
    from pydantic import ValidationError
    from app.schemas.calendar import CalendarEventCreate
    try:
        CalendarEventCreate(event_date=MONDAY, title="x", tone="plan")
    except ValidationError:
        check(True, "schema: tone=plan 被拒（收敛生效）")
    else:
        check(False, "schema: tone=plan 仍被接受（收敛未生效）")


# ---------------------------------------------------------------- completed_at 读写
def test_completion_can_be_set_and_cleared():
    from app.schemas.calendar import CalendarEventUpdate
    db = make_session()
    e = ev(MONDAY)
    db.add(e)
    db.commit()

    e.completed_at = datetime(2026, 10, 6, 9, 0)
    db.commit()
    check(e.completed_at is not None, "completed_at: 可写入")

    e.completed_at = None
    db.commit()
    check(e.completed_at is None, "completed_at: 可清空（撤销完成）")

    # exclude_unset 语义：不传该字段时不应改动它
    data = CalendarEventUpdate(title="新标题")
    check("completed_at" not in data.model_dump(exclude_unset=True),
          "completed_at: 未传时不进入 update 载荷（不会误清空）")


def test_completed_at_defaults_to_null():
    db = make_session()
    e = ev(MONDAY)
    db.add(e)
    db.commit()
    db.refresh(e)
    check(e.completed_at is None, "completed_at: 新记录默认 NULL（未完成）")


# ---------------------------------------------------------------- 待做清单（第二轮）
# 这一组固化 docs/14 §2.4 的取数与排序规则。它是本轮修的两个缺陷的回归：
#   - 缺陷1：固定周窗导致"下周一交作业"看不到
#   - 缺陷2：卡片数据源绑定日历可见月份，翻月就变空

def test_pending_includes_far_future_items():
    """缺陷1的回归：下周一（甚至在更远）的事项必须出现在清单里。"""
    db = make_session()
    db.add(ev(date(2026, 10, 12), title="下周一交作业"))   # 本周之外
    db.add(ev(date(2027, 3, 1), title="明年的事"))          # 很久以后
    db.add(ev(MONDAY, title="本周的事"))
    db.commit()

    items, total = pending_events(db)
    titles = [e.title for e in items]
    check(total == 3, "清单: 跨周/跨年的事项都计入总数", )
    check("下周一交作业" in titles, "清单: 下周一的事项**在清单里**（缺陷1 已修）")
    check("明年的事" in titles, "清单: 远期事项也在清单里")


def test_pending_excludes_completed():
    """已完成的（含很久以前完成的）不进清单。"""
    db = make_session()
    db.add(ev(MONDAY, title="未完成"))
    db.add(ev(MONDAY, title="已完成", completed_at=datetime(2026, 10, 6, 9, 0)))
    db.commit()

    items, total = pending_events(db)
    check(total == 1, "清单: 只含未完成（total=1）")
    check([e.title for e in items] == ["未完成"], "清单: 已完成的被排除")


def test_pending_sort_puts_unscheduled_first():
    """核心排序规则：无 event_time 的排最前，其余按 (date, time) 升序。

    用户给的验算例子：2 条极速 + 明天 + 后天 → 极速、极速、明天、后天。
    """
    db = make_session()
    today = date(2026, 10, 7)
    db.add(ev(today + timedelta(days=2), event_time=time(9, 0), title="后天"))
    db.add(ev(today + timedelta(days=1), event_time=time(9, 0), title="明天"))
    db.add(ev(today, title="极速A"))                    # 无时间
    db.add(ev(today, title="极速B"))                    # 无时间
    db.commit()

    items, _ = pending_events(db)
    order = [e.title for e in items]
    # 「未安排」组内**最新的排最前**（用户 2026-10-07 决定），所以 B（后插入）在 A 前。
    check(order == ["极速B", "极速A", "明天", "后天"],
          f"排序: 未安排（新的在前）+ 更早的 DDL，实际={order}")
    check(order[2] == "明天", f"排序: 无时间之后是更早的 DDL，实际={order}")
    check(order[3] == "后天", f"排序: 然后是较晚的 DDL，实际={order}")
    check(order[:3] == ["极速B", "极速A", "明天"],
          f"排序: 取前 3 = 两条极速 + 明天（用户例子），实际前3={order[:3]}")


def test_unscheduled_group_newest_first():
    """「未安排」组内最新的排最前（用户 2026-10-07 决定）。

    这条是实测发现的回归：原先两条无时间的事项排序键完全相同，
    `sorted()` 稳定排序会保留查询顺序（按主键升序），导致**刚记的事沉到下面**，
    用户会怀疑"到底记上了没"。
    """
    db = make_session()
    for i in range(3):
        db.add(ev(MONDAY, title=f"未安排{i}"))
    db.commit()

    items, _ = pending_events(db)
    order = [e.title for e in items]
    check(order == ["未安排2", "未安排1", "未安排0"],
          f"未安排组: 最新的排最前，实际={order}")


def test_pending_sort_does_not_use_date_for_unscheduled():
    """无时间的事项排最前，**即使它的日期比有时间的更晚**。

    这是刻意的：未安排的事项需要先被看到并决定何时做（清空收集箱）。
    若按日期排，一条"今天刚记下、还没安排"的事会排在"昨天就该交的作业"之后。
    """
    db = make_session()
    db.add(ev(date(2026, 10, 6), event_time=time(9, 0), title="昨天该交的"))
    db.add(ev(date(2026, 10, 20), title="下下周的、未安排"))   # 日期更晚但无时间
    db.commit()

    items, _ = pending_events(db)
    check(items[0].title == "下下周的、未安排",
          f"排序: 无时间优先于日期，实际={[e.title for e in items]}")


def test_pending_respects_limit_and_reports_total():
    """超过上限时**如实返回总数**，不静默截断。"""
    db = make_session()
    for i in range(PENDING_LIMIT + 5):
        db.add(ev(MONDAY + timedelta(days=i), event_time=time(9, 0), title=f"事{i}"))
    db.commit()

    items, total = pending_events(db)
    check(total == PENDING_LIMIT + 5, f"上限: 总数如实返回 {PENDING_LIMIT + 5}")
    check(len(items) == PENDING_LIMIT, f"上限: 列表截到 {PENDING_LIMIT} 条")

    summary = pending_summary(items, total)
    check(summary["truncated"] is True, "上限: truncated 标记为 True（前端据此提示）")
    check(summary["total"] == PENDING_LIMIT + 5, "上限: 摘要里的 total 是真实总数")


def test_pending_summary_counts_are_priority_ordered():
    """分类计数按优先级判定，一条事项只进一个桶。

    优先级：overdue > unscheduled > today
    """
    db = make_session()
    now = datetime(2026, 10, 7, 12, 0, 0)      # 今天中午
    today = now.date()

    # overdue：有日期有时间的过去事项
    db.add(ev(today - timedelta(days=1), event_time=time(9, 0), title="过期"))
    db.add(ev(today - timedelta(days=1), event_time=time(9, 0), title="过期2"))
    # unscheduled：无时间（无论日期）
    db.add(ev(today, title="未安排"))
    # today：今天且有时间，未过期
    db.add(ev(today, event_time=time(20, 0), title="今天晚些"))
    # 未来：不计入三个分类
    db.add(ev(today + timedelta(days=5), event_time=time(9, 0), title="下周"))
    db.commit()

    events, total = pending_events(db)
    summary = pending_summary(events, total, now=now)
    counts = summary["counts"]
    check(counts["overdue"] == 2, f"分类: overdue=2，实际={counts}")
    check(counts["unscheduled"] == 1, f"分类: unscheduled=1，实际={counts}")
    check(counts["today"] == 1, f"分类: today=1，实际={counts}")
    check(sum(counts.values()) <= total,
          f"分类: 各类之和 ≤ total（未来事项不占分类），实际={counts} total={total}")


def test_unscheduled_becomes_overdue_once_its_date_passes():
    """无时间的事项在日期过去后应归入 overdue，而不是永远停在 unscheduled。

    否则极速录入的旧事项永远不会被当成欠账提醒——它会一直显示为"未安排"。
    """
    db = make_session()
    now = datetime(2026, 10, 7, 12, 0, 0)
    # 一周前极速录入、一直没安排
    db.add(ev(date(2026, 10, 1), title="一周前记的、没安排"))
    db.commit()

    events, total = pending_events(db)
    summary = pending_summary(events, total, now=now)
    check(summary["counts"]["overdue"] == 1,
          f"分类: 过期的无时间事项算 overdue，实际={summary['counts']}")
    check(summary["counts"]["unscheduled"] == 0,
          "分类: 不再算 unscheduled（否则永远不提醒）")


def test_pending_sort_is_stable_for_same_key():
    """同 key（同日期同时间）的事项顺序稳定，不因查询顺序抖动。"""
    db = make_session()
    for i in range(5):
        db.add(ev(MONDAY, event_time=time(9, 0), title=f"同{i}"))
    db.commit()

    first, _ = pending_events(db)
    second, _ = pending_events(db)
    check([e.title for e in first] == [e.title for e in second],
          "排序: 同 key 时顺序稳定（两次调用一致）")


# ---------------------------------------------------------------- 作废（废纸篓）
# 这一组固化 docs/14 §2.5 的语义：作废 = "我决定不做了"，可恢复，
# 与"完成"是两件事。用户四条决定：分子分母都不算、每项一个按钮、
# 抽屉里可查看可恢复、日历照常显示。

def test_archived_disappears_from_pending():
    """作废后从待做清单消失——这是作废的全部作用。"""
    db = make_session()
    db.add(ev(MONDAY, title="要作废的"))
    db.add(ev(MONDAY, title="留下的"))
    db.commit()

    target = db.query(CalendarEvent).filter_by(title="要作废的").one()
    target.archived_at = datetime.now()
    db.commit()

    items, total = pending_events(db)
    titles = [e.title for e in items]
    check(total == 1, f"作废: 总数减 1，实际 {total}")
    check("要作废的" not in titles, "作废: 从待做清单消失")
    check("留下的" in titles, "作废: 其余事项不受影响")


def test_archived_appears_in_archived_list():
    """作废后出现在废纸篓里——否则就不是回收站，而是黑洞。"""
    db = make_session()
    db.add(ev(MONDAY, title="作废的"))
    db.commit()
    target = db.query(CalendarEvent).filter_by(title="作废的").one()
    target.archived_at = datetime.now()
    db.commit()

    items, total = archived_events(db)
    check(total == 1, "废纸篓: 总数正确")
    check([e.title for e in items] == ["作废的"], "废纸篓: 能看到刚作废的")


def test_pending_and_archived_are_mutually_exclusive():
    """一条事项要么在待做清单、要么在废纸篓，不会同时出现。"""
    db = make_session()
    db.add(ev(MONDAY, title="待做中"))
    db.add(ev(MONDAY, title="已作废", archived_at=datetime.now()))
    db.add(ev(MONDAY, title="已完成", completed_at=datetime.now()))
    db.commit()

    pending, _ = pending_events(db)
    archived, _ = archived_events(db)
    pending_titles = {e.title for e in pending}
    archived_titles = {e.title for e in archived}

    check(pending_titles == {"待做中"}, f"清单只含待做中，实际 {pending_titles}")
    check(archived_titles == {"已作废"}, f"废纸篓只含已作废，实际 {archived_titles}")
    check(not (pending_titles & archived_titles), "清单与废纸篓没有交集")
    # 「已完成但未作废」两边都不在——它既不是待做，也没被作废。
    check("已完成" not in pending_titles and "已完成" not in archived_titles,
          "已完成未作废的事项两边都不在")


def test_unarchive_restores_to_pending():
    """恢复（archived_at 置回 NULL）后回到待做清单。"""
    db = make_session()
    db.add(ev(MONDAY, title="先作废再恢复"))
    db.commit()
    target = db.query(CalendarEvent).filter_by(title="先作废再恢复").one()

    target.archived_at = datetime.now()
    db.commit()
    _, after_archive = pending_events(db)
    check(after_archive == 0, "恢复: 作废后清单里没有它")

    target.archived_at = None
    db.commit()
    items, after_restore = pending_events(db)
    check(after_restore == 1, "恢复: 撤销作废后回到清单")
    check(items[0].title == "先作废再恢复", "恢复: 是原来那条")


def test_archived_does_not_count_toward_week_progress():
    """⭐ 用户的明确要求：已作废的事项**分子分母都不算**。

    这条是本节最重要的一条：作废必须让它从周进度里彻底消失，
    否则"清理积压"这个动作会莫名其妙地改变完成率。
    """
    db = make_session()
    db.add(ev(MONDAY, title="留在周里的"))
    db.add(ev(MONDAY, title="周内作废的"))
    db.commit()

    before = week_progress(db, anchor=MONDAY)
    check(before["total"] == 2, f"周进度: 作废前分母 2，实际 {before['total']}")

    target = db.query(CalendarEvent).filter_by(title="周内作废的").one()
    target.archived_at = datetime.now()
    db.commit()

    after = week_progress(db, anchor=MONDAY)
    check(after["total"] == 1, f"周进度: 作废后**分母减 1**，实际 {after['total']}")
    check(after["numerator"] == before["numerator"],
          f"周进度: 分子不变（作废不算达成），实际 {after['numerator']}")


def test_archived_still_exists_in_calendar_list():
    """⭐ 用户的明确要求：日历**照常显示**已作废的事项。

    理由：它确实占用过那天，抹掉会让日历与你对那天的记忆不符。
    """
    db = make_session()
    db.add(ev(MONDAY, title="日历里要看得见", archived_at=datetime.now()))
    db.commit()

    from app.crud.calendar import list_calendar_events
    rows = list_calendar_events(db, date_from=MONDAY, date_to=MONDAY)
    titles = [e.title for e in rows]
    check("日历里要看得见" in titles,
          f"日历: 已作废事项仍然出现在日历查询里，实际 {titles}")


def test_archived_sorted_by_archive_time_desc():
    """废纸篓按**作废时间倒序**（最近作废的在前）——它是回顾用的。"""
    db = make_session()
    for i in range(3):
        db.add(ev(MONDAY, title=f"废{i}"))
    db.commit()

    # 刻意让"废0"最后作废，它应该排在废纸篓最前。
    order = {"废0": 3, "废1": 1, "废2": 2}
    for title, hour in order.items():
        row = db.query(CalendarEvent).filter_by(title=title).one()
        row.archived_at = datetime(2026, 10, 7, hour, 0, 0)
    db.commit()

    items, _ = archived_events(db)
    check([e.title for e in items] == ["废0", "废2", "废1"],
          f"废纸篓: 按作废时间倒序，实际 {[e.title for e in items]}")


def test_archived_and_completed_are_independent():
    """作废与完成互不影响：一条已完成的事项也可以被作废。"""
    db = make_session()
    db.add(ev(MONDAY, title="既完成又作废",
              completed_at=datetime(2026, 10, 6, 9, 0),
              archived_at=datetime(2026, 10, 7, 9, 0)))
    db.commit()

    # 它不在待做清单里（已作废），但在废纸篓里。
    pending, _ = pending_events(db)
    archived, _ = archived_events(db)
    check(not pending, "既完成又作废: 不在待做清单")
    check(len(archived) == 1, "既完成又作废: 在废纸篓里")
    check(archived[0].completed_at is not None,
          "既完成又作废: completed_at 未被作废操作清掉")


# ---------------------------------------------------------------- 标签页分桶
# 这一组固化 docs/14 §11.6 的标签页分组：全部 / 今天 / 已过期 / 未安排。
# 分桶判定只有一处（`pending_bucket()`），角标数字与列表条数都从它派生。

def test_bucket_priority_order():
    """分桶按优先级，一条事项只进一个桶。"""
    now = datetime(2026, 10, 7, 12, 0, 0)
    today = now.date()
    # 过期：有日期有时间的过去事项
    check(pending_bucket(ev(today - timedelta(days=1), event_time=time(9, 0)), now=now)
          == "overdue", "分桶: 过期 -> overdue")
    # 未安排：无时间
    check(pending_bucket(ev(today), now=now) == "unscheduled", "分桶: 无时间 -> unscheduled")
    # 今天：今天且有时间、未过期
    check(pending_bucket(ev(today, event_time=time(20, 0)), now=now) == "today",
          "分桶: 今天未过期 -> today")


def test_bucket_none_for_future_timed_items():
    """⭐ 有时间的**未来**事项不属于任何桶——返回 None。

    这是「必须有『全部』页」的原因：这类事项既不逾期、不是今天、也有具体时间。
    若标签页只按三个桶切，它会在**每个**标签页里都看不见——
    那就是第二轮"固定窗口让边界事项隐身"那个缺陷的翻版。
    """
    now = datetime(2026, 10, 7, 12, 0, 0)
    future = ev(now.date() + timedelta(days=5), event_time=time(14, 0), title="下周一 14:00 交作业")
    check(pending_bucket(future, now=now) is None,
          "分桶: 有时间的未来事项 -> None（只在「全部」页出现）")


def test_bucket_unscheduled_beats_today():
    """今天但无时间的事项算「未安排」，不算「今天」。

    它还没被规划——"未安排"这个数字正是用来提醒你去安排的。
    """
    now = datetime(2026, 10, 7, 12, 0, 0)
    check(pending_bucket(ev(now.date()), now=now) == "unscheduled",
          "分桶: 今天且无时间 -> unscheduled（优先于 today）")


def test_bucket_overdue_beats_unscheduled():
    """过期的无时间事项算「过期」，不算「未安排」。

    否则一周前极速录入、一直没安排的事项会永远停在"未安排"里，
    永远不会被当成欠账提醒。
    """
    now = datetime(2026, 10, 7, 12, 0, 0)
    check(pending_bucket(ev(now.date() - timedelta(days=7)), now=now) == "overdue",
          "分桶: 过期的无时间事项 -> overdue（优先于 unscheduled）")


def test_bucket_counts_are_complete_partition_of_bucketed_items():
    """⭐ 核心不变量：**每个桶的计数 = 该桶的条数**。

    角标数字与标签页列表都从 `pending_bucket()` 派生，所以两者必须一致。
    这条断言是那个设计的回归——如果将来有人让前端自己写过滤条件，
    这里就会红。
    """
    db = make_session()
    now = datetime(2026, 10, 7, 12, 0, 0)
    today = now.date()
    db.add(ev(today - timedelta(days=1), event_time=time(9, 0), title="过期1"))
    db.add(ev(today - timedelta(days=2), event_time=time(9, 0), title="过期2"))
    db.add(ev(today, title="未安排1"))
    db.add(ev(today, event_time=time(20, 0), title="今天1"))
    db.add(ev(today + timedelta(days=5), event_time=time(14, 0), title="未来1"))
    db.add(ev(today + timedelta(days=30), event_time=time(9, 0), title="未来2"))
    db.commit()

    events, total = pending_events(db)
    summary = pending_summary(events, total, now=now)

    for bucket in ("overdue", "today", "unscheduled"):
        actual = sum(1 for e in events if pending_bucket(e, now=now) == bucket)
        check(summary["counts"][bucket] == actual,
              f"不变量: {bucket} 角标={summary['counts'][bucket]} 等于条数={actual}")

    # 「全部」= 全集，且 = 三个桶 + 不属于任何桶的
    unbucketed = sum(1 for e in events if pending_bucket(e, now=now) is None)
    check(sum(summary["counts"].values()) + unbucketed == total,
          f"不变量: 三桶之和 + 无桶项 = total（{sum(summary['counts'].values())} + "
          f"{unbucketed} = {total}）")
    check(unbucketed == 2, f"不变量: 2 条未来有时间的事项不属于任何桶，实际 {unbucketed}")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print()
    if failures:
        print(f"{len(failures)}/{checks} checks FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"{checks}/{checks} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
