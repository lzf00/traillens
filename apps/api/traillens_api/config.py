"""集中配置(env-var DI)。

设计:
- 单例 + lru_cache,首次访问加载,之后零成本。
- 用 pydantic BaseModel(项目已依赖)做强校验;不引入 pydantic-settings 减小依赖。
- 任何新增 env var 都登记在这里,routes 不直接读 os.environ。

注入:
    from fastapi import Depends
    from .config import get_settings, Settings

    @router.get("/foo")
    def foo(s: Settings = Depends(get_settings)):
        return {"env": s.env}
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field


class Settings(BaseModel):
    # ---- 运行环境 ----
    env: Literal["local", "staging", "prod"] = "local"
    log_level: str = "info"

    # ---- 数据库 / 缓存 ----
    database_url: str | None = None
    redis_url: str | None = None

    # ---- LLM ----
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-4-7"
    qwen_vl_base_url: str = "https://api.siliconflow.cn/v1"
    qwen_vl_api_key: str | None = None
    qwen_vl_model: str = "Qwen/Qwen3-VL-32B-Instruct"

    # ---- 美学评分(契约 7 接口) ----
    aesthetic_endpoint: str | None = None
    aesthetic_token: str | None = None

    # ---- 对象存储 ----
    r2_bucket: str | None = None
    r2_public_base: str | None = None

    # ---- 鉴权(Better-Auth) ----
    better_auth_secret: str | None = None

    # ---- 计费 ----
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None

    # ---- 可观测性 ----
    langfuse_host: str | None = None
    sentry_dsn: str | None = None

    # ---- agent 行为开关 ----
    use_stubs: bool = False  # TRAILLENS_USE_STUBS=1 → True
    mcp_transport: Literal["inprocess", "stdio", "http"] = "inprocess"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            env=os.environ.get("TRAILLENS_ENV", "local"),  # type: ignore
            log_level=os.environ.get("LOG_LEVEL", "info"),
            database_url=os.environ.get("DATABASE_URL"),
            redis_url=os.environ.get("REDIS_URL"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7"),
            qwen_vl_base_url=os.environ.get("QWEN_VL_BASE_URL", "https://api.siliconflow.cn/v1"),
            qwen_vl_api_key=os.environ.get("QWEN_VL_API_KEY"),
            qwen_vl_model=os.environ.get("QWEN_VL_MODEL", "Qwen/Qwen3-VL-32B-Instruct"),
            aesthetic_endpoint=os.environ.get("TRAILLENS_AESTHETIC_ENDPOINT"),
            aesthetic_token=os.environ.get("TRAILLENS_AESTHETIC_TOKEN"),
            r2_bucket=os.environ.get("R2_BUCKET"),
            r2_public_base=os.environ.get("R2_PUBLIC_BASE"),
            better_auth_secret=os.environ.get("BETTER_AUTH_SECRET"),
            stripe_secret_key=os.environ.get("STRIPE_SECRET_KEY"),
            stripe_webhook_secret=os.environ.get("STRIPE_WEBHOOK_SECRET"),
            langfuse_host=os.environ.get("LANGFUSE_HOST"),
            sentry_dsn=os.environ.get("SENTRY_DSN"),
            use_stubs=os.environ.get("TRAILLENS_USE_STUBS") == "1",
            mcp_transport=os.environ.get("TRAILLENS_MCP_TRANSPORT", "inprocess"),  # type: ignore
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
