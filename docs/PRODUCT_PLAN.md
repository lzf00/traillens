# TrailLens 产品 & 工程开发方案

> 这份文档不重复 `compass_artifact_wf.md`（那是赛道调研）。
> 这份是**可直接执行到代码层的产品 + 工程方案**，覆盖定位、设计语言、AI 原生交互、架构契约、商业化、12 周冲刺计划。
> 目标读者：未来 12 周内会动这个仓库的人（你自己 / 协作者 / Claude Code）。

---

## 0. 现状评估（30 秒读懂"差距在哪")

| 维度 | 现状 | 商业级标准 | 差距 |
|---|---|---|---|
| Agent 编排 | supervisor + 5 节点骨架可跑，纯 Python fallback 工作 | 同左 + 真实 LangGraph checkpoint + HITL interrupt | 接 langgraph + PostgresSaver |
| 美学模型 | 训练脚本仅骨架，推理是 random stub | LoRA 训练完成 + Modal endpoint + PLCC>0.78 | 0% |
| MCP 工具 | `packages/mcp_servers/` 空 | EXIF / Weather / Sun-Moon / Trail 4 个 server 可被 Claude Desktop 直接装 | 0% |
| 前端 | `apps/web/` 空 | Next.js 15 + 上传 → 流式 agent 轨迹 → artifact 选片画板 | 0% |
| 后端 API | `apps/api/` 空 | FastAPI + SSE/WebSocket + R2 上传签名 + Stripe webhook | 0% |
| 数据库 | 无 | Postgres + pgvector + Redis（队列/会话） | 0% |
| 可观测性 | 无 | Langfuse + Sentry + OpenTelemetry | 0% |
| 文档 | README 写得好，但 `docs/` 全空 | ARCHITECTURE / EVAL / RESEARCH / PRODUCT_PLAN | 1/4（本文件） |
| 历史包袱 | 根目录 7 个旧 .py 与 `packages/` 重复 | 单一事实来源 | 待清理 |

**结论**：scaffold 完成度 ≈ 15%。本方案聚焦把 15% 拉到 80% 的最短路径。

---

## 1. 产品定位（先把"为什么是 TrailLens 而不是另一个 Photo AI"说清楚）

### 1.1 一句话定位（用于 PH/HN/小红书 hero）

> **The AI darkroom for landscape photographers who hike.**
> 不是"AI 帮你 P 图"，是"AI 帮你把一整次徒步的素材，变成一份你愿意分享的作品集"。

### 1.2 切口（避免 me-too）

市面已有的竞品其实分散在三个赛道，TrailLens 的差异化是**把它们缝合 + 加上"户外语境"**：

| 现有产品 | 解决了什么 | 没解决什么（= TrailLens 机会） |
|---|---|---|
| Aftershoot / Imagen AI | 商业摄影师的批量选片+套预设 | 风光摄影标准被婚礼模型误判；与户外地理无关 |
| Photo AI（levelsio） | 一键生成"我"的写真 | 不处理"我自己拍的"照片；不懂构图 |
| AllTrails Peak / HiiKER | 路线规划 + AI 建议 | 不看你拍了什么；事后无作品产出 |
| Lightroom AI | 调色/降噪/天气替换 | 不做选片决策；无叙事生成 |

**TrailLens 的独特卖点（USP）**：
1. **唯一一个把"拍摄行为"作为上下文**（EXIF + GPX + 蓝/金时 + 天气）的美学评分系统。
2. **唯一一个开源 + 可自托管**的风光摄影 MLLM 评分模型（Q-Align 微调权重 + HF Space）。
3. **唯一一个把所有外部能力做成 MCP server**——Claude Desktop / Cursor / ChatGPT 用户可以"零成本调用 TrailLens 的能力"，反向给主产品引流。

### 1.3 目标用户分层（决定 paywall 在哪触发）

