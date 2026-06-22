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
    # 优先级:腾讯云 COS(国内首选) > 七牛云 > R2(海外) > None
    if os.environ.get("COS_SECRET_ID") and os.environ.get("COS_SECRET_KEY"):
        return _presign_cos(op, key, expires=expires, content_type=content_type)

    if os.environ.get("QINIU_ACCESS_KEY") and os.environ.get("QINIU_SECRET_KEY"):
        return _presign_qiniu(op, key, expires=expires)

    cfg = _config()
    if not (cfg["access_key"] and cfg["secret_key"]):
        return None  # 未配置 → 返回 None,routes 走 stub 响应

    try:
        return _presign_boto3(op, key, cfg, expires=expires, content_type=content_type)
    except ImportError:
        return _presign_sigv4(op, key, cfg, expires=expires, content_type=content_type)


# --------------------------------------------------------------------------- #
# 腾讯云 COS — 国内首选
# --------------------------------------------------------------------------- #
def _presign_cos(op: str, key: str, *, expires: int, content_type: str | None = None) -> str | None:
    """腾讯云 COS 签名 URL。

    必填 env:
      COS_SECRET_ID, COS_SECRET_KEY, COS_BUCKET, COS_REGION
    可选 env:
      COS_DOMAIN — bucket 绑的 CDN/自定义域(默认用 cos.<region>.myqcloud.com)
    """
    secret_id = os.environ["COS_SECRET_ID"]
    secret_key = os.environ["COS_SECRET_KEY"]
    bucket = os.environ["COS_BUCKET"]      # 形如 traillens-photos-1305566123 (含 appid)
    region = os.environ.get("COS_REGION", "ap-shanghai")

    # 优先用官方 SDK(签名规则比 S3 SigV4 严格)
    try:
        from qcloud_cos import CosConfig, CosS3Client  # type: ignore
    except ImportError:
        return _presign_cos_fallback(op, key, secret_id, secret_key, bucket, region, expires)

    cfg = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    client = CosS3Client(cfg)
    method = "PUT" if op == "put" else "GET"
    headers = {"Content-Type": content_type} if (op == "put" and content_type) else {}
    return client.get_presigned_url(
        Bucket=bucket, Key=key, Method=method,
        Expired=expires, Headers=headers,
    )


def _presign_cos_fallback(op, key, secret_id, secret_key, bucket, region, expires):
    """无 cos SDK 时:腾讯云 COS 支持 S3 兼容协议,用 SigV4 也能签。

    与 R2/OSS 一样的代码路径,只需重组 endpoint。
    """
    cfg = {
        "endpoint": f"https://{bucket}.cos.{region}.myqcloud.com",
        "bucket": "",   # COS 的 S3 endpoint 把 bucket 嵌入了 host,canonical_uri 直接 /<key>
        "access_key": secret_id,
        "secret_key": secret_key,
        "region": region,
    }
    return _presign_sigv4_cos(op, key, cfg, expires=expires)


