# 本地开发指引(完整版)

> [CONTRIBUTING.md](../CONTRIBUTING.md) 给的是 5 分钟入门;这份是真正改代码时要看的。

## 1. 仓库地图

```
TrailLens/
├── apps/
│   ├── api/                   FastAPI + SSE + Stripe + Alembic
│   ├── web/                   Next.js 15 + Tailwind + shadcn 风格
│   └── lightroom-plugin/      Lightroom Classic plugin (Lua + LrSDK)
├── packages/
│   ├── agents/                LangGraph supervisor + 5 nodes(主)
│   ├── aesthetic/             美学评分模型 + Modal serve + HF Space
│   ├── annotation/            自标注工具(synth + prefill + serve + α)
│   └── mcp_servers/
│       ├── traillens_exif/
│       ├── traillens_sunmoon/
│       └── traillens_weather/
├── docs/                       本目录
├── tests/                      跨包统一测试(unittest,零依赖兼容)
├── scripts/
├── .github/                    CI / issue templates / CODEOWNERS / release flow
└── docker-compose.yml          本地依赖
```

## 2. 启什么服务做什么事

| 你想做的事 | 启动 |
|---|---|
| 跑测试 | `make test` |
| 跑 agent demo | `make demo` |
| 改 agent 节点 | 改 `packages/agents/`,跑 `make verify` |
| 调 API endpoint | `make api`(localhost:8000) |
| 调前端 UI | 先 `make api`,再 `cd apps/web && npm run dev`(localhost:3000) |
| 测 MCP server | `make mcp-exif` 然后 stdin 喂 JSON-RPC |
| 加新数据库表 | 新建 `apps/api/alembic/versions/<时间>_<描述>.py`;upgrade/downgrade 必须对称 |
| 改美学评分接口 | `packages/aesthetic/serve.py`;同步 `tests/test_aesthetic_serve.py` 的契约 7 |
| 调试 SSE | 浏览器 DevTools Network → EventStream;或 `curl -N` |

## 3. 调试技巧

### Agent 路由不对
```bash
python3 -c "
from packages.agents.traillens_agents.demo import run_fallback
from packages.agents.traillens_agents.state.schema import GraphState
from packages.agents.traillens_agents.tools import clients
final = run_fallback(GraphState(photos=clients.load_sample_photos(3)))
for m in final.messages: print(m)
"
```

### SSE 看不到流(看似阻塞)
- 检查 `headers['X-Accel-Buffering']` = 'no'(已设)
- nginx / cloudflare 前置代理需要禁用 buffering;Fly.io 默认 OK
- 浏览器 EventSource 不支持 POST,前端用 fetch + ReadableStream(见 `apps/web/lib/sse.ts`)

### MCP server 装到 Claude Desktop 不显示
- macOS 路径:`~/Library/Application Support/Claude/claude_desktop_config.json`
- 改完必须**重启** Claude Desktop
- 失败时查 `~/Library/Logs/Claude/mcp.log`

### 测试本地通 CI 红
- 大概率:你装了 pydantic v2 / Pillow / 其他可选包,本地走真实路径,CI 走 fallback 路径
- 复现:`pip uninstall pydantic Pillow && python -m unittest discover tests`

### Modal 部署失败
- 90% 是 `pyproject.toml` 里没列对依赖
- 试 `modal run packages/aesthetic/serve.py::web --detach=false` 看实时日志
- 镜像构建超 1 分钟:换 `.pip_install(...)` 行的顺序,把不变的层放前面

## 4. 性能基准(2026-05,offline 测)

| 测试 | 时长 | 备注 |
|---|---|---|
| 全套 unittest(57) | < 2s | 全部 stub,无外网 |
| make demo(8 张照片端到端) | < 1s | fallback 路径 |
| `_via_langgraph` 启动 | ~200ms | 真实 langgraph 装了的话 |
| MCP stdio 单次 RTT | ~10ms | 含子进程冷启 |
| MCP in-process 单次 | <1ms | dispatch 直调 |
| 美学评分 stub | < 1ms | url hash 算法 |
| 美学评分 Modal cold | 8-15s | A10G 镜像启动 |
| 美学评分 Modal warm | < 1s | per-image |

## 5. 常见踩坑

| 现象 | 原因 | 解决 |
|---|---|---|
| `ImportError: traillens_agents` | sys.path 没塞 `packages/agents` | 看 `apps/api/traillens_api/services/orchestrator.py` 顶部的 sys.path.insert |
| 测试一会儿过一会儿不过 | weather/sunmoon 走了真实外网 | 设 `TRAILLENS_USE_STUBS=1` |
| `make demo` 输出"weather: 毛毛雨..." | 真实调了 Open-Meteo | 同上;或者 just enjoy 真实数据 |
| 前端 `/v1/*` 404 | API 没启 / next 反代没生效 | `make api` 同时跑;next.config.mjs 已有 rewrite |
| Lightroom 插件看不到菜单 | Info.lua 路径不对 / Plug-in Manager 没加 | File → Plug-in Manager → Add → 选 `.lrdevplugin/` 目录 |

## 6. 我加了一个新 MCP server

1. `cp -r packages/mcp_servers/traillens_exif packages/mcp_servers/traillens_<name>`
2. 改 `traillens_<name>/__init__.py / core.py / server.py / __main__.py / pyproject.toml / README.md`
3. 加契约测试:验证输出 schema 与 agents 端期望对齐
4. 注册到 `packages/agents/traillens_agents/tools/clients.py`(如果是 agent 用)
5. 文档:加到 `docs/ARCHITECTURE.md` 的模块表

## 7. 我加了一个 SSE event 类型

1. 加到 `apps/api/traillens_api/schemas/trail.py::TrailRunEvent.event` 的 Literal 列表
2. 在 `services/orchestrator.py` emit
3. 前端 `apps/web/app/trails/[id]/page.tsx` 的 setTrace 分支处理
4. `apps/web/components/agent/AgentTrace.tsx::eventColor` 加色
5. 写到 docs/ARCHITECTURE.md §4.2 的 event 流契约

## 8. 我要发布一个 release

```bash
# 1. 更新 CHANGELOG.md 加 [vX.Y.Z] 段
git add CHANGELOG.md && git commit -m "docs: changelog for vX.Y.Z"

# 2. tag + push
git tag vX.Y.Z
git push origin main --tags

# 3. GitHub Actions release workflow 自动建 release(从 CHANGELOG 抽 notes)
```

## 9. 我离开项目了

- 检查 [CODEOWNERS](.github/CODEOWNERS) 把自己拿掉
- 把进行中的分支推上去并打 issue 移交
- 在 README Contributors 段保留你的名字 — 你的贡献被记住
