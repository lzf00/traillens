#!/usr/bin/env bash
# AgentSaaS Template Init — fork 后跑一次生成新 example。
#
# 模式:
#   ./scripts/init_template.sh                      dry-run 交互
#   ./scripts/init_template.sh --apply              apply 交互(仅生成新 example)
#   ./scripts/init_template.sh --apply --rename     apply + 全仓库重命名
#     (traillens → your_slug,包括 docker container 名 / nginx domain / agents 包)
#
# 前两个模式安全,只在 examples/ 下加新目录,不动仓库其它文件。
# --rename 会改根仓库,请在 fork 上跑。

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPLY=0
RENAME=0
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1 ;;
    --rename) RENAME=1 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
  esac
done

echo "════ AgentSaaS Template Init ════"
echo "ROOT: $ROOT"
echo "Mode: $([[ $APPLY -eq 1 ]] && echo APPLY || echo DRY-RUN)$([[ $RENAME -eq 1 ]] && echo ' + RENAME' || echo '')"
echo ""

read -p "App 名 (PascalCase, e.g. FoodieAI): " APP_NAME
read -p "Slug (kebab-case, e.g. foodie-ai): " APP_SLUG
read -p "描述一句话 (会写进 example README): " APP_DESC
read -p "Agents 节点名 (逗号分隔, e.g. search,plan,generate): " AGENTS
read -p "起始 example (empty 或某个 example 名如 recipe-helper): " STARTER

APP_PKG=$(echo "$APP_SLUG" | tr - _)
EX_DIR="$ROOT/examples/$APP_SLUG"

echo ""
echo "── 将做的事 ──"
echo "  · 建 examples/$APP_SLUG/"
echo "  · README.md(描述 + 3 处改文档 + fork 步骤)"
echo "  · agents/business.py(骨架,每个 agent 一个 stub 函数)"
echo "  · agents/__init__.py"
echo "  · tests/test_agents.py"
if [[ $RENAME -eq 1 ]]; then
  echo "  · [RENAME] docker container: traillens- → ${APP_SLUG}-"
  echo "  · [RENAME] nginx domain → 你的域名(问后续)"
  echo "  · [RENAME] packages/agents/traillens_agents → ${APP_PKG}_agents"
fi
echo ""

if [[ $APPLY -eq 0 ]]; then
  echo "✓ Dry-run 完成。带 --apply 真改。"
  exit 0
fi

# ---------- APPLY: 生成新 example ----------
if [[ -d "$EX_DIR" ]]; then
  echo "✗ examples/$APP_SLUG 已存在。手动删或换名"
  exit 1
fi

mkdir -p "$EX_DIR/agents" "$EX_DIR/tests"

# README.md
cat > "$EX_DIR/README.md" <<MD
# Example: $APP_SLUG ($APP_NAME)

$APP_DESC

## Live (待你部署后填)

- URL: https://your-domain.example.com

## 业务定义

