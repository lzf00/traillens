"""端到端 demo 入口。

两种运行模式:
1. 若安装了 langgraph -> 走真实编译图。
2. 否则 -> 走纯 Python fallback(手动驱动 orchestrator 循环),
   保证你 clone 下来 `python -m traillens_agents.demo` 就能看到效果,
   零外部依赖。这对作品集"一键复现"非常关键。

运行:
    cd packages/agents
    python -m traillens_agents.demo
"""

from __future__ import annotations

import json

from .orchestrator import decide_next, orchestrator_node
from .nodes.business import (
    critic_node,
    culling_node,
    human_review_node,
    planner_node,
    story_node,
)
from .state.schema import GraphState, HikeContext
from .tools import clients

_NODE_FUNCS = {
    "culling": culling_node,
    "human_review": human_review_node,
    "critic": critic_node,
    "story": story_node,
    "planner": planner_node,
}


def _apply(state: GraphState, update: dict) -> GraphState:
    """把节点返回的部分更新合并进 state(模拟 LangGraph reducer)。"""
    data = state.model_dump()
    for k, v in update.items():
        if k in ("messages", "errors"):
            data[k] = data.get(k, []) + v
        else:
            data[k] = v
    return GraphState(**data)


def run_fallback(state: GraphState, max_steps: int = 20) -> GraphState:
    """无 langgraph 时的手动 supervisor 循环。"""
    for _ in range(max_steps):
        route = orchestrator_node(state)
        state = _apply(state, route)
        nxt = state.next_agent
        if nxt == "FINISH":
            break
        state = _apply(state, _NODE_FUNCS[nxt](state))
    return state


def run_demo() -> None:
    photos = clients.load_sample_photos(8)
    init = GraphState(
        photos=photos,
        hike=HikeContext(location_name="贡嘎环线", gpx_uri="sample://track.gpx"),
    )

    try:
        from .orchestrator import build_graph

        graph = build_graph()
        # LangGraph 接受 dict 或 BaseModel;这里用 dict 以兼容不同版本
        final_raw = graph.invoke(init.model_dump())
        final = GraphState(**final_raw) if isinstance(final_raw, dict) else final_raw
        mode = "LangGraph"
    except Exception as e:  # noqa: BLE001  (demo 容错,生产不要这样吞异常)
        print(f"[fallback] langgraph 不可用或报错({type(e).__name__}),走纯 Python 模式\n")
        final = run_fallback(init)
        mode = "fallback"

    print(f"=== TrailLens demo 运行完成({mode}) ===\n")
    print("路由轨迹:")
    for m in final.messages:
        print(f"  [{m['role']:>13}] {m['content']}")

    kept = final.kept_photos()
    print(f"\n精选 {len(kept)} 张:")
    for p in kept:
        score = p.aesthetic.overall if p.aesthetic else "-"
        print(f"  {p.photo_id}  overall={score}  {(p.critique or '')[:40]}")

    print("\n--- 游记(前 6 行)---")
    print("\n".join((final.travelogue_md or "").splitlines()[:6]))

    print("\n--- 下次拍摄计划 ---")
    print(json.dumps(final.next_trip_plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_demo()
