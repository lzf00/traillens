"""把 annotations.jsonl 导出为训练 / 验证 / 测试 manifest。

切分:80 / 10 / 10,随机种子固定(可复现)。
输出格式与 packages/aesthetic/train_qalign_lora.py 的 manifest 规范一致。
"""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANNOT = ROOT / "data/annotations.jsonl"
OUT_DIR = ROOT / "data"

SEED = 42


def main():
    if not ANNOT.exists():
        raise SystemExit(f"找不到 {ANNOT}。请先标注。")

    # 每张照片取最新一条标注(去重)
    by_image: dict[str, dict] = {}
    for line in ANNOT.read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            by_image[d["image"]] = d
    records = list(by_image.values())
    print(f"  {len(records)} unique labeled images")

    if len(records) < 10:
        raise SystemExit("样本太少(< 10),建议至少标 50 张再 export。")

    rng = random.Random(SEED)
    rng.shuffle(records)
    n = len(records)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    splits = {
        "landscape_train": records[:n_train],
        "landscape_val": records[n_train : n_train + n_val],
        "landscape_test": records[n_train + n_val:],
    }
    for name, batch in splits.items():
        out = OUT_DIR / f"{name}.jsonl"
        with out.open("w") as f:
            for r in batch:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  → {out.name}: {len(batch)} samples")

    print("\n下一步:")
    print("  ln -s packages/annotation/data/landscape_train.jsonl packages/aesthetic/data/")
    print("  cd packages/aesthetic && python train_qalign_lora.py train")


if __name__ == "__main__":
    main()
