"""traillens-exif MCP server 契约与单元测试。

契约:server 暴露的 EXIF 字段必须与 agents 包的 ExifMeta 字段严格对齐
     (一侧改字段名,CI 红)。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "packages/agents"
EXIF_PKG = ROOT / "packages/mcp_servers/traillens_exif"
for p in (AGENTS, EXIF_PKG):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


# --------------------------------------------------------------------------- #
# 契约 6: server 字段 ⊇ ExifMeta 字段
# --------------------------------------------------------------------------- #
class TestContract6ExifServerAlignsExifMeta(unittest.TestCase):
    def test_exif_fields_cover_exif_meta(self):
        from traillens_agents.state.schema import ExifMeta
        from traillens_exif import EXIF_FIELDS

        agent_fields = set(
            getattr(ExifMeta, "model_fields", None) or ExifMeta.__dataclass_fields__
        )
        server_fields = set(EXIF_FIELDS)
        missing = agent_fields - server_fields
        self.assertFalse(
            missing,
            f"MCP server 未覆盖 ExifMeta 字段: {missing}"
            " (改 ExifMeta 时务必同步更新 traillens_exif/core.py::EXIF_FIELDS)",
        )


# --------------------------------------------------------------------------- #
# 单元测试:核心解析函数
# --------------------------------------------------------------------------- #
class TestExifCorePureHelpers(unittest.TestCase):
    def test_format_shutter_for_fast(self):
        from traillens_exif.core import _format_shutter

        self.assertEqual(_format_shutter(0.004), "1/250")

    def test_format_shutter_for_long_exposure(self):
        from traillens_exif.core import _format_shutter

        self.assertEqual(_format_shutter(30), "30s")

    def test_format_shutter_invalid(self):
        from traillens_exif.core import _format_shutter

        self.assertIsNone(_format_shutter(None))
        self.assertIsNone(_format_shutter(0))
        self.assertIsNone(_format_shutter("nope"))

    def test_to_iso_parses_exif_datetime(self):
        from traillens_exif.core import _to_iso

        self.assertEqual(_to_iso("2026:05:15 18:30:00"), "2026-05-15T18:30:00")
        self.assertIsNone(_to_iso(None))

    def test_parse_gps_decimal_signs(self):
        from traillens_exif.core import _parse_gps

        # 31°30'00"S, 99°45'00"E
        gps = {1: "S", 2: (31, 30, 0), 3: "E", 4: (99, 45, 0)}
        lat, lon = _parse_gps(gps)
        self.assertAlmostEqual(lat, -31.5, places=4)
        self.assertAlmostEqual(lon, 99.75, places=4)


# --------------------------------------------------------------------------- #
# 集成:对不存在的文件不抛异常,返回 error 字段
# --------------------------------------------------------------------------- #
class TestExifGracefulDegradation(unittest.TestCase):
    def test_missing_file_returns_error_not_exception(self):
        from traillens_exif import extract_exif

        result = extract_exif("/definitely/does/not/exist.jpg")
        self.assertIsNotNone(result.error)
        self.assertIn("file_not_found", result.error)

    def test_dispatch_unknown_tool_raises(self):
        from traillens_exif.server import dispatch

        with self.assertRaises(ValueError):
            dispatch("nonexistent", {})

    def test_dispatch_read_exif_for_missing_file(self):
        from traillens_exif.server import dispatch

        out = dispatch("read_exif", {"path": "/nope.jpg"})
        # 返回 dict,不抛
        self.assertIsInstance(out, dict)
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
