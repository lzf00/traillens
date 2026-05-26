"""HTTP 请求/响应 schema(Pydantic v2)。

这些 schema 与 agents 包的 GraphState 不是同一组对象——
agent state 是图内部状态,这里是面向前端的契约。两者通过 services/orchestrator.py 翻译。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PhotoIn(BaseModel):
    """前端已经直传 R2 后,告诉后端 uri。"""

    uri: str
    exif: dict[str, Any] | None = None  # 可选,前端已用 traillens-exif 解析过


class PhotoBulkIn(BaseModel):
    photos: list[PhotoIn]


class PhotoOut(BaseModel):
    photo_id: str
    uri: str
    verdict: str | None = None
    reject_reason: str | None = None
    aesthetic: dict[str, Any] | None = None
    critique: str | None = None
    decision_trace: list[dict[str, Any]] = Field(default_factory=list)


class TrailCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    location_name: str | None = None
    gpx_uri: str | None = None


class TrailOut(BaseModel):
    id: str
    user_id: str
    name: str
    location_name: str | None = None
    gpx_uri: str | None = None
    travelogue_md: str | None = None
    next_trip_plan: dict[str, Any] | None = None
    photo_count: int = 0
    state_summary: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class TrailRunEvent(BaseModel):
    """SSE event payload。"""

    event: Literal[
        "orchestrator.routed",
        "culling.progress",
        "culling.photo_scored",
        "human_review.required",
        "critic.photo_critiqued",
        "story.delta",
        "planner.plan_ready",
        "run.finished",
        "run.error",
    ]
    data: dict[str, Any]
