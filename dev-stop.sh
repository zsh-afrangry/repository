#!/usr/bin/env bash
#
# KnowledgeMap 开发服务停止 / 状态查看（Ubuntu 22.04）。
#
# 对应文档：docs/15_开发启动脚本方案.md「§4 结束方式（决策 3）」/「§4.5 不杀"看起来不是本项目"的进程」。
#
# **这是"备选项"，不是日常主线。** 正常结束开发用 dev-start.sh 那个终端的
# Ctrl+C 就够（它会把前后端一起干净收掉）。本脚本用于两种情况：
#
#     1. 终端窗口被误关 / 进程残留 —— 这时 Ctrl+C 已经没机会按了；
#     2. 想知道"现在到底有什么在跑" —— 用 --status，它**只读**。
#
# 用户 2026-10-08 明确要求：**专门杀端口，不用 PID 文件**。
# 理由很实际——PID 会随着进程反复拉起而变个不停，基于 PID 的记录很快就会过期，
# 过期后可能杀到无关进程。端口是这个项目里更稳定的"身份"。
#
# 用法：
#     ./dev-stop.sh --status               # 只查看，不结束任何进程（建议先跑）
#     ./dev-stop.sh                        # 结束 3000 / 8010 上的服务
#     ./dev-stop.sh --backend-port 8011    # 换过端口时
#     ./dev-stop.sh --force                # 连"看起来不是本项目"的占用者也结束
#     ./dev-stop.sh --help
#
# ⚠️ 与 Stop-KnowledgeMap.sh 的区别：那个停的是**生产/移动访问**模式
# （Tailscale 转发 + systemd 用户服务）。本脚本只管开发模式的 Vite + uvicorn。

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${KM_PYTHON:-$HOME/miniconda3/envs/desheng/bin/python}"

BACKEND_PORT=8010
FRONTEND_PORT=3000
DO_STATUS=0
FORCE=0

C_RESET=$'\033[0m'; C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'
C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_DIM=$'\033[2m'

step() { printf '\n%s==> %s%s\n' "$C_CYAN" "$1" "$C_RESET"; }
ok()   { printf '  %s[OK]%s %s\n' "$C_GREEN" "$C_RESET" "$1"; }
warn() { printf '  %s[--]%s %s\n' "$C_YELLOW" "$C_RESET" "$1"; }
err()  { printf '  %s[!!]%s %s\n' "$C_RED" "$C_RESET" "$1"; }
dim()  { printf '  %s%s%s\n' "$C_DIM" "$1" "$C_RESET"; }

usage() {
    # 从 "用法：" 那行起，到第一个空注释行或非注释行为止。
    #
    # ⚠️ **不要用 `sub()` 去 `$0` 上的前缀**：`sub()` 就地修改 `$0`，
    # 后面的 `!/^#/ { exit }` 会把这条已改过的记录当成非注释行而提前退出——
    # 表现是 `--help` 只打印一行。改成复制到 `line` 再处理。
    # （2026-10-11 在 `dev-start.sh` 实测踩到，这里同步修。）
    awk '
        /^# 用法：/ { capture = 1 }
        !capture    { next }
        /^#$/       { exit }
        !/^#/       { exit }
        {
            line = $0
            sub(/^# ?/, "", line)
            print line
        }
    ' "${BASH_SOURCE[0]}"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --status)         DO_STATUS=1; shift ;;
        --force)          FORCE=1; shift ;;
        --backend-port)   BACKEND_PORT="$2"; shift 2 ;;
        --frontend-port)  FRONTEND_PORT="$2"; shift 2 ;;
        -h|--help)        usage ;;
        *) err "未知参数：$1"; dim '用 --help 看用法。'; exit 1 ;;
    esac
done

PORTS=("$BACKEND_PORT" "$FRONTEND_PORT")

