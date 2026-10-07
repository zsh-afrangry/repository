"""Isolated hosting/auth tests: no MySQL, MongoDB or paid API calls.

对应文档：docs/11_Linux本机启动.md「一键启动与停止（Tailscale / 局域网）」。
改动 backend/app/web_host.py 的鉴权、SPA 回退或静态资源边界时复跑本文件。
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import StreamingResponse

from app.web_host import configure_web_host


def main():
    with tempfile.TemporaryDirectory() as folder:
        dist = Path(folder)
        (dist / "index.html").write_text("<html>KnowledgeMap</html>")
        (dist / "assets").mkdir()
        (dist / "assets/app.js").write_text("console.log('ok')")
        app = FastAPI()

        @app.get("/api/health")
        def health():
            return {"status": "ok"}

        @app.post("/api/write")
        def write():
            return {"ok": True}

        @app.post("/api/stream")
        def stream():
            return StreamingResponse(iter(["data: one\n\n", "data: two\n\n"]), media_type="text/event-stream")

        key = "test-key-" + "x" * 32
        configure_web_host(app, {"dist": folder, "access_key": key})
        with TestClient(app) as client:
            for path in ["/", "/bills", "/api/health", "/docs", "/openapi.json", "/assets/app.js"]:
                assert client.get(path).status_code == 401, path
            assert client.post("/api/write").status_code == 401
            assert client.get("/", auth=("km", "wrong")).status_code == 401
            assert client.get("/", headers={"Authorization": "Basic !!!"}).status_code == 401
            print("PASS authentication covers pages, assets, docs and API")
            client.auth = ("km", key)
            assert client.get("/api/health").json() == {"status": "ok"}
            for path in ["/", "/bills", "/tradesim/simulate", "/notes/deep/link"]:
                assert "<html>KnowledgeMap" in client.get(path).text
            assert client.get("/assets/app.js").status_code == 200
            for path in ["/api/missing", "/assets/missing.js", "/assets/missing", "/.env"]:
                assert client.get(path).status_code == 404, path
            print("PASS SPA refresh, static assets and API 404 boundaries")
            assert client.post("/api/write", headers={"Origin": "https://evil.example"}).status_code == 403
            assert client.post("/api/write", headers={"Origin": "null"}).status_code == 403
            assert client.post("/api/write", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
            assert client.post("/api/write", headers={"Origin": "http://testserver"}).status_code == 200
            assert client.post("/api/write").status_code == 200
            print("PASS cross-origin writes blocked; same-origin and CLI allowed")
            response = client.post("/api/stream")
            assert response.text == "data: one\n\ndata: two\n\n"
            assert response.headers["content-type"].startswith("text/event-stream")
            print("PASS streaming response preserved")
        with TestClient(app, base_url="https://testserver") as client:
            login = client.get("/_km/login")
            assert login.status_code == 200 and key not in login.text
            assert login.headers["cache-control"] == "no-store"
            assert client.post("/_km/session", headers={"Authorization": "Bearer wrong"}).status_code == 401
            assert "www-authenticate" not in client.post("/_km/session").headers
            headers = {"Authorization": "Bearer " + key, "Origin": "https://testserver"}
            assert client.post("/_km/session", headers={**headers, "Origin": "https://evil.example"}).status_code == 403
            response = client.post("/_km/session", headers=headers)
            assert response.status_code == 204
            cookie = response.headers["set-cookie"]
            assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie
            assert key not in cookie
            assert client.get("/api/health").status_code == 200
            assert client.post("/api/write", headers={"Origin": "https://evil.example"}).status_code == 403
            assert client.post("/api/write", headers={"Origin": "https://testserver"}).status_code == 200
            client.cookies.clear()
            client.cookies.set("km_session", "invalid")
            assert client.get("/api/health").status_code == 401
            print("PASS link login, secure cookie, invalid keys/cookies and cross-origin protection")


if __name__ == "__main__":
    main()
