# 摄影 × 徒步 × AI Agent：一份面向 2026 年的深度项目指导方案

## TL;DR
- **最推荐的"主项目"**：构建一个名为 **TrailLens（暂名）** 的"摄影+徒步多智能体助手"——核心由 **LangGraph（Python，多智能体编排）+ Next.js/Vercel AI SDK（前端）+ Mastra 或 FastAPI（后端）+ Qwen3-VL/Claude Opus 4.7（多模态视觉）+ MCP 工具层** 组成，外挂一个 **自研的"风光摄影美学评分 + 构图诊断"算法模块**（基于 Q-Align / ArtiMuse 微调，开源单独发布）。这条路线同时满足"研究算法挑战 + 工程完整性 + 兴趣绑定 + 可商业化"四个目标。
- **作品集求职价值**：在 2026 年 AI 算法/Agent 工程岗的招聘信号中，最稀缺的不是"会调 API"，而是"能把一个真实的、能跑的、有评估指标的多智能体产品端到端落地，且包含一项可发论文级的算法贡献"。把"摄影美学评分模型 + 多 Agent 编排 + 完整全栈 + MCP 工具生态 + 真实用户/评测数据"五件套同时呈现在 README 里，远比 5 个独立的 Demo 更能拿到面试。
- **变现现实**：摄影/户外垂直 AI 工具是一个 **已被验证可单人盈利** 的赛道——Pieter Levels 的 Photo AI 在 2025 年 11 月达到约 132K USD MRR（约 158 万美元 ARR）；Aragon AI 在 2025 年 4 月达到 1000 万美元 ARR（仍为 bootstrap）；Imagen AI 早在 2022 年底就突破 1000 万美元 ARR 并完成 3000 万美元 B 轮。摄影后期 SaaS（订阅 19–49 美元/月）和户外/风光 AI 工具（订阅或一次性付费 + API）是当前可行性最高的两条变现路径。建议先按"开源 MVP → 免费 + Pro 订阅"双层模式上线，6 个月再决定是否走 indie 产品化。

---

## Key Findings（结论与判断）

1. **Agent 框架已经在 2026 年完成了一轮"产品级收敛"**：LangGraph（Python）、Mastra（TypeScript）、Claude Agent SDK、OpenAI Agents SDK、Google ADK 形成 5 家主流，其余基本是细分场景。对一个想"打作品集 + 学前沿"的算法工程师，**Python 主线建议选 LangGraph**（最适合复杂状态机、HITL、可观测性）**+ MCP 工具层**；**TypeScript 副线建议选 Mastra**，因为它的"workflow + memory + evals + tracing"一体化设计最贴合 Next.js 全栈交付。CrewAI 仅作快速 prototype 用，不建议长期押注。
2. **2025–2026 年摄影 AI 模型的研究前沿明确**：以 MLLM 为底座的"统一图像质量+美学评估（IAA）"是绝对主流。可直接微调或对比的 SOTA 包括 **Q-Align（ICML 2024, arXiv 2312.17090）、AesExpert（ACM MM 2024, arXiv 2404.09624）、UNIAA-LLaVA（arXiv 2404.09619）、ArtiMuse（CVPR 2026, arXiv 2507.14533）**。其中 ArtiMuse 提供了 10,000 张专家标注、含独立"摄影"类别的数据集 **ArtiMuse-10K**，是当前最适合做风光摄影微调的开源数据集。这给了项目"算法研究深度"的天然抓手。
3. **Vibe Coding 工具链的"产品化分层"已经清晰**：日常代码改造用 **Cursor**（Pro $20/月 + 信用池，Composer Agent 已并入 Agents Window）；大型重构/跨文件 agentic 任务用 **Claude Code**（Max 5× $100/月 是性价比甜区，**Claude Opus 4.7 于 2026 年 4 月 16 日发布**，在 SWE-bench Verified 上达 87.6%，图像分辨率提升约 3.3 倍至 3.75 MP）；前端 UI 原型用 **v0**（最佳 React/Next.js 组件质量）；快速一键全栈 MVP 用 **Lovable**（最适合非技术 demo）。本项目的建议组合是 **Claude Code（主力）+ Cursor（编辑器内联）+ v0（前端组件 scaffolding）**。
4. **MCP（Model Context Protocol）已经在 2026 年成为事实标准**：根据 Anthropic 在 2025 年 11 月一周年官方博客的披露——"Over 97 million monthly SDK downloads, 10,000 active servers and first-class client support across major AI platforms like ChatGPT, Claude, Cursor, Gemini, Microsoft Copilot, Visual Studio Code and many more."。把项目里的所有外部能力（EXIF 读取、地图、天气、Lightroom Catalog、AllTrails 数据、相机 RAW 处理）**全部封装为 MCP server**，是这个项目获得"前沿工程感"和"可被 Claude Desktop/Cursor/ChatGPT 直接调用"的关键技术决策。
5. **变现先例已被验证**：摄影类 AI SaaS 的天花板已被 Photo AI（132K MRR）、Aragon AI（10M ARR）、Imagen AI（10M+ ARR）证明远高于一般 micro-SaaS；徒步/户外赛道则有 HiiKER TrailGPT、AllTrails Peak 这种闭源订阅模型，**开源社区里反而没有强劲的"LLM 驱动的户外 Agent"**——这正是机会窗口。
6. **求职差异化要诀**：根据 alexeygrigorev/ai-engineering-field-guide（基于 2025 Q4–2026 Q1 大量真实面试样本）和多份 2025/2026 招聘文章的共同信号，能加分的不是"我用了 LangChain"，而是：**(a) 有可复现的 eval（precision/recall/latency/cost）；(b) 部署链路完整可访问；(c) 至少一个 hybrid retrieval 或自研模型贡献；(d) README 在 30 秒内可读懂 + 架构图 + Live Demo**。

