"""QWeather-backed weather endpoint for the dashboard."""

from __future__ import annotations

import gzip
import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener, urlopen

from fastapi import APIRouter, HTTPException, Query, Request as WebRequest, Response
from dotenv import load_dotenv

router = APIRouter(prefix="/weather", tags=["weather"])

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_CACHE_TTL_SECONDS = 30 * 60
_GEO_CACHE_TTL_SECONDS = 24 * 60 * 60
# 缓存按 location id 分槽：早期是单槽缓存，换城市会拿到上一个城市的数据。
_weather_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_geo_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_weather_lock = Lock()

# Default location: Tianhe District, Guangzhou, Guangdong (QWeather Location ID).
_DEFAULT_LOCATION_ID = "101280109"

# 城市搜索：`/v7/weather/*` 需要 Location ID，空气质量接口还需要经纬度，
# 所以换城市必须一次拿到 id + lat + lon 三者。
_SEARCH_RESULT_LIMIT = 8
_SHARED_LOCATION_PATH = "/plugins/personal-profile/current-location"
_SHARED_LOCATION_PURPOSE = b"kurumi:shared-default-city:v1"


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _read_shared_location() -> dict[str, Any]:
    """Read only the owner's weather place over the fixed local service boundary."""
    token_path = Path(os.environ.get("KM_ASSISTANT_TOKEN_FILE", str(Path.home() / ".config/knowledgemap/assistant-token")))
    try:
        stat = token_path.lstat()
        if not token_path.is_absolute() or not token_path.is_file() or token_path.is_symlink() or stat.st_mode & 0o077 or stat.st_size > 512:
            raise ValueError("credential permissions")
        token = token_path.read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"[\x21-\x7e]{32,256}", token):
            raise ValueError("credential format")
        key = hmac.new(token.encode(), _SHARED_LOCATION_PURPOSE, hashlib.sha256).hexdigest()
        configured = os.environ.get("KURUMI_SHARED_LOCATION_URL", "http://127.0.0.1:18890" + _SHARED_LOCATION_PATH)
        url = urlsplit(configured)
        if (url.scheme != "http" or url.hostname != "127.0.0.1" or url.username or url.password
                or url.path != _SHARED_LOCATION_PATH or url.query or url.fragment or not url.port):
            raise ValueError("location service origin")
        request = Request(configured, headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
        opener = build_opener(ProxyHandler({}), _RejectRedirects())
        with opener.open(request, timeout=3) as response:
            if response.status != 200 or response.headers.get_content_type() != "application/json":
                raise ValueError("location service response")
            content = response.read(4097)
        if len(content) > 4096:
            raise ValueError("location service response size")
        result = json.loads(content)
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise ValueError("location service result")
        location, name, revision = result.get("location"), result.get("displayName"), result.get("revision")
        if not isinstance(location, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}|-?\d{1,3}\.\d{2},-?\d{1,2}\.\d{2}", location):
            raise ValueError("location identifier")
        if "," in location:
            longitude, latitude = (float(part) for part in location.split(","))
            if abs(longitude) > 180 or abs(latitude) > 90:
                raise ValueError("coordinates")
        if not isinstance(name, str) or not name.strip() or len(name) > 200 or re.search(r"[\x00-\x1f\x7f]", name):
            raise ValueError("location name")
        if type(revision) is not int or revision < 1:
            raise ValueError("location revision")
        return {"location": location, "displayName": name, "revision": revision}
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError, HTTPError, URLError, TimeoutError):
        raise HTTPException(503, detail="暂时无法读取助手所在地。", headers={"Cache-Control": "no-store"}) from None


def _weather_icon(icon_code: str | None) -> str:
    code = (icon_code or "").zfill(3)
    if code in {"100", "150"}:
        return "☀️"
    if code in {"101", "102", "103", "151", "152", "153"}:
        return "⛅"
    if code in {"104", "154"}:
        return "☁️"
    if code.startswith(("3", "4")):
        return "🌧️"
    if code.startswith("2"):
        return "❄️"
    if code.startswith("5"):
        return "🌫️"
    return "🌤️"


