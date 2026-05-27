# TrailLens 开发命令入口。请用 GNU Make。
#
#   make help     展开所有可用目标
#
.DEFAULT_GOAL := help
SHELL := /bin/bash

PY ?= python3
COMPOSE ?= docker compose

# ---- 帮助 ------------------------------------------------------------------
.PHONY: help
help: ## 展开命令列表
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---- 本地依赖(docker) ----------------------------------------------------
.PHONY: dev down logs reset-db
dev: ## 启动 postgres + redis(后台)
	$(COMPOSE) up -d postgres redis
	@echo "→ postgres on :$${POSTGRES_PORT:-5432} ; redis on :$${REDIS_PORT:-6379}"

down: ## 停止全部 compose 服务
	$(COMPOSE) down

logs: ## 跟随日志
	$(COMPOSE) logs -f --tail=80

reset-db: ## 销毁并重建本地数据库(慎用,丢数据)
	$(COMPOSE) down -v
	$(COMPOSE) up -d postgres
	@echo "→ DB reset; pgvector/postgis extensions re-applied by init script"

# ---- 测试 / Demo ----------------------------------------------------------
.PHONY: test demo aesthetic-demo verify
test: ## 跑全部单元测试(零依赖)
	$(PY) -m unittest discover tests -v

demo: ## 跑端到端 agent demo
	$(PY) -m packages.agents.traillens_agents.demo

aesthetic-demo: ## 跑美学模型 PLCC/SRCC 实现自检
	cd packages/aesthetic && $(PY) train_qalign_lora.py demo-metric

verify: test demo aesthetic-demo ## 串行做全栈烟测,CI 入口

.PHONY: ci-local
ci-local: ## 本地预演 GitHub Actions 全流程
	bash scripts/ci_local.sh

# ---- API ------------------------------------------------------------------
.PHONY: api api-test
api: ## 启 FastAPI dev server(localhost:8000)
	cd apps/api && uvicorn traillens_api.main:app --reload --port 8000

api-test: ## 跑 api 集成测试(需要 fastapi + httpx)
	$(PY) -m unittest tests.test_api -v

# ---- Sprint 2: 数据标注 ---------------------------------------------------
.PHONY: sprint2 sprint2-finalize
sprint2: ## 启动 Sprint 2 标注流水线(放完照片后跑这条)
	bash scripts/sprint2_kickoff.sh

sprint2-finalize: ## 标注完成后:算 α + 切分训练集
	bash scripts/sprint2_kickoff.sh --finalize

# ---- MCP server -----------------------------------------------------------
.PHONY: mcp-exif mcp-exif-install
mcp-exif: ## 在前台启 traillens-exif(stdio loop;Ctrl-C 退出)
	cd packages/mcp_servers/traillens_exif && $(PY) -m traillens_exif

mcp-exif-install: ## 把 traillens-exif 装到当前 venv(editable + mcp extra)
	cd packages/mcp_servers/traillens_exif && pip install -e ".[mcp]"

# ---- 清理 -----------------------------------------------------------------
.PHONY: clean
clean: ## 删 pyc / __pycache__ / .pytest_cache
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
