# Example: stargazer(星空堆栈)

> AgentSaaS template 的第 3 个 example:**Direction B 的产品化**。
> 独立 spec 见 [docs/SPEC_B_STARGAZER.md](../../docs/SPEC_B_STARGAZER.md)。

## Live PoC

- 前端: https://traillens.zorotreeking.online/stack/new
- 后端: `POST /v1/trails/{id}/stack:preview`
- 算法: [`apps/api/traillens_api/services/stacker.py`](../../apps/api/traillens_api/services/stacker.py)

## 业务定义(对齐 template abstraction)

| 抽象 | 对应 |
|---|---|
| `resource` (trails.resource_type='stack') | 一次星空拍摄会话 |
| `item` (photos.item_type='stack_frame') | 单张长曝 raw frame |
| **agent 1** `frame-triage` | 用 blur/cloud/plane 检测过滤 |
| **agent 2** `stacker` | OpenCV phaseCorrelate align + median 合成 |
| **agent 3** `stack-critic` | SNR / 星点圆度 / 银河饱和度 打分 |
| 公开 demo | `/stack/demo` 显示 3 个候选堆栈对比 |

## 当前 PoC 覆盖

| Phase | 状态 |
|---|---|
| 后端 stack algorithm (median align) | ✅ `services/stacker.py` |
| API endpoint | ✅ `/v1/trails/{id}/stack:preview` 支持 2-200 张 |
| 前端 upload UI | ✅ `/stack/new` |
| trails.resource_type 分类 | ✅ migration 0004 加了字段(默认 'trail', 'stack' 待用) |
| frame-triage(云/飞机检测) | ⏳ 未做 |
| stack-critic(SNR 打分) | ⏳ 未做 |
| RAW 解码(rawpy) | ⏳ 未做 |
| Background job(200+ 张异步) | ⏳ 未做 |

## 复用 template 的哪些

**直接用**:
- 认证 (JWT) / 上传管线 / DB schema
- Canvas 结构 / theme / share 页(改成对比 3 候选)
- SSE agent orchestrator(重跑不同参数的 stack 用它推进度)

**改动**:
- Canvas grid 需 virtualized scroll(300 张缩略图)
- share 页 hero 是"合成结果 + N 张原片对比"
- Landing 页文案换"星空堆栈"

## 下一步(from PoC → 真产品)

按 [SPEC_B_STARGAZER.md](../../docs/SPEC_B_STARGAZER.md) §5 时间估:
- 周 1: frame-triage 加检测器
- 周 2: stack-critic 打分节点
- 周 3: Canvas 重做 + 3 候选对比
- 周 4: RAW 上传 + 大文件
- 周 5: 5 个真星空摄影师 beta

## fork 这个 example 你要改的

假设 `init_template.sh --apply` 后:
1. `packages/agents/{your_slug}_agents/nodes/business.py` — frame_triage/stacker/critic
2. `apps/api/traillens_api/services/stacker.py` — 换 phaseCorrelate 为 astroalign(SIFT + 旋转)
3. `apps/web/app/stack/[id]/page.tsx` — 3 候选并排对比 Canvas
