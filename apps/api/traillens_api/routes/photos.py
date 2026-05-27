"""/v1/photos — 跨 trail 的照片操作。

主要供:
  - Lightroom 插件下载选片到本地 catalog
  - 公开分享页拿单图(无 auth,签名 URL 鉴权)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from ..deps import CurrentUser, get_current_user
from ..services import storage, store

router = APIRouter()


@router.get("/{photo_id}/download")
def download_photo(
    photo_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> RedirectResponse:
    """302 到 R2 presigned URL — 客户端直接从 R2 拉,省 api 带宽。"""
    # TODO Sprint 5: store 加 get_photo_by_id 直接按 id 查;
    # 当前 in-memory 模式 store 按 trail 索引,这里先 demo
    # 用 stub 返回 placeholder
    key = storage.make_object_key(
        user_id=user.id, trail_id="unknown", photo_id=photo_id, ext="jpg",
    )
    url = storage.presign("get", key, expires=900)
    if not url:
        # R2 未配 → 给 placeholder 占位图(让 LR 插件不崩)
        raise HTTPException(503, {"error": "storage_not_configured"})
    return RedirectResponse(url, status_code=302)
