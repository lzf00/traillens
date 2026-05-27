"""Rate limiting middleware — Redis token bucket + in-memory fallback。

策略:
- key 优先级:Authorization Bearer 前 12 位 > X-Forwarded-For > client.host
- 每 endpoint 不同 limit(写比读严)
- 超限返回 429 + Retry-After header
- /healthz / /readyz / 静态资源不限流

Sprint 5 末:Stripe webhook 路径走更严格的反重放限流。
"""

from __future__ import annotations

import logging
import os
import time
from typing import Awaitable, Callable

# fastapi / starlette 在无 deps CI 不可用 → 纯算法部分(path 归一化、token bucket)
# 仍可单测;只有 dispatch 这层需要 starlette
try:
    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse
    HAS_STARLETTE = True
except ImportError:
    HAS_STARLETTE = False

    class BaseHTTPMiddleware:  # type: ignore
        def __init__(self, app): self.app = app

        async def dispatch(self, request, call_next):
            return await call_next(request)

    class Request:  # type: ignore
        pass

    class JSONResponse:  # type: ignore
        def __init__(self, *a, **kw): pass

log = logging.getLogger("traillens.ratelimit")

# 每 endpoint:(每分钟最大请求数, burst)
DEFAULT_LIMIT = (120, 30)
LIMITS = {
    "POST /v1/trails": (30, 10),
    "POST /v1/trails/run": (10, 3),       # SSE 启动重,严
    "POST /v1/billing/checkout": (10, 3),
    "POST /v1/billing/webhook": (1000, 100),  # Stripe 重试可能爆,放松
    "POST /v1/settings/tokens": (10, 3),
}

# 不限流路径
EXEMPT_PATHS = {"/healthz", "/readyz", "/docs", "/openapi.json", "/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self._redis = None
        self._mem: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable]):
        if not self.enabled or request.url.path in EXEMPT_PATHS:
            return await call_next(request)
        if request.url.path.startswith("/static") or request.url.path.startswith("/og"):
            return await call_next(request)

        key = self._client_key(request)
        endpoint_key = f"{request.method} {self._normalize_path(request.url.path)}"
        limit, burst = LIMITS.get(endpoint_key, DEFAULT_LIMIT)

        allowed, retry_after = self._consume(key, endpoint_key, limit, burst)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limited",
                    "endpoint": endpoint_key,
                    "limit_per_minute": limit,
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

    # ----- helpers -----
    def _client_key(self, request: Request) -> str:
        # 优先用 Bearer token 前 12 位(更精准)
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            return "bearer:" + auth[7:19]
        # 然后 X-Forwarded-For(经 Fly / CF 代理后真 IP)
        xff = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if xff:
            return f"ip:{xff}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    def _normalize_path(self, path: str) -> str:
        """把 /v1/trails/<uuid>/run 归一为 /v1/trails/run。"""
        parts = path.strip("/").split("/")
        normalized = []
        for p in parts:
            # uuid-like:36 字符含 4 个 dash
            if len(p) == 36 and p.count("-") == 4:
                continue
            normalized.append(p)
        return "/" + "/".join(normalized)

    def _redis_client(self):
        if self._redis is not None:
            return self._redis
        url = os.environ.get("REDIS_URL")
        if not url:
            return None
        try:
            import redis  # type: ignore
            self._redis = redis.Redis.from_url(url, decode_responses=True, socket_timeout=0.5)
            self._redis.ping()
        except Exception:  # noqa: BLE001
            self._redis = None
        return self._redis

    def _consume(self, client_key: str, endpoint_key: str, limit: int, burst: int) -> tuple[bool, int]:
        """token bucket:返回 (allowed, retry_after_seconds)。"""
        now = time.time()
        cap = limit + burst
        rate_per_sec = limit / 60.0
        full_key = f"rl:{client_key}:{endpoint_key}"

        r = self._redis_client()
        if r is not None:
            try:
                pipe = r.pipeline()
                pipe.hmget(full_key, "tokens", "last")
                pipe.expire(full_key, 120)
                tokens_s, last_s = pipe.execute()[0]
                tokens = float(tokens_s) if tokens_s else float(cap)
                last = float(last_s) if last_s else now
                tokens = min(cap, tokens + (now - last) * rate_per_sec)
                if tokens < 1:
                    retry = int(max(1, (1 - tokens) / rate_per_sec))
                    r.hset(full_key, mapping={"tokens": tokens, "last": now})
                    return False, retry
                r.hset(full_key, mapping={"tokens": tokens - 1, "last": now})
                return True, 0
            except Exception:  # noqa: BLE001  Redis 错 → fallback in-memory
                pass

        # in-memory fallback(进程内,scale-out 时不准但不致命)
        bucket = self._mem.setdefault(full_key, [float(cap), now])
        tokens, last = bucket
        tokens = min(cap, tokens + (now - last) * rate_per_sec)
        if tokens < 1:
            retry = int(max(1, (1 - tokens) / rate_per_sec))
            bucket[0], bucket[1] = tokens, now
            return False, retry
        bucket[0], bucket[1] = tokens - 1, now
        return True, 0
