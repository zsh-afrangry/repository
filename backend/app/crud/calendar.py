from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bill import CalendarEvent, CalendarEventTone
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate

# `event_time` 为空时的兜底时刻：当天 23:59:59。
# 选择"当天结束"而非 00:00:00 的原因（用户 2026-10-06 决定）：
#   - 用户把 todo 当作业 DDL 用（"下周三要交作业"），只给日期不给时刻是常态；
#   - 若兜底成 00:00:00，则当天一创建就算过期，语义荒谬；
#   - 兜底成当天结束 = "今天做的事今天做完"，符合直觉。
# 注意：MySQL TIME 本身能存到秒，所以"按秒计"在 DATE+TIME 两列结构下完全成立。
_END_OF_DAY = time(23, 59, 59)


def event_due_at(event: CalendarEvent) -> datetime:
    """把 `event_date` + `event_time` 合成一个可比较的 datetime。

    **所有"是否过期"的判断都必须走这个函数**，不要在各处手写两列比较。
    原因（docs/14 §4.2）：两列结构中，跨天比较写成
    `event.event_time < now.time()` 是**错的**——它忽略了日期，
    会让"上周三 10:00"和"今天 10:00"给出相同结论。
    """
    return datetime.combine(event.event_date, event.event_time or _END_OF_DAY)


def is_overdue(event: CalendarEvent, *, now: Optional[datetime] = None) -> bool:
    """事项是否**已过时间点**（仅表示时间已过，不含"是否算达成"的语义）。

    定义：已完成的（`completed_at` 非空）永远返回 False——完成就是完成；
    否则到期时刻（见 `event_due_at`）早于 `now` 即为 True。

    ⚠️ 本函数回答的是"时间过了没有"，**不回答"这算不算达成"**。
    那个判断与 `tone` 有关，见 `counts_as_progress()`。
    两个问题刻意分开，因为 `todo` 与 `meeting` 过期的含义相反（见下）。
    """
    if event.completed_at is not None:
        return False
    return event_due_at(event) < (now or datetime.now())


def counts_as_progress(event: CalendarEvent, *, now: Optional[datetime] = None) -> bool:
    """该事项是否计入「本周进度」的**分子**（= 算作已达成）。

    ⚠️ 这是本模块语义最微妙的一处，`todo` 与 `meeting` 的规则**相反**：

    | 类型 | 完成方式 | 过期意味着 |
    |---|---|---|
    | `meeting`（安排/会议） | 时间去过了就算发生 | **算达成** —— 会开完了 |
    | `todo`（待做事项/作业 DDL） | 只能靠手动勾选 | **算失败** —— 超期未交 |

    所以：

    - `meeting` → 手动完成 **或** 时间已过，都算达成；
    - `todo`    → **只有**手动完成才算达成；过期不算，反而是没做到。

    为什么必须区分（2026-10-06 实测发现的错误）：若对 `todo` 也用"过期即达成"，
    那么拖着不做的作业会**让进度数字变高**，指标鼓励拖延，完全违背初衷。
    这个错误在开发期被端到端测试抓到（见 docs/14 §9 的记录）。
    """
    completed = event.completed_at is not None
    if event.tone == CalendarEventTone.todo:
        # todo 只有"手动完成"一条达成路径。
        return completed
    # meeting（以及未来新增的"强时间"类型）：手动完成或时间已过都算达成。
    return completed or (event_due_at(event) < (now or datetime.now()))


def week_bounds(anchor: Optional[date] = None) -> tuple[date, date]:
    """返回 `anchor` 所在**日历周**的 (周一, 周日)。

    用户定义（2026-10-06）："'本周'的定义是'当前所在的日历周'，
    哪怕今天是周六，本周也是'到明天为止'。"

    即：周一为一周之始、周日为末。与前端日历组件的排布一致
    （`Dashboard.vue` 的 `calendarDays` 用"Monday=0 based offset"）。
    """
    today = anchor or date.today()
    monday = today - timedelta(days=today.weekday())  # weekday(): 周一=0
    return monday, monday + timedelta(days=6)


