"""一次性迁移：把 `calendar_events` 重建为 2026-10-06 的新结构。

对应文档：docs/14_主页仪表盘与待做事项开发方案.md「§2.1 数据模型 / §3.2 表结构管理」。

**这个脚本做什么**

把 `calendar_events` 从旧结构改为新结构：

| 变化 | 旧 | 新 |
|---|---|---|
| `tone` 枚举 | `enum('todo','plan','meeting','bill')` | `enum('todo','meeting')` |
| 完成状态 | 无 | 新增 `completed_at DATETIME NULL` |

**为什么用 DROP + CREATE 而不是 ALTER**

执行时该表为 **0 行**（已实测），两种方式结果等价。选 DROP + CREATE 的原因：
改枚举用 `ALTER TABLE ... MODIFY COLUMN` 也能做到，但要手写完整列定义
（字符集、排序规则、注释都得抄一遍），容易抄漏；而重建让**模型成为唯一事实来源**，
不会有手抄偏差。

**⚠️ 为什么必须单独写这个脚本，而不是让人跑 `backend/sql/knowledgemap.sql`**

那份导出文件含**全部 6 张表**的 `DROP TABLE`。直接执行会连 `notes_topics`
（7 行种子数据）和 `bills`（29 行真实账单）一起删掉。本脚本**只碰
`calendar_events` 一张表**，其余表原样不动。

**幂等性**：重复执行安全——它先检测结构，已是新结构就直接跳过。

**用法**
    python backend/scripts/rebuild_calendar_events.py --dry-run   # 只看会做什么
    python backend/scripts/rebuild_calendar_events.py             # 实际执行

**另一台机器上怎么用**：Ubuntu 那边的库同样需要这次变更。
把本文件随 git 带过去执行一次即可（`KM_MYSQLDUMP` 无关，它只用 SQLAlchemy）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import inspect, text  # noqa: E402

from app.database import engine  # noqa: E402
from app.models.bill import Base, CalendarEvent  # noqa: E402

OK_MARK = "[OK]"
WARN_MARK = "[--]"
FAIL_MARK = "[!!]"

TABLE = CalendarEvent.__tablename__

# 期望的 tone 取值。与模型保持一致（见 models/bill.py 的 CalendarEventTone）。
EXPECTED_TONES = {"todo", "meeting"}


def expected_columns() -> dict[str, str]:
    """从 **SQLAlchemy 模型**推导期望的列名集合。

    ⚠️ 刻意不写死"新增了哪一列"。第一版硬编码了 `completed_at`，
    于是 2026-10-07 再加 `archived_at` 时它会误报"已是最新结构"——
    每加一列就得改一次脚本，等于把模型结构抄了两份。
    现在改为与模型比对：**缺任何一列**（或多了模型里没有的列）都能发现。
    """
    return {column.name for column in CalendarEvent.__table__.columns}


def current_column_types() -> dict[str, str]:
    """返回 {列名: 类型字符串}。表不存在时返回空 dict。

    ⚠️ 对 MySQL 的 ENUM，必须读 `information_schema.COLUMNS.COLUMN_TYPE`，
    不能用 SQLAlchemy inspector 的 `str(column["type"])` —— 后者对 ENUM 只给出
    字符串 `"ENUM"`，**不含具体取值**，会让"是否已迁移"的判断永远为假。
    这是实测踩到的坑（2026-10-06）：曾据此误报 `tone 枚举需收敛: ['ENU'] -> ...`。
    """
    inspector = inspect(engine)
    if TABLE not in inspector.get_table_names():
        return {}

    if engine.dialect.name == "mysql":
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT COLUMN_NAME, COLUMN_TYPE FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
                    "ORDER BY ORDINAL_POSITION"
                ),
                {"t": TABLE},
            ).all()
        return {name: column_type for name, column_type in rows}

    # 非 MySQL（例如测试用的 SQLite）：退回 inspector。
    return {c["name"]: str(c["type"]) for c in inspector.get_columns(TABLE)}


def current_column_comments() -> dict[str, str]:
    """返回 {列名: 列注释}（MySQL only；其他方言返回空 dict）。

    为什么需要它：本表曾被 DROP + CREATE 重建过一次，当时因为模型里没写
    `comment=`，原库的列注释全部丢失。只检查 `tone` 与 `completed_at`
    无法发现这种"结构对了但注释没了"的回退，所以把注释也纳入比对。
    """
    if engine.dialect.name != "mysql":
        return {}
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT COLUMN_NAME, COLUMN_COMMENT FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
                "ORDER BY ORDINAL_POSITION"
            ),
            {"t": TABLE},
        ).all()
    return {name: (comment or "") for name, comment in rows}


def expected_comments() -> dict[str, str]:
    """从模型读出应有的列注释，作为比对基准（模型是唯一事实来源）。"""
    return {
        column.name: (column.comment or "")
        for column in CalendarEvent.__table__.columns
    }


def enum_values_from_type(type_str: str) -> set[str]:
    """从 MySQL 的 `enum('todo','meeting')` 字符串里抽出取值集合。

    解析不出取值时返回**空集**表示"未知"。注意区分"未知"与"空枚举"：
    调用方只有拿到非空集合才会做严格比较。
    """
    lowered = type_str.lower()
    if not lowered.startswith("enum"):
        return set()
    if "(" not in type_str or ")" not in type_str:
        return set()
    inside = type_str[type_str.find("(") + 1: type_str.rfind(")")]
    return {part.strip().strip("'\"") for part in inside.split(",") if part.strip()}


def row_count() -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(f"SELECT COUNT(*) FROM `{TABLE}`")).scalar() or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="只报告将要做什么，不改库")
    args = parser.parse_args()

    print(f"数据库: {engine.url.render_as_string(hide_password=True)}")
    print(f"目标表: {TABLE}")
    print()

    columns = current_column_types()

    # ---- 情况 1：表不存在 ----
    if not columns:
        print(f"{WARN_MARK} 表不存在。将直接按模型创建。")
        if args.dry_run:
            print("     （dry-run，未执行）")
            return 0
        Base.metadata.create_all(bind=engine, tables=[CalendarEvent.__table__])
        print(f"{OK_MARK} 已创建")
        return 0

    # ---- 检查结构是否已是新的 ----
    tone_values = enum_values_from_type(columns.get("tone", ""))
    wanted_columns = expected_columns()
    actual_columns = set(columns)
    missing_columns = sorted(wanted_columns - actual_columns)
    extra_columns = sorted(actual_columns - wanted_columns)
    structure_ok = (tone_values == EXPECTED_TONES) and not missing_columns

    # 注释比对：只检查两边都有的列。注释漂移同样需要重建来修复
    # （2026-10-06 实测：曾因模型缺 comment= 导致重建后注释全丢）。
    actual_comments = current_column_comments()
    wanted_comments = expected_comments()
    comment_drift = {
        name: (actual_comments.get(name, ""), wanted)
        for name, wanted in wanted_comments.items()
        if name in actual_comments and actual_comments.get(name, "") != wanted
    }
    already_migrated = structure_ok and not comment_drift

    print("当前结构:")
    for name, type_str in columns.items():
        comment = actual_comments.get(name, "")
        suffix = f"  -- {comment}" if comment else "  -- (无注释)"
        print(f"    {name:16} {type_str}{suffix}")
    print()
    print(f"模型期望 {len(wanted_columns)} 列: {', '.join(sorted(wanted_columns))}")
    print()

    if already_migrated:
        print(f"{OK_MARK} 已是新结构（tone={sorted(tone_values)}，列与模型一致），"
              f"且 {len(wanted_comments)} 列注释一致，无需迁移")
        return 0

    # ---- 情况 2：需要迁移 ----
    if tone_values and tone_values != EXPECTED_TONES:
        print(f"{WARN_MARK} tone 枚举需收敛: {sorted(tone_values)} -> {sorted(EXPECTED_TONES)}")
    if missing_columns:
        print(f"{WARN_MARK} 缺少列（模型有、库里没有）: {', '.join(missing_columns)}")
    if extra_columns:
        # 只提示，不作为"需要迁移"的理由：库里多出来的列可能是别人手工加的，
        # 重建会把它删掉——值得让人先看一眼再决定。
        print(f"{WARN_MARK} 库中多出模型没有的列（重建会**删除**它们）: {', '.join(extra_columns)}")
    if comment_drift:
        print(f"{WARN_MARK} {len(comment_drift)} 列的注释与模型不一致:")
        for name, (got, want) in comment_drift.items():
            print(f"       {name}: 库中={got!r}  模型={want!r}")

    n = row_count()
    print(f"{WARN_MARK} 表中现有 {n} 行")

    if n > 0:
        # 表非空——DROP 会丢数据。这不是预期情况，停下来让人判断。
        # 这里**给出针对性的 ALTER 建议**（而不是让人自己想办法），
        # 因为"表非空"迟早会遇到，而不加索引的 DATETIME 列用 ALTER 加是安全的。
        print()
        print(f"{FAIL_MARK} 表非空（{n} 行），DROP + CREATE 会**丢失这些数据**。")
        print("     这些数据看起来要保留，因此不要重建。改用 ALTER 增量迁移：")
        if tone_values and tone_values != EXPECTED_TONES:
            print(f"       ALTER TABLE `{TABLE}` MODIFY COLUMN `tone` "
                  f"ENUM({','.join(repr(t) for t in sorted(EXPECTED_TONES))}) NOT NULL;")
        for name in missing_columns:
            column = CalendarEvent.__table__.columns[name]
            sql_type = column.type.compile(engine.dialect)
            nullability = "" if column.nullable else " NOT NULL"
            print(f"       ALTER TABLE `{TABLE}` ADD COLUMN `{name}` {sql_type}{nullability} NULL;")
        if comment_drift:
            print("       -- 另有列注释漂移，见上方逐列列出")
        print("     执行后跑一次 `python scripts/rebuild_calendar_events.py` 复核。")
        return 1

    if args.dry_run:
        print()
        print(f"（dry-run）将执行: DROP TABLE `{TABLE}` 然后按模型重建。未实际执行。")
        return 0

    # 表为空，安全重建。
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE `{TABLE}`"))
    print(f"{OK_MARK} 已 DROP")
    Base.metadata.create_all(bind=engine, tables=[CalendarEvent.__table__])
    print(f"{OK_MARK} 已按模型重建")

    # ---- 复核 ----
    after = current_column_types()
    after_tones = enum_values_from_type(after.get("tone", ""))
    still_missing = sorted(expected_columns() - set(after))
    print()
    print("迁移后结构:")
    for name, type_str in after.items():
        print(f"    {name:16} {type_str}")
    print()

    if after_tones == EXPECTED_TONES and not still_missing:
        print(f"{OK_MARK} 复核通过：tone={sorted(after_tones)}，{len(after)} 列与模型一致")
        return 0

    print(f"{FAIL_MARK} 复核未通过：tone={sorted(after_tones)}，仍缺列 {still_missing}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