| 层 | 画像 | 核心痛点 | 付费意愿 |
|---|---|---|---|
| L1 业余风光爱好者 | 一次徒步拍 500+ 张 RAW，回家选片崩溃 | 选片体力活 | 免费层够用 |
| L2 半专业 / 摄影博主 | 周更小红书/B站，需要快速产出图文 | 游记产出慢 | **$19/月（主力付费层）** |
| L3 户外向导 / 商业风光 | 给客户交付作品集 + 下次行程方案 | 客户管理 + 风格一致性 | $49/月（团队） |
| L4 工具开发者 | 想在自己 app 里调用美学评分 | 没开源风光美学 API | API 按调用付费 |

**核心 paywall 触发器**：免费层处理 **50 张/月 + 不导出 Lightroom 预设**；导出与"生成游记"是付费转化点（参照 Aftershoot 的转化设计）。

---

## 2. 设计语言（这是最容易被忽略的差异化）

### 2.1 参考的"近期好项目"——只挑能落地到 TrailLens 的元素

不是抄设计，是**抄设计哲学**。每条都写明"如何映射到 TrailLens"。

| 参考产品 | 借鉴元素 | TrailLens 落地 |
|---|---|---|
| **Linear** | 信息密度高、键盘优先、状态机可视化 | 选片画板用 `j/k` 上下、`x` 拒、`k` 留；agent 状态条永远顶部 |
| **Raycast** | Command Palette + 极简结果列表 | `Cmd+K` 唤起"重新分析这张照片 / 改用风格 X / 导出预设" |
| **Vercel v0 / shadcn** | 中性灰 + 单一强调色 + 大留白 + serif 标题混排 | 主色用**山岩灰 #2A2F36** + **极光绿 #6FBF8B**（强调）+ **冰川蓝 #8FB8D1**（链接） |
| **Granola / Cluely** | 流式 "thinking trace" 可见、可回滚 | 右侧抽屉永远显示 agent 路由轨迹与 token 用量 |
| **Cursor / Claude Code** | "Diff View" 让 AI 修改可审计 | 选片决策给"为什么留/拒"的可点击解释卡片 |
| **Krea / Higgsfield** | 生成结果以"作品板"形式呈现，非聊天 | 主舞台是"作品板"而非聊天框，agent 是工具不是对话伙伴 |
| **Perplexity Spaces** | 把会话 = artifact 容器 | 一次徒步 = 一个 Trail（持久化、可分享 URL、可继续追加） |
| **ChatGPT Atlas / Arc** | 把 AI 嵌入浏览动作而非新窗口 | Lightroom Plugin + Capture One Plugin 是一等公民，不是事后想到的 |
| **ElevenLabs / Suno** | 上传即开始处理，进度条 = 价值预览 | 上传开始就流式跑 culling，用户在等的过程中看到分数滚动 |
| **Notion AI** | 行内 AI，不打断写作流 | 游记编辑器内 `/` 唤起"改写本段为更抒情 / 加入天气数据" |

### 2.2 视觉系统（直接定下来，避免每个页面重新设计）

```
Color
├── bg/base       #0F1115  (deep slate, 户外夜空感)
├── bg/raised     #1A1E25
├── bg/overlay    #232932
├── fg/primary    #E8ECF1
├── fg/secondary  #9AA4B2
├── fg/tertiary   #5B6573
├── accent/aurora #6FBF8B  (极光绿，主 CTA)
├── accent/glacier#8FB8D1  (冰川蓝，链接/选中)
├── accent/golden #E8B96A  (金时刻，"keep" 状态)
├── accent/danger #D97757  (落日橙，"reject" 状态)
└── divider       rgba(255,255,255,0.06)

Typography
├── Display       Fraunces 600 (serif，标题/封面，致敬胶片摄影画册)
├── UI            Inter 400/500 (英文 UI)
├── CN UI         "PingFang SC" / "HarmonyOS Sans" 400/500
└── Mono          JetBrains Mono (EXIF / agent trace)

Spacing      4 / 8 / 12 / 16 / 24 / 32 / 48 / 64
Radius       6 (button) / 10 (card) / 16 (modal) / 24 (artifact frame)
Motion       Framer Motion: ease=[0.2, 0.8, 0.2, 1], dur=180-240ms
Photography  照片永远用 4:5 / 3:2 原比例 + 1px 内边框，不裁切
```

