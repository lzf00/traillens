# 腾讯云 CVM 生产部署

> 一台腾讯云 CVM,docker-compose 跑全套(API + Postgres + Redis + Caddy + 可选 Langfuse)。
> 起步配置:**2c4g 50G,约 ¥50/月**;能撑住 1000 注册 / 100 DAU。

## 你要给我的信息

部署前请告诉我:

1. **公网 IP**(公开就行,我会写到文档里)
2. 服务器规格(2c4g / 4c8g 等)
3. 操作系统(`cat /etc/os-release | head -3` 给我看)
4. 是否装了 Docker(`docker --version`)
5. SSH 你怎么登(密钥 / 密码)— **不要给我密钥,只告诉我"我能 ssh"即可**

## 你要自己操作的(我没法替你做)

```bash
# 1. SSH 登服务器
ssh root@<你的-IP>

# 2. 装 Docker(如果没装)
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
apt install -y docker-compose-plugin   # 或 yum,看发行版

# 3. 拉代码
cd /opt
git clone https://github.com/lzf00/traillens
cd traillens

# 4. 准备 .env
cp .env.example .env
nano .env       # 至少填这 3 个:
                #   ARK_API_KEY=<你的豆包 key>
                #   POSTGRES_PASSWORD=<生成强密码:openssl rand -hex 16>
                #   QINIU_ACCESS_KEY / QINIU_SECRET_KEY / QINIU_DOMAIN(七牛云)
                # 其他都可以留空(SENTRY/LANGFUSE 等可选)

# 5. 一键部署
bash infra/prod/deploy.sh

# 6. 在腾讯云域名解析后台加:
#    A      api.traillens     <这台 CVM 公网 IP>
#    A      traillens         <这台 CVM 公网 IP>(若 web 也部署在此)
```

## 验证部署成功

```bash
# 在服务器上
curl -fsS http://localhost:8000/healthz
# → {"status":"ok","version":"0.0.1"}

# 5 分钟后在你本地浏览器
open https://api.traillens.zorotreeking.online/healthz
open https://api.traillens.zorotreeking.online/docs   # Swagger UI
```

## 升级 / 回滚

```bash
# 升级
cd /opt/traillens
git pull
bash infra/prod/deploy.sh
# → 自动 build 新镜像 + alembic upgrade head + 滚动重启

# 回滚到上一版
git log --oneline -5
git checkout <要回到的-commit-hash>
bash infra/prod/deploy.sh
```

## 启用 Langfuse(LLM 观测)

```bash
docker compose --profile observability -f infra/prod/docker-compose.prod.yml up -d langfuse
# 域名解析加 A: obs.traillens → CVM IP
# 5 分钟后访问 https://obs.traillens.zorotreeking.online 创管理员账号
# 拿到 PUBLIC_KEY + SECRET_KEY 写回 .env,重启 api
```

## 文件结构

```
infra/prod/
├── docker-compose.prod.yml   # 5 个服务定义(api/pg/redis/caddy/langfuse 可选)
├── Caddyfile                  # 反代 + 自动 HTTPS + SSE 支持 + CORS + 安全 header
├── deploy.sh                  # 一键部署/升级
└── README.md                  # 本文件
```

## 常见问题

| 问题 | 解决 |
|---|---|
| `docker compose: command not found` | `apt install -y docker-compose-plugin` |
| Caddy 起不来 / SSL 证书没签 | 检查 80/443 端口是否被腾讯云安全组放行 |
| API 起来但 502 | `docker compose logs api` 看真实错;大概率是 .env 缺 ARK_API_KEY |
| Postgres 连不上 | 第一次启动需要 init,等 30 秒;看 `docker compose ps postgres` |
| 升级后 schema 变 | deploy.sh 会自动跑 `alembic upgrade head`;手动跑:`docker compose run --rm api alembic upgrade head` |

## 安全清单(上线前)

- [ ] 腾讯云安全组:只开 22 (你的 IP)、80、443;其它全关
- [ ] root 禁密码登,只允许密钥
- [ ] fail2ban 装上:`apt install -y fail2ban`
- [ ] 自动安全更新:`apt install -y unattended-upgrades`
- [ ] `.env` 文件 chmod 600
- [ ] 别把 .env 上传 GitHub(已在 .gitignore)
- [ ] Postgres 不暴露公网(docker-compose 只 expose 给内部)
- [ ] 定期 backup:`docker compose exec postgres pg_dump traillens > backup.sql`
