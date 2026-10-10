#!/usr/bin/env bash
#
# KnowledgeMap 开发环境一键启动（Ubuntu 22.04）。
#
# 对应文档：docs/15_开发启动脚本方案.md「§3.4 `ensure_database.py` 的边界」/「§5.2 启动流程（两个平台同构）」。
#
# 一条命令起后端 + 前端，Ctrl+C 一起停。
#
# 启动流程（每一步失败都明确停下并说明原因）：
#     1. 解析 Python 解释器
#     2. 检查 backend/.env（缺失只提示，不阻止）
#     3. 检查后端依赖（--check 时才查，默认跳过以加快启动）
#     4. 检查端口占用（被占用就报错并停，**不自动杀**）
#     5. 跑 ensure_database.py（建库 + 报告表/种子/Mongo）
#     6. 起后端，**等健康检查通过**才继续
#     7. 起前端（Vite）
#     8. 前台守候；任一进程退出或 Ctrl+C 就一起收摊
#
# 用法：
#     ./dev-start.sh                       # 起前后端
#     ./dev-start.sh --check               # 额外做类型检查与依赖检查
#     ./dev-start.sh --backend-port 8011   # 换端口（前端会一起跟着换）
#     ./dev-start.sh --no-frontend         # 只起后端
#     ./dev-start.sh --backend-entry main.py
#     ./dev-start.sh --help
#
# ## 端口由本脚本统一决定
#
# 这是本脚本最重要的设计：端口只在一个地方决定，然后注入给两个进程：
#
#     后端  <- KM_BACKEND_PORT   （main.py 读它）
#     前端  <- KM_API_TARGET     （vite.config.ts 读它，作为代理目标）
#
# 为什么必须这样：Vite 的代理发生在 **Node 进程内部**，不是浏览器里，
# 所以"前端读后端的端口"只能发生在 Vite 启动那一刻。若两边各自决定端口，
# 一旦不一致，页面能打开但所有接口 404 —— 那种故障很难定位。
#
# ## 为什么不自动杀占用端口的进程
#
# 被占用时报错并停，而不是替你杀掉。因为那个占用者可能是：
#     - 你上一次忘记关的开发服务（→ 用 dev-stop.sh）
#     - 另一个不相关的程序（→ 杀了就是事故）
# 脚本无法区分这两者，所以把判断权交回给你，并打印占用者的 PID 与进程名。
#
# ⚠️ 与 Start-KnowledgeMap.sh 的区别：那是**生产/移动访问**模式
# （Tailscale HTTPS + 鉴权 + 构建静态快照）。本脚本是**开发**模式
# （Vite dev server，热更新）。两者互不干扰，各用各的。

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# 默认解释器：docs/11 记录的 Ubuntu 环境。
PYTHON="${KM_PYTHON:-$HOME/miniconda3/envs/desheng/bin/python}"

BACKEND_PORT=8010
FRONTEND_PORT=3000
DO_CHECK=0
START_FRONTEND=1
BACKEND_ENTRY="main.py"
HEALTH_TIMEOUT=40

# ---------------------------------------------------------------- 输出

C_RESET=$'\033[0m'; C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'
C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_DIM=$'\033[2m'

step()  { printf '\n%s==> %s%s\n' "$C_CYAN" "$1" "$C_RESET"; }
ok()    { printf '  %s[OK]%s %s\n' "$C_GREEN" "$C_RESET" "$1"; }
warn()  { printf '  %s[--]%s %s\n' "$C_YELLOW" "$C_RESET" "$1"; }
err()   { printf '  %s[!!]%s %s\n' "$C_RED" "$C_RESET" "$1"; }
dim()   { printf '  %s%s%s\n' "$C_DIM" "$1" "$C_RESET"; }

usage() {
    # 打印文件顶部注释块作为帮助。
    # 从 "用法：" 那行起，到第一个空注释行或非注释行为止。
    #
    # ⚠️ 两个坑（2026-10-11 实测修掉，`--help` 当时只输出"用法："一行就没了）：
    #   1. **不能用 `sub()` 去掉 `# ` 前缀**——`sub()` 会**就地修改 `$0`**，
    #      于是同一条记录流到**后面的规则**时已经不是注释行了，
    #      下一条 `!/^#/ { exit }` 立刻命中并退出。用 `line = $0` 复制一份再处理。
    #   2. **先判断、后决定退出**：把"非注释行 → 退出"放在**末尾**，
    #      并且用原始 `$0` 判断，不要用被改过的值。
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

# ---------------------------------------------------------------- 参数

while [[ $# -gt 0 ]]; do
    case "$1" in
        --check)            DO_CHECK=1; shift ;;
        --no-frontend)      START_FRONTEND=0; shift ;;
        --backend-port)     BACKEND_PORT="$2"; shift 2 ;;
        --frontend-port)    FRONTEND_PORT="$2"; shift 2 ;;
        --backend-entry)    BACKEND_ENTRY="$2"; shift 2 ;;
        -h|--help)          usage ;;
        *) err "未知参数：$1"; dim "用 --help 看用法。"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------- 进程管理

