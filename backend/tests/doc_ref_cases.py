"""文档引用校验器（`check_doc_refs.py`）的用例。

对应文档：docs/15_开发启动脚本方案.md「§6.2 `shell_script_cases.py`：shell 语法与约定」。

**为什么需要它**（2026-10-08 的真实教训）

`check_doc_refs.py` 原本只校验脚本头部的 `对应文档：…「<章节>」` 格式，
**行内提及完全没被覆盖**。而重排章节编号（"把一节并进另一节"）时，
行内引用会**静默失效**——不报错、不影响构建，只是让读者去翻一个不存在的章节。

实测结果：前几轮重排 §11/§12 时留下了 **11 处**行内断链，**好几轮都没被发现**。
补上这个检查后立刻又抓出 2 处（`docs/14` 里一个已被合并掉的 §12 子节编号）。

**这个文件要钉住的第一件事是"量具本身不能太窄"**：

第一版行内正则要求写 `.md`（`docs/14_xxx.md §11.2`），而项目里最常见的
写法**不带扩展名**（`docs/14 §11.2`）。于是它报告"扫到 4 处、全部可解析"——
**把"没检查"伪装成了"检查通过"**。这比不做检查更危险：
它会给后续改动一个虚假的安全感。所以下面有一条用例专门断言
扫描量级（`>= 50`），防止正则被改窄后无声退化。

跑法：

    conda activate desheng
    cd backend
    python tests/doc_ref_cases.py
"""

import re
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

CHECKER = BACKEND_DIR / "scripts" / "check_doc_refs.py"

failures = []
checks = 0


def check(condition, label):
    global checks
    checks += 1
    if condition:
        print("PASS", label)
    else:
        print("FAIL", label)
        failures.append(label)


def run_checker() -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(CHECKER)],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# ---------------------------------------------------------------- 真实仓库

def test_checker_passes_on_current_repo():
    code, out = run_checker()
    check(code == 0, f"仓库当前状态校验通过（exit={code}）")
    if code != 0:
        for line in out.splitlines():
            if line.strip().startswith("-"):
                print("     ", line.strip())


def test_inline_scan_is_not_silently_narrow():
    """⭐ 行内引用扫描量必须达到量级——防止正则被改窄后"假通过"。

    这条是本次最重要的固化：第一版正则要求 `.md`，只扫到 4 处却报告"全部可解析"。
    真实量级是 **90+**（2026-10-08 实测 94 处）。
    若将来有人"简化"正则，扫描量会骤降——本用例会立刻失败。
    """
    _, out = run_checker()
    m = re.search(r"扫描到 (\d+) 处行内", out)
    check(m is not None, "校验器报告了行内引用扫描量")
    if m:
        n = int(m.group(1))
        check(n >= 50, f"行内引用扫描量 >= 50（实际 {n}）——量具没有变窄")


def test_inline_regex_handles_both_forms():
    """行内引用**带不带 `.md`** 都要能匹配。

    本项目最常见的写法是 `docs/14 §11.2`（无扩展名），
    而带扩展名的 `docs/14_xxx.md §2.1` 也存在。两种都必须在量具覆盖内。
    """
    sys.path.insert(0, str(BACKEND_DIR / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_doc_refs", CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    cases = [
        "见 docs/14 §11.2 的说明",
        "见（docs/14 §11.1）",
        "见 `docs/14 §12.3` 的教训",
        "对应文档：docs/15_开发启动脚本方案.md「§6」",
        "见 docs/14_主页仪表盘与待做事项开发方案.md §2.1",
    ]
    for text in cases:
        m = mod.INLINE_REF_RE.search(text)
        check(m is not None, f"能匹配: {text[:45]}")

    # 编号要正确捕获
    m = mod.INLINE_REF_RE.search("见 docs/14 §11.2 的说明")
    check(m and m.group(1) == "14" and m.group(2) == "11.2",
          "捕获到正确的文档号与章节号（14 / 11.2）")


def test_section_numbers_are_extracted():
    """能从标题里抽出编号（`### 11.2 极速录入` → `11.2`）。"""
    sys.path.insert(0, str(BACKEND_DIR / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_doc_refs2", CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    numbers = mod.section_numbers_of(REPO_ROOT / "docs/14_主页仪表盘与待做事项开发方案.md")
    for expected in ("1.1", "2.4", "11.1", "11.3", "12.3"):
        check(expected in numbers, f"docs/14 抽出编号 {expected}")


def test_not_a_pure_number_substring_match():
    """⭐ 校验必须比对**编号**，不能退化成"字符串在正文里出现过"。

    这个区别很关键：一个形如 `§12.5` 的引用里含 `12.5` 这样的子串，
    而对正文做子串搜索时，`12.5` 可能出现在**任何地方**（日期、版本号、行号），
    于是断链会被漏掉。本次抓到的那两处正是这种情形——
    必须判"没有编号为 12.5 的**标题**"，而不是"正文里没有这几个字符"。

    ⚠️ 本函数的文档字符串里**刻意不写出"文档号 + 节号"的完整形式**：
    那样会被校验器当成真引用而报错——**已实测踩到，而且踩了两次**：
    第一次是把断链原文照抄进说明，第二次是写"刻意不写出完整形式"时
    又把它复述了一遍。这是"说明文字被当成数据"的极佳例证
    （`check_doc_refs.py` 的注释里记着同一类错误）。
    """
    sys.path.insert(0, str(BACKEND_DIR / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_doc_refs3", CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    numbers = mod.section_numbers_of(REPO_ROOT / "docs/14_主页仪表盘与待做事项开发方案.md")
    check("12.5" not in numbers, "docs/14 确实没有编号 12.5 的节（断链会被判出）")
    # 正向对照：真实存在的编号必须能抽出来，否则上一条会因为"什么都抽不到"而假通过
    check("12.3" in numbers, "同一份文档里真实存在的 12.3 能抽出（对照）")


def test_archived_docs_are_excluded():
    """`已归档/` 必须排除。

    归档材料引用的是**历史编号**，按 `已归档/0_README.md` 的映射查找。
    拿现在的结构去校验它必然误报（`docs/0_README.md` 规则 4 说明了这条边界）。
    """
    src = CHECKER.read_text(encoding="utf-8")
    check("已归档" in src, "校验器排除了 `已归档/`")


def main():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
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
