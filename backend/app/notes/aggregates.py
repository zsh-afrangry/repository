"""Notes 模块对外的聚合读数。

**为什么这个文件存在**

`notes_topics.data` 是一个 JSON 列，主题的"目录数/单元数"是**在 Python 侧数出来**的
（`len(data["sections"])` / `len(data["units"])`），没有 SQL 聚合可用。

于是"数单元"这件事存在两种做法，而后一种会埋雷：

- ✅ **本模块提供唯一实现**，dashboard 调它 → JSON 结构知识只存在于 Notes 模块内；
- ❌ dashboard 自己写 `len(row.data["units"])` → 一旦 Notes 改了 data 的结构
  （改名 `units`、改成嵌套），dashboard 会在**运行时**才炸，且报错离原因很远。

所以：**任何模块想知道"有多少单元"，都必须走这里**，
不要在别处直接读 `data["units"]`。

对应文档：docs/14_主页仪表盘与待做事项开发方案.md「§5.3 跨模块取数」。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import NoteTopic


def _counts_of(data: dict) -> tuple[int, int]:
    """从主题的 `data` 里数出 (目录数, 单元数)。

    对缺字段的情况返回 0 而不是抛异常：历史数据或手工插入的行可能没有
    `sections`/`units`，让一个主题把整个首页统计搞崩是不值得的。
    """
    sections = data.get("sections") or []
    units = data.get("units") or []
    return len(sections), len(units)


def topic_counts(data: dict) -> dict:
    """单个主题的计数，供 `list_topics` 复用，保证两处口径一致。"""
    section_count, unit_count = _counts_of(data)
    return {"sectionCount": section_count, "unitCount": unit_count}


def count_all(db: Session) -> dict:
    """全库 Notes 汇总：主题数 / 目录总数 / 单元总数。

    供首页「笔记与文档」统计卡使用。返回结构对应
    `types/portal.ts` 的 `DashboardStats.notes_units`。
    """
    rows = db.scalars(select(NoteTopic.data)).all()

    topics = 0
    sections = 0
    units = 0
    for data in rows:
        topic_sections, topic_units = _counts_of(data or {})
        topics += 1
        sections += topic_sections
        units += topic_units

    return {"topics": topics, "sections": sections, "units": units}
