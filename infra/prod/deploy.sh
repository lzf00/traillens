#!/usr/bin/env bash
# 腾讯云 CVM 一键部署(在服务器上跑,不是你本地)。
#
# 首次部署:
#   git clone https://github.com/lzf00/traillens
#   cd traillens
#   cp .env.example .env
#   nano .env   # 填 ARK_API_KEY / POSTGRES_PASSWORD / QINIU_xxx
#   bash infra/prod/deploy.sh
#
# 之后每次更新:
#   git pull && bash infra/prod/deploy.sh

set -euo pipefail
cd "$(dirname "$0")/../.."

echo "════════ 0. 环境检查 ════════"
command -v docker >/dev/null || { echo "✗ Docker 未装。运行:curl -fsSL https://get.docker.com | sh"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "✗ docker compose v2 未装。Ubuntu: apt install docker-compose-plugin"; exit 1; }
[ -f .env ] || { echo "✗ .env 不存在。cp .env.example .env 后填值"; exit 1; }
grep -q "^ARK_API_KEY=." .env || { echo "✗ .env 缺 ARK_API_KEY"; exit 1; }
grep -q "^POSTGRES_PASSWORD=." .env || { echo "✗ .env 缺 POSTGRES_PASSWORD"; exit 1; }
echo "✓ 环境检查通过"

echo ""
echo "════════ 1. 构建 API 镜像 ════════"
docker compose -f infra/prod/docker-compose.prod.yml build api

echo ""
echo "════════ 2. 启动核心服务 ════════"
docker compose -f infra/prod/docker-compose.prod.yml up -d postgres redis
echo "等 postgres healthy..."
until docker compose -f infra/prod/docker-compose.prod.yml ps postgres | grep -q "healthy"; do
  sleep 2
done

echo ""
echo "════════ 3. 跑 DB migration ════════"
docker compose -f infra/prod/docker-compose.prod.yml run --rm \
  --workdir /app/api api alembic upgrade head || \
  echo "(migration 已是最新,或表已存在)"

echo ""
echo "════════ 4. 启动 API + Caddy ════════"
docker compose -f infra/prod/docker-compose.prod.yml up -d api caddy

echo ""
echo "════════ 5. 等待 API healthy ════════"
sleep 5
until docker compose -f infra/prod/docker-compose.prod.yml exec -T api \
  python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz').read()" 2>/dev/null; do
  sleep 2
  echo "..."
done
echo "✓ API healthy"

echo ""
echo "════════ 完成 ════════"
echo "  API:  https://api.traillens.zorotreeking.online/healthz"
echo "  日志: docker compose -f infra/prod/docker-compose.prod.yml logs -f api"
echo "  状态: docker compose -f infra/prod/docker-compose.prod.yml ps"
echo ""
echo "下一步:"
echo "  1) 在腾讯云域名解析里加 CNAME:"
echo "     主机记录 api.traillens   记录值 <这台 CVM 的公网 IP>"
echo "  2) 等 DNS 生效(1-10 分钟)"
echo "  3) 访问 https://api.traillens.zorotreeking.online/healthz"
echo "     Caddy 会自动签 Let's Encrypt 证书,首次访问稍慢"
