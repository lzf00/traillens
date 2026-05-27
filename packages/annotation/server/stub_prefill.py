"""离线 prefill — 不调 GPT-5V,用 serve.py 的确定性 stub 给一组照片打分。

意图:让 sprint 2 的"prefill → 人工校准 → export"流水线在
*没有 API key 时* 也能从头到尾跑一遍,验证格式不出错。

用法:
    python stub_prefill.py photos/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 复用 aesthetic/serve.py 的确定性算法
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "aesthetic"))
from serve import ScoreRequest, score_image  # type: ignore  # noqa: E402

DIMS = (
    "overall", "composition", "visual_elements", "technical",
    "originality", "theme", "emotion", "gestalt",
)


def main():
    if len(sys.argv) != 2:
        print("usage: stub_prefill.py <photos_dir>", file=sys.stderr); sys.exit(1)
    folder = Path(sys.argv[1])
    photos_root = (Path(__file__).resolve().parents[1] / "photos").resolve()
    out = Path(__file__).resolve().parents[1] / "data" / "prefill.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)

    photos = sorted(p for p in folder.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    print(f"  {len(photos)} images to prefill (stub)")

    with out.open("w") as f:
        for i, p in enumerate(photos, 1):
            resp = score_image(ScoreRequest(image_url=str(p)))
            scores = {d: getattr(resp, d) for d in DIMS}
            try:
                rel = str(p.relative_to(photos_root))
            except ValueError:
                rel = p.name
            f.write(json.dumps(
                {"image": rel, "scores": scores, "source": "stub"},
                ensure_ascii=False,
            ) + "\n")
            print(f"  [{i}/{len(photos)}] {p.name} overall={scores['overall']}")

    print(f"\n→ wrote {out}")


if __name__ == "__main__":
    main()
