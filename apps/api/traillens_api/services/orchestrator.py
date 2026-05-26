"""把 agents 包跑出的事件转换成 SSE 流。

Sprint 3 末:用 LangGraph 的 astream_events;当前用 fallback 路径
封装成 generator,行为与真实路径一致(supervisor → node → orchestrator)。
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path

# 让 traillens_agents 可被 import(monorepo 布局)
_AGENTS = Path(__file__).resolve().parents[4] / "packages" / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

from traillens_agents.demo import run_fallback  # noqa: E402
from traillens_agents.state.schema import GraphState, HikeContext  # noqa: E402
from traillens_agents.tools import clients  # noqa: E402


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def run_trail_stream(trail_id: str, run_id: str) -> AsyncIterator[str]:
    """SSE 事件流。Sprint 3 末真正接入 langgraph.astream_events。

    当前实现:用 run_fallback 同步跑,把 state.messages 翻译成 SSE 事件。
    每个事件 yield 后 sleep 一点点,模拟真实流式体验(前端能看到逐条到达)。
    """
    # TODO: Sprint 5 — 从 store 读真实 photos,这里先用 sample。
    init = GraphState(
        photos=clients.load_sample_photos(8),
        hike=HikeContext(location_name="贡嘎环线", gpx_uri="sample://"),
        run_id=run_id,
    )

    yield _sse("run.started", {"run_id": run_id, "trail_id": trail_id})

    # 这里同步跑,因为 fallback 是阻塞的;
    # Sprint 3 改用 LangGraph astream_events 时,这里换成真正的 async for。
    final = run_fallback(init)

    for msg in final.messages:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        # 路由消息 → orchestrator.routed
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
        await asyncio.sleep(0.02)  # 给前端一个能感知"流"的节奏

    # 把每张照片的最终评分也单独 emit(供前端缩略图轨道高亮)
    for p in final.photos:
        if p.aesthetic:
            yield _sse("culling.photo_scored", {
                "photo_id": p.photo_id,
                "verdict": p.verdict.value if p.verdict else None,
                "overall": p.aesthetic.overall,
                "trace_steps": len(p.decision_trace),
            })

    yield _sse("run.finished", {
        "run_id": run_id,
        "trail_id": trail_id,
        "kept": len(final.kept_photos()),
        "total": len(final.photos),
    })
