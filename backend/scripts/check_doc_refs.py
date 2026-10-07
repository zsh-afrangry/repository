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
