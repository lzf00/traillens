"""store_protocol 契约测试:验证 alias 层等价于直接调 store。

不依赖 DB(用 mem 模式)。这个测试进 CI 后能防止业务代码
调 protocol 时因为签名漂移崩掉。
"""

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

# 强制 mem 模式(store.has_db() 返 False)
os.environ.setdefault("DATABASE_URL", "")


class ProtocolAliasTest(unittest.TestCase):
    def setUp(self):
        from traillens_api.services import store
        store.reset()
        self.store = store

    def test_create_get_delete_alias(self):
        from traillens_api.services.store_protocol import default_store
        s = default_store()

        # 用 protocol API 创
        t = s.create_resource(user_id="u1", name="test", location_name=None, gpx_uri=None)
        self.assertEqual(t.name, "test")

        # 用 protocol 读
        got = s.get_resource(t.id, user_id="u1")
        self.assertIsNotNone(got)
        self.assertEqual(got.id, t.id)

        # user 隔离
        self.assertIsNone(s.get_resource(t.id, user_id="u2"))

        # 列表
        rows = s.list_resources(user_id="u1")
        self.assertEqual(len(rows), 1)

        # 删
        s.delete_resource(t.id, user_id="u1")
        self.assertIsNone(s.get_resource(t.id, user_id="u1"))

    def test_direct_vs_protocol_same_result(self):
        """直接调 store vs 走 protocol 应完全等价。"""
        from traillens_api.services.store_protocol import default_store
        s = default_store()

        t1 = self.store.create_trail(user_id="u", name="direct",
                                      location_name="L", gpx_uri=None)
        t2 = s.get_resource(t1.id, user_id="u")
        self.assertEqual(t1.id, t2.id)
        self.assertEqual(t1.name, t2.name)


if __name__ == "__main__":
    unittest.main()
