"""契约 8:SQLAlchemy ORM models 字段 ⊆ Alembic migration 字段。

防止 model 加列但忘了写 migration → 部署后 ORM 查不到列。
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_PKG = ROOT / "apps" / "api"
if str(API_PKG) not in sys.path:
    sys.path.insert(0, str(API_PKG))


def _migration_columns(table: str) -> set[str]:
    """从 0001 migration 源码里抽指定表的列名(粗暴正则,够用)。"""
    src = (ROOT / "apps/api/alembic/versions/20260526_0001_initial_schema.py").read_text()
    # 找 "CREATE TABLE IF NOT EXISTS <table> ( ... );"
    m = re.search(rf"CREATE TABLE IF NOT EXISTS {table} \((.*?)\);", src, re.S)
    if not m:
        return set()
    body = m.group(1)
    cols = set()
    for line in body.splitlines():
        line = line.strip().rstrip(",")
        # 跳过 CHECK / FK / PRIMARY KEY 行
        if not line or line.upper().startswith(("CHECK", "FOREIGN", "PRIMARY", "CONSTRAINT")):
            continue
        # 第一个 token 就是列名
        tok = line.split()[0] if line.split() else ""
        if tok and tok.isidentifier():
            cols.add(tok)
    return cols


class TestContract8OrmMatchesMigration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from traillens_api.models import HAS_SQLALCHEMY
        except ImportError:
            cls.has_sa = False
            return
        cls.has_sa = HAS_SQLALCHEMY

    def setUp(self):
        if not self.__class__.has_sa:
            self.skipTest("sqlalchemy not installed")

    def _check(self, model_cls, table_name):
        from traillens_api import models  # noqa

        orm_cols = {c.key for c in model_cls.__table__.columns}
        mig_cols = _migration_columns(table_name)
        missing = orm_cols - mig_cols - {"gps_bbox", "embedding"}  # 这两列 ORM 不映射(pgvector/PostGIS),需手动 raw
        self.assertFalse(
            missing,
            f"{table_name}: ORM 有但 migration 没有的列: {missing}",
        )

    def test_trail(self):
        from traillens_api.models import Trail
        self._check(Trail, "trails")

    def test_photo(self):
        from traillens_api.models import Photo
        self._check(Photo, "photos")

    def test_subscription(self):
        from traillens_api.models import Subscription
        self._check(Subscription, "subscriptions")

    def test_user_preference(self):
        from traillens_api.models import UserPreference
        self._check(UserPreference, "user_preferences")

    def test_agent_run(self):
        from traillens_api.models import AgentRun
        self._check(AgentRun, "agent_runs")


if __name__ == "__main__":
    unittest.main(verbosity=2)
