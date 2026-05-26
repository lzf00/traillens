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
from ..services import store
from ..services.orchestrator import run_trail_stream

router = APIRouter()


@router.post("", response_model=TrailOut, status_code=201)
def create_trail(
    body: TrailCreate,
    user: CurrentUser = Depends(get_current_user),
) -> TrailOut:
    trail = store.create_trail(user_id=user.id, **body.model_dump())
    return trail


@router.get("/{trail_id}", response_model=TrailOut)
def get_trail(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> TrailOut:
    trail = store.get_trail(trail_id, user_id=user.id)
    if not trail:
        raise HTTPException(404, "trail_not_found")
    return trail


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
        run_trail_stream(trail_id, run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
