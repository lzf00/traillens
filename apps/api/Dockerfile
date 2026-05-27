# 多阶段构建:builder 装包,runtime 极简(更小镜像 + 启动更快)。
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# 装依赖(独立层,代码变化时不重新跑)
COPY apps/api/pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install \
    "fastapi>=0.110" "uvicorn[standard]>=0.27" "pydantic>=2.7" \
    "sqlalchemy>=2.0" "psycopg[binary]>=3.1" "alembic>=1.13" \
    "httpx>=0.27" "redis>=5.0" \
    "openai>=1.50" "qiniu>=7.13" \
    "sentry-sdk[fastapi]>=2.0" "langfuse>=2.0"

# ---------- runtime ----------
FROM python:3.11-slim
WORKDIR /app

# 非 root 用户(安全 + Fly.io 推荐)
RUN groupadd --system app && useradd --system --gid app --home /app app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 ca-certificates && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

# Monorepo 布局:agents/aesthetic 包也要 COPY 进来(API 在进程内调它们)
COPY --chown=app:app apps/api/ /app/api/
COPY --chown=app:app packages/agents/ /app/packages/agents/
COPY --chown=app:app packages/aesthetic/ /app/packages/aesthetic/
COPY --chown=app:app packages/mcp_servers/ /app/packages/mcp_servers/

USER app

# 让进程内 import 找到 monorepo 各模块
ENV PYTHONPATH=/app/api:/app/packages/agents
ENV PORT=8000

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz').read()" || exit 1

# Sprint 5:启动前跑 alembic upgrade head
CMD ["uvicorn", "traillens_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
