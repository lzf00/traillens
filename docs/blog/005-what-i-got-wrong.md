# 我在 TrailLens 上想错的 7 件事

> Build-in-public 周记 #5。诚实复盘。
> 一个核心信念:**不愿承认假设错的项目,会一直把工程量花在错地方**。

## 1. "摄影师需要 AI 帮他选片" — 大概率不真

这是项目的**第一性假设**。但我跟 3 个真摄影师朋友聊完后:

- "我用 Lightroom 五星打分,30 秒搞定 100 张,AI 比我慢"
- "AI 给我的'综合分 8.4'毫无意义,我只关心**这张能不能发**"
- "电脑选好的最后我还得自己再过一遍 — 那不如一开始就自己过"

**摄影师的肌肉记忆 + 自我审美 > 任何 AI 评分**。我建的"AI darkroom"在解决一个**他们不觉得是问题的问题**。

真问题可能是:**"帮我从 200 张几乎一样的相似机位里选 1 张最棒的"** — 这是个真累人的活,AI 能赢肌肉记忆。但 TrailLens 当前没专做这个。

## 2. "八维评分"是学术框架,不是用户语言

PRODUCT_PLAN 里写了"overall / composition / visual_elements / technical / originality / theme / emotion / gestalt"。**Q-Align 论文的标准**。

实际用户拿到八维分:
- 不知道 6.4 的"原创性"低了具体哪里
- 不知道怎么改下次能涨
- 比起雷达图,更想看**一句话"这张为什么这么打"**

我做了 AI 点评(critique)解决这个,但 critique 的内容其实就是雷达图的解释 — **可以扔掉雷达图,只留 critique**。

## 3. LangGraph 不该是叙事重点

我花了相当时间打磨 LangGraph 集成 + SSE 流式 + on_chain_end 多态 unwrap。这些是**工程师之间互相 show off** 的东西。

真用户看到的是:点 Run → 等 90 秒 → 看结果。中间的 12 个 SSE 事件**他不在乎**。
build-in-public 圈子里 LangGraph 加分,但**对终端用户 = 零价值**。

如果重做:可能直接同步跑 + 进度条,代码少 60%。LangGraph 留在简历上写。

## 4. 公开 demo 用 Pexels 图是错的

第一版 demo trail 上传了 8 张 Pexels 风光图。AI 跑分出来,游记全是 "Nonemm f/None ISONone" 因为 Pexels 剥 EXIF。

后来 SQL 注入合理 mock EXIF 让它"看起来真"。但**这违反了"build in public"的精神** — 演示用假数据是另一种 vanity。

真要做 demo,应该上**自己的真徒步原片**(就算只有 5 张)。这是 TrailLens 的**作品**,不是它的**功能展示**。

## 5. Library 语义搜索是 over-engineering

我接通了豆包 embedding + pgvector。中文 "雪山日落" 真能搜到对的 critique。
但**用户上传 100 张照片的频率 < 1 次/年**。Library 的价值线性正比于:
> (你跑过 trail 的次数) × (你忘了哪张照片在哪个 trail 的概率)

对 95% 用户这个乘积 ≈ 0。当前 Library 更像是技术展示而非真需求。

## 6. Theme toggle 是体面型工程,不是功能

dark/light/auto 切换三态、防 FOUC inline script。**实现的时间** > 它给用户带来的价值。
但 — Hacker News 评论"这个 dark theme 不错"会比"功能复杂"更出圈。所以**体面型工程对 build-in-public 反而合理**,只是不能假装它解决问题。

## 7. 我以为自己在做产品,实际在做"作品集"

最大的认知错位。
真做产品:第 1 天就找 5 个用户、定 1 个 KPI(注册转化率 / DAU / 留存)、所有功能砍到只为这个 KPI 服务。
我做的是:**每个我觉得"该有"的功能都加** — 因为它能放进作品集,而不是因为有用户要。

承认这个之后,反而轻松了。**TrailLens 的产品名应该叫 "TrailLens-portfolio"**,目标是工程能力展示,而不是 product-market fit。

---

## 接下来怎么办

短期不强求转产品,**先把作品集做到最强**:
1. README 加 30 秒视频 demo
2. 几篇技术深度文章(LangGraph 集成、pgvector + 豆包 embedding、Next 15 踩坑) → 投 HN / Twitter / 即刻
3. 整理一份 case study(架构 + 决策 + 失败) 放 portfolio 站
4. 投相关公司(全栈 AI / 多模态 / agent 框架方向)

如果几周后还想继续做产品,**重新选问题** — 可能是"星空堆栈自动评估"或别的更窄的真痛点。

## 给同样在 build-in-public 的朋友的话

- 写**承认错误的文章**比写新功能 demo 转发率高
- "我曾以为 X,后来发现 Y" 比 "我做了 Z" 更有人读
- 工程过度漂亮往往是**绕开做用研**的借口

下一篇:**TrailLens 架构 case study(写给招聘 reviewer 看的)**。
