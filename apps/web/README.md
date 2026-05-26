# traillens-web

Next.js 15 + React 19 + Tailwind + shadcn-style components。

## 开发

```bash
cd apps/web
npm install     # 或 pnpm install
npm run dev     # localhost:3000

# 另开一个 terminal 启 API
cd ../api
uvicorn traillens_api.main:app --reload --port 8000
```

`next.config.mjs` 已经把 `/v1/*` 反代到 `localhost:8000`,避免跨域。

## 关键路径

- `app/page.tsx` — landing(参考 PRODUCT_PLAN §2.2)
- `app/trails/[id]/page.tsx` — Canvas 主舞台(§3.2)
- `components/canvas/` — 缩略图轨道 / 雷达图
- `components/agent/AgentTrace.tsx` — 流式 agent 轨迹
- `lib/sse.ts` — 极简 SSE 客户端(POST + ReadableStream)

## 设计 tokens

颜色 / 字体 / 间距严格映射 `docs/PRODUCT_PLAN.md §2.2`。
任何改动:先改 PRODUCT_PLAN,再改 `tailwind.config.ts`。