---

## Details（详细方案）

### A. 8 个项目创意方向（按"研究 × 工程"双维度评分）

下表中：研究深度 = 算法挑战、可发论文/可写技术博客的潜力；工程完整性 = 适合作为作品集的端到端工程量；护城河 = 数据/算法/品牌的差异化壁垒。⭐⭐⭐⭐⭐ 为推荐主线。

| # | 项目 | 核心功能 | 研究深度 | 工程完整性 | 变现潜力 | 护城河 |
|---|------|----------|----------|------------|----------|---------|
| **1** | **TrailLens（推荐主线⭐⭐⭐⭐⭐）：风光摄影 + 徒步多智能体助手** | 上传一次徒步的整组 RAW/JPG，agent 自动生成：① 精选片（culling）② 美学评分 + 构图诊断 ③ Lightroom 预设建议 ④ 自动生成游记 + EXIF 足迹地图 ⑤ 下次同地点的拍摄计划（蓝/金时间、天气、构图建议） | 高 | 高 | 高 | 高 |
| 2 | **AI 风光构图 Copilot（手机端）** | 拍摄时实时分析取景框：三分法/引导线/前景平衡/天际线倾斜 + 建议"向左移 1 步"等可执行指令 | 高 | 中 | 中 | 中 |
| 3 | **个人照片库语义 Agent**（基于 CLIP + RAG + Immich） | "找 2024 年秋天在川西拍的有人物逆光的照片" 这类自然语言查询；可作为 Immich/PhotoPrism 的 MCP plug-in | 中 | 高 | 中 | 中 |
| 4 | **户外安全 + 天气风险 Agent** | 输入路线 GPX → 多源（气象/积雪/野生动物/SAR 历史）评估 + 装备清单 + 应急预案；可对接 Garmin inReach | 中 | 高 | 中 | 中 |
| 5 | **作品点评 / 摄影教学 Agent** | 上传作品 → 多 Agent（构图老师/光影老师/调色老师/历史风格对比）分别给评论，最后由"主编 agent"汇总 | 高 | 中 | 中 | 低（已有 AI Photo Critic 类竞品） |
| 6 | **基于 EXIF 的"摄影足迹/装备分析"** | 自动聚类你过去 X 年的拍摄行为：最常用焦段、最佳出片时间、风格演化时间线、装备升级 ROI | 低 | 中 | 低 | 低 |
| 7 | **AI 辅助风光"机位"推荐 Agent** | 给定一个地理坐标 + 季节 + 时间 → 检索社区机位库 + 太阳/月亮方位 + 历史照片 → 推荐机位 + 构图 mockup | 中 | 高 | 中 | 高（数据壁垒） |
| 8 | **徒步游记自动生成器** | 输入照片 + GPX 轨迹 → 多 Agent（行程 agent / 故事 agent / 摄影笔记 agent）协作生成图文并茂的小红书/公众号文章 | 中 | 中 | 中 | 低 |

**核心建议**：把项目 1 作为 **主作品集项目** 做深做完，把项目 2、3、7 作为 **算法/工程独立可拆模块** 沿途产出（单独开源、单独写博客）。这样 6 个月结束时你会拥有 **1 个完整产品 + 3 个独立开源仓库 + 2–3 篇技术博客**，求职面板会非常厚实。

#### TrailLens 主项目展开

