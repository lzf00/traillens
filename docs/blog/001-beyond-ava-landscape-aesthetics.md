---
title: "Beyond AVA: Why I'm Fine-Tuning Q-Align for Landscape Photography"
date: 2026-06-XX  # Sprint 3 末发布
author: liuzifei
tags: [ml, aesthetics, q-align, lora, multimodal, build-in-public]
crosspost:
  - medium.com
  - 知乎(中文版)
  - HuggingFace Blog
  - dev.to
---

> 这是 TrailLens build-in-public 系列第 1 篇。
> TL;DR: 主流图像美学评分模型对风光摄影系统性误判。我们用 Q-Align + 1000 张
> landscape 标注做 LoRA 微调,目标 overall PLCC 从 0.75 → > 0.78。
> 数据集 + 权重 + 训练代码全部开源。

---

## 1. 这个问题真的存在吗

我把同一组 200 张川西风光照,分别喂给:
- LAION-Aesthetics v2(CLIP-based)
- NIMA (CNN-based, 2018)
- Q-Align (MLLM-based, ICML 2024)

人工评分(我 + 1 位国家地理签约摄影师独立评)排序,与三个模型的排序算 Spearman:

|  | SRCC vs 人工 |
|---|---|
| LAION-Aesthetics | 0.42 |
| NIMA | 0.49 |
| Q-Align(zero-shot) | 0.71 |

差距比预期大。**Q-Align 已经是 zero-shot SOTA,但 0.71 离"能商用"差一截。**

更糟的是失败模式:
- **逆光剪影**(山脊+夕阳),Q-Align 给 4.2,人工 8.5(被判"曝光问题")
- **极简留白**(三分之二空旷天空 + 远山),Q-Align 给 3.8,人工 8.0(被判"内容空泛")
- **长曝光水流**(单色冷调,无锐边),Q-Align 给 4.5,人工 7.8(被判"对焦/色彩偏差")

这三类正是风光摄影**最被赞许**的语言。

## 2. 为什么会这样

主流美学数据集的样本分布:

| Dataset | 风光占比 | 主要内容 |
|---|---|---|
| AVA(25 万) | < 10% | 婚礼 / 人像 / 微距 / 美食 |
| PARA(3.1 万) | < 15% | 同上 |
| TAD66K | ~20% | 较平衡 |
| **ArtiMuse-10K**(CVPR 2026 新发) | **~30% + 独立 Photography 子类** | 这是机会 |

Q-Align 用 ArtiMuse-10K 训过,但 Photography 子类是混合的(街拍 / 人像 / 风光 / 商业)。风光语言被淹没了。

## 3. 我们的实验设计

三个可证伪的假设:

**H1** 用 ArtiMuse Photography + 自标 1000 张 landscape 做 LoRA → landscape 测试集 PLCC 显著提升。
**H2** 把 EXIF(focal/aperture/iso/time)作为 prompt 辅助 token → technical 维度 PLCC 进一步提升。
**H3** 用户标 50 张 → 个人 PIAA LoRA → 该用户测试集 PLCC 比全局模型再高 > 10%。

代码:[`packages/aesthetic/train_qalign_lora.py`](../../packages/aesthetic/train_qalign_lora.py),三个 hypothesis 由 CLI flag 切换:

```bash
python train_qalign_lora.py train               # H1 baseline
python train_qalign_lora.py train --use-exif    # H1+H2
python train_qalign_lora.py train --piaa-user alice  # H3
```

## 4. 数据怎么标

是的,我得自己标。但我让 GPT-5V 先打 8 维分,人工只需要"校准",每张 30 秒:

[截图:annotation tool 的 UI]

工具开源在 [`packages/annotation/`](../../packages/annotation/) — 启 server、放图、按 1-9 打分。
标完 1000 张大约 8 小时。

招募了 2 位摄影爱好者协标,每人 200 张,换 6 个月 Pro 兑换。
一致性指标(Krippendorff's α)将公开在 [`docs/RESEARCH.md`](../RESEARCH.md)。

## 5. 接下来 4 周

| Week | 目标 |
|---|---|
| 1 | 完成 1000 张标注 |
| 2 | 验证 pipeline(300 张小批量,Modal A10G 跑通) |
| 3 | A100 上正式训(H1 + H2) |
| 4 | 评估 + HF Space + 发本文 |

如果 PLCC > 0.78:开放 API,$0.02 / call。
如果 < 0.78:降级为"Q-Align + 摄影规则" hybrid,继续往后做主产品。
无论哪种,**指标 + 权重 + 训练代码无条件开源**。

## 6. 你能帮我什么

- ⭐ Star [github.com/your-handle/traillens](https://github.com/your-handle/traillens)
- 📸 报名标注(私信我 "TrailLens")
- 🐛 PR / issue / 数据质疑 都欢迎
- 💬 在评论区分享你心目中"被低估"的风光作品

---

## 引用

```bibtex
@inproceedings{wu2024qalign, ... }
@inproceedings{artimuse2026, ... }
```

下一篇预告:**"Why I built 5 MCP servers before the product itself"** —— TrailLens
为什么把所有外部能力都封装为可独立分发的 MCP server。
