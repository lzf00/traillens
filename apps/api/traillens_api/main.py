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
from .routes import health, photos, trails
from .services.observability import init_sentry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(
    title="TrailLens API",
    version=__version__,
    description="多智能体摄影助手 HTTP API。前端契约见 docs/ARCHITECTURE.md §4.2。",
)
init_sentry(app)  # 没 SENTRY_DSN 自动 no-op

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(trails.router, prefix="/v1/trails", tags=["trails"])
app.include_router(photos.router, prefix="/v1/photos", tags=["photos"])
