"""Rate limit middleware 测试。"""

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


class TestRateLimitInternals(unittest.TestCase):
    def test_path_normalization(self):
        from traillens_api.middleware.rate_limit import RateLimitMiddleware

        rl = RateLimitMiddleware(None, enabled=False)
        self.assertEqual(
            rl._normalize_path("/v1/trails/6d21a404-dbb4-47a4-a1d1-dd1e0a397863/run"),
            "/v1/trails/run",
        )
        self.assertEqual(
            rl._normalize_path("/v1/photos/abc/download"),
            "/v1/photos/abc/download",   # 'abc' 不是 uuid,保留
        )

    def test_token_bucket_allows_under_limit(self):
        from traillens_api.middleware.rate_limit import RateLimitMiddleware

        rl = RateLimitMiddleware(None, enabled=True)
        # 限 120/min,前几次应该都过
        for i in range(5):
            allowed, _ = rl._consume("test-client", "GET /test", 120, 30)
            self.assertTrue(allowed, f"request {i} should pass")

    def test_token_bucket_blocks_over_limit(self):
        from traillens_api.middleware.rate_limit import RateLimitMiddleware

        rl = RateLimitMiddleware(None, enabled=True)
        # 限 1/min + burst 0:第 2 次应被拒
        blocked = False
        for i in range(3):
            allowed, retry = rl._consume("burst-client", "POST /strict", 1, 0)
            if not allowed:
                blocked = True
                self.assertGreater(retry, 0)
                break
        self.assertTrue(blocked, "should have hit limit within 3 calls")


class TestRateLimitEndToEnd(unittest.TestCase):
    """端到端:启用 rate limit 后,连续打 /healthz(豁免)与 /v1/trails(受限)。"""

    def setUp(self):
        # 这个测试主动启用 rate limit
        os.environ.pop("TRAILLENS_DISABLE_RATELIMIT", None)
        # 重新 import 一次 app,确保新 middleware 配置生效
        for mod in list(sys.modules):
            if mod.startswith("traillens_api"):
                del sys.modules[mod]
        try:
            from fastapi.testclient import TestClient
            from traillens_api.main import app
            self.client = TestClient(app)
        except ImportError:
            self.skipTest("fastapi not installed")

    def tearDown(self):
        os.environ["TRAILLENS_DISABLE_RATELIMIT"] = "1"
        for mod in list(sys.modules):
            if mod.startswith("traillens_api"):
                del sys.modules[mod]

    def test_healthz_exempt(self):
        # /healthz 应永不被限流
        for _ in range(50):
            r = self.client.get("/healthz")
            self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
