"""代码量口径探测：验证「本月源码行数」与「提交数」的计算方式。

对应文档：docs/14_主页仪表盘与待做事项开发方案.md「§4.2 代码量口径」。

**为什么需要这个脚本**
`dashboard` 的「代码量」卡按口径④实现（只算源码后缀、按月、取净变化）。
在把它写进 `crud/dashboard.py` 之前，需要先确认三件事，本脚本就是这三件事的证据：

1. 用 `--pretty=tformat:<marker>` 做提交分隔符，能否在**一次** `git log` 调用里
   同时数出「提交数」与「增删行数」——省掉一次 subprocess（docs/14 §6.2 提到的优化点）。
2. **合并提交**是否会让行数重复计数（默认 `git log --numstat` 对 merge 不产生 diff）。
3. **二进制文件**在 numstat 里的输出格式（`-\\t-\\t路径`），累加时必须跳过，否则抛异常。

**用法**
    python backend/scripts/code_volume_probe.py              # 口径④（正式口径）
    python backend/scripts/code_volume_probe.py --all        # 五种口径对比
    python backend/scripts/code_volume_probe.py --since 2026-09-01

只读操作：只跑 `git log`/`git rev-list`，不写任何文件、不改数据库。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

# Windows 控制台默认 GBK，输出 ✓ / ✗ 这类符号会抛 UnicodeEncodeError 并中断脚本。
# 后端服务同样跑在这个控制台上，所以这是**环境事实**而非脚本问题。
# 统一改成 ASCII 标记，避免脚本在 Windows 上"跑到一半崩"。
OK_MARK = "[OK]"
FAIL_MARK = "[!!]"

# 仓库根：本文件在 backend/scripts/ 下，向上三级即仓库根。
REPO_ROOT = Path(__file__).resolve().parents[2]

# 口径④：只算源码后缀。刻意**不含** .json —— 否则 package-lock.json 之类
# 锁文件的一次更新就能让「代码量」暴涨几千行，数字失去意义。
SOURCE_SUFFIXES = (".py", ".ts", ".vue", ".css", ".sh", ".js")

# ⚠️ 只按后缀过滤**不够**：`frontend_example/` 里有 20 个第三方示例文件
# （app.js / marked.min.js / tex-mml-chtml.js / styles.css …）**全都匹配后缀**，
# 所以正式口径必须同时排除它们，否则 vendored 代码会被算成自己的产出。
# 实测（全量历史）：不排除 25897 行 vs 排除 18942 行，**相差 6955 行**。
# ⚠️ 这两个常量必须与 `app/git_stats.py` 的 `SOURCE_SUFFIXES` / `EXCLUDED_PATHSPECS`
# 保持一致——本脚本是"口径的说明与验证工具"，与实现给出不同数字就失去意义了。
EXCLUDED_PATHSPECS = (
    ":(exclude)frontend_example/**",
    ":(exclude)已归档/**",
)

# 提交分隔符。选一个不可能出现在 numstat 行首的字符串。
_COMMIT_MARKER = "__KM_COMMIT__"

# 口径②⑤用的排除路径。
_EXCLUDE_VENDOR = ":(exclude)frontend_example/**"
_EXCLUDE_DOCS = ("docs/**", "已归档/**")


def _run_git(*args: str) -> str:
    """跑一条 git 命令，返回 stdout。失败时抛 RuntimeError（便于区分于 git 自身的退出码）。"""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"git {' '.join(args)} 执行失败: {error}") from error
    return result.stdout


def scan_month(since: str, pathspec: list[str] | None = None) -> dict:
    """扫一个时间窗，返回 {commits, added, deleted, binary_files}.

    **一次 git 调用同时得到提交数与行数**：用 `--pretty=tformat:<marker>` 让每个提交
    输出一行标记，numstat 行跟在后面。数标记 = 提交数，累加数字行 = 行数。

    不加 `--no-merges`：实测合并提交在默认 `--numstat` 下不产生 diff 行，
    对行数无影响；而提交数要跟既有 `git rev-list --count` 的口径一致（它含 merge）。
    """
    args = ["log", f"--since={since} 00:00:00", f"--pretty=tformat:{_COMMIT_MARKER}", "--numstat"]
    if pathspec:
        args += ["--", *pathspec]

    stdout = _run_git(*args)

    commits = 0
    added = 0
    deleted = 0
    binary_files = 0

    for line in stdout.splitlines():
        if line.startswith(_COMMIT_MARKER):
            commits += 1
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        left, right, _path = parts
        if left == "-" or right == "-":
            # 二进制文件：numstat 用 "-" 表示不可数。必须跳过，否则 int() 抛异常。
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


def count_commits_via_rev_list(since: str) -> int:
    """既有实现的口径（`git rev-list --count`），用来交叉验证提交数是否一致。"""
    return int(_run_git("rev-list", "--count", f"--since={since} 00:00:00", "HEAD").strip() or 0)


def monthly_source_lines(since: str) -> dict:
    """口径④的正式实现：只算源码后缀，并排除 vendored / 归档目录。

    提交数要统计**全部**提交（含只改文档的），而行数只算源码，两者范围不同，
    所以这里发两次调用：一次全量取提交数，一次限定后缀取行数。
    """
    stats = scan_month(since)
    source_stats = scan_month(
        since,
        [f"*{suffix}" for suffix in SOURCE_SUFFIXES] + list(EXCLUDED_PATHSPECS),
    )
    return {
        "commits": stats["commits"],
        "added": source_stats["added"],
        "deleted": source_stats["deleted"],
        "net": source_stats["net"],
        "binary_files": source_stats["binary_files"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", default=date.today().replace(day=1).isoformat(),
                        help="起始日期 YYYY-MM-DD（默认本月 1 号）")
    parser.add_argument("--all", action="store_true", help="打印五种口径对比，而不只是口径④")
    args = parser.parse_args()

    since = args.since
    print(f"仓库根: {REPO_ROOT}")
    print(f"起始时间: {since} 00:00:00")
    print()

    started = time.perf_counter()

    if args.all:
        variants = [
            ("① 全部", None),
            ("② 排除 frontend_example", [".", _EXCLUDE_VENDOR]),
            ("③ 再排除 docs/ 与 已归档/", [".", _EXCLUDE_VENDOR, *[f":(exclude){p}" for p in _EXCLUDE_DOCS]]),
            ("④ 只算源码后缀（正式口径）",
             [f"*{s}" for s in SOURCE_SUFFIXES] + list(EXCLUDED_PATHSPECS)),
            ("⑤ 只算 backend + frontend/src", ["backend/**", "frontend/src/**"]),
        ]
        print(f"{'口径':<34}{'新增':>8}{'删除':>8}{'净':>8}{'二进制':>8}")
        print("-" * 66)
        for label, pathspec in variants:
            r = scan_month(since, pathspec)
            print(f"{label:<34}{r['added']:>8}{r['deleted']:>8}{r['net']:>8}{r['binary_files']:>8}")
        print()
        # 提交数校验：一次调用 vs rev-list
        r = scan_month(since)
        rl = count_commits_via_rev_list(since)
        print("提交数交叉验证：")
        print(f"  单次 git log 数标记 : {r['commits']}")
        print(f"  git rev-list --count: {rl}")
        print(f"  一致: {OK_MARK if r['commits'] == rl else FAIL_MARK + ' 需要改用 rev-list'}")
    else:
        result = monthly_source_lines(since)
        print("口径④（本月源码行数，净变化）：")
        print(f"  提交数（全部，含文档提交）: {result['commits']}")
        print(f"  新增行: {result['added']}")
        print(f"  删除行: {result['deleted']}")
        print(f"  净变化: {result['net']}")
        print(f"  跳过的二进制文件: {result['binary_files']}")
        rl = count_commits_via_rev_list(since)
        same = OK_MARK if result["commits"] == rl else FAIL_MARK
        print(f"  提交数交叉验证: 单次调用={result['commits']} rev-list={rl} {same}")

    elapsed = (time.perf_counter() - started) * 1000
    print()
    print(f"耗时: {elapsed:.0f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
