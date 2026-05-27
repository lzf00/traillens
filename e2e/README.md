# TrailLens E2E (Playwright)

Cross-layer smoke tests:web → api → agents → SSE。

## 本地跑

```bash
# 装一次
cd e2e && npm install && npx playwright install --with-deps chromium

# 起服务(2 个 terminal,或 tmux split)
make api          # localhost:8000
cd apps/web && npm run dev   # localhost:3000

# 跑测试
cd e2e
npm test
npm run test:headed   # 看真实浏览器
npm run report        # 失败 trace + 截图 + 录屏
```

## 测试集

| 文件 | 覆盖 |
|---|---|
| `landing.spec.ts` | landing 渲染 + i18n 切换 + OG card |
| `canvas-sse.spec.ts` | 创 trail → 触发 run → SSE 事件流完成 |

## CI

`.github/workflows/ci.yml` 末尾的 `e2e` job 自动启 api + web 后跑(在 CI 才启,本地手动启更省事)。
