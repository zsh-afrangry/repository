"""天气地点切换的隔离用例：桩掉 QWeather HTTP，只验证纯逻辑。

对应文档：docs/12_首页与账单收尾验收.md「首页天气地点可切换（2026-10-06）」。
改动本项目天气逻辑时，先复跑本文件，再按该节的验收路径做浏览器确认。

不连数据库、不发真实网络请求、不读 .env 里的 key（只用假值即可）。
跑法（需已安装 fastapi 的 desheng 环境）：

    conda activate desheng
    cd backend
    python tests/weather_cases.py

设计要点：被测的是 `app.routers.weather` 的真实函数，只把 `_request_qweather`
换成桩，因此地点解析、标签拼接、按地点分槽缓存、降级路径都是真实代码在跑。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.routers import weather  # noqa: E402

failures = []
checks = 0


def check(condition, label):
    global checks
    checks += 1
    if condition:
        print("PASS", label)
    else:
        failures.append(label)
        print("FAIL", label)


# ---- 桩掉对 QWeather 的 HTTP 调用 ----
CALLS: list[str] = []

GEO_BY_KEYWORD = {
    "天河": [
        {"id": "101280109", "name": "天河区", "adm1": "广东省", "adm2": "广州市", "lat": "23.14", "lon": "113.34"}
    ],
    "101280109": [
        {"id": "101280109", "name": "天河区", "adm1": "广东省", "adm2": "广州市", "lat": "23.14", "lon": "113.34"}
    ],
    "成都": [
        {"id": "101270101", "name": "成都", "adm1": "四川省", "adm2": "成都市", "lat": "30.67", "lon": "104.06"}
    ],
    "101270101": [
        {"id": "101270101", "name": "成都", "adm1": "四川省", "adm2": "成都市", "lat": "30.67", "lon": "104.06"}
    ],
}

WEATHER_NOW = {
    "101280109": {"now": {"temp": "30", "text": "多云", "icon": "101", "feelsLike": "33", "humidity": "70", "windDir": "东南风", "windScale": "2", "precip": "0.0", "obsTime": "2026-10-06T12:00+08:00"}},
    "101270101": {"now": {"temp": "22", "text": "小雨", "icon": "305", "feelsLike": "21", "humidity": "85", "windDir": "北风", "windScale": "3", "precip": "1.2", "obsTime": "2026-10-06T12:00+08:00"}},
}


def fake_request(path: str):
    CALLS.append(path)
    if path.startswith("/geo/v2/city/lookup"):
        from urllib.parse import parse_qs, urlparse

        keyword = parse_qs(urlparse(path).query).get("location", [""])[0]
        return {"code": "200", "location": GEO_BY_KEYWORD.get(keyword, [])}
    if path.startswith("/v7/weather/now"):
        loc = path.split("location=")[1].split("&")[0]
        return {"code": "200", **WEATHER_NOW.get(loc, WEATHER_NOW["101280109"])}
    if path.startswith("/v7/weather/7d"):
        return {"code": "200", "daily": [{"fxDate": f"2026-10-{6 + i:02d}", "iconDay": "101", "tempMax": "30", "tempMin": "20"} for i in range(7)]}
    if path.startswith("/airquality/"):
        return {"code": "200", "indexes": [{"code": "cn-mee", "aqiDisplay": "42"}]}
    raise AssertionError(f"未预期的路径: {path}")


weather._request_qweather = fake_request
weather._weather_cache.clear()
weather._geo_cache.clear()
CALLS.clear()

# ---- 1. 地点标签拼接（含同地两级的去重） ----
check(
    weather._place_label({"adm1": "广东省", "adm2": "广州市", "name": "天河区"}) == "广东省 · 广州市 · 天河区",
    "地点标签按 adm1 · adm2 · name 拼接（与改造前的展示一致）",
)
check(
    weather._place_label({"adm1": "北京市", "adm2": "北京", "name": "北京"}) == "北京市",
    "完全同名的两级只保留一级",
)
check(
    weather._place_label({"adm1": "四川省", "adm2": "成都市", "name": "成都"}) == "四川省 · 成都市",
    "只差行政区划后缀的两级只保留一级（不拼成「四川省 · 成都市 · 成都」）",
)
check(weather._place_label({}) == "未命名地区", "空地点有回退名")

# ---- 2. 城市搜索 ----
results = weather.search_locations("成都")
check(len(results) == 1, "搜索「成都」返回 1 条")
check(results[0]["id"] == "101270101", "搜索结果带 Location ID")
check(results[0]["label"] == "四川省 · 成都市", "搜索结果带拼好的展示名")
check(results[0]["lat"] == "30.67" and results[0]["lon"] == "104.06", "搜索结果带经纬度")
check(weather.search_locations("") == [], "空关键词不发起搜索")
check(weather.search_locations("不存在的城市") == [], "无匹配时返回空列表（由接口层转 404）")

# ---- 3. 天气按地点取值，缓存按地点分槽 ----
CALLS.clear()
gz = weather._load_weather("101280109")
check(gz["location"] == "广东省 · 广州市 · 天河区", "默认城市标签来自解析结果，不再是硬编码常量")
check(gz["locationId"] == "101280109", "返回里带 locationId")
check(gz["temp"] == 30 and gz["condition"] == "多云", "广州天气字段正确")

cd = weather._load_weather("101270101")
check(cd["temp"] == 22 and cd["condition"] == "小雨", "换到成都后拿到的是成都的数据（单槽缓存已修）")
check(cd["location"] == "四川省 · 成都市", "成都标签正确且无重复层级")
check(gz["temp"] == 30, "换城市没有污染上一个地点的缓存对象")

CALLS.clear()
again = weather._load_weather("101270101")
check(again["temp"] == 22, "重复请求同一地点返回同样数据")
check(len([c for c in CALLS if c.startswith("/v7/")]) == 0, "重复请求同一地点命中缓存、未再调用 QWeather")

CALLS.clear()
gz2 = weather._load_weather("101280109")
check(gz2["temp"] == 30, "广州缓存仍独立存在")
check(len([c for c in CALLS if c.startswith("/v7/")]) == 0, "广州也命中缓存")

# ---- 4. 空气质量用解析出的经纬度，而不是硬编码坐标 ----
CALLS.clear()
weather._weather_cache.clear()
weather._load_weather("101270101")
air = [c for c in CALLS if c.startswith("/airquality/")]
check(len(air) == 1, "空气质量请求发起 1 次")
check("/30.67/104.06" in air[0], "空气质量用的是该城市解析出的经纬度，不是硬编码的广州坐标")

# ---- 5. 地点解析失败时降级，天气不整体失败 ----
weather._weather_cache.clear()
weather._geo_cache.clear()
original = weather._request_qweather


def failing_geo(path):
    if path.startswith("/geo/"):
        raise weather.HTTPException(status_code=502, detail="geo 挂了")
    return original(path)


weather._request_qweather = failing_geo
CALLS.clear()
try:
    degraded = weather._load_weather("999999999")
    check(True, "地点解析失败时天气请求不整体失败")
    check(degraded["location"] == "999999999", "解析不到时用 id 作为展示名回退")
except Exception as exc:  # noqa: BLE001 - 用例就是要记录任何异常
    check(False, f"地点解析失败时天气请求不整体失败（实际抛了 {exc!r}）")

print()
print(f"{checks - len(failures)}/{checks} checks passed")
if failures:
    print("失败项：")
    for item in failures:
        print("  -", item)
    sys.exit(1)
