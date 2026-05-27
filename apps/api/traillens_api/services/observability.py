"""可观测性三件套封装。

策略:
  - 所有 SDK init 都是 *可选* 的:装了 + 设了 DSN 才启用,否则 no-op
  - 业务代码只 import 这里的 wrap 函数,不直接 import sentry_sdk / langfuse / posthog
  - 一个第三方故障不能拖垮主流程(全部 try/except)

集成位置:
  - Sentry → apps/api/main.py:app 创建后 install
  - Langfuse → orchestrator.py:每个 SSE 事件
  - PostHog → 由 web 前端 SDK 收集,server 端只发 server-side event(如 stripe webhook)
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any

from ..config import get_settings

log = logging.getLogger("traillens.obs")


# --------------------------------------------------------------------------- #
# Sentry
# --------------------------------------------------------------------------- #
def init_sentry(app) -> None:
    """在 FastAPI app 上安装 Sentry middleware。"""
    s = get_settings()
    if not s.sentry_dsn:
        log.info("sentry: no DSN; skipping")
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        log.warning("sentry_sdk not installed; skipping")
        return
    try:
        sentry_sdk.init(
            dsn=s.sentry_dsn,
            environment=s.env,
            traces_sample_rate=0.1 if s.env == "prod" else 1.0,
            profiles_sample_rate=0.1 if s.env == "prod" else 1.0,
            integrations=[FastApiIntegration(), StarletteIntegration()],
        )
        log.info("sentry: initialized for env=%s", s.env)
    except Exception as e:  # noqa: BLE001
        log.error("sentry init failed: %s", e)


def capture_exception(e: Exception) -> None:
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(e)
    except ImportError:
        pass


# --------------------------------------------------------------------------- #
# Langfuse — LLM observability
# --------------------------------------------------------------------------- #
_langfuse_client = None


def langfuse_client():
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client
    s = get_settings()
    pk = os.environ.get("LANGFUSE_PUBLIC_KEY")
    sk = os.environ.get("LANGFUSE_SECRET_KEY")
    if not (pk and sk):
        return None
    try:
        from langfuse import Langfuse
    except ImportError:
        return None
    try:
        _langfuse_client = Langfuse(
            public_key=pk, secret_key=sk, host=s.langfuse_host or "https://cloud.langfuse.com",
        )
        return _langfuse_client
    except Exception:  # noqa: BLE001
        return None


@contextmanager
def trace_agent_run(run_id: str, trail_id: str, user_id: str):
    """包住一次 agent run,自动把开始/结束/异常报给 Langfuse。"""
    client = langfuse_client()
    if not client:
        yield None
        return
    trace = client.trace(
        id=run_id,
        name="trail_run",
        user_id=user_id,
        metadata={"trail_id": trail_id},
    )
    try:
        yield trace
    except Exception as e:  # noqa: BLE001
        trace.update(level="ERROR", status_message=str(e))
        capture_exception(e)
        raise
    finally:
        try:
            client.flush()
        except Exception:  # noqa: BLE001
            pass


def log_agent_event(run_id: str, event: str, data: dict[str, Any]) -> None:
    """把 SSE event 同步登到 Langfuse(作为 trace 的 span)。"""
    client = langfuse_client()
    if not client:
        return
    try:
        client.event(trace_id=run_id, name=event, metadata=data)
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- #
# PostHog — product analytics(server-side)
# --------------------------------------------------------------------------- #
_posthog_client = None


def posthog_client():
    global _posthog_client
    if _posthog_client is not None:
        return _posthog_client
    key = os.environ.get("POSTHOG_API_KEY")
    if not key:
        return None
    try:
        from posthog import Posthog
    except ImportError:
        return None
    try:
        _posthog_client = Posthog(
            project_api_key=key,
            host=os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com"),
        )
        return _posthog_client
    except Exception:  # noqa: BLE001
        return None


def capture_event(user_id: str, event: str, props: dict[str, Any] | None = None) -> None:
    """server-side event(stripe webhook / agent finish 等)。"""
    client = posthog_client()
    if not client:
        return
    try:
        client.capture(distinct_id=user_id, event=event, properties=props or {})
    except Exception:  # noqa: BLE001
        pass