def _presign_sigv4_cos(op, key, cfg, *, expires):
    """COS-specialized SigV4 — host 已含 bucket,canonical_uri 只放 /<key>。"""
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    method = "PUT" if op == "put" else "GET"
    host = cfg["endpoint"].replace("https://", "").replace("http://", "")
    canonical_uri = "/" + quote(key, safe="/")

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

    def _hmac(k, m):
        return hmac.new(k, m.encode(), hashlib.sha256).digest()

    k_date = _hmac(("AWS4" + cfg["secret_key"]).encode(), date_stamp)
    k_region = _hmac(k_date, cfg["region"])
    k_service = _hmac(k_region, "s3")
    k_signing = _hmac(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
    return f"{cfg['endpoint']}{canonical_uri}?{canonical_qs}&X-Amz-Signature={signature}"


# --------------------------------------------------------------------------- #
# 七牛云 Kodo
# --------------------------------------------------------------------------- #
def _presign_qiniu(op: str, key: str, *, expires: int) -> str | None:
    """七牛云对象存储 — PUT 返回上传 token+URL,GET 返回签名下载 URL。"""
    ak = os.environ.get("QINIU_ACCESS_KEY", "")
    sk = os.environ.get("QINIU_SECRET_KEY", "")
    bucket = os.environ.get("QINIU_BUCKET", "")
    domain = os.environ.get("QINIU_DOMAIN", "")  # bucket 绑定的 CDN/源站域名

    try:
        from qiniu import Auth  # type: ignore
    except ImportError:
        return _presign_qiniu_fallback(op, key, ak, sk, domain, expires)

    q = Auth(ak, sk)
    if op == "put":
        # 七牛上传协议:客户端拿 token POST 到 up-z*.qiniup.com
        # 返回带 token 的占位 URL,前端 SDK 用 token 走 multipart POST
        token = q.upload_token(bucket, key=key, expires=expires)
        return f"https://up-z0.qiniup.com?token={token}&key={key}"
    # GET:私有空间签名 URL
    if not domain:
        return None
    base_url = f"https://{domain}/{key}"
    return q.private_download_url(base_url, expires=expires)


def _presign_qiniu_fallback(op, key, ak, sk, domain, expires):
    """无 qiniu SDK 时手撸下载签名 — 上传留给 SDK。"""
    if op != "get" or not domain:
        return None
    import base64, hashlib, hmac, time
    deadline = int(time.time()) + expires
    base = f"https://{domain}/{key}?e={deadline}"
    sign = hmac.new(sk.encode(), base.encode(), hashlib.sha1).digest()
    encoded = base64.urlsafe_b64encode(sign).decode()
    return f"{base}&token={ak}:{encoded}"


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


def delete_object_by_uri(uri: str) -> bool:
    """根据 public URL 反查 key 后删 COS 对象。失败静默返回 False。"""
    if not (uri and os.environ.get("COS_SECRET_ID") and os.environ.get("COS_SECRET_KEY")):
        return False
    # 形如 https://traillens-photos-xxx.cos.ap-shanghai.myqcloud.com/users/.../xxx.jpg
    try:
        path = uri.split("//", 1)[1].split("/", 1)[1] if "//" in uri else None
    except IndexError:
        return False
    if not path:
        return False
    try:
        from qcloud_cos import CosConfig, CosS3Client  # type: ignore
        cfg = CosConfig(
            Region=os.environ.get("COS_REGION", "ap-shanghai"),
            SecretId=os.environ["COS_SECRET_ID"],
            SecretKey=os.environ["COS_SECRET_KEY"],
        )
        CosS3Client(cfg).delete_object(Bucket=os.environ["COS_BUCKET"], Key=path)
        return True
    except Exception:  # noqa: BLE001
        return False


def make_thumbnail(data: bytes, max_side: int = 300) -> bytes | None:
    """生成最长边 max_side px 的 JPEG 缩略图;失败返 None。"""
    try:
        from PIL import Image  # type: ignore
        import io
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB") if img.mode != "RGB" else img
        w, h = img.size
        if max(w, h) > max_side:
            if w >= h:
                img = img.resize((max_side, int(h * max_side / w)), Image.LANCZOS)
            else:
                img = img.resize((int(w * max_side / h), max_side), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80, optimize=True)
        return buf.getvalue()
    except Exception:  # noqa: BLE001
        return None


def put_object(key: str, data: bytes, content_type: str = "image/jpeg") -> str | None:
    """服务端代理上传(浏览器走不通 COS CORS 时的 fallback)。

    成功 → 返回 public_url；
    未配置存储后端 → 返回 None,routes 应当报 503。
    """
    if os.environ.get("COS_SECRET_ID") and os.environ.get("COS_SECRET_KEY"):
        try:
            from qcloud_cos import CosConfig, CosS3Client  # type: ignore
        except ImportError:
            return None
        cfg = CosConfig(
            Region=os.environ.get("COS_REGION", "ap-shanghai"),
            SecretId=os.environ["COS_SECRET_ID"],
            SecretKey=os.environ["COS_SECRET_KEY"],
        )
        client = CosS3Client(cfg)
        client.put_object(
            Bucket=os.environ["COS_BUCKET"],
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return public_url(key)
    return None


def public_url(key: str) -> str | None:
    """优先级:COS_DOMAIN > QINIU_DOMAIN > R2_PUBLIC_BASE。"""

    def _strip_proto(d: str) -> str:
        for prefix in ("https://", "http://"):
            if d.startswith(prefix):
                return d[len(prefix):]
        return d

    # 1) 腾讯云 COS
    cos_domain = os.environ.get("COS_DOMAIN")
    if cos_domain:
        return f"https://{_strip_proto(cos_domain).rstrip('/')}/{key}"
    # 默认 COS host(无自定义域时)
    if os.environ.get("COS_BUCKET") and os.environ.get("COS_REGION"):
        return f"https://{os.environ['COS_BUCKET']}.cos.{os.environ['COS_REGION']}.myqcloud.com/{key}"

    # 2) 七牛云
    qiniu_domain = os.environ.get("QINIU_DOMAIN")
    if qiniu_domain:
        return f"https://{_strip_proto(qiniu_domain).rstrip('/')}/{key}"

    # 3) S3 兼容
    cfg = _config()
    if not cfg["public_base"]:
        return None
    return f"{cfg['public_base'].rstrip('/')}/{key}"
