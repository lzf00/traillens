"""Settings(token + preferences) + Library(search) endpoints。"""

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
class TestTokens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from traillens_api.config import get_settings
        get_settings.cache_clear()
        from traillens_api.main import app
        cls.client = TestClient(app)

    def test_create_token_then_list(self):
        r = self.client.post("/v1/settings/tokens", json={"label": "LR Plugin"})
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertTrue(data["token"].startswith("tl_"))
        self.assertEqual(len(data["prefix"]), 8)

        # list 不返回完整 token
        r2 = self.client.get("/v1/settings/tokens")
        self.assertEqual(r2.status_code, 200)
        tokens = r2.json()
        self.assertTrue(any(t["label"] == "LR Plugin" for t in tokens))
        # 不可能列出完整 token
        for t in tokens:
            self.assertNotIn("token", t)

    def test_revoke_token(self):
        r = self.client.post("/v1/settings/tokens", json={"label": "to-revoke"})
        token_id = r.json()["id"]
        r2 = self.client.delete(f"/v1/settings/tokens/{token_id}")
        self.assertEqual(r2.status_code, 204)
        # 再 revoke 404
        r3 = self.client.delete(f"/v1/settings/tokens/{token_id}")
        self.assertEqual(r3.status_code, 404)


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TestPreferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from traillens_api.config import get_settings
        get_settings.cache_clear()
        from traillens_api.main import app
        cls.client = TestClient(app)

    def test_default_preferences(self):
        r = self.client.get("/v1/settings/preferences")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("favorite_focal_lengths", data)
        self.assertIn("style_keywords", data)

    def test_update_preferences(self):
        r = self.client.put("/v1/settings/preferences", json={
            "favorite_focal_lengths": [24, 70],
            "style_keywords": ["moody", "high-contrast"],
        })
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["favorite_focal_lengths"], [24, 70])
        self.assertIn("moody", data["style_keywords"])


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TestLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from traillens_api.main import app
        cls.client = TestClient(app)

    def test_search_returns_array(self):
        r = self.client.get("/v1/library/search?q=test")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_search_rejects_empty_query(self):
        r = self.client.get("/v1/library/search?q=")
        self.assertEqual(r.status_code, 422)

    def test_reembed_returns_queued(self):
        r = self.client.post("/v1/library/embed/some-trail")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "stub")


if __name__ == "__main__":
    unittest.main(verbosity=2)
