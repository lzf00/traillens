# Direction B Spec — TrailLens → Stargazer

> 把 TrailLens 收窄到**一个真痛点**:**星空照片自动堆栈 + AI 评估**。
> 重用现有 80% 代码,product surface 重做。

## 1. 真痛点(为什么是这个不是别的)

星空摄影师的工作流:
1. 出门拍 60-300 张曝光(降低单张 ISO 噪点,后期堆栈合成)
2. 回家用 **Sequator / Starry Landscape Stacker / DeepSkyStacker** 对齐 + 平均
3. 选堆栈最干净的那张 → Lightroom 调
4. 想试不同子集(用 100 张 vs 200 张?用前 50 vs 后 50?)→ **每次重跑堆栈 10-30 分钟**

痛点排序:
- **(A) 等待时间**:堆栈本身慢,试不同子集要等好几轮
- **(B) 选片**:300 张曝光哪些有云遮 / 飞机轨迹 / 抖动,**肉眼挑 30 分钟**
- **(C) 评估**:堆完不知道好坏,要拉到 Photoshop 100% 才看得出

跟当前 TrailLens 的关系:**(B) + (C) 正是 culling + critic 的核心能力**。
TrailLens 的"AI 选片 + 评分" 在风光场景下用户不需要(他们自己挑),
**但在 300 张星空 long exposure 里挑 - AI 真的比人快**。

## 2. 用户路径(MVP)

1. `/stack/new` 上传 50-300 张 RAW/JPG(都是同一机位长曝)
2. 后端**先 AI 过滤**(EXIF blur + 云 ratio + 飞机检测)→ 给出"建议丢 30 张"
3. 用户 reject 那 30 张 / keep 270 张
4. 后端**真跑堆栈**(OpenCV align + mean/median 合成) → 输出 1 张
5. 同时跑**另两个对照堆栈**(只用前 1/2 / 只用 keep+verdict=excellent)→ 用户对比哪个最干净
6. Critic 节点对最终堆栈打分(信噪比 + 星轨弯曲度 + 整体)

跟 TrailLens 闭环对比:
| 步 | TrailLens | Stargazer |
|---|---|---|
| 上传 | ✅ 复用 | ✅ 复用,加 batch ≥50 张优化 |
| culling | ✅ 复用 | 改:加 cloud_ratio / plane_streak 检测 |
| critic | ✅ 复用 prompt | 改:针对堆栈结果(SNR / 星点圆度) |
| story | ❌ 删 | — |
| planner | ❌ 删 | — |
| **stack** | ❌ 新加 | OpenCV align + median (核心新功能) |

## 3. 复用清单

**直接复用**:
- 部署架构(Tencent CVM + docker compose + nginx)
- 认证 (sign-up/in/JWT)
- 上传管线 (multipart + COS + Pillow EXIF + 缩略图)
- DB schema (trails + photos + critique + embedding)
- agent orchestrator (SSE 流式 + 持久化)
- Library 语义搜索(对堆栈成品搜索"低噪银河 / 蓝时刻"等)
- 公开 demo + 分享页 + Settings + theme

**改造**:
- Canvas 重做:300 张缩略图要 virtualized scroll
- culling 节点加 stargazer-specific 检测器
- 加 stack 节点(OpenCV align + median)

**新增**:
- `services/stacker.py` 真堆栈算法
- `/v1/trails/{id}/stack` 端点(SSE 实时进度)
- `apps/web/app/stack/[id]/` Canvas 变种(对比 3 个候选堆栈)

## 4. 技术挑战

| 挑战 | 解 |
|---|---|
| 300 张 RAW 上传带宽 | 客户端 thumbnail + 选 keep 后只传 keep 的 full res |
| OpenCV align 耗时(1 张 4-8 秒)| 后台 worker(Celery / FastAPI BackgroundTasks) |
| 内存(300 张 24MP 拼一起 ~50GB) | 增量 streaming median(Welford-like) |
| RAW 解码 | rawpy(libraw 绑定),CPU 重 |

## 5. 时间估算

- 周 1:culling 检测器 (cloud ratio / plane streak)
- 周 2:stack 节点 + 后端端点 + SSE 进度
- 周 3:前端 Canvas 重做(300 张 grid + 3 候选对比)
- 周 4:RAW 上传 / 大文件 / 错误恢复
- 周 5:beta 5 个真星空摄影师反馈

## 6. 怎么验证假设

发广告到**摄影 / 天文** 微信群 / 即刻:
> "在做一个工具:300 张星空曝光丢进去,AI 帮你挑 + 自动堆栈 +
> 给 3 个对照版本对比。要 5 个真用过 Sequator 的人 beta 试用,免费 + 反馈换早鸟价。"

预设 KPI:5 个 beta 至少 3 个说"比 Sequator 工作流舒服" → 继续投。

## 7. 不做这个的理由

- **市场窄**:中国星空摄影师可能 < 5000 活跃
- **付费意愿低**:他们用 Sequator(免费)+ Photoshop(已订阅)
- **竞品强**:Sequator 单机版本已经够用,云端工具迁移成本

## 8. 做这个的理由

- **真痛点**:等堆栈跑完 = 真痛
- **AI 真有优势**:VLM 看一眼就知道有没有云 / 飞机,人扫 300 张要 30 分钟
- **TrailLens 80% 复用率**:工程量不大
- **小众但深**:更容易出圈被业内人推
