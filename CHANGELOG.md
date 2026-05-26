# Changelog

> 每个 sprint 末发布一条。格式遵循 [Keep a Changelog](https://keepachangelog.com)。
> 把这份 changelog **同时**发到 Twitter / 即刻 / 小红书 — build-in-public 的弹药。

## [Unreleased]

### Added
- _TODO Sprint 2 末_ — 数据标注 SOP 第一批 100 张
- _TODO Sprint 3 末_ — Q-Align landscape LoRA v0 weights on HuggingFace

---

## [0.0.1] — 2026-05-26 — 基础骨架就绪

第一次能让人看到完整脉络的版本。距离 beta 还有 ~10 周。

### Added
- **多智能体核心**:5 节点(Culling / Critic / Story / Planner / HumanReview)+ supervisor 路由,零依赖 fallback 跑通。
- **三个 MCP server**:
  - `traillens-exif` — EXIF 读取(Pillow + 8 个摄影师友好字段)
  - `traillens-sunmoon` — 日出日落 + 蓝/金时刻 + 月相(NOAA 公式 / astral 可选)
  - `traillens-weather` — Open-Meteo 代理(无 API key)
- **决策审计**:`Photo.decision_trace` — 每个 verdict 的"为什么"可追溯。
- **HTTP API 骨架**:FastAPI + SSE 流式 `/v1/trails/{id}/run`,前端可订阅 agent 事件。
- **Next.js 15 前端骨架**:Canvas 主舞台(缩略图轨道 + 8 维雷达图 + 实时 agent trace)、键盘快捷键(j/k)、设计 tokens 落地。
- **Postgres + pgvector + PostGIS** Alembic 初始 migration(5 表)。
- **美学模型推理服务骨架**:Modal-ready FastAPI app,本地可用 uvicorn 启。
- **CI**:GitHub Actions 跑 7 个契约测试 + agent demo 烟测 + 美学评估指标自检。
- **docs**:`PRODUCT_PLAN.md` / `ARCHITECTURE.md` / `EVAL.md` / `RESEARCH.md` 四份核心文档。

### Changed
- 根目录 7 个重复脚本(`business.py` / `clients.py` / `schema.py` / `orchestrator.py` / `demo.py` / `train_qalign_lora.py` / `consistency_check.py`)删除,统一到 `packages/` 下。
- `tools/clients.py` 从 stub 升级为"MCP 优先 + 网络失败 fallback",demo 现在能看到真实天气数据。

### Infrastructure
- `docker-compose.yml`(postgres+pgvector / redis / langfuse profile)
- `Makefile`(11 个开发命令)
- `.env.example`(全部环境变量分组示例)
- `scripts/ci_local.sh`(提交前一键自检)

### Test coverage
- 32 个单元/契约测试,全套 < 1 秒
- 契约 1-7 守护跨模块字段一致性

---

## 发布渠道 checklist(每个 release 都要走)

复制下面到 issue / Notion,按顺序勾选:

```
[ ] Twitter 主帖(中英双语)+ 截图 + GIF
[ ] 即刻动态(中文,加 #buildinpublic 标签)
[ ] 小红书(中文,标题用钩子句)
[ ] HuggingFace blog(如果涉及模型)
[ ] r/MachineLearning(如果涉及算法)
[ ] r/photography(如果涉及面向用户的功能)
[ ] Hacker News(只在 0.x → 0.y 才发,避免疲劳)
[ ] Product Hunt(只 1.0 + 重大功能)
[ ] 邮件 newsletter(订阅用户)
[ ] 项目仓库 release notes
```

## Build-in-public 节奏

- **每天**:在 Trello/Notion 私人 dev log 写 1 行(给自己看,不发)
- **每周一**:发 1 篇推文/动态总结上周 + 下周目标
- **每 2 周**:发 1 篇短博客(< 800 字),deep dive 一个技术决策
- **每 sprint 末**:发 changelog + 录 30s 屏幕 gif
- **每月 1 号**:更新 EVAL.md 指标 + 成本 + DAU

不要打破节奏。冷启动靠的就是**可预测的频次**。
