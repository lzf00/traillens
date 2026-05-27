"""生成确定性合成照片用于流水线干跑。

什么时候用:
  - sprint 2 真数据到位前(测 prefill / serve / 训练 data loader 形态)
  - CI 里测端到端流水线(不能依赖真照片)
  - 给标注工具截图 / 录 demo

为什么合成而非随机:
  - 同样的 seed 永远得到同样的图,test 可复现
  - 不同 seed 得到颜色/构图差异明显的图,模型 / 评分能区分

输出:30 张 256x192 jpg,文件名 synth_p000.jpg ... synth_p029.jpg
"""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path


def generate_batch(out_dir: Path, n: int = 30, seed: int = 42) -> list[Path]:
    """生成 n 张合成 landscape 风格图。"""
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        raise SystemExit("pip install Pillow")

    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    files: list[Path] = []

    for i in range(n):
        img = Image.new("RGB", (256, 192))
        draw = ImageDraw.Draw(img)

        # 天空(顶部 2/3)— 渐变
        sky_top = (rng.randint(20, 80), rng.randint(40, 120), rng.randint(80, 180))
        sky_bot = tuple(min(255, c + rng.randint(40, 80)) for c in sky_top)
        for y in range(128):
            t = y / 128
            r = int(sky_top[0] * (1 - t) + sky_bot[0] * t)
            g = int(sky_top[1] * (1 - t) + sky_bot[1] * t)
            b = int(sky_top[2] * (1 - t) + sky_bot[2] * t)
            draw.line([(0, y), (256, y)], fill=(r, g, b))

        # 山脊线(底部 1/3)
        ground_color = (rng.randint(20, 60), rng.randint(40, 80), rng.randint(20, 60))
        peaks = [(x, 128 + int(20 * math.sin(x / 30 + i)) + rng.randint(-10, 10))
                 for x in range(0, 256, 8)]
        peaks = [(0, 192)] + peaks + [(256, 192)]
        draw.polygon(peaks, fill=ground_color)

        # 小细节:太阳 / 月亮
        if i % 4 == 0:
            cx = rng.randint(40, 220)
            cy = rng.randint(20, 80)
            r = rng.randint(8, 16)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(240, 220, 150))

        # 轻微模糊增加自然感
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

        path = out_dir / f"synth_p{i:03d}.jpg"
        img.save(path, "JPEG", quality=85)
        files.append(path)

    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../photos", help="输出目录(相对 annotation/server/)")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    out = (Path(__file__).resolve().parent / args.out).resolve()
    files = generate_batch(out, n=args.n, seed=args.seed)
    print(f"→ {len(files)} synth images at {out}")


if __name__ == "__main__":
    main()
