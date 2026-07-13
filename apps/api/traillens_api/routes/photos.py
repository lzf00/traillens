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
    """302 到 COS presigned URL — 客户端直接从 COS 拉,省 api 带宽。

    强制 owner 校验:JOIN photos+trails 确认 photo 属于 user,否则 404
    (不返 403,避免枚举 photo_id 的攻击)。
    """
    info = store.get_photo_owned(photo_id, user_id=user.id)
    if not info:
        raise HTTPException(404, "photo_not_found")
    key = storage.make_object_key(
        user_id=user.id, trail_id=info["trail_id"], photo_id=photo_id, ext=info["ext"],
    )
    url = storage.presign("get", key, expires=900)
    if not url:
        raise HTTPException(503, {"error": "storage_not_configured"})
    return RedirectResponse(url, status_code=302)
