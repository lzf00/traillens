"""三块交付物一致性测试(cross-check)。

把"README 描述的架构 = 代码骨架的真实结构 = 微调方案产出的模型接口"
这三者的对齐关系做成 *可执行断言*,既能本地 `python -m unittest`,
也能在 CI 里被 pytest 收集(pytest 兼容 unittest.TestCase)。

零依赖:仅用标准库 + 项目内代码,跑通无需安装 pytest / pydantic。

运行:
    python -m unittest tests.test_consistency -v
    # 或
    pytest tests/test_consistency.py -v
"""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

# 测试期间默认走 stub,避免依赖外网(否则 CI 在无网络环境会假阳性失败)
# 个别测试可在本地 unset 这个变量来测真实 MCP 集成
os.environ.setdefault("TRAILLENS_USE_STUBS", "1")
os.environ.setdefault("TRAILLENS_DISABLE_RATELIMIT", "1")

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "packages/agents"
# 把 agents 包路径塞到 sys.path,使 `import traillens_agents` 工作
if str(AGENTS) not in sys.path:
    sys.path.insert(0, str(AGENTS))


# --------------------------------------------------------------------------- #
# 契约 1: 美学微调方案的 score_dims == agent 端 AestheticScore 的 8 个评分字段
# --------------------------------------------------------------------------- #
class TestContract1AestheticSchema(unittest.TestCase):
    """美学评分维度在"训练脚本 ↔ agent 状态"两侧必须严格对齐。"""

    SCORE_DIMS = {
        "overall", "composition", "visual_elements", "technical",
        "originality", "theme", "emotion", "gestalt",
    }

    def test_aesthetic_score_contains_all_8_dims(self):
        from traillens_agents.state.schema import AestheticScore

        # pydantic v2 用 model_fields;dataclass fallback 用 __dataclass_fields__
        fields = set(
            getattr(AestheticScore, "model_fields", None)
            or AestheticScore.__dataclass_fields__
        )
        missing = self.SCORE_DIMS - fields
        self.assertFalse(missing, f"AestheticScore 缺失维度: {missing}")

    def test_train_script_dims_match_schema(self):
        train_src = (ROOT / "packages/aesthetic/train_qalign_lora.py").read_text(
            encoding="utf-8"
        )
        m = re.search(r"score_dims:.*?=\s*\((.*?)\)", train_src, re.S)
        self.assertIsNotNone(m, "未在训练脚本中找到 score_dims 元组")
        train_dims = set(re.findall(r'"(\w+)"', m.group(1)))
        diff = train_dims ^ self.SCORE_DIMS
        self.assertFalse(
            diff, f"训练脚本与 AestheticScore 维度不一致: {diff}"
        )


# --------------------------------------------------------------------------- #
# 契约 2: README 架构图节点 == orchestrator 路由表 == 实际节点函数
# --------------------------------------------------------------------------- #
class TestContract2GraphTopology(unittest.TestCase):
    """README 架构、路由器、节点实现三者必须能对得上。"""

    def setUp(self):
        self.readme_src = (ROOT / "README.md").read_text(encoding="utf-8")
        self.orch_src = (
            AGENTS / "traillens_agents/orchestrator.py"
        ).read_text(encoding="utf-8")
        self.readme_agents = set(
            re.findall(r"next_agent=(\w+)", self.readme_src)
        )
        self.orch_returns = set(re.findall(r'return\s+"(\w+)"', self.orch_src))
        self.orch_routes = self.orch_returns - {"FINISH"}

    def test_readme_agents_are_subset_of_router(self):
        extra = self.readme_agents - self.orch_returns
        self.assertFalse(
            extra,
            f"README 提到的路由 {extra} 在 orchestrator.decide_next 中不存在",
        )

    def test_every_router_target_has_node_function(self):
        from traillens_agents.nodes import business

        node_funcs = {n.replace("_node", "") for n in dir(business) if n.endswith("_node")}
        missing = self.orch_routes - node_funcs
        self.assertFalse(missing, f"路由指向但无实现的节点: {missing}")


# --------------------------------------------------------------------------- #
# 契约 3: tools.score_aesthetics 返回的是 AestheticScore 实例,分数在 [0,10]
# --------------------------------------------------------------------------- #
class TestContract3ToolsReturnShape(unittest.TestCase):
    def test_score_aesthetics_returns_aesthetic_score(self):
        from traillens_agents.state.schema import AestheticScore
        from traillens_agents.tools import clients

        sample = clients.load_sample_photos(1)[0]
        score = clients.score_aesthetics(sample)
        self.assertIsInstance(score, AestheticScore)

    def test_score_within_valid_range(self):
        from traillens_agents.tools import clients

        sample = clients.load_sample_photos(1)[0]
        score = clients.score_aesthetics(sample)
        self.assertGreaterEqual(score.overall, 0.0)
        self.assertLessEqual(score.overall, 10.0)


# --------------------------------------------------------------------------- #
# 契约 4: 端到端可跑(冒烟测试)—— 整张图活着
# --------------------------------------------------------------------------- #
class TestContract4EndToEndSmoke(unittest.TestCase):
    def test_demo_pipeline_finishes_and_produces_travelogue(self):
        from traillens_agents.demo import run_fallback
        from traillens_agents.state.schema import GraphState, HikeContext
        from traillens_agents.tools import clients

        init = GraphState(
            photos=clients.load_sample_photos(6),
            hike=HikeContext(location_name="test", gpx_uri="x"),
        )
        final = run_fallback(init)
        self.assertTrue(final.travelogue_md, "未产出游记")
        self.assertEqual(
            final.next_agent, "FINISH", f"未到达 FINISH, 停在 {final.next_agent}"
        )


# --------------------------------------------------------------------------- #
# 契约 5: 每张被 culling 处理过的照片都有非空 decision_trace
#         (§3.1 M4 Auditable Decisions 模式的实现底线)
# --------------------------------------------------------------------------- #
class TestContract5DecisionTrace(unittest.TestCase):
    def test_every_processed_photo_has_decision_trace(self):
        from traillens_agents.demo import run_fallback
        from traillens_agents.state.schema import GraphState
        from traillens_agents.tools import clients

        init = GraphState(photos=clients.load_sample_photos(8))
        final = run_fallback(init)
        empty = [p.photo_id for p in final.photos if not p.decision_trace]
        self.assertFalse(
            empty, f"以下照片缺 decision_trace: {empty}"
        )

    def test_trace_step_has_required_fields(self):
        from traillens_agents.demo import run_fallback
        from traillens_agents.state.schema import GraphState
        from traillens_agents.tools import clients

        init = GraphState(photos=clients.load_sample_photos(4))
        final = run_fallback(init)
        step = final.photos[0].decision_trace[0]
        self.assertTrue(step.actor)
        self.assertTrue(step.action)


if __name__ == "__main__":
    unittest.main(verbosity=2)
