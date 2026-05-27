"""FastAPI app entry。

启动:
    cd apps/api
    uvicorn traillens_api.main:app --reload --port 8000

设计要点:
- 所有依赖项(quota / current_user / db_session)集中在 deps.py,便于单测替换。
- 业务逻辑分到 services/,routes/ 只做参数解析 + 响应组装。
- 中间件链:CORS → 错误统一 → metrics → quota → 业务。
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .routes import billing, health, library, photos, settings as settings_route, trails
import os

from .middleware.rate_limit import RateLimitMiddleware
from .services.observability import init_sentry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(
    title="TrailLens API",
    version=__version__,
    description=(
        "多智能体摄影助手 HTTP API。\n\n"
        "**核心契约**:\n"
        "- 所有时间戳:UTC,ISO 8601\n"
        "- `text/event-stream` 端点用 W3C SSE,每条消息 `event: <name>\\ndata: <json>\\n\\n`\n"
        "- 认证:`Authorization: Bearer <token>` 或 cookie `better-auth.session`\n"
        "- 配额超限:HTTP 429 + `{detail: {error, remaining, requested, upgrade_url}}`\n\n"
        "更多见 [docs/ARCHITECTURE.md](https://github.com/lzf00/traillens/blob/main/docs/ARCHITECTURE.md#42-数据契约)。"
    ),
    contact={"name": "TrailLens", "url": "https://traillens.zorotreeking.online", "email": "hello@zorotreeking.online"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    openapi_tags=[
        {"name": "health", "description": "存活探针 / 就绪检查。"},
        {"name": "trails", "description": "Trail = 一次徒步 = 一个 agent run 容器。"},
        {"name": "photos", "description": "跨 trail 的照片操作(下载 / 公开分享)。"},
        {"name": "library", "description": "跨 trail 的语义搜索(Sprint 5 接 pgvector)。"},
        {"name": "settings", "description": "用户 API token + PIAA 偏好。"},
        {"name": "billing", "description": "Stripe checkout + webhook。"},
    ],
    servers=[
        {"url": "https://api.traillens.zorotreeking.online", "description": "production"},
        {"url": "http://localhost:8000", "description": "local dev"},
    ],
)
init_sentry(app)  # 没 SENTRY_DSN 自动 no-op

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 测试时通过 TRAILLENS_DISABLE_RATELIMIT=1 关掉(不然 60 个 test 撞限流)
app.add_middleware(
    RateLimitMiddleware,
    enabled=os.environ.get("TRAILLENS_DISABLE_RATELIMIT") != "1",
)

app.include_router(health.router)
app.include_router(trails.router, prefix="/v1/trails", tags=["trails"])
app.include_router(photos.router, prefix="/v1/photos", tags=["photos"])
app.include_router(billing.router, prefix="/v1/billing", tags=["billing"])
app.include_router(library.router, prefix="/v1/library", tags=["library"])
app.include_router(settings_route.router, prefix="/v1/settings", tags=["settings"])