**关键反模式**（写出来强制自己别犯）：
- 不用渐变背景 hero（每个 AI SaaS 都在用，已审美疲劳）
- 不用 emoji 做导航 icon（用 Lucide 线性 icon）
- 不在主舞台放对话框（聊天是辅助，artifact 是主体）
- 不用"AI ✨"字样（产品本身就是 AI，不需要标注）

### 2.3 信息架构（IA）

```
/                          → landing（一屏 hero + 30s demo gif + price + FAQ）
/app                       → 已登录主舞台
  /app/trails              → 我的所有徒步（卡片网格，每张= 一次出行）
  /app/trails/[id]         → 单次徒步作品板（核心页，见 §4）
  /app/trails/[id]/share   → 公开分享页（含游记 + 精选图 + 拍摄数据）
  /app/library             → 全部照片库（语义搜索）
  /app/presets             → 我的 Lightroom 预设（生成 + 下载）
  /app/settings            → 账号 / API key / 个性化偏好（PIAA 标注入口）
/api/v1/...                → REST API（Pro+ 用户）
/mcp/...                   → MCP 服务发现端点
/docs                      → 公开文档（含 RESEARCH / EVAL / API）
/changelog                 → 每周更新（build-in-public 主页）
```

---

## 3. AI 原生 UX 设计（这是 2026 年真正的差异化）

**核心命题**：传统 SaaS 是"用户操作 → 看到结果"；AI 原生是"用户表达意图 → 看到 AI 思考 → 介入或接受"。
TrailLens 的所有交互都按这个范式重写。

### 3.1 五个必须实现的 AI 原生模式

#### M1. Stream-First（流式优先）
**反例**：上传 200 张 → 显示 loading spinner 3 分钟 → 一次性出结果。
**正例**：上传开始的瞬间，左侧缩略图按 culling 顺序逐张高亮，分数滚动跳出；agent 轨迹在右侧实时刷新。
**技术**：SSE 流（FastAPI `StreamingResponse`）+ React `useSSE` hook，LangGraph 用 `.astream_events()` 输出。

#### M2. Generative UI（生成式 UI，非纯文本）
**反例**：agent 输出大段 markdown 报告。
**正例**：agent 调用 `render_score_card(photo_id, scores)` 工具，前端动态渲染 8 维雷达图组件；调用 `render_map(gps_points)` 渲染轨迹地图。
**技术**：Vercel AI SDK `useChat` + RSC `streamUI`，所有可视化是 component-as-tool。

#### M3. Interrupt-and-Resume（可中断可恢复）
**反例**：agent 跑到一半用户想改主意 → 只能 cancel 重来。
**正例**：任何时刻可点"暂停"，state 保存到 PostgresSaver；改完上下文（如"再严一点，只留 8 分以上"）后 resume。
**技术**：LangGraph `interrupt()` + `Command(resume=...)`；HITL 节点天然支持。

#### M4. Auditable Decisions（决策可审计）
**反例**：AI 说"这张拒了"，用户不知道为什么。
**正例**：每个 reject/keep 决策右上角小 `i` icon，点击展开：技术检测分数（拉普拉斯方差=42 < 80 → blur）+ 美学 8 维 + 模型置信度 + "类似训练样本" 3 张。
**技术**：决策 trace 写入 `Photo.decision_trace: list[DecisionStep]`，前端可视化为时间线。

#### M5. Memory-as-Preference（记忆作为偏好沉淀）
**反例**：每次新建 trail 都是冷启动。
**正例**：用户驳回 → 后台静默写入 Mem0；下次自动按用户口味调整阈值；个人 PIAA LoRA 在 50 张样本后自动训出。
**技术**：Mem0 + 每周离线任务跑 PIAA 增量训练（Modal cron job）。

### 3.2 主交互范式：作品板（Canvas）而非聊天

**主舞台不是 chat，是一块"暗房工作台"**（参考 Krea / Figma）：

