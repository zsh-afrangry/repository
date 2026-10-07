#!/usr/bin/env bash
# 一键启动带鉴权的独立网页服务（默认 Tailscale HTTPS；--lan 为局域网 HTTP）。
# 对应文档：docs/11_Linux本机启动.md「一键启动与停止（Tailscale / 局域网）」。
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$ROOT/scripts/knowledgemap_launcher.py" start "$@"
