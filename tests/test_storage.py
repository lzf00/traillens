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

try:
    import pydantic  # noqa: F401
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


@unittest.skipUnless(HAS_PYDANTIC, "storage uses pydantic via config")
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


@unittest.skipUnless(HAS_PYDANTIC, "storage uses pydantic via config")
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


@unittest.skipUnless(HAS_PYDANTIC, "storage uses pydantic via config")
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


@unittest.skipUnless(HAS_PYDANTIC, "storage uses pydantic via config")
class TestCosPresign(unittest.TestCase):
    """腾讯云 COS 路径 — fallback(SigV4)即使无 cos sdk 也能签 URL。"""

    def setUp(self):
        os.environ["COS_SECRET_ID"] = "AKIDfake"
        os.environ["COS_SECRET_KEY"] = "secretfake"
        os.environ["COS_BUCKET"] = "traillens-photos-1305566123"
        os.environ["COS_REGION"] = "ap-shanghai"
        from traillens_api.config import get_settings
        get_settings.cache_clear()

    def tearDown(self):
        for k in ("COS_SECRET_ID", "COS_SECRET_KEY", "COS_BUCKET", "COS_REGION", "COS_DOMAIN"):
            os.environ.pop(k, None)
        from traillens_api.config import get_settings
        get_settings.cache_clear()

    def test_get_url_signed_with_sigv4(self):
        from traillens_api.services.storage import presign

        url = presign("get", "users/u/trails/t/p.jpg", expires=600)
        self.assertIsNotNone(url)
        # COS endpoint 形态
        self.assertIn("traillens-photos-1305566123.cos.ap-shanghai.myqcloud.com", url)
        # 必含 SigV4 参数(无 SDK 时走 fallback)或 COS SDK 风格签名
        self.assertTrue("X-Amz-Signature=" in url or "q-signature=" in url)

    def test_cos_takes_priority_over_qiniu_and_r2(self):
        os.environ["QINIU_ACCESS_KEY"] = "should_not_use"
        os.environ["QINIU_SECRET_KEY"] = "should_not_use"
        os.environ["R2_ACCESS_KEY_ID"] = "should_not_use"
        os.environ["R2_SECRET_ACCESS_KEY"] = "should_not_use"
        try:
            from traillens_api.services.storage import presign
            url = presign("get", "u/t/p.jpg", expires=600)
            self.assertIn(".cos.ap-shanghai.myqcloud.com", url)
        finally:
            for k in ("QINIU_ACCESS_KEY", "QINIU_SECRET_KEY",
                      "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"):
                os.environ.pop(k, None)

    def test_public_url_uses_cos_domain_when_set(self):
        from traillens_api.services.storage import public_url
        os.environ["COS_DOMAIN"] = "photos.traillens.zorotreeking.online"
        try:
            url = public_url("u/t/p.jpg")
            self.assertEqual(url, "https://photos.traillens.zorotreeking.online/u/t/p.jpg")
        finally:
            os.environ.pop("COS_DOMAIN", None)

    def test_public_url_falls_back_to_default_cos_host(self):
        from traillens_api.services.storage import public_url
        # 无 COS_DOMAIN → 用默认 <bucket>.cos.<region>.myqcloud.com
        url = public_url("u/t/p.jpg")
        self.assertEqual(
            url,
            "https://traillens-photos-1305566123.cos.ap-shanghai.myqcloud.com/u/t/p.jpg",
        )


@unittest.skipUnless(HAS_PYDANTIC, "storage uses pydantic via config")
class TestQiniuPresign(unittest.TestCase):
    """七牛云路径 — 即使无 qiniu SDK 也能签 GET URL(纯 hmac-sha1)。"""

    def setUp(self):
        os.environ["QINIU_ACCESS_KEY"] = "test-ak"
        os.environ["QINIU_SECRET_KEY"] = "test-sk"
        os.environ["QINIU_BUCKET"] = "traillens-photos"
        os.environ["QINIU_DOMAIN"] = "photos.test.com"
        from traillens_api.config import get_settings
        get_settings.cache_clear()

    def tearDown(self):
        for k in ("QINIU_ACCESS_KEY", "QINIU_SECRET_KEY", "QINIU_BUCKET", "QINIU_DOMAIN"):
            os.environ.pop(k, None)
        from traillens_api.config import get_settings
        get_settings.cache_clear()

    def test_get_url_signed_correctly(self):
        from traillens_api.services.storage import presign

        url = presign("get", "users/u/trails/t/p.jpg", expires=3600)
        self.assertIsNotNone(url)
        self.assertIn("photos.test.com", url)
        # 七牛 token 格式:ak:base64sign(若装了 qiniu SDK 用 SDK,否则用 fallback hmac)
        self.assertTrue("token=test-ak:" in url or "token=" in url)
        self.assertIn("e=", url)

    def test_qiniu_takes_priority_over_r2(self):
        os.environ["R2_ACCESS_KEY_ID"] = "should_not_be_used"
        os.environ["R2_SECRET_ACCESS_KEY"] = "should_not_be_used"
        try:
            from traillens_api.services.storage import presign
            url = presign("get", "u/t/p.jpg", expires=600)
            self.assertIn("photos.test.com", url)
            self.assertNotIn("r2.cloudflarestorage", url)
        finally:
            os.environ.pop("R2_ACCESS_KEY_ID", None)
            os.environ.pop("R2_SECRET_ACCESS_KEY", None)

    def test_public_url_uses_qiniu_domain(self):
        from traillens_api.services.storage import public_url
        self.assertEqual(public_url("u/t/p.jpg"), "https://photos.test.com/u/t/p.jpg")


if __name__ == "__main__":
    unittest.main(verbosity=2)
