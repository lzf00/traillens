"""Orchestrator(supervisor)与 LangGraph 图组装。

架构:supervisor 路由模式
-------------------------
            +-------------+
            | orchestrator|<-------------------+
            +------+------+                    |
                   | next_agent                | (每个业务节点跑完回到 orchestrator)
      +------------+------------+------------+  |
      v            v            v            v  |
  culling   human_review     story       planner
      |            |            |            |  |
      +------------+------------+------------+--+

orchestrator 是一个 *确定性* 路由器(也可换成 LLM 决策)。
当前用规则:先选片 -> 若有待审则 HITL -> 点评 -> 游记 -> 计划 -> FINISH。

为什么不直接线性串联?
- supervisor 模式让"是否需要 HITL""是否跳过 planner(无 GPS)"等动态决策集中可控,
  也便于后续替换为 LLM-as-router,符合路线图后期演进。
- 这是 LangGraph 相对 CrewAI 顺序流的核心优势:显式状态机 + 条件边。

依赖: langgraph>=0.2
若未安装 langgraph,可运行 run_demo() 走纯 Python fallback(见 demo.py)。
"""

from __future__ import annotations

from .nodes.business import (
    critic_node,
    culling_node,
    human_review_node,
    planner_node,
    story_node,
)
from .state.schema import GraphState, PhotoVerdict


# --------------------------------------------------------------------------- #
# Orchestrator 路由逻辑(纯函数,易测)
# --------------------------------------------------------------------------- #
def decide_next(state: GraphState) -> str:
    """返回下一个要去的节点名(或 FINISH)。

    通过已完成的痕迹推断进度 —— 用 state 里已被填充的字段作为"阶段标记"。
    """
    done_culling = any(p.verdict is not None for p in state.photos)
    if not done_culling:
        return "culling"

    # 选片后若仍有待审,先走人工(HITL)
    if state.pending_review_ids:
        return "human_review"

    done_critic = any(
        p.critique is not None for p in state.photos if p.verdict == PhotoVerdict.KEEP
    )
    if not done_critic and state.kept_photos():
        return "critic"

    if state.travelogue_md is None:
        return "story"

    if state.next_trip_plan is None and state.hike.gps_lat is not None:
        return "planner"

    return "FINISH"


def orchestrator_node(state: GraphState) -> dict:
    nxt = decide_next(state)
    return {
        "next_agent": nxt,
        "messages": [{"role": "orchestrator", "content": f"route -> {nxt}"}],
    }


# --------------------------------------------------------------------------- #
# LangGraph 图组装(真实运行路径)
# --------------------------------------------------------------------------- #
def build_graph():
    """组装并编译 LangGraph。仅在 langgraph 可用时调用。"""
    from langgraph.graph import END, StateGraph  # 延迟导入,避免无依赖时报错

    g = StateGraph(GraphState)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("culling", culling_node)
    g.add_node("human_review", human_review_node)
    g.add_node("critic", critic_node)
    g.add_node("story", story_node)
    g.add_node("planner", planner_node)

    g.set_entry_point("orchestrator")

    # 条件边:orchestrator 根据 next_agent 分发
    g.add_conditional_edges(
        "orchestrator",
        lambda s: s.next_agent,
        {
            "culling": "culling",
            "human_review": "human_review",
            "critic": "critic",
            "story": "story",
            "planner": "planner",
            "FINISH": END,
        },
    )
    # 每个业务节点执行完回到 orchestrator 重新路由(supervisor 模式)
    for node in ["culling", "human_review", "critic", "story", "planner"]:
        g.add_edge(node, "orchestrator")

    # [REAL] 生产中传入 checkpointer=PostgresSaver(...) 以支持 HITL 中断/恢复
    return g.compile()
