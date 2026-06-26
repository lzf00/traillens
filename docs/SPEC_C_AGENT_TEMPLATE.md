# Direction C Spec — TrailLens → AgentSaaS Template

> 把 TrailLens 的**架构 + DX** 抽成模板,让任何人 fork → 改 3 处 → 跑出
> "AI 简历助手 / AI 食谱助手 / ..." 的 SaaS。

## 1. 真痛点(为什么是这个)

每个想做 "AI app + 多智能体 + 流式 + 持久化 + 分享" 的开发者今天的痛:

1. **Vercel ai-chatbot** 给了聊天 + auth,但**多智能体** + **领域数据持久化** 自己写
2. **LangChain Templates** 是后端孤岛,**没前端**
3. **HuggingFace Spaces** 是 demo,**没 prod 数据库 + 用户系统**
4. **Cloudflare Agents SDK** 是 worker side,**没真 SaaS 框架**

TrailLens 摸索一周搞定的:
- 后端 FastAPI + Postgres + pgvector + Redis + 豆包/OpenAI 兼容
- 前端 Next 15 + Tailwind + SSE + dark/light theme
- agent 5 节点 LangGraph + 无依赖 fallback
- 部署 docker compose + nginx + HTTPS + cookie auth + OAuth 路由
- 持久化 + embedding + Library 语义搜索
- 公开分享页 + OG card + JSON-LD
- Playwright E2E + GitHub Actions CI

**这套就是模板的形状**。

## 2. 目标用户

- 独立开发者想做 "AI X 助手" 但不想从 0 搭基础设施
- 学校老师 / 黑客马拉松参赛者快速出 demo
- 创业公司 PoC 阶段需要 1 周出可分享的产品

**不是**:已经选定 Vercel + Supabase + LangChain Cloud 的成熟团队。

## 3. 产品形态

```bash
# Step 1: clone(或用 GitHub template "Use this template")
git clone https://github.com/<you>/agentsaas-template my-app
cd my-app

# Step 2: 跑 init 脚本(交互式问 3 个问题)
./scripts/init_template.sh
# → app name? "FoodieAI"
# → domain? "foodieai.com"
# → agents? "search / recipe-gen / nutrition" (逗号分隔)

# Step 3: 实现你的 agent 节点(只改这 1 个文件)
$EDITOR packages/agents/{your_app}_agents/nodes/business.py

# Step 4: 跑
docker compose up
open http://localhost:3000
```

**3 改之外的一切都共享**:auth / DB / 上传 / embedding / 分享页 / theme / CI / 部署 docs。

## 4. 拆模板需要做的事

### Phase 1 — 提抽出"模板核心"
- [ ] 仓库结构改名:`traillens` → `agent_saas`(参数化)
- [ ] 把 trail/photo schema 抽象成"resource/item"
  - trails → `resources` 表
  - photos → `items` 表
  - 字段 `meta jsonb` 容纳领域特定字段
- [ ] agent node 接口标准化:`(state) → state`,业务方实现 3 个就行
  - `discover_items(state)` — 对应 culling
  - `enrich_item(state, item)` — 对应 critic
  - `synthesize(state)` — 对应 story/planner

### Phase 2 — 模板化
- [ ] `template.config.yaml`:app_name / brand / agent_list / domain
- [ ] cookiecutter 或自写 `init_template.sh` 替换 placeholder
- [ ] `docs/CHECKLIST.md`:fork 后第 1 / 第 1 周 / 上线 todo

### Phase 3 — DX
- [ ] `examples/` 目录三个完整 demo:
  - `simple-chat/` — 1 个 agent 的最简 chat
  - `landscape-photo/` — 当前 TrailLens 完整版
  - `recipe-helper/` — 食谱推荐(showcase template 多业务能力)
- [ ] CI 矩阵:每个 example 单独 build 验证

### Phase 4 — 推广
- [ ] 投 ProductHunt "Agent SaaS in a box"
- [ ] 写 "从 0 到上线 AI app 的最短路径" 系列文章
- [ ] 找 5 个 fork 用户做案例采访

## 5. 竞争对手对比

| 项目 | 给了 | 没给 | TrailLens template 多给的 |
|---|---|---|---|
| **Vercel ai-chatbot** | Next + auth + chat | 多智能体 / 领域数据 / 分享页 | LangGraph + pgvector + dogfood |
| **LangChain Templates** | 后端 agent | 前端 / 数据库 / 部署 | 一整套 SaaS surface |
| **HF Spaces** | Gradio demo | 用户系统 / 持久化 / prod | 真 SaaS |
| **Cloudflare Agents** | Worker + DO | 关系型 DB / SSR 前端 / 上传管线 | 国内可部署 |

差异化:**国内开发者友好**(豆包兼容 / 腾讯 COS / 阿里云 DNS / 国内 CDN / docker)。

## 6. 时间估算

- 周 1-2:抽 resource/item 抽象,把 TrailLens 当 example 跑通
- 周 3:`init_template.sh` + 第 2 个 example (`recipe-helper`)
- 周 4:docs + tutorial 视频 + ProductHunt 发布
- 周 5+:看反馈优化

## 7. 不做这个的理由

- **模板项目难变现**:大多免费,靠流量带其他 funnel
- **竞争激烈**:Vercel / LangChain 资源比你多 100×
- **维护成本**:每次 Next / FastAPI / LangGraph 升级你都得跟,fork 者抱怨多

## 8. 做这个的理由

- **DX 是真痛点**:每个独立开发者都吃过这个亏
- **TrailLens 已经付的工程税可以 amortize 给所有 fork 者**
- **可作"GitHub 千 star repo"个人品牌**(简历杀器)
- **国内空白**:中文 + 国内云厂商 + 豆包 兼容的模板几乎没人做
