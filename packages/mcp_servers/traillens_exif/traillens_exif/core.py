"""EXIF 读取核心逻辑(无 MCP 依赖,可单独 import)。

设计选择
--------
- *优先用标准库 + Pillow*,因为 Pillow 在大多数 Python 环境已存在;
  Pillow 不在时降级为只读取文件元信息(尺寸/格式),给出 best-effort 结果。
- 返回 schema 与 `traillens_agents.state.schema.ExifMeta` 严格对齐
  (见 contract test in tests/test_exif_server.py)。
- 不解析厂商私有标签(节省维护成本);只覆盖摄影师真正用得到的 8 个字段。
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# 与 packages/agents/traillens_agents/state/schema.py::ExifMeta 对齐的 8 个字段
EXIF_FIELDS = (
    "focal_length_mm",
    "aperture_f",
    "iso",
    "shutter",
    "captured_at",
    "gps_lat",
    "gps_lon",
    "camera_model",
)


@dataclass
class ExifResult:
    """与 ExifMeta 同形;独立定义避免本包反向依赖 agents 包。"""

    focal_length_mm: float | None = None
    aperture_f: float | None = None
    iso: int | None = None
    shutter: str | None = None
    captured_at: str | None = None  # ISO8601;agent 端再 parse 成 datetime
    gps_lat: float | None = None
    gps_lon: float | None = None
    camera_model: str | None = None
    # 元信息(非 EXIF schema 一部分,便于 debug)
    source: str = "unknown"  # pillow / pyexiv2 / fallback
    error: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# 公共入口
# --------------------------------------------------------------------------- #
def extract_exif(path: str | Path) -> ExifResult:
    """读取一张图的 EXIF,返回与 ExifMeta 对齐的结果。

    多策略:
        Pillow → (将来) pyexiv2 → 文件元信息 fallback。
    任何分支失败都返回 ExifResult(error=...),不抛异常,让 agent 不被一张坏图打断。
    """
    p = Path(path)
    if not p.exists():
        return ExifResult(source="fallback", error=f"file_not_found:{path}")

    result = _try_pillow(p)
    if result is not None:
        return result

    # 最后兜底:只给文件名 / 大小,EXIF 字段全 None
    stat = p.stat()
    return ExifResult(
        source="fallback",
        error="no_exif_library_available",
        extras={"size_bytes": stat.st_size, "modified_at": stat.st_mtime},
    )


# --------------------------------------------------------------------------- #
# 实现策略 1: Pillow
# --------------------------------------------------------------------------- #
def _try_pillow(p: Path) -> ExifResult | None:
    try:
        from PIL import ExifTags, Image  # type: ignore
    except ImportError:
        return None

    try:
        with Image.open(p) as img:
            raw = img.getexif()
    except Exception as e:  # noqa: BLE001  Pillow 对非图像文件会抛各种异常
        return ExifResult(source="pillow", error=f"open_failed:{type(e).__name__}")

    if not raw:
        return ExifResult(source="pillow", error="empty_exif")

    tag_map = {ExifTags.TAGS.get(k, str(k)): v for k, v in raw.items()}
    gps_raw = raw.get(ExifTags.Base.GPSInfo.value) if hasattr(ExifTags, "Base") else None
    gps = _parse_gps(gps_raw) if gps_raw else (None, None)

    return ExifResult(
        focal_length_mm=_to_float(tag_map.get("FocalLength")),
        aperture_f=_to_float(tag_map.get("FNumber")),
        iso=_to_int(tag_map.get("ISOSpeedRatings") or tag_map.get("PhotographicSensitivity")),
        shutter=_format_shutter(tag_map.get("ExposureTime")),
        captured_at=_to_iso(tag_map.get("DateTimeOriginal") or tag_map.get("DateTime")),
        gps_lat=gps[0],
        gps_lon=gps[1],
        camera_model=_concat_model(tag_map.get("Make"), tag_map.get("Model")),
        source="pillow",
    )


# --------------------------------------------------------------------------- #
# 解析帮手(纯函数,易测)
# --------------------------------------------------------------------------- #
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
    """Pillow 把 ExposureTime 返回为 IFDRational/float(秒)。
    转回摄影师习惯的 1/N 或 Ns 表达。"""
    f = _to_float(v)
    if f is None or f <= 0:
        return None
    if f >= 1:
        return f"{f:g}s"
    return f"1/{round(1 / f)}"


def _to_iso(v: Any) -> str | None:
    if not v:
        return None
    # EXIF 标准格式: "YYYY:MM:DD HH:MM:SS"
    try:
        dt = datetime.strptime(str(v), "%Y:%m:%d %H:%M:%S")
        return dt.isoformat()
    except ValueError:
        return str(v)  # 原样返回,前端容错处理


def _concat_model(make: Any, model: Any) -> str | None:
    parts = [str(x).strip() for x in (make, model) if x]
    return " ".join(parts) if parts else None


def _parse_gps(gps: dict) -> tuple[float | None, float | None]:
    """EXIF GPS 是 (度, 分, 秒) + 半球字符,转成带符号十进制。"""

    def dms_to_decimal(dms, ref):
        try:
            d, m, s = (float(x) for x in dms)
            val = d + m / 60 + s / 3600
            return -val if ref in ("S", "W") else val
        except (TypeError, ValueError):
            return None

    lat = dms_to_decimal(gps.get(2), gps.get(1)) if gps.get(2) and gps.get(1) else None
    lon = dms_to_decimal(gps.get(4), gps.get(3)) if gps.get(4) and gps.get(3) else None
    return lat, lon


# --------------------------------------------------------------------------- #
# 便利:批量摘要(给 agent 在 culling 前做 "这一组照片大致拍了什么" 概览)
# --------------------------------------------------------------------------- #
def summarize_batch(paths: list[str | Path]) -> dict[str, Any]:
    """对一组照片产出统计摘要,给 Critic / Story / Planner 节点做上下文。"""
    results = [extract_exif(p) for p in paths]
    focals = [r.focal_length_mm for r in results if r.focal_length_mm]
    isos = [r.iso for r in results if r.iso]
    gps_pts = [(r.gps_lat, r.gps_lon) for r in results if r.gps_lat and r.gps_lon]
    return {
        "n_photos": len(results),
        "n_with_exif": sum(1 for r in results if r.error is None),
        "focal_range_mm": [min(focals), max(focals)] if focals else None,
        "iso_range": [min(isos), max(isos)] if isos else None,
        "gps_bbox": _bbox(gps_pts) if gps_pts else None,
        "cameras": sorted({r.camera_model for r in results if r.camera_model}),
    }


def _bbox(points: list[tuple[float, float]]) -> dict[str, float]:
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    return {
        "min_lat": min(lats), "max_lat": max(lats),
        "min_lon": min(lons), "max_lon": max(lons),
    }