**核心功能拆解**（5 个子 Agent + 1 个 Orchestrator）：
- `Orchestrator`（LangGraph supervisor）：接收用户上传的 RAW/JPG + GPX + 元信息，路由至子 agent。
- `Culling Agent`：批量过相似帧、模糊、闭眼（人像）、过/欠曝；调用自研美学评分模型（基于 Q-Align 或 ArtiMuse 微调）打分。算法挑战在于 **风光摄影场景下美学标准与 AVA 数据集的婚礼/人像偏置不一致**——这是你的算法贡献点。
- `Critic Agent`：对入选照片输出"构图诊断 + 改进建议"，使用 AesExpert 风格的描述式输出 + ArtiMuse 的 8 维评分（构图、视觉元素、技术执行、原创性、主题、情感、整体格式塔、综合评价）。
- `Story Agent`：调用地图/天气/海拔 MCP server，结合 EXIF 时间序列，生成游记。
- `Planner Agent`：输入"我下个月想再去同一地区" → 输出天气窗口、蓝/金时间、备选机位、装备清单。
- `Memory`：长期记忆使用户的拍摄风格、常用焦段、过往作品偏好（pgvector + Mem0）。

**为什么这个项目同时满足"研究 + 工程"**：
- **研究侧**：风光摄影美学评分模型是一个 **未被很好解决的问题**——主流 AVA/PARA 数据集都偏人像/普通生活照。可做的研究贡献：(a) 用 ArtiMuse-10K 的 Photography 子集 + 自己爬取的 500 Px / Unsplash Landscape 子集微调 Q-Align；(b) 加入 EXIF 元数据（焦距、光圈、ISO、拍摄时间）作为辅助特征（"context-aware aesthetic scoring"）；(c) 引入"用户个人偏好微调"（用 LoRA + 几十张用户标注样本做 PIAA—Personalized Image Aesthetics Assessment）。这至少能写出一篇 arXiv preprint 或 strong 技术博客。
- **工程侧**：完整的端到端链路涵盖 **多模态推理 + 多 agent 编排 + RAG + MCP 工具 + 持久化记忆 + 全栈 UI + 部署 + 可观测性**——几乎覆盖 2026 年 AI 应用所有关键工程模块。

**变现路径假设**：
- 免费层：50 张/月，无个性化微调。
- Pro $19/月：1000 张/月 + Lightroom 预设导出 + 个性化美学微调。
- Pro+ $49/月：无限张 + 多机位规划 + 团队共享。
- 长期：开放 MCP server 让其他 AI 工具调用你的"摄影美学 API"，按调用付费（参考 Replicate 模式）。

---

### B. 技术栈选型（2026 年 5 月最新）

#### B.1 Agent 框架矩阵

| 框架 | 语言 | 2026 现状 | 适用场景 | 我的建议 |
|------|------|-----------|----------|----------|
| **LangGraph** | Python | 1.0 GA，约 5104 万月度 PyPI 下载（pypistats.org，2026 年 4 月底快照），Klarna/Uber/LinkedIn 在产；time-travel 调试、checkpointing、HITL 一流 | 复杂状态机、生产级、需要审计 | **主线 Orchestrator 用它** |
| **Claude Agent SDK** | Python/TS | 2026.03 更名（原 Claude Code SDK），含 20+ 内置工具、subagent、hooks；Pro/Max 订阅自 2026.06.15 起单独有 Agent SDK credit | 需要 Claude 模型 + 子 agent 隔离上下文 | 用于"摄影后期专家"等专业子 agent |
| **OpenAI Agents SDK** | Python/TS | 2025.03 GA；2026.04 大改加入 sandboxing、sub-agents、原生 MCP；handoff 模式简洁 | OpenAI 生态优先 | 备选，不主推（vendor lock-in） |
| **Mastra** | TypeScript | 1.0 于 2026.01.21 发布；**1.0 发布时即已 300,000+ 周 npm 下载、19,400+ GitHub stars**（Mastra 官方 Product Hunt 公告），到 2026.02 月度下载已达约 180 万（generative.inc 分析）；workflow + RAG + evals + tracing 一体；3300+ 模型路由 | Next.js 全栈、TS 团队 | **如果你想纯 TS，主推这个** |
| **Google ADK** | Python | 2025.04 推出，A2A 协议、Vertex AI 原生 | GCP 部署 | 仅当用 Gemini 时考虑 |
| **CrewAI** | Python | 46.3K stars；MCP 支持；2–4 小时 prototype 速度 | 极快原型 | 不推荐做主框架，可第 1 周用 |
| **Pydantic AI** | Python | 16K stars；类型安全、FastAPI 风格 | 单 agent、强类型 | 用于你的"美学评分 API" wrapper |
| **AutoGen / AG2** | Python | 已并入 Microsoft Agent Framework v1.0 (2026.04) | Azure/.NET | 不推 |

