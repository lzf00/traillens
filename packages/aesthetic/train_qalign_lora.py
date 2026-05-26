"""风光摄影美学评分模型微调 —— 实验脚本骨架。

定位
----
这是 TrailLens 的"算法研究核心"。目标:在 Q-Align 基础上,用 LoRA 微调出
一个 *风光摄影专用* 的美学评分模型,输出对齐 packages/agents 里的 AestheticScore
8 维 schema(overall + 7 个细分维度)。

为什么这是真问题(研究价值)
---------------------------
主流美学数据集(AVA / PARA)样本偏人像、生活照、婚礼,landscape 占比低且标注
标准不一致。直接用通用美学模型给风光照打分,会出现"偏色/逆光/极简留白被低估"
等系统性偏差。我们的贡献假设:
  H1: 用 ArtiMuse-10K 的 Photography 子集 + 自标 landscape 子集做领域适配,
      在 landscape 测试集上 PLCC/SRCC 显著优于 zero-shot Q-Align。
  H2: 把 EXIF(焦距/光圈/ISO/时间)作为辅助 token 注入,能进一步提升技术维度评分。
  H3: 用户少量标注(20-50 张)做 PIAA LoRA,可个性化对齐"个人风格"。

本文件是 *实验骨架*,不可直接训练(需真实数据 + GPU + 依赖)。
每个 [TODO] 标出需要补全的真实实现。
依赖(真实运行时): torch, transformers, peft, datasets, scipy, pillow
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path


# =========================================================================== #
# 0. 实验配置(集中管理,便于 sweep / 复现)
# =========================================================================== #
@dataclass
class ExperimentConfig:
    # --- 数据 ---
    base_model: str = "q-future/one-align"  # Q-Align 官方权重(HF)
    train_manifest: str = "data/landscape_train.jsonl"
    val_manifest: str = "data/landscape_val.jsonl"
    test_manifest: str = "data/landscape_test.jsonl"
    image_root: str = "data/images"

    # --- LoRA 超参(领域适配的关键旋钮)---
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    # 只训练注意力投影 + 视觉-语言连接层,冻结主干(成本/显存友好)
    target_modules: tuple[str, ...] = ("q_proj", "k_proj", "v_proj", "o_proj")

    # --- 训练 ---
    epochs: int = 3
    batch_size: int = 4
    grad_accum: int = 4  # 有效 batch=16
    lr: float = 1e-4
    warmup_ratio: float = 0.03
    bf16: bool = True
    max_image_tokens: int = 1280

    # --- 消融开关(对应 H1/H2/H3)---
    use_exif_tokens: bool = False  # H2:是否注入 EXIF 辅助 token
    piaa_user_id: str | None = None  # H3:若指定,加载该用户偏好做个性化 LoRA

    # --- 评估 ---
    # 8 维 schema,必须与 AestheticScore 完全对齐(接口契约!)
    score_dims: tuple[str, ...] = (
        "overall", "composition", "visual_elements", "technical",
        "originality", "theme", "emotion", "gestalt",
    )
    output_dir: str = "runs/qalign-landscape-lora-v0"


# =========================================================================== #
# 1. 数据 manifest 规范(自标注流程的产物)
# =========================================================================== #
#
# 每行一条 JSON(jsonl),字段:
# {
#   "image": "img_0001.jpg",
#   "scores": {"overall": 7.2, "composition": 8.0, ... 8 维},
#   "exif": {"focal_length_mm": 24, "aperture_f": 8.0, "iso": 100, ...},
#   "source": "artimuse10k" | "self_annotated" | "unsplash_landscape",
#   "annotator": "expert_01" | "self" | "gpt5_assisted",
# }
#
# 自标注 SOP(路线图 M1 Week3):
#   1) 从 ArtiMuse-10K 取 Photography 子集 + 自爬 500px/Unsplash landscape。
#   2) 单人标注易漂移 -> 采用 "GPT-5V 预打分 -> 人工校准 -> 双周重标 50 张测一致性"。
#   3) 记录标注者间一致性(Krippendorff's alpha),alpha<0.6 的维度要重新定义 rubric。
#      *** 这一步的数据来源/流程必须写进 docs/RESEARCH.md,回应"算法凝视"偏见批评 ***
# --------------------------------------------------------------------------- #


def load_manifest(path: str) -> list[dict]:
    """读取 jsonl manifest。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"未找到 {path}。请先按 SOP 产出标注数据(见本文件头部 manifest 规范)。"
        )
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


# =========================================================================== #
# 2. 模型与 LoRA 装配
# =========================================================================== #
def build_model(cfg: ExperimentConfig):
    """加载 Q-Align 主干并挂 LoRA。

    [TODO] 真实实现:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import LoraConfig, get_peft_model
        model = AutoModelForCausalLM.from_pretrained(
            cfg.base_model, torch_dtype=torch.bfloat16, trust_remote_code=True
        )
        lora = LoraConfig(
            r=cfg.lora_r, lora_alpha=cfg.lora_alpha, lora_dropout=cfg.lora_dropout,
            target_modules=list(cfg.target_modules), task_type="CAUSAL_LM",
        )
        return get_peft_model(model, lora)

    Q-Align 把美学评分建模为"在 [excellent/good/fair/poor/bad] 5 个 token 上的
    加权期望",而非直接回归一个标量。微调时沿用其 token-level 监督,
    再把 5 级映射到 0-10 连续分。这是它比 NIMA 类回归模型更鲁棒的原因。
    """
    raise NotImplementedError("[TODO] 装配 Q-Align + LoRA(需 GPU 与依赖)")


