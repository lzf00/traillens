"""在 Modal 上跑 Q-Align landscape LoRA 训练。

部署:
    modal volume create traillens-models
    modal volume put traillens-models ./data /data
    modal run train_modal.py::run
    # → LoRA weights 写到 /models/qalign-landscape-lora-v0/

成本估算(2026 Modal 价格):
    A10G $0.65/hr × 4-8 hr = $3-5      (300 张样本验证 pipeline)
    A100-40GB $3.10/hr × 8-16 hr = $25-50  (1000 张正式训练)
    总 budget 建议 $50 起步。

预算上限:在 modal.App.function 装饰器加 max_duration_s 强制止损。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Modal 可选(本地无 modal 包也能 import 这个文件用于打印命令)
try:
    import modal
    HAS_MODAL = True
except ImportError:
    HAS_MODAL = False
    print("[train_modal] modal not installed; run `pip install modal` to deploy", file=sys.stderr)


if HAS_MODAL:
    image = (
        modal.Image.debian_slim(python_version="3.11")
        .pip_install(
            "torch==2.4.0",
            "transformers>=4.45,<5.0",
            "peft>=0.13",
            "accelerate>=0.34",
            "datasets>=2.20",
            "Pillow>=10",
            "scipy>=1.14",
            "bitsandbytes>=0.43",
            "wandb",
        )
        .apt_install("git")
    )

    app = modal.App("traillens-train")
    volume = modal.Volume.from_name("traillens-models", create_if_missing=True)
    data_volume = modal.Volume.from_name("traillens-data", create_if_missing=True)

    @app.function(
        image=image,
        gpu="A10G",                # 第一次跑用 A10G 验证;改 "A100" 上正式
        volumes={"/models": volume, "/data": data_volume},
        timeout=4 * 3600,          # 4 小时硬上限(止损)
        secrets=[modal.Secret.from_name("traillens-train", required_keys=["WANDB_API_KEY"])],
    )
    def run(use_exif: bool = False, lora_r: int = 16, epochs: int = 3, run_name: str = "v0"):
        """主训练函数。从 /data/landscape_*.jsonl 读数据,把 LoRA 写到 /models/。"""
        _train(use_exif=use_exif, lora_r=lora_r, epochs=epochs, run_name=run_name)
        volume.commit()
        print(f"→ checkpoint saved to /models/qalign-landscape-lora-{run_name}/")


# --------------------------------------------------------------------------- #
# 真实训练逻辑(独立于 modal,本地有 GPU 也可跑)
# --------------------------------------------------------------------------- #
def _train(*, use_exif: bool, lora_r: int, epochs: int, run_name: str):
    import json
    from PIL import Image as PILImage
    import torch
    from torch.utils.data import Dataset
    from transformers import (
        AutoModelForCausalLM, AutoProcessor, Trainer, TrainingArguments,
    )
    from peft import LoraConfig, get_peft_model

    DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data"))
    OUT_ROOT = Path(os.environ.get("OUT_ROOT", "/models"))
    OUT_DIR = OUT_ROOT / f"qalign-landscape-lora-{run_name}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- 1. Load data ----
    def load_jsonl(p):
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

    train = load_jsonl(DATA_ROOT / "landscape_train.jsonl")
    val = load_jsonl(DATA_ROOT / "landscape_val.jsonl")
    print(f"[data] train={len(train)} val={len(val)}")

    # ---- 2. Load Q-Align base ----
    base = "q-future/one-align"
    processor = AutoProcessor.from_pretrained(base, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        base, torch_dtype=torch.bfloat16, trust_remote_code=True, device_map="auto",
    )
    print(f"[model] loaded {base}")

    # ---- 3. Attach LoRA ----
    lora = LoraConfig(
        r=lora_r, lora_alpha=lora_r * 2, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM", bias="none",
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    # ---- 4. Build dataset ----
    class LandscapeDS(Dataset):
        def __init__(self, records, image_root):
            self.records = records
            self.image_root = Path(image_root)

        def __len__(self):
            return len(self.records)

        def __getitem__(self, i):
            r = self.records[i]
            img = PILImage.open(self.image_root / r["image"]).convert("RGB")
            exif_text = ""
            if use_exif and r.get("exif"):
                e = r["exif"]
                exif_text = (
                    f" Shot at {e.get('focal_length_mm', '?')}mm, "
                    f"f/{e.get('aperture_f', '?')}, ISO {e.get('iso', '?')}."
                )
            # Q-Align 监督信号:overall 0-10 → 5 个 level token 的目标分布
            prompt = f"Rate this landscape photograph aesthetically.{exif_text}"
            target = _level_label(r["scores"]["overall"])
            return {"image": img, "prompt": prompt, "target": target}

    train_ds = LandscapeDS(train, DATA_ROOT / "images")
    val_ds = LandscapeDS(val, DATA_ROOT / "images")

    # ---- 5. Train ----
    args = TrainingArguments(
        output_dir=str(OUT_DIR),
        num_train_epochs=epochs,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=1e-4,
        warmup_ratio=0.03,
        bf16=True,
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="epoch",
        report_to=["wandb"] if os.environ.get("WANDB_API_KEY") else [],
        run_name=f"qalign-landscape-{run_name}",
    )

    def collate(batch):
        return processor(
            images=[b["image"] for b in batch],
            text=[b["prompt"] for b in batch],
            return_tensors="pt", padding=True,
        ) | {"labels": _encode_targets(processor, [b["target"] for b in batch])}

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=collate,
    )
    trainer.train()
    model.save_pretrained(OUT_DIR)
    processor.save_pretrained(OUT_DIR)
    print(f"[done] saved to {OUT_DIR}")


# Q-Align 的 5-level token 映射(论文 §3.2)
LEVELS = ["bad", "poor", "fair", "good", "excellent"]


def _level_label(overall: float) -> str:
    """0-10 连续分 → 5 个离散 level。"""
    idx = min(4, max(0, int(overall // 2)))
    return LEVELS[idx]


def _encode_targets(processor, targets):
    """把 level 单词序列化为 token id。"""
    import torch
    enc = processor.tokenizer(targets, return_tensors="pt", padding=True)
    return enc["input_ids"]


# --------------------------------------------------------------------------- #
# CLI(本地无 modal 时打印命令清单,有 modal 时直接走 `modal run`)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    if not HAS_MODAL:
        print("用法:")
        print("  1) pip install modal && modal token new")
        print("  2) modal volume create traillens-models")
        print("  3) modal volume create traillens-data")
        print("  4) modal volume put traillens-data ./packages/annotation/data /")
        print("  5) modal volume put traillens-data ./photos /images")
        print("  6) modal secret create traillens-train --from-env WANDB_API_KEY")
        print("  7) modal run packages/aesthetic/train_modal.py::run --use-exif true")
        sys.exit(0)
    print("→ 用 `modal run train_modal.py::run` 启动训练")
