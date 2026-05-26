"""MCPClient 抽象测试 — 验证三种 transport 的行为一致。"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "packages/agents"
if str(AGENTS) not in sys.path:
    sys.path.insert(0, str(AGENTS))


class TestMCPClientInProcess(unittest.TestCase):
    """in-process(默认 transport)调用直接 dispatch。"""

    def setUp(self):
        os.environ["TRAILLENS_MCP_TRANSPORT"] = "inprocess"

    def test_weather_call_via_inprocess(self):
        from traillens_agents.tools.mcp_client import client

        out = client("traillens_weather").call("weather_at", lat=30.0, lon=100.0)
        self.assertIsNotNone(out)
        self.assertIn("source", out)

    def test_sunmoon_call_via_inprocess(self):
        from traillens_agents.tools.mcp_client import client

        out = client("traillens_sunmoon").call("sun_moon_times", lat=30.0, lon=100.0, date="2026-05-26")
        self.assertIsNotNone(out)
        self.assertIn("source", out)

    def test_unknown_server_returns_none(self):
        from traillens_agents.tools.mcp_client import MCPClient

        c = MCPClient("nonexistent_server")
        self.assertIsNone(c.call("any_tool"))


class TestMCPClientStdio(unittest.TestCase):
    """stdio subprocess transport — 真实启子进程。"""

    def setUp(self):
        os.environ["TRAILLENS_MCP_TRANSPORT"] = "stdio"

    def tearDown(self):
        # 关闭可能残留的子进程
        from traillens_agents.tools.mcp_client import _CLIENTS
        for c in _CLIENTS.values():
            c.close()
        _CLIENTS.clear()
        os.environ["TRAILLENS_MCP_TRANSPORT"] = "inprocess"

    def test_sunmoon_via_stdio(self):
        from traillens_agents.tools.mcp_client import MCPClient

        c = MCPClient("traillens_sunmoon")
        out = c.call("sun_moon_times", lat=30.0, lon=100.0, date="2026-05-26")
        c.close()
        self.assertIsNotNone(out)
        # NOAA fallback 应有 sunrise 字段
        self.assertIn("sunrise", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
