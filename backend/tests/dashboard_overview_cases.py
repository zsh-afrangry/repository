"""`GET /api/dashboard/overview/` 的隔离用例。

对应文档：docs/14_主页仪表盘与待做事项开发方案.md「§5.1 `GET /api/dashboard/overview/` / §10 验收」。
改动 `app/routers/dashboard.py`、`app/git_stats.py` 或 `app/notes/aggregates.py`
时，先复跑本文件。

跑法（需已安装 fastapi 的 desheng 环境）：

    conda activate desheng
    cd backend
    python tests/dashboard_overview_cases.py

**不碰真实 MySQL、不调真实 git 之外的副作用**：数据库用内存 SQLite 覆盖依赖，
git 部分用桩替换 `git_stats.scan_numstat` / `count_commits`，
因此用例结果与"这台机器当前的 git 状态"无关，可稳定复跑。

**重点验证「--」与「0」的语义区分**（用户第 13 条）：
接口失败/取不到 -> `null`（前端显示 `--`）；真实为零 -> `0`。
这两者绝不能混，否则"后端挂了"会被误读成"我这月没写代码"。
"""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import git_stats  # noqa: E402
from app.database import get_db  # noqa: E402
from app.models.bill import Base, CalendarEvent, CalendarEventTone  # noqa: E402
from app.notes.models import NoteTopic  # noqa: E402
from app.routers.dashboard import router as dashboard_router  # noqa: E402

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


