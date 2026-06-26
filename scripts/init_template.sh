#!/usr/bin/env bash
# Direction C PoC — agent-template 初始化脚本(fork 后跑一次)。
#
# 交互式问 3 个问题 → 全仓库批量替换 placeholder → 输出"接下来改哪 3 个文件"。
# 当前 PoC 只做 dry-run (打印将要做什么),真改文件需要 --apply。

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

echo "════ AgentSaaS Template Init ════"
echo "ROOT: $ROOT"
echo ""

# ---------- 1. 收信息 ----------
read -p "App 名 (英文,e.g. FoodieAI): " APP_NAME
read -p "Slug (kebab-case,e.g. foodie-ai): " APP_SLUG
read -p "域名 (e.g. foodie.example.com): " APP_DOMAIN
read -p "Agents (逗号分隔,e.g. search,recipe,nutrition): " AGENTS

APP_PKG=$(echo "$APP_SLUG" | tr - _)
echo ""
echo "── 将做的事(${APPLY:+真改} ${APPLY:-dry-run}) ──"
echo "  · 改 README 顶部 title → $APP_NAME"
echo "  · 改 docker-compose 容器名 traillens-* → ${APP_SLUG}-*"
echo "  · 改 next.config / nginx server_name → $APP_DOMAIN"
echo "  · packages/agents/traillens_agents → packages/agents/${APP_PKG}_agents"
echo "  · packages/agents/.../nodes/business.py 标 [YOUR-CODE-HERE] 区域"
echo "  · agent 列表写入 packages/agents/.../config.py: AGENTS = [$AGENTS]"
echo ""

if [[ $APPLY -eq 0 ]]; then
  echo "✓ Dry-run 完成。带 --apply 真改。"
  echo ""
  echo "── 真改后你需要手动做 ──"
  echo "1. 实现你的 agent 节点:packages/agents/${APP_PKG}_agents/nodes/business.py"
  echo "   每个 agent 实现 (state) → dict 接口"
  echo "2. 改 web 文案 + 颜色:apps/web/styles/globals.css + apps/web/app/page.tsx"
  echo "3. 改 db schema 命名(可选):apps/api/.../alembic/versions/*"
  echo ""
  echo "  4. cp .env.example .env 填 API key"
  echo "  5. docker compose up -d"
  echo "  6. 打开 http://localhost:3000"
  exit 0
fi

# ---------- 2. 真改(暂占位,Phase 2 实现)----------
echo "✗ --apply 模式还没实现(Phase 2 todo)。"
echo "  当前 PoC 只验证交互式 wizard 形态,真模板化要先做"
echo "  docs/SPEC_C_AGENT_TEMPLATE.md 里 Phase 1 抽 resource/item 抽象。"
exit 2
