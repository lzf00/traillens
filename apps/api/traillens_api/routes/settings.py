"""/v1/settings — 用户设置(API token / PIAA 偏好)。

Sprint 5 末:真正落库到 user_preferences 表;现在 stub 用 env / in-memory dict。
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import CurrentUser, get_current_user

router = APIRouter()


# in-memory(Sprint 5 替换)
_API_TOKENS: dict[str, list[dict]] = {}    # user_id → [{id, prefix, label, created_at}]
_TOKEN_SECRETS: dict[str, str] = {}        # token → user_id (反向查)


class TokenCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=80)


class TokenInfo(BaseModel):
    id: str
    label: str
    prefix: str   # 只回显前 8 位,完整 token 仅在创建时返回一次
    created_at: datetime


class TokenCreateResponse(TokenInfo):
    token: str   # 完整,仅此一次


@router.get("/tokens", response_model=list[TokenInfo])
def list_tokens(user: CurrentUser = Depends(get_current_user)) -> list[TokenInfo]:
    return [TokenInfo(**t) for t in _API_TOKENS.get(user.id, [])]


@router.post("/tokens", response_model=TokenCreateResponse, status_code=201)
def create_token(
    body: TokenCreate,
    user: CurrentUser = Depends(get_current_user),
) -> TokenCreateResponse:
    full = "tl_" + secrets.token_urlsafe(32)
    info = {
        "id": secrets.token_hex(8),
        "label": body.label,
        "prefix": full[:8],
        "created_at": datetime.now(timezone.utc),
    }
    _API_TOKENS.setdefault(user.id, []).append(info)
    _TOKEN_SECRETS[full] = user.id
    return TokenCreateResponse(token=full, **info)


@router.delete("/tokens/{token_id}", status_code=204)
def revoke_token(
    token_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    items = _API_TOKENS.get(user.id, [])
    new = [t for t in items if t["id"] != token_id]
    if len(new) == len(items):
        raise HTTPException(404, "token_not_found")
    _API_TOKENS[user.id] = new
    return None


# --------------------------------------------------------------------------- #
# PIAA 偏好(参考 PRODUCT_PLAN §3.1 M5 Memory-as-Preference)
# --------------------------------------------------------------------------- #
class PreferencesIn(BaseModel):
    favorite_focal_lengths: list[float] | None = None
    style_keywords: list[str] | None = None


_PREFS: dict[str, dict] = {}


@router.get("/preferences")
def get_preferences(user: CurrentUser = Depends(get_current_user)) -> dict:
    return _PREFS.get(user.id, {
        "favorite_focal_lengths": [],
        "style_keywords": [],
        "rejected_photo_ids": [],
        "piaa_sample_count": 0,
    })


@router.put("/preferences")
def update_preferences(
    body: PreferencesIn,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    current = _PREFS.get(user.id, {})
    for k, v in body.model_dump(exclude_none=True).items():
        current[k] = v
    _PREFS[user.id] = current
    return current
