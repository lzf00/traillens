"""对象存储抽象 — 当前只实现 R2(S3 兼容)。

设计:
- presigned PUT URL → web 直传,绕开 api 带宽
- presigned GET URL → Lightroom 插件 / 公开分享页用
- 无 boto3 时降级到 stub URL,让 demo 不崩

为什么不直接用 boto3 全程:
- presign 是纯算法(HMAC-SHA256),不需要建立连接,所以可以独立实现
- 但 boto3 已经是 R2 推荐 client,装 sdk 后用 boto3 更稳
- 这里两条路径都准备:有 boto3 用 boto3;没有就用本地 hash 实现
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import os
import uuid
from typing import Literal
from urllib.parse import quote

from ..config import get_settings


def _config():
    s = get_settings()
    return {
        "endpoint": f"https://{os.environ.get('R2_ACCOUNT_ID', 'stub')}.r2.cloudflarestorage.com",
        "bucket": s.r2_bucket or "traillens-stub",
        "access_key": os.environ.get("R2_ACCESS_KEY_ID", ""),
        "secret_key": os.environ.get("R2_SECRET_ACCESS_KEY", ""),
        "public_base": s.r2_public_base,
        "region": "auto",  # R2 用 "auto"
    }


def make_object_key(*, user_id: str, trail_id: str, photo_id: str, ext: str = "jpg") -> str:
    """统一对象命名 — 按用户+trail+照片分层,便于 lifecycle / 配额。"""
    safe_ext = (ext or "jpg").lstrip(".").lower()[:5]
    return f"users/{user_id}/trails/{trail_id}/{photo_id}.{safe_ext}"


# --------------------------------------------------------------------------- #
# Presign — 优先 boto3,fallback 到本地 SigV4 实现
# --------------------------------------------------------------------------- #
def presign(
    op: Literal["put", "get"],
    key: str,
    *,
    expires: int = 3600,
    content_type: str | None = None,
) -> str | None:
    cfg = _config()
    if not (cfg["access_key"] and cfg["secret_key"]):
        return None  # 未配置 R2 → 返回 None,routes 走 stub 响应

    try:
        return _presign_boto3(op, key, cfg, expires=expires, content_type=content_type)
    except ImportError:
        return _presign_sigv4(op, key, cfg, expires=expires, content_type=content_type)


def _presign_boto3(op, key, cfg, *, expires, content_type):
    import boto3  # type: ignore
    from botocore.config import Config

    client = boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret_key"],
        region_name=cfg["region"],
        config=Config(signature_version="s3v4"),
    )
    params = {"Bucket": cfg["bucket"], "Key": key}
    if op == "put" and content_type:
        params["ContentType"] = content_type
    method = "put_object" if op == "put" else "get_object"
    return client.generate_presigned_url(method, Params=params, ExpiresIn=expires)


def _presign_sigv4(op, key, cfg, *, expires, content_type):
    """Self-contained AWS SigV4 query-string signing(boto3 不可用时的备份)。

    参考 AWS 官方 spec: https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-query-string-auth.html
    """
    now = _dt.datetime.now(_dt.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    method = "PUT" if op == "put" else "GET"
    host = cfg["endpoint"].replace("https://", "").replace("http://", "")
    canonical_uri = "/" + cfg["bucket"] + "/" + quote(key, safe="/")

    credential_scope = f"{date_stamp}/{cfg['region']}/s3/aws4_request"
    credential = f"{cfg['access_key']}/{credential_scope}"

    qs = {
        "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
        "X-Amz-Credential": credential,
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires),
        "X-Amz-SignedHeaders": "host",
    }
    canonical_qs = "&".join(f"{k}={quote(v, safe='')}" for k, v in sorted(qs.items()))
    canonical_headers = f"host:{host}\n"
    payload_hash = "UNSIGNED-PAYLOAD"
    canonical_request = "\n".join([method, canonical_uri, canonical_qs, canonical_headers, "host", payload_hash])

    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amz_date, credential_scope,
        hashlib.sha256(canonical_request.encode()).hexdigest(),
    ])

    def hmac_sha256(k, m):
        return hmac.new(k, m.encode(), hashlib.sha256).digest()

    k_date = hmac_sha256(("AWS4" + cfg["secret_key"]).encode(), date_stamp)
    k_region = hmac_sha256(k_date, cfg["region"])
    k_service = hmac_sha256(k_region, "s3")
    k_signing = hmac_sha256(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

    return f"{cfg['endpoint']}{canonical_uri}?{canonical_qs}&X-Amz-Signature={signature}"


def public_url(key: str) -> str | None:
    cfg = _config()
    if not cfg["public_base"]:
        return None
    return f"{cfg['public_base'].rstrip('/')}/{key}"