def week_progress(db: Session, *, anchor: Optional[date] = None,
                  now: Optional[datetime] = None) -> dict:
    """「本周进度」的分子/分母。

    口径（用户 2026-10-06，措辞按类型展开后等价）：
        分母 = 本周所有待做事项 + 本周所有安排
        分子 = 已完成的待做事项 + 已过期的安排

    ⚠️ 两类事项的"达成"规则**相反**，由 `counts_as_progress()` 统一判定：
      - `todo`   ：只有手动勾选才算达成，**过期不算**（超期未交是失败）；
      - `meeting`：手动勾选 **或** 时间已过都算达成（会开完即完成）。

    返回字段里的 `overdue` 是"已过时间点且未完成"的计数，**仅供展示**；
    它**不等于**分子里的贡献项——对 `meeting` 来说过期计入分子，
    对 `todo` 来说过期不计入。前端若要展示分子构成，用 `numerator` 即可。

    ⚠️ 分母为 0 时 `ratio` 返回 **None**（不是 0、不是 NaN）。
    前端据此显示 `--`。原因：周一早上必然为空，
    `(0/0)*100` 会得到 NaN，进而让 `stroke-dasharray="NaN, 100"` 整个失效
    （见 docs/14 §10.2 V3）。
    """
    monday, sunday = week_bounds(anchor)
    reference_now = now or datetime.now()

    events = db.scalars(
        select(CalendarEvent).where(
            CalendarEvent.event_date >= monday,
            CalendarEvent.event_date <= sunday,
            # 已作废的事项**分子分母都不算**（用户 2026-10-07 决定，见 §4.1）：
            # 作废 = "我决定不做了"，它不是承诺，不该出现在任何达成率里。
            # 否则"清理积压"这个动作会莫名其妙地改变完成率。
            CalendarEvent.archived_at.is_(None),
        )
    ).all()

    total = len(events)
    done = sum(1 for e in events if e.completed_at is not None)
    overdue = sum(1 for e in events if is_overdue(e, now=reference_now))
    numerator = sum(1 for e in events if counts_as_progress(e, now=reference_now))

    return {
        "start": monday.isoformat(),
        "end": sunday.isoformat(),
        "total": total,
        "done": done,
        "overdue": overdue,
        "numerator": numerator,
        "ratio": round(numerator / total * 100, 1) if total else None,
    }


# --------------------------------------------------------------------------
# 「待做事项」清单（第二轮，2026-10-07）
#
# 与上面的 `week_progress` 是**两套口径，互不复用**：
#   - week_progress ：「本周」这一固定窗口的达成率（周报）
#   - pending_events：**所有未完成的事项**，不限日期（清单）
# 之所以强调这点：待做卡片曾用 week_progress 的窗口取数，导致
# "下周一交作业"看不到、翻月后卡片还会变空（见 docs/14 §11.1）。
# --------------------------------------------------------------------------

# 清单一次最多返回多少条。超出时**如实返回总数**，由前端提示，
# 绝不静默截断——静默截断会让事项"隐身"，这正是本轮要修的问题。
PENDING_LIMIT = 200


