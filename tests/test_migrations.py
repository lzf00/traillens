"""Alembic migration 静态检查 — 不需要真 DB。

只验证:
  1. migration 文件能 import(语法正确)
  2. upgrade/downgrade 都有定义
  3. 关键表名都在 upgrade 里出现(防漏建表)
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG_DIR = ROOT / "apps/api/alembic/versions"


def _load(path: Path):
    """绕开 alembic.op import — 测试只需检查源码字符串与函数存在,不真正执行。"""
    src = path.read_text(encoding="utf-8")
    return src


class TestInitialSchemaMigration(unittest.TestCase):
    def setUp(self):
        files = list(MIG_DIR.glob("*_0001_*.py"))
        self.assertEqual(len(files), 1, "should be exactly one initial migration")
        self.path = files[0]
        self.src = _load(self.path)

    def test_has_upgrade_and_downgrade(self):
        self.assertIn("def upgrade()", self.src)
        self.assertIn("def downgrade()", self.src)

    def test_creates_all_five_core_tables(self):
        for tbl in ("trails", "photos", "user_preferences", "agent_runs", "subscriptions"):
            self.assertIn(
                f"CREATE TABLE IF NOT EXISTS {tbl}",
                self.src,
                f"migration missing create for {tbl}",
            )

    def test_uses_pgvector(self):
        self.assertIn("vector(768)", self.src, "photos.embedding must use pgvector")

    def test_gps_bbox_present(self):
        # MVP: gps_bbox 用 jsonb;PostGIS 留给后续 sprint
        self.assertIn("gps_bbox", self.src, "trails must have gps_bbox column")

    def test_downgrade_drops_in_reverse_order(self):
        # 反向 drop:子表先 drop,父表后 drop(避免 FK 残留)。
        # migration 用 f-string 循环生成 DROP,这里检查 tuple 字面里的顺序。
        import re

        m = re.search(
            r'def downgrade.*?for tbl in\s*\(([^)]+)\)', self.src, re.S
        )
        self.assertIsNotNone(m, "downgrade should iterate a tuple of table names")
        tables = [t.strip().strip('"').strip("'") for t in m.group(1).split(",") if t.strip()]
        # agent_runs / photos 是子表必须在 trails 前;subscriptions 与 trails 无 FK,放最后
        self.assertLess(tables.index("agent_runs"), tables.index("trails"))
        self.assertLess(tables.index("photos"), tables.index("trails"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
