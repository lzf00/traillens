# 可观测性配置（Langfuse + Sentry）

后端代码已集成 trace_agent_run / log_agent_event，只需配置环境变量即可启用。

## Langfuse（agent trace + token 成本）

### 1. 注册账号 + 拿 key
https://cloud.langfuse.com → Sign up → 创建项目 `traillens` → Settings → API Keys → New API key
拿 **Public Key** (`pk-lf-...`) + **Secret Key** (`sk-lf-...`)

### 2. 写到服务器 .env

```bash
ssh root@110.40.142.199 << 'EOF'
cat >> /opt/traillens/.env << 'ENV'

# Langfuse
LANGFUSE_PUBLIC_KEY=<你的 public key>
LANGFUSE_SECRET_KEY=<你的 secret key>
LANGFUSE_HOST=https://cloud.langfuse.com
ENV
echo "Langfuse env 写入"
EOF
```

### 3. compose 透传（一次性，告诉我后我做）

我会在 `infra/prod/docker-compose.prod.yml` 加 3 行透传 + 重启 api。

### 4. 验证

跑一次 trail Run，然后到 Langfuse 控制台 → Tracing → 应当看到 `trail_run` trace，包含每个 SSE 事件（culling.photo_scored / story.delta 等）+ 豆包 API 调用的 token 用量 + 累计费用。

---

## Sentry（错误监控）

类似流程：https://sentry.io 注册 → 新建 Python project → 拿 DSN → 写到 `.env`：

```
SENTRY_DSN=https://...@sentry.io/...
```

代码里 `init_sentry(app)` 在 `apps/api/main.py` 已调，配上即生效。
