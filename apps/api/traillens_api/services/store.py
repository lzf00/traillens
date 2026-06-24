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


def get_trail_public(trail_id: str) -> TrailOut | None:
    """跨用户读取 — 仅用于分享页 SSR(无 user_id 限定)。"""
    if db.has_db():
        return _db_get_trail_public(trail_id)
    trail = _TRAILS.get(trail_id)
    return trail


def list_photos_public(trail_id: str) -> list[PhotoOut]:
    if db.has_db():
        return _db_list_photos_public(trail_id)
    return _PHOTOS.get(trail_id, [])


def pick_demo_trail() -> TrailOut | None:
    """挑一个最适合做 demo 的 trail:有 travelogue + 有照片 > 0。

    选择规则:travelogue 非空 > photo_count 高 > updated_at 新。
    """
    if db.has_db():
        return _db_pick_demo()
    for t in sorted(_TRAILS.values(), key=lambda x: x.updated_at, reverse=True):
        if t.travelogue_md and t.photo_count > 0:
            return t
    # fallback:取最新一条
    return next(iter(sorted(_TRAILS.values(), key=lambda x: x.updated_at, reverse=True)), None)


def list_trails(*, user_id: str, limit: int = 50) -> list[TrailOut]:
    if db.has_db():
        return _db_list_trails(user_id=user_id, limit=limit)
    return _mem_list_trails(user_id=user_id, limit=limit)


def update_trail(
    trail_id: str,
    *,
    user_id: str,
    name: str | None = None,
    location_name: str | None = None,
    travelogue_md: str | None = None,
    next_trip_plan: dict | None = None,
) -> TrailOut | None:
    if db.has_db():
        return _db_update_trail(
            trail_id, user_id=user_id,
            name=name, location_name=location_name,
            travelogue_md=travelogue_md, next_trip_plan=next_trip_plan,
        )
    return _mem_update_trail(
        trail_id, user_id=user_id,
        name=name, location_name=location_name,
        travelogue_md=travelogue_md, next_trip_plan=next_trip_plan,
    )


def update_photo(
    trail_id: str,
    photo_id: str,
    *,
    user_id: str,
    verdict: str | None = None,
    aesthetic: dict | None = None,
    critique: str | None = None,
) -> bool:
    """改单张照片的 verdict / aesthetic / critique。返回是否找到。"""
    if db.has_db():
        return _db_update_photo(trail_id, photo_id, user_id=user_id,
                                verdict=verdict, aesthetic=aesthetic, critique=critique)
    return _mem_update_photo(trail_id, photo_id, user_id=user_id,
                             verdict=verdict, aesthetic=aesthetic, critique=critique)


def delete_photo(trail_id: str, photo_id: str, *, user_id: str) -> list[str]:
    """删单张照片,返回被删的 uri 列表(原图 + 缩略图,供 caller 清 COS)。"""
    if db.has_db():
        out = _db_delete_photo(trail_id, photo_id, user_id=user_id)
        return out or []
    one = _mem_delete_photo(trail_id, photo_id, user_id=user_id)
    return [one] if one else []


def delete_trail(trail_id: str, *, user_id: str) -> list[str]:
    """删除 trail + 所有 photos(级联),返回被删的 photo uri 列表(供 caller 清 COS)。"""
    if db.has_db():
        return _db_delete_trail(trail_id, user_id=user_id)
    return _mem_delete_trail(trail_id, user_id=user_id)


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


def _mem_update_trail(trail_id, *, user_id, name, location_name,
                       travelogue_md=None, next_trip_plan=None):
    trail = _TRAILS.get(trail_id)
    if not trail or trail.user_id != user_id:
        return None
    if name is not None:
        trail.name = name
    if location_name is not None:
        trail.location_name = location_name
    if travelogue_md is not None:
        trail.travelogue_md = travelogue_md
    if next_trip_plan is not None:
        trail.next_trip_plan = next_trip_plan
    trail.updated_at = _now()
    return trail


