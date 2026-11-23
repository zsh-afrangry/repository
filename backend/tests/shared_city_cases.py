"""Isolated shared-city API contract; loopback fixtures only, no production data or weather calls.

对应文档：docs/18_助手业务接口与共享数据.md「测试与脚本」。
With --external-profile, a caller supplies a disposable loopback Fusion profile fixture.
"""
import hashlib
import hmac
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers import weather
from app.web_host import configure_web_host

TOKEN = "fixture-shared-city-" + "x" * 40
KEY = "website-test-" + "y" * 40
DERIVED = hmac.new(TOKEN.encode(), b"kurumi:shared-default-city:v1", hashlib.sha256).hexdigest()


def client_for(folder: Path, authenticated: bool):
    app = FastAPI()
    app.include_router(weather.router, prefix="/api")
    if authenticated:
        (folder / "index.html").write_text("test", encoding="utf-8")
        configure_web_host(app, {"dist": str(folder), "access_key": KEY})
    return TestClient(app)


def exercise_base(folder: Path):
    # The weather provider is stubbed: no database or external weather network.
    old_load = weather._load_weather
    weather._load_weather = lambda location: {"locationId": location, "location": "upstream label", "temp": 21}
    try:
        with client_for(folder, False) as client:
            assert client.get("/api/weather/owner").status_code == 403
            assert client.get("/api/weather/", params={"location": "101010100"}).json()["locationId"] == "101010100"
        with client_for(folder, True) as client:
            assert client.get("/api/weather/owner").status_code == 401
            client.auth = ("km", KEY)
            result = client.get("/api/weather/owner")
            assert result.status_code == 200, result.text
            assert result.headers["cache-control"] == "no-store"
            assert result.json() == {"locationId": "101280109", "location": "广东省广州市天河区", "temp": 21}
            denied_write = client.post("/api/weather/owner")
            assert denied_write.status_code in (404, 405), denied_write.status_code
            assert client.get("/api/weather/", params={"location": "101010100"}).json()["locationId"] == "101010100"
    finally:
        weather._load_weather = old_load


def main():
    with tempfile.TemporaryDirectory(prefix="km-shared-city-") as tmp:
        folder = Path(tmp)
        if sys.argv[1:] == ["--external-profile"]:
            endpoint = urlsplit(os.environ.get("KURUMI_SHARED_LOCATION_URL", ""))
            token_file = Path(os.environ.get("KM_ASSISTANT_TOKEN_FILE", ""))
            assert endpoint.hostname == "127.0.0.1" and endpoint.port not in (None, 18890)
            assert token_file.is_absolute() and str(token_file).startswith(tempfile.gettempdir() + "/")
            exercise_base(folder)
            print("PASS authenticated website reads real isolated Fusion HTTP profile; no production services")
            return
        assert not sys.argv[1:]
        token_file = folder / "token"
        token_file.write_text(TOKEN, encoding="ascii")
        token_file.chmod(0o600)
        os.environ["KM_ASSISTANT_TOKEN_FILE"] = str(token_file)
        state = {"count": 0, "result": {"ok": True, "location": "101280109", "displayName": "广东省广州市天河区", "revision": 1}}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                state["count"] += 1
                if self.headers.get("Authorization") != "Bearer " + DERIVED:
                    self.send_response(401)
                    self.end_headers()
                    return
                body = json.dumps(state["result"], ensure_ascii=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        os.environ["KURUMI_SHARED_LOCATION_URL"] = f"http://127.0.0.1:{server.server_port}" + weather._SHARED_LOCATION_PATH
        try:
            exercise_base(folder)
            assert state["count"] == 1, "unauthenticated and independent city reads must not query the profile"
            state["result"] = {"ok": True, "location": "114.57,35.12", "displayName": "测试校区", "revision": 2}
            old_load = weather._load_weather
            weather._load_weather = lambda location: {"locationId": location, "location": "other", "temp": 20}
            try:
                with client_for(folder, True) as client:
                    client.auth = ("km", KEY)
                    current = client.get("/api/weather/owner")
                    assert current.status_code == 200
                    assert current.json() == {"locationId": "114.57,35.12", "location": "测试校区", "temp": 20}
            finally:
                weather._load_weather = old_load
            for invalid in [
                {"ok": True, "location": "101&bad=1", "displayName": "test", "revision": 1},
                {"ok": True, "location": "181.00,20.00", "displayName": "test", "revision": 1},
                {"ok": True, "location": "101", "displayName": "test\nforged", "revision": 1},
                {"ok": True, "location": "101", "displayName": "test", "revision": True},
            ]:
                state["result"] = invalid
                try:
                    weather._read_shared_location()
                    raise AssertionError("invalid location accepted")
                except weather.HTTPException as error:
                    assert error.status_code == 503
            token_file.chmod(0o644)
            try:
                weather._read_shared_location()
                raise AssertionError("unsafe token accepted")
            except weather.HTTPException as error:
                assert error.status_code == 503
            print("PASS website authentication, independent city selection, scoped credential and invalid results")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    main()
