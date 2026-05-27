"""Krippendorff α 单测。

通过文献已知的小数据验证算法实现正确。
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AESTH = ROOT / "packages/aesthetic"
if str(AESTH) not in sys.path:
    sys.path.insert(0, str(AESTH))


class TestKrippendorff(unittest.TestCase):
    def test_perfect_agreement_alpha_is_one(self):
        from inter_rater import krippendorff_alpha_interval

        ratings = [
            [5, 7, 3, 8, 6],
            [5, 7, 3, 8, 6],
        ]
        self.assertAlmostEqual(krippendorff_alpha_interval(ratings), 1.0, places=4)

    def test_random_independent_ratings_alpha_near_zero(self):
        """完全独立随机的两组评分,α 应接近 0(允许 ±0.3 容差)。"""
        from inter_rater import krippendorff_alpha_interval
        import random
        rng = random.Random(7)
        n = 200
        ratings = [
            [rng.uniform(0, 10) for _ in range(n)],
            [rng.uniform(0, 10) for _ in range(n)],
        ]
        a = krippendorff_alpha_interval(ratings)
        self.assertLess(abs(a), 0.3, f"random α should be near 0, got {a}")

    def test_complete_disagreement_alpha_negative(self):
        """两个标注者完全反向,α 应明显负。"""
        from inter_rater import krippendorff_alpha_interval

        ratings = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
        ]
        a = krippendorff_alpha_interval(ratings)
        self.assertLess(a, 0, f"reverse correlation α should be < 0, got {a}")

    def test_missing_data_supported(self):
        """支持缺失评分(None)。"""
        from inter_rater import krippendorff_alpha_interval

        ratings = [
            [5, None, 3, 8, 6],
            [5, 7, 3, None, 6],
        ]
        a = krippendorff_alpha_interval(ratings)
        # 共同评的 3 个单位完全一致 → α 应该很高
        self.assertGreater(a, 0.8)

    def test_single_rater_returns_nan(self):
        from inter_rater import krippendorff_alpha_interval

        a = krippendorff_alpha_interval([[5, 7, 3]])
        self.assertTrue(math.isnan(a))


class TestAlphaPerDim(unittest.TestCase):
    """对接 annotations.jsonl 格式。"""

    def test_two_raters_eight_dims(self):
        from inter_rater import alpha_per_dim, DIMS

        annotations = [
            {"image": "p001.jpg", "annotator": "alice",
             "scores": {d: 7.0 for d in DIMS}},
            {"image": "p001.jpg", "annotator": "bob",
             "scores": {d: 7.0 for d in DIMS}},
            {"image": "p002.jpg", "annotator": "alice",
             "scores": {d: 4.0 for d in DIMS}},
            {"image": "p002.jpg", "annotator": "bob",
             "scores": {d: 4.0 for d in DIMS}},
        ]
        alphas = alpha_per_dim(annotations)
        for dim in DIMS:
            self.assertIn(dim, alphas)
            self.assertAlmostEqual(alphas[dim], 1.0, places=4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
