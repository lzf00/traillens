"""MCP stdio server wrapper。

设计选择
--------
- mcp SDK 不在 sys.path 时 *优雅降级* 到 "fake MCP" 模式:进程读 JSON-RPC over stdio,
  实现最小的 initialize / tools/list / tools/call 子集。这让本仓库不强依赖 mcp 包,
  且在 CI 里可不装 mcp 也能跑契约测试。
- 真实分发(发到 Claude Desktop / Cursor)请装 `mcp` 官方 SDK,自动走真实实现。
"""

from __future__ import annotations

import json
import sys
from typing import Any

from .core import extract_exif, summarize_batch

TOOL_SCHEMA = [
    {
        "name": "read_exif",
        "description": "读取单张照片 EXIF,返回与 TrailLens ExifMeta 对齐的 8 个字段。",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "本地文件绝对路径"}},
            "required": ["path"],
        },
    },
    {
        "name": "summarize_batch",
        "description": "对一组照片产出 EXIF 统计摘要(焦段范围 / GPS bbox / 相机机型)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "paths": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["paths"],
        },
    },
]


# --------------------------------------------------------------------------- #
# 业务 dispatch:tool 名 -> 函数,纯函数易测
# --------------------------------------------------------------------------- #
def dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "read_exif":
        return extract_exif(args["path"]).to_dict()
    if name == "summarize_batch":
        return summarize_batch(args.get("paths", []))
    raise ValueError(f"unknown_tool:{name}")


# --------------------------------------------------------------------------- #
# 优先用官方 mcp SDK
# --------------------------------------------------------------------------- #
def _serve_with_official_sdk() -> bool:
    try:
        from mcp.server import Server  # type: ignore
        from mcp.server.stdio import stdio_server  # type: ignore
        from mcp.types import TextContent, Tool  # type: ignore
    except ImportError:
        return False

    import anyio

    server = Server("traillens-exif")

    @server.list_tools()
    async def _list() -> list[Tool]:
        return [Tool(**t) for t in TOOL_SCHEMA]

    @server.call_tool()
    async def _call(name: str, arguments: dict) -> list[TextContent]:
        result = dispatch(name, arguments or {})
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    async def _run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    anyio.run(_run)
    return True


# --------------------------------------------------------------------------- #
# fallback:手写最小 JSON-RPC over stdio(只为本地 dev,不上生产)
# --------------------------------------------------------------------------- #
def _serve_fallback() -> None:
    sys.stderr.write("[traillens-exif] mcp SDK 未安装,启动 fallback stdio loop\n")
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue

        method = msg.get("method")
        msg_id = msg.get("id")
        if method == "tools/list":
            _reply(msg_id, {"tools": TOOL_SCHEMA})
        elif method == "tools/call":
            params = msg.get("params", {})
            try:
                out = dispatch(params.get("name", ""), params.get("arguments") or {})
                _reply(msg_id, {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}]})
            except Exception as e:  # noqa: BLE001
                _reply(msg_id, {"error": str(e)}, error=True)
        elif method == "initialize":
            _reply(msg_id, {"protocolVersion": "2025-11-25", "serverInfo": {"name": "traillens-exif", "version": "0.0.1"}})


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
