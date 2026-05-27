"""config.Settings 测试。"""

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


@unittest.skipUnless(HAS_PYDANTIC, "config.py needs pydantic")
class TestSettings(unittest.TestCase):
    def test_default_values(self):
        from traillens_api.config import Settings

        s = Settings()
        self.assertEqual(s.env, "local")
        self.assertFalse(s.use_stubs)
        self.assertEqual(s.mcp_transport, "inprocess")
        self.assertEqual(s.anthropic_model, "claude-opus-4-7")

    def test_from_env_reads_environment(self):
        os.environ["TRAILLENS_USE_STUBS"] = "1"
        os.environ["TRAILLENS_ENV"] = "staging"
        os.environ["LOG_LEVEL"] = "debug"
        try:
            from traillens_api.config import Settings

            s = Settings.from_env()
            self.assertTrue(s.use_stubs)
            self.assertEqual(s.env, "staging")
            self.assertEqual(s.log_level, "debug")
        finally:
            for k in ("TRAILLENS_USE_STUBS", "TRAILLENS_ENV", "LOG_LEVEL"):
                os.environ.pop(k, None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
