"""QWeather-backed weather endpoint for the dashboard."""

from __future__ import annotations

import gzip
import json
import os
import time
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv

router = APIRouter(prefix="/weather", tags=["weather"])

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_CACHE_TTL_SECONDS = 30 * 60
_cache: dict[str, Any] = {"expires_at": 0.0, "value": None}
_cache_lock = Lock()

# QWeather Location ID for Tianhe District, Guangzhou, Guangdong.
_LOCATION_ID = "101280109"
_LATITUDE = "23.14"
_LONGITUDE = "113.34"
_LOCATION_LABEL = "广东省 · 广州市 · 天河区"


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


def _load_weather() -> dict[str, Any]:
    now = time.monotonic()
    with _cache_lock:
        if _cache["value"] is not None and _cache["expires_at"] > now:
            return _cache["value"]

        current = _ensure_qweather_success(_request_qweather(f"/v7/weather/now?location={_LOCATION_ID}&lang=zh"))
        daily = _ensure_qweather_success(_request_qweather(f"/v7/weather/7d?location={_LOCATION_ID}&lang=zh"))
        air_quality = _request_qweather(f"/airquality/v1/current/{_LATITUDE}/{_LONGITUDE}?lang=zh")

        current_data = current.get("now", {})
        forecast = daily.get("daily", [])[:5]
        value = {
            "location": _LOCATION_LABEL,
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
        _cache.update(value=value, expires_at=now + _CACHE_TTL_SECONDS)
        return value


@router.get("/")
def get_weather():
    return _load_weather()
