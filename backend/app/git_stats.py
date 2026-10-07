"""从本地 git 仓库读取仪表盘统计（只读，不依赖数据库）。

**为什么是独立顶层模块而不是放进 `crud/`**

项目门户代码按层组织（`models/` `schemas/` `crud/` `routers/`），但 git 不是数据库，
塞进 `crud/` 会让那一层名不副实。这里沿用 `app/web_host.py` 已确立的先例：
**与某一层无关的聚焦能力，作为 `app/` 下的独立模块**。

**为什么不用 GitHub API**（用户 2026-10-06 决定）
本机 `git` 已能回答"这周/这月改了多少代码"，且零凭证、零速率限制。
GitHub API 反而只覆盖推到远端的部分，还要处理 token、分页与限流。

对应文档：docs/14_主页仪表盘与待做事项开发方案.md「§4.2 代码量口径 / §5.1 `GET /api/dashboard/overview/`」。
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

# 仓库根。本文件位于 backend/app/ 下，向上两级即仓库根。
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

# 代码量口径④：只算源码后缀（用户 2026-10-06 选定的正式口径）。
#
# 刻意**不含** .json —— 否则 package-lock.json 之类锁文件的一次更新
# 就能让数字暴涨几千行，指标随之失去意义。
# 也不含 .md/.txt —— 文档字数不是"代码量"；想连文档一起统计就换口径③。
SOURCE_SUFFIXES: tuple[str, ...] = (".py", ".ts", ".vue", ".css", ".sh", ".js")

# 永远排除的目录（pathspec 的 `:(exclude)` 语法）。
#
# ⚠️ **为什么必须显式排除**：只按后缀过滤是不够的——`frontend_example/` 里有 20 个
# 第三方示例文件（`app.js` / `marked.min.js` / `tex-mml-chtml.js` / `styles.css` …），
# 它们**都匹配 `.js` / `.css` 后缀**。哪天有人动了那个目录，"代码量"就会把
# 别人的 vendored 代码算成你的产出。
# 2026-10-06 实测：该目录当月没被改动，所以排除前后数字相同（2714/2163）——
# **看不出差别不等于不需要**，它防的是将来。
#
# `已归档/` 一并排除：那是历史文档快照，不属于当前产出。
EXCLUDED_PATHSPECS: tuple[str, ...] = (
    ":(exclude)frontend_example/**",
    ":(exclude)已归档/**",
)

# 提交分隔符。选一个不会出现在 numstat 行首的字符串。
_COMMIT_MARKER = "__KM_COMMIT__"

# git 命令超时（秒）。两次调用共享这个预算——单次实测约 100~180ms，
# 留足余量以容忍大仓库或磁盘抖动。
_GIT_TIMEOUT = 15


class GitUnavailable(RuntimeError):
    """git 不可用（未安装、不在 PATH、超时，或目标不是仓库）。

    调用方应把它转成 HTTP 503 并让前端显示 `--`，而不是 500。
    """


def _run_git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GIT_TIMEOUT,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise GitUnavailable(f"git {' '.join(args[:2])} 执行失败") from error
    return result.stdout


def month_start(today: date | None = None) -> date:
    """本月 1 号（本地时区）。

    用 `date.today()` 而非 `utcnow()` —— 与前端一致，且在 UTC+8 的凌晨
    不会把"本月"算成上个月（`utils/date.ts` 里有同类问题的完整说明）。
    """
    return (today or date.today()).replace(day=1)


def count_commits(*, since: date | None = None) -> int:
    """提交总数；给了 `since` 就只数该日期之后的。"""
    args = ["rev-list", "--count"]
    if since is not None:
        args.append(f"--since={since.isoformat()} 00:00:00")
    args.append("HEAD")
    return int(_run_git(*args).strip() or 0)


def scan_numstat(*, since: date, pathspec: list[str] | None = None) -> dict:
    """扫一个时间窗，返回提交数与增删行数。

    **一次 git 调用同时得到两个数**：用 `--pretty=tformat:<marker>` 让每个提交
    先输出一行标记，numstat 行跟在后面。数标记 = 提交数，累加数字行 = 行数。
    这比"调一次 rev-list 数提交 + 调一次 log 数行数"少一次 subprocess
    （实测单次约 180ms，见 docs/14 §6.2）。

    不加 `--no-merges`：实测合并提交在默认 `--numstat` 下不产生 diff 行，
    对行数无影响；而提交数因此与 `git rev-list --count` 口径一致。

    二进制文件在 numstat 里是 `-\\t-\\t路径`，必须跳过，否则 `int()` 抛异常。
    """
    args = [
        "log",
        f"--since={since.isoformat()} 00:00:00",
        f"--pretty=tformat:{_COMMIT_MARKER}",
        "--numstat",
    ]
    if pathspec:
        args += ["--", *pathspec]

    commits = 0
    added = 0
    deleted = 0
    binary_files = 0

    for line in _run_git(*args).splitlines():
        if line.startswith(_COMMIT_MARKER):
            commits += 1
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        left, right, _path = parts
        if left == "-" or right == "-":
            binary_files += 1
            continue
        added += int(left)
        deleted += int(right)

    return {
        "commits": commits,
        "added": added,
        "deleted": deleted,
        "net": added - deleted,
        "binary_files": binary_files,
    }


def code_stats(today: date | None = None) -> dict:
    """仪表盘「代码量」与「Git 提交（本月）」两张卡的数据。

    返回结构对应前端 `types/portal.ts` 的 `DashboardStats.code_lines` / `git_commits`。
    """
    start = month_start(today)

    # 行数只算源码后缀；提交数要含**全部**提交（包括只改文档的那些），
    # 所以这里发两次调用：一次全量取提交数，一次限定后缀取行数。
    all_changes = scan_numstat(since=start)
    source_changes = scan_numstat(
        since=start,
        pathspec=[f"*{s}" for s in SOURCE_SUFFIXES] + list(EXCLUDED_PATHSPECS),
    )

    return {
        "code_lines": {
            "period": "month",
            "month_start": start.isoformat(),
            "added": source_changes["added"],
            "deleted": source_changes["deleted"],
            "net": source_changes["net"],
            "binary_files": source_changes["binary_files"],
        },
        "git_commits": {
            "month": all_changes["commits"],
            "total": count_commits(),
        },
    }