| 抽象 | 对应 |
|---|---|
| \`resource\` | (你的领域主概念,如 一次做菜会话) |
| \`item\` | (item 类型,如 dish) |
$(echo "$AGENTS" | tr ',' '\n' | awk 'NR>0 {print "| **agent " NR ": " $1 "** | (说明) |"}')

## fork 这个 example 你要改的

1. \`examples/$APP_SLUG/agents/business.py\` — 实现你的 $(echo "$AGENTS" | awk -F',' '{print NF}') 个节点
2. \`apps/web/app/{your-page}/page.tsx\` — 加一个前端入口
3. \`apps/api/traillens_api/routes/{your_route}.py\` — 加一个后端 route 调 agents

## 启动

\`\`\`bash
cp .env.example .env && \$EDITOR .env
docker compose -f infra/prod/docker-compose.prod.yml up -d
\`\`\`
MD

# agents/business.py
cat > "$EX_DIR/agents/business.py" <<PY
"""$APP_NAME agent 节点 stub。fork 后你把 [TODO] 换成真实现。"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Item:
    name: str
    verdict: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class State:
    input_text: str
    items: list[Item] = field(default_factory=list)
    travelogue_md: str = ""

    def kept_items(self) -> list[Item]:
        return [i for i in self.items if i.verdict == "keep"]

PY
# 用 python 生成 agent 节点(避免 awk/tr 转义地狱)
python3 - "$AGENTS" "$EX_DIR/agents/business.py" "$EX_DIR/agents/__init__.py" "$APP_NAME" <<'PY'
import sys, re

raw, biz_path, init_path, app_name = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
# 清洗:去空白 + 只保留 [a-z0-9_]
names = []
for a in raw.split(","):
    a = re.sub(r"[^a-zA-Z0-9]+", "_", a.strip()).strip("_")
    if a:
        names.append(a.lower())

with open(biz_path, "a", encoding="utf-8") as f:
    for i, n in enumerate(names, 1):
        f.write(f"\n# ------- Agent {i}: {n} -------\n")
        f.write(f"def {n}_node(state: State) -> dict:\n")
        f.write(f'    """[TODO] 实现 {n} 节点。返回 dict 覆盖 state 字段。"""\n')
        f.write(f'    return {{"messages": [{{"role": "{n}", "content": "stub"}}]}}\n')

with open(init_path, "w", encoding="utf-8") as f:
    f.write(f'"""{app_name} agents export."""\n\n')
    f.write("from .business import Item, State\n")
    for n in names:
        f.write(f"from .business import {n}_node\n")
    f.write("\n")
    exports = ['"Item"', '"State"'] + [f'"{n}_node"' for n in names]
    f.write(f"__all__ = [{', '.join(exports)}]\n")
PY

# tests/test_agents.py
cat > "$EX_DIR/tests/test_agents.py" <<PY
"""$APP_NAME 节点最小契约测试(0 依赖 stdlib)。"""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents import Item, State

class SkeletonTest(unittest.TestCase):
    def test_state_creates(self):
        s = State(input_text="hello")
        self.assertEqual(s.input_text, "hello")
        self.assertEqual(len(s.items), 0)

    def test_item_verdict_filter(self):
        s = State(input_text="x", items=[
            Item(name="a", verdict="keep"),
            Item(name="b", verdict="skip"),
        ])
        self.assertEqual([i.name for i in s.kept_items()], ["a"])

if __name__ == "__main__":
    unittest.main()
PY

# 如果指定了 starter,从 starter 复制 agent 骨架覆盖
if [[ -n "$STARTER" && -f "$ROOT/examples/$STARTER/agents/business.py" ]]; then
  echo "── 从 $STARTER 复制 business.py 作为起点 ──"
  cp "$ROOT/examples/$STARTER/agents/business.py" "$EX_DIR/agents/business.py"
fi

# 写 template.config.yaml
cat > "$EX_DIR/template.config.yaml" <<YAML
name: $APP_NAME
slug: $APP_SLUG
description: $APP_DESC
agents:
$(echo "$AGENTS" | tr ',' '\n' | sed 's/^/  - /')
starter: ${STARTER:-null}
YAML

echo ""
echo "✓ 已生成 examples/$APP_SLUG/"
find "$EX_DIR" -type f | sort | sed "s|$EX_DIR|  examples/$APP_SLUG|"

# 可选:全仓库重命名
if [[ $RENAME -eq 1 ]]; then
  read -p "重命名用的域名 (e.g. $APP_SLUG.example.com): " DOMAIN
  echo ""
  echo "── RENAME 全仓库 ──"
  sed -i.bak "s/traillens-/${APP_SLUG}-/g" "$ROOT/infra/prod/docker-compose.prod.yml"
  sed -i.bak "s/traillens\.zorotreeking\.online/${DOMAIN}/g" \
      "$ROOT/infra/prod/nginx-traillens-web.conf" \
      "$ROOT/infra/prod/nginx-traillens-api.conf" 2>/dev/null || true
  if [[ -d "$ROOT/packages/agents/traillens_agents" && "$APP_PKG" != "traillens" ]]; then
    mv "$ROOT/packages/agents/traillens_agents" "$ROOT/packages/agents/${APP_PKG}_agents"
    grep -rl --include="*.py" "traillens_agents" "$ROOT/packages" "$ROOT/apps" 2>/dev/null \
      | xargs -r sed -i.bak "s/traillens_agents/${APP_PKG}_agents/g"
  fi
  find "$ROOT" -name "*.bak" -delete 2>/dev/null || true
  echo "  重命名完成。"
fi

echo ""
echo "── 下一步 ──"
echo "  1. ${EDITOR:-\$EDITOR} $EX_DIR/agents/business.py    # 实现节点"
echo "  2. 加一个 route 到 apps/api/traillens_api/routes/"
echo "  3. 加一个页面到 apps/web/app/"
echo "  4. 参考 examples/recipe-helper 的实现模式"
