#!/usr/bin/env bash
# 本地预演 CI(给提交前用)。
set -euo pipefail

cd "$(dirname "$0")/.."

echo "--- contract tests ---"
TRAILLENS_USE_STUBS=1 python3 -m unittest discover tests -v

echo "--- agent demo smoke ---"
TRAILLENS_USE_STUBS=1 python3 -m packages.agents.traillens_agents.demo > /dev/null
echo "agent demo: OK"

echo "--- aesthetic demo-metric ---"
(cd packages/aesthetic && python3 train_qalign_lora.py demo-metric)

echo "--- doc paths ---"
for p in packages/agents/traillens_agents/state/schema.py \
         packages/agents/traillens_agents/orchestrator.py \
         packages/aesthetic/train_qalign_lora.py \
         docs/ARCHITECTURE.md \
         docs/PRODUCT_PLAN.md; do
  test -e "$p" || { echo "missing: $p"; exit 1; }
done
echo "doc paths: OK"

echo "--- mermaid blocks ---"
grep -c '```mermaid' docs/ARCHITECTURE.md

echo ""
echo "ALL GREEN"
