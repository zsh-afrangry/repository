"""Authenticated, same-origin web hosting for the Linux launcher only."""

import base64
import binascii
import hashlib
import hmac
import secrets
from pathlib import Path

from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.requests import HTTPConnection
from starlette.responses import HTMLResponse, PlainTextResponse, Response
from starlette.staticfiles import StaticFiles


LOGIN_PAGE = """<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>登录 KnowledgeMap</title>
<body><p id="status">正在登录 KnowledgeMap…</p>
<script nonce="__NONCE__">
(async () => {
  const key = new URLSearchParams(location.hash.slice(1)).get('key');
  history.replaceState(null, '', location.pathname);
  const status = document.getElementById('status');
  if (!key) { status.textContent = '请打开启动脚本输出的完整鉴权链接。'; return; }
  try {
    const response = await fetch('/_km/session', {
      method: 'POST', headers: {Authorization: 'Bearer ' + key}, credentials: 'same-origin'
    });
    if (!response.ok) throw new Error('auth');
    location.replace('/');
  } catch (_) { status.textContent = '登录失败，请重新运行启动脚本并打开完整链接。'; }
})();
</script></body></html>"""


class AccessKeyMiddleware:
    """Protect both the SPA and API, without buffering streaming responses."""

    def __init__(self, app, access_key: str):
        if len(access_key) < 32:
            raise ValueError("Web access key must contain at least 32 characters")
        self.app = app
        self.expected = f"km:{access_key}".encode()
        self.access_key = access_key.encode()
        self.session = hmac.new(self.access_key, b"KnowledgeMap browser session v1", hashlib.sha256).hexdigest()

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        if scope["type"] == "http" and scope["path"] == "/_km/login" and scope["method"] in {"GET", "HEAD"}:
            # The key is in the URL fragment, never in the HTTP request URL/logs.
            nonce = secrets.token_urlsafe(18)
            await HTMLResponse(LOGIN_PAGE.replace("__NONCE__", nonce), headers={
                "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": f"default-src 'none'; script-src 'nonce-{nonce}'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
            })(scope, receive, send)
            return
        authenticated = False
        try:
            scheme, encoded = headers.get("authorization", "").split(" ", 1)
            if scheme.lower() == "basic":
                authenticated = secrets.compare_digest(base64.b64decode(encoded, validate=True), self.expected)
            elif scheme.lower() == "bearer":
                authenticated = secrets.compare_digest(encoded.encode(), self.access_key)
        except (ValueError, binascii.Error):
            pass
        if "authorization" not in headers:
            cookie = HTTPConnection(scope).cookies.get("km_session", "")
            authenticated = secrets.compare_digest(cookie.encode(), self.session.encode())
        if not authenticated:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                response_headers = {"Cache-Control": "no-store"}
                # A bad link should show an error, not open a browser Basic dialog.
                if scope["path"] != "/_km/session":
                    response_headers["WWW-Authenticate"] = 'Basic realm="KnowledgeMap", charset="UTF-8"'
                await PlainTextResponse("Login required", status_code=401, headers=response_headers)(scope, receive, send)
            return
        # Browsers cache credentials/cookies. Reject cross-origin writes so another
        # website cannot use those credentials through a form or fetch request.
        if scope["type"] == "http" and scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
            origin = headers.get("origin")
            expected_origin = f'{scope["scheme"]}://{headers.get("host", "")}'
            if headers.get("sec-fetch-site") == "cross-site" or (origin and origin != expected_origin):
                await PlainTextResponse("Cross-origin write rejected", status_code=403)(scope, receive, send)
                return
        if scope["type"] == "http" and scope["path"] == "/_km/session":
            if scope["method"] != "POST":
                await PlainTextResponse("Method not allowed", status_code=405)(scope, receive, send)
                return
            response = Response(status_code=204, headers={"Cache-Control": "no-store"})
            response.set_cookie("km_session", self.session, httponly=True,
                                secure=scope["scheme"] == "https", samesite="strict", path="/")
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


class SPAFiles(StaticFiles):
    async def get_response(self, path, scope):
        # Missing API endpoints/assets must not turn into successful HTML pages.
        if (path == "api" or path.startswith("api/")
                or any(part.startswith(".") and part != "." for part in path.split("/"))):
            raise HTTPException(404)
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or Path(path).suffix or path.startswith("assets/"):
                raise
            return await super().get_response("index.html", scope)


def configure_web_host(app, config):
    dist = Path(config["dist"])
    if not (dist / "index.html").is_file():
        raise RuntimeError("Frontend build missing; run Start-KnowledgeMap.sh")
    app.add_middleware(AccessKeyMiddleware, access_key=config["access_key"])
    app.mount("/", SPAFiles(directory=dist, html=True), name="frontend")
