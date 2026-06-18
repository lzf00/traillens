"""/v1/library — 跨 trail 的搜索。

策略(自动降级):
  1) 优先用 Doubao embedding 对 q 编码,pgvector cosine 距离查 photos.embedding
     · 召回数据需照片有 critique embedding(orchestrator 跑完后写)
  2) embedding 不可用 / 无结果 → 回退 PG ILIKE 三路 OR
     (critique + trails.name/location + travelogue)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text

from ..deps import CurrentUser, get_current_user
from ..services import db, store
from ..services.embedding import embed_text

router = APIRouter()


class SearchResult(BaseModel):
    photo_id: str
    trail_id: str
    trail_name: str
    uri: str
    verdict: str | None = None
    overall: float | None = None
    score: float  # 0-1,目前 = 命中字段数 / 3


@router.get("/search", response_model=list[SearchResult])
def search(
    q: str = Query(..., min_length=1, description="自然语言查询,如:川西秋天逆光"),
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
) -> list[SearchResult]:
    if not db.has_db():
        return []

    # ----- 路径 1: pgvector 语义查询 -----
    qvec = embed_text(q)
    if qvec:
        vec_str = "[" + ",".join(f"{x:.6f}" for x in qvec) + "]"
        sem_sql = text("""
            SELECT
              p.id, p.uri, p.verdict, p.aesthetic,
              t.id AS trail_id, t.name AS trail_name,
              1 - (p.embedding <=> CAST(:v AS vector)) AS score
            FROM photos p
            JOIN trails t ON t.id = p.trail_id
            WHERE t.user_id = :uid AND p.embedding IS NOT NULL
            ORDER BY p.embedding <=> CAST(:v AS vector)
            LIMIT :lim
        """)
        with db.session() as s:
            rows = s.execute(sem_sql, dict(v=vec_str, uid=user.id, lim=limit)).all()
        if rows:
            return [
                SearchResult(
                    photo_id=str(r.id),
                    trail_id=str(r.trail_id),
                    trail_name=r.trail_name,
                    uri=r.uri,
                    verdict=r.verdict,
                    overall=(r.aesthetic or {}).get("overall") if isinstance(r.aesthetic, dict) else None,
                    score=float(r.score),
                )
                for r in rows
            ]

    # ----- 路径 2: ILIKE fallback -----
    like = f"%{q.strip()}%"
    sql = text("""
        SELECT
            p.id, p.uri, p.verdict, p.aesthetic,
            t.id AS trail_id, t.name AS trail_name,
            (
              (CASE WHEN p.critique ILIKE :like THEN 1 ELSE 0 END)
            + (CASE WHEN t.name ILIKE :like OR coalesce(t.location_name,'') ILIKE :like THEN 1 ELSE 0 END)
            + (CASE WHEN coalesce(t.travelogue_md,'') ILIKE :like THEN 1 ELSE 0 END)
            )::float / 3.0 AS score
        FROM photos p
        JOIN trails t ON t.id = p.trail_id
        WHERE t.user_id = :uid
          AND (
              p.critique ILIKE :like
              OR t.name ILIKE :like
              OR coalesce(t.location_name, '') ILIKE :like
              OR coalesce(t.travelogue_md, '') ILIKE :like
          )
        ORDER BY score DESC, p.created_at DESC
        LIMIT :lim
    """)
    with db.session() as s:
        rows = s.execute(sql, dict(like=like, uid=user.id, lim=limit)).all()
    return [
        SearchResult(
            photo_id=str(r.id),
            trail_id=str(r.trail_id),
            trail_name=r.trail_name,
            uri=r.uri,
            verdict=r.verdict,
            overall=(r.aesthetic or {}).get("overall") if isinstance(r.aesthetic, dict) else None,
            score=float(r.score),
        )
        for r in rows
    ]


@router.post("/embed/all")
def reembed_all(user: CurrentUser = Depends(get_current_user)) -> dict:
    """对该用户所有有 critique 的照片重算 embedding(MVP 后台脚本式)。"""
    from ..services.embedding import embed_batch
    sql = text("""
        SELECT p.id, p.critique FROM photos p
        JOIN trails t ON t.id = p.trail_id
        WHERE t.user_id = :uid AND p.critique IS NOT NULL AND p.embedding IS NULL
    """)
    with db.session() as s:
        rows = s.execute(sql, dict(uid=user.id)).all()
    if not rows:
        return {"embedded": 0, "skipped": 0}
    vecs = embed_batch([r.critique for r in rows])
    written = 0
    for r, v in zip(rows, vecs):
        if v:
            store.write_photo_embedding(str(r.id), v)
            written += 1
    return {"embedded": written, "skipped": len(rows) - written}


@router.post("/embed/{trail_id}")
def reembed_trail(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """对单个 trail 的所有 critique 照片重算 embedding。"""
    from ..services.embedding import embed_batch
    photos = store.list_photos(trail_id, user_id=user.id)
    targets = [p for p in photos if p.critique]
    if not targets:
        return {"trail_id": trail_id, "embedded": 0, "skipped": len(photos)}
    vecs = embed_batch([p.critique for p in targets])
    written = 0
    for p, v in zip(targets, vecs):
        if v:
            store.write_photo_embedding(p.photo_id, v)
            written += 1
    return {
        "trail_id": trail_id,
        "embedded": written,
        "skipped": len(photos) - written,
    }
