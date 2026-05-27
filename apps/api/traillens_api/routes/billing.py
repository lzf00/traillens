"""/v1/billing — checkout + webhook."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..deps import CurrentUser, get_current_user
from ..services import billing

router = APIRouter()


class CheckoutRequest(BaseModel):
    plan: str  # "pro" | "pro_plus"


@router.post("/checkout")
def create_checkout(
    body: CheckoutRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """创建 Stripe Checkout Session,返回 URL 让前端 redirect 过去。"""
    if body.plan == "pro":
        price_id = os.environ.get("STRIPE_PRICE_PRO")
    elif body.plan == "pro_plus":
        price_id = os.environ.get("STRIPE_PRICE_PRO_PLUS")
    else:
        raise HTTPException(400, "invalid_plan")
    if not price_id:
        raise HTTPException(503, "stripe_not_configured")

    site = os.environ.get("PUBLIC_SITE_URL", "https://traillens.zorotreeking.online")
    try:
        url = billing.create_checkout_session(
            user_id=user.id, user_email=user.email,
            price_id=price_id,
            success_url=f"{site}/app/settings",
            cancel_url=f"{site}/app/settings?cancelled=1",
        )
    except billing.BillingNotConfigured as e:
        raise HTTPException(503, f"stripe_not_configured: {e}")
    return {"checkout_url": url}


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    """Stripe → 这里 POST。签名校验必通过才能处理。"""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = billing.verify_webhook(payload, sig)
    except billing.BillingNotConfigured:
        raise HTTPException(503, "stripe_not_configured")
    except billing.InvalidWebhookSignature:
        # 401 而不是 400 — 阻止 Stripe 的 retry,因为这看起来是攻击
        raise HTTPException(401, "invalid_signature")

    summary = billing.apply_subscription_event(event)
    return {"ok": True, **summary}
