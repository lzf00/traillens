"""/v1/trails routes。

注意:in-memory store 仅是 Sprint 4 骨架,Sprint 5 末替换为 Postgres + Alembic。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

import os as _os

# 上传大小上限:单张 50MB、单批总量 200MB(env 可配)
# 攻击者可用巨图打爆内存 → 每张 read 完立刻 len(data) 校验,超限即拒
MAX_UPLOAD_BYTES = int(_os.environ.get("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
MAX_BATCH_BYTES = int(_os.environ.get("MAX_BATCH_BYTES", str(200 * 1024 * 1024)))
# MIME 白名单:magic-bytes 校验(防 content_type 伪造)
_MAGIC = {
    b"\xff\xd8\xff":       "image/jpeg",
    b"\x89PNG\r\n\x1a\n":  "image/png",
    b"RIFF":               "image/webp",   # 前 4 字节;完整还要 offset 8 = WEBP
    b"GIF87a":             "image/gif",
    b"GIF89a":             "image/gif",
}


def _sniff_mime(data: bytes) -> str | None:
    for magic, mime in _MAGIC.items():
        if data.startswith(magic):
            if mime == "image/webp" and data[8:12] != b"WEBP":
                continue
            return mime
    return None


async def _read_bounded(f: UploadFile, per_file_max: int = MAX_UPLOAD_BYTES) -> bytes:
    """安全 read:超过 per_file_max 立刻抛 413。"""
    data = await f.read()
    if len(data) > per_file_max:
        raise HTTPException(413, {
            "error": "file_too_large",
            "filename": f.filename,
            "size": len(data),
            "max": per_file_max,
        })
    return data

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
from ..services.store_protocol import default_store

router = APIRouter()


@router.post("", response_model=TrailOut, status_code=201)
def create_trail(
    body: TrailCreate,
    user: CurrentUser = Depends(get_current_user),
) -> TrailOut:
    # 走 protocol 层,底层仍是 store.create_trail
    return default_store().create_resource(user_id=user.id, **body.model_dump())


@router.get("", response_model=list[TrailOut])
def list_trails(
    limit: int = 50,
    user: CurrentUser = Depends(get_current_user),
) -> list[TrailOut]:
    return default_store().list_resources(user_id=user.id, limit=limit)


@router.get("/_health")
def trails_health(user: CurrentUser = Depends(get_current_user)) -> dict:
    """逐 trail 健康度:photo 数 / scored / critique / embedding 完整度。

    Settings 面板用,一眼看出哪些 trail 还没跑过 Run 或缺 embedding。
    """
    from sqlalchemy import text as _text
    from ..services import db as _db
    if not _db.has_db():
        return {"trails": []}
    sql = _text("""
        SELECT t.id, t.name,
               COUNT(p.id) AS total,
               SUM(CASE WHEN p.verdict IS NOT NULL THEN 1 ELSE 0 END) AS scored,
               SUM(CASE WHEN p.verdict = 'keep' THEN 1 ELSE 0 END) AS keeps,
               SUM(CASE WHEN p.critique IS NOT NULL THEN 1 ELSE 0 END) AS critiqued,
               SUM(CASE WHEN p.embedding IS NOT NULL THEN 1 ELSE 0 END) AS embedded
        FROM trails t
        LEFT JOIN photos p ON p.trail_id = t.id
        WHERE t.user_id = :uid
        GROUP BY t.id, t.name
        ORDER BY t.updated_at DESC
    """)
    with _db.session() as s:
        rows = s.execute(sql, dict(uid=user.id)).all()
    return {
        "trails": [
            {
                "id": str(r.id),
                "name": r.name,
                "total": int(r.total or 0),
                "scored": int(r.scored or 0),
                "keeps": int(r.keeps or 0),
                "critiqued": int(r.critiqued or 0),
                "embedded": int(r.embedded or 0),
            }
            for r in rows
        ],
    }


@router.get("/{trail_id}", response_model=TrailOut)
def get_trail(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> TrailOut:
    trail = default_store().get_resource(trail_id, user_id=user.id)
    if not trail:
        raise HTTPException(404, "trail_not_found")
    return trail


@router.get("/_demo/public", response_model=TrailOut)
def get_demo_trail() -> TrailOut:
    """自动选一个有照片 + travelogue 的 trail 作为 demo;否则取最新一条。

    /trails/demo 页面调它,跳过去看 share 页。不用 hardcode trail_id。
    """
    trail = store.pick_demo_trail()
    if not trail:
        raise HTTPException(404, "no_public_trail")
    return trail


@router.get("/{trail_id}/public", response_model=TrailOut)
def get_trail_public(trail_id: str) -> TrailOut:
    """无需登录的公开 trail 读取(分享页用)。"""
    trail = store.get_trail_public(trail_id)
    if not trail:
        raise HTTPException(404, "trail_not_found")
    return trail


@router.get("/{trail_id}/photos/public", response_model=list[PhotoOut])
def list_photos_public(trail_id: str) -> list[PhotoOut]:
    return store.list_photos_public(trail_id)


@router.patch("/{trail_id}", response_model=TrailOut)
def update_trail(
    trail_id: str,
    body: dict,
    user: CurrentUser = Depends(get_current_user),
) -> TrailOut:
    """编辑 trail name / location / travelogue_md / next_trip_plan(任一字段可选)。"""
    trail = store.update_trail(
        trail_id, user_id=user.id,
        name=body.get("name"),
        location_name=body.get("location_name"),
        travelogue_md=body.get("travelogue_md"),
        next_trip_plan=body.get("next_trip_plan"),
    )
    if not trail:
        raise HTTPException(404, "trail_not_found")
    return trail


@router.patch("/{trail_id}/photos/{photo_id}")
def update_photo(
    trail_id: str,
    photo_id: str,
    body: dict,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """改单张照片 verdict / aesthetic / critique(手动 override AI)。"""
    ok = store.update_photo(
        trail_id, photo_id, user_id=user.id,
        verdict=body.get("verdict"),
        aesthetic=body.get("aesthetic"),
        critique=body.get("critique"),
    )
    if not ok:
        raise HTTPException(404, "photo_not_found")
    return {"ok": True}


@router.delete("/{trail_id}/photos/{photo_id}", status_code=204)
def delete_photo(
    trail_id: str,
    photo_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """删单张照片(原图 + 缩略图同步清 COS)。"""
    uris = store.delete_photo(trail_id, photo_id, user_id=user.id)
    if not uris:
        raise HTTPException(404, "photo_not_found")
    for uri in uris:
        storage.delete_object_by_uri(uri)
    return None


@router.delete("/{trail_id}", status_code=204)
def delete_trail(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """删除 trail + 所有照片(DB 级联)+ COS 对象(best-effort)。"""
    trail = store.get_trail(trail_id, user_id=user.id)
    if not trail:
        raise HTTPException(404, "trail_not_found")
    uris = store.delete_trail(trail_id, user_id=user.id)
    for uri in uris:
        storage.delete_object_by_uri(uri)
    return None


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


@router.post("/{trail_id}/stack:preview", status_code=200)
async def stack_preview(
    trail_id: str,
    files: list[UploadFile] = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    """Direction B (Stargazer) PoC:N 张 multipart → median 堆栈 → 返回 jpg。

    不入库,纯 stateless 预览。前端用 blob URL 显示。
    """
    from fastapi.responses import Response
    from ..services.stacker import stack_median
    if len(files) < 2:
        raise HTTPException(400, "need at least 2 photos to stack")
    if len(files) > 200:
        raise HTTPException(400, "max 200 photos per stack(超过分两次跑)")

    # 逐张 read 然后 stack;~200 张 6MP * 4 bytes = 5GB,够堆栈中等机型。
    # 真生产改 background task + 增量写。
    blobs = []
    total = 0
    for f in files:
        data = await _read_bounded(f)
        total += len(data)
        if total > MAX_BATCH_BYTES:
            raise HTTPException(413, {"error": "batch_too_large", "max": MAX_BATCH_BYTES})
        if data:
            blobs.append(data)
    result = stack_median(blobs)
    if not result:
        raise HTTPException(500, "stack failed (OpenCV missing or all decode failed)")
    # 用 critic 节点给成品打分,分数塞 response header 前端展示
    from ..services.stacker import critic_stack
    metrics = critic_stack(result)
    return Response(content=result, media_type="image/jpeg",
                    headers={
                        "X-Stack-Frames": str(len(blobs)),
                        "X-Stack-Overall": str(metrics.get("overall") or ""),
                        "X-Stack-SNR-dB": str(metrics.get("snr_db") or ""),
                        "X-Stack-Star-Roundness": str(metrics.get("star_roundness") or ""),
                        "Access-Control-Expose-Headers": "X-Stack-Frames,X-Stack-Overall,X-Stack-SNR-dB,X-Stack-Star-Roundness",
                        "Cache-Control": "no-store",
                    })


@router.post("/{trail_id}/stack:triage")
async def stack_triage(
    trail_id: str,
    files: list[UploadFile] = File(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Direction B: 逐张 frame-triage 分档,不合成,不落库。

    返回每张的 verdict/blur/exposure 指标,前端展示 keep/reject 列表 → 用户
    再决定送哪些进 :preview 合成。
    """
    from ..services.stacker import triage_frame
    if len(files) < 1:
        raise HTTPException(400, "need >=1 photo")
    if len(files) > 200:
        raise HTTPException(400, "max 200 per triage")

    out = []
    total = 0
    for f in files:
        data = await _read_bounded(f)
        total += len(data)
        if total > MAX_BATCH_BYTES:
            raise HTTPException(413, {"error": "batch_too_large", "max": MAX_BATCH_BYTES})
        r = triage_frame(data) if data else {"verdict": "reject", "reason": "empty"}
        r["filename"] = f.filename
        r["size"] = len(data)
        out.append(r)
    keeps = sum(1 for r in out if r["verdict"] == "keep")
    return {
        "total": len(out),
        "keeps": keeps,
        "rejects": len(out) - keeps,
        "frames": out,
    }


