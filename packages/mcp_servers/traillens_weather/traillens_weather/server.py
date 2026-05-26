"""traillens-weather MCP stdio server。"""

from __future__ import annotations

import json
import sys
from typing import Any

from .core import forecast, weather_at

TOOL_SCHEMA = [
    {
        "name": "weather_at",
        "description": "查指定 lat/lon/date 的天气摘要(Open-Meteo)。date 省略则为当前。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "date": {"type": "string", "description": "YYYY-MM-DD, optional"},
            },
            "required": ["lat", "lon"],
        },
    },
    {
        "name": "forecast",
        "description": "N 天预报(默认 3 天, 上限 14 天)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "days": {"type": "integer", "minimum": 1, "maximum": 14},
            },
            "required": ["lat", "lon"],
        },
    },
]


def dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "weather_at":
        return weather_at(args["lat"], args["lon"], args.get("date"))
    if name == "forecast":
        return forecast(args["lat"], args["lon"], args.get("days", 3))
    raise ValueError(f"unknown_tool:{name}")


def _serve_with_official_sdk() -> bool:
    try:
        from mcp.server import Server  # type: ignore
        from mcp.server.stdio import stdio_server  # type: ignore
        from mcp.types import TextContent, Tool  # type: ignore
    except ImportError:
        return False

    import anyio

    server = Server("traillens-weather")

    @server.list_tools()
    async def _list() -> list[Tool]:
        return [Tool(**t) for t in TOOL_SCHEMA]

    @server.call_tool()
    async def _call(name: str, arguments: dict) -> list[TextContent]:
        return [TextContent(type="text", text=json.dumps(dispatch(name, arguments or {}), ensure_ascii=False))]

    async def _run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    anyio.run(_run)
    return True


def _serve_fallback() -> None:
    sys.stderr.write("[traillens-weather] mcp SDK 未安装,fallback stdio loop\n")
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        method, msg_id = msg.get("method"), msg.get("id")
        if method == "tools/list":
            _reply(msg_id, {"tools": TOOL_SCHEMA})
        elif method == "tools/call":
            p = msg.get("params", {})
            try:
                out = dispatch(p.get("name", ""), p.get("arguments") or {})
                _reply(msg_id, {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}]})
            except Exception as e:  # noqa: BLE001
                _reply(msg_id, {"error": str(e)}, error=True)
        elif method == "initialize":
            _reply(msg_id, {"protocolVersion": "2025-11-25", "serverInfo": {"name": "traillens-weather", "version": "0.0.1"}})


def _reply(msg_id, payload, error: bool = False) -> None:
    body = {"jsonrpc": "2.0", "id": msg_id}
    body["error" if error else "result"] = payload
    sys.stdout.write(json.dumps(body, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    if not _serve_with_official_sdk():
        _serve_fallback()


if __name__ == "__main__":
    main()
