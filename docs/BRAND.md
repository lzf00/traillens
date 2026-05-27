# TrailLens 品牌规范

> 2026-05-26 锁定。任何品牌相关变更先改这里,再同步代码。

## 名字

**TrailLens** — 一个英文单词的视觉化合成:`Trail`(徒步路径)+ `Lens`(镜头)。
中文叙述时直接用 "TrailLens",不强行翻译。
项目化叙事:"AI darkroom for landscape photographers who hike."

## 命名规范

| 形式 | 写法 | 用法 |
|---|---|---|
| 品牌全称 | TrailLens | landing / 演示 / 文章正文 |
| 小写技术名 | traillens | 包名 / npm / pypi / GitHub repo |
| URL / 邮件 | traillens.zorotreeking.online / hello@zorotreeking.online | 域名 |
| MCP server | traillens-{exif,sunmoon,weather,...} | 标识 family |
| 模型权重 | qalign-landscape-lora-{version} | HF model id |

## Logo 概念(待设计师做)

文字 logo 优先。建议方案:
- 字体:Fraunces 600(serif,呼应"darkroom"的胶片质感)
- 大写 T 与 L 都做小型衬线,中间 `rail` `ens` 小写
- 配 1 个山脊线 + 镜头光圈合体的 mark(单色 #6FBF8B)

如何快速搞出 v0(本周):
```bash
# 用 v0.dev 或 Bing Image Creator 生成几版 → 选 1 个矢量化(Recraft.ai)
# → SVG 放到 apps/web/public/logo.svg
```

## 视觉系统(强制)

见 [PRODUCT_PLAN §2.2](PRODUCT_PLAN.md#22-视觉系统直接定下来避免每个页面重新设计) 与 [apps/web/tailwind.config.ts](../apps/web/tailwind.config.ts)——这两份是唯一权威,不要再开第三份色卡。

## 口径(message 一致性)

| 场景 | 一句话定位 |
|---|---|
| 一句话(< 80 字) | The AI darkroom for landscape photographers who hike. |
| 一段话(landing) | 把一整次徒步的素材丢进去 — AI 自动选片、点评、生成游记,并规划你下次的拍摄计划。 |
| 求职 portfolio | 多模态多智能体摄影助手,含一项自研开源风光美学评分模型(Q-Align + LoRA)、5 个 MCP server、完整全栈 + CI + eval。 |
| 投资 / BD(若需) | 摄影后期 SaaS + 美学评分 API,垂直差异化于 Aftershoot / Imagen / Photo AI。 |

**不要混用**:不在求职稿里讲 ARR 目标;不在 PH 文案里讲算法贡献。

## 商标 / 法务声明

- 模型权重 License:CC BY-NC 4.0(非商用 / 学术 OK / 商用须谈)
- 代码 License:MIT(吸引 OSS 贡献)
- TrailLens 商标:**未注册**(2026-05-26 状态)。优先级见 [DOMAINS.md](DOMAINS.md) 末尾。

## 不要做

- ❌ 不在产品名加 "AI" 字样("TrailLens AI" 听起来像被迫贴标签)
- ❌ 不在 logo 用渐变(每个 AI 公司都在用,审美疲劳)
- ❌ 不出现 emoji 在主导航 / 标题(只在 changelog / 推文里出现)
- ❌ 不用 "革命性 / 颠覆性 / Powered by GPT" 这类自夸话术
