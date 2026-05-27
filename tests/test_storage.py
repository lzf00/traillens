"""storage.py — presign / key generation 测试。"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_PKG = ROOT / "apps" / "api"
if str(API_PKG) not in sys.path:
    sys.path.insert(0, str(API_PKG))


class TestObjectKey(unittest.TestCase):
    def test_layered_path_structure(self):
        from traillens_api.services.storage import make_object_key

        k = make_object_key(user_id="u1", trail_id="t1", photo_id="p1", ext="jpg")
        self.assertEqual(k, "users/u1/trails/t1/p1.jpg")

    def test_ext_normalized(self):
        from traillens_api.services.storage import make_object_key

        self.assertEqual(
            make_object_key(user_id="u", trail_id="t", photo_id="p", ext=".PNG"),
            "users/u/trails/t/p.png",
        )

    def test_ext_truncated_to_5_chars(self):
        from traillens_api.services.storage import make_object_key

        k = make_object_key(user_id="u", trail_id="t", photo_id="p", ext="malicious_super_long_ext")
        self.assertTrue(k.endswith(".malic"))


class TestPresignWithoutCreds(unittest.TestCase):
    """无 R2 凭证时应返回 None,而不是崩。"""

    def test_returns_none(self):
        # 临时清空凭证
        saved = {k: os.environ.pop(k, None) for k in ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")}
        try:
            from traillens_api.services import storage
            url = storage.presign("put", "users/u/trails/t/p.jpg")
            self.assertIsNone(url)
        finally:
            for k, v in saved.items():
                if v: os.environ[k] = v


class TestPresignSigV4(unittest.TestCase):
    """SigV4 fallback 实现 — 即使无 boto3 也能产出合法 query 串。"""

    def setUp(self):
        os.environ["R2_ACCOUNT_ID"] = "stubaccount"
        os.environ["R2_ACCESS_KEY_ID"] = "AKIATESTKEY"
        os.environ["R2_SECRET_ACCESS_KEY"] = "TESTSECRET"
        os.environ["R2_BUCKET"] = "traillens-test"
        # 清掉 settings 单例缓存
        from traillens_api.config import get_settings
        get_settings.cache_clear()

    def tearDown(self):
        for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
            os.environ.pop(k, None)
        from traillens_api.config import get_settings
        get_settings.cache_clear()

    def test_sigv4_url_contains_required_params(self):
        from traillens_api.services.storage import _presign_sigv4, _config

        url = _presign_sigv4("put", "users/u/trails/t/p.jpg", _config(),
                             expires=3600, content_type="image/jpeg")
        for required in ("X-Amz-Algorithm=AWS4-HMAC-SHA256",
                         "X-Amz-Credential=",
                         "X-Amz-Date=",
                         "X-Amz-Expires=3600",
                         "X-Amz-Signature="):
            self.assertIn(required, url, f"missing {required} in presigned URL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
