---
title: "为什么我要给 Q-Align 做风光摄影微调 —— TrailLens 项目笔记 #1"
date: 2026-06-XX  # 与英文版同步发
author: liuzifei
tags: [机器学习, 图像质量评估, 多模态大模型, LoRA, 风光摄影, build-in-public]
crosspost:
  - 知乎(本文)
  - 即刻(精简版)
  - 小红书(更视觉化版本)
target: 2000-3000 字
---

> 这是我做的 TrailLens 项目的第 1 篇技术笔记。
> 一句话:主流图像美学评分模型对风光摄影系统性误判。
> 我在用 Q-Align 加 1000 张 landscape 自标数据做 LoRA 微调,目标把 overall PLCC 从 0.75 拉到 0.78 以上。
> 数据集、权重、训练代码会全部开源。

---

## 一、先说我看到的问题

我把同一组川西风光的 200 张照片,分别喂给三个开源 / 公开的图像美学评分模型:

|  | 与人工评分的 Spearman 等级相关 |
|---|---|
| LAION-Aesthetics v2(CLIP-based) | 0.42 |
| NIMA(CNN, 2018) | 0.49 |
| Q-Align(MLLM-based, ICML 2024) | 0.71 |

(人工评分:我 + 一位国家地理签约摄影师独立打分,8 维平均)

差距比我预想的大,但更让我警觉的是 **失败模式**。
具体几个典型例子(都是被三个模型同时误判的):

- **逆光剪影**(山脊在落日下的剪影):Q-Align 给 4.2 / 10,人工 8.5 → 模型判定"曝光问题"
- **极简留白**(三分之二空旷天空 + 远处一线山):Q-Align 给 3.8,人工 8.0 → 模型判定"内容空泛"
- **长曝光水流**(单色冷调,无锐边):Q-Align 给 4.5,人工 7.8 → 模型判定"对焦/色彩偏差"

这三类正是风光摄影里**最被赞许**的视觉语言。模型不是"打错分",而是**完全不懂这种摄影语言**。

## 二、为什么会这样

翻了下主流美学数据集的样本分布:

| 数据集 | 风光占比 | 主要内容 |
|---|---|---|
| AVA(25 万张) | < 10% | 婚礼 / 人像 / 微距 / 美食 |
| PARA(3.1 万) | < 15% | 同上 |
| TAD66K | ~20% | 较平衡 |
| ArtiMuse-10K(CVPR 2026 新发) | ~30% + 独立 Photography 子类 | **这是我们的机会** |

模型不是不智能,是没看过足够多的风光照片。而它们看过的"摄影"样本里,
风光的语言被人像 / 街拍 / 商业广告淹没了。

## 三、我的实验设计

把项目挑战拆成 3 个**可证伪**的假设:

**H1** — 用 ArtiMuse Photography 子集 + 我自标的 1000 张风光照,做 Q-Align 的 LoRA 微调,landscape 测试集的 PLCC 会显著超越 zero-shot Q-Align。

**H2** — 把 EXIF(焦距 / 光圈 / ISO / 拍摄时间)作为 prompt 的辅助 token 注入,technical 维度的评分会进一步提升。直觉:技术执行评估天然需要拍摄参数上下文。

**H3** — 让单用户标 50 张照片做个人 PIAA(Personalized Image Aesthetics Assessment)LoRA,该用户的个人测试集 PLCC 会比全局模型再高 > 10%。

代码在 [`packages/aesthetic/train_qalign_lora.py`](https://github.com/lzf00/traillens/blob/main/packages/aesthetic/train_qalign_lora.py),三个假设由 CLI flag 切换:

```bash
python train_qalign_lora.py train                # H1 baseline
python train_qalign_lora.py train --use-exif     # H1 + H2
python train_qalign_lora.py train --piaa-user alice  # H3
```

## 四、数据怎么标

是的,只能自己标。但我让 GPT-5V(或 Claude Opus 4.7,谁便宜用谁)先预打分,
我只需要在每张照片上做"校准",平均每张 30 秒。

工具我开源在 [`packages/annotation/`](https://github.com/lzf00/traillens/tree/main/packages/annotation),
是个用 Python 标准库写的 80 行 HTTP server + 单文件 HTML 界面,
完全本地运行,不上传任何数据:

[标注工具截图(占位)]

我招募了 2 位摄影爱好者一起标,每人 200 张,换 6 个月 Pro 兑换码。
标注者之间的一致性用 Krippendorff α 衡量,α<0.6 的维度会重写 rubric。

## 五、为什么不直接调 GPT-5V API

我考虑过。但有三个原因不行:

1. **成本**:1000 张 × 8 维详细评分,GPT-5V 跑一次 ≈ $40。
   摄影师付费意愿是 19 美元/月,API 成本要远低于这个数才行得通。
2. **延迟**:一次徒步可能 200-500 张照片。云端串行 8-15 分钟,本地推理可以 1-2 分钟。
3. **可控**:我希望产出**可解释的 8 维评分**而非黑盒数字。Q-Align 的 5-level token
   分布(excellent/good/fair/poor/bad)是有研究 grounding 的离散监督信号,
   不是简单回归一个数。

## 六、接下来 4 周路线图

| 周次 | 目标 | Go/No-Go |
|---|---|---|
| W1 | 完成 1000 张标注 + 算 Krippendorff α | α > 0.6 |
| W2 | 验证 pipeline:300 张小批量 + Modal A10G 跑通 | 训练能收敛 |
| W3 | A100 上正式训(H1 + H2 各一组) | overall PLCC > 0.78 |
| W4 | 评估 + HF Space + 发本文英文版 | — |

如果 PLCC 没达标,就退到"Q-Align + 摄影规则系统"hybrid 方案。
但无论结果如何,**指标 + 权重 + 训练代码全部开源**。

## 七、你能怎么帮

这是个 build-in-public 项目,完全开放:

- ⭐ Star [github.com/lzf00/traillens](https://github.com/lzf00/traillens)
- 📸 报名一起标注(私信我"TrailLens")
- 🐛 数据 / 算法 / 工程任何 PR / issue 都欢迎
- 💬 在评论区分享你心目中"被低估"的风光作品 —— 我会都用模型跑一遍,
  看看 zero-shot 哪些误判最严重

下一篇预告:**为什么我先做了 5 个 MCP server,再做产品本身** ——
关于 MCP 协议如何成为 TrailLens 的隐藏分发渠道。

---

## 附录:关键文献

```bibtex
@inproceedings{wu2024qalign,
  title={Q-Align: Teaching LMMs for Visual Scoring via Discrete Text-Defined Levels},
  author={Wu, Haoning and others},
  booktitle={ICML 2024}
}
@inproceedings{artimuse2026,
  title={ArtiMuse: Towards Fine-Grained Aesthetic Evaluation},
  booktitle={CVPR 2026}
}
@inproceedings{aesexpert2024,
  title={AesExpert: Towards Expert-Level Multimodal Aesthetic Critique},
  booktitle={ACM MM 2024}
}
```