**最终推荐组合**：
- **后端 Orchestrator**：LangGraph（Python） 
- **专业子 agent**：Claude Agent SDK（在 LangGraph 节点内调用）
- **工具层**：所有外部能力封装为 **MCP server**（用官方 Python SDK）
- **结构化输出 / API wrapper**：Pydantic AI
- **可观测性**：LangSmith + Langfuse（开源）

#### B.2 多模态视觉模型

| 模型 | 开/闭源 | 强项 | 用法 |
|------|---------|------|------|
| **Qwen3-VL-235B / 32B** | 开源（Apache 2.0） | 2025.09 发布；多模态推理 SOTA 开源；32B 实例可自托管 | **作为本项目主力视觉模型**（自托管/通过 SiliconFlow） |
| **InternVL 2.5 / 3** | 开源 | 78B 用 1/10 训练 token 即超过 Qwen2-VL-72B | 与 Qwen3-VL 二选一 |
| **Claude Opus 4.7** | 闭源 | **2026.04.16 发布**；图像输入支持约 3.75 MP（约前代 3.3 倍）；SWE-bench Verified 87.6%；最强推理 | 用于"摄影评论"子 agent |
| **GPT-4o / GPT-5 Vision** | 闭源 | OCR + 通用 VLM | 仅做 fallback |
| **Gemini 2.5 Pro** | 闭源 | 长视频理解 | 视频徒步 vlog 分析 |

#### B.3 摄影美学/质量评分（你的算法核心）

| 项目 | 类型 | 用途 |
|------|------|------|
| **chaofengc/IQA-PyTorch**（~3.2k stars） | 开源工具箱 | **你的 baseline**，一行调用 30+ 指标（NIMA、MUSIQ、TOPIQ、Q-Align） |
| **Q-Align**（arXiv 2312.17090, ICML 2024） | MLLM-based IAA/IQA | **微调起点** |
| **AesExpert**（arXiv 2404.09624, ACM MM 2024） | MLLM 风格化点评 | 用于 Critic Agent 的描述式输出 |
| **UNIAA-LLaVA**（arXiv 2404.09619） | 统一框架 | 备选 |
| **ArtiMuse + ArtiMuse-10K**（arXiv 2507.14533, CVPR 2026） | 8 维语言评估 + 摄影类数据集 | **最新 SOTA，含独立摄影类数据，强烈推荐** |
| LAION-Aesthetics v2 | CLIP-based 经典 | 弱基线对比 |
| Google NIMA (2018) | CNN 经典 | 弱基线对比 |

**数据集**：AVA（25 万张，但偏婚礼/人像）、AADB、PARA（3.1 万）、TAD66K、ICAA17K（艺术）、**ArtiMuse-10K（含独立 Photography 子类，2025 年新发布）**、自爬 500px + Unsplash Landscape 子集（建议自建 1000–3000 张专家标注）。

#### B.4 Vibe Coding 工具链

| 工具 | 2026 现状 | 你的用法 |
|------|-----------|----------|
| **Claude Code（Opus 4.7）** | SWE-bench Verified 87.6%；Max 5× $100/月；1M context | **主力大型重构 + 跨文件代码生成** |
| **Cursor 3.0** | Composer 并入 Agents Window；Design Mode；$20 Pro 含信用池 | **日常编辑器内联补全 + 小型 agent 任务** |
| **Windsurf 2.0**（Cognition 旗下） | SWE-1.5 模型快 13×；Agent Command Center | 备选；多 IDE 跨编辑器需要时 |
| **v0 by Vercel** | 最佳 React/Next.js + shadcn/ui 组件 | **前端组件 scaffolding** |
| **Lovable** | 全栈 prompt-to-app，含 Stripe/auth | 仅用于 landing page MVP |
| **Bolt.new** | Browser 全栈 | 替代 Lovable |

**实战策略**：80% 时间在 Claude Code + Cursor；前端"截屏 → 复刻 UI 组件"丢给 v0；landing page 用 Lovable 半小时搞定。

#### B.5 全栈技术选型

