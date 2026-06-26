#!/usr/bin/env bash
# AgentSaaS Template Init — fork 后跑一次。
#
# 模式:
#   ./scripts/init_template.sh           dry-run(打印将做的事,不改)
#   ./scripts/init_template.sh --apply   真改 docker container / domain / agent 包名
#
# 注意:--apply 只做安全的命名替换。深度业务改造(agent 节点实现 / db schema /
# Landing 文案) 见 examples/ 里现成 example,自行 cp 参考。

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

echo "════ AgentSaaS Template Init ════"
echo "ROOT: $ROOT"
echo "Mode: $([[ $APPLY -eq 1 ]] && echo APPLY || echo DRY-RUN)"
echo ""

read -p "App 名 (英文 PascalCase, e.g. FoodieAI): " APP_NAME
read -p "Slug (kebab-case, e.g. foodie-ai): " APP_SLUG
read -p "域名 (e.g. foodie.example.com): " APP_DOMAIN
read -p "Agents (逗号分隔, e.g. search,recipe,nutrition): " AGENTS

APP_PKG=$(echo "$APP_SLUG" | tr - _)
echo ""
echo "── 将做的替换 ──"
echo "  · docker container 前缀: traillens- → ${APP_SLUG}-"
echo "  · web 域名: traillens.zorotreeking.online → $APP_DOMAIN"
echo "  · agents 包: traillens_agents → ${APP_PKG}_agents"
echo "  · README title: TrailLens → $APP_NAME"
echo "  · template.config.yaml 写: app=$APP_NAME slug=$APP_SLUG domain=$APP_DOMAIN agents=[$AGENTS]"
echo ""

if [[ $APPLY -eq 0 ]]; then
  echo "✓ Dry-run 完成。带 --apply 真改:./scripts/init_template.sh --apply"
  exit 0
fi

# ---------- 真改 ----------
echo "── 改 docker-compose ──"
sed -i.bak "s/traillens-/${APP_SLUG}-/g" "$ROOT/infra/prod/docker-compose.prod.yml"

echo "── 改 nginx domain ──"
sed -i.bak "s/traillens\.zorotreeking\.online/${APP_DOMAIN}/g" \
    "$ROOT/infra/prod/nginx-traillens-web.conf" \
    "$ROOT/infra/prod/nginx-traillens-api.conf" 2>/dev/null || true

echo "── 改 agents 包名(目录 rename + import 替换)──"
if [[ -d "$ROOT/packages/agents/traillens_agents" && "$APP_PKG" != "traillens" ]]; then
  mv "$ROOT/packages/agents/traillens_agents" "$ROOT/packages/agents/${APP_PKG}_agents"
  # 全仓库替换 import
  grep -rl --include="*.py" "traillens_agents" "$ROOT/packages" "$ROOT/apps" 2>/dev/null \
    | xargs -r sed -i.bak "s/traillens_agents/${APP_PKG}_agents/g"
fi

echo "── 写 template.config.yaml ──"
cat > "$ROOT/template.config.yaml" <<YAML
app: $APP_NAME
slug: $APP_SLUG
domain: $APP_DOMAIN
agents:
$(echo "$AGENTS" | tr ',' '\n' | sed 's/^/  - /')
YAML

# 清理 .bak 文件
find "$ROOT" -name "*.bak" -delete 2>/dev/null || true

echo ""
echo "✓ Template 初始化完成。"
echo ""
echo "── 下一步你手动改 ──"
echo "1. agent 业务逻辑:"
echo "     \$EDITOR $ROOT/packages/agents/${APP_PKG}_agents/nodes/business.py"
echo "2. Landing 文案 + 主色:"
echo "     \$EDITOR $ROOT/apps/web/app/page.tsx"
echo "     \$EDITOR $ROOT/apps/web/styles/globals.css"
echo "3. 跑起来:"
echo "     cp .env.example .env && \$EDITOR .env"
echo "     docker compose -f infra/prod/docker-compose.prod.yml up -d"
echo "     open http://localhost:3000"
echo ""
echo "── 参考 ──"
echo "  examples/landscape-photo/  完整成品(本仓库根)"
echo "  examples/recipe-helper/    另一业务的 stub"
