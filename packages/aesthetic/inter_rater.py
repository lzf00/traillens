"""标注者间一致性 — Krippendorff's α(interval scale)。

为什么是 Krippendorff 而非 Cohen's kappa
----------------------------------------
- Krippendorff α 支持 *任意* 标注者数量 + *缺失* 数据
- 支持区间数据(我们的 0-10 评分)、有序数据、分类数据
- 比 Cohen kappa 适用面广,文献用得更多

参考: Krippendorff (2011) "Computing Krippendorff's Alpha-Reliability"
http://web.asc.upenn.edu/usr/krippendorff/mwebreliability4.pdf

Α >= 0.8: 优秀
Α >= 0.667: 可接受(社会科学界惯用门槛)
Α >= 0.5: 用于探索性研究
Α < 0.5: rubric 需要重写

工程意图(对接 RESEARCH.md §3.2):
  对 100 张子集,2-3 位标注者独立打 8 维分 → 算每个维度的 α
  α < 0.6 的维度 → 修 rubric → 重标
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path


def krippendorff_alpha_interval(ratings: list[list[float | None]]) -> float:
    """计算 Krippendorff α(interval metric)。

    Args:
        ratings: 形如 [[r1_unit1, r1_unit2, ...], [r2_unit1, r2_unit2, ...], ...]
                 即 ratings[标注者][单位]。缺失用 None。

    Returns:
        α 值,范围 (-∞, 1]。1 = 完美一致;0 = 随机;<0 = 比随机还差。

    Algorithm:
        D_o = Σ Σ δ(c_uk, c_uk') / Σ count_pairs(u)        (观察到的不一致)
        D_e = Σ Σ δ(c_i, c_j) * n_i * n_j / (n*(n-1))      (期望不一致)
        α = 1 - D_o / D_e
        其中 δ(a, b) = (a-b)² 对 interval scale。
    """
    if not ratings or len(ratings) < 2:
        return float("nan")

    n_units = len(ratings[0])
    if not all(len(r) == n_units for r in ratings):
        raise ValueError("all raters must rate the same number of units")

    # 收集所有非空评分(c_uk)与每单位的评分数
    all_vals: list[float] = []
    units_with_pairs = 0
    sum_observed_disagree = 0.0

    for u in range(n_units):
        col = [r[u] for r in ratings if r[u] is not None]
        if len(col) < 2:
            continue
        units_with_pairs += 1
        nu = len(col)
        all_vals.extend(col)
        # 单位内两两 δ 求和,归一到"每对"
        pair_disagree = 0.0
        for i in range(nu):
            for j in range(nu):
                if i != j:
                    pair_disagree += (col[i] - col[j]) ** 2
        sum_observed_disagree += pair_disagree / (nu - 1)

    if not all_vals or units_with_pairs == 0:
        return float("nan")

    N = len(all_vals)
    # 期望不一致:全样本两两 δ 期望
    sum_expected_disagree = 0.0
    for i in range(N):
        for j in range(N):
            if i != j:
                sum_expected_disagree += (all_vals[i] - all_vals[j]) ** 2
    D_e = sum_expected_disagree / (N * (N - 1)) if N > 1 else 0.0
    D_o = sum_observed_disagree / N

    if D_e == 0:
        return 1.0 if D_o == 0 else float("nan")
    return 1.0 - D_o / D_e


# --------------------------------------------------------------------------- #
# 按维度算 α(对接标注 jsonl 格式)
# --------------------------------------------------------------------------- #
DIMS = (
    "overall", "composition", "visual_elements", "technical",
    "originality", "theme", "emotion", "gestalt",
)


def alpha_per_dim(
    annotations: list[dict],
    raters: Iterable[str] | None = None,
) -> dict[str, float]:
    """对一组多人标注算每个维度的 α。

    Args:
        annotations: 标注列表,每条形如:
            {"image": "p001.jpg", "annotator": "alice", "scores": {"overall": 7.2, ...}}
        raters: 强制使用的标注者集合;不给则用 annotations 中出现的所有

    Returns:
        {dim: α} dict
    """
    # 整理 image 集合 + 标注者集合
    images = sorted({a["image"] for a in annotations})
    if raters is None:
        raters = sorted({a["annotator"] for a in annotations})
    else:
        raters = list(raters)

    # 建索引:(annotator, image) → scores
    by_rater_image: dict[tuple[str, str], dict] = {}
    for a in annotations:
        by_rater_image[(a["annotator"], a["image"])] = a.get("scores", {})

    result = {}
    for dim in DIMS:
        ratings = [
            [
                by_rater_image.get((r, img), {}).get(dim)
                for img in images
            ]
            for r in raters
        ]
        result[dim] = round(krippendorff_alpha_interval(ratings), 4)
    return result


# --------------------------------------------------------------------------- #
# CLI:把 annotations.jsonl 喂进去得到每维 α
# --------------------------------------------------------------------------- #
def main():
    import argparse

    ap = argparse.ArgumentParser(description="算 Krippendorff α(按 8 维)")
    ap.add_argument("annotations", type=Path, help="annotations.jsonl 路径")
    ap.add_argument("--threshold", type=float, default=0.667,
                    help="低于此 α 的维度被标记为需重写 rubric")
    args = ap.parse_args()

    records = [
        json.loads(l) for l in args.annotations.read_text().splitlines() if l.strip()
    ]
    print(f"  {len(records)} annotations from {len({r['annotator'] for r in records})} raters")
    alphas = alpha_per_dim(records)

    print(f"\n{'维度':<20} {'α':>8}  状态")
    print("-" * 40)
    for dim, a in alphas.items():
        status = "✓" if a >= args.threshold else f"× (< {args.threshold})"
        print(f"{dim:<20} {a:>8.4f}  {status}")

    bad = [d for d, a in alphas.items() if a < args.threshold]
    if bad:
        print(f"\n⚠ {len(bad)} 个维度需重写 rubric: {bad}")
    else:
        print("\n✓ 全部维度达标")


if __name__ == "__main__":
    main()
