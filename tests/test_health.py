"""healthz / readyz 测试。"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("TRAILLENS_USE_STUBS", "1")
os.environ.setdefault("TRAILLENS_DISABLE_RATELIMIT", "1")

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
class TestHealthEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from traillens_api.config import get_settings
        get_settings.cache_clear()
        from traillens_api.main import app
        cls.client = TestClient(app)

    def test_healthz_always_fast_and_200(self):
        r = self.client.get("/healthz")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_readyz_returns_check_table(self):
        # 无 DATABASE_URL / REDIS_URL → 跳过(算 ok)
        for k in ("DATABASE_URL", "REDIS_URL", "TRAILLENS_AESTHETIC_ENDPOINT"):
            os.environ.pop(k, None)
        r = self.client.get("/readyz")
        # 因为全部 skipped,应该 200 + ready=true
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ready"])
        for check in ("db", "redis", "aesthetic", "mcp"):
            self.assertIn(check, data["checks"])

    def test_readyz_reports_503_when_dependency_unreachable(self):
        # 故意指向不通的 PG
        os.environ["DATABASE_URL"] = "postgresql://nope:nope@127.0.0.1:1/none"
        try:
            r = self.client.get("/readyz")
            self.assertEqual(r.status_code, 503)
            self.assertFalse(r.json()["ready"])
            self.assertFalse(r.json()["checks"]["db"]["ok"])
        finally:
            os.environ.pop("DATABASE_URL", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
