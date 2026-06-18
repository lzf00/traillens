"""依赖注入(单测可替换)。

Auth 策略:
  - 与 apps/web 用 Better-Auth(决策 D6)
  - web 前端登录后,session token 写到 cookie + 也以 Bearer 传 API
  - 这里两条路径都接受:cookie("better-auth.session") 或 Authorization: Bearer ...
  - Sprint 5 末:接真实的 Better-Auth secret 验签

Test override(在 conftest 或 test_*.py):
    app.dependency_overrides[get_current_user] = lambda: FakeUser(...)
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request


@dataclass
class CurrentUser:
    id: str
    email: str
    plan: str = "free"  # free / pro / pro_plus
    quota_remaining: int = 50


def _dev_user(request: Request | None = None) -> CurrentUser:
    """开发期默认用户。允许用 X-Dev-User-Id 头覆盖,便于多用户场景测试。"""
    user_id = os.environ.get("DEV_USER_ID", "dev-user-001")
    if request is not None:
        user_id = request.headers.get("X-Dev-User-Id", user_id)
    return CurrentUser(
        id=user_id,
        email=os.environ.get("DEV_USER_EMAIL", "dev@traillens.local"),
        plan=os.environ.get("DEV_USER_PLAN", "free"),
        quota_remaining=int(os.environ.get("DEV_USER_QUOTA", "50")),
    )


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    """优先验 traillens_session(JWT cookie / Bearer);
    无 token 且 env=local → dev_user fallback(X-Dev-User-Id 仍可用,便于本地测试)。
    """
    env = os.environ.get("TRAILLENS_ENV", "local")

    # ---- 真 session token ----
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    else:
        token = request.cookies.get("traillens_session")

    if token:
        try:
            from .services import auth as _auth_svc
            payload = _auth_svc.verify_session_token(token)
        except Exception:  # noqa: BLE001 — secret 缺 / lib 缺装
            payload = None
        if payload:
            info = _auth_svc.get_user(payload["sub"])
            if info:
                return CurrentUser(
                    id=info["user_id"],
                    email=info["email"],
                    plan=info["plan"],
                    quota_remaining=info["quota_remaining"],
                )
        # token 存在但无效 → prod 直接 401;local 继续 fallback
        if env == "prod":
            raise HTTPException(401, "invalid_session")

    if env == "local":
        return _dev_user(request)

    raise HTTPException(401, "missing_session")


def check_quota(user: CurrentUser, requested: int) -> None:
    """超额时按 PRODUCT_PLAN §5.2:不 hard reject,降级队列。

    这里 stub:仅当远超时抛 429;真实实现写入 Redis 计数 + 触发降级。
    """
    from fastapi import HTTPException

    if requested > user.quota_remaining * 2:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "quota_exceeded",
                "remaining": user.quota_remaining,
                "requested": requested,
                "upgrade_url": "/app/billing/upgrade",
            },
        )