# 用哪个工具查"谁在监听端口"。
#
# ⚠️ 必须**启动时探测一次并明确报错**，不能让 `ss` 缺失时静默退化。
# 原来的写法直接 `ss ... 2>/dev/null`：`ss` 不存在时它什么都不输出，
# 于是脚本把"查不到"当成"没有进程在跑"——`--status` 会显示端口空闲、
# `dev-stop.sh` 会报告"没有本项目的开发服务在运行"，**而服务其实好好地占着端口**。
# 这种"工具缺失伪装成正常状态"的失败最危险：用户会以为已经停干净了。
# （2026-10-11 在 Windows 的 Git Bash 上跑 `--status` 时发现该路径无输出，
#   进而意识到 Ubuntu 上若 iproute2 缺失就是同一个静默失败。）
PORT_TOOL=""
if command -v ss >/dev/null 2>&1; then
    PORT_TOOL="ss"
elif command -v lsof >/dev/null 2>&1; then
    PORT_TOOL="lsof"      # 兜底：ss 不在时用 lsof（部分精简系统只装了这个）
fi

listener_pid() {
    # 打印监听某端口的 PID；没有则什么都不打印。
    case "$PORT_TOOL" in
        ss)
            # `ss -lptnH` 是 iproute2 自带（Ubuntu 22.04 默认）。
            ss -lptnH "sport = :$1" 2>/dev/null |
                grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2
            ;;
        lsof)
            lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null | head -1
            ;;
        *)
            return 1      # 没有可用工具——由调用方报错，不要假装"端口空闲"
            ;;
    esac
}

pid_cmdline() {
    # 读 /proc/<pid>/cmdline（NUL 分隔）并转成可读字符串。
    # ⚠️ 进程可能已经退出，读不到就返回空——调用方必须容忍这一点。
    [[ -r "/proc/$1/cmdline" ]] || return 0
    tr '\0' ' ' < "/proc/$1/cmdline" 2>/dev/null || true
}

pid_name() {
    [[ -r "/proc/$1/comm" ]] && cat "/proc/$1/comm" 2>/dev/null || echo '(已退出)'
}

port_free() {
    "$PYTHON" - "$1" <<'PY' 2>/dev/null
import socket, sys
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("127.0.0.1", int(sys.argv[1])))
except OSError:
    sys.exit(1)
finally:
    s.close()
PY
}

is_ours() {
    # 判断这个 PID 是不是本项目启动的开发进程。
    #
    # ⚠️ 只看命令行，因为 dev-start.sh 启动前端时用的是**相对路径**
    # （node_modules/vite/bin/vite.js），命令行里没有项目根目录。
    # 一开始只匹配项目路径，结果把自己刚启的前端认成别人的（实测踩到）。
    local cmd="$1"
    [[ -n "$cmd" ]] || return 1
    [[ "$cmd" == *"$ROOT"* ]] && return 0
    [[ "$cmd" == *"main.py"* ]] && return 0
    [[ "$cmd" == *"vite"* ]] && return 0
    return 1
}

