"""校验 `对应文档：` 引用的可解析性。

规则（AGENTS.md 2026-10-06 立）：每个测试/脚本头部写一行
`对应文档：docs/<file>「<section>」`，且该文档里必须真有这个章节。

本脚本做三件事：
  1. 扫描 backend/ 与 frontend/ 下的脚本/测试，抽出引用行；
  2. 检查被引用的**文档文件**是否存在；
  3. 检查被引用的**章节名**是否在该文档里出现（按标题行匹配）。

用法：
    python backend/scripts/check_doc_refs.py
退出码 0 = 全部可解析；1 = 有断链。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# 扫描范围：只看脚本/测试，不看应用代码（应用代码的注释引用不必这么严格，
# 但它们的引用也会被顺带检查，因为同一条规则更省心）。
SCAN_DIRS = [REPO_ROOT / "backend", REPO_ROOT / "frontend" / "tests", REPO_ROOT / "scripts"]

# 仓库根目录下的启动脚本也要检查（2026-10-08 新增）。
# ⚠️ 只列具体文件，不对整个根目录 rglob——那里有 node_modules 级别的体量
# 与 `已归档/` 等历史材料，全扫既慢又会翻出历史引用。
SCAN_FILES = [
    REPO_ROOT / "dev-start.ps1",
    REPO_ROOT / "dev-stop.ps1",
    REPO_ROOT / "dev-start.sh",
    REPO_ROOT / "dev-stop.sh",
]

SUFFIXES = {".py", ".cjs", ".mjs", ".sh", ".cmd", ".ps1", ".bat"}

# 一条引用形如：<标记>：docs/<文档>.md「<章节>」。
# ⚠️ 正则刻意要求引用**位于注释或文档字符串里、且独占一行的开头**，
# 否则会把本文件里"举例说明格式"的那行也当成真引用（实测踩过，
# 与 docs/14 §V3 记录的是同一类错误：把说明文字当成数据）。
REF_RE = re.compile(r"^\s*(?:#|//|\*|/\*)?\s*对应文档：\s*(docs/[^\s「]+?\.(?:md|txt))\s*「([^」]+)」",
                    re.MULTILINE)

OK = "[OK]"
BAD = "[!!]"


def iter_script_files():
    for base in SCAN_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in SUFFIXES:
                continue
            if "__pycache__" in path.parts or "node_modules" in path.parts:
                continue
            yield path
    for path in SCAN_FILES:
        if path.is_file():
            yield path


def headings_of(doc: Path) -> list[str]:
    """返回文档里所有标题行的文本（去掉 # 与空白）。"""
    try:
        text = doc.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            out.append(stripped.lstrip("#").strip())
    return out


def section_numbers_of(doc: Path) -> set[str]:
    """返回文档里所有**编号型**标题的编号集合（如 {"11.1", "11.2"}）。

    ⚠️ 为什么需要它（2026-10-08 的真实教训）：
    行内引用常写成 `docs/14 §11.2` 这种**只有编号、没有标题文字**的形式。
    只比对标题文字的话，**编号写错了也发现不了**——
    而 §11 这类编号会在"把某节内容并进另一节"时整体位移，
    正是最容易写错的地方。

    本文件原先只校验脚本头部的 `对应文档：…「<章节>」`，
    行内提及完全没被覆盖。结果 2026-10-08 发现 **11 处**行内引用是断链，
    全是前几轮重排 §11 时留下的（`docs/14 §11.1` 等指向了已不存在的节）。
    """
    numbers: set[str] = set()
    for line in doc.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^#{2,4}\s+(\d+(?:\.\d+)*)[.\s、]", line.strip())
        if m:
            numbers.add(m.group(1))
    return numbers


# 行内引用：形如 `docs/14 §11.2`、`docs/14_xxx.md` §2.1、`（docs/14 §11.1）`。
#
# ⚠️ **`.md` 是可选的**——本项目里最常见的写法恰恰**不带**扩展名
# （`docs/14 §11.2`）。第一版正则要求 `.md`，于是"扫到 4 处、全部可解析"，
# 而实际有几十处：**量具太窄会把"没检查"伪装成"检查通过"**，
# 这比不做检查更危险。改完后立刻抓出 11 处真实断链。
INLINE_REF_RE = re.compile(
    r"docs/(\d+)(?:_[^\s§）)\]]*)?(?:\.md)?[^\n§]{0,12}?§\s*(\d+(?:\.\d+)*)"
)


