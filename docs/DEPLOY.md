# 部署指引

> 4 套独立部署链路。任一可单独 ship,互不阻塞。

| 组件 | 平台 | 配置文件 | 单月起步成本 |
|---|---|---|---|
| `apps/web` | Vercel | [`apps/web/vercel.json`](../apps/web/vercel.json) | $0(Hobby)|
| `apps/api` | Fly.io | [`apps/api/fly.toml`](../apps/api/fly.toml) + Dockerfile | $5-10 |
| `packages/aesthetic` | Modal | [`packages/aesthetic/serve.py`](../packages/aesthetic/serve.py) | 按调用 |
| Postgres + Redis | Fly Postgres + Upstash | 见下 | $0-5(免费层够 MVP)|

---

## 1. apps/web → Vercel(5 分钟)

```bash
# 1) 登录 + 关联
cd apps/web
npx vercel link

# 2) 设环境变量(在 Vercel 网页或 CLI)
npx vercel env add NEXT_PUBLIC_API_BASE production
# → 输入: https://api.traillens.app
npx vercel env add NEXT_PUBLIC_POSTHOG_KEY production
npx vercel env add BETTER_AUTH_SECRET production
npx vercel env add DATABASE_URL production

# 3) 部署
npx vercel --prod
```

绑定域名:Vercel → Project → Domains → 加 `traillens.app`(按提示在 Cloudflare 设 CNAME)。

---

## 2. apps/api → Fly.io(10 分钟)

```bash
# 0) 装 flyctl
curl -L https://fly.io/install.sh | sh

# 1) 在 monorepo 根创建 app(需要 packages/ 在 build context)
fly launch --no-deploy --copy-config --name traillens-api \
  --org personal --region hkg --dockerfile apps/api/Dockerfile \
  --config apps/api/fly.toml

# 2) Postgres
fly postgres create --name traillens-pg --region hkg --vm-size shared-cpu-1x --volume-size 3
fly postgres attach traillens-pg --app traillens-api
fly postgres connect -a traillens-pg -d traillens
  # 在 psql:
  > CREATE EXTENSION IF NOT EXISTS vector;
  > CREATE EXTENSION IF NOT EXISTS postgis;
  > CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

# 3) Redis(用 Upstash 集成)
fly redis create --name traillens-redis --region hkg --plan free --eviction allkeys-lru
fly redis attach traillens-redis --app traillens-api

# 4) Secrets(秘密一次性注入)
fly secrets set \
  ANTHROPIC_API_KEY=sk-ant-... \
  QWEN_VL_API_KEY=sk-... \
  BETTER_AUTH_SECRET="$(openssl rand -hex 32)" \
  STRIPE_SECRET_KEY=sk_live_... \
  STRIPE_WEBHOOK_SECRET=whsec_... \
  R2_ACCESS_KEY_ID=... \
  R2_SECRET_ACCESS_KEY=... \
  SENTRY_DSN=https://...@sentry.io/... \
  LANGFUSE_PUBLIC_KEY=pk-lf-... \
  LANGFUSE_SECRET_KEY=sk-lf-... \
  --app traillens-api

# 5) 第一次部署(会自动跑 alembic upgrade head)
fly deploy --config apps/api/fly.toml --dockerfile apps/api/Dockerfile

# 6) 自定义域名
fly certs add api.traillens.app
# → 按提示在 Cloudflare 加 CNAME api → traillens-api.fly.dev
```

监控:
```bash
fly logs        # 实时日志
fly status      # 实例状态
fly ssh console # 进容器
fly scale show  # 当前规模
```

紧急回滚:
```bash
fly releases    # 看版本号
fly deploy --image registry.fly.io/traillens-api:deployment-XXX  # 回滚到指定版本
```

---

## 3. packages/aesthetic → Modal(15 分钟)

```bash
# 0) 装 modal + token
pip install modal && modal token new

# 1) 创建持久 volume + secrets
modal volume create traillens-models
modal volume create traillens-data
modal secret create traillens-aesthetic \
  --from-literal AUTH_TOKEN=$(openssl rand -hex 32)

# 2) 上传训练数据(本地有 photos/ 与 annotations 后)
modal volume put traillens-data ./packages/annotation/data /
modal volume put traillens-data ./photos /images

# 3) 部署推理 endpoint(serve.py)
modal deploy packages/aesthetic/serve.py
# → 拿到 https://your-handle--traillens-aesthetic-fastapi-app.modal.run

# 4) 把 endpoint 写回 Fly secret
fly secrets set TRAILLENS_AESTHETIC_ENDPOINT=https://...modal.run --app traillens-api

# 5) 训练(数据齐了再跑;预算见 train_modal.py 注释)
modal secret create traillens-train --from-env WANDB_API_KEY
modal run packages/aesthetic/train_modal.py::run --use-exif true --run-name v0
```

---

## 4. 域名 DNS(Cloudflare)

最终拓扑:

```
traillens.app          → Vercel(web)
api.traillens.app      → Fly.io
photos.traillens.app   → Cloudflare R2 自定义域(public read)
docs.traillens.app     → Vercel(同一项目的 /docs 子路径,或独立 Mintlify)
```

DNS 记录(全部 Proxied):
```
A      @       76.76.21.21              Vercel 入口
CNAME  www     cname.vercel-dns.com.    Vercel
CNAME  api     traillens-api.fly.dev.   Fly
CNAME  photos  <r2-public-bucket-url>   R2
TXT    @       google-site-verification=...
TXT    _dmarc  v=DMARC1; p=quarantine; rua=mailto:hello@traillens.app
```

---

## 5. CI/CD(GitHub Actions)

已有 `.github/workflows/ci.yml`(test 跑在每个 PR)。
Sprint 4 末加 `deploy.yml`:`main` push 自动 `fly deploy` + `vercel --prod`。

模板:

```yaml
# .github/workflows/deploy.yml (Sprint 4 末添加)
on:
  push:
    branches: [main]
jobs:
  deploy-api:
    needs: [contract-tests, full-tests]   # 必须 CI 全绿
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only --config apps/api/fly.toml
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
  deploy-web:
    needs: [web-typecheck]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
          working-directory: apps/web
```

---

## 6. 成本预警

设置 Fly 与 Modal 的预算告警,任何一个超 $20/月触发邮件:

```bash
fly settings billing-alerts --limit 20 --email you@example.com
# Modal: 在 web 控制台 Settings → Usage Alerts
```
