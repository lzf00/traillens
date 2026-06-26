# 我是怎么用 LangGraph + 豆包做多智能体的

> TrailLens 技术深度博客 #1。从骨架到生产,一个风光摄影 AI darkroom 的多智能体架构设计。

## TL;DR

5 个 agent (Culling / Critic / Story / Planner / HumanReview) 通过 LangGraph
supervisor 编排,SSE 流式向前端推事件,**关键决策**:

1. **fallback 路径优先**:即使 LangGraph 没装也能跑通完整流程 — 作品集"一键复现"零翻车
2. **agent 不直接写库**:跑在内存 GraphState,orchestrator 在 `run.finished` 时统一 persist + embed
3. **豆包 Responses API 是 OpenAI 兼容的**:`openai` SDK + `base_url` 切就行,**省一个依赖**
4. **SSE 而非 WebSocket**:HTTP/2 多路复用 + 无双向状态 + nginx 反代友好

## 1. 为什么是 LangGraph 而不是裸 Python

我**先写了裸 Python 版本**(`packages/agents/traillens_agents/demo.py` 里的
`run_fallback`)。直接 if/else 路由 5 个 agent。能跑,但 3 个问题:

- **中断后无法恢复**(HumanReview 节点要等人工)
- **不支持并发分支**(critique 和 story 可以并行)
- **流式事件需要手撸 queue**

LangGraph 解决这三个。但我**没扔掉裸 Python 版本** — 留作 fallback:

```python
async def run_trail_stream(trail_id, run_id, user_id):
    try:
        async for chunk in _via_langgraph(trail_id, run_id, user_id):
            yield chunk
    except _LangGraphUnavailable:
        async for chunk in _via_fallback(trail_id, run_id, user_id):
            yield chunk
```

`_LangGraphUnavailable` 在 `import langgraph` 失败或 `build_graph()` 抛
`ImportError` 时触发。**前端不感知差异**,SSE schema 完全一致。

这让我能:
- CI 不装 langgraph 也能跑全套 integration test
- README"零依赖 CLI demo"永不翻车
- 生产换 langgraph 版本时,fallback 仍是真备胎

## 2. SSE 的 8 个事件 schema

```typescript
type Event =
  | { event: "run.started",            data: { run_id, trail_id } }
  | { event: "orchestrator.routed",    data: { node: "culling" | ... } }
  | { event: "culling.progress",       data: { summary } }
  | { event: "culling.photo_scored",   data: { photo_id, verdict, overall } }
  | { event: "critic.photo_critiqued", data: { summary } }
  | { event: "story.delta",            data: { chunk } }
  | { event: "planner.plan_ready",     data: { plan } }
  | { event: "human_review.required",  data: { summary } }
  | { event: "run.finished",           data: { kept, total } }
  | { event: "run.error",              data: { phase, error } }
```

**踩过的坑**:LangGraph 的 `astream_events(version="v2")` 给 `on_chain_end` 时
`output` 类型不统一 — 可能是 `dict`、`GraphState`、或别的 `BaseModel`。
最初只 `isinstance(output, dict)`,**整套 photo_scored 事件从来不 emit**。

修法:三态 union:

```python
photos_iter = None
if isinstance(output, dict) and "photos" in output:
    photos_iter = output["photos"]
elif isinstance(output, GraphState):
    photos_iter = output.photos
elif hasattr(output, "photos"):
    photos_iter = output.photos
```

## 3. agent 不直接写库

agent 包是**纯函数** — `GraphState in, GraphState out`。从不调 `store`。

为什么:
- **可单测**:`run_fallback(state)` 没有 DB 依赖
- **可重放**:同一份 state 跑多次结果一致(LLM 调用除外)
- **解耦持久化**:orchestrator 决定**什么时候**写库(跑完后一次性),agent 只关心**算什么**

orchestrator 跑完 langgraph 后的 persist:

```python
store.persist_run_results(
    trail_id, last_state.photos,
    travelogue_md=last_state.travelogue_md,
    next_trip_plan=last_state.next_trip_plan,
)
# 顺手把 critique 编码进 embedding,供 Library 语义搜索
scored = [p for p in last_state.photos if p.critique]
if scored:
    vecs = embed_batch([p.critique for p in scored])
    for p, v in zip(scored, vecs):
        if v: store.write_photo_embedding(p.photo_id, v)
```

## 4. Culling 节点的真技术指标

之前 Culling 节点是 LLM 一把抓 — 同一张照片 LLM 偶尔说 blur 偶尔说 sharp。
改成"硬指标先过一遍":

```python
# OpenCV 拉普拉斯方差判模糊(<100 通常模糊)
blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

# 直方图判过/欠曝
under_pct = hist[:16].sum() / total    # 灰度 0-15 占比
over_pct = hist[240:].sum() / total    # 灰度 240-255 占比

# dHash 跨照片去重(汉明距离 < 5 视为重复)
small = cv2.resize(gray, (9, 8))
diff = small[:, 1:] > small[:, :-1]
dhash = sum((1 << i) for i, b in enumerate(diff.flatten()) if b)
```