show_status() {
    step '当前状态'
    local any=0
    for port in "${PORTS[@]}"; do
        # ⚠️ `listener_pid` 返回 1 = 没有可用的端口查询工具。
        # 这时**必须报错退出**，不能继续当作"端口空闲"——
        # 否则用户会以为服务已经停了，而它其实还在跑。
        local pid
        if ! pid="$(listener_pid "$port")"; then
            err "找不到查询端口的工具（需要 \`ss\` 或 \`lsof\`）。"
            dim '  Ubuntu 上通常自带 ss（iproute2）；精简镜像可 apt install iproute2'
            dim '  现在无法判断端口状态，不要据此认为服务已停。'
            return 1
        fi
        if [[ -z "$pid" ]]; then
            dim "端口 $port ：空闲"
            continue
        fi
        any=1
        local cmd; cmd="$(pid_cmdline "$pid")"
        if ! kill -0 "$pid" 2>/dev/null; then
            dim "端口 $port ：进程正在退出（PID $pid）"
            continue
        fi
        local tag='**非本项目**'
        is_ours "$cmd" && tag='本项目'
        printf '  端口 %s ：PID %s  %s  [%s]\n' "$port" "$pid" "$(pid_name "$pid")" "$tag"
        [[ -n "$cmd" ]] && dim "               $(printf '%.110s' "$cmd")"
    done

    # 数据库服务只报告，不碰（它们是系统服务，不属于本脚本管）。
    printf '\n'
    if systemctl --user list-unit-files 2>/dev/null | grep -q '^knowledgemap-mongodb'; then
        local mstat; mstat="$(systemctl --user is-active knowledgemap-mongodb 2>/dev/null || true)"
        printf '  MongoDB 用户服务：%s\n' "${mstat:-unknown}"
    fi
    if command -v systemctl >/dev/null 2>&1; then
        local mys; mys="$(systemctl is-active mysql 2>/dev/null || true)"
        printf '  MySQL 服务：%s\n' "${mys:-unknown}"
    fi

    [[ $any -eq 0 ]] && { printf '\n'; ok '没有本项目的开发服务在运行。'; }
    return 0
}

# ---------------------------------------------------------------- 主流程

if [[ $DO_STATUS -eq 1 ]]; then
    show_status || exit 1
    exit 0
fi

printf 'KnowledgeMap 开发服务停止\n'
# `show_status` 在"查不到端口工具"时返回非零——这时**必须停**，
# 继续往下走只会打印一堆"端口空闲"的假象。
show_status || exit 1

step '结束进程'
killed=0; skipped=0

for port in "${PORTS[@]}"; do
    if ! pid="$(listener_pid "$port")"; then
        err "找不到查询端口的工具（需要 \`ss\` 或 \`lsof\`），无法继续。"
        exit 1
    fi
    [[ -n "$pid" ]] || continue

    # 进程正在退出（TCP 连接还没被回收）：不是"别人的进程"，也不是要杀的目标。
    # 不单独处理的话会打印"已跳过：不属于本项目"这种**误导性警告**
    # （实测踩到：dev-start 的 cleanup 已在关前端，dev-stop 随后看到残留连接）。
    if ! kill -0 "$pid" 2>/dev/null; then
        dim "端口 $port 上的进程正在退出，无需处理"
        continue
    fi

    cmd="$(pid_cmdline "$pid")"
    if ! is_ours "$cmd" && [[ $FORCE -eq 0 ]]; then
        # ⚠️ 默认不杀"看起来不是本项目"的进程。命令行不含项目特征，
        # 说明它多半是别的程序——杀掉它是事故，不是清理。
        warn "端口 $port 上的 PID $pid（$(pid_name "$pid")）命令行不含本项目特征，已跳过"
        dim '       确认要结束它请加 --force'
        skipped=$((skipped + 1))
        continue
    fi

    dim "结束端口 $port 上的 PID $pid（$(pid_name "$pid")）"
    # 负号 = 整个进程组。dev-start.sh 用 setsid 起子进程，
    # 所以这里能一次收掉 vite/uvicorn 再 spawn 的子进程，不留孤儿。
    kill -TERM -"$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
    killed=$((killed + 1))
done

sleep 1     # 给它们一点时间优雅退出

# 复核：还活着的强杀
for port in "${PORTS[@]}"; do
    pid="$(listener_pid "$port")"
    [[ -n "$pid" ]] || continue
    kill -0 "$pid" 2>/dev/null || continue
    dim "强制结束 PID $pid"
    kill -KILL -"$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
done

sleep 1
printf '\n'
[[ $killed -gt 0 ]] && ok "已结束 $killed 个进程"
[[ $skipped -gt 0 ]] && warn "跳过 $skipped 个（不属于本项目；如确需结束请加 --force）"

step '复核'
for port in "${PORTS[@]}"; do
    if port_free "$port"; then
        ok "端口 $port 已释放"
    else
        warn "端口 $port 仍被占用"
    fi
done
