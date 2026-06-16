"""/v1/trails routes。

注意:in-memory store 仅是 Sprint 4 骨架,Sprint 5 末替换为 Postgres + Alembic。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..deps import CurrentUser, check_quota, get_current_user
from ..schemas import (
    PhotoBulkIn,
    PhotoOut,
    TrailCreate,
    TrailOut,
)
from fastapi.responses import RedirectResponse

from ..services import storage, store
from ..services.orchestrator import run_trail_stream

router = APIRouter()


@router.post("", response_model=TrailOut, status_code=201)
def create_trail(
    body: TrailCreate,
    user: CurrentUser = Depends(get_current_user),
) -> TrailOut:
    trail = store.create_trail(user_id=user.id, **body.model_dump())
    return trail


@router.get("", response_model=list[TrailOut])
def list_trails(
    limit: int = 50,
    user: CurrentUser = Depends(get_current_user),
) -> list[TrailOut]:
    return store.list_trails(user_id=user.id, limit=limit)


@router.get("/{trail_id}", response_model=TrailOut)
def get_trail(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> TrailOut:
    trail = store.get_trail(trail_id, user_id=user.id)
    if not trail:
        raise HTTPException(404, "trail_not_found")
    return trail


@router.post("/{trail_id}/photos:presign", status_code=200)
def presign_uploads(
    trail_id: str,
    body: dict,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """前端按"我准备上传 N 张照片"调一次,拿回 N 个 PUT URL → 并行直传 R2。

    body = {"files": [{"filename": "a.jpg", "content_type": "image/jpeg"}, ...]}
    """
    trail = store.get_trail(trail_id, user_id=user.id)
    if not trail:
        raise HTTPException(404, "trail_not_found")
    files = body.get("files") or []
    check_quota(user, requested=len(files))

    out = []
    for f in files:
        ext = (f.get("filename", "")).rsplit(".", 1)[-1] if "." in f.get("filename", "") else "jpg"
        photo_id = str(uuid.uuid4())
        key = storage.make_object_key(
            user_id=user.id, trail_id=trail_id, photo_id=photo_id, ext=ext,
        )
        url = storage.presign("put", key,
                              expires=3600,
                              content_type=f.get("content_type", "image/jpeg"))
        out.append({
            "photo_id": photo_id,
            "key": key,
            "put_url": url,        # None 时前端 fallback 走 :bulk + base64
            "public_url": storage.public_url(key),
        })
    return {"uploads": out, "expires_in": 3600}


@router.post("/{trail_id}/photos:bulk", status_code=202)
def add_photos(
    trail_id: str,
    body: PhotoBulkIn,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    check_quota(user, requested=len(body.photos))
    n = store.add_photos(trail_id, user_id=user.id, photos=body.photos)
    return {"accepted": n, "trail_id": trail_id}


@router.get("/{trail_id}/photos", response_model=list[PhotoOut])
def list_photos(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> list[PhotoOut]:
    return store.list_photos(trail_id, user_id=user.id)


@router.get("/{trail_id}/photos/{photo_id}", response_model=PhotoOut)
def get_photo(
    trail_id: str,
    photo_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> PhotoOut:
    """单张照片详情 — 含完整 decision_trace,前端时间线组件用。"""
    photos = store.list_photos(trail_id, user_id=user.id)
    for p in photos:
        if p.photo_id == photo_id:
            return p
    raise HTTPException(404, "photo_not_found")


@router.post("/{trail_id}/run")
def run_trail(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """触发 agent 跑。SSE 流式返回。

    每行格式: `event: <name>\\ndata: <json>\\n\\n` (W3C SSE)。
    """
    trail = store.get_trail(trail_id, user_id=user.id)
    if not trail:
        raise HTTPException(404, "trail_not_found")
    run_id = str(uuid.uuid4())
    return StreamingResponse(
        run_trail_stream(trail_id, run_id, user_id=user.id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
