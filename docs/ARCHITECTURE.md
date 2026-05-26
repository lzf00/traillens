# TrailLens 架构说明

> 本文件是**面向 reviewer 与未来 contributor 的"系统外貌图"**——
> 想了解"为什么这样做"与"路线图"请读 [PRODUCT_PLAN.md](PRODUCT_PLAN.md)；
> 想了解"赛道判断"请读 [../compass_artifact_wf.md](../compass_artifact_wf.md)。

---

## 1. 系统全景

```mermaid
flowchart LR
    User([用户浏览器])

    subgraph Web["apps/web — Next.js 15"]
        UI[Canvas 主舞台<br/>RSC + Vercel AI SDK]
        Upload[R2 presigned PUT<br/>大文件直传]
    end

    subgraph API["apps/api — FastAPI"]
        REST[REST endpoints]
        SSE[SSE stream<br/>/trails/:id/run]
        MW[middleware<br/>auth / quota / trace]
    end

    subgraph Agents["packages/agents — LangGraph"]
        ORC[orchestrator<br/>supervisor]
        CUL[culling]
        HR[human_review<br/>HITL interrupt]
        CRI[critic]
        STO[story]
        PLA[planner]
        CKPT[(PostgresSaver<br/>checkpoint)]
    end

    subgraph MCP["packages/mcp_servers — MCP"]
        EXIF[traillens-exif]
        WEA[traillens-weather]
        SUN[traillens-sunmoon]
        TRAIL[traillens-trails]
        AES[traillens-aesthetic<br/>付费]
    end

    subgraph Model["packages/aesthetic — Modal"]
        QA[Q-Align + LoRA<br/>/score endpoint]
    end

    subgraph Infra["基础设施"]
        R2[(Cloudflare R2<br/>RAW/JPG)]
        PG[(Postgres + pgvector)]
        REDIS[(Redis 队列)]
        STRIPE[Stripe]
        LF[Langfuse]
    end

    User -->|HTTPS| UI
    UI -->|presigned URL| Upload
    Upload -.直传.-> R2
    UI -->|SSE| SSE
    UI -->|REST| REST

    REST --> MW --> Agents
    SSE --> MW --> Agents

    ORC <--> CUL
    ORC <--> HR
    ORC <--> CRI
    ORC <--> STO
    ORC <--> PLA
    Agents <-.checkpoint.-> CKPT
    CKPT --> PG

    CUL -->|score| AES --> QA
    CUL --> EXIF
    STO --> WEA
    PLA --> SUN
    PLA --> TRAIL

    Agents -->|trace| LF
    MW -->|usage| STRIPE
    MW -->|read| PG
    Agents -->|RAG embed| PG

    classDef done fill:#2d4a3e,color:#fff,stroke:#6FBF8B
    classDef todo fill:#3a2929,color:#fff,stroke:#D97757,stroke-dasharray:3 3
    class ORC,CUL,HR,CRI,STO,PLA done
    class UI,Upload,REST,SSE,MW,EXIF,WEA,SUN,TRAIL,AES,QA,R2,PG,REDIS,STRIPE,LF,CKPT todo
```

绿色实线 = 已有骨架；红色虚线 = 路线图待落地（参见 PRODUCT_PLAN §6 Sprint 计划）。

---

## 2. Agent 子图（supervisor 路由）

```mermaid
stateDiagram-v2
    [*] --> orchestrator
    orchestrator --> culling: 任何照片 verdict 为空
    orchestrator --> human_review: pending_review_ids 非空
    orchestrator --> critic: keep 照片有未点评
    orchestrator --> story: travelogue_md 为空
    orchestrator --> planner: hike.gps_lat 非空 & next_trip_plan 为空
    orchestrator --> [*]: FINISH

    culling --> orchestrator
    human_review --> orchestrator
    critic --> orchestrator
    story --> orchestrator
    planner --> orchestrator
```

**为什么是 supervisor 而非线性串联**：
- HITL 中断、条件跳过（无 GPS 则跳过 Planner）、可观测性都需要显式状态机。
- 路由可演化为 LLM-as-router（GraphState 加 `route_reason` 字段即可），不改图结构。
- LangGraph 的 conditional_edges + checkpointer 是这类编排的最小依赖；CrewAI 等线性流不适合。

实现入口：
- 路由器：[`orchestrator.decide_next`](../packages/agents/traillens_agents/orchestrator.py)
- 节点：[`nodes/business.py`](../packages/agents/traillens_agents/nodes/business.py)
- 状态契约：[`state/schema.py`](../packages/agents/traillens_agents/state/schema.py)