```
┌─────────────────────────────────────────────────────────────────┐
│  Trail: 贡嘎环线  ·  2026-05-15  ·  ●●●○ 142/200 已处理         │ ← Header
├─────────────┬──────────────────────────────────┬────────────────┤
│             │                                  │  Agent Trace   │
│  缩略图轨道  │                                  │  ────────────  │
│  (按时间)   │       主舞台（被选中的照片）        │  orchestrator  │
│             │                                  │   → culling    │
│  [img] 8.2  │  ┌────────────────────────────┐  │     142 张筛   │
│  [img] 7.1  │  │                            │  │   → human_rev  │
│  [img] —    │  │      [大图预览 + 雷达图]     │  │     3 张待审   │
│  [img] 9.0★│  │                            │  │   → critic     │
│  [img] —    │  │                            │  │     6 张点评   │
│             │  └────────────────────────────┘  │  ────────────  │
│             │   构图 8.0 ████████░░             │  Cost: $0.04   │
│             │   技术 6.5 ██████░░░░             │  Token: 12.4K  │
│             │   情感 7.8 ███████░░░             │                │
│             │                                  │                │
│             │   "前景空旷，建议靠近 2 步..."     │                │
│             │   [接受] [反驳] [换风格]          │                │
└─────────────┴──────────────────────────────────┴────────────────┘
  键盘： j/k 上下  ·  x 拒  ·  k 留  ·  ? 帮助  ·  ⌘K 命令面板
```

**为什么是 Canvas 不是 Chat**：摄影师的工作模式本来就是"在大量素材中筛选"，强制套对话范式（"请帮我筛选第 47 张"）反而低效。Chat 仅在游记编辑、Planner 问答场景下使用。

### 3.3 Agent 化的写作（游记编辑器）

游记不是一次性生成丢给用户，是一份**像 Notion 一样的可编辑文档**，内嵌：

- `/` 唤起："改写为更克制的笔调 / 加入当天天气 / 把这段换成对话风格"
- 选中段落 → 浮动工具栏 → "用另一张照片替换" / "查证这个事实"
- 右侧栏：照片 EXIF / 天气数据 / 引用过的 trail 数据 → 任何引用可点击溯源

---

## 4. 端到端架构（接口级具体，不是泛泛架构图）

### 4.1 模块责任划分

```
┌─────────────────────────────────────────────────────────────────┐
│ apps/web (Next.js 15)                                           │
│  ├─ React 19 + RSC + Server Actions                            │
│  ├─ Vercel AI SDK (useChat / streamUI)                         │
│  ├─ shadcn/ui + Tailwind + Framer Motion                       │
│  └─ Upload: 直传 R2 (presigned PUT) 绕开 API                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ SSE / REST
┌──────────────────────────▼──────────────────────────────────────┐
│ apps/api (FastAPI)                                              │
│  ├─ /v1/trails           CRUD + 触发 agent                      │
│  ├─ /v1/trails/{id}/run  POST → SSE 流 agent 事件                │
│  ├─ /v1/photos/{id}/...  单张操作（重评 / 反馈）                 │
│  ├─ /v1/billing/webhook  Stripe                                 │
│  ├─ /v1/auth             Clerk / Better-Auth                    │
│  └─ middleware: rate-limit + quota + tracing                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ in-process
┌──────────────────────────▼──────────────────────────────────────┐
│ packages/agents (LangGraph)                                     │
│  ├─ orchestrator + 5 nodes (已有)                                │
│  ├─ PostgresSaver checkpointer                                  │
│  ├─ astream_events → 转 SSE                                      │
│  └─ tools/clients.py → 调下面 MCP servers                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MCP stdio / HTTP
┌──────────────────────────▼──────────────────────────────────────┐
│ packages/mcp_servers/                                           │
│  ├─ exif_server      (本地，pyexiv2)                            │
│  ├─ weather_server   (Open-Meteo proxy)                         │
│  ├─ sun_moon_server  (astral 计算)                              │
│  └─ trail_server     (Overpass API + OSM)                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────────────┐
│ packages/aesthetic (Modal endpoint)                             │
│  └─ Q-Align + landscape LoRA → POST /score → AestheticScore     │
└─────────────────────────────────────────────────────────────────┘

外部：
  - Cloudflare R2     (照片对象存储)
  - Postgres+pgvector (业务数据 + 向量)
  - Redis             (Celery 队列 + session)
  - Stripe            (订阅)
  - Langfuse          (LLM 可观测性，自托管)
  - Sentry            (error)
  - Anthropic API     (Claude Opus 4.7，Critic / Story 节点)
  - SiliconFlow       (Qwen3-VL，Culling 节点的细粒度视觉判断)
```