# 子进程 PID 列表。收摊时按**反序**处理（先前端后后端）。
CHILD_PIDS=()
CHILD_LABELS=()

cleanup_done=0

cleanup() {
    # 幂等：Ctrl+C 与正常退出都可能走到这里。
    [[ $cleanup_done -eq 1 ]] && return
    cleanup_done=1

    printf '\n'
    step '收摊'
    # 反序：先前端后后端。反过来的话 Vite 会看到后端断开，
    # 在终端刷一屏 ECONNREFUSED，日志很脏。
    local i
    for (( i=${#CHILD_PIDS[@]}-1; i>=0; i-- )); do
        local pid="${CHILD_PIDS[$i]}"
        local label="${CHILD_LABELS[$i]}"
        if kill -0 "$pid" 2>/dev/null; then
            dim "停止 $label（PID $pid）"
            # 负号 = 整个进程组。子进程是用 setsid 起的（见下），
            # 所以这里能一次收掉 vite/uvicorn 再 spawn 的子进程。
            kill -TERM -"$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
        fi
    done

    # 给它们 3 秒优雅退出，然后强杀。
    sleep 3
    for pid in "${CHILD_PIDS[@]:-}"; do
        [[ -n "$pid" ]] || continue
        if kill -0 "$pid" 2>/dev/null; then
            kill -KILL -"$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
        fi
    done
    ok '已停止'
}

trap 'cleanup; exit 130' INT TERM
trap 'cleanup' EXIT

port_free() {
    # 用"能否真正绑定"判断——TIME_WAIT 状态的连接不算占用（docs/11 记过这个误报）。
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

port_owner() {
    # 打印占用某端口的进程信息（PID + 命令名），用于可读的报错。
    # `ss` 是 Ubuntu 22.04 的默认工具（iproute2 自带）。
    ss -lptnH "sport = :$1" 2>/dev/null |
        awk 'NR==1 { match($0, /pid=[0-9]+/); if (RSTART) print substr($0, RSTART+4, RLENGTH-4) }'
}

start_child() {
    # 用 setsid 起独立进程组：这样收摊时能 kill 整个组，
    # 不会留下 vite/uvicorn 的子进程孤儿（Windows 侧对应 taskkill /T）。
    local label="$1"; shift
    ok "启动 $label"
    setsid "$@" &
    local pid=$!
    CHILD_PIDS+=("$pid")
    CHILD_LABELS+=("$label")
    LAST_PID=$pid
}

wait_health() {
    local port="$1" deadline=$(( SECONDS + HEALTH_TIMEOUT ))
    local url="http://127.0.0.1:$port/api/health"
    while (( SECONDS < deadline )); do
        # 后端若已死，不必等满超时。
        if [[ -n "${BACKEND_PID:-}" ]] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
            err "后端进程已退出。请看上方日志。"
            return 1
        fi
        if "$PYTHON" - "$url" <<'PY' 2>/dev/null
import sys, urllib.request
try:
    with urllib.request.urlopen(sys.argv[1], timeout=2) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
PY
        then
            return 0
        fi
        sleep 0.5
    done
    err "后端未在 $HEALTH_TIMEOUT 秒内就绪。健康检查地址：$url"
    return 1
}

# ---------------------------------------------------------------- 主流程

printf 'KnowledgeMap 开发启动\n'
printf '  项目根目录：%s\n' "$ROOT"

# ---- 1. Python ----
step '检查 Python'
if [[ ! -x "$PYTHON" ]]; then
    err "找不到可执行的 Python：$PYTHON"
    dim '设置环境变量 KM_PYTHON 指向解释器绝对路径后重试。'
    exit 1
fi
ok "解释器：$PYTHON"

# ---- 2. .env ----
step '检查 backend/.env'
if [[ ! -f "$BACKEND/.env" ]]; then
    warn '缺少 backend/.env —— 将使用默认值（root:root@127.0.0.1:3306/knowledgemap）'
    dim '可复制 backend/.env.example 为 backend/.env 并填写密钥。'
else
    ok 'backend/.env 存在'
fi

# ---- 3. 依赖（仅 --check）----
if [[ $DO_CHECK -eq 1 ]]; then
    step '检查依赖（--check）'
    missing="$("$PYTHON" - <<'PY'
import importlib.util
need = ["fastapi", "uvicorn", "sqlalchemy", "pymysql", "dotenv", "pymongo"]
print(" ".join(n for n in need if importlib.util.find_spec(n) is None))
PY
)"
    if [[ -n "$missing" ]]; then
        err "后端缺少依赖：$missing"
        dim 'pip install -r backend/requirements.txt'
        exit 1
    fi
    ok '后端依赖齐全'

    if [[ $START_FRONTEND -eq 1 ]]; then
        if [[ ! -d "$FRONTEND/node_modules" ]]; then
            err '前端依赖未安装'
            dim 'cd frontend && npm ci'
            exit 1
        fi
        ok '前端依赖已安装'
        printf '  %s运行 vue-tsc 类型检查（可能需要十几秒）...%s\n' "$C_DIM" "$C_RESET"
        ( cd "$FRONTEND" && node node_modules/vue-tsc/bin/vue-tsc.js --noEmit )
        ok '类型检查通过'
    fi
fi

# ---- 4. 端口占用 ----
step '检查端口'
conflict=0
check_port() {
    local port="$1" what="$2"
    if port_free "$port"; then
        ok "$what端口 $port 空闲"
    else
        local owner; owner="$(port_owner "$port")"
        local desc='未知进程'
        [[ -n "$owner" ]] && desc="PID $owner"
        err "$what端口 $port 已被占用：$desc"
        conflict=1
    fi
}
check_port "$BACKEND_PORT" '后端'
[[ $START_FRONTEND -eq 1 ]] && check_port "$FRONTEND_PORT" '前端'

if [[ $conflict -eq 1 ]]; then
    printf '\n  %s本脚本不会自动结束占用者——因为它可能是别的程序。请二选一：%s\n' "$C_YELLOW" "$C_RESET"
    dim '  1) 如果是上次遗留的开发服务：  ./dev-stop.sh'
    dim '  2) 换个端口：                  ./dev-start.sh --backend-port 8011 --frontend-port 3001'
    exit 1
fi

# ---- 5. 环境自检（建库 / 报告表 / 报告 Mongo）----
step '环境自检（MySQL 数据库 / 表 / MongoDB）'
# 与 Windows 侧同理：确保 UTF-8，避免中文输出在看板上变成乱码。
PYTHONIOENCODING=utf-8 "$PYTHON" "$BACKEND/scripts/ensure_database.py" || {
    err '环境自检未通过，已停止启动。'
    exit 1
}

# ---- 6/7. 注入端口并启动 ----
# ⚠️ 端口只在这里决定一次。前后端同源，不可能不一致。
export KM_BACKEND_PORT="$BACKEND_PORT"
export KM_API_TARGET="http://127.0.0.1:$BACKEND_PORT"

ENTRY="$BACKEND_ENTRY"
[[ "$ENTRY" = /* ]] || ENTRY="$BACKEND/$BACKEND_ENTRY"
if [[ ! -f "$ENTRY" ]]; then
    err "后端入口不存在：$ENTRY"
    exit 1
fi

step "启动后端（端口 $BACKEND_PORT）"
start_child "后端(:$BACKEND_PORT)" "$PYTHON" "$ENTRY"
BACKEND_PID="$LAST_PID"

printf '  %s等待后端就绪...%s\n' "$C_DIM" "$C_RESET"
wait_health "$BACKEND_PORT" || exit 1
ok "后端就绪：http://127.0.0.1:$BACKEND_PORT/docs"

if [[ $START_FRONTEND -eq 1 ]]; then
    step "启动前端（端口 $FRONTEND_PORT，代理 → $KM_API_TARGET）"
    # ⚠️ 不要用子 shell `( cd ... && start_child ... )`：那样 CHILD_PIDS
    # 的追加发生在子 shell 里，父 shell 收不到 → **前端不会被收摊**。
    # 改成先 cd、启动、再 cd 回来。
    cd "$FRONTEND"
    start_child "前端(:$FRONTEND_PORT)" \
        node node_modules/vite/bin/vite.js --port "$FRONTEND_PORT" --host 127.0.0.1
    cd "$ROOT"
fi

# ---- 8. 前台守候 ----
printf '\n%s──────────────────────────────────────────────%s\n' "$C_DIM" "$C_RESET"
if [[ $START_FRONTEND -eq 1 ]]; then
    printf '  页面：  http://127.0.0.1:%s/\n' "$FRONTEND_PORT"
fi
printf '  接口：  http://127.0.0.1:%s/docs\n' "$BACKEND_PORT"
printf '  停止：  在本终端按 Ctrl+C（前后端会一起停）\n'
printf '%s──────────────────────────────────────────────%s\n\n' "$C_DIM" "$C_RESET"

# 守候：任一子进程退出就结束（例如后端崩了），不必让你盯着一个半死的会话。
while true; do
    sleep 0.7
    for pid in "${CHILD_PIDS[@]}"; do
        if ! kill -0 "$pid" 2>/dev/null; then
            warn "有子进程（PID $pid）已退出，正在停止其余进程。"
            exit 1
        fi
    done
done
