"""Open-Meteo 天气代理。

为何 Open-Meteo
---------------
- 免费 + 无 key,适合一开始就跑起来。
- 数据源自欧洲中期天气预报中心(ECMWF) + 多家国家气象局,质量靠谱。
- API 简单:GET https://api.open-meteo.com/v1/forecast?...

设计选择
--------
- 标准库 urllib + json,不引入 httpx/requests,保持包的轻量。
- 网络失败时返回 stub 字符串("未知 — 网络不可用"),不抛异常,
  让 agent 不被外部依赖打断。
- 输出兼容 agents.tools.clients.fetch_weather 现有签名(返回 str/dict 双形态)。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_S = 6.0

# WMO weather code → 摄影友好的人类描述
WMO_CN = {
    0: "晴",
    1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "凇雾",
    51: "毛毛雨", 53: "中等毛毛雨", 55: "密毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    77: "雪粒",
    80: "阵雨小", 81: "阵雨中", 82: "阵雨大",
    85: "阵雪小", 86: "阵雪大",
    95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
}


def _wmo_label(code: int | None) -> str:
    if code is None:
        return "未知"
    return WMO_CN.get(int(code), f"WMO {code}")


# --------------------------------------------------------------------------- #
# 公共入口
# --------------------------------------------------------------------------- #
def weather_at(lat: float, lon: float, date: str | None = None) -> dict[str, Any]:
    """返回当日 / 指定日期的简明天气摘要(供 Story 节点用)。"""
    params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,weather_code,cloud_cover,visibility",
        "daily": "weather_code,sunrise,sunset,precipitation_sum",
        "timezone": "auto",
    }
    if date:
        params["start_date"] = date
        params["end_date"] = date

    data = _fetch(params)
    if "error" in data:
        return {
            "summary": "未知 — 网络不可用",
            "source": "stub",
            "error": data["error"],
        }

    cur = data.get("current") or {}
    daily = data.get("daily") or {}
    weather_code = (daily.get("weather_code") or [cur.get("weather_code")])[0] if daily else cur.get("weather_code")
    label = _wmo_label(weather_code)
    cloud = cur.get("cloud_cover")
    vis_km = (cur.get("visibility") or 0) / 1000 if cur.get("visibility") else None
    temp = cur.get("temperature_2m")

    bits = [label]
    if cloud is not None:
        bits.append(f"云量 {cloud}%")
    if vis_km:
        bits.append(f"能见度 {vis_km:.0f}km")
    if temp is not None:
        bits.append(f"{temp}°C")
    return {
        "summary": ",".join(bits),
        "weather_code": weather_code,
        "weather_label": label,
        "cloud_cover": cloud,
        "visibility_km": vis_km,
        "temperature_c": temp,
        "source": "open-meteo",
    }


def forecast(lat: float, lon: float, days: int = 3) -> dict[str, Any]:
    """N 天预报概览(供 Planner 节点用)。"""
    days = max(1, min(days, 14))
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,sunrise,sunset",
        "forecast_days": days,
        "timezone": "auto",
    }
    data = _fetch(params)
    if "error" in data:
        return {"days": [], "source": "stub", "error": data["error"]}

    d = data.get("daily") or {}
    times = d.get("time") or []
    out = []
    for i, dt in enumerate(times):
        out.append({
            "date": dt,
            "weather_label": _wmo_label(_safe(d.get("weather_code"), i)),
            "t_max_c": _safe(d.get("temperature_2m_max"), i),
            "t_min_c": _safe(d.get("temperature_2m_min"), i),
            "precip_mm": _safe(d.get("precipitation_sum"), i),
            "sunrise": _safe(d.get("sunrise"), i),
            "sunset": _safe(d.get("sunset"), i),
        })
    return {"days": out, "source": "open-meteo"}


# --------------------------------------------------------------------------- #
# 私有
# --------------------------------------------------------------------------- #
def _safe(seq, i):
    try:
        return seq[i]
    except (IndexError, TypeError):
        return None


def _fetch(params: dict[str, Any]) -> dict[str, Any]:
    q = urllib.parse.urlencode(params)
    url = f"{BASE}?{q}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "traillens-weather/0.0.1"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return {"error": f"{type(e).__name__}:{e}"}
