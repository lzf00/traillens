"""导出 trail 数据(JSON / 小红书 / 微信图文)。

- /v1/trails/{id}/export/json    完整 trail + photos JSON 备份
- /v1/trails/{id}/export/xhs     小红书图文(9 图 URL + 文案 markdown)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import CurrentUser, get_current_user
from ..services import store

router = APIRouter()


@router.get("/{trail_id}/export/json")
def export_json(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """完整 trail + photos JSON 备份(用户备份用)。"""
    trail = store.get_trail(trail_id, user_id=user.id)
    if not trail:
        raise HTTPException(404, "trail_not_found")
    photos = store.list_photos(trail_id, user_id=user.id)
    return {
        "version": "1.0",
        "trail": trail.model_dump(),
        "photos": [p.model_dump() for p in photos],
    }


@router.get("/{trail_id}/export/xhs")
def export_xhs(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """小红书图文格式:取最多 9 张 keep 照片(按分数倒序) + 自动文案。

    返回 {images: [9 个 URL], caption: markdown, hashtags: [...]}.
    """
    trail = store.get_trail(trail_id, user_id=user.id)
    if not trail:
        raise HTTPException(404, "trail_not_found")
    photos = store.list_photos(trail_id, user_id=user.id)

    # 优先 keep,按 overall 倒序;不够 9 张就补 review;最多 9
    keep = sorted(
        [p for p in photos if p.verdict == "keep"],
        key=lambda p: (p.aesthetic or {}).get("overall", 0),
        reverse=True,
    )
    extras = [p for p in photos if p.verdict == "review"]
    selected = (keep + extras)[:9]
    images = [p.uri for p in selected]

    avg = sum((p.aesthetic or {}).get("overall", 0) for p in selected) / max(1, len(selected))
    location = trail.location_name or "未知地点"

    # 文案模板(小红书风格:emoji + 短句 + tag)
    lines = [
        f"📍 {location}",
        "",
        f"📷 {trail.name}",
        "",
    ]
    if trail.travelogue_md:
        lines.append(trail.travelogue_md.strip()[:300])
        lines.append("")
    lines.extend([
        f"✨ AI 选片 · {len(selected)} 张精选 · 综合分 {avg:.1f}/10",
        "",
        "由 TrailLens 自动整理 · 多智能体选片 + AI 点评 + 游记生成",
        "",
        "#徒步 #风光摄影 #AI选片 #TrailLens",
    ])

    return {
        "images": images,
        "image_count": len(images),
        "caption": "\n".join(lines),
        "hashtags": ["徒步", "风光摄影", "AI选片", "TrailLens", location.split()[0] if location.split() else ""],
        "trail_id": trail_id,
        "trail_name": trail.name,
    }