| 层 | 选型 | 理由 |
|---|------|------|
| 前端 | **Next.js 15 + React 19 + Tailwind + shadcn/ui** | v0 生成的代码原生兼容；SSR/RSC 利于 SEO |
| 后端 | **FastAPI（Python，主）+ LangGraph 应用** | 与 ML 模型同语言；async 性能足够 |
| 数据库 | **PostgreSQL + pgvector**（向量）+ Redis（缓存/队列） | pgvector 已是 2026 RAG 默认 |
| 向量/嵌入 | **CLIP ViT-L/14 + OpenCLIP** 或 **SigLIP 2** | 用于图片语义检索 |
| 文件存储 | **Cloudflare R2 / Backblaze B2**（S3 兼容，便宜） | RAW 文件较大 |
| 长期记忆 | **Mem0** 或 LangGraph checkpointing + Postgres | |
| 部署 | **前端 Vercel；后端 Fly.io / Railway / Modal**；GPU 推理 **Replicate / RunPod / Modal** | Modal 适合零保留 GPU 推理 |
| 可观测性 | **Langfuse**（开源自托管）+ **OpenTelemetry** + **Sentry** | |
| 评估 | LangSmith / Langfuse + 自建 eval 集（200 张专家标注） | 作品集硬通货 |
| CI/CD | GitHub Actions + Docker | |
| 工具协议 | **MCP server** 暴露所有工具能力 | 关键差异化 |

---

### C. 可借鉴的开源标杆与商业先例

| 项目 | 类型 | 状态 | 借鉴点 |
|------|------|------|--------|
| **chaofengc/IQA-PyTorch** (~3.2k★) | 开源 | 活跃 | 美学评分 baseline；API 设计；目前 GitHub 上最完整的 IAA/IQA 工具箱 |
| **idealo/image-quality-assessment** (~2.1k★) | 开源 | 已归档 2024.12 | NIMA 权重可直接复用 |
| **photoprism/photoprism** (~37k★) | 开源 | 活跃 | EXIF 处理 + 自托管架构 |
| **immich-app/immich** (~98k★) | 开源 | 高速增长 | CLIP 语义搜索 + face recognition + 移动 App；目标对标 Google Photos |
| **kylecorry31/Trail-Sense** (~2.6k★) | 开源 | 活跃（v7.7.0 于 2026.04） | 户外离线 sensor 应用最完整的开源参考；纯 Kotlin/Android，纯离线 |
| **HarimxChoi/langgraph-travel-agent** | 开源 | 学习模板 | LangGraph 多 agent + Amadeus API + HITL |
| **thunderbolt215/ArtiMuse** | 学术 | 新 | 最新美学评估 SOTA + 数据集 |
| **reinaldosimoes/ai-photo-critic** | 开源 | 小 | LangChain + GPT-4o Vision 的 photo critic 模板 |

**商业先例**（参考变现可行性）：
- **Photo AI** by Pieter Levels：2023.02.10 上线 → 2025.11 约 132K USD MRR（≈1.6M ARR）；solo 开发 + Twitter 422K 粉丝分发；Stable Diffusion + Replicate 托管。
- **Interior AI** by Pieter Levels：2025.11 约 40–45K MRR；GPU 月开销仅约 200 USD，>99% 毛利。
- **HeadshotPro** by Danny Postma：2023 年内峰值约 300K MRR；一次性付费 $29–$59；联盟营销贡献 50K+/月。
- **Aragon AI** by Wesley Tian：2025.04 达 10M USD ARR，仍 bootstrap，11–15 人，2M+ 用户、4000 万+ 张照片。
- **Imagen AI**（专业摄影师后期 SaaS）：2022.12 已 10M+ ARR，2022.12 完成 30M Series B（Summit Partners + NFX 领投），226 人团队（2026.03），每年处理 1.5 亿+ 张照片。
- **HiiKER TrailGPT**：HiiKER 团队（爱尔兰）2024 年内基于其 10 万+ 条 trail 数据库 + 实时天气 + 用户徒步历史发布的 LLM 徒步助手，作为 PRO+ 订阅功能。
- **AllTrails Peak**：2025 夏季新发布的高阶订阅层，含 AI custom routes 和 wrong-turn alerts；按 Crunchbase 平台公开口径，AllTrails 帮助"over 60 million people worldwide find their way outside"。

---

### D. 作品集 + 求职价值最大化策略

**1. 项目结构（什么样的 GitHub 仓库能拿面试）**：
```
traillens/
├── README.md           # ★★★ 30秒内说清楚 What/Why/How + 架构图 + Demo 链接
├── docs/
│   ├── ARCHITECTURE.md # Mermaid 架构图
│   ├── EVAL.md         # 评估指标、数据集、复现命令
│   └── RESEARCH.md     # 美学模型研究笔记 + arXiv 引用
├── apps/
│   ├── web/            # Next.js 前端
│   └── api/            # FastAPI 后端
├── packages/
│   ├── agents/         # LangGraph 多 agent
│   ├── aesthetic/      # 自研美学评分模型（独立可用，独立开源 repo 镜像）
│   ├── mcp-servers/    # EXIF / Weather / GPX / Lightroom MCP
│   └── eval/           # 评估脚本
├── infra/              # Docker + Fly.io / Modal
└── .github/workflows/  # CI + eval-on-PR
```

