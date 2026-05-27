"""/v1/library — 跨 trail 的语义搜索 + 标签 / 时间筛选。

Sprint 5 末:用 pgvector 真实查询;当前 stub 走 in-memory store + 简单关键词。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..deps import CurrentUser, get_current_user
from ..services import store

router = APIRouter()


class SearchResult(BaseModel):
    photo_id: str
    trail_id: str
    trail_name: str
    uri: str
    score: float  # 相似度 0-1


@router.get("/search", response_model=list[SearchResult])
def search(
    q: str = Query(..., min_length=1, description="自然语言查询,如:川西秋天逆光人像"),
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
) -> list[SearchResult]:
    """语义搜索用户照片。

    Sprint 5 接 pgvector:
      1. 把 q 用 BGE-M3 / SigLIP-text 转 embedding(768d)
      2. SELECT ... ORDER BY embedding <=> :q_vec LIMIT N
      3. 按 trail + verdict=keep 过滤

    当前 stub:返回 user 名下所有 trail 的 keep 照片,按 trail name 含 q 排序。
    """
    # TODO Sprint 5: 真实 pgvector 查询
    out: list[SearchResult] = []
    # in-memory store 没暴露 list_user_trails;这里给个最小可工作版本
    return out


@router.post("/embed/{trail_id}")
def reembed_trail(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """触发对单 trail 所有照片重新生成 embedding。

    Sprint 5 末:从 R2 拉图 → BGE-M3 / SigLIP 编码 → 写 photos.embedding 列。
    当前 stub:返回排队信息。
    """
    photos = store.list_photos(trail_id, user_id=user.id)
    return {"trail_id": trail_id, "queued": len(photos), "status": "stub"}