def _request_qweather(path: str) -> dict[str, Any]:
    api_host = os.getenv("QWEATHER_API_HOST", "").strip().rstrip("/")
    api_key = os.getenv("QWEATHER_API_KEY", "").strip()
    if not api_host or not api_key:
        raise HTTPException(
            status_code=503,
            detail="天气服务尚未配置。请设置 QWEATHER_API_HOST 和 QWEATHER_API_KEY。",
        )

    request = Request(
        f"https://{api_host}{path}",
        headers={"X-QW-Api-Key": api_key, "Accept-Encoding": "gzip"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = response.read()
            if response.headers.get("Content-Encoding", "").lower() == "gzip":
                payload = gzip.decompress(payload)
    except HTTPError as error:
        raise HTTPException(status_code=502, detail="天气服务暂时不可用。") from error
    except (URLError, TimeoutError) as error:
        raise HTTPException(status_code=502, detail="无法连接天气服务。") from error

    try:
        return json.loads(payload)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=502, detail="天气服务返回了无效数据。") from error


def _qweather_aqi(air_quality: dict[str, Any]) -> str:
    indexes = air_quality.get("indexes", [])
    preferred_codes = {"cn-mee", "cn-mee-1h", "qaqi"}
    selected = next((item for item in indexes if item.get("code") in preferred_codes), None)
    selected = selected or next((item for item in indexes if item.get("aqiDisplay")), None)
    return str(selected.get("aqiDisplay", "--")) if selected else "--"


def _ensure_qweather_success(payload: dict[str, Any]) -> dict[str, Any]:
    if "code" in payload and str(payload["code"]) != "200":
        raise HTTPException(status_code=502, detail="天气服务未能返回可用数据。")
    return payload


_ADMIN_SUFFIXES = ("特别行政区", "自治区", "省", "市", "区", "县", "盟", "州")


def _skeleton(name: str) -> str:
    """去掉行政区划后缀后的骨架，用于判断两级是不是同一个地方。

    `成都` / `成都市` 与 `北京` / `北京市` 这类组合必须视为同一级，
    否则标签会拼成「四川省 · 成都市 · 成都」。
    """
    for suffix in _ADMIN_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _place_label(place: dict[str, Any]) -> str:
    """把 GeoAPI 的行政区划拼成「广东省 · 广州市 · 天河区」这种标签。

    逐级去重：完全同名或只差行政区划后缀的两级只保留一级，
    这样城市级结果不会被拼成「四川省 · 成都市 · 成都」。
    """
    parts: list[str] = []
    skeletons: list[str] = []
    for key in ("adm1", "adm2", "name"):
        value = str(place.get(key) or "").strip()
        if not value:
            continue
        skeleton = _skeleton(value)
        if skeleton and skeleton in skeletons:
            continue
        parts.append(value)
        skeletons.append(skeleton)
    return " · ".join(parts) or "未命名地区"


def _search_places(keyword: str) -> list[dict[str, Any]]:
    """按名称搜索城市；返回 GeoAPI 的 location 数组。结果缓存 24h，避免反复消耗配额。"""
    cache_key = keyword.strip().lower()
    now = time.monotonic()
    with _weather_lock:
        cached = _geo_cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]["locations"]

    payload = _ensure_qweather_success(
        _request_qweather(
            f"/geo/v2/city/lookup?location={quote(keyword)}&number={_SEARCH_RESULT_LIMIT}&lang=zh"
        )
    )
    locations = payload.get("location") or []
    with _weather_lock:
        _geo_cache[cache_key] = (now + _GEO_CACHE_TTL_SECONDS, {"locations": locations})
    return locations


def _resolve_place(location_id: str) -> dict[str, Any] | None:
    """把 Location ID 解析成带经纬度的地点信息；解析不到时返回 None（调用方降级）。"""
    now = time.monotonic()
    with _weather_lock:
        cached = _geo_cache.get(location_id)
        if cached and cached[0] > now:
            return cached[1]["place"]

    try:
        payload = _ensure_qweather_success(
            _request_qweather(f"/geo/v2/city/lookup?location={quote(location_id)}&number=1&lang=zh")
        )
    except HTTPException:
        # 解析失败不应该让整个天气请求失败，交给调用方用默认坐标兜底
        return None

    locations = payload.get("location") or []
    place = locations[0] if locations else None
    with _weather_lock:
        _geo_cache[location_id] = (now + _GEO_CACHE_TTL_SECONDS, {"place": place})
    return place


