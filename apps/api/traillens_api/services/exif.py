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
    """从字节流读 EXIF + OpenCV 计算 blur/exposure 指标。

    返回 ExifMeta 兼容字段 + 扩展 _tech_metrics:
      blur_score (拉普拉斯方差,<100 模糊)
      exposure_under_pct / exposure_over_pct (0-1,>30% 即过/欠)

    失败永远返回空 dict — 上传不该被坏 EXIF 阻断。
    """
    result: dict[str, Any] = {}

    # ---- EXIF (Pillow) ----
    try:
        from PIL import ExifTags, Image
        with Image.open(io.BytesIO(data)) as img:
            raw = img.getexif()
            if raw:
                tag = {ExifTags.TAGS.get(k, str(k)): v for k, v in raw.items()}
                gps_raw = raw.get(ExifTags.Base.GPSInfo.value) if hasattr(ExifTags, "Base") else None
                lat, lon = _parse_gps(gps_raw) if gps_raw else (None, None)
                ef = {
                    "focal_length_mm": _to_float(tag.get("FocalLength")),
                    "aperture_f": _to_float(tag.get("FNumber")),
                    "iso": _to_int(tag.get("ISOSpeedRatings") or tag.get("PhotographicSensitivity")),
                    "shutter": _format_shutter(tag.get("ExposureTime")),
                    "captured_at": _to_iso(tag.get("DateTimeOriginal") or tag.get("DateTime")),
                    "gps_lat": lat,
                    "gps_lon": lon,
                    "camera_model": _concat(tag.get("Make"), tag.get("Model")),
                }
                result.update({k: v for k, v in ef.items() if v is not None})
    except Exception:  # noqa: BLE001
        pass

    # ---- OpenCV 技术指标 ----
    try:
        import cv2
        import numpy as np
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is not None:
            # 缩到 short side 512px 加速
            h, w = img.shape[:2]
            scale = 512 / max(h, w) if max(h, w) > 512 else 1.0
            if scale < 1.0:
                img = cv2.resize(img, (int(w * scale), int(h * scale)))
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 1. 拉普拉斯方差判模糊(<100 通常模糊)
            blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            # 2. 直方图判过/欠曝(灰度 0-15 占比 / 240-255 占比)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
            total = hist.sum() or 1.0
            under_pct = float(hist[:16].sum() / total)
            over_pct = float(hist[240:].sum() / total)

            # 3. 计算 dHash(64-bit,用于跨照片去重)
            small = cv2.resize(gray, (9, 8))
            diff = small[:, 1:] > small[:, :-1]
            dhash = 0
            for bit in diff.flatten():
                dhash = (dhash << 1) | int(bool(bit))

            result["_tech_metrics"] = {
                "blur_score": round(blur_score, 1),
                "exposure_under_pct": round(under_pct, 3),
                "exposure_over_pct": round(over_pct, 3),
                "dhash": f"{dhash:016x}",
            }
    except Exception:  # noqa: BLE001
        pass

    return result


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
