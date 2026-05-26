"""MCP client 抽象 — 把"调用哪种 transport"从业务代码解耦。

三种 transport 优先级(由 env 控制):
  1. TRAILLENS_MCP_TRANSPORT=stdio: 启 subprocess,JSON-RPC over stdin/stdout
  2. TRAILLENS_MCP_TRANSPORT=http:  调远端 HTTP(用于 Cloudflare Workers 上的 server)
  3. (默认 / 未设)inprocess:直接 import server 模块的 dispatch 函数 — 最快,适合本地 dev

生产模式建议 stdio,因为:
  - server 进程隔离 → 一个 server 崩不会拖累 agent
  - 可独立观测 / 限流 / 滚动重启
  - 与 Claude Desktop 等其它 MCP 客户端共用同一份 server,不分叉
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_MCP_ROOT = Path(__file__).resolve().parents[4] / "packages" / "mcp_servers"


class MCPClient:
    """单个 MCP server 的客户端句柄。"""

    def __init__(self, server_name: str):
        self.server_name = server_name  # e.g. "traillens_exif"
        self._proc: subprocess.Popen | None = None
        self._req_id = 0

    # ----- 公开:call a tool -----
    def call(self, tool: str, **arguments: Any) -> dict[str, Any] | None:
        transport = os.environ.get("TRAILLENS_MCP_TRANSPORT", "inprocess")
        if transport == "stdio":
            return self._call_stdio(tool, arguments)
        if transport == "http":
            return self._call_http(tool, arguments)
        return self._call_inprocess(tool, arguments)

    def close(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=1.0)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                self._proc.kill()
            self._proc = None

    # ----- in-process(开发期默认) -----
    def _call_inprocess(self, tool: str, args: dict) -> dict | None:
        pkg_path = _MCP_ROOT / self.server_name
        if not pkg_path.exists():
            return None
        if str(pkg_path) not in sys.path:
            sys.path.insert(0, str(pkg_path))
        try:
            server_mod = __import__(f"{self.server_name}.server", fromlist=["dispatch"])
        except ImportError:
            return None
        try:
            return server_mod.dispatch(tool, args)
        except Exception:  # noqa: BLE001
            return None

    # ----- stdio subprocess -----
    def _ensure_subprocess(self) -> subprocess.Popen | None:
        if self._proc is not None and self._proc.poll() is None:
            return self._proc
        pkg_path = _MCP_ROOT / self.server_name
        if not pkg_path.exists():
            return None
        self._proc = subprocess.Popen(
            [sys.executable, "-m", self.server_name],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(pkg_path), text=True, bufsize=1,
        )
        # 握手:initialize
        self._jsonrpc("initialize", {})
        return self._proc

    def _jsonrpc(self, method: str, params: dict | None = None) -> dict | None:
        proc = self._ensure_subprocess()
        if not proc or not proc.stdin or not proc.stdout:
            return None
        self._req_id += 1
        msg = {"jsonrpc": "2.0", "id": self._req_id, "method": method}
        if params is not None:
            msg["params"] = params
        try:
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            if not line:
                return None
            return json.loads(line)
        except (OSError, ValueError):
            return None

    def _call_stdio(self, tool: str, args: dict) -> dict | None:
        resp = self._jsonrpc("tools/call", {"name": tool, "arguments": args})
        if not resp:
            return None
        if "error" in resp:
            return None
        content = (resp.get("result") or {}).get("content") or []
        if not content:
            return None
        # MCP 规范:content[0].text 是 JSON 字符串
        text = content[0].get("text")
        try:
            return json.loads(text)
        except (TypeError, json.JSONDecodeError):
            return None

    # ----- http transport(生产远端,带 Redis cache) -----
    def _call_http(self, tool: str, args: dict) -> dict | None:
        try:
            import httpx  # type: ignore
        except ImportError:
            return None
        base = os.environ.get(f"MCP_{self.server_name.upper()}_URL")
        if not base:
            return None

        cache_key = _cache_key(self.server_name, tool, args)
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
        try:
            resp = httpx.post(
                f"{base.rstrip('/')}/tools/{tool}",
                json=args, timeout=10.0,
            )
            resp.raise_for_status()
            out = resp.json()
        except Exception:  # noqa: BLE001
            return None
        ttl = _CACHE_TTL.get((self.server_name, tool), _DEFAULT_TTL)
        _cache_set(cache_key, out, ttl)
        return out


# --------------------------------------------------------------------------- #
# 单例:每个 server 一个长连接,在进程退出时由 atexit 收尾
# --------------------------------------------------------------------------- #
import atexit
import hashlib

# ---- 缓存(Redis 优先,无 Redis 时降为进程内 dict) ----------------------------
_DEFAULT_TTL = 600  # 10 分钟
_CACHE_TTL = {
    ("traillens_weather", "weather_at"): 1800,   # 30 分钟
    ("traillens_weather", "forecast"): 3600,     # 1 小时
    ("traillens_sunmoon", "sun_moon_times"): 86400,  # 1 天(同地点同日不变)
    ("traillens_sunmoon", "moon_phase"): 86400,
}
_MEM_CACHE: dict[str, tuple[float, dict]] = {}
_redis_client = None


def _redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    url = os.environ.get("REDIS_URL")
    if not url:
        return None
    try:
        import redis  # type: ignore
    except ImportError:
        return None
    try:
        _redis_client = redis.Redis.from_url(url, decode_responses=True, socket_timeout=1)
        _redis_client.ping()
        return _redis_client
    except Exception:  # noqa: BLE001
        _redis_client = None
        return None


def _cache_key(server: str, tool: str, args: dict) -> str:
    h = hashlib.sha1(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return f"mcp:{server}:{tool}:{h}"


def _cache_get(key: str) -> dict | None:
    r = _redis()
    if r is not None:
        try:
            raw = r.get(key)
            return json.loads(raw) if raw else None
        except Exception:  # noqa: BLE001
            pass
    import time
    entry = _MEM_CACHE.get(key)
    if not entry:
        return None
    expire_at, val = entry
    if time.time() > expire_at:
        del _MEM_CACHE[key]
        return None
    return val


def _cache_set(key: str, val: dict, ttl: int) -> None:
    r = _redis()
    if r is not None:
        try:
            r.setex(key, ttl, json.dumps(val, default=str))
            return
        except Exception:  # noqa: BLE001
            pass
    import time
    _MEM_CACHE[key] = (time.time() + ttl, val)


_CLIENTS: dict[str, MCPClient] = {}


def client(server_name: str) -> MCPClient:
    if server_name not in _CLIENTS:
        _CLIENTS[server_name] = MCPClient(server_name)
    return _CLIENTS[server_name]


@atexit.register
def _close_all():
    for c in _CLIENTS.values():
        c.close()