def _mem_update_photo(trail_id, photo_id, *, user_id, verdict, aesthetic, critique):
    trail = _mem_get_trail(trail_id, user_id=user_id)
    if not trail:
        return False
    for p in _PHOTOS.get(trail_id, []):
        if p.photo_id == photo_id:
            if verdict is not None: p.verdict = verdict
            if aesthetic is not None: p.aesthetic = aesthetic
            if critique is not None: p.critique = critique
            return True
    return False


def _mem_delete_photo(trail_id, photo_id, *, user_id):
    trail = _mem_get_trail(trail_id, user_id=user_id)
    if not trail:
        return None
    bucket = _PHOTOS.get(trail_id, [])
    for i, p in enumerate(bucket):
        if p.photo_id == photo_id:
            bucket.pop(i)
            return p.uri
    return None


def _mem_delete_trail(trail_id, *, user_id):
    trail = _TRAILS.get(trail_id)
    if not trail or trail.user_id != user_id:
        return []
    uris = [p.uri for p in _PHOTOS.get(trail_id, [])]
    _TRAILS.pop(trail_id, None)
    _PHOTOS.pop(trail_id, None)
    return uris


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
                 SELECT COALESCE(thumb_uri, uri) FROM photos
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
    sql = _text("""
        INSERT INTO photos (trail_id, uri, thumb_uri, exif)
        VALUES (:tid, :uri, :thumb, CAST(:exif AS jsonb))
    """)
    with db.session() as s:
        for p in photos:
            s.execute(sql, dict(
                tid=trail_id, uri=p.uri, thumb=getattr(p, "thumb_uri", None),
                exif=json.dumps(p.exif) if p.exif else None,
            ))
        return len(photos)


def _db_list_photos(trail_id, *, user_id):
    if not _db_get_trail(trail_id, user_id=user_id):
        return []
    return _db_list_photos_public(trail_id)


def _db_list_photos_public(trail_id):
    sql = _text("""
        SELECT id, uri, thumb_uri, verdict, reject_reason, aesthetic, critique, decision_trace
        FROM photos WHERE trail_id = :tid ORDER BY created_at
    """)
    with db.session() as s:
        rows = s.execute(sql, dict(tid=trail_id)).all()
        return [PhotoOut(
            photo_id=str(r.id), uri=r.uri, thumb_uri=r.thumb_uri,
            verdict=r.verdict, reject_reason=r.reject_reason,
            aesthetic=r.aesthetic, critique=r.critique,
            decision_trace=r.decision_trace or [],
        ) for r in rows]


def _db_get_trail_public(trail_id):
    sql = _text("""
        SELECT t.id, t.user_id, t.name, t.location_name, t.gpx_uri, t.state,
               t.travelogue_md, t.next_trip_plan, t.created_at, t.updated_at,
               (SELECT COUNT(*) FROM photos WHERE trail_id=t.id) AS photo_count,
               NULL::text AS cover_uri
        FROM trails t WHERE t.id = :tid
    """)
    with db.session() as s:
        row = s.execute(sql, dict(tid=trail_id)).first()
        return _row_to_trail(row) if row else None


def _db_pick_demo():
    sql = _text("""
        SELECT t.id, t.user_id, t.name, t.location_name, t.gpx_uri, t.state,
               t.travelogue_md, t.next_trip_plan, t.created_at, t.updated_at,
               (SELECT COUNT(*) FROM photos WHERE trail_id=t.id) AS photo_count,
               NULL::text AS cover_uri
        FROM trails t
        WHERE (SELECT COUNT(*) FROM photos WHERE trail_id=t.id) > 0
        ORDER BY (t.travelogue_md IS NOT NULL) DESC,
                 (SELECT COUNT(*) FROM photos WHERE trail_id=t.id) DESC,
                 t.updated_at DESC
        LIMIT 1
    """)
    with db.session() as s:
        row = s.execute(sql).first()
        return _row_to_trail(row) if row else None


