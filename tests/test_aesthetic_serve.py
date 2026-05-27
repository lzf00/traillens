"""packages/aesthetic/serve.py 契约 + 单元测试。

契约 7:ScoreResponse 字段 == AestheticScore 字段
       (任何一侧改字段名 / 加维度,CI 红)
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "packages/agents"
AESTH = ROOT / "packages/aesthetic"
for p in (AGENTS, AESTH):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


class TestContract7ServeAlignsAestheticScore(unittest.TestCase):
    def test_response_fields_equal_aesthetic_score(self):
        from serve import ScoreResponse
        from traillens_agents.state.schema import AestheticScore

        agent_fields = set(
            getattr(AestheticScore, "model_fields", None)
            or AestheticScore.__dataclass_fields__
        )
        serve_fields = set(
            getattr(ScoreResponse, "model_fields", None)
            or ScoreResponse.__dataclass_fields__
        )
        diff = serve_fields ^ agent_fields
        self.assertFalse(
            diff,
            f"ScoreResponse 与 AestheticScore 字段不一致: {diff}",
        )


class TestScoreImageDeterminism(unittest.TestCase):
    """同一 url 多次调用应当返回完全一致的分数(stub 是确定性的)。"""

    def test_same_url_yields_same_scores(self):
        from serve import ScoreRequest, score_image

        a = score_image(ScoreRequest(image_url="r2://photos/a.jpg"))
        b = score_image(ScoreRequest(image_url="r2://photos/a.jpg"))
        self.assertEqual(a.model_dump(), b.model_dump())

    def test_different_urls_yield_different_scores(self):
        from serve import ScoreRequest, score_image

        a = score_image(ScoreRequest(image_url="r2://photos/a.jpg"))
        b = score_image(ScoreRequest(image_url="r2://photos/b.jpg"))
        self.assertNotEqual(a.overall, b.overall)

    def test_score_range(self):
        from serve import ScoreRequest, score_image

        for i in range(20):
            s = score_image(ScoreRequest(image_url=f"r2://photos/{i}.jpg"))
            for dim, v in s.model_dump().items():
                if isinstance(v, (int, float)):
                    if dim == "confidence":
                        self.assertGreaterEqual(v, 0); self.assertLessEqual(v, 1)
                    elif dim != "model_version":
                        self.assertGreaterEqual(v, 0); self.assertLessEqual(v, 10)

    def test_rejects_empty_request(self):
        # 用 serve 自己暴露的 HTTPException(无 fastapi 时 serve 提供 stub)
        from serve import HTTPException, ScoreRequest, score_image

        with self.assertRaises(HTTPException):
            score_image(ScoreRequest())


if __name__ == "__main__":
    unittest.main(verbosity=2)