def check_inline_refs() -> tuple[int, list[str]]:
    """校验行内引用 `docs/N §X.Y` 指向的章节**真实存在**。

    **为什么单独做这一轮**（2026-10-08）：上一轮只覆盖了脚本头部的
    `对应文档：…「<章节>」`，而行内提及（注释里、文档正文里）完全没管。
    结果是 11 处断链在**好几轮里都没被发现**——它们全是"把某节内容并进
    另一节后编号整体位移"造成的，而编号位移**不会报错、不会影响构建**，
    只是让读者去翻一个不存在的章节。

    范围刻意**只查 .md 与源码注释**，不含 `已归档/`：
    归档材料引用的是历史编号，按 `已归档/0_README.md` 的映射查找，
    拿现在的结构去校验它必然误报（这条边界在 `docs/0_README.md` 规则 4 有说明）。
    """
    problems: list[str] = []
    checked = 0
    doc_numbers: dict[str, set[str] | None] = {}

    targets: list[Path] = []
    for base in (REPO_ROOT / "docs", REPO_ROOT / "backend", REPO_ROOT / "frontend" / "src",
                 REPO_ROOT / "frontend" / "tests"):
        if base.exists():
            targets.extend(p for p in base.rglob("*") if p.is_file()
                           and p.suffix in {".md", ".py", ".ts", ".vue", ".cjs", ".txt"})
    for extra in (REPO_ROOT / "AGENTS.md", REPO_ROOT / "CLAUDE.md", REPO_ROOT / "todolist.txt"):
        if extra.is_file():
            targets.append(extra)

    # 文档编号 -> 真实文件（docs/14 → 14_xxx.md）
    doc_files: dict[str, Path] = {}
    for p in (REPO_ROOT / "docs").glob("*.md"):
        m = re.match(r"^(\d+)_", p.name)
        if m:
            doc_files[m.group(1)] = p

    for path in targets:
        if "已归档" in path.parts or "node_modules" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in INLINE_REF_RE.finditer(text):
            doc_num, section = m.group(1), m.group(2)
            doc_path = doc_files.get(doc_num)
            if doc_path is None:
                continue          # 不是本目录编号文档（可能是 docs/4 这类已归档）
            checked += 1
            key = str(doc_path)
            if key not in doc_numbers:
                doc_numbers[key] = section_numbers_of(doc_path)
            numbers = doc_numbers[key] or set()
            if section not in numbers:
                rel = path.relative_to(REPO_ROOT).as_posix()
                line_no = text[:m.start()].count("\n") + 1
                problems.append(
                    f"{rel}:{line_no}: docs/{doc_num} §{section} 不存在"
                    f"（该文档有 {len(numbers)} 个编号节）"
                )
    return checked, problems


def main() -> int:
    problems: list[str] = []
    checked = 0
    doc_cache: dict[Path, list[str]] = {}

    for path in sorted(iter_script_files()):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = REF_RE.search(text)
        if not match:
            continue
        checked += 1
        rel = path.relative_to(REPO_ROOT).as_posix()
        doc_rel, section_blob = match.group(1), match.group(2)

        doc_path = REPO_ROOT / doc_rel
        if not doc_path.exists():
            problems.append(f"{rel}: 文档不存在 -> {doc_rel}")
            continue

        if doc_path not in doc_cache:
            doc_cache[doc_path] = headings_of(doc_path)
        headings = doc_cache[doc_path]

        # 章节串可能形如 "§7 相关脚本与测试 / §10 验收"，逐段验证
        for chunk in section_blob.split("/"):
            chunk = chunk.strip()
            if not chunk:
                continue
            # 去掉开头的 §x / §x.y 编号，取标题文字
            title = re.sub(r"^§?\s*[\d.]+(?:\.\d+)*\s*", "", chunk).strip()
            title = title.strip("「」")
            if not title:
                # 只给了编号（如 §5.5），退化为"编号是否在文档里出现过"
                num = re.sub(r"^§\s*", "", chunk).strip()
                body = doc_path.read_text(encoding="utf-8", errors="replace")
                if num and num not in body:
                    problems.append(f"{rel}: 章节编号 {chunk} 在 {doc_rel} 里找不到")
                continue
            # 标题匹配：允许标题里带额外后缀（如「§5.5 表结构管理（用户第 2 条，采纳）」）
            if not any(title in h for h in headings):
                problems.append(f"{rel}: 章节「{title}」在 {doc_rel} 里找不到")

    print(f"扫描到 {checked} 个带引用行的脚本")

    # ---- 第二轮：行内 `docs/N §X.Y` 引用（2026-10-08 新增）----
    inline_checked, inline_problems = check_inline_refs()
    problems.extend(inline_problems)
    print(f"扫描到 {inline_checked} 处行内 `docs/N §X.Y` 引用")
    print()
    if problems:
        print(f"{BAD} {len(problems)} 处引用无法解析：")
        for p in problems:
            print("   -", p)
        return 1
    print(f"{OK} 全部引用可解析")
    return 0


if __name__ == "__main__":
    sys.exit(main())
