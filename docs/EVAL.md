# 评估指标 & 复现命令

> 这份文档是**作品集硬通货**——任何招聘方/合作方都会先翻到这里看真实指标。
> 现状(Sprint 2 启动前)指标全部 `_TODO_`,Sprint 3 末填入第一组真实数。

---

## 1. 美学评分模型(主线指标)

### 1.1 测试集

| Dataset | n | 来源 | 用途 |
|---|---|---|---|
| ArtiMuse-10K Photography | 待定 | [arXiv 2507.14533](https://arxiv.org/abs/2507.14533) | 主测试集(对外可比) |
| TrailLens-Landscape-300 | 300 | 自爬 Unsplash + 500px + 个人作品 | 风光垂直专测(护城河) |
| AVA-Landscape | ~2000 | AVA 子集筛选 | 与历史模型对照 |

### 1.2 指标

PLCC = Pearson Linear Correlation Coefficient(预测分 vs 人工分,线性相关)
SRCC = Spearman Rank Correlation Coefficient(预测排序 vs 人工排序)

两者都是 IAA / IQA 领域标准指标。**目标:overall 维度 PLCC > 0.78**(M2 Go/No-Go 触发器,见 README §路线图)。

### 1.3 指标表(每次 Sprint 末更新)

| 维度 | zero-shot Q-Align(baseline) | **本模型(LoRA)** | 提升 | 备注 |
|---|---|---|---|---|
| overall | _TODO_ | _TODO_ | _TODO_ | M2 Go/No-Go: > 0.78 |
| composition | _TODO_ | _TODO_ | _TODO_ | |
| visual_elements | _TODO_ | _TODO_ | _TODO_ | |
| technical | _TODO_ | _TODO_ | _TODO_ | EXIF 注入(H2)对此影响最大 |
| originality | _TODO_ | _TODO_ | _TODO_ | |
| theme | _TODO_ | _TODO_ | _TODO_ | |
| emotion | _TODO_ | _TODO_ | _TODO_ | |
| gestalt | _TODO_ | _TODO_ | _TODO_ | |

### 1.4 复现命令

```bash
# 1. 评估当前模型在 landscape 测试集上
cd packages/aesthetic
python train_qalign_lora.py eval

# 2. 评估指标实现正确性(无需 GPU,演示评估代码本身)
python train_qalign_lora.py demo-metric

# 3. 三块交付物一致性自检(包含字段对齐)
cd ../..
python -m unittest discover tests
```

每次 run 把输出 JSON 贴到本文件 §1.3 表里,并更新日期。

---

## 2. 端到端延迟

| 阶段 | 单张延迟 p50 | 200 张端到端 p50 | 备注 |
|---|---|---|---|
| Culling.technical | _TODO_ | _TODO_ | CPU 上跑(本地) |
| Culling.aesthetic | _TODO_ | _TODO_ | Modal A10G(冷启动 + 推理) |
| Critic | _TODO_ | _TODO_ | Claude Opus 4.7 / 8 张并发 |
| Story | _TODO_ | _TODO_ | 流式输出 |
| Planner | _TODO_ | _TODO_ | 含 weather + sun-moon |
| **全链路** | — | **目标 < 5 min** | Sprint 4 末测 |

测量方式:agent_runs 表的 `started_at` / `finished_at`,用 Langfuse trace 看每节点。

---

## 3. 成本

| 项 | 单 Trail 估算(200 张) | 月预算前提 |
|---|---|---|
| Modal A10G 美学推理 | _TODO_ USD | 100 trails/月 |
| Claude Opus 4.7 Critic | _TODO_ USD | |
| Claude Opus 4.7 Story | _TODO_ USD | |
| Qwen3-VL 备选 | _TODO_ USD | |
| R2 存储(增量) | _TODO_ USD | |
| **合计** | _TODO_ | < $200/月(MVP) |

成本数据来源:Langfuse 的 token + Modal 后台。每月 1 号更新。

---

## 4. 用户侧指标(Sprint 6 后)

| Metric | 当前 | 目标(M5 末) | 测量方式 |
|---|---|---|---|
| 注册→上传转化 | — | > 30% | PostHog funnel |
| 上传→分享转化 | — | > 10% | PostHog event |
| Week-1 retention | — | > 25% | cohort analysis |
| NPS | — | > 30 | in-app survey |

---

## 5. 契约测试(每次 PR 必跑,见 .github/workflows/ci.yml)

| Contract | 检查内容 | 守护文件 |
|---|---|---|
| 1 | AestheticScore 8 维齐全;训练脚本 score_dims 与之相等 | test_consistency.py |
| 2 | README 架构节点 ⊆ orchestrator 路由 ⊆ 节点实现 | test_consistency.py |
| 3 | score_aesthetics 返回 AestheticScore;分数 ∈ [0,10] | test_consistency.py |
| 4 | 端到端 demo 跑通,游记生成,FINISH 到达 | test_consistency.py |
| 5 | 每张照片有非空 decision_trace | test_consistency.py |
| 6 | traillens-exif 输出字段 ⊇ ExifMeta 字段 | test_exif_server.py |
| 7 | serve.py ScoreResponse 字段 == AestheticScore 字段 | test_aesthetic_serve.py |

跑全套:`make test`(<1 秒,32 个用例)。
