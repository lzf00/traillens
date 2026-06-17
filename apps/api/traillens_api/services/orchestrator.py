"""把 agents 跑出的事件转换成 SSE 流。

两条路径(自动选择):
  (1) 装了 langgraph + checkpointer 时:用 graph.astream_events(),真正的事件流
  (2) 否则:在线程池跑 run_fallback,边消费 messages 边产生事件

两条路径的 SSE 输出 schema 完全一致 — 前端不区分。
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path

_AGENTS = Path(__file__).resolve().parents[4] / "packages" / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

from traillens_agents.demo import run_fallback  # noqa: E402
from traillens_agents.state.schema import GraphState, HikeContext, PhotoVerdict  # noqa: E402
from traillens_agents.tools import clients  # noqa: E402

from .observability import log_agent_event, trace_agent_run  # noqa: E402


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _sse_and_log(run_id: str, event: str, data: dict) -> str:
    log_agent_event(run_id, event, data)
    return _sse(event, data)


def _build_initial_state(trail_id: str, run_id: str) -> GraphState:
    # TODO Sprint 5:从 store 读真实 photos
    return GraphState(
        photos=clients.load_sample_photos(8),
        hike=HikeContext(location_name="贡嘎环线", gpx_uri="sample://"),
        run_id=run_id,
    )


def _photo_event(p) -> dict:
    return {
        "photo_id": p.photo_id,
        "verdict": p.verdict.value if p.verdict else None,
        "overall": p.aesthetic.overall if p.aesthetic else None,
        "trace_steps": len(p.decision_trace),
    }


# --------------------------------------------------------------------------- #
# 主入口:自动二选一
# --------------------------------------------------------------------------- #
async def run_trail_stream(trail_id: str, run_id: str, user_id: str = "anon") -> AsyncIterator[str]:
    log_agent_event(run_id, "run.started", {"trail_id": trail_id})
    yield _sse("run.started", {"run_id": run_id, "trail_id": trail_id})

    with trace_agent_run(run_id, trail_id, user_id):
        try:
            async for chunk in _via_langgraph(trail_id, run_id):
                yield chunk
            return
        except _LangGraphUnavailable:
            async for chunk in _via_fallback(trail_id, run_id):
                yield chunk


class _LangGraphUnavailable(Exception):
    pass


# --------------------------------------------------------------------------- #
# Path A:真实 LangGraph astream_events
# --------------------------------------------------------------------------- #
async def _via_langgraph(trail_id: str, run_id: str) -> AsyncIterator[str]:
    try:
        from traillens_agents.orchestrator import build_graph
    except ImportError:
        raise _LangGraphUnavailable()
    try:
        graph = build_graph()
    except ImportError:
        raise _LangGraphUnavailable()

    state = _build_initial_state(trail_id, run_id)
    last_state: GraphState | None = None
    seen_photo_ids: set[str] = set()
    try:
        async for event in graph.astream_events(state, version="v2"):
            kind = event.get("event")
            name = event.get("name", "")
            # 节点开始 / 结束转 SSE
            if kind == "on_chain_start" and name in {"culling", "human_review", "critic", "story", "planner", "orchestrator"}:
                yield _sse("orchestrator.routed", {"node": name, "phase": "start"})
            elif kind == "on_chain_end":
                data = event.get("data", {}) or {}
                output = data.get("output")
                # LangGraph 节点的 output 可能是 dict、GraphState 或 BaseModel
                photos_iter = None
                if isinstance(output, dict) and "photos" in output:
                    last_state = output if isinstance(output, GraphState) else GraphState(**output)
                    photos_iter = last_state.photos
                elif isinstance(output, GraphState):
                    last_state = output
                    photos_iter = output.photos
                elif hasattr(output, "photos"):
                    last_state = output  # type: ignore[assignment]
                    photos_iter = output.photos
                if photos_iter:
                    for p in photos_iter:
                        if p.aesthetic and p.photo_id not in seen_photo_ids:
                            seen_photo_ids.add(p.photo_id)
                            yield _sse("culling.photo_scored", _photo_event(p))
    except Exception as e:  # noqa: BLE001  langgraph API 任何报错 → 切 fallback
        yield _sse("run.error", {"phase": "langgraph", "error": str(e)})
        raise _LangGraphUnavailable() from e

    if last_state:
        # 兜底:跑完后 photos 还没 emit 过的(可能 on_chain_end 漏抓)统一推
        for p in last_state.photos:
            if p.aesthetic and p.photo_id not in seen_photo_ids:
                seen_photo_ids.add(p.photo_id)
                yield _sse("culling.photo_scored", _photo_event(p))
        # 持久化分数 + 游记 + 计划到 DB
        try:
            from . import store
            store.persist_run_results(
                trail_id,
                last_state.photos,
                travelogue_md=last_state.travelogue_md,
                next_trip_plan=last_state.next_trip_plan,
            )
        except Exception as e:  # noqa: BLE001
            yield _sse("run.error", {"phase": "persist", "error": str(e)})
        if last_state.travelogue_md:
            yield _sse("story.delta", {"chunk": last_state.travelogue_md})
        if last_state.next_trip_plan:
            yield _sse("planner.plan_ready", {"plan": last_state.next_trip_plan})
        yield _sse("run.finished", {
            "run_id": run_id, "trail_id": trail_id,
            "kept": sum(1 for p in last_state.photos if p.verdict == PhotoVerdict.KEEP),
            "total": len(last_state.photos),
        })


# --------------------------------------------------------------------------- #
# Path B:fallback — 在线程池跑同步 run_fallback,边跑边推
# --------------------------------------------------------------------------- #
async def _via_fallback(trail_id: str, run_id: str) -> AsyncIterator[str]:
    """跑同步 fallback,在线程外把 messages 当事件流"投递"。

    真实流式效果靠"每个 message 之间 sleep(0.02)"模拟,
    虽然不是 token-level streaming,但对 UX 已经足够"活"。
    """
    state = _build_initial_state(trail_id, run_id)

    loop = asyncio.get_event_loop()
    final = await loop.run_in_executor(None, run_fallback, state)

    for msg in final.messages:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if role == "orchestrator":
            yield _sse("orchestrator.routed", {"trace": content})
        elif role == "culling":
            yield _sse("culling.progress", {"summary": content})
        elif role == "human_review":
            yield _sse("human_review.required", {"summary": content})
        elif role == "critic":
            yield _sse("critic.photo_critiqued", {"summary": content})
        elif role == "story":
            yield _sse("story.delta", {"chunk": final.travelogue_md or ""})
        elif role == "planner":
            yield _sse("planner.plan_ready", {"plan": final.next_trip_plan or {}})
        await asyncio.sleep(0.02)

    for p in final.photos:
        if p.aesthetic:
            yield _sse("culling.photo_scored", _photo_event(p))

    # 持久化到 DB
    try:
        from . import store
        store.persist_run_results(
            trail_id,
            final.photos,
            travelogue_md=final.travelogue_md,
            next_trip_plan=final.next_trip_plan,
        )
    except Exception as e:  # noqa: BLE001
        yield _sse("run.error", {"phase": "persist", "error": str(e)})

    yield _sse("run.finished", {
        "run_id": run_id, "trail_id": trail_id,
        "kept": len(final.kept_photos()),
        "total": len(final.photos),
    })