**LLM 只对硬指标过关的照片做美学评分**。结果:
- 跑得快(LLM 调用减半)
- 决定更稳定(LLM 不再纠结模糊与否)
- 决策可解释(`reject_reason: "blur_score=42 < 100"`)

## 5. 豆包 Responses API 是 OpenAI 兼容的

很多人不知道:豆包(Volcengine Ark)`/api/v3/responses` 端点**直接兼容 OpenAI**。
不用装 `volcengine-python-sdk`:

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["ARK_API_KEY"],
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)
resp = client.responses.create(
    model="doubao-seed-2-0-pro-260215",
    input=[{"role": "user", "content": [
        {"type": "input_text", "text": "评价这张照片"},
        {"type": "input_image", "image_url": photo_url},
    ]}],
)
text = resp.output_text
```

省一个依赖。base_url 切回 OpenAI,代码不动。

**Embedding 也一样**:

```python
client.embeddings.create(model="doubao-embedding-text-240715", input=texts)
# 返回 2560d,我截断到 768d + L2 normalize 适配 pgvector(768) 列
```

## 6. SSE > WebSocket(对这个场景)

agent 跑 1-2 分钟,事件 < 30 个,**单向** server→client。WebSocket 是杀鸡用牛刀。

SSE 在浏览器里的坑:**EventSource 不支持 POST + custom headers**。
所以前端不能用 `EventSource`,要 fetch + ReadableStream 自己解析:

```typescript
async function* streamSse(url: string, init?: RequestInit) {
  const r = await fetch(url, {
    method: "POST",
    headers: { Accept: "text/event-stream", ...init?.headers },
    ...init,
  });
  const reader = r.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      yield parseChunk(chunk);  // event: xxx\ndata: {...}
    }
  }
}
```

**nginx 配置必须**:

```nginx
location /v1/ {
    proxy_pass http://api:8000;
    proxy_buffering off;        # 不缓冲流式响应!
    proxy_cache off;
    proxy_read_timeout 300s;    # SSE 长连接
}
```

`proxy_buffering off` 漏配会让 SSE 卡在 nginx buffer 里,前端看似停了。

## 7. pgvector + 豆包 embedding 的小细节

`photos.embedding` 是 `vector(768)` 列。**ivfflat 索引**:

```sql
CREATE INDEX idx_photos_emb ON photos
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

查询:

```sql
SELECT ..., 1 - (p.embedding <=> CAST(:v AS vector)) AS score
FROM photos p
WHERE t.user_id = :uid AND p.embedding IS NOT NULL
ORDER BY p.embedding <=> CAST(:v AS vector)
LIMIT 30;
```

`<=>` 是 cosine 距离(0=完全相同,2=完全相反)。`1 - dist` 给 0-1 的相似度分。

**字符串字面量**写法:`'[0.1,0.2,...]'::vector` 或 `CAST(:v AS vector)`,
后者支持参数化避免 SQL 注入。

## 8. orchestrator 是异步的,但 LangGraph 是同步的

`astream_events` 返回 `AsyncIterator`。但 fallback 走 `run_fallback(state)` 是
同步函数(纯计算 + 同步 LLM 调)。在 FastAPI 异步路由里跑同步会阻塞 event loop:

```python
# WRONG: 阻塞
final = run_fallback(state)

# RIGHT: 丢线程池
loop = asyncio.get_event_loop()
final = await loop.run_in_executor(None, run_fallback, state)
```

然后**伪流式**:跑完后按 `final.messages` 顺序 emit,每条间 `sleep(0.02)`。
UX 上看不出是回放的。

## 没做的(下一阶段)

- **token-level 流式**:`story.delta` 当前是节点跑完一次性给整段 markdown。
  接 LLM streaming response 后可逐 token emit。
- **agent 之间真正并行**:critic 和 planner 当前串行(LangGraph 默认),
  可以拆成并行分支。但 critic 输入需要 culling 的 keep 集,planner 需要 GPS,
  其实强串行也合理。
- **HumanReview interrupt 真接通**:LangGraph checkpointer 写入 Postgres,
  前端按"裁决"按钮 resume。当前是规则 fallback("分数 ≥6 → keep")。

## 代码

- `apps/api/traillens_api/services/orchestrator.py` — SSE 主入口
- `packages/agents/traillens_agents/orchestrator.py` — LangGraph build_graph
- `packages/agents/traillens_agents/nodes/business.py` — 5 节点实现
- `packages/agents/traillens_agents/demo.py` — fallback 零依赖路径

Live demo: https://traillens.zorotreeking.online/trails/demo