**2. README 必备六要素**（来自 2025/2026 AI 招聘 field guide 共识）：
1. **一句话定位** + 视频/GIF demo（≤30s）
2. **架构图**（Mermaid 即可）
3. **Live demo URL**（即使是 50 RPS 限流的免费层）
4. **Eval 表格**：你的美学模型 vs Q-Align / ArtiMuse 在 ArtiMuse-10K Photography 子集上的 PLCC / SRCC；latency p50/p95；cost per request。
5. **一键复现**：`docker compose up` 或 `pip install` + `python -m traillens.cli demo`
6. **Tradeoff 段**：你为什么选 LangGraph 而不是 CrewAI？为什么自托管 Qwen3-VL 而不是 GPT-4o？写清楚就是工程成熟度信号。

**3. 社区涨星的杠杆**：
- **首发节奏**：开源美学评分子模块（独立 repo）→ 在 Hugging Face 发模型权重 → 写一篇 ArtiMuse 风格的技术博客 → 发 Hacker News / r/MachineLearning / r/LocalLLaMA / 即刻 → 发 X（@levelsio 等 indie 大 V）→ Show HN → Product Hunt。
- **持续运营**：每周 1 篇 build-in-public 帖子（参考 Senja.io 三年到 $83K MRR 的路径）；每月 1 个新 MCP server 释出。
- **可观测的影响力指标**：GitHub stars / HuggingFace downloads / npm or PyPI downloads / Live demo MAU / 真实用户截图。

**4. 求职信号清单**（按 2025 Q4–2026 Q1 真实面试样本提炼，参考 alexeygrigorev/ai-engineering-field-guide）：
- ✅ 自己微调过 MLLM（不是只调 API）
- ✅ 用过 LangGraph / Claude Agent SDK 写过 5+ 节点的图
- ✅ 写过 MCP server
- ✅ 有可复现的 eval（不只是 demo）
- ✅ Live demo + Docker + CI
- ✅ 架构图 + tradeoff 写作
- ✅ 算法贡献（arXiv preprint > 技术博客 > Issue/PR 到 Q-Align）

---

### E. 变现路径详细推演

| 阶段 | 形态 | 收入预期 | 关键动作 |
|------|------|----------|----------|
| **阶段 0（M1–2）** | Pure 开源 + 个人作品集 | 0 USD，但 GitHub stars + HF downloads 为后续背书 | 发布美学评分模型 + LangGraph template |
| **阶段 1（M3–4）** | 免费 Web App + waitlist | 0 USD | Twitter/小红书 build in public；收集 200+ waitlist |
| **阶段 2（M5–6）** | Pro 订阅上线 | 目标 $500–$2K MRR | Stripe 接入；Pro $19/月；Lightroom Plugin |
| **阶段 3（6–12 个月）** | API + 团队版 | 目标 $5–$15K MRR | Pro+ $49/月；API 按调用计费（Replicate 模式）；联盟营销 |
| **阶段 4（>12 个月）** | 选择道路：(a) SaaS 化做 indie 产品 / (b) 留作品集开源 / (c) 卖给摄影品牌 | 视选择 | 取决于第 9–12 月数据 |

**可参考的定价**：
- 摄影师后期 SaaS 行业标准：$19–$49/月（Aftershoot $45/月，Imagen 按张数，Narrative $20–$50/月）。
- AI 头像/人像类一次性 $29–$59（HeadshotPro / Aragon）。
- 户外/徒步 freemium：AllTrails+ $35.99/年，Peak 是更高一档；ARPU 约 $3/月。
- **你的最佳定价点**：Pro $19/月（参照 Photo AI 入门档 + 摄影师群体付费意愿）。

**风险提示**：
- 摄影师群体对"AI 自动选片"的精度容忍度高，但对"AI 修改风格"敏感——务必让用户可控（人在环）。
- 户外/徒步类 AI 路线规划已被加拿大 BC 省 SAR 等机构警告过"AI 幻觉导致的搜救增加"。**根据 BC 政府 2024.08 官方新闻稿（gov.bc.ca）："GSAR groups were deployed to 1865 incidents in B.C. in 2023 and to 1030 incidents to date in 2024."**——这是你设计路线规划 Agent 时必须正视的安全背景。**强烈建议你的路线规划 Agent 强制声明免责 + 显示数据来源 + 不脱离已验证 trail 数据库**。

---

## F. 6 个月分阶段路线图