def encode_exif_as_text(exif: dict) -> str:
    """H2:把 EXIF 转成可注入 prompt 的自然语言片段。

    例: "Shot at 24mm, f/8, ISO 100, 1/125s, golden hour."
    研究问题:这种软注入 vs 把 EXIF 做成独立 embedding 拼接,哪种更有效?
    -> 作为消融实验的一个 arm。
    """
    parts = []
    if exif.get("focal_length_mm"):
        parts.append(f"{exif['focal_length_mm']}mm")
    if exif.get("aperture_f"):
        parts.append(f"f/{exif['aperture_f']}")
    if exif.get("iso"):
        parts.append(f"ISO {exif['iso']}")
    return "Shot at " + ", ".join(parts) + "." if parts else ""


# =========================================================================== #
# 3. 训练循环(骨架)
# =========================================================================== #
def train(cfg: ExperimentConfig) -> None:
    train_data = load_manifest(cfg.train_manifest)
    val_data = load_manifest(cfg.val_manifest)
    print(f"[train] {len(train_data)} 训练样本 / {len(val_data)} 验证样本")
    print(f"[train] 消融配置: use_exif={cfg.use_exif_tokens} piaa={cfg.piaa_user_id}")

    # [TODO] model = build_model(cfg)
    # [TODO] 构造 DataLoader:图像 -> processor;scores -> token-level 监督标签
    # [TODO] 标准 HF Trainer 或自写循环;每 epoch 末在 val 上算 PLCC/SRCC 早停
    # [TODO] 保存 LoRA adapter 到 cfg.output_dir
    raise NotImplementedError("[TODO] 实现训练循环")


# =========================================================================== #
# 4. 评估(作品集硬通货:可复现的指标表)
# =========================================================================== #
def pearson_spearman(pred: list[float], gold: list[float]) -> tuple[float, float]:
    """PLCC(线性相关)+ SRCC(秩相关),IAA 领域标准指标。

    纯 Python 实现,无 scipy 依赖,保证评估脚本零依赖可跑。
    """
    n = len(pred)
    if n < 2:
        return 0.0, 0.0

    def _pearson(a, b):
        ma, mb = sum(a) / n, sum(b) / n
        cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        va = sum((x - ma) ** 2 for x in a) ** 0.5
        vb = sum((y - mb) ** 2 for y in b) ** 0.5
        return cov / (va * vb) if va and vb else 0.0

    def _rank(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        ranks = [0.0] * len(xs)
        for r, i in enumerate(order):
            ranks[i] = r
        return ranks

    plcc = _pearson(pred, gold)
    srcc = _pearson(_rank(pred), _rank(gold))
    return round(plcc, 4), round(srcc, 4)


def evaluate(cfg: ExperimentConfig, model=None) -> dict:
    """在 test 集上对每个维度算 PLCC/SRCC。

    返回的 dict 直接写进 docs/EVAL.md 的指标表。
    目标(路线图 M2 的 go/no-go 触发器):overall 维度 PLCC > 0.78。
    """
    test_data = load_manifest(cfg.test_manifest)
    results = {}
    for dim in cfg.score_dims:
        gold = [d["scores"][dim] for d in test_data if dim in d.get("scores", {})]
        # [TODO] pred = [model.score(img)[dim] for ...];此处用占位
        pred = list(gold)  # 占位:真实实现替换为模型预测
        plcc, srcc = pearson_spearman(pred, gold)
        results[dim] = {"PLCC": plcc, "SRCC": srcc, "n": len(gold)}
    return results


# =========================================================================== #
# 5. 推理服务接口(与第一块 agent 的接口契约)
# =========================================================================== #
def score_image(image_path: str, model=None, cfg: ExperimentConfig | None = None) -> dict:
    """单图推理 -> 返回与 AestheticScore 完全对齐的 dict。

    *** 这是与 packages/agents/.../tools/clients.py::score_aesthetics 的契约 ***
    部署为 Modal/FastAPI endpoint 后,agent 端 httpx.post 即可消费。

    [TODO] 真实实现:
        image = Image.open(image_path)
        out = model.score(image)  # Q-Align token 期望 -> 0-10
        return {
            "overall": out["overall"], "composition": out["composition"], ...,
            "confidence": out["confidence"],
            "model_version": cfg.output_dir.split("/")[-1],
        }
    """
    raise NotImplementedError("[TODO] 实现推理,返回 8 维 + confidence + model_version")


# =========================================================================== #
# CLI
# =========================================================================== #
def main() -> None:
    parser = argparse.ArgumentParser(description="风光摄影美学评分 LoRA 微调")
    parser.add_argument("cmd", choices=["train", "eval", "demo-metric"])
    parser.add_argument("--use-exif", action="store_true", help="H2 消融:注入 EXIF token")
    parser.add_argument("--piaa-user", default=None, help="H3:个性化用户 id")
    args = parser.parse_args()

    cfg = ExperimentConfig(use_exif_tokens=args.use_exif, piaa_user_id=args.piaa_user)

    if args.cmd == "train":
        train(cfg)
    elif args.cmd == "eval":
        print(json.dumps(evaluate(cfg), ensure_ascii=False, indent=2))
    elif args.cmd == "demo-metric":
        # 无需数据/GPU,演示评估指标实现本身是对的
        pred = [7.2, 5.0, 8.1, 6.3, 4.5, 9.0, 6.8]
        gold = [7.0, 5.5, 7.9, 6.0, 5.0, 8.7, 6.5]
        plcc, srcc = pearson_spearman(pred, gold)
        print(f"demo PLCC={plcc}  SRCC={srcc}")


if __name__ == "__main__":
    main()
