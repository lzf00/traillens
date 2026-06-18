"""轻量自实现 auth — 功能等价 Better Auth 核心(sign-up/in/session),无 Node.js 包依赖。

设计:
- bcrypt 密码哈希(开销 cost=12)
- session token 用 JWT HS256(BETTER_AUTH_SECRET / TRAILLENS_AUTH_SECRET)
- 30 天 expiry,内含 user_id + email + iat/exp
- 后端 deps.py 解 token 拿 user
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text as _text

from . import db

# ---- token / 密码 ---------------------------------------------------------

_SESSION_DAYS = int(os.environ.get("TRAILLENS_SESSION_DAYS", "30"))
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _secret() -> str:
    s = os.environ.get("TRAILLENS_AUTH_SECRET") or os.environ.get("BETTER_AUTH_SECRET")
    if not s:
        raise RuntimeError("TRAILLENS_AUTH_SECRET / BETTER_AUTH_SECRET 未配置")
    return s


def hash_password(plain: str) -> str:
    import bcrypt  # local import,避免 stub mode 装不上包时崩
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    import bcrypt
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def make_session_token(user_id: str, email: str) -> str:
    import jwt
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=_SESSION_DAYS)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def verify_session_token(token: str) -> dict | None:
    import jwt
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except Exception:  # noqa: BLE001 — InvalidToken/Expired/etc.
        return None


# ---- 用户表操作 -----------------------------------------------------------

def _normalize_email(email: str) -> str:
    return email.strip().lower()


def sign_up(email: str, password: str, name: str | None = None) -> dict:
    """返回 {user_id, email, name, plan, quota_remaining, token}。重名抛 ValueError。"""
    e = _normalize_email(email)
    if not _EMAIL_RE.match(e):
        raise ValueError("invalid_email")
    if len(password) < 6:
        raise ValueError("password_too_short")

    if not db.has_db():
        raise RuntimeError("db_unavailable")

    pw_hash = hash_password(password)
    sql = _text("""
        INSERT INTO users (email, password_hash, name)
        VALUES (:email, :pw, :name)
        RETURNING id, email, name, plan, quota_remaining
    """)
    try:
        with db.session() as s:
            row = s.execute(sql, dict(email=e, pw=pw_hash, name=name)).one()
    except Exception as ex:  # noqa: BLE001
        if "unique" in str(ex).lower() or "duplicate" in str(ex).lower():
            raise ValueError("email_already_exists") from ex
        raise
    uid = str(row.id)
    return {
        "user_id": uid,
        "email": row.email,
        "name": row.name,
        "plan": row.plan,
        "quota_remaining": row.quota_remaining,
        "token": make_session_token(uid, row.email),
    }


def sign_in(email: str, password: str) -> dict:
    """成功返回与 sign_up 同形;失败抛 ValueError。"""
    e = _normalize_email(email)
    if not db.has_db():
        raise RuntimeError("db_unavailable")
    sql = _text("""
        SELECT id, email, name, password_hash, plan, quota_remaining
        FROM users WHERE lower(email) = :email
    """)
    with db.session() as s:
        row = s.execute(sql, dict(email=e)).first()
    if not row or not verify_password(password, row.password_hash):
        raise ValueError("invalid_credentials")
    uid = str(row.id)
    return {
        "user_id": uid,
        "email": row.email,
        "name": row.name,
        "plan": row.plan,
        "quota_remaining": row.quota_remaining,
        "token": make_session_token(uid, row.email),
    }


def get_user(user_id: str) -> dict | None:
    if not db.has_db():
        return None
    sql = _text("""
        SELECT id, email, name, plan, quota_remaining
        FROM users WHERE id = :uid
    """)
    with db.session() as s:
        row = s.execute(sql, dict(uid=user_id)).first()
    if not row:
        return None
    return {
        "user_id": str(row.id),
        "email": row.email,
        "name": row.name,
        "plan": row.plan,
        "quota_remaining": row.quota_remaining,
    }
