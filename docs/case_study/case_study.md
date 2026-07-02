# TrailLens

## Case Study · 2026-07

**AI darkroom for landscape photographers**
**（→ 逐步演变为 AgentSaaS 模板）**

Live: [traillens.zorotreeking.online](https://traillens.zorotreeking.online) · [公开 demo](https://traillens.zorotreeking.online/trails/demo)
GitHub: github.com/lzf00/traillens
构建时间: 2026-05 至 2026-07（约 8 周）

---

## 1. 一页摘要

TrailLens 是一次徒步后**把 200 张照片丢进去 → AI 自动选片、点评、写游记、规划下次拍摄**的多智能体 SaaS。真跑起来后，我发现最初的"AI darkroom"定位有假设错误，遂将项目**演变为 AgentSaaS 模板**：同一套架构 + 3 个 example（landscape-photo / recipe-helper / stargazer）证明可复用。

**技术栈**：Next.js 15 · FastAPI · Postgres + pgvector · LangGraph · 豆包 Vision · Docker · Nginx · Tencent CVM

**代码规模**：Python 后端 15k 行 · TypeScript 前端 8k 行 · 3 套自动化 E2E · CI 4 job 全绿

**上线**：单容器 stack 运行 4 周 uptime > 99%，无关键 bug 逃逸

---

## 2. 学到的最重要的三件事

### 2.1 摄影师大概率不需要 AI 选片
调研 3 位真摄影师后：他们的肌肉记忆 + Lightroom 打分 > 任何 AI。TrailLens 建的"AI darkroom"在**解决他们不觉得是问题的问题**。真痛点可能是"300 张几乎一样的相似机位挑最佳的 1 张"——那是另一个产品。

### 2.2 LangGraph 是给工程师看的，不是给用户看的
花很多时间打磨 SSE 流式 + on_chain_end 事件识别。真用户看到的是"点 Run → 等 90 秒 → 结果"。中间的 12 个 SSE 事件他不在乎。build-in-public 圈子里 LangGraph 加分，但对终端用户零价值。

### 2.3 工程越漂亮往往越是绕开做用研
dark/light theme toggle 三态、Playwright 自动录 GIF、防 FOUC inline script。**实现的时间 > 它给用户带来的价值**，但对作品集有效。承认这点后反而轻松了——**TrailLens 的产品名应该叫 "TrailLens-portfolio"**，目标是工程能力展示，不是 PMF。

---

## 3. 架构

### 3.1 系统全貌

```
浏览器
  │
  ▼
Nginx (host, TLS)  ──┬─ /              → Next.js 15 SSR (docker)
                     ├─ /v1/*          → FastAPI (docker)
                     └─ /annotate/*    → 标注后台 (docker, cookie 白名单)
                       │
                       ▼
              Postgres + pgvector      + Redis (session/rate limit)
                       │
                       └─── 豆包 Vision / Doubao Embedding
                            (OpenAI 兼容 SDK 直接调)
```

### 3.2 Agent 编排

5 个 agent 通过 LangGraph supervisor 编排。SSE 事件推给前端，同时状态保留在内存 GraphState。跑完 orchestrator 一次性 persist + 自动 embed：

```
run.started
  ↓
Culling  (OpenCV blur/exposure + 豆包 Vision 八维评分)
  ↓
Critic   (对 KEEP 照片调豆包 LLM 写自然语言点评)
  ↓
Story    (拼 markdown 游记 + EXIF 时序)
  ↓
Planner  (下次拍摄计划：蓝金时刻、装备、焦段)
  ↓
persist_run_results + embed_batch(critique)
  ↓
run.finished
```

**关键设计**：装了 langgraph 走真实编译图；没装则走纯 Python supervisor 循环。作品集"一键复现"永不翻车。

### 3.3 store abstraction (Direction C)

```python
# 业务代码依赖 protocol，不依赖具体 store 实现
class ResourceStore(Protocol):
    def create_resource(self, *, user_id, name, resource_type='trail', ...) -> Any
    def get_resource(self, id, *, user_id) -> Any | None
    def list_resources(self, *, user_id, limit=50, resource_type=None) -> list

# TrailLens 现有 store 通过 adapter 实现 protocol
class _TrailLensAdapter:
    def get_resource(self, id, *, user_id):
        return self._s.get_trail(id, user_id=user_id)  # alias
```

trails.resource_type / photos.item_type 字段（migration 0004）让同一张表存不同业务：
- `resource_type='trail'` → 一次徒步（landscape-photo）
- `resource_type='stack'` → 一次星空拍摄（stargazer）
- `resource_type='session'` → 一次做菜会话（recipe-helper）

---

## 4. Direction A：TrailLens 本体（作品集）

Live: [traillens.zorotreeking.online](https://traillens.zorotreeking.online)

### 已实现的功能

| 模块 | 能力 |
|---|---|
| 认证 | 邮箱+密码注册登录、JWT cookie、OAuth 路由就绪 |
| Trail CRUD | 增/改名/删（级联清 COS） |
| 上传 | 服务端代理 + Pillow EXIF + 300px 缩略图 |
| Agent | 5 节点 LangGraph + fallback，SSE 流式，豆包 Vision |
| 打分持久化 | verdict / 八维 / critique / 自动 embed |
| Library 语义搜索 | 豆包 embedding + pgvector + trail 过滤 + 无限滚动 |
| 公开 demo | `/trails/demo` 自动选最佳 trail，免登录 |
| 导出 | keep 原图 zip / 小红书图文 / JSON 备份 |
| 标注后台 | 8 维评分 + 键盘快捷键 + cookie 白名单 |
| 数据健康 | 每 trail photo / scored / keep / critique / embedding 计数 |
| 主题 | dark / light / auto（跟 `prefers-color-scheme`） |

### 关键指标
- 30 个 REST 路由
- 5 张 DB 表（trails / photos / users / user_preferences / agent_runs）
- Playwright 3 套 E2E 全绿

---

## 5. Direction B：Stargazer 星空堆栈（B example）

Live: [/stack/new](https://traillens.zorotreeking.online/stack/new)

### 真痛点
星空摄影师拍 60-300 张长曝，用 Sequator / Starry Landscape Stacker 对齐 + 平均——每次试不同子集要等 10-30 分钟。挑 300 张里的坏帧（云 / 飞机轨迹 / 抖动）肉眼 30 分钟。

### 已实现
1. **frame-triage 节点**：OpenCV 拉普拉斯方差 + 直方图判 blur / cloud / underexposed
2. **stack median align**：phaseCorrelate 平移对齐 + median 合成（对异常值鲁棒）
3. **stack critic**：SNR / 星点圆度 / 动态范围 / 综合 0-10 打分
4. **前端 /stack/new**：拖入 → 分档 → 合成 → 下载

### 待做
- RAW 解码（rawpy）
- Canvas 300 帧 virtualized grid
- 后台 worker（200+ 张异步）
- 找 5 个真星空摄影师 beta

---

## 6. Direction C：AgentSaaS 模板

### 3 examples 共存

```
examples/
├── landscape-photo/       ✅ 完整线上（根 = TrailLens）
├── recipe-helper/         ✅ 骨架 + 线上 /dishes/new
│   └── agents/business.py：3 节点（search / recipe / nutrition）
└── stargazer/             ✅ PoC + triage + critic
```

同一份 template（auth / DB / SSE / 上传 / theme / 部署）承接 3 种业务。

### init_template.sh --apply

```bash
$ ./scripts/init_template.sh --apply
> App 名: JournalGen
> Slug: journal-gen
> Agents: capture, structure, summarize

生成:
  examples/journal-gen/README.md
  examples/journal-gen/agents/business.py         (3 节点 stub)
  examples/journal-gen/agents/__init__.py         (auto export)
  examples/journal-gen/tests/test_agents.py       (2 契约测试)
  examples/journal-gen/template.config.yaml
```

生成后跑单测：`Ran 2 tests in 0.000s · OK` — 骨架即开即用。

---

## 7. 4 篇博客

| # | 标题 | 主题 |
|---|---|---|
| 003 | Week in Review | 一周 build-in-public 复盘 |
| 004 | LangGraph + 豆包 Deep Dive | 8 个技术主题（fallback / SSE / pgvector 细节 / sync 包 async 等） |
| 005 | 我在 TrailLens 上想错的 7 件事 | 诚实复盘假设推翻 |
| SPEC_B | Stargazer spec | 用户路径 + 复用清单 + 5 周路线 |

**005** 是转发率最高的那类——build-in-public 圈子最喜欢的"承认错误"文章。

---

## 8. 测试报告

### 单测
- `packages/agents` 契约测试：**7/7 OK**
- `examples/recipe-helper` agent 骨架：**3/3 OK**
- `store_protocol` 等价性：**2/2 OK**
- `train_dry_run.py` 训练 pipeline：**8 dims PLCC + stub adapter 产物完整**

### Playwright E2E
- `tl-e2e-browser.py` 9 步（Landing→注册→trails→library→settings→share→登出）：**9/9 OK**
- `tl-jklm-test.py` 6 步（健康面板 / 三态 theme / FOUC）：**6/6 OK**
- `tl-nopq-test.py` 3 大项（theme system 跟随 / offset 翻页 / EXIF 入库）：**3/3 OK**

### 部署
- Tencent CVM + Docker Compose：**4 容器 healthy uptime > 25 hours**
- 宝塔 Nginx + HTTPS：**免费证书自动续签**
- GitHub Actions CI：**4 job 全绿**

---

## 9. 8 周时间线

| 周 | 主题 |
|---|---|
| W1 | 后端骨架 + LangGraph 5 节点 |
| W2 | 前端 Canvas + SSE 流式 |
| W3 | 部署 Tencent CVM + docker compose + 宝塔 nginx + HTTPS |
| W4 | 真 auth + Trail/Photo CRUD + 上传 EXIF + 缩略图 |
| W5 | pgvector 语义搜索 + Library UI + Settings 数据健康 |
| W6 | 公开 demo + 分享页 + OG card + 3 篇博客 |
| W7 | Direction B/C 探索 + 3 examples 结构 + protocol 抽象 |
| W8 | Recipe hello-world + stack critic + template 生成器 + case study |

**平均每周产出**：3-5 个新功能 + 1-2 篇文档 + 全 E2E 保持绿。

---

## 10. 关键工程决策

| 决策 | 结果 |
|---|---|
| LangGraph + fallback 双路径 | CI 不装 langgraph 也能跑 |
| agent 不直接写库 | 单测更简单 + 持久化解耦 |
| SSE 而非 WebSocket | HTTP/2 复用 + nginx 反代友好 |
| 豆包用 OpenAI SDK | 省一个依赖 |
| examples/ 而非 monorepo 顶级 | 让 template 概念清晰 |
| resource_type 字段 default 'trail' | migration 对现有数据零影响 |
| Content-Disposition RFC 5987 | 中文文件名下载不炸 |

---

## 11. 我做错的（诚实一栏）

- **过度打磨 UI**：dark/light/auto 三态实现的时间 > 用户价值
- **Library 是 over-engineering**：用户上传 100 张频率 < 1 次/年，语义搜索的边际效用近 0
- **公开 demo 用 Pexels 图**：违反 build-in-public 精神，应该用真相机原片
- **每个功能都加**：以"该有"而非"用户要"作决策标准
- **写太多博客**：4 篇够了，本该早停

---

## 12. 联系

- **邮箱**：`your-email@example.com`（占位，需填真邮箱）
- **GitHub**：github.com/lzf00/traillens
- **Live**：traillens.zorotreeking.online

如果你在招全栈 / AI / 多模态 / agent 框架方向的人，或对架构有反馈，欢迎联系。

---

*本 case study 由 Playwright chromium headless print 从 markdown 自动生成。*
*源: `docs/case_study/case_study.md`, 生成脚本: `scripts/build_case_study.py`*