### 4.2 数据契约（写在这里防止三块漂移）

#### DB schema（核心 5 张表）

```sql
-- users          已有（来自 auth provider）
-- subscriptions  Stripe customer + plan + quota
-- trails         一次徒步 = 一个 agent run 容器
CREATE TABLE trails (
  id            uuid PRIMARY KEY,
  user_id       uuid NOT NULL,
  name          text NOT NULL,
  location_name text,
  gpx_uri       text,
  gps_bbox      geometry(POLYGON, 4326),  -- PostGIS
  state         jsonb NOT NULL,            -- GraphState 序列化
  travelogue_md text,
  next_trip_plan jsonb,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
);

-- photos         单张照片
CREATE TABLE photos (
  id            uuid PRIMARY KEY,
  trail_id      uuid NOT NULL REFERENCES trails(id) ON DELETE CASCADE,
  uri           text NOT NULL,                  -- R2 URL
  exif          jsonb,
  verdict       text,                            -- keep/reject/review
  reject_reason text,
  aesthetic     jsonb,                           -- AestheticScore
  critique      text,
  embedding     vector(768),                     -- CLIP/SigLIP，pgvector
  decision_trace jsonb,                          -- 可审计
  created_at    timestamptz DEFAULT now()
);
CREATE INDEX ON photos USING ivfflat (embedding vector_cosine_ops);

-- user_preferences  PIAA 用
CREATE TABLE user_preferences (
  user_id              uuid PRIMARY KEY,
  favorite_focal_lengths jsonb,
  style_keywords       text[],
  rejected_photo_ids   uuid[],
  piaa_lora_path       text,
  piaa_sample_count    int DEFAULT 0
);

-- agent_runs        审计/计费/调试
CREATE TABLE agent_runs (
  id            uuid PRIMARY KEY,
  trail_id      uuid NOT NULL,
  user_id       uuid NOT NULL,
  status        text NOT NULL,                  -- running/paused/finished/failed
  events        jsonb,                          -- 全量 LangGraph event stream
  cost_usd      numeric(10, 4) DEFAULT 0,
  tokens_in     int DEFAULT 0,
  tokens_out    int DEFAULT 0,
  started_at    timestamptz DEFAULT now(),
  finished_at   timestamptz
);
```

#### API contract（关键 3 个）

```http
POST /v1/trails
Body: { name, gpx_uri?, location_name? }
→ 201 { trail_id }

POST /v1/trails/{id}/photos:bulk
Body: { photos: [{uri, exif?}] }    # uri 是用户已直传 R2 的 URL
→ 202 { accepted: N }

POST /v1/trails/{id}/run
→ 200 text/event-stream
event: orchestrator.routed   data: {"next": "culling"}
event: culling.progress      data: {"done": 42, "total": 200}
event: culling.photo_scored  data: {"photo_id": "...", "scores": {...}}
event: human_review.required data: {"photo_ids": [...]}
event: critic.photo_critiqued data: {"photo_id": "...", "critique": "..."}
event: story.delta           data: {"chunk": "..."}
event: run.finished          data: {"trail_id": "...", "cost_usd": 0.12}
```

#### Agent State 已有契约（保持不变，只补两个字段）

```python
class Photo(BaseModel):
    # ... 已有字段
    decision_trace: list[dict] = Field(default_factory=list)  # 新增，用于 §3.1 M4

class GraphState(BaseModel):
    # ... 已有字段
    run_id: str | None = None    # 新增，串联 agent_runs 表
    quota_used: int = 0          # 新增，超额时 raise QuotaExceeded
```

### 4.3 MCP server 设计（项目独有的 distribution channel）

每个 MCP server 都是**独立可发布到 npm/pypi 的小项目**，README 写"用 Claude Desktop 一键安装"。这条隐藏分发渠道是项目能拿到 stars 的关键。

