"""Stripe 集成 — checkout + webhook 处理。

设计:
- 不直接 import stripe 到 routes;routes 调这里的纯函数
- 无 STRIPE_SECRET_KEY → 抛 503 而不是崩
- webhook 签名校验在 verify_webhook()里;签名错 → 401(防伪造攻击)
- 状态变更只写一个地方:apply_subscription_event()
"""

from __future__ import annotations

import logging
import os
from typing import Any

from ..config import get_settings
from .observability import capture_event

log = logging.getLogger("traillens.billing")


# --------------------------------------------------------------------------- #
# 价格表(与 docs/PRODUCT_PLAN §5.1 锁定)
# --------------------------------------------------------------------------- #
PRICE_PLAN_MAP = {
    # 这些 ID 来自 Stripe Dashboard,通过 env 注入
    os.environ.get("STRIPE_PRICE_PRO", ""): "pro",
    os.environ.get("STRIPE_PRICE_PRO_PLUS", ""): "pro_plus",
}

PLAN_QUOTA = {
    "free": 50,
    "pro": 1000,
    "pro_plus": 10_000_000,  # 实际无上限
}


# --------------------------------------------------------------------------- #
# Checkout
# --------------------------------------------------------------------------- #
def create_checkout_session(
    *, user_id: str, user_email: str, price_id: str, success_url: str, cancel_url: str,
) -> str:
    """生成 Stripe Checkout Session,返回 hosted URL。"""
    s = get_settings()
    if not s.stripe_secret_key:
        raise BillingNotConfigured()
    try:
        import stripe
    except ImportError:
        raise BillingNotConfigured("stripe package not installed")
    stripe.api_key = s.stripe_secret_key

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=user_email,
        client_reference_id=user_id,         # 用 user_id 反查
        success_url=success_url + "?session={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        allow_promotion_codes=True,           # 学生 / 早鸟促销码
        subscription_data={
            "metadata": {"user_id": user_id},
        },
    )
    capture_event(user_id, "checkout.started", {"price_id": price_id})
    return session.url


# --------------------------------------------------------------------------- #
# Webhook
# --------------------------------------------------------------------------- #
def verify_webhook(payload: bytes, sig_header: str) -> dict[str, Any]:
    """验证 Stripe webhook 签名,返回 event 对象。

    Raises:
        BillingNotConfigured: 无 STRIPE_WEBHOOK_SECRET
        InvalidWebhookSignature: 签名错(可能是伪造攻击)
    """
    s = get_settings()
    if not s.stripe_webhook_secret:
        raise BillingNotConfigured()
    try:
        import stripe
    except ImportError:
        raise BillingNotConfigured("stripe package not installed")
    try:
        return stripe.Webhook.construct_event(
            payload, sig_header, s.stripe_webhook_secret,
        )
    except stripe.error.SignatureVerificationError as e:
        raise InvalidWebhookSignature() from e


def apply_subscription_event(event: dict[str, Any]) -> dict[str, Any]:
    """处理 webhook 事件,写入订阅状态。返回操作摘要。

    支持的事件:
      checkout.session.completed      → 用户初次付费,激活订阅
      customer.subscription.updated   → 换计划 / 续费
      customer.subscription.deleted   → 取消订阅,降级到 free
      invoice.paid                    → 周期续费成功
      invoice.payment_failed          → 支付失败,挂起或降级
    """
    et = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    summary = {"event": et, "handled": False}

    if et == "checkout.session.completed":
        user_id = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("user_id")
        customer_id = obj.get("customer")
        price_id = _first_price_id(obj)
        plan = PRICE_PLAN_MAP.get(price_id, "free")
        _upsert_subscription(user_id=user_id, customer_id=customer_id, plan=plan)
        capture_event(user_id or "anon", "checkout.completed", {"plan": plan})
        summary.update({"handled": True, "user_id": user_id, "plan": plan})

    elif et == "customer.subscription.updated":
        user_id = (obj.get("metadata") or {}).get("user_id")
        price_id = _first_price_id_from_sub(obj)
        plan = PRICE_PLAN_MAP.get(price_id, "free")
        _upsert_subscription(user_id=user_id, customer_id=obj.get("customer"), plan=plan)
        summary.update({"handled": True, "plan": plan})

    elif et == "customer.subscription.deleted":
        user_id = (obj.get("metadata") or {}).get("user_id")
        _upsert_subscription(user_id=user_id, customer_id=obj.get("customer"), plan="free")
        capture_event(user_id or "anon", "subscription.canceled", {})
        summary.update({"handled": True})

    elif et == "invoice.payment_failed":
        user_id = (obj.get("subscription_details") or {}).get("metadata", {}).get("user_id")
        log.warning("payment_failed for user=%s", user_id)
        summary["handled"] = True

    else:
        log.info("unhandled stripe event: %s", et)

    return summary


def _first_price_id(checkout_session) -> str:
    """从 checkout.session.completed 中提 price_id(可能在 line_items 也可能在 amount_total)。"""
    # Stripe 不在 webhook payload 自动展开 line_items,需要单独 retrieve;
    # 简化:先读 subscription.items.data[0].price.id
    sub = checkout_session.get("subscription")
    if not sub or not isinstance(sub, dict):
        return ""
    return _first_price_id_from_sub(sub)


def _first_price_id_from_sub(sub: dict) -> str:
    items = ((sub.get("items") or {}).get("data") or [])
    if not items:
        return ""
    return ((items[0] or {}).get("price") or {}).get("id", "")


def _upsert_subscription(*, user_id: str | None, customer_id: str | None, plan: str) -> None:
    """落库 — Sprint 5 末换为真实 SQL upsert。"""
    if not user_id:
        log.warning("subscription event missing user_id; skipped")
        return
    quota = PLAN_QUOTA.get(plan, 50)
    # TODO Sprint 5: store.upsert_subscription(user_id, customer_id, plan, quota)
    log.info("subscription upsert: user=%s plan=%s quota=%d cust=%s",
             user_id, plan, quota, customer_id)


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class BillingNotConfigured(Exception):
    pass


class InvalidWebhookSignature(Exception):
    pass