@router.post("/{trail_id}/photos:upload", status_code=202)
async def upload_photos(
    trail_id: str,
    files: list[UploadFile] = File(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """服务端代理上传 fallback。

    用于浏览器走不通 COS CORS 的环境(MVP 期默认走这条)。
    后端拿到 multipart 后直接 put_object → 写入 trails.photos 表。
    """
    trail = store.get_trail(trail_id, user_id=user.id)
    if not trail:
        raise HTTPException(404, "trail_not_found")
    check_quota(user, requested=len(files))

    from ..schemas import PhotoIn
    from ..services.exif import extract_exif_from_bytes

    photos: list[PhotoIn] = []
    failed = []
    total = 0
    for f in files:
        data = await _read_bounded(f)
        total += len(data)
        if total > MAX_BATCH_BYTES:
            raise HTTPException(413, {"error": "batch_too_large", "max": MAX_BATCH_BYTES})
        # magic-bytes 校验:不认可扩展名/content_type
        sniffed = _sniff_mime(data)
        if not sniffed:
            failed.append(f.filename)
            continue
        # ext 用 sniffed MIME 决定,防路径伪造
        ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}.get(sniffed, "jpg")
        photo_id = str(uuid.uuid4())
        key = storage.make_object_key(
            user_id=user.id, trail_id=trail_id, photo_id=photo_id, ext=ext,
        )
        uri = storage.put_object(key, data, content_type=sniffed)
        if not uri:
            failed.append(f.filename)
            continue
        # 上传时一次性解析 EXIF 入库,Run 时不需要再下载 COS
        exif = extract_exif_from_bytes(data)
        # 同步生成 300px 缩略图(失败不阻断上传)
        thumb_uri = None
        thumb_bytes = storage.make_thumbnail(data, max_side=300)
        if thumb_bytes:
            thumb_key = key.rsplit(".", 1)[0] + "_thumb.jpg"
            thumb_uri = storage.put_object(thumb_key, thumb_bytes, content_type="image/jpeg")
        photos.append(PhotoIn(uri=uri, thumb_uri=thumb_uri, exif=exif or None))

    accepted = store.add_photos(trail_id, user_id=user.id, photos=photos)
    return {
        "accepted": accepted,
        "failed": failed,
        "trail_id": trail_id,
    }


@router.get("/{trail_id}/photos", response_model=list[PhotoOut])
def list_photos(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> list[PhotoOut]:
    return store.list_photos(trail_id, user_id=user.id)


@router.get("/{trail_id}/download/keeps.zip")
def download_keeps_zip(
    trail_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """下载该 trail 所有 verdict=keep 的原图 zip(stream,避免大内存)。"""
    import io
    import zipfile
    import urllib.request
    from fastapi.responses import StreamingResponse

    trail = store.get_trail(trail_id, user_id=user.id)
    if not trail:
        raise HTTPException(404, "trail_not_found")
    photos = [p for p in store.list_photos(trail_id, user_id=user.id) if p.verdict == "keep"]
    if not photos:
        raise HTTPException(404, "no_keep_photos")

    def gen():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
            for i, p in enumerate(photos, 1):
                try:
                    with urllib.request.urlopen(p.uri, timeout=20) as r:
                        data = r.read()
                except Exception:
                    continue
                ext = (p.uri.rsplit(".", 1)[-1] or "jpg").lower()[:5]
                # 文件名按打分排序前缀,方便用户选片
                overall = (p.aesthetic or {}).get("overall") if isinstance(p.aesthetic, dict) else None
                score = f"{overall:.1f}_" if isinstance(overall, (int, float)) else ""
                zf.writestr(f"{score}{i:03d}_{p.photo_id[:8]}.{ext}", data)
        buf.seek(0)
        yield buf.read()

    # Content-Disposition header 必须 latin-1;中文 trail name 用 RFC 5987 编码
    from urllib.parse import quote
    ascii_fb = "".join(c for c in trail.name if c.isascii() and (c.isalnum() or c in "-_")) or "trail"
    utf8_q = quote(f"{trail.name}_keeps.zip", safe="")
    return StreamingResponse(
        gen(),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_fb}_keeps.zip"; '
                f"filename*=UTF-8''{utf8_q}"
            )
        },
    )


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
