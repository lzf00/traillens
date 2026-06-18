"""/v1/library — 跨 trail 的搜索。

当前(MVP):走 PG ILIKE 三路 OR 匹配
  · photos.critique (AI 点评)
  · trails.name + trails.location_name
  · trails.travelogue_md (游记)
得分=命中字段数/3,粗排但比 stub 实用。

Sprint 5 末:接 pgvector + Doubao/BGE-M3 embedding 做真语义。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text

from ..deps import CurrentUser, get_current_user
from ..services import db, store

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


@router.post("/embed/{trail_id}")
def reembed_trail(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Sprint 5 末:接 BGE-M3 / Doubao Embedding,写 photos.embedding 列。"""
    photos = store.list_photos(trail_id, user_id=user.id)
    return {"trail_id": trail_id, "queued": len(photos), "status": "pending_embedding_model"}
