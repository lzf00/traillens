# 风光摄影美学评分 — 研究笔记

> 这份文档面向 ML reviewer / 招聘方 / 学术合作者。
> 目标:任何人读完都能(a) 复现实验;(b) 理解我们做了哪些选择;(c) 知道局限在哪。

---

## 1. 问题

**主流美学评分模型对风光摄影系统性误判**。

具体表现:
- AVA / PARA 等数据集偏婚礼/人像/生活照,风光占比 < 10%,标注 rubric 不强调风光特有维度(留白、引导线、地平线、天际线、前景平衡)。
- 用 NIMA / LAION-Aesthetics / Q-Align(zero-shot)给风光照打分,系统性低估的样本类型:
  - 极简留白构图(被判"内容空泛")
  - 强烈逆光剪影(被判"曝光问题")
  - 单色冷调长曝水流(被判"色彩偏差")
- 风光摄影师社区的"好作品"分布,与通用美学分数的分布有显著差异(详细数据待 Sprint 2 末出基线后填入)。

---

## 2. 假设(消融实验的 arm)

| 假设 | 操作 | 验证方式 |
|---|---|---|
| H1 | 用 ArtiMuse-10K Photography + 自标 landscape 子集做领域 LoRA | landscape 测试集 PLCC > zero-shot Q-Align |
| H2 | 把 EXIF(焦距/光圈/ISO/拍摄时间)作为辅助 token 注入 prompt | technical 维度 PLCC 显著提升 |
| H3 | 用户标 20-50 张做 PIAA LoRA | 该用户的个人测试集 PLCC > 全局模型 |

H1/H2 在 [`packages/aesthetic/train_qalign_lora.py`](../packages/aesthetic/train_qalign_lora.py) 中由 `--use-exif` flag 控制开关;H3 由 `--piaa-user <id>` 触发。

---

## 3. 数据

### 3.1 来源与许可

| 数据集 | 数量 | 许可 | 我们的使用方式 |
|---|---|---|---|
| ArtiMuse-10K | 10K | CC BY-NC 4.0(待与作者确认) | 训练 + 主测试集 |
| 自爬 Unsplash Landscape | 1500 | Unsplash License(免费商用) | 训练增量 |
| 自爬 500px Landscape | 800 | 仅 metadata 抓取 + 缓存预览(不再分发原图) | 训练增量 |
| 个人作品 | 300 | 自有 | PIAA 验证集 |

### 3.2 标注 SOP(自标注流程,Sprint 1 末完成)

```
1) 从公开数据集抽样 500 张风光照(分层:山岳/海岸/草原/森林/沙漠/城市夜景)
2) GPT-5V 预打分(8 维 0-10)→ 得到 baseline 标签
3) 自校验 + 与 2 个摄影爱好者(待邀)独立标注 100 张子集
4) 算 Krippendorff's α 一致性;α<0.6 的维度重写 rubric
5) 全量 1000 张:GPT-5V 预打分 → 人工修正(自己 + 上面 2 位)
6) 公开标注协议 + rubric 卡片到本仓库 docs/RUBRIC.md
```

### 3.3 偏见声明(写在这里,也写在用户协议里)

**任何美学评分模型都带有训练数据的风格偏好**——LAION-Aesthetics 被批评为"算法凝视",我们的模型也不例外。
本模型定位为**个人风格助理**而非"客观评分":
- 默认风格偏 Outdoor Photographer / National Geographic 一类的传统风光美学。
- 不擅长后现代/实验性/AI-generated 风格的判断。
- PIAA(H3)是缓解 this 的关键机制:用户少量标注后,LoRA 适配个人审美。

---

## 4. 方法

### 4.1 模型

- 基座:[Q-Align](https://arxiv.org/abs/2312.17090) (ICML 2024)。理由:用"在 [excellent/good/fair/poor/bad] 5 个 token 上的加权期望"而非回归一个标量,比 NIMA/CLIP-aesthetic 更鲁棒。
- 适配:LoRA(r=16, alpha=32, dropout=0.05),target_modules = `q/k/v/o_proj`。
- 训练:HF Trainer + bf16 + grad_accum=4(有效 batch=16),3 epoch,lr=1e-4 + 3% warmup。
- 8 维输出:沿用 ArtiMuse 的细粒度 rubric(`overall, composition, visual_elements, technical, originality, theme, emotion, gestalt`)。

### 4.2 EXIF 注入(H2)

```python
def encode_exif_as_text(exif):
    # "Shot at 24mm, f/8, ISO 100, 1/125s, golden hour."
```

注入方式对比(消融):
- (a) 软注入:拼到 prompt 文本里
- (b) 硬注入:把 EXIF 编码为 special token 拼到 vision token 之后

预期:(b) 在 technical 维度提升更大,但参数量增加。

### 4.3 PIAA(H3)

用户在 web app 内标注 50 张(打分 + 短评)→ 后台触发个人 LoRA 增量训练(在全局模型 LoRA 之上叠加用户 LoRA)→ 部署为用户专属 endpoint。
增量训练每 50 张样本触发一次;Modal cron job 跑(每用户每周一次,1× A10G ~15 分钟)。

---

## 5. 结果(将在 Sprint 3 末填入)

见 [EVAL.md §1.3](EVAL.md#13-指标表每次-sprint-末更新)。

预期 vs 实际:
- H1: zero-shot Q-Align overall PLCC ≈ 0.75(论文报告值);本模型目标 > 0.78 → 提升 ≈ 4-6%
- H2: technical 维度提升 5-8%
- H3: 用户测试集提升 > 10%(if 用户标注 >= 50 张)

---

## 6. 局限与未来工作

1. **数据量受限**:自标注 1000 张 vs 通用美学数据集的 25 万张。会限制模型上限。下一步:开源后众包标注。
2. **8 维 rubric 是从 ArtiMuse 借的**,未必完全适合风光。可能需要扩出 "long-exposure / HDR / wide-angle distortion / atmospheric haze" 等风光专有维度——但加维度会破坏与 ArtiMuse 的可比性。tradeoff 留给社区讨论。
3. **缺少多文化美学样本**:东亚山水画式审美 vs 北美 grandiose 风格 vs 北欧极简,模型可能更偏后两者。
4. **PIAA 隐私**:用户标注样本上传到云端训练,虽然只用于该用户,但仍是 PII。提供本地训练选项(用户的 macOS GPU)是长期目标。

---

## 7. 引用

```bibtex
@inproceedings{wu2024qalign,
  title={Q-Align: Teaching LMMs for Visual Scoring via Discrete Text-Defined Levels},
  author={Wu, Haoning et al.},
  booktitle={ICML}, year={2024}
}
@inproceedings{artimuse2026,
  title={ArtiMuse: Towards Fine-Grained Aesthetic Evaluation},
  author={Zhang, et al.}, booktitle={CVPR}, year={2026}
}
@inproceedings{aesexpert2024,
  title={AesExpert: Towards Expert-Level Multimodal Aesthetic Critique},
  author={Huang, et al.}, booktitle={ACM MM}, year={2024}
}
```

---

## 8. 想合作?

- 摄影师:在 web app 里参与 PIAA 标注(每完成 50 张得 1 个月 Pro 免单)。
- 研究者:数据集 / 评估方法 / 偏见审计的 PR 我们 welcome。
- 投稿目标:CVPR / ECCV / ACM MM workshop。