| Server | 工具 | 实现要点 | 单独价值 |
|---|---|---|---|
| `traillens-exif` | `read_exif(url)`, `extract_gps(url)`, `batch_summarize(urls)` | pyexiv2，本地运行 | 任何摄影工作流都能用 |
| `traillens-weather` | `weather_at(lat,lon,date)`, `forecast(...)` | Open-Meteo 代理，无 key 免费 | 比 OWM 简洁 |
| `traillens-sunmoon` | `golden_hour(lat,lon,date)`, `moon_phase(...)` | astral 库 | 摄影师高频需求 |
| `traillens-trails` | `nearby_trails(lat,lon,radius)`, `elevation_profile(gpx)` | Overpass + OSRM | 户外社区 |
| `traillens-aesthetic` | `score(image_url) -> 8维分` | 调 Modal endpoint | **这是项目的"API 商业化产品"** |

**关键**：第 5 个 server 是付费的（API key 鉴权），前 4 个开源免费——构成"免费工具引流 → API 付费"的漏斗。

---

## 5. 商业化设计

### 5.1 定价（直接写定，避免后期回炉）

| 层 | 价格 | 限额 | 解锁 |
|---|---|---|---|
| Free | $0 | 50 张/月，3 个 trails | 基础选片 + 评分 + 1 篇游记/月 |
| Pro | **$19/月**（年付 $190） | 1000 张/月，无限 trails | + Lightroom 预设 + 游记无限 + Planner + 个性化 PIAA |
| Pro+ | $49/月 | 无限张 + 5 席 | + 团队共享 + 自定义品牌 + 优先队列 |
| API | $0.02 / 1k tokens 等价 | 按调用 | 美学评分 + Critic 调用，按月结算 |

**关键设计**：
- **Free 限的不是"功能"是"额度"**——用户能体验全流程，被额度卡住而不是被"灰色按钮"卡住，转化率高 3-5×（参考 Notion / Linear 设计）。
- **付费墙前必给 dopamine hit**：第一次跑完免费额度的最后 10 张时弹出"已为你处理 50 张，发现 7 张精选片 → 解锁 950 张？"——而不是冷冰冰的 quota exceeded。
- **年付折扣 17%**（约 2 个月）+ 学生 50% off（摄影爱好者大量是学生）。

### 5.2 Stripe / 计费实现

- 用 Stripe Checkout（不自建 form），webhook 接 `customer.subscription.{created,updated,deleted}`。
- 配额检查在 FastAPI middleware，存 Redis（key = `quota:{user_id}:{yyyymm}`），过期自动 reset。
- **超额行为**：不是 hard reject，是"队列降级"——超额请求降到低优先级队列，处理时间 5-10 分钟，转化提示在该队列页面强提示。

### 5.3 Anti-churn 与 Growth Loops

- **每次跑完一个 trail 自动生成"分享卡片"**（含 1 张精选 + 1 句游记 + EXIF + TrailLens 水印 + 二维码），用户分享到小红书/即刻/X 即为分发。
- **公开 trail 页面**（`/app/trails/[id]/share`）SEO 友好（OG meta + JSON-LD Photograph schema），长期沉淀地点+照片的搜索流量。
- **MCP 工具用户漏斗**：用 traillens-exif 的用户都收到一封"试试完整版"邮件。

---

## 6. 12 周冲刺计划（Sprint Plan）

每个 sprint = 2 周，6 个 sprint。每周 5 个工作日 × 4-6 h（个人项目节奏）。
每个 sprint 末尾必须有一次**公开 changelog 发布**（即使只是 build-in-public 帖）。

### Sprint 1（Week 1-2）：清场 + 接 LangGraph 真链路
- [ ] 删根目录重复 .py（用 git mv 留 history），更新 import 路径
- [ ] 装 langgraph + pydantic + 真实 PostgresSaver；让现有 5 节点跑在 LangGraph 上而非 fallback
- [ ] 起 docker-compose（postgres + pgvector + redis）
- [ ] 写 `docs/ARCHITECTURE.md`（mermaid 同步本文件 §4）
- [ ] 给 culling 节点加 `decision_trace` 写入

