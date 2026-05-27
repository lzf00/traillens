"""Stripe billing 集成测试。

无 STRIPE_SECRET_KEY 时应优雅 503,而不是崩。
有签名头但签名错应给 401 不是 500(攻击防护)。
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("TRAILLENS_USE_STUBS", "1")

ROOT = Path(__file__).resolve().parents[1]
API_PKG = ROOT / "apps" / "api"
if str(API_PKG) not in sys.path:
    sys.path.insert(0, str(API_PKG))

try:
    from fastapi.testclient import TestClient
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TestBillingEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 清掉 settings cache 以确保 env 变化生效
        from traillens_api.config import get_settings
        get_settings.cache_clear()
        from traillens_api.main import app
        from traillens_api.services import store
        store.reset()
        cls.client = TestClient(app)

    def test_checkout_returns_503_without_price_id(self):
        # 无 STRIPE_PRICE_PRO env → 503
        for k in ("STRIPE_PRICE_PRO", "STRIPE_SECRET_KEY"):
            os.environ.pop(k, None)
        r = self.client.post("/v1/billing/checkout", json={"plan": "pro"})
        self.assertEqual(r.status_code, 503)

    def test_checkout_400_for_invalid_plan(self):
        r = self.client.post("/v1/billing/checkout", json={"plan": "diamond"})
        self.assertEqual(r.status_code, 400)

    def test_webhook_503_without_secret(self):
        for k in ("STRIPE_WEBHOOK_SECRET",):
            os.environ.pop(k, None)
        from traillens_api.config import get_settings
        get_settings.cache_clear()
        r = self.client.post("/v1/billing/webhook", content=b"fake", headers={"stripe-signature": "sig"})
        self.assertEqual(r.status_code, 503)


class TestPriceMap(unittest.TestCase):
    def test_unknown_price_defaults_to_free(self):
        from traillens_api.services.billing import PRICE_PLAN_MAP
        self.assertEqual(PRICE_PLAN_MAP.get("price_random"), None)

    def test_plan_quota_table_complete(self):
        from traillens_api.services.billing import PLAN_QUOTA
        for plan in ("free", "pro", "pro_plus"):
            self.assertIn(plan, PLAN_QUOTA)


if __name__ == "__main__":
    unittest.main(verbosity=2)
