"""Health endpoints。

约定(Kubernetes / Fly.io 通用):
  /healthz  liveness  — 进程活着就 200。绝对不能查外部依赖,
                          否则一个外部抖动会被 orchestrator 当成"进程死了"重启。
  /readyz   readiness — 真正检 DB / Redis / Modal 联通,
                          挂了 503 → load balancer 把流量切走,但不会被重启。
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter, Response

from .. import __version__

router = APIRouter(tags=["health"])
log = logging.getLogger("traillens.health")

CHECK_TIMEOUT_S = 2.0


@router.get("/healthz")
def healthz() -> dict:
    """Liveness — 只要进程能响应这个 endpoint 就 OK。"""
    return {"status": "ok", "version": __version__}


@router.get("/readyz")
async def readyz(response: Response) -> dict:
    """Readiness — 检 4 个关键依赖,任一挂掉 503。"""
    started = time.time()
    checks = await asyncio.gather(
        _check_db(), _check_redis(), _check_aesthetic_endpoint(), _check_mcp_inprocess(),
        return_exceptions=True,
    )
    db, redis_c, aesthetic, mcp = checks
    all_ok = all(c.get("ok") for c in checks if isinstance(c, dict))
    if not all_ok:
        response.status_code = 503
    return {
        "ready": all_ok,
        "version": __version__,
        "checks": {"db": db, "redis": redis_c, "aesthetic": aesthetic, "mcp": mcp},
        "took_ms": int((time.time() - started) * 1000),
    }


# --------------------------------------------------------------------------- #
# 单项检查 — 每个都有自己的超时与"无配置时跳过"逻辑
# --------------------------------------------------------------------------- #
async def _check_db() -> dict[str, Any]:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return {"ok": True, "skipped": "no DATABASE_URL"}
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        return {"ok": True, "skipped": "sqlalchemy not installed"}
    try:
        # 这里同步连,因为 SA async engine 加 asyncpg 依赖太重;readyz 慢一点 OK
        engine = create_engine(db_url, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"}


async def _check_redis() -> dict[str, Any]:
    url = os.environ.get("REDIS_URL")
    if not url:
        return {"ok": True, "skipped": "no REDIS_URL"}
    try:
        import redis  # type: ignore
    except ImportError:
        return {"ok": True, "skipped": "redis package not installed"}
    try:
        client = redis.Redis.from_url(url, socket_timeout=2)
        client.ping()
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"}


async def _check_aesthetic_endpoint() -> dict[str, Any]:
    endpoint = os.environ.get("TRAILLENS_AESTHETIC_ENDPOINT")
    if not endpoint:
        return {"ok": True, "skipped": "no TRAILLENS_AESTHETIC_ENDPOINT"}
    try:
        async with httpx.AsyncClient(timeout=CHECK_TIMEOUT_S) as client:
            r = await client.get(f"{endpoint.rstrip('/')}/healthz")
            return {"ok": r.status_code == 200, "status": r.status_code}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"}


async def _check_mcp_inprocess() -> dict[str, Any]:
    """MCP 的 in-process 路径:能 import + 能 dispatch 就算通。"""
    import sys
    from pathlib import Path
    mcp_root = Path(__file__).resolve().parents[4] / "packages" / "mcp_servers"
    if not mcp_root.exists():
        return {"ok": False, "error": "mcp_servers dir missing"}
    sys.path.insert(0, str(mcp_root / "traillens_sunmoon"))
    try:
        from traillens_sunmoon import moon_phase  # type: ignore
        out = moon_phase("2026-05-27")
        return {"ok": "phase" in out}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"}
