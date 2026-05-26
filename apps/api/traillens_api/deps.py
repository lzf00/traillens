"""依赖注入(单测可替换)。

当前是 stub 实现,Sprint 4 末把 Clerk + Postgres + Stripe 真正接上。
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class CurrentUser:
    id: str
    email: str
    plan: str = "free"  # free / pro / pro_plus
    quota_remaining: int = 50


def get_current_user() -> CurrentUser:
    """开发期:从 env var 读 fake user。生产期:解析 JWT / Clerk session。"""
    return CurrentUser(
        id=os.environ.get("DEV_USER_ID", "dev-user-001"),
        email=os.environ.get("DEV_USER_EMAIL", "dev@traillens.local"),
        plan=os.environ.get("DEV_USER_PLAN", "free"),
        quota_remaining=int(os.environ.get("DEV_USER_QUOTA", "50")),
    )


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
