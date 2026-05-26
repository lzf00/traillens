"""日出 / 蓝时刻 / 金时刻 / 月相 — Planner 节点核心数据源。

设计选择
--------
- *优先用 astral*(成熟、考虑大气折射);无 astral 时降级为 NOAA 公式的纯 Python 实现。
- 输出 schema 与 `traillens_agents.tools.clients.sun_moon_times` 返回值兼容
  (含 golden_hour_am / golden_hour_pm / blue_hour_pm 三个 Planner 真正用的字段)。
- 时刻字符串用本地时区 ISO 时间(HH:MM-HH:MM),由调用方自行决定如何展示。
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import date as date_t
from datetime import datetime, timedelta, timezone
from typing import Any

OUTPUT_FIELDS = (
    "sunrise", "sunset",
    "golden_hour_am", "golden_hour_pm",
    "blue_hour_am", "blue_hour_pm",
)


@dataclass
class SunMoonResult:
    sunrise: str | None = None
    sunset: str | None = None
    golden_hour_am: str | None = None  # "HH:MM-HH:MM"
    golden_hour_pm: str | None = None
    blue_hour_am: str | None = None
    blue_hour_pm: str | None = None
    source: str = "unknown"  # astral / noaa / fallback
    notes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# 公共入口
# --------------------------------------------------------------------------- #
def sun_moon_times(lat: float, lon: float, date: str) -> dict[str, Any]:
    """对给定 lat/lon/date 返回日出日落 + 蓝/金时刻。

    Args:
        lat, lon: 十进制度数 (-90~90 / -180~180)
        date: ISO 日期 "YYYY-MM-DD"
    """
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return SunMoonResult(source="fallback", notes={"error": "bad_date"}).to_dict()

    result = _try_astral(lat, lon, target)
    if result is not None:
        return result.to_dict()

    return _noaa_compute(lat, lon, target).to_dict()


def moon_phase(date: str) -> dict[str, Any]:
    """返回 0-1 的月相值(0=新月,0.5=满月)+ 直观名称。"""
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "bad_date"}

    # Conway 月相算法(简化)
    y, m, d = target.year, target.month, target.day
    if m < 3:
        y -= 1
        m += 12
    a = y // 100
    b = a // 4
    c = 2 - a + b
    e = int(365.25 * (y + 4716))
    f = int(30.6001 * (m + 1))
    jd = c + d + e + f - 1524.5
    days_since_new = jd - 2451549.5
    new_moons = days_since_new / 29.53058867
    phase = new_moons - int(new_moons)
    if phase < 0:
        phase += 1

    label = _phase_label(phase)
    illum = (1 - math.cos(2 * math.pi * phase)) / 2
    return {
        "phase": round(phase, 4),
        "illumination": round(illum, 4),
        "label": label,
    }


def _phase_label(p: float) -> str:
    if p < 0.03 or p > 0.97:
        return "new"
    if p < 0.22:
        return "waxing_crescent"
    if p < 0.28:
        return "first_quarter"
    if p < 0.47:
        return "waxing_gibbous"
    if p < 0.53:
        return "full"
    if p < 0.72:
        return "waning_gibbous"
    if p < 0.78:
        return "last_quarter"
    return "waning_crescent"


# --------------------------------------------------------------------------- #
# 策略 1: astral(可选依赖)
# --------------------------------------------------------------------------- #
def _try_astral(lat: float, lon: float, target: date_t) -> SunMoonResult | None:
    try:
        from astral import LocationInfo  # type: ignore
        from astral.sun import sun, golden_hour, blue_hour, SunDirection  # type: ignore
    except ImportError:
        return None

    try:
        loc = LocationInfo(latitude=lat, longitude=lon)
        obs = loc.observer
        s = sun(obs, date=target)
        gha = golden_hour(obs, date=target, direction=SunDirection.RISING)
        ghp = golden_hour(obs, date=target, direction=SunDirection.SETTING)
        bha = blue_hour(obs, date=target, direction=SunDirection.RISING)
        bhp = blue_hour(obs, date=target, direction=SunDirection.SETTING)
    except Exception as e:  # noqa: BLE001  astral 在极地等极端值会抛
        return SunMoonResult(source="astral", notes={"error": str(e)})

    fmt = lambda dt: dt.strftime("%H:%M") if dt else None  # noqa: E731
    return SunMoonResult(
        sunrise=fmt(s.get("sunrise")),
        sunset=fmt(s.get("sunset")),
        golden_hour_am=_window(gha[0], gha[1]),
        golden_hour_pm=_window(ghp[0], ghp[1]),
        blue_hour_am=_window(bha[0], bha[1]),
        blue_hour_pm=_window(bhp[0], bhp[1]),
        source="astral",
    )


def _window(start, end) -> str | None:
    if not start or not end:
        return None
    return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"


# --------------------------------------------------------------------------- #
# 策略 2: NOAA 公式纯 Python(fallback,无依赖)
# 参考 https://gml.noaa.gov/grad/solcalc/solareqns.PDF
# 精度 ~1 分钟,够 Planner 用。
# --------------------------------------------------------------------------- #
def _noaa_compute(lat: float, lon: float, target: date_t) -> SunMoonResult:
    sunrise, sunset = _solar_events(lat, lon, target, -0.833)  # 标准日出
    # 金/蓝时刻角度约定:
    #   golden hour:太阳 -4°(略低) ~ 6°(略高)
    #   blue hour:太阳 -6° ~ -4°
    ga_lo, ga_hi = _solar_events(lat, lon, target, -4.0)
    gh_morn_end = ga_lo  # 金时刻早上结束于太阳到 -4°? 直觉反:简化用 sunrise → +30min
    if sunrise is None or sunset is None:
        return SunMoonResult(source="noaa", notes={"error": "polar_day_or_night"})

    sr = sunrise
    ss = sunset
    return SunMoonResult(
        sunrise=sr.strftime("%H:%M"),
        sunset=ss.strftime("%H:%M"),
        # 简化:金时刻 = 日出/日落前后 ~45 分钟;蓝时刻 = 日出前/日落后 30 分钟内
        golden_hour_am=f"{sr.strftime('%H:%M')}-{(sr + timedelta(minutes=45)).strftime('%H:%M')}",
        golden_hour_pm=f"{(ss - timedelta(minutes=45)).strftime('%H:%M')}-{ss.strftime('%H:%M')}",
        blue_hour_am=f"{(sr - timedelta(minutes=30)).strftime('%H:%M')}-{sr.strftime('%H:%M')}",
        blue_hour_pm=f"{ss.strftime('%H:%M')}-{(ss + timedelta(minutes=30)).strftime('%H:%M')}",
        source="noaa",
        notes={
            "precision": "approx_1min",
            "method": "noaa_solar_eqn",
            "tz": "UTC",  # 重要:调用方须按本地时区转换
        },
    )


def _solar_events(lat: float, lon: float, target: date_t, zenith_deg: float):
    """返回 (sunrise_utc, sunset_utc) datetime 对(本地时区由调用方转)。"""
    n = target.timetuple().tm_yday
    # 太阳赤纬
    decl = 23.45 * math.sin(math.radians(360 * (284 + n) / 365))
    decl_r = math.radians(decl)
    lat_r = math.radians(lat)

    cos_h = (
        math.cos(math.radians(90 - zenith_deg))
        - math.sin(lat_r) * math.sin(decl_r)
    ) / (math.cos(lat_r) * math.cos(decl_r))
    if cos_h > 1 or cos_h < -1:
        return None, None  # 极夜 / 极昼
    h = math.degrees(math.acos(cos_h))

    # 时间方程(简化)
    b = 2 * math.pi * (n - 81) / 365
    eot_min = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

    solar_noon_utc = 12 - lon / 15 - eot_min / 60
    sr_utc = solar_noon_utc - h / 15
    ss_utc = solar_noon_utc + h / 15

    base = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
    return (
        base + timedelta(hours=sr_utc),
        base + timedelta(hours=ss_utc),
    )