---

## 3. 模块责任表

| 模块 | 单一职责 | 主要依赖 | 是否可独立运行 |
|---|---|---|---|
| `packages/agents` | 多 agent 编排 + 状态 | langgraph, pydantic | ✅ 零依赖 fallback |
| `packages/aesthetic` | 美学评分模型训练 + 推理服务 | torch, peft, transformers | ✅ demo-metric 子命令 |
| `packages/mcp_servers/*` | 各自一个原子能力 | mcp-sdk + 特定第三方 | ✅ 每个 server 独立发布 |
| `apps/api` | HTTP 接口 + SSE + middleware | fastapi, sqlalchemy, stripe | ❌ 依赖 postgres/redis |
| `apps/web` | UI、上传、Canvas | next, vercel-ai-sdk, shadcn | ❌ 依赖 api |

**契约保护**：跨模块契约由 [`tests/test_consistency.py`](../tests/test_consistency.py) 5 个 contract test 守住——任何一项被破坏，CI 红。

---

## 4. 关键数据流（一次 Trail run）

```mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant W as web (Next)
    participant A as api (FastAPI)
    participant G as agents (LangGraph)
    participant M as Modal (Q-Align)
    participant R as R2

    U->>W: 选择 200 张 RAW + GPX
    W->>A: POST /v1/trails {name, gpx_uri}
    A-->>W: 201 {trail_id, presigned URLs[]}
    W->>R: PUT 直传(并行)
    W->>A: POST /v1/trails/:id/photos:bulk {uris[]}
    W->>A: POST /v1/trails/:id/run
    A-->>W: 200 text/event-stream
    A->>G: invoke(GraphState)

    loop 每张照片
        G->>G: culling.detect_technical (本地)
        G->>M: POST /score (远端 GPU)
        M-->>G: AestheticScore 8 维
        G-->>A: event: culling.photo_scored
        A-->>W: SSE 推送
    end

    G->>G: human_review (interrupt if needed)
    G->>G: critic / story / planner
    G-->>A: event: run.finished
    A-->>W: SSE end
    W->>U: 渲染作品板
```

**关键设计抉择**：
- 大文件**直传 R2**，不走 API（省带宽、绕开 API 文件大小限制）。
- 评分 **stream 回前端**而非一次性返回（§3.1 M1 Stream-First）。
- HITL 用 **LangGraph interrupt + PostgresSaver**，断电也能恢复。

---

## 5. 部署拓扑（目标态）

| 组件 | 平台 | 计费模式 | 备注 |
|---|---|---|---|
| `apps/web` | Vercel | 按 invocation | edge runtime 优先 |
| `apps/api` | Fly.io / Railway | 按容器小时 | 多区域，靠近 R2 |
| `packages/aesthetic` (推理) | Modal | 按 GPU 秒 | 零保留，冷启动可接受 |
| `packages/mcp_servers/*` | npm / pypi 发布 + 可选托管 | — | 用户本地装最常见 |
| Postgres + pgvector | Neon / Supabase | 按存储 + 计算 | 备份每日 |
| Redis | Upstash | 按命令 | 队列 + session |
| Langfuse | 自托管 Docker | — | 数据敏感，避免 SaaS |

---

## 6. 演进与版本策略

- **State schema 是核心契约**，演进遵循"加字段必须默认值、改字段必须迁移"的规则；新增字段必须更新 `tests/test_consistency.py`。
- **LangGraph / langgraph-checkpoint** 每季锁版本（参考 PRODUCT_PLAN §"风险"）。
- **MCP server 协议** 跟随 modelcontextprotocol.io 官方 spec；server `init` 时声明支持的 protocol 版本。

---

## 7. 与其他文档的引用关系

```
README.md              30s 卖点 + Quick Start          [面向陌生人]
├── docs/
│   ├── ARCHITECTURE.md  本文(系统是什么样)              [面向 contributor]
│   ├── PRODUCT_PLAN.md  产品定位 + Sprint 计划         [面向团队/未来的自己]
│   ├── EVAL.md          (TODO) 美学模型指标表           [面向 reviewer / 招聘方]
│   └── RESEARCH.md      (TODO) 美学微调研究笔记         [面向 ML reviewer]
└── compass_artifact_wf.md  赛道调研报告                [战略背景]
```