### M1（启动月）：技术热身 + 数据准备
- **Week 1**：用 LangGraph 复刻一个最小可用的多 agent（参考 HarimxChoi/langgraph-travel-agent），打通 Anthropic/OpenAI API + Tavily 搜索；体验 CrewAI 半天理解差异。
- **Week 2**：跑通 chaofengc/IQA-PyTorch；用 Q-Align 给自己 1000 张风光照片打分，理解失败模式。
- **Week 3**：下载 ArtiMuse-10K + AVA，建立自己的"风光摄影专家标注子集"（300 张，自评分 + ChatGPT-5 辅助标注 + 自校验）。
- **Week 4**：写第 1 个 MCP server（EXIF reader），发布到 GitHub。完成最小 Next.js + FastAPI 骨架。

**交付物**：①一个开源 MCP server（EXIF）；②美学评分 baseline notebook 公开；③ Twitter/小红书"build in public" 启动。

### M2（核心算法月）：微调你的美学评分模型
- **Week 5–6**：用 LoRA 在 Q-Align 上微调 ArtiMuse-10K Photography + 自标 300 张子集；目标 PLCC > 0.78（Q-Align baseline 约 0.75）。
- **Week 7**：把模型部署到 Hugging Face Inference Endpoint / Modal；写成 OpenAI 兼容的推理 API。
- **Week 8**：写第一篇技术博客《Beyond AVA: Fine-tuning Q-Align for Landscape Photography Aesthetics》，发布到 Medium + 知乎 + HF 博客。

**交付物**：①一个开源美学评分模型（权重 + 推理代码）；② Hugging Face Space demo；③ 技术博客；④ arXiv preprint（可选但加分巨大）。

### M3（多 Agent 编排月）：把 TrailLens 骨架搭起来
- **Week 9**：用 LangGraph 实现 Orchestrator + Culling + Critic + Story + Planner 5 个节点；用 Pydantic 定义 State；接入 Langfuse tracing。
- **Week 10**：把美学评分模型作为 MCP tool 暴露；把天气（OpenWeather / Open-Meteo）、海拔、地图（Overpass API）、Sun/Moon（Astral）封装为 MCP servers。
- **Week 11**：实现 RAG：用户照片 → CLIP 嵌入 → pgvector；支持自然语言查询。
- **Week 12**：Human-in-the-loop：用户可以"驳回"agent 选片建议，反馈回流到 Mem0 个性化记忆。

**交付物**：①完整的 LangGraph + MCP demo 视频；② Live demo 上线（限流免费）。

### M4（全栈与产品化月）：让普通摄影师能用
- **Week 13–14**：v0 + shadcn/ui 做主界面；上传 → 等待 → 选片 → 评论 → 游记 → 下载 ZIP；Stripe 接入（Lemon Squeezy 也行）。
- **Week 15**：Lightroom plugin（LrSDK）一键导出选片到 LR；这是摄影师付费的关键转化点。
- **Week 16**：性能优化、Eval、压测；写完整 README + 架构图 + Eval 表。

**交付物**：①公开 beta 上线；② Product Hunt + Show HN 发布预热；③ 招募 50 个种子用户。

### M5（发布与冷启动月）
- **Week 17**：Product Hunt + Show HN + Hacker News + r/photography + 小红书 + 即刻同步发布；目标 1000 GitHub stars / 200 注册用户。
- **Week 18**：联系 PetaPixel / Fstoppers / 国内"图虫"等摄影媒体；联系 Lightroom YouTube KOL。
- **Week 19**：根据真实用户反馈做大改；建立每周一更的 changelog。
- **Week 20**：第一笔付费收入（即使只是 1 个 $19/月也是大里程碑）。

**交付物**：①前 100 个真实用户；②首个付费用户；③ 1 万+ 累计 PV。

### M6（变现验证 + 求职准备月）
- **Week 21–22**：根据 4 周真实数据决定走向——MRR 增长率 > 30%/月 → 继续 indie 路；否则收紧产品定位，主打作品集。
- **Week 23**：写求职 portfolio 文档（含项目 1 主作 + 美学模型 + MCP servers + 技术博客 + arXiv preprint + 1000+ stars 数据）。
- **Week 24**：投递 AI 算法 / Agent 工程方向岗位；以 TrailLens 作为面试 60% 的话题载体。

**6 个月结束你将拥有**：
- 1 个 active 的多模态多 agent 产品（带真实用户）
- 1 个开源美学评分模型（带 HF Space + 权重 + 论文）
- 4–6 个开源 MCP servers
- 2–3 篇高质量技术博客
- ≥ 1000 GitHub stars（可达目标，参考 Mastra 在 1.0 发布即 19,400+ stars、Senja 三年 $0→$1M ARR 路径）
- 一份"研究 + 工程"双叙事的求职 portfolio

---

## Recommendations（行动建议与触发条件）