def pending_events(db: Session, *, limit: int = PENDING_LIMIT) -> tuple[list[CalendarEvent], int]:
    """返回（未完成事项列表, 未完成总数）。

    **取数口径**：`completed_at IS NULL` **且** `archived_at IS NULL` 的事项，
    **不限日期**——既包括未来的，也包括过去未完成（欠账）的。

    ⚠️ **这是"未完成"的唯一查询入口**，不要在别处写 `completed_at.is_(None)`。
    两个条件各有用途：
      - `completed_at IS NULL` 排除"已做到"的；
      - `archived_at IS NULL` 排除"我决定不做了"的（废纸篓语义，见 §2.5）。
    集中在这里，将来再加状态条件也只需改这一处。

    **排序**（用户 2026-10-07 定的规则，见 docs/14 §2.4）：

        1. `event_time` 为空的排在最前 —— 这些是"只填了标题、还没规划"的事项，
           需要先被看到并决定何时做（清空收集箱）。
           组内**最新的排最前**（次级键 `-id`）。
        2. 其余按 (event_date, event_time) 升序。

    刻意**不按 event_date 单独排序**：否则"只填标题、今天刚记下"的事项
    会排在"昨天就该交的作业"之后，与"未规划的先看"这一意图冲突。
    """
    all_pending = db.scalars(
        select(CalendarEvent).where(
            CalendarEvent.completed_at.is_(None),
            CalendarEvent.archived_at.is_(None),
        )
    ).all()

    # 排序键：无时间的排在前面（0），有时间的按日期+时刻（1, 日期, 时刻）。
    # SQL 里表达"NULL 优先 + 两列升序"跨方言写法繁琐，而事项量很小
    # （个人使用，几十~几百条），所以在 Python 侧排序，可读性更好且易测。
    def sort_key(event: CalendarEvent):
        if event.event_time is None:
            # 「未安排」组：**最新的排最前**（用户 2026-10-07 决定）。
            #
            # 用 `-id` 而不是原顺序：id 自增，等价于创建时间倒序。
            # 为什么需要这个次级键——两条都无时间时，前三元组完全相同，
            # `sorted()` 是**稳定排序**，于是保留查询返回顺序（MySQL 未指定
            # ORDER BY 时通常按主键升序），结果就是"刚记的沉到下面"。
            # 用户实测发现了这一点：新录入的事项没有出现在顶部。
            #
            # 为什么选"最新在前"：刚记下的事需要立刻可见，否则用户会怀疑"记上了吗"。
            # 这与"清空收集箱"的直觉一致——越新越需要被安排。
            return (0, -event.id)
        return (1, event.event_date, event.event_time)

    ordered = sorted(all_pending, key=sort_key)
    return ordered[:limit], len(ordered)


def pending_bucket(event: CalendarEvent, *, now: Optional[datetime] = None) -> Optional[str]:
    """判断一条待做事项属于哪个**标签页**（bucket）。返回 `None` 表示不属于任何分类页。

    **这是分桶的唯一判定处**——`pending_summary()` 的计数与前端标签页的过滤
    都从这里派生，所以"标签上的数字"与"标签里的条数"**在构造上不可能不一致**。
    若让前端自己写过滤条件，两者迟早分叉（见 docs/14 §12.3 的教训）。

    判定**按优先级，互不重叠**（一条事项只进一个桶）：

    | 优先 | 桶 | 判定 | 用户该做什么 |
    |---|---|---|---|
    | 1 | `overdue` 过期 | `is_overdue()`（精确到秒，与卡片上的「过期」标记同口径） | 补做，或改期 |
    | 2 | `unscheduled` 未安排 | `event_time IS NULL` | 安排一个时间 |
    | 3 | `today` 今天 | `event_date == 今天` | 今天做 |
    | — | `None` | 有时间的**未来**事项 | 不紧急，只在「全部」里出现 |

    ⚠️ **判定顺序是刻意的**：`unscheduled` 必须排在 `today` 之前，
    否则"只填了标题、默认落在今天"的极速录入事项会被算作"今天"，
    而它其实还没被规划——"未安排"正是用来提醒你去安排的。

    ⚠️ **`unscheduled` 不能只看"时间是否为空"而忽略日期**：
    一条一周前极速录入、一直没安排的事项，`is_overdue()` 会因
    `event_date` 已过而返回 True，从而正确地落进 `overdue`。
    否则它会永远停在"未安排"里，永远不会被当成欠账提醒。

    ⚠️ **返回 `None` 是必要的，不是遗漏**：三个桶**不构成完整划分**。
    一条"下周一 14:00 交作业"既不逾期、不是今天、也有具体时间，
    三个桶都不属于。因此前端**必须有「全部」页**作为兜底——
    否则这类事项会在每个标签页里都看不见，那就是第二轮
    "固定窗口让边界事项隐身"那个缺陷的翻版。
    """
    reference_now = now or datetime.now()
    if is_overdue(event, now=reference_now):
        return "overdue"
    if event.event_time is None:
        return "unscheduled"
    if event.event_date == reference_now.date():
        return "today"
    return None