def search_locations(keyword: str) -> list[dict[str, Any]]:
    """给接口层用的城市搜索入口，返回裁剪过的字段。"""
    if not keyword.strip():
        return []
    return [
        {
            "id": str(place.get("id", "")),
            "name": str(place.get("name", "")),
            "label": _place_label(place),
            "lat": str(place.get("lat", "")),
            "lon": str(place.get("lon", "")),
        }
        for place in _search_places(keyword)
        if place.get("id")
    ]


def _load_weather(location_id: str) -> dict[str, Any]:
    now = time.monotonic()
    with _weather_lock:
        cached = _weather_cache.get(location_id)
        if cached and cached[0] > now:
            return cached[1]

    place = _resolve_place(location_id)
    latitude = str(place.get("lat", "")) if place else ""
    longitude = str(place.get("lon", "")) if place else ""

    current = _ensure_qweather_success(_request_qweather(f"/v7/weather/now?location={location_id}&lang=zh"))
    daily = _ensure_qweather_success(_request_qweather(f"/v7/weather/7d?location={location_id}&lang=zh"))

    # 空气质量按经纬度取；地点解析不到时退回城市级查询，再不行才留空。
    air_quality: dict[str, Any] = {}
    if latitude and longitude:
        air_quality = _request_qweather(f"/airquality/v1/current/{latitude}/{longitude}?lang=zh")
    else:
        try:
            air_quality = _request_qweather(f"/airquality/v1/current/{location_id}?lang=zh")
        except HTTPException:
            air_quality = {}

    current_data = current.get("now", {})
    forecast = daily.get("daily", [])[:5]
    value = {
        "locationId": location_id,
        "location": _place_label(place) if place else location_id,
        "temp": int(float(current_data.get("temp", 0))),
        "condition": current_data.get("text", "未知"),
        "icon": _weather_icon(current_data.get("icon")),
        "feel": int(float(current_data.get("feelsLike", 0))),
        "humidity": int(float(current_data.get("humidity", 0))),
        "wind": f"{current_data.get('windDir', '无持续风向')} {current_data.get('windScale', '0')}级",
        "precip": str(current_data.get("precip", "0")),
        "aqi": _qweather_aqi(air_quality),
        "forecast": [
            {
                "day": item.get("fxDate", "")[5:].replace("-", "/"),
                "icon": _weather_icon(item.get("iconDay")),
                "tempHigh": int(float(item.get("tempMax", 0))),
                "tempLow": int(float(item.get("tempMin", 0))),
            }
            for item in forecast
        ],
        "updatedAt": current_data.get("obsTime"),
    }
    with _weather_lock:
        _weather_cache[location_id] = (now + _CACHE_TTL_SECONDS, value)
    return value


@router.get("/")
def get_weather(location: str | None = Query(default=None, max_length=64)):
    """取当前天气。`location` 传 QWeather Location ID；省略时用默认城市（广州天河）。"""
    return _load_weather(location.strip() if location and location.strip() else _DEFAULT_LOCATION_ID)


@router.get("/owner")
def get_owner_weather(request: WebRequest, response: Response):
    """Authenticated website only; browser choices never write to the owner profile."""
    if not getattr(request.app.state, "authenticated_web_host", False):
        raise HTTPException(403, detail="需要登录后查看助手所在地。", headers={"Cache-Control": "no-store"})
    shared = _read_shared_location()
    result = dict(_load_weather(shared["location"]))
    result["location"] = shared["displayName"]
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("/locations")
def get_locations(q: str = Query(min_length=1, max_length=64)):
    """按名称搜索城市，供首页天气板块切换地点使用。"""
    results = search_locations(q)
    if not results:
        raise HTTPException(status_code=404, detail="没有找到匹配的城市，换个关键词试试。")
    return {"query": q, "locations": results}
