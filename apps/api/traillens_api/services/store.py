"""Trail/Photo 存储 — 双后端(SQLAlchemy + in-memory)。

策略:
  - 配 DATABASE_URL 且能装 sqlalchemy → 用 Postgres(对接 Alembic 0001 migration)
  - 否则 → in-memory dict(测试 / 离线 demo)
  - routes 不感知后端差异 — 这是为什么 Sprint 4 -> Sprint 5 切换不会动 routes
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from ..schemas import PhotoIn, PhotoOut, TrailOut
from . import db

# in-memory 后端
_TRAILS: dict[str, TrailOut] = {}
_PHOTOS: dict[str, list[PhotoOut]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# 公开 API(routes 调这些)
# --------------------------------------------------------------------------- #
def create_trail(*, user_id: str, name: str, location_name: str | None, gpx_uri: str | None) -> TrailOut:
    if db.has_db():
        return _db_create_trail(user_id=user_id, name=name, location_name=location_name, gpx_uri=gpx_uri)
    return _mem_create_trail(user_id=user_id, name=name, location_name=location_name, gpx_uri=gpx_uri)


def get_trail(trail_id: str, *, user_id: str) -> TrailOut | None:
    if db.has_db():
        return _db_get_trail(trail_id, user_id=user_id)
    return _mem_get_trail(trail_id, user_id=user_id)


def list_trails(*, user_id: str, limit: int = 50) -> list[TrailOut]:
    if db.has_db():
        return _db_list_trails(user_id=user_id, limit=limit)
    return _mem_list_trails(user_id=user_id, limit=limit)


def add_photos(trail_id: str, *, user_id: str, photos: list[PhotoIn]) -> int:
    if db.has_db():
        return _db_add_photos(trail_id, user_id=user_id, photos=photos)
    return _mem_add_photos(trail_id, user_id=user_id, photos=photos)


def list_photos(trail_id: str, *, user_id: str) -> list[PhotoOut]:
    if db.has_db():
        return _db_list_photos(trail_id, user_id=user_id)
    return _mem_list_photos(trail_id, user_id=user_id)


def persist_run_results(
    trail_id: str,
    photos: list[Any],
    *,
    travelogue_md: str | None = None,
    next_trip_plan: dict[str, Any] | None = None,
) -> None:
    """跑完 agent 把 GraphState.photos 的分数 + verdict + 游记/计划写回 DB。

    photos 是 agent 包的 PhotoState 列表(uri 作主键匹配),按 uri 找已存的
    photos 行,UPDATE verdict/aesthetic/critique。
    """
    if db.has_db():
        _db_persist_run(trail_id, photos, travelogue_md=travelogue_md, next_trip_plan=next_trip_plan)
        return
    bucket = _PHOTOS.get(trail_id, [])
    by_uri = {p.uri: p for p in bucket}
    for ap in photos:
        existing = by_uri.get(ap.uri)
        if not existing:
            continue
        existing.verdict = getattr(ap.verdict, "value", ap.verdict) if ap.verdict else None
        existing.reject_reason = ap.reject_reason
        existing.aesthetic = ap.aesthetic.model_dump() if ap.aesthetic and hasattr(ap.aesthetic, "model_dump") else ap.aesthetic
        existing.critique = ap.critique
    trail = _TRAILS.get(trail_id)
    if trail:
        if travelogue_md:
            trail.travelogue_md = travelogue_md
        if next_trip_plan:
            trail.next_trip_plan = next_trip_plan
        trail.updated_at = _now()


def update_state_summary(trail_id: str, summary: dict[str, Any]) -> None:
    if db.has_db():
        _db_update_state(trail_id, summary)
    else:
        trail = _TRAILS.get(trail_id)
        if trail:
            trail.state_summary = summary
            trail.updated_at = _now()


def reset() -> None:
    """测试用 — 清空 in-memory;DB 模式下走 TRUNCATE。"""
    _TRAILS.clear()
    _PHOTOS.clear()
    if db.has_db():
        with db.session() as s:
            s.execute(_text("TRUNCATE photos, trails, agent_runs CASCADE"))


# --------------------------------------------------------------------------- #
# in-memory 实现
# --------------------------------------------------------------------------- #
def _mem_create_trail(*, user_id, name, location_name, gpx_uri):
    tid = str(uuid.uuid4())
    trail = TrailOut(
        id=tid, user_id=user_id, name=name, location_name=location_name, gpx_uri=gpx_uri,
        photo_count=0, state_summary={}, created_at=_now(), updated_at=_now(),
    )
    _TRAILS[tid] = trail
    _PHOTOS[tid] = []
    return trail


def _mem_get_trail(trail_id, *, user_id):
    trail = _TRAILS.get(trail_id)
    if not trail or trail.user_id != user_id:
        return None
    return trail


def _mem_add_photos(trail_id, *, user_id, photos):
    trail = _mem_get_trail(trail_id, user_id=user_id)
    if not trail:
        return 0
    bucket = _PHOTOS.setdefault(trail_id, [])
    for p in photos:
        bucket.append(PhotoOut(photo_id=str(uuid.uuid4()), uri=p.uri))
    trail.photo_count = len(bucket)
    trail.updated_at = _now()
    return len(photos)


def _mem_list_photos(trail_id, *, user_id):
    trail = _mem_get_trail(trail_id, user_id=user_id)
    if not trail:
        return []
    return _PHOTOS.get(trail_id, [])


def _mem_list_trails(*, user_id, limit):
    out = [t for t in _TRAILS.values() if t.user_id == user_id]
    out.sort(key=lambda t: t.updated_at, reverse=True)
    return out[:limit]


# --------------------------------------------------------------------------- #
# Postgres 实现(裸 SQL,对接 Alembic 0001)
# --------------------------------------------------------------------------- #
def _text(q):
    from sqlalchemy import text
    return text(q)


def _row_to_trail(row) -> TrailOut:
    return TrailOut(
        id=str(row.id),
        user_id=str(row.user_id),
        name=row.name,
        location_name=row.location_name,
        gpx_uri=row.gpx_uri,
        travelogue_md=row.travelogue_md,
        next_trip_plan=row.next_trip_plan,
        photo_count=row.photo_count or 0,
        cover_uri=getattr(row, "cover_uri", None),
        state_summary=(row.state if isinstance(row.state, dict) else (json.loads(row.state or "{}"))),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _db_create_trail(*, user_id, name, location_name, gpx_uri):
    sql = _text("""
        INSERT INTO trails (id, user_id, name, location_name, gpx_uri, state)
        VALUES (uuid_generate_v4(), :user_id, :name, :location_name, :gpx_uri, '{}'::jsonb)
        RETURNING id, user_id, name, location_name, gpx_uri, state, travelogue_md, next_trip_plan,
                  created_at, updated_at, 0 AS photo_count
    """)
    with db.session() as s:
        row = s.execute(sql, dict(user_id=user_id, name=name, location_name=location_name, gpx_uri=gpx_uri)).one()
        return _row_to_trail(row)


def _db_get_trail(trail_id, *, user_id):
    sql = _text("""
        SELECT t.id, t.user_id, t.name, t.location_name, t.gpx_uri, t.state,
               t.travelogue_md, t.next_trip_plan, t.created_at, t.updated_at,
               (SELECT COUNT(*) FROM photos WHERE trail_id=t.id) AS photo_count
        FROM trails t WHERE t.id = :tid AND t.user_id = :uid
    """)
    with db.session() as s:
        row = s.execute(sql, dict(tid=trail_id, uid=user_id)).first()
        return _row_to_trail(row) if row else None


def _db_list_trails(*, user_id, limit):
    sql = _text("""
        SELECT t.id, t.user_id, t.name, t.location_name, t.gpx_uri, t.state,
               t.travelogue_md, t.next_trip_plan, t.created_at, t.updated_at,
               (SELECT COUNT(*) FROM photos WHERE trail_id=t.id) AS photo_count,
               (
                 SELECT uri FROM photos
                 WHERE trail_id = t.id
                 ORDER BY (verdict = 'keep') DESC NULLS LAST, created_at ASC
                 LIMIT 1
               ) AS cover_uri
        FROM trails t
        WHERE t.user_id = :uid
        ORDER BY t.updated_at DESC
        LIMIT :lim
    """)
    with db.session() as s:
        rows = s.execute(sql, dict(uid=user_id, lim=limit)).all()
        return [_row_to_trail(r) for r in rows]


def _db_add_photos(trail_id, *, user_id, photos):
    if not _db_get_trail(trail_id, user_id=user_id):
        return 0
    sql = _text("INSERT INTO photos (trail_id, uri) VALUES (:tid, :uri)")
    with db.session() as s:
        for p in photos:
            s.execute(sql, dict(tid=trail_id, uri=p.uri))
        return len(photos)


def _db_list_photos(trail_id, *, user_id):
    if not _db_get_trail(trail_id, user_id=user_id):
        return []
    sql = _text("""
        SELECT id, uri, verdict, reject_reason, aesthetic, critique, decision_trace
        FROM photos WHERE trail_id = :tid ORDER BY created_at
    """)
    with db.session() as s:
        rows = s.execute(sql, dict(tid=trail_id)).all()
        return [PhotoOut(
            photo_id=str(r.id), uri=r.uri,
            verdict=r.verdict, reject_reason=r.reject_reason,
            aesthetic=r.aesthetic, critique=r.critique,
            decision_trace=r.decision_trace or [],
        ) for r in rows]


def _db_persist_run(trail_id, photos, *, travelogue_md, next_trip_plan):
    upd_photo = _text("""
        UPDATE photos
           SET verdict       = :verdict,
               reject_reason = :reason,
               aesthetic     = CAST(:aesthetic AS jsonb),
               critique      = :critique
         WHERE trail_id = :tid AND uri = :uri
    """)
    upd_trail = _text("""
        UPDATE trails
           SET travelogue_md  = COALESCE(:tg, travelogue_md),
               next_trip_plan = CAST(COALESCE(:plan, next_trip_plan::text) AS jsonb),
               updated_at     = now()
         WHERE id = :tid
    """)
    with db.session() as s:
        for ap in photos:
            verdict = getattr(ap.verdict, "value", ap.verdict) if ap.verdict else None
            aesthetic = ap.aesthetic.model_dump() if (ap.aesthetic and hasattr(ap.aesthetic, "model_dump")) else ap.aesthetic
            s.execute(upd_photo, dict(
                tid=trail_id,
                uri=ap.uri,
                verdict=verdict,
                reason=ap.reject_reason,
                aesthetic=json.dumps(aesthetic) if aesthetic else None,
                critique=ap.critique,
            ))
        s.execute(upd_trail, dict(
            tid=trail_id,
            tg=travelogue_md,
            plan=json.dumps(next_trip_plan) if next_trip_plan else None,
        ))


def _db_update_state(trail_id, summary):
    sql = _text("UPDATE trails SET state = :s, updated_at = now() WHERE id = :tid")
    with db.session() as s:
        s.execute(sql, dict(tid=trail_id, s=json.dumps(summary)))
