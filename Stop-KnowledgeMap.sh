#!/usr/bin/env bash
# 停止 Start-KnowledgeMap.sh 启动的独立网页服务及其 Tailscale 转发，保留数据库与手动开发进程。
# 对应文档：docs/11_Linux本机启动.md「一键启动与停止（Tailscale / 局域网）」。
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$ROOT/scripts/knowledgemap_launcher.py" stop "$@"
