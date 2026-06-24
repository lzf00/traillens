# OAuth 一键登录配置（Google / GitHub）

后端代码就绪（`apps/api/traillens_api/routes/oauth.py`），只缺凭证。

## 一、Google OAuth

1. 打开 https://console.cloud.google.com/apis/credentials
2. **创建凭据 → OAuth 客户端 ID → Web 应用**
3. 填：
   - **名称**：`TrailLens Prod`
   - **已获授权的 JavaScript 来源**：`https://traillens.zorotreeking.online`
   - **已获授权的重定向 URI**：`https://traillens.zorotreeking.online/v1/auth/oauth/google/callback`
4. 创建后页面拿到 `client_id` 和 `client_secret`
5. （首次用必做）OAuth 同意屏幕 → 用户类型选 **外部**，应用名/邮箱填好后**发布**

## 二、GitHub OAuth

1. https://github.com/settings/developers → **New OAuth App**
2. 填：
   - **Application name**：`TrailLens`
   - **Homepage URL**：`https://traillens.zorotreeking.online`
   - **Authorization callback URL**：`https://traillens.zorotreeking.online/v1/auth/oauth/github/callback`
3. 创建后 **Generate a new client secret**，记下 `client_id` 和 `client_secret`

## 三、写入服务器 .env

```bash
ssh root@traillens-server
cat >> /opt/traillens/.env <<EOF
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
GITHUB_CLIENT_ID=Iv1.xxx
GITHUB_CLIENT_SECRET=xxx
EOF

cd /opt/traillens && docker compose --env-file .env -f infra/prod/docker-compose.prod.yml up -d api
```

## 四、国内服务器墙问题

国内 CVM 调 `oauth2.googleapis.com` / `api.github.com` 经常超时。**两种解决**：

### 方案 A：本地 HTTP 代理（最简）
```bash
echo 'OAUTH_HTTP_PROXY=http://your-proxy:port' >> /opt/traillens/.env
```
适合：你已有外网代理。

### 方案 B：CF Worker 中转（推荐 build-in-public）
部署一个 Cloudflare Worker 把 `/google/token`、`/github/user` 这些路径反代到对应 endpoint，把 worker URL 写到 env：
```bash
echo 'OAUTH_PROXY_BASE=https://oauth-proxy.your-worker.workers.dev' >> /opt/traillens/.env
```
适合：长期稳定 + 不暴露代理凭证。Worker 代码模板见 `infra/cf-workers/oauth-proxy/`（待写）。

## 五、验证

```bash
# 路由可达性
curl -sS -o /dev/null -w "%{http_code}\n" https://traillens.zorotreeking.online/v1/auth/oauth/google/start
# → 302（成功跳 Google）
# → 503（缺凭证，检查 .env）

# 浏览器
# 1. 打开 /login → 点「用 Google 登录」
# 2. 第三方页授权
# 3. 跳回 /trails，Nav 显示你的 Google 邮箱
```

## 六、故障排查

| 现象 | 原因 |
|---|---|
| `oauth_state` 不匹配 | 浏览器禁了第三方 cookie 或跨域；确认重定向 URI 完全匹配 |
| `redirect_uri_mismatch` | console 里填的 URI 跟实际 callback 不一致（末尾斜杠也算） |
| token endpoint 超时 | 国内墙，配 `OAUTH_HTTP_PROXY` 或 `OAUTH_PROXY_BASE` |
| Google 同意屏未发布 | 测试模式下只有添加为测试用户的邮箱能登 |
