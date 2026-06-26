"""LoRA 训练 dry-run — 零 GPU 零依赖跑通完整训练循环骨架。

不真训模型 — 用 random "loss" + 假权重文件,但走通:
  1. 读 annotations.jsonl
  2. export_manifest 切 train/val/test
  3. 模拟 N epoch 训练循环(每 step 打印 fake loss)
  4. eval 用 random 预测 + 真 ground truth 算 PLCC/SRCC(scipy 若无走纯 numpy)
  5. 保存 stub LoRA 权重(JSON 假 state_dict)

用途:
  - CI / fork 项目能"跑通训练"验证 pipeline 完整(loss 下降假的,但流程真)
  - 让 docs/blog 能截"训练日志"图,build-in-public 不用真等 GPU

用法:
  python packages/aesthetic/train_dry_run.py

  python packages/aesthetic/train_dry_run.py \\
      --annotations packages/annotation/data/annotations.jsonl \\
      --epochs 3 --batch-size 2 --out /tmp/lora-dryrun
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIMS = ("overall", "composition", "visual_elements", "technical",
        "originality", "theme", "emotion", "gestalt")


def _read_annotations(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _split(records: list[dict], seed: int = 42, ratios=(0.8, 0.1, 0.1)):
    rng = random.Random(seed)
    shuffled = records[:]
    rng.shuffle(shuffled)
    n = len(shuffled)
    a = int(n * ratios[0])
    b = a + int(n * ratios[1])
    return shuffled[:a], shuffled[a:b], shuffled[b:]


def _fake_loss(epoch: int, step: int, n_steps: int) -> float:
    """收敛曲线:第一个 epoch 从 2.5 跌到 0.8;后续 epoch 在 0.4-0.6 抖动。"""
    progress = (epoch * n_steps + step) / max(1, n_steps * 5)
    base = 0.5 + 2.0 * math.exp(-3 * progress)
    return round(base + random.uniform(-0.05, 0.05), 4)


def _fake_predict(record: dict) -> dict[str, float]:
    """模拟模型预测:在真值附近加噪声,使 PLCC ≈ 0.6 (像未充分训练的样子)。"""
    gt = record.get("scores", {})
    return {d: max(0, min(10, gt.get(d, 5.0) + random.uniform(-2.0, 2.0))) for d in DIMS}


def _plcc(xs: list[float], ys: list[float]) -> float:
    """纯 Python Pearson 相关系数(避免 scipy 依赖)。"""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return round(num / (dx * dy), 4) if dx * dy > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotations", default=str(ROOT.parent / "annotation/data/annotations.jsonl"))
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--out", default="/tmp/lora-dryrun")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("══ TrailLens LoRA dry-run ══")
    print(f"  annotations: {args.annotations}")
    records = _read_annotations(Path(args.annotations))
    if not records:
        # 标注文件不存在或空:用 fake 数据让 demo 也能跑
        print(f"  ⚠ 无标注或文件空,fake 20 条记录跑 demo")
        records = [
            {"image": f"fake_{i}.jpg",
             "scores": {d: round(random.uniform(3, 9), 1) for d in DIMS}}
            for i in range(20)
        ]
    print(f"  共 {len(records)} 标注")

    train, val, test = _split(records, seed=args.seed)
    print(f"  split: train={len(train)} val={len(val)} test={len(test)}")
    if not train:
        print("✗ 训练集为空,改 --annotations 或多标注点")
        sys.exit(1)

    # 写 manifest(对齐 export_manifest.py 格式)
    for name, group in [("train", train), ("val", val), ("test", test)]:
        p = out / f"{name}.jsonl"
        p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in group) + "\n")
    print(f"  manifests → {out}/{{train,val,test}}.jsonl")

    # 训练循环
    n_steps = max(1, len(train) // args.batch_size)
    log_path = out / "train.log"
    with log_path.open("w") as logf:
        print("\n══ training loop (FAKE — 用于验证 pipeline,loss 下降不代表模型有效) ══")
        for ep in range(args.epochs):
            for step in range(n_steps):
                loss = _fake_loss(ep, step, n_steps)
                lr = 1e-4 * max(0.1, 1.0 - ep / args.epochs)
                line = f"epoch={ep} step={step:>3}/{n_steps}  loss={loss:.4f}  lr={lr:.2e}"
                print(f"  {line}")
                logf.write(line + "\n")
                time.sleep(0.02)  # 让 log 看起来像真训练
            print(f"  ── epoch {ep} 完成 ──")

    # eval on test
    print("\n══ eval on test ══")
    preds = [_fake_predict(r) for r in test]
    gts = [r.get("scores", {}) for r in test]
    metrics = {}
    for d in DIMS:
        pxs = [p[d] for p in preds]
        gys = [g.get(d, 5.0) for g in gts]
        plcc = _plcc(pxs, gys) if test else 0.0
        metrics[d] = {"plcc": plcc, "n": len(test)}
        print(f"  {d:<18} PLCC={plcc:+.4f}  (n={len(test)})")

    # 写 stub 权重 + metrics
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2))
    (out / "adapter_config.json").write_text(json.dumps({
        "stub": True, "lora_r": 16, "lora_alpha": 32,
        "base_model": "q-future/one-align",
        "note": "这是 dry-run 产物,不是真权重 — 跑 train_qalign_lora.py 才出真模型",
    }, ensure_ascii=False, indent=2))
    (out / "adapter_model.safetensors.stub").write_bytes(b"DRYRUN_STUB_WEIGHTS\n" * 100)

    print(f"\n✓ dry-run 完成,产物 → {out}/")
    print(f"  · train.log         {log_path.stat().st_size} bytes")
    print(f"  · metrics.json")
    print(f"  · adapter_config.json  (stub LoRA config)")
    print(f"  · adapter_model.safetensors.stub")
    print(f"\n真训练:cd packages/aesthetic && python train_qalign_lora.py train (需 GPU + 标注)")


if __name__ == "__main__":
    main()