def pending_summary(events: list[CalendarEvent], total: int, *,
                    now: Optional[datetime] = None) -> dict:
    """把清单整理成前端要的结构：分类计数 + 是否被截断。

    分类计数是**必需**的（见 docs/14 §2.4）：摘要只显示 3 条，
    被截掉的事项必须通过数字仍然可见，否则会变成新的"隐身"。

    计数由 `pending_bucket()` 派生（判定规则见那个函数）。
    """
    counts = {"overdue": 0, "unscheduled": 0, "today": 0}
    for event in events:
        bucket = pending_bucket(event, now=now)
        if bucket is not None:
            counts[bucket] += 1
        # bucket 为 None（有时间的未来事项）不计数——不紧急，不需要在摘要里占注意力。
        # 因此三个数字之和 ≤ total，前端不要假设它们相加等于 total。

    return {
        "total": total,
        "shown": len(events),
        "counts": counts,
        "truncated": total > len(events),
    }


def archived_events(db: Session, *, limit: int = PENDING_LIMIT) -> tuple[list[CalendarEvent], int]:
    """返回（已作废事项列表, 总数）——「废纸篓」的内容。

    **排序**：按作废时间**倒序**（最近作废的在前）。
    这里刻意不用 `pending_events()` 那套"未安排优先"的规则——
    废纸篓是**回顾**用的，时间倒序最符合"我刚作废了什么"的查找习惯。

    **三个列表互斥且完备**（一条事项只出现在一处）：

    | 列表 | 判据 |
    |---|---|
    | 待做清单 `pending_events()` | `completed_at IS NULL AND archived_at IS NULL` |
    | **已完成** `completed_events()` | `completed_at IS NOT NULL AND archived_at IS NULL` |
    | 废纸篓 `archived_events()` | `archived_at IS NOT NULL`（无论是否完成过） |

    ⚠️ 「已作废」优先级最高：一条**既完成又作废**的事项只进废纸篓，
    不会同时出现在「已完成」里——否则两处都能看到它，用户会怀疑哪个是真的。
    """
    all_archived = db.scalars(
        select(CalendarEvent).where(CalendarEvent.archived_at.is_not(None))
    ).all()
    ordered = sorted(all_archived, key=lambda e: e.archived_at, reverse=True)
    return ordered[:limit], len(ordered)


def completed_events(db: Session, *, limit: int = PENDING_LIMIT) -> tuple[list[CalendarEvent], int]:
    """返回（已完成事项列表, 总数）——抽屉「已完成」标签页的内容。

    **为什么需要它**：勾选完成后事项会离开待做清单，而在此之前**没有任何地方**
    能看到或撤销它——误勾了就找不回来。这个列表补上那个缺口。

    **排序**：按完成时间**倒序**（最近完成的在前）。与废纸篓同理——
    它是回顾用的（"我刚做完了什么"），而不是待办优先级那套"未安排优先"。

    **不含已作废的**：见 `archived_events()` 的互斥表。
    """
    done = db.scalars(
        select(CalendarEvent).where(
            CalendarEvent.completed_at.is_not(None),
            # 既完成又作废的只进废纸篓（否则两处都出现）。
            CalendarEvent.archived_at.is_(None),
        )
    ).all()
    # completed_at 非空是 WHERE 保证的，这里直接取用。
    ordered = sorted(done, key=lambda e: e.completed_at, reverse=True)
    return ordered[:limit], len(ordered)


def create_calendar_event(db: Session, data: CalendarEventCreate) -> CalendarEvent:
    event = CalendarEvent(**data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_calendar_event(db: Session, event_id: int) -> CalendarEvent | None:
    return db.get(CalendarEvent, event_id)


def list_calendar_events(
    db: Session,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[CalendarEvent]:
    query = select(CalendarEvent)
    if date_from is not None:
        query = query.where(CalendarEvent.event_date >= date_from)
    if date_to is not None:
        query = query.where(CalendarEvent.event_date <= date_to)

    return list(
        db.scalars(
            query.order_by(
                CalendarEvent.event_date.asc(),
                CalendarEvent.event_time.asc(),
                CalendarEvent.id.asc(),
            )
        ).all()
    )


def update_calendar_event(
    db: Session,
    event: CalendarEvent,
    data: CalendarEventUpdate,
) -> CalendarEvent:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event


def delete_calendar_event(db: Session, event: CalendarEvent) -> None:
    db.delete(event)
    db.commit()