### 立即执行（本周内）
1. **不要试图同时做 8 个想法。** 选择 TrailLens 主线，把其他想法降级为"沿途产出的子模块"。
2. **本周开通**：GitHub 项目仓库 + Vercel 账号 + Modal 账号 + Hugging Face 账号 + Twitter（如果还没）+ Anthropic API + OpenAI API + LangSmith 免费层。
3. **本周读完**：(a) LangGraph 官方多 agent supervisor tutorial；(b) Q-Align 论文（arXiv 2312.17090）；(c) ArtiMuse 论文（arXiv 2507.14533）；(d) MCP 官方 spec（modelcontextprotocol.io/specification/2025-11-25）。

### 第 1 个月内
4. 启动 build-in-public：每周一篇 Twitter/即刻进展帖。
5. 拍/选 300 张风光照片做自标注 → 这是你的数据壁垒起点。
6. 先把 EXIF MCP server 发到 GitHub 拿前 50 个 stars。

### 第 3 个月触发点（决定继续 vs 转向）
- ✅ 如果美学模型 PLCC > 0.78 且博客在 HN/Reddit 上 > 100 upvotes → 继续主线。
- ❌ 如果美学模型微调反复失败、训练 cost 失控 → **降级算法目标**：改做"基于 Q-Align 调用 + 摄影规则系统"的 hybrid critic，仍保留工程完整性。
- ❌ 如果 LangGraph 复杂度劝退你 → 切到 **Mastra（TS）+ Vercel AI SDK** 重做骨架（2 周内可完成）。

### 第 6 个月触发点（决定 indie 化 vs 求职）
- 触发 indie 化：MRR > $1.5K 且月增 > 30% 且付费用户留存 > 80%。
- 触发求职：MRR < $500 但 GitHub stars > 800 且至少完成 1 篇高质量博客和 1 个完整 demo。

### 持续动作
- **每周**：1 篇 build-in-public 帖；1 次 eval 数据更新；1 次 changelog；监控 Langfuse cost。
- **每月**：1 个新 MCP server；1 篇深度博客；1 次外网（HN/小红书）发布尝试。
- **每季**：与 1 位摄影师 + 1 位户外向导做 1 小时用户访谈。

---

## Caveats（风险与不确定性）

1. **模型 / 框架快速迭代风险**：本报告基于 2026.05 信息。LangGraph、Mastra、Claude Agent SDK 在过去 12 个月经历过 ≥ 2 次重大 API 变更；建议 **至少每季锁定一次依赖版本**，并避免使用 beta 特性作为生产依赖。
2. **美学评分模型的主观性**：LAION-Aesthetics 等模型已被学术界批评含有"算法凝视"偏见（参考 FAccT '26 Audit paper，arXiv 2601.09896）。你的微调结果应当公开训练数据的来源、标注流程、限制；并避免把模型部署为"客观评分"——而是定位为"个人风格助理"。
3. **AI 户外路线推荐的安全风险**：BC 搜救等机构已记录到 AI 错误路线导致的真实事故。若产品包含路线/天气建议，必须 (a) 不脱离已验证 trail 数据；(b) 显式免责声明；(c) 强烈推荐不要做"实时离线导航替代"。
4. **GPU / API 成本**：自托管 Qwen3-VL-32B 在 Modal A100 上约 $1.5/小时；Claude Opus 4.7 输入 $5/MTok、输出 $25/MTok。月预算建议从 $100–$200 起步；超过 1000 用户时再讨论自托管 vs API 的拐点。
5. **变现存在显著生存偏差**：上文引用的 Photo AI、Aragon、Imagen 都是赢家叙事；摄影/户外赛道也有大量 0–$1K MRR 的失败项目（multiple Indie Hackers post-mortems）。建议把"变现"作为可选目标，把"作品集 + 求职 + 开源影响力"作为底线目标。
6. **数据合规**：用户上传的 RAW 文件可能包含 GPS 位置；EU GDPR 与中国《个人信息保护法》均要求显式告知与最小化收集。设计上建议默认本地处理 + 用户主动上传选项。
7. **MCP 仍是新协议**：截至 2026.05 已有约 9700 万月下载、10,000 个活跃 server（Anthropic 官方 2025.11 一周年博客口径），但 OAuth 2.1 企业认证仍在路线图上。若你的项目要做企业版，需要等待 2026 后半年的标准化完善。
8. **某些数字为公开自述**：Photo AI / Interior AI 的 MRR 来自 levelsio 个人公开发布；Aragon ARR 来自创始人播客；HeadshotPro 的 $300K 是峰值非当前；Imagen AI 的 $10M ARR 是 2022 年底数据。请把这些视为"该赛道天花板存在"的证据，而非"你也能达到"的保证。