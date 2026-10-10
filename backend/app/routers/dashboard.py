"""仪表盘聚合读数：一次请求返回首页四张卡所需的全部数据。

对应文档：docs/14_主页仪表盘与待做事项开发方案.md「§5.1 `GET /api/dashboard/overview/`」。

**为什么是聚合端点而不是让前端串几个请求**（用户 2026-10-06 决定）

1. 首屏一次请求拿全，避免四张卡各自 loading 造成布局跳动；
2. "本周"边界、除零、时区这些逻辑集中在后端一处，前端不做重复推导；
3. 前端只负责渲染，逻辑改了不用动前端。

**跨模块读数的边界**（需要后续开发者注意）

「笔记与文档」的数据在 `notes_topics` 表，属于 Notes 模块。本模块**不直接解析**
那个 JSON 列，而是调用 `app.notes.aggregates.count_all()`——JSON 结构知识留在
Notes 模块内。**若将来 Notes 改了 data 结构，只需改 aggregates.py，这里不受影响。**

同理，「代码量/提交数」走 `app.git_stats`，不在本文件里拼 git 命令。

**降级策略**：git 不可用时**不返回错误码**，而是返回 **200 且对应字段为 `null`**。
理由：首页是展示型页面，git 挂了不该让整页失败；前端按 `null` 显示 `--`——
`null` 的语义正是"取不到"，与真实的 0 区分开（见 docs/14 §2.6）。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import git_stats
from app.crud.calendar import (
    archived_events,
    completed_events,
    pending_bucket,
    pending_events,
    pending_summary,
    week_progress,
)
from app.database import get_db
from app.notes import aggregates as notes_aggregates
from app.schemas.calendar import CalendarEventOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _build_pending(db: Session) -> dict:
    """组装「待做事项」清单的返回结构。

    抽成函数是因为 `/overview/` 与 `/pending/` 都要用它——
    两处各写一遍迟早会走样（这正是第二轮"两套窗口"的教训）。

    **每条事项带上 `bucket` 字段**（标签页分组），与 `counts` 由**同一个**
    `pending_bucket()` 派生。这样前端按 `bucket === 当前标签页` 过滤时，
    列表条数必然等于角标数字——前端**不需要**（也不应该）自己重算判定规则。
    """
    events, total = pending_events(db)
    summary = pending_summary(events, total)
    return {
        **summary,
        # 用 CalendarEventOut 序列化，避免手工拼字段时漏掉 completed_at / archived_at 之类的新列。
        "items": [
            {
                **CalendarEventOut.model_validate(e).model_dump(mode="json"),
                # `None` = 有时间的未来事项，只在「全部」页出现（见 pending_bucket 的说明）。
                "bucket": pending_bucket(e),
            }
            for e in events
        ],
    }


def _build_archived(db: Session) -> dict:
    """组装「已作废」（废纸篓）的返回结构。

    与 `_build_pending` 一样抽成函数，供 `/pending/` 与 `/overview/` 共用。

    刻意**只返回条目与总数**，不返回分类计数——废纸篓不需要
    "过期/今天/未安排"那套分类（那些是给待办优先级用的）。
    """
    events, total = archived_events(db)
    return {
        "total": total,
        "shown": len(events),
        "truncated": total > len(events),
        "items": [CalendarEventOut.model_validate(e).model_dump(mode="json") for e in events],
    }


def _build_completed(db: Session) -> dict:
    """组装「已完成」的返回结构（抽屉的第 5 个标签页）。

    结构与 `_build_archived` 相同——同样只给条目与总数，不给分类计数。
    已完成的条目不再需要"该不该做"的优先级提示。

    ⚠️ 它**不在** `pending.items` 里，所以「全部」标签页不含已完成项
    （用户 2026-10-07 决定）：三个列表互斥，主视图不会被已完成的事淹没。
    """
    events, total = completed_events(db)
    return {
        "total": total,
        "shown": len(events),
        "truncated": total > len(events),
        "items": [CalendarEventOut.model_validate(e).model_dump(mode="json") for e in events],
    }


@router.get("/git-stats/")
def get_git_stats():
    """既有端点，保留不动（兼容既有调用）。

    新代码请用 `/dashboard/overview/`；本端点只为不破坏已发布的接口而存在。
    """
    today = None
    stats = git_stats.code_stats(today)
    return {
        "month_commits": stats["git_commits"]["month"],
        "total_commits": stats["git_commits"]["total"],
        "month_start": stats["code_lines"]["month_start"],
    }


@router.get("/overview/")
def get_overview(db: Session = Depends(get_db)):
    """首页仪表盘聚合读数。

    返回的每一项都可能为 `null`，语义是**取不到**（前端显示 `--`）；
    真实的零值返回 `0`。两者必须能区分——这是 2026-10-06 的明确要求。
    """
    # 周进度：纯数据库查询，不会因外部命令失败。空周时 ratio 为 None。
    week = week_progress(db)

    # Notes 汇总：同样只依赖数据库。
    notes = notes_aggregates.count_all(db)

    # 待做清单与废纸篓：纯数据库查询。
    pending = _build_pending(db)
    archived = _build_archived(db)
    completed = _build_completed(db)

    # Git 统计：唯一可能失败的部分（git 未安装/不在 PATH/不是仓库/超时）。
    # 失败时把这两项置 None，其余照常返回，页面仍可用。
    try:
        git = git_stats.code_stats()
        code_lines: Optional[dict] = git["code_lines"]
        git_commits: Optional[dict] = git["git_commits"]
    except git_stats.GitUnavailable:
        code_lines = None
        git_commits = None

    return {
        "week": week,
        "stats": {
            "code_lines": code_lines,
            "notes_units": notes,
            "git_commits": git_commits,
        },
        "pending": pending,
        "archived": archived,
        "completed": completed,
    }


@router.get("/pending/")
def get_pending(db: Session = Depends(get_db)):
    """「待做事项」清单 + 废纸篓（**所有未完成的事项，不限日期**）。

    单独开一个端点（而不是塞进 `/overview/`）的原因：
    勾选完成、新增或作废事项之后只需刷新清单，不必重取 git 统计与 Notes 汇总
    （那两项开销大且不会因勾选而变）。首页首屏仍可一次拿到全部。

    返回 `{...pending, archived: {...}}` —— 两者一起给，因为抽屉同时显示
    "待做列表"与"已作废折叠区"，分两次请求只会在作废/恢复时产生中间态。
    """
    return {
        **_build_pending(db),
        "archived": _build_archived(db),
        "completed": _build_completed(db),
    }
