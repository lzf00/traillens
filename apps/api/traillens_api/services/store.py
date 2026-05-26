"""极简 in-memory 存储,Sprint 5 替换为 Postgres + SQLAlchemy。

把"未来要换 Postgres"的契约用纯函数边界框死,
未来切换只换实现不动 routes。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ..schemas import PhotoIn, PhotoOut, TrailOut

# {trail_id: TrailOut + photos[]}
_TRAILS: dict[str, TrailOut] = {}
_PHOTOS: dict[str, list[PhotoOut]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_trail(*, user_id: str, name: str, location_name: str | None, gpx_uri: str | None) -> TrailOut:
    tid = str(uuid.uuid4())
    trail = TrailOut(
        id=tid,
        user_id=user_id,
        name=name,
        location_name=location_name,
        gpx_uri=gpx_uri,
        photo_count=0,
        state_summary={},
        created_at=_now(),
        updated_at=_now(),
    )
    _TRAILS[tid] = trail
    _PHOTOS[tid] = []
    return trail


def get_trail(trail_id: str, *, user_id: str) -> TrailOut | None:
    trail = _TRAILS.get(trail_id)
    if not trail or trail.user_id != user_id:
        return None
    return trail


def add_photos(trail_id: str, *, user_id: str, photos: list[PhotoIn]) -> int:
    trail = get_trail(trail_id, user_id=user_id)
    if not trail:
        return 0
    bucket = _PHOTOS.setdefault(trail_id, [])
    for p in photos:
        bucket.append(PhotoOut(photo_id=str(uuid.uuid4()), uri=p.uri))
    trail.photo_count = len(bucket)
    trail.updated_at = _now()
    return len(photos)


def list_photos(trail_id: str, *, user_id: str) -> list[PhotoOut]:
    trail = get_trail(trail_id, user_id=user_id)
    if not trail:
        return []
    return _PHOTOS.get(trail_id, [])


def update_state_summary(trail_id: str, summary: dict[str, Any]) -> None:
    trail = _TRAILS.get(trail_id)
    if trail:
        trail.state_summary = summary
        trail.updated_at = _now()


def reset() -> None:
    """测试用。"""
    _TRAILS.clear()
    _PHOTOS.clear()