**交付**：`docker compose up && python -m traillens demo` 跑通真实 LangGraph，state 持久化到 postgres。

### Sprint 2（Week 3-4）：MCP server 立项 + 美学模型 baseline
- [ ] `packages/mcp_servers/exif_server.py`（pyexiv2，stdio + HTTP 双协议）
- [ ] `packages/mcp_servers/sun_moon_server.py`（astral）
- [ ] `packages/mcp_servers/weather_server.py`（Open-Meteo）
- [ ] 把 `tools/clients.py` 的对应函数换成调 MCP server（同进程 stdio）
- [ ] 跑 `chaofengc/IQA-PyTorch` 的 Q-Align 给自己 100 张照片打分，记录 baseline + 失败模式
- [ ] 起 ArtiMuse-10K Photography 子集 + 自标 50 张

**交付**：3 个 MCP server 开源到 GitHub（独立 README），baseline 数据进 `docs/EVAL.md`。

### Sprint 3（Week 5-6）：美学模型微调 + Modal 部署
- [ ] LoRA 训练（先小规模 300 张验证 pipeline 正确）
- [ ] PLCC 评估脚本接进 `consistency_check.py`
- [ ] Modal deploy：`/score` endpoint，返回 AestheticScore 8 维
- [ ] `tools/clients.py::score_aesthetics` 切换到真实 endpoint
- [ ] 写 `docs/RESEARCH.md`（含数据来源 / 标注 SOP / 偏见声明）

**交付**：HF Space 上线美学评分 demo（拖入照片 → 8 维分 + 雷达图）。

**Go/No-Go**：overall PLCC > 0.78 → 继续；否则降级为"Q-Align 调用 + 摄影规则" hybrid，但工程主线不停。

### Sprint 4（Week 7-8）：FastAPI 后端 + Next.js 骨架 + 上传链路
- [ ] FastAPI 起 `/v1/trails`, `/v1/trails/{id}/run`（SSE）
- [ ] R2 presigned PUT 直传（前端绕开 API 上传大文件）
- [ ] Next.js 起 `/app/trails/[id]`，画板 layout（参考 §3.2 ASCII）
- [ ] Vercel AI SDK 接 SSE，缩略图轨道实时高亮 + 分数滚动
- [ ] shadcn/ui 装 + 主题文件按 §2.2 锁死

**交付**：本地可用——拖入 20 张照片，看到流式选片过程。

### Sprint 5（Week 9-10）：HITL + 游记编辑器 + Stripe
- [ ] LangGraph `interrupt()` 接 HumanReview，前端实现"待审照片栏"
- [ ] 游记编辑器（TipTap）+ `/` slash menu + 浮动工具栏
- [ ] Stripe Checkout + webhook + quota middleware
- [ ] 限额超额时的"降级队列"UX
- [ ] Langfuse 自托管接上，每个 agent run 可在 Langfuse 看 trace

**交付**：完整付费链路通；3 个真实朋友/同行测试。

### Sprint 6（Week 11-12）：Lightroom 插件 + 分享页 + 公开 beta
- [ ] Lightroom Classic Plugin（LrSDK Lua）：导出选片到 LR collection
- [ ] `/app/trails/[id]/share` 公开页 + OG meta + 分享卡片图（Satori 生成）
- [ ] `/changelog` 页（mdx），写完前 12 周所有更新
- [ ] PH / HN / 小红书 / 即刻发布素材准备（30s gif + 截图 + 一句话）
- [ ] 公开 beta 上线，开 100 个早鸟名额（Pro 半价首年）

**交付**：Product Hunt 发布；200+ waitlist 转化测试。

---

## 7. 立刻可做（本周内）的 5 个具体 PR

按优先级从高到低，每个都是独立可 merge 的小 PR：

1. **`chore: 清理根目录重复脚手架`**
   删除 `business.py`, `clients.py`, `schema.py`, `orchestrator.py`, `demo.py`, `train_qalign_lora.py`（根目录），保留 `packages/` 下版本。
   `consistency_check.py` 移到 `tests/` 并改为 pytest 测试。
   验收：`python -m packages.agents.traillens_agents.demo` 仍可跑；`pytest tests/test_consistency.py` 通过。

