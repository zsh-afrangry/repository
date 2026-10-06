#!/usr/bin/env python3
"""Manage only KnowledgeMap's authenticated web service and its Serve endpoint."""

import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
STATE = Path.home() / ".local/state/knowledgemap-launcher"
CONFIG = STATE / "web.json"
UNIT = "knowledgemap-web.service"
PORT = 8020
HTTPS_PORT = 8443
TARGET = f"http://127.0.0.1:{PORT}"


def run(*args, capture=False, check=True, **kwargs):
    return subprocess.run(args, text=True, check=check, capture_output=capture, **kwargs)


def active():
    return run("systemctl", "--user", "is-active", "--quiet", UNIT, check=False).returncode == 0


def serve_state():
    return json.loads(run("tailscale", "serve", "status", "--json", capture=True).stdout or "{}")


def endpoint_owned(state, config):
    authority = config.get("tailnet_authority")
    return (authority is not None
            and state.get("Web", {}).get(authority, {}).get("Handlers") == {"/": {"Proxy": TARGET}}
            and state.get("TCP", {}).get(str(HTTPS_PORT)) == {"HTTPS": True}
            and not state.get("AllowFunnel", {}).get(authority))


def check_tailnet(config):
    status = json.loads(run("tailscale", "status", "--json", capture=True).stdout)
    if status.get("BackendState") != "Running":
        raise RuntimeError("Tailscale 未连接；请先登录，或使用 --lan 启动。")
    dns = status.get("Self", {}).get("DNSName", "").rstrip(".")
    if not dns:
        raise RuntimeError("未找到 Tailscale DNS 名称。")
    config["tailnet_authority"] = f"{dns}:{HTTPS_PORT}"
    state = serve_state()
    occupied = (str(HTTPS_PORT) in state.get("TCP", {})
                or any(key.endswith(f":{HTTPS_PORT}") for key in state.get("Web", {})))
    if occupied and not endpoint_owned(state, config):
        raise RuntimeError("Tailscale 8443 已被其他配置占用；未覆盖它。")
    if state.get("AllowFunnel", {}).get(config["tailnet_authority"]):
        raise RuntimeError("8443 存在 Funnel 公网配置；请先手动关闭。")


def change_serve(*args):
    result = run("tailscale", "serve", *args, capture=True, check=False)
    if result.returncode:
        # Some installations reserve Serve changes for root. Let sudo prompt only
        # in an actual terminal; unattended runs fail with an actionable message.
        if "access denied" in (result.stderr + result.stdout).lower():
            prefix = ["sudo"] if sys.stdin.isatty() else ["sudo", "-n"]
            run(*prefix, "tailscale", "serve", *args)
        else:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def remove_serve(config):
    if config.get("mode") == "tailscale" and config.get("tailnet_authority"):
        state = serve_state()
        if endpoint_owned(state, config):
            change_serve(f"--https={HTTPS_PORT}", "off")
        elif str(HTTPS_PORT) in state.get("TCP", {}):
            print("8443 转发已被其他配置替换，保留该配置。", file=sys.stderr)


def save(config):
    temporary = CONFIG.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(CONFIG)


def show(config, reveal=True):
    print(f"KnowledgeMap 已启动（{config['mode']}）。")
    suffix = "/_km/login#key=" + quote(config["access_key"], safe="") if reveal else "/"
    if config["mode"] == "tailscale":
        print(f"Tailscale: https://{config['tailnet_authority']}{suffix}")
    else:
        data = json.loads(run("ip", "-j", "-4", "addr", "show", "scope", "global", capture=True).stdout)
        for interface in data:
            if interface["ifname"] != "tailscale0":
                for address in interface.get("addr_info", []):
                    print(f"局域网: http://{address['local']}:{PORT}{suffix}")
        print("局域网模式使用 HTTP，仅适用于可信网络；HTTPS 请使用默认 Tailscale 模式。")
    print(f"本机: {TARGET}{suffix}")
    if reveal:
        print("打开上方完整链接即可自动登录。")
    print(f"口令文件（仅当前用户可读）: {CONFIG}")
    print(f"停止: {ROOT / 'Stop-KnowledgeMap.sh'}")


