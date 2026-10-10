"""Shell 脚本（dev-start.sh / dev-stop.sh）的语法与约定检查。

对应文档：docs/15_开发启动脚本方案.md「§6.2 `shell_script_cases.py`：shell 语法与约定」。

**为什么需要它**

Win11 与 Ubuntu 各有一份启动脚本，但开发这个项目时通常在 Windows 上，
改了 `.sh` 之后如果无法本地验证，一个括号错要等到 Ubuntu 上才发现。

本文件做两件事：

  1. **`bash -n`**（真语法检查）——找得到 bash 就**必须**通过；
  2. **约定检查**——几条从实际 bug 里来的硬规则（见下）。

**教训：不要手写 shell 结构检查器。**

第一版尝试用 Python 数括号、配对 `if/fi`，结果 **8 条里 7 条是误报**：

  - heredoc 里的 Python 片段（`socket.socket()`）把括号计数搞乱；
  - 单引号里的 sed 表达式 `'s/^# \\{0,1\\}//'` 被当成花括号；
  - `for x in ...; do` 的 `do` 在行尾，`^\\s*do\\b` 匹配不到；
  - `if` 出现在 `elif`、`[[ ... ]]` 里被重复计数。

**误报比没有检查更糟**——它会训练人忽略警告。而 `bash -n` 是 GNU 官方的
解析器，几十年的边界情况都处理过了。所以这里直接用它：

  - **Git for Windows 自带 bash**（`C:\\Program Files\\Git\\bin\\bash.exe`），
    Windows 上也能跑，不必依赖 WSL（WSL 未装发行版时 `bash.exe` 只是个转发器，
    会报 `execvpe(/bin/bash) failed`——这个坑也踩过）；
  - 找不到 bash 时才退化为"跳过"，并**明确打印 SKIP**，不假装检查过了。

跑法：

    conda activate desheng
    cd backend
    python tests/shell_script_cases.py
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ("dev-start.sh", "dev-stop.sh")

# Git for Windows 的 bash 常见位置。`shutil.which("bash")` 在 Windows 上
# **可能**指向 WSL 的转发器（`C:\Windows\system32\bash.exe`），那不是真 bash。
BASH_CANDIDATES = (
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
    r"C:\Program Files (x86)\Git\bin\bash.exe",
    "/bin/bash",
    "/usr/bin/bash",
)

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


def find_bash() -> str | None:
    """找一个**真正的** bash。

    ⚠️ 不直接用 `shutil.which("bash")`：在 Windows 上它可能返回
    `C:\\Windows\\system32\\bash.exe`，那是 WSL 的转发器；WSL 未装发行版时
    执行它会报 `execvpe(/bin/bash) failed: No such file or directory`，
    看起来像"脚本语法错"，实际是环境问题。所以要**验证它能真的跑起来**。
    """
    candidates = []
    for path in BASH_CANDIDATES:
        if Path(path).is_file():
            candidates.append(path)
    found = shutil.which("bash")
    if found:
        candidates.append(found)

    for path in candidates:
        try:
            proc = subprocess.run([path, "-c", "echo ok"], capture_output=True,
                                  text=True, timeout=15)
            if proc.returncode == 0 and "ok" in proc.stdout:
                return path
        except (OSError, subprocess.SubprocessError):
            continue
    return None


BASH = find_bash()


def load(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------- 语法

def test_scripts_exist():
    for name in SCRIPTS:
        check((REPO_ROOT / name).is_file(), f"{name} 存在")


def test_bash_syntax():
    """真语法检查。没有 bash 就明确跳过（不假装通过）。"""
    if not BASH:
        print("SKIP bash -n（本机找不到可用的真 bash；"
              "Windows 上装 Git for Windows 即自带）")
        return
    print(f"  （使用 {BASH}）")
    for name in SCRIPTS:
        proc = subprocess.run([BASH, "-n", name], cwd=REPO_ROOT,
                              capture_output=True, text=True, timeout=60)
        detail = proc.stderr.strip().splitlines()
        check(proc.returncode == 0,
              f"{name}: bash -n 通过" + (f" — {detail[-1]}" if detail else ""))


def test_shebang_and_strict_mode():
    for name in SCRIPTS:
        src = load(name)
        check(src.startswith("#!/usr/bin/env bash"), f"{name}: shebang 正确")
        check("set -euo pipefail" in src, f"{name}: 启用了 set -euo pipefail")


def test_help_output_is_complete():
    """⭐ `--help` 必须输出**整段**用法，不能只出标题一行。

    这条固化的是一类**静默失效**：`usage()` 用 awk 从脚本自身的注释块里
    抽取用法。第一版写成

        capture && /^# ?/ { sub(/^# ?/, ""); print }

    `sub()` 会**就地修改 `$0`**，于是这条记录流到后面的
    `capture && !/^#/ { exit }` 时已经不匹配 `^#`，**立刻退出**——
    结果是 `--help` 只打印"用法："一行就结束，**不报错、退出码仍是 0**。

    为什么值得一条用例：`--help` 是脚本的"说明书"，残缺时用户会以为
    参数就这么几个。而它不报错，所以只能靠断言"输出行数"来发现。
    """
    if not BASH:
        print("SKIP --help 检查（本机找不到可用的真 bash）")
        return
    for name in SCRIPTS:
        proc = subprocess.run([BASH, name, "--help"], cwd=REPO_ROOT,
                              capture_output=True, text=True, timeout=60,
                              encoding="utf-8")
        out = proc.stdout or ""
        lines = [ln for ln in out.splitlines() if ln.strip()]
        # 两个脚本的用法块都有 5 条以上的示例
        check(len(lines) >= 6,
              f"{name}: --help 输出至少 6 行（实际 {len(lines)} 行）"
              + (f" — 首行「{lines[0]}」" if lines else ""))
        check("./" + name in out,
              f"{name}: --help 里出现了自身的用法示例")


# ---------------------------------------------------------------- 约定（来自真实 bug）

def test_frontend_not_started_in_subshell():
    """⭐ 前端不能在子 shell 里启动。

    子 shell 里对 `CHILD_PIDS` 的追加**父 shell 收不到**，
    结果是收摊时收不到前端、Vite 变孤儿一直占着端口。
    这个错很隐蔽：功能看着正常，只有关闭时才发现端口没释放。
    """
    src = load("dev-start.sh")
    bad = re.search(r"\(\s*cd\s+\"\$FRONTEND\"\s*&&\s*start_child", src)
    check(bad is None, "dev-start.sh: 前端启动不在子 shell 里（否则收摊收不到）")


def test_trap_registered():
    """启动脚本必须注册 cleanup trap——否则 Ctrl+C 会留下孤儿进程。"""
    src = load("dev-start.sh")
    check(re.search(r"trap\s+'cleanup[^']*'\s+(INT|TERM)", src) is not None,
          "dev-start.sh: trap 绑定了 INT/TERM")
    check("cleanup()" in src, "dev-start.sh: 定义了 cleanup()")


def test_port_decided_once():
    """⭐ 端口只在启动脚本里决定一次，再注入给前后端。

    若两边各自决定，一旦不一致：页面能开但所有接口 404 —— 很难定位。
    """
    src = load("dev-start.sh")
    check("KM_API_TARGET" in src, "dev-start.sh: 向前端注入 KM_API_TARGET（代理目标）")
    check("KM_BACKEND_PORT" in src, "dev-start.sh: 向后端注入 KM_BACKEND_PORT")


def test_stop_uses_ports_not_pidfile():
    """用户要求：按端口找进程，不用 PID 文件（PID 会随反复拉起而变）。"""
    src = load("dev-stop.sh")
    check(".pid" not in src, "dev-stop.sh: 不依赖 PID 文件")
    check("sport = :" in src or "lport" in src, "dev-stop.sh: 按端口定位监听进程")


def test_port_tool_absence_is_not_silent():
    """⭐ 查不到"谁在监听端口"时必须**报错**，不能当作"端口空闲"。

    这条固化一个危险的反向失败：`dev-stop.sh` 靠 `ss`（或 `lsof`）找监听进程。
    若该工具不存在而代码只是 `ss ... 2>/dev/null`，它会输出空 →
    脚本把"查不到"读成"没有服务在跑" → `--status` 显示端口空闲、
    停止脚本报告"没有本项目的开发服务在运行"，**而服务其实还占着端口**。
    用户会据此以为已经停干净了。

    "工具缺失伪装成正常状态"比直接报错危险得多，所以：
      1. 必须有 `command -v` 探测 + 明确的报错分支；
      2. 必须有兜底工具（`lsof`）；
      3. 调用方必须**因该错误而中止**，不能继续打印"空闲"。
    """
    src = load("dev-stop.sh")
    check("command -v ss" in src, "dev-stop.sh: 探测了 `ss`")
    check("command -v lsof" in src, "dev-stop.sh: 有 `lsof` 兜底")
    check("找不到查询端口的工具" in src, "dev-stop.sh: 工具缺失时有明确报错文案")
    check("不要据此认为服务已停" in src, "dev-stop.sh: 报错里说明了风险（别当成已停）")
    # 调用方必须中止：show_status 失败要退出，而不是继续打印"空闲"
    check(re.search(r"show_status \|\| exit 1", src) is not None,
          "dev-stop.sh: show_status 失败会中止（不继续输出假的空闲状态）")


def test_status_flag_is_read_only():
    """--status 必须**只读**，不能走到结束流程。"""
    src = load("dev-stop.sh")
    check(re.search(r"if\s+\[\[\s+\$DO_STATUS\s+-eq\s+1\s+\]\][\s\S]{0,200}?exit 0", src)
          is not None,
          "dev-stop.sh: --status 分支以 exit 0 结束（不进入结束流程）")


def test_no_destructive_operations():
    """两个脚本都不得含破坏性数据库操作。"""
    for name in SCRIPTS:
        src = load(name)
        for forbidden in ("DROP TABLE", "DROP DATABASE", "TRUNCATE", "DELETE FROM"):
            check(forbidden not in src, f"{name}: 不含 `{forbidden}`")


def test_no_wholesale_kill():
    """停止脚本不得用"杀所有同名进程"这类粗暴手段。

    只按端口定位到具体 PID，再定向结束——避免误杀同机的其他 Node/Python。
    """
    src = load("dev-stop.sh")
    for brutal in ("pkill", "killall", "taskkill /IM", "Stop-Process -Name"):
        check(brutal not in src, f"dev-stop.sh: 不用 `{brutal}`（会误杀同名进程）")


def test_shared_selfcheck_is_used():
    """两个平台脚本都调用同一个 ensure_database.py（不在各自脚本里重写检查逻辑）。"""
    for name in SCRIPTS:
        if name == "dev-stop.sh":
            continue    # 停止脚本不需要跑自检
        check("ensure_database.py" in load(name),
              f"{name}: 调用共享的 ensure_database.py（检查逻辑只有一份）")


def test_utf8_for_python_output():
    """调 Python 时要设 UTF-8，否则中文输出在终端是乱码。

    实测踩到：`ensure_database.py` 的中文在 PowerShell 里显示成 `��������ӣ�`。
    Python 默认按控制台代码页（GBK）编码输出，而 shell 按 UTF-8 解码。
    """
    ps = (REPO_ROOT / "dev-start.ps1").read_text(encoding="utf-8")
    check("PYTHONIOENCODING" in ps, "dev-start.ps1: 调 Python 前设了 PYTHONIOENCODING")
    sh = load("dev-start.sh")
    check("PYTHONIOENCODING" in sh, "dev-start.sh: 调 Python 时设了 PYTHONIOENCODING")


def test_windows_uses_taskkill_tree():
    """Windows 侧必须用 taskkill /T 杀整棵进程树。

    vite 与 uvicorn 都会再 spawn 子进程，只杀父进程会留下孤儿、端口不释放。
    """
    ps = (REPO_ROOT / "dev-start.ps1").read_text(encoding="utf-8")
    stop_ps = (REPO_ROOT / "dev-stop.ps1").read_text(encoding="utf-8")
    check("/T" in ps and "taskkill" in ps, "dev-start.ps1: 用 taskkill /T 收整棵进程树")
    check("/T" in stop_ps and "taskkill" in stop_ps, "dev-stop.ps1: 用 taskkill /T 收整棵进程树")


def test_unix_uses_process_group():
    """Unix 侧必须用进程组（setsid + 负 PID），否则同样留孤儿。"""
    src = load("dev-start.sh")
    check("setsid" in src, "dev-start.sh: 用 setsid 起独立进程组")
    check(re.search(r"kill\s+-TERM\s+-\"\$pid\"", src) is not None,
          "dev-start.sh: 按进程组结束（负 PID）")
    stop = load("dev-stop.sh")
    check(re.search(r"kill\s+-TERM\s+-\"\$pid\"", stop) is not None,
          "dev-stop.sh: 按进程组结束（负 PID）")


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
