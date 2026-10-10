"""为「待做事项 / 本周进度」造测试数据，供浏览器人工验收。

对应文档：docs/14_主页仪表盘与待做事项开发方案.md「§10.1 前置条件」。

**为什么需要它**

`calendar_events` 表原本 0 行，而本周进度的分子/分母**无法用真实数据验收**。
本脚本按用户口径造出覆盖所有分支的最小数据集。

**造什么**（本周 = 当前日历周）：

| 场景 | 类型 | 期望计入分子？ | 理由 |
|---|---|---|---|
| 未过期、未完成 | todo | ✗ | 还没到时间也没勾 |
| 已过期、未完成 | todo | ✗ | **超期未交是失败**（关键回归点） |
| 已完成（未来日期） | todo | ✓ | 手动勾选 |
| 已过期 | meeting | ✓ | 会开完即完成 |
| 未过期 | meeting | ✓ | 见下方说明 |

**用法**

    python backend/scripts/seed_week_demo.py            # 造数
    python backend/scripts/seed_week_demo.py --clear    # 只删 [演示] 行（不动真实数据）
    python backend/scripts/seed_week_demo.py --verify   # 只读当前聚合结果

⚠️ 会**删掉 `calendar_events` 现有全部行**再写入。该表在开发期为测试数据，
但请勿在有真实数据时使用。只碰这一张表，不动 bills / tags / notes。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.crud.calendar import week_bounds, week_progress  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.bill import CalendarEvent, CalendarEventTone  # noqa: E402

OK_MARK = "[OK]"
WARN_MARK = "[--]"


# 本脚本造的数据都带这个前缀。清理时**只删带前缀的行**。
DEMO_PREFIX = "[演示]"


def clear(db) -> int:
    """只删**本脚本造的** `[演示]` 行。

    ⚠️ **这里曾经是整表删除（`db.query(CalendarEvent).delete()`），2026-10-07 造成了真实数据丢失。**
    这个脚本用于"造数 → 人工验收 → 清理"，而清理往往紧跟在验收之后。
    整表删除会把你**在页面上真实创建**的事项一起删掉——它们没有标记，
    无法用"看起来像测试数据"来判断。

    现在的规则：**任何清理都必须能说清"删的是哪些"**，因此按前缀限定范围。
    用户数据零风险，代价是清理后表里可能残留非本脚本的行——那正是我们想要的。
    """
    n = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.title.like(f"{DEMO_PREFIX}%"))
        .delete(synchronize_session=False)
    )
    db.commit()
    return n


def seed(db) -> list[str]:
    monday, sunday = week_bounds()
    today = date.today()
    now = datetime.now()

    # 相对"今天"构造，保证无论哪天跑都落在本周内。
    def day(offset: int) -> date:
        d = monday + timedelta(days=offset)
        # 夹在本周范围内，避免 offset 越界
        return min(max(d, monday), sunday)

    rows = [
        # 1) 未过期、未完成 -> 不进分子
        dict(event_date=day(6), event_time=time(23, 30), title="[演示] 周日晚上的待做",
             detail="未完成且未过期", tone=CalendarEventTone.todo),
        # 2) 已过期、未完成 -> **不进分子**（关键回归点）
        dict(event_date=day(0), event_time=time(0, 5), title="[演示] 已过期的待做",
             detail="超期未交，不应计入进度", tone=CalendarEventTone.todo),
        # 3) 已完成 -> 进分子
        dict(event_date=day(5), event_time=time(18, 0), title="[演示] 已完成的待做",
             detail="手动勾选完成", tone=CalendarEventTone.todo,
             completed_at=now),
        # 4) meeting 已过期 -> 进分子
        dict(event_date=day(0), event_time=time(9, 0), title="[演示] 已开完的会",
             detail="时间已过，视为完成", tone=CalendarEventTone.meeting),
        # 5) meeting 未过期 -> 不进分子
        dict(event_date=day(6), event_time=time(20, 0), title="[演示] 周日的安排",
             detail="还没到时间", tone=CalendarEventTone.meeting),
        # 6) 今天有一条 todo，方便浏览器里直接看到勾选效果
        dict(event_date=today, event_time=time(21, 0), title="[演示] 今晚要做的事",
             detail="点一下即可勾选", tone=CalendarEventTone.todo),
    ]

    created: list[str] = []
    for row in rows:
        event = CalendarEvent(**row)
        db.add(event)
        created.append(f"{row['event_date']} {row.get('event_time') or '全天'} "
                       f"[{row['tone'].value}] {row['title']}")
    db.commit()
    return created


def show(db) -> dict:
    result = week_progress(db)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    rows = db.query(CalendarEvent).order_by(CalendarEvent.event_date,
                                            CalendarEvent.event_time).all()
    print()
    print(f"calendar_events 共 {len(rows)} 行：")
    for r in rows:
        done = "完成" if r.completed_at else "未完成"
        print(f"  #{r.id:<3} {r.event_date} {str(r.event_time or '全天'):>8} "
              f"[{r.tone.value:<7}] {done:<4} {r.title}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clear", action="store_true",
                        help=f"只删除本脚本造的 {DEMO_PREFIX} 行（不动你的真实数据）")
    parser.add_argument("--verify", action="store_true", help="只读当前状态")
    args = parser.parse_args()

    monday, sunday = week_bounds()
    print(f"本周: {monday} (周一) ~ {sunday} (周日)")
    print()

    db = SessionLocal()
    try:
        if args.verify:
            show(db)
            return 0

        if args.clear:
            n = clear(db)
            print(f"{OK_MARK} 已删除本脚本造的 {DEMO_PREFIX} 行（{n} 行）——你的数据不受影响")
            show(db)
            return 0

        removed = clear(db)
        if removed:
            print(f"{WARN_MARK} 先清掉了已有 {removed} 行")
        created = seed(db)
        print(f"{OK_MARK} 已写入 {len(created)} 条演示数据：")
        for line in created:
            print("    " + line)
        print()
        result = show(db)
        print()
        print("预期（按 docs/14 §2 口径）：")
        print("  分母 total      = 6")
        print("  分子 numerator  = 2  （已完成的 todo + 已过期的 meeting）")
        print("  其中 done       = 1")
        print("  其中 overdue    = 2  （已过期的 todo + 已开完的会；仅供参考展示）")
        ok = result["total"] == 6 and result["numerator"] == 2
        print()
        print(f"  {OK_MARK} 与预期一致" if ok else
              f"  [!!] 与预期不一致：total={result['total']} numerator={result['numerator']}")
        return 0 if ok else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
