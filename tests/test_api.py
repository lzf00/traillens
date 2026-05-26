"""apps/api FastAPI 路由集成测试。

需要 fastapi + httpx;无这些依赖时整文件 skip,保持 contract-tests job 仍能跑通。
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
    from fastapi.testclient import TestClient  # type: ignore
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed; skipping API tests")
class TestApiSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from traillens_api.main import app
        from traillens_api.services import store

        store.reset()
        cls.client = TestClient(app)

    def test_healthz(self):
        r = self.client.get("/healthz")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_trail_lifecycle(self):
        r = self.client.post("/v1/trails", json={"name": "贡嘎环线"})
        self.assertEqual(r.status_code, 201, r.text)
        trail = r.json()
        tid = trail["id"]

        # 加 5 张照片
        r2 = self.client.post(
            f"/v1/trails/{tid}/photos:bulk",
            json={"photos": [{"uri": f"r2://photos/{i}.jpg"} for i in range(5)]},
        )
        self.assertEqual(r2.status_code, 202)
        self.assertEqual(r2.json()["accepted"], 5)

        # 查照片列表
        r3 = self.client.get(f"/v1/trails/{tid}/photos")
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(len(r3.json()), 5)

    def test_get_photo_returns_404_for_unknown(self):
        r = self.client.post("/v1/trails", json={"name": "photo-detail-test"})
        tid = r.json()["id"]
        r2 = self.client.get(f"/v1/trails/{tid}/photos/nonexistent")
        self.assertEqual(r2.status_code, 404)

    def test_trail_404(self):
        r = self.client.get("/v1/trails/nonexistent")
        self.assertEqual(r.status_code, 404)

    def test_quota_exceeded_triggers_429(self):
        os.environ["DEV_USER_QUOTA"] = "10"
        try:
            r = self.client.post("/v1/trails", json={"name": "quota-test"})
            tid = r.json()["id"]
            big_batch = {"photos": [{"uri": f"r2://x/{i}"} for i in range(100)]}
            r2 = self.client.post(f"/v1/trails/{tid}/photos:bulk", json=big_batch)
            self.assertEqual(r2.status_code, 429)
            self.assertEqual(r2.json()["detail"]["error"], "quota_exceeded")
        finally:
            os.environ.pop("DEV_USER_QUOTA", None)

    def test_run_streams_sse_events(self):
        r = self.client.post("/v1/trails", json={"name": "stream-test"})
        tid = r.json()["id"]

        with self.client.stream("POST", f"/v1/trails/{tid}/run") as resp:
            self.assertEqual(resp.status_code, 200)
            self.assertIn("text/event-stream", resp.headers["content-type"])
            body = "".join(resp.iter_text())

        # 起码包含 run.started 和 run.finished
        self.assertIn("event: run.started", body)
        self.assertIn("event: run.finished", body)
        # 至少出现一次 culling 事件
        self.assertTrue(
            "event: culling.progress" in body or "event: culling.photo_scored" in body
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