def ready(config):
    credentials = base64.b64encode(f"km:{config['access_key']}".encode()).decode()
    request = urllib.request.Request(TARGET + "/api/health", headers={"Authorization": "Basic " + credentials})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(60):
        if not active():
            raise RuntimeError(f"服务启动失败，请查看 journalctl --user -u {UNIT} -n 50")
        try:
            with opener.open(request, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.5)
    raise RuntimeError("服务未在 30 秒内就绪，请检查数据库与服务日志。")


def start(args, previous):
    mode = "lan" if args.lan else "tailscale"
    if active():
        if not previous or previous.get("root") != str(ROOT):
            raise RuntimeError("同名服务已存在但不属于当前目录，未修改它。")
        if previous["mode"] != mode:
            raise RuntimeError("服务正在另一模式运行，请先执行 Stop-KnowledgeMap.sh 再切换。")
        ready(previous)
        if mode == "tailscale":
            check_tailnet(previous)
            if not endpoint_owned(serve_state(), previous):
                change_serve("--bg", f"--https={HTTPS_PORT}", TARGET)
        show(previous, not args.hide_key)
        return
    python = Path(os.environ.get("KM_PYTHON", str(Path.home() / "miniconda3/envs/desheng/bin/python")))
    if not python.is_file():
        raise RuntimeError("找不到 desheng Python；请设置 KM_PYTHON 为解释器绝对路径。")
    if not (ROOT / "frontend/node_modules").is_dir():
        raise RuntimeError("缺少前端依赖，请先在 frontend 执行 npm ci。")
    config = {"root": str(ROOT), "mode": mode, "port": PORT,
              "host": "0.0.0.0" if args.lan else "127.0.0.1",
              "access_key": previous.get("access_key", secrets.token_urlsafe(32)),
              "dist": str(STATE / "site")}
    if mode == "tailscale":
        check_tailnet(config)
    with socket.socket() as probe:
        # Match uvicorn: recently closed connections in TIME_WAIT are reusable.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((config["host"], PORT))
        except OSError as exc:
            raise RuntimeError(f"端口 {PORT} 已占用；不会停止现有进程。") from exc
    run("npm", "run", "build", cwd=ROOT / "frontend")
    # Keep a private snapshot: a later development build cannot replace live files.
    site = STATE / "site"
    if site.exists():
        shutil.rmtree(site)
    shutil.copytree(ROOT / "frontend/dist", site)
    run("systemctl", "--user", "start", "knowledgemap-mongodb.service")
    if previous.get("root") == str(ROOT):
        remove_serve(previous)
    save(config)
    run("systemctl", "--user", "reset-failed", UNIT, capture=True, check=False)
    try:
        run("systemd-run", "--user", "--collect", f"--unit={UNIT}",
            f"--working-directory={ROOT / 'backend'}",
            "--property=TimeoutStopSec=20", f"--setenv=KM_WEB_CONFIG={CONFIG}",
            str(python), str(ROOT / "backend/main.py"))
        ready(config)
        if mode == "tailscale":
            change_serve("--bg", f"--https={HTTPS_PORT}", TARGET)
    except BaseException:
        run("systemctl", "--user", "stop", UNIT, check=False)
        remove_serve(config)
        raise
    show(config, not args.hide_key)


def main():
    parser = argparse.ArgumentParser(description="KnowledgeMap 启停器：默认 Tailscale HTTPS，--lan 使用局域网 HTTP。")
    parser.add_argument("action", choices=["start", "stop"])
    parser.add_argument("--lan", action="store_true", help="监听 0.0.0.0:8020（需登录口令）")
    parser.add_argument("--hide-key", action="store_true", help="不在终端打印口令")
    args = parser.parse_args()
    os.umask(0o077)
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    STATE.chmod(0o700)
    with (STATE / "launcher.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
        if previous and previous.get("root") != str(ROOT):
            raise RuntimeError("启动配置属于另一份项目目录，请先处理原目录的服务和配置。")
        if args.action == "start":
            start(args, previous)
        else:
            # Stop the app even if tailscaled is currently unavailable.
            if active():
                if not previous:
                    raise RuntimeError("缺少本项目配置，拒绝停止来源不明的同名服务。")
                run("systemctl", "--user", "stop", UNIT)
            remove_serve(previous)
            print("KnowledgeMap 已停止。开发进程、MySQL、MongoDB 和 DSH 保持原状。")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