def _db_update_trail(trail_id, *, user_id, name, location_name,
                       travelogue_md=None, next_trip_plan=None):
    fields = []
    params = {"tid": trail_id, "uid": user_id}
    if name is not None:
        fields.append("name = :name")
        params["name"] = name
    if location_name is not None:
        fields.append("location_name = :loc")
        params["loc"] = location_name
    if travelogue_md is not None:
        fields.append("travelogue_md = :tg")
        params["tg"] = travelogue_md
    if next_trip_plan is not None:
        fields.append("next_trip_plan = CAST(:plan AS jsonb)")
        params["plan"] = json.dumps(next_trip_plan)
    if not fields:
        return _db_get_trail(trail_id, user_id=user_id)
    sql = _text(f"""
        UPDATE trails SET {', '.join(fields)}, updated_at = now()
        WHERE id = :tid AND user_id = :uid
    """)
    with db.session() as s:
        s.execute(sql, params)
    return _db_get_trail(trail_id, user_id=user_id)


def _db_update_photo(trail_id, photo_id, *, user_id, verdict, aesthetic, critique):
    # 先 check ownership(trail 属于该 user)
    own = _text("SELECT 1 FROM trails WHERE id = :tid AND user_id = :uid")
    upd_fields = []
    params = {"pid": photo_id, "tid": trail_id, "uid": user_id}
    if verdict is not None:
        upd_fields.append("verdict = :v")
        params["v"] = verdict
    if aesthetic is not None:
        upd_fields.append("aesthetic = CAST(:a AS jsonb)")
        params["a"] = json.dumps(aesthetic)
    if critique is not None:
        upd_fields.append("critique = :c")
        params["c"] = critique
    if not upd_fields:
        return False
    sql = _text(f"""
        UPDATE photos SET {', '.join(upd_fields)}
        WHERE id = :pid AND trail_id = :tid
    """)
    with db.session() as s:
        if not s.execute(own, dict(tid=trail_id, uid=user_id)).first():
            return False
        result = s.execute(sql, params)
        return result.rowcount > 0


def _db_delete_photo(trail_id, photo_id, *, user_id):
    own = _text("SELECT 1 FROM trails WHERE id = :tid AND user_id = :uid")
    fetch = _text("SELECT uri, thumb_uri FROM photos WHERE id = :pid AND trail_id = :tid")
    delete = _text("DELETE FROM photos WHERE id = :pid AND trail_id = :tid")
    with db.session() as s:
        if not s.execute(own, dict(tid=trail_id, uid=user_id)).first():
            return None
        row = s.execute(fetch, dict(pid=photo_id, tid=trail_id)).first()
        if not row:
            return None
        s.execute(delete, dict(pid=photo_id, tid=trail_id))
        # 返回 (full_uri, thumb_uri) 让 caller 一并清
        return [u for u in (row.uri, row.thumb_uri) if u]


def _db_delete_trail(trail_id, *, user_id):
    """先查 photos uri,再 DELETE trail(级联删 photos)。"""
    uris_sql = _text("""
        SELECT uri FROM photos p
        JOIN trails t ON p.trail_id = t.id
        WHERE p.trail_id = :tid AND t.user_id = :uid
    """)
    del_sql = _text("DELETE FROM trails WHERE id = :tid AND user_id = :uid")
    with db.session() as s:
        uris = [r.uri for r in s.execute(uris_sql, dict(tid=trail_id, uid=user_id)).all()]
        s.execute(del_sql, dict(tid=trail_id, uid=user_id))
    return uris


def write_photo_embedding(photo_id: str, vec: list[float]) -> None:
    """单张照片的 critique embedding 写回 photos.embedding。

    pgvector 接受 '[0.1,0.2,...]' 字符串格式。
    """
    if not db.has_db() or not vec:
        return
    vec_str = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
    sql = _text("UPDATE photos SET embedding = CAST(:v AS vector) WHERE id = :pid")
    with db.session() as s:
        s.execute(sql, dict(pid=photo_id, v=vec_str))


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
