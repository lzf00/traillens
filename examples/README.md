# Examples

> AgentSaaS template 的样例。每个子目录是一个"用这套模板做出来的应用"。
> 看了 examples 就能想象自己 fork 后能做什么。

| Example | 状态 | 说明 |
|---|---|---|
| [landscape-photo/](landscape-photo/) | ✅ 完整 | 即根目录的 TrailLens 本体(风光摄影 AI darkroom) |
| [recipe-helper/](recipe-helper/) | 🟡 stub | 食谱推荐(showcase 同一模板的另一个业务) |

## 这个目录为什么存在

把根目录的 TrailLens 当成**第一个 example**,而不是"项目本体"。
这是 Direction C(详见 [docs/SPEC_C_AGENT_TEMPLATE.md](../docs/SPEC_C_AGENT_TEMPLATE.md))
的关键认知转换:

> 项目本体 = 模板 + 5 节点 agent 抽象 + (deploy/auth/upload/embed/share)
> 单个 app = 模板实例化 + 业务节点实现

新人 clone repo 应当先看:
1. 根 README:"这是个 AI SaaS template,看 examples 想象能做什么"
2. examples 里挑一个最像自己想做的
3. 跟着 `scripts/init_template.sh` 改名 → 改 3 个 agent 节点 → 跑

## 各 example 改了什么(对比 template 默认)

| 文件 | landscape-photo | recipe-helper |
|---|---|---|
| `packages/agents/.../nodes/business.py` | culling / critic / story / planner | search / recipe-gen / nutrition |
| Landing 文案 | "AI darkroom for landscape" | "What's for dinner" |
| 数据 schema | trail + photo | session + dish |
| 上传 | 照片(jpg/raw) | 文本食材 list |
| 公开 demo | /trails/demo | /sessions/demo |
| 主色 | aurora 绿 | tomato 红 |

模板共享:auth / DB / SSE / embedding / 分享页 / theme / CI / 部署。