def build_client(*, git_available=True):
    """构造一个只挂 dashboard 路由的测试应用，数据库换成内存 SQLite。

    ⚠️ 两个必须的设置，缺一个就会踩坑（2026-10-06 实测踩过）：

    1. **`StaticPool`**：默认连接池会为每次连接新建一个内存库，
       而内存库是"每连接独立"的，于是建完表的下一个连接看不到表，
       报 `no such table: calendar_events`。
    2. **`check_same_thread=False`**：FastAPI 把同步端点丢进线程池执行，
       而 sqlite3 默认拒绝跨线程使用连接，报
       `SQLite objects created in a thread can only be used in that same thread`。

    因此测试用内存库必须写成
    `create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)`。
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # CalendarEvent 与 NoteTopic 共用同一个 Base，一次 create_all 建全部表。
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    app = FastAPI()
    app.include_router(dashboard_router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: session

    # 桩掉 git：让用例不受本机仓库状态影响。
    original_scan = git_stats.scan_numstat
    original_count = git_stats.count_commits

    if git_available:
        def fake_scan(*, since, pathspec=None):
            # 区分两种调用：带 pathspec = 算行数；不带 = 取提交数
            if pathspec:
                return {"commits": 0, "added": 2714, "deleted": 2163,
                        "net": 551, "binary_files": 0}
            return {"commits": 3, "added": 9999, "deleted": 8888,
                    "net": 1111, "binary_files": 0}

        git_stats.scan_numstat = fake_scan
        git_stats.count_commits = lambda *, since=None: 70
    else:
        def boom(*, since, pathspec=None):
            raise git_stats.GitUnavailable("桩：git 不可用")

        git_stats.scan_numstat = boom
        git_stats.count_commits = lambda *, since=None: (_ for _ in ()).throw(
            git_stats.GitUnavailable("桩：git 不可用"))

    return TestClient(app), session, (original_scan, original_count)


def restore(originals):
    git_stats.scan_numstat, git_stats.count_commits = originals


# ---------------------------------------------------------------- 正常路径
def test_overview_returns_all_four_sections():
    client, session, orig = build_client()
    try:
        r = client.get("/api/dashboard/overview/")
        check(r.status_code == 200, "overview: 200")
        body = r.json()
        check(set(body.keys()) == {"week", "stats", "pending", "archived"},
              "overview: 顶层含 week / stats / pending / archived")
        check(set(body["stats"].keys()) == {"code_lines", "notes_units", "git_commits"},
              "overview: stats 含三项")
    finally:
        restore(orig)


def test_overview_week_shape():
    client, session, orig = build_client()
    try:
        week = client.get("/api/dashboard/overview/").json()["week"]
        expected = {"start", "end", "total", "done", "overdue", "numerator", "ratio"}
        check(set(week.keys()) == expected, "week: 字段齐全")
        check(week["start"] <= week["end"], "week: start <= end")
    finally:
        restore(orig)


# ---------------------------------------------------------------- 待做清单（第二轮）
def test_pending_section_shape():
    client, session, orig = build_client()
    try:
        pending = client.get("/api/dashboard/overview/").json()["pending"]
        expected = {"total", "shown", "counts", "truncated", "items"}
        check(set(pending.keys()) == expected, "pending: 字段齐全")
        check(set(pending["counts"].keys()) == {"overdue", "today", "unscheduled"},
              "pending: counts 含三个分类")
        check(isinstance(pending["items"], list), "pending: items 是列表")
    finally:
        restore(orig)


def test_pending_endpoint_matches_overview_section():
    """`/pending/` 与 `overview` 的两段必须一致——口径不能分叉。

    ⚠️ `/pending/` 的响应是 `{...pending, archived}`（两段拼在一起），
    而 `overview` 里它们是并列的两个键。所以比对时要把 `archived` 摘出来。
    """
    client, session, orig = build_client()
    try:
        monday = date.today() - timedelta(days=date.today().weekday())
        session.add(CalendarEvent(event_date=monday + timedelta(days=30), title="远期",
                                  tone=CalendarEventTone.todo))
        session.add(CalendarEvent(event_date=monday, title="已完成",
                                  tone=CalendarEventTone.todo,
                                  completed_at=datetime.now()))
        session.add(CalendarEvent(event_date=monday, title="已作废",
                                  tone=CalendarEventTone.todo,
                                  archived_at=datetime.now()))
        session.commit()

        overview = client.get("/api/dashboard/overview/").json()
        endpoint = client.get("/api/dashboard/pending/").json()
        archived_from_endpoint = endpoint.pop("archived")

        check(overview["pending"] == endpoint,
              "pending: /pending/ 与 overview.pending 完全一致")
        check(overview["archived"] == archived_from_endpoint,
              "archived: /pending/ 与 overview.archived 完全一致")
    finally:
        restore(orig)


def test_archived_section_shape():
    """`archived` 段的字段契约。刻意**没有** `counts`（见 docs/14 §5.2）。"""
    client, session, orig = build_client()
    try:
        archived = client.get("/api/dashboard/overview/").json()["archived"]
        check(set(archived.keys()) == {"total", "shown", "truncated", "items"},
              "archived: 字段齐全")
        check("counts" not in archived,
              "archived: 不含 counts（分类是给待办优先级用的，废纸篓不需要）")
        check(archived["items"] == [], "archived: 空时 items 为空列表")
    finally:
        restore(orig)


def test_archived_item_excluded_from_pending_section():
    """接口级：作废的事项不在 `pending.items` 里，但在 `archived.items` 里。"""
    client, session, orig = build_client()
    try:
        session.add(CalendarEvent(event_date=date.today(), title="要作废的",
                                  tone=CalendarEventTone.todo,
                                  archived_at=datetime.now()))
        session.add(CalendarEvent(event_date=date.today(), title="留下的",
                                  tone=CalendarEventTone.todo))
        session.commit()

        body = client.get("/api/dashboard/pending/").json()
        pending_titles = [i["title"] for i in body["items"]]
        archived_titles = [i["title"] for i in body["archived"]["items"]]
        check(pending_titles == ["留下的"], f"接口: 作废的不在待做清单，实际 {pending_titles}")
        check(archived_titles == ["要作废的"], f"接口: 作废的在废纸篓，实际 {archived_titles}")
    finally:
        restore(orig)


def test_archived_does_not_affect_week_progress_endpoint():
    """接口级：作废后周进度分母减 1（用户决定①）。"""
    client, session, orig = build_client()
    try:
        monday = date.today() - timedelta(days=date.today().weekday())
        session.add(CalendarEvent(event_date=monday, title="正常"))
        session.add(CalendarEvent(event_date=monday, title="作废的",
                                  archived_at=datetime.now()))
        session.commit()

        week = client.get("/api/dashboard/overview/").json()["week"]
        check(week["total"] == 1,
              f"接口: 周进度分母不含已作废，实际 {week['total']}")
    finally:
        restore(orig)


def test_pending_includes_far_future_item():
    """缺陷1的接口级回归：远期事项必须出现在清单里（不受"本周"窗口限制）。"""
    client, session, orig = build_client()
    try:
        far = date.today() + timedelta(days=200)
        session.add(CalendarEvent(event_date=far, title="很远的 DDL",
                                  tone=CalendarEventTone.todo))
        session.commit()

        pending = client.get("/api/dashboard/pending/").json()
        titles = [i["title"] for i in pending["items"]]
        check("很远的 DDL" in titles, "pending: 200 天后的事项也在清单里（缺陷1）")
        check(pending["total"] == 1, "pending: total 正确")
    finally:
        restore(orig)


def test_pending_items_carry_completed_at_field():
    """清单条目要带 completed_at —— 前端靠它判断勾选状态。"""
    client, session, orig = build_client()
    try:
        session.add(CalendarEvent(event_date=date.today(), title="x",
                                  tone=CalendarEventTone.todo))
        session.commit()
        item = client.get("/api/dashboard/pending/").json()["items"][0]
        check("completed_at" in item, "pending: 条目含 completed_at 字段")
        check(item["completed_at"] is None, "pending: 未完成项的 completed_at 为 null")
    finally:
        restore(orig)


def test_pending_is_empty_list_not_null_when_nothing_pending():
    """没有未完成事项时返回空列表（不是 null）——空列表语义是"确实没有"。"""
    client, session, orig = build_client()
    try:
        pending = client.get("/api/dashboard/pending/").json()
        check(pending["items"] == [], "pending: 无事项时 items 为空列表")
        check(pending["total"] == 0, "pending: total 为 0（真实零值，非 null）")
        check(pending["truncated"] is False, "pending: truncated 为 False")
    finally:
        restore(orig)


def test_overview_counts_notes_units():
    client, session, orig = build_client()
    try:
        session.add(NoteTopic(id="a", version=1, data={
            "title": "A", "description": "", "sortOrder": 1,
            "sections": [{"id": "s1"}], "units": [{"id": "u1"}, {"id": "u2"}],
        }))
        session.add(NoteTopic(id="b", version=1, data={
            "title": "B", "description": "", "sortOrder": 2,
            "sections": [{"id": "s2"}, {"id": "s3"}], "units": [{"id": "u3"}],
        }))
        session.commit()

        notes = client.get("/api/dashboard/overview/").json()["stats"]["notes_units"]
        check(notes == {"topics": 2, "sections": 3, "units": 3},
              f"notes_units: 主题2/目录3/单元3，实际={notes}")
    finally:
        restore(orig)


def test_notes_counts_survive_missing_keys():
    """历史数据可能没有 sections/units 字段，不该让整个首页崩掉。"""
    client, session, orig = build_client()
    try:
        session.add(NoteTopic(id="broken", version=1, data={
            "title": "X", "description": "", "sortOrder": 1,
        }))
        session.commit()
        notes = client.get("/api/dashboard/overview/").json()["stats"]["notes_units"]
        check(notes == {"topics": 1, "sections": 0, "units": 0},
              f"notes_units: 缺字段时计 0 而非抛异常，实际={notes}")
    finally:
        restore(orig)


def test_overview_reports_code_and_commit_stats():
    client, session, orig = build_client()
    try:
        stats = client.get("/api/dashboard/overview/").json()["stats"]
        check(stats["code_lines"]["net"] == 551, "code_lines: net 来自源码后缀口径")
        check(stats["code_lines"]["added"] == 2714, "code_lines: added 正确")
        check(stats["git_commits"] == {"month": 3, "total": 70}, "git_commits: 正确")
    finally:
        restore(orig)


# ---------------------------------------------------------------- 空周：null 而非 NaN
def test_empty_week_ratio_is_null():
    client, session, orig = build_client()
    try:
        week = client.get("/api/dashboard/overview/").json()["week"]
        check(week["ratio"] is None, "空周: ratio 为 null（前端显示 --）")
        check(week["total"] == 0, "空周: total 为 0（真实零值）")
    finally:
        restore(orig)


def test_ratio_never_serialized_as_nan():
    """NaN 不是合法 JSON；一旦泄漏会让前端 JSON.parse 失败。"""
    client, session, orig = build_client()
    try:
        raw = client.get("/api/dashboard/overview/").text
        check("NaN" not in raw, "响应体不含 NaN 字面量")
    finally:
        restore(orig)


# ---------------------------------------------------------------- 降级：null 与 0 必须可区分
def test_git_failure_yields_null_not_zero():
    """git 不可用时必须是 null（--），不能是 0——否则会被误读成'真的没提交'。"""
    client, session, orig = build_client(git_available=False)
    try:
        r = client.get("/api/dashboard/overview/")
        check(r.status_code == 200, "git 失败: 仍返回 200（首页不整页失败）")
        stats = r.json()["stats"]
        check(stats["code_lines"] is None, "git 失败: code_lines 为 null")
        check(stats["git_commits"] is None, "git 失败: git_commits 为 null")
    finally:
        restore(orig)


def test_real_zero_is_zero_not_null():
    """真实为零必须是 0（不是 null）——与'取不到'区分开。"""
    client, session, orig = build_client()
    try:
        # 新的空库 + 桩掉的 git 返回 0 提交
        git_stats.scan_numstat = lambda *, since, pathspec=None: {
            "commits": 0, "added": 0, "deleted": 0, "net": 0, "binary_files": 0}
        git_stats.count_commits = lambda *, since=None: 0

        stats = client.get("/api/dashboard/overview/").json()["stats"]
        check(stats["code_lines"]["net"] == 0, "真零: code_lines.net 为 0（非 null）")
        check(stats["code_lines"]["net"] is not None, "真零: 不是 null")
        check(stats["git_commits"]["month"] == 0, "真零: month 为 0（非 null）")
        check(stats["notes_units"]["units"] == 0, "真零: notes units 为 0（非 null）")
    finally:
        restore(orig)


def test_git_failure_does_not_break_week_or_notes():
    """git 挂掉时，周进度与笔记统计仍应正常返回。"""
    client, session, orig = build_client(git_available=False)
    try:
        monday = date.today() - timedelta(days=date.today().weekday())
        session.add(CalendarEvent(event_date=monday, title="x",
                                  tone=CalendarEventTone.todo))
        session.commit()

        body = client.get("/api/dashboard/overview/").json()
        check(body["week"]["total"] == 1, "git 失败: week 仍正确（total=1）")
        check(body["stats"]["notes_units"] is not None, "git 失败: notes 仍返回")
    finally:
        restore(orig)


# ---------------------------------------------------------------- 既有端点兼容
def test_legacy_git_stats_endpoint_still_works():
    client, session, orig = build_client()
    try:
        r = client.get("/api/dashboard/git-stats/")
        check(r.status_code == 200, "兼容: git-stats/ 仍可用")
        body = r.json()
        check(set(body.keys()) == {"month_commits", "total_commits", "month_start"},
              "兼容: git-stats/ 字段未变")
    finally:
        restore(orig)


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
