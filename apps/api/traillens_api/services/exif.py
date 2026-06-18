"""上传时从二进制字节提取 EXIF,存到 photos.exif jsonb 字段。

策略:
- Pillow 解析 EXIF;失败/无 Pillow 时返回空 dict(不阻断上传)
- 字段对齐 packages/agents/traillens_agents/state/schema.py::ExifMeta

为什么不复用 packages/mcp_servers/traillens_exif:
- 那个模块吃文件路径 + 是 MCP server,启动开销大
- 这里上传热路径需要纯字节解析,做最小 inline 版本
"""

from __future__ import annotations

import io
from typing import Any


def extract_exif_from_bytes(data: bytes) -> dict[str, Any]:
    """从字节流读 EXIF,返回 ExifMeta 兼容 dict。

    失败永远返回空 dict — 上传不该被坏 EXIF 阻断。
    """
    try:
        from PIL import ExifTags, Image  # type: ignore
    except ImportError:
        return {}

    try:
        with Image.open(io.BytesIO(data)) as img:
            raw = img.getexif()
    except Exception:  # noqa: BLE001
        return {}
    if not raw:
        return {}

    tag = {ExifTags.TAGS.get(k, str(k)): v for k, v in raw.items()}
    gps_raw = raw.get(ExifTags.Base.GPSInfo.value) if hasattr(ExifTags, "Base") else None
    lat, lon = _parse_gps(gps_raw) if gps_raw else (None, None)

    result: dict[str, Any] = {
        "focal_length_mm": _to_float(tag.get("FocalLength")),
        "aperture_f": _to_float(tag.get("FNumber")),
        "iso": _to_int(tag.get("ISOSpeedRatings") or tag.get("PhotographicSensitivity")),
        "shutter": _format_shutter(tag.get("ExposureTime")),
        "captured_at": _to_iso(tag.get("DateTimeOriginal") or tag.get("DateTime")),
        "gps_lat": lat,
        "gps_lon": lon,
        "camera_model": _concat(tag.get("Make"), tag.get("Model")),
    }
    return {k: v for k, v in result.items() if v is not None}


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    if isinstance(v, (list, tuple)) and v:
        v = v[0]
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _format_shutter(v: Any) -> str | None:
    f = _to_float(v)
    if f is None or f <= 0:
        return None
    if f >= 1:
        return f'{f:.0f}"'
    denom = round(1 / f)
    return f"1/{denom}"


def _to_iso(s: Any) -> str | None:
    if not s:
        return None
    s = str(s).strip()
    # EXIF DateTimeOriginal:"YYYY:MM:DD HH:MM:SS" → ISO8601
    if len(s) >= 19 and s[4] == ":" and s[7] == ":":
        return s[:4] + "-" + s[5:7] + "-" + s[8:10] + "T" + s[11:]
    return s


def _concat(make: Any, model: Any) -> str | None:
    m = (str(make).strip() if make else "")
    md = (str(model).strip() if model else "")
    if m and md and md.startswith(m):
        return md
    return (m + " " + md).strip() or None


def _parse_gps(gps: dict[int, Any]) -> tuple[float | None, float | None]:
    try:
        lat = _dms_to_deg(gps[2], gps.get(1, "N"))
        lon = _dms_to_deg(gps[4], gps.get(3, "E"))
        return lat, lon
    except (KeyError, TypeError, ValueError):
        return None, None


def _dms_to_deg(dms, ref: str) -> float | None:
    if not dms or len(dms) < 3:
        return None
    d = float(dms[0]) + float(dms[1]) / 60 + float(dms[2]) / 3600
    if str(ref).upper() in ("S", "W"):
        d = -d
    return round(d, 6)
