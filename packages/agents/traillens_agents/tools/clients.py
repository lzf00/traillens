"""工具层:把"外部能力"与"agent 逻辑"解耦。

为什么单独抽一层
----------------
- agent 节点只依赖这里的函数签名,不关心背后是 MCP server、HTTP API 还是本地模型。
- 这样第一周可以用 stub 跑通整张图,后续逐个替换为真实实现,
  对应路线图 M1->M3 的"先骨架后填肉"策略。
- *** 与第二块(美学微调)的接口在 score_aesthetics() ***:
  微调好的模型只要实现这个签名 + 返回 AestheticScore,即可热插拔。

真实接入提示见各函数 docstring 的 [REAL] 段。
"""

from __future__ import annotations

import os
import random
import sys
from pathlib import Path

from ..state.schema import AestheticScore, ExifMeta, Photo, PhotoVerdict

# --------------------------------------------------------------------------- #
# 把 packages/mcp_servers/<server>/ 加到 sys.path 以便 in-process 调用。
# 这种 in-process 调用是单机 dev 模式;生产模式下 MCP server 跑在独立进程或
# 通过 HTTP 暴露,见 docs/ARCHITECTURE.md §5。
# --------------------------------------------------------------------------- #
_MCP_ROOT = Path(__file__).resolve().parents[4] / "packages" / "mcp_servers"
for _pkg in ("traillens_sunmoon", "traillens_weather", "traillens_exif"):
    _p = _MCP_ROOT / _pkg
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# 允许通过 env var TRAILLENS_USE_STUBS=1 强制走 stub(测试 / 离线)
_USE_STUBS = os.environ.get("TRAILLENS_USE_STUBS") == "1"


# --------------------------------------------------------------------------- #
# 1) 美学评分(第二块的落地接口)
# --------------------------------------------------------------------------- #
def score_aesthetics(photo: Photo) -> AestheticScore:
    """对单张照片做 8 维美学评分。

    实现层级(从优先到 fallback):
      1) 调远端 Modal endpoint(TRAILLENS_AESTHETIC_ENDPOINT 设置时)
      2) 调本地 serve.py 的 score_image 函数(import 得到时)
      3) 随机 stub(保证 demo 永不翻车)

    切换契约:返回 schema 必须与 AestheticScore 严格一致。
    """
    if not _USE_STUBS:
        endpoint = os.environ.get("TRAILLENS_AESTHETIC_ENDPOINT")
        if endpoint:
            score = _score_via_http(photo, endpoint)
            if score is not None:
                return score
        # 本地 stub:复用 serve.py 的确定性算法
        score = _score_via_local_serve(photo)
        if score is not None:
            return score

    return _random_stub_score()


def _score_via_http(photo: Photo, endpoint: str) -> AestheticScore | None:
    try:
        import httpx  # type: ignore
    except ImportError:
        return None
    try:
        resp = httpx.post(
            f"{endpoint.rstrip('/')}/score",
            json={"image_url": photo.uri},
            timeout=20.0,
        )
        resp.raise_for_status()
        return AestheticScore(**resp.json())
    except Exception:  # noqa: BLE001  网络任何错都 fallback
        return None


def _score_via_local_serve(photo: Photo) -> AestheticScore | None:
    try:
        _serve_path = Path(__file__).resolve().parents[4] / "packages" / "aesthetic"
        if str(_serve_path) not in sys.path:
            sys.path.insert(0, str(_serve_path))
        from serve import ScoreRequest, score_image  # type: ignore
    except ImportError:
        return None
    try:
        out = score_image(ScoreRequest(image_url=photo.uri))
        return AestheticScore(**out.model_dump())
    except Exception:  # noqa: BLE001
        return None


def _random_stub_score() -> AestheticScore:
    base = random.uniform(4.5, 8.5)
    jitter = lambda: max(0.0, min(10.0, base + random.uniform(-1.2, 1.2)))  # noqa: E731
    return AestheticScore(
        overall=round(base, 2),
        composition=round(jitter(), 2),
        visual_elements=round(jitter(), 2),
        technical=round(jitter(), 2),
        originality=round(jitter(), 2),
        theme=round(jitter(), 2),
        emotion=round(jitter(), 2),
        gestalt=round(jitter(), 2),
        confidence=round(random.uniform(0.6, 0.95), 2),
        model_version="STUB-random-v0",
    )