2. **`feat(agents): 加 decision_trace + run_id 字段`**
   `state/schema.py` 给 `Photo` 加 `decision_trace`、给 `GraphState` 加 `run_id` 与 `quota_used`。
   `nodes/business.py::culling_node` 在每次写 verdict 时同步 append 一条 trace。
   验收：demo 输出每张照片都有非空 trace。

3. **`docs: 补 ARCHITECTURE.md（来自 PRODUCT_PLAN §4）`**
   把 §4.1 的 ASCII 图改成 mermaid + 补每个模块的 README 链接。

4. **`feat(mcp): 立项 traillens-exif`**
   新建 `packages/mcp_servers/exif_server/`，最小可用的 `read_exif` 工具，stdio 协议跑通；README 写 Claude Desktop 安装说明。
   验收：在 Claude Desktop 装好后能 `read_exif("file:///path/to/test.jpg")` 返回真实 EXIF。

5. **`chore: 起 docker-compose.yml（postgres + pgvector + redis）+ Makefile`**
   `make dev` 一键启依赖；`.env.example` 列全部环境变量。

每个 PR 描述里链接回本文件对应章节，让 reviewer（哪怕是未来的自己）能立刻看到 why。

---

## 8. 不做什么（同等重要）

为防止范围蔓延，下列**明确推迟到 v2 或永远不做**：

- ❌ 视频处理 / 视频游记（v2 才考虑）
- ❌ 移动 App（前 12 周 PWA 够用）
- ❌ 中文以外的 i18n（先把中英搞好）
- ❌ AI 自动调色 / 风格迁移（Aftershoot 和 LR 已经做得好，越界即输）
- ❌ 实时离线导航 / SAR 集成（合规风险高，明确不做）
- ❌ 自建 auth（用 Clerk 或 Better-Auth，省 2 周）
- ❌ 自建图床（直接 R2）
- ❌ 通用 photo critic（明确只做风光，垂直才有壁垒）

---

## 9. 衡量成功的指标（北极星 + 健康度）

| 阶段 | 北极星 | 健康度指标 |
|---|---|---|
| Sprint 1-2 | demo 跑通真实 LangGraph | 0 待办的 [TODO]，consistency_check 全绿 |
| Sprint 3 | PLCC > 0.78 | 训练成本 < $50；HF Space DAU > 10 |
| Sprint 4-5 | 3 个种子用户完整跑完 1 次 trail | p95 端到端处理 200 张 < 5 min |
| Sprint 6 | PH 发布 + 50 注册 | 注册→上传转化 > 30%；上传→分享转化 > 10% |
| Month 6 | $500 MRR 或 1000 GitHub stars 二选一 | 月 churn < 10%；NPS > 30 |

---

## 附录 A. 与现有 `compass_artifact_wf.md` 的关系

- compass 是**赛道地图**（为什么做这个赛道）
- 本文件是**施工蓝图**（这周这个月具体做什么）
- 路线图层面本文件**收紧了 compass 的 24 周计划为 12 周**——前 12 周交付可商用 beta，后 12 周根据数据决定 indie / 求职。
- 数据/指标/参考产品凡 compass 已写的不重复，需要的请直接读 compass §A-F。

## 附录 B. 决策日志（重大选择必须在这里留痕）

| 日期 | 决策 | 备选 | 选定理由 |
|---|---|---|---|
| 2026-05-26 | 主交互范式：Canvas 而非 Chat | Chat-first | 摄影师工作流是筛选不是对话 |
| 2026-05-26 | 美学模型部署在 Modal 而非自有 GPU | RunPod / 自建 | 零保留计费，初期 MAU 不确定 |
| 2026-05-26 | auth 选 Clerk 或 Better-Auth | NextAuth / 自建 | 节省 2 周；社交登录开箱 |
| 2026-05-26 | 5 个 MCP server 中 4 个开源 1 个付费 | 全开源 / 全闭源 | 构成 funnel：免费工具引流 → 美学 API 付费 |

（后续每条重大决策追加一行）