# --------------------------------------------------------------------------- #
# 2) 技术质量检测(选片硬指标:模糊/曝光/重复)
# --------------------------------------------------------------------------- #
def detect_technical_defects(photo: Photo) -> tuple[PhotoVerdict, str | None]:
    """返回 (verdict, reason)。

    [STUB] 随机给瑕疵标签。
    [REAL] 用 OpenCV 拉普拉斯方差判模糊 + 直方图判过/欠曝 +
           CLIP/感知哈希(pHash)判重复帧。这些是 *确定性* 算法,
           应跑在美学模型之前作为快速过滤,降低 GPU 调用成本。
    """
    roll = random.random()
    if roll < 0.12:
        return PhotoVerdict.REJECT, "blur"
    if roll < 0.18:
        return PhotoVerdict.REJECT, "over_exposed"
    if roll < 0.25:
        return PhotoVerdict.REVIEW, "near_duplicate"  # 触发 HITL
    return PhotoVerdict.KEEP, None


# --------------------------------------------------------------------------- #
# 3) EXIF MCP server 客户端(第一个该开源的 MCP server)
# --------------------------------------------------------------------------- #
def read_exif(uri: str) -> ExifMeta:
    """[STUB] 返回伪造 EXIF。

    [REAL] 调用 packages/mcp_servers/exif_server.py 暴露的 MCP tool。
    本地实现可用 exifread / Pillow / pyexiv2。
    """
    return ExifMeta(
        focal_length_mm=random.choice([16, 24, 35, 50, 70, 200]),
        aperture_f=random.choice([1.8, 2.8, 4.0, 8.0, 11.0]),
        iso=random.choice([100, 200, 400, 800]),
        shutter=random.choice(["1/1000", "1/250", "1/60", "1/8"]),
        camera_model=random.choice(["Sony A7R5", "Fujifilm X-T5", "Nikon Z8"]),
        gps_lat=round(random.uniform(28.0, 31.0), 5),
        gps_lon=round(random.uniform(99.0, 103.0), 5),
    )


# --------------------------------------------------------------------------- #
# 4) 天气 / 天文 MCP servers(Story & Planner 用) — 已接真实实现 + 离线 fallback
# --------------------------------------------------------------------------- #
_WEATHER_STUBS = [
    "晴,能见度高,午后有积云", "多云转阴,光线柔和", "清晨有雾,适合氛围感拍摄"
]


def fetch_weather(lat: float, lon: float, date: str | None = None) -> str:
    """返回适合写入游记的天气短句。通过 MCPClient 抽象调 traillens-weather。"""
    if _USE_STUBS:
        return random.choice(_WEATHER_STUBS)
    from .mcp_client import client

    out = client("traillens_weather").call("weather_at", lat=lat, lon=lon, date=date)
    if not out or out.get("source") == "stub":
        return random.choice(_WEATHER_STUBS)
    return out.get("summary") or random.choice(_WEATHER_STUBS)


def sun_moon_times(lat: float, lon: float, date: str) -> dict:
    """蓝/金时刻 dict。通过 MCPClient 抽象调 traillens-sunmoon。"""
    if _USE_STUBS:
        return _sun_moon_stub()
    from .mcp_client import client

    out = client("traillens_sunmoon").call("sun_moon_times", lat=lat, lon=lon, date=date)
    return out or _sun_moon_stub()


def _sun_moon_stub() -> dict:
    return {
        "sunrise": "06:00",
        "sunset": "19:30",
        "golden_hour_am": "06:12-06:58",
        "golden_hour_pm": "18:30-19:14",
        "blue_hour_am": "05:42-06:12",
        "blue_hour_pm": "19:14-19:42",
        "source": "stub",
    }


def load_sample_photos(n: int = 8) -> list[Photo]:
    """造一批样本照片用于本地端到端跑通(无需真实文件)。"""
    photos = []
    for i in range(n):
        uri = f"sample://hike_2026_05/IMG_{1000 + i}.RAW"
        photos.append(Photo(photo_id=f"p{i:03d}", uri=uri, exif=read_exif(uri)))
    return photos
