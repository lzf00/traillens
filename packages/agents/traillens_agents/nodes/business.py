"""五个业务节点。

每个节点签名统一为: (state: GraphState) -> dict
返回的 dict 是对 state 的 *部分更新*,由 LangGraph 合并。
节点保持"纯逻辑",所有外部能力都经 tools.clients 调用,便于替换与单测。
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..state.schema import DecisionStep, GraphState, PhotoVerdict
from ..tools import clients


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Culling:技术过滤 -> 美学评分 -> 给出 verdict
# --------------------------------------------------------------------------- #
def culling_node(state: GraphState) -> dict:
    photos = [p.model_copy(deep=True) for p in state.photos]
    pending: list[str] = []

    for p in photos:
        # 增量:已有 verdict 的照片直接跳过(支持补传后重 Run)
        if p.verdict is not None:
            continue

        # 1) 先跑确定性技术检测(便宜,先筛掉硬伤,省 GPU)
        verdict, reason = clients.detect_technical_defects(p)
        p.verdict, p.reject_reason = verdict, reason
        p.decision_trace.append(
            DecisionStep(
                actor="culling",
                action=f"technical_check:{verdict.value}",
                reason=reason,
                evidence={"stage": "deterministic_filter"},
                at=_now(),
            )
        )

        # 2) 只有没被技术硬伤毙掉的才送美学模型(成本优化)
        if verdict != PhotoVerdict.REJECT:
            p.aesthetic = clients.score_aesthetics(p)
            a = p.aesthetic
            # 低分但置信度高 -> 直接拒;低置信度 -> 转人工
            if a.overall < 5.0:
                if a.confidence >= 0.8:
                    p.verdict, p.reject_reason = PhotoVerdict.REJECT, "low_aesthetic"
                    final_action = "aesthetic_reject"
                else:
                    p.verdict, p.reject_reason = PhotoVerdict.REVIEW, "uncertain_score"
                    final_action = "aesthetic_review"
            else:
                final_action = "aesthetic_keep"
            p.decision_trace.append(
                DecisionStep(
                    actor="culling",
                    action=final_action,
                    reason=p.reject_reason,
                    evidence={
                        "overall": a.overall,
                        "confidence": a.confidence,
                        "model_version": a.model_version,
                    },
                    at=_now(),
                )
            )

        if p.verdict == PhotoVerdict.REVIEW:
            pending.append(p.photo_id)

    kept = sum(1 for p in photos if p.verdict == PhotoVerdict.KEEP)
    return {
        "photos": photos,
        "pending_review_ids": pending,
        "messages": [
            {"role": "culling", "content": f"处理 {len(photos)} 张,保留 {kept},待审 {len(pending)}"}
        ],
    }


# --------------------------------------------------------------------------- #
# Critic:对保留的照片生成自然语言点评
# --------------------------------------------------------------------------- #
def critic_node(state: GraphState) -> dict:
    from ..tools.llm import chat as llm_chat

    photos = [p.model_copy(deep=True) for p in state.photos]
    for p in photos:
        if p.verdict == PhotoVerdict.KEEP and p.aesthetic is not None:
            a = p.aesthetic
            weakest = min(
                [("构图", a.composition), ("技术执行", a.technical), ("情感", a.emotion)],
                key=lambda x: x[1],
            )
            # 接豆包 / DeepSeek;失败 / 离线 fallback 到规则文案
            llm_out = llm_chat(
                purpose="critic",
                messages=[
                    {"role": "system", "content":
                        "你是一位资深风光摄影评审,语言克制有洞察。每次回复不超过 80 字。"},
                    {"role": "user", "content":
                        f"照片 EXIF: {p.exif.focal_length_mm}mm f/{p.exif.aperture_f} "
                        f"ISO{p.exif.iso}。8 维评分: overall={a.overall} "
                        f"构图={a.composition} 视觉={a.visual_elements} 技术={a.technical} "
                        f"原创={a.originality} 主题={a.theme} 情感={a.emotion} 格式塔={a.gestalt}。"
                        f"请给一段简短点评 + 一条下次改进建议。"},
                ],
                max_tokens=1024,   # 豆包 thinking 模型 reasoning 占大半,要给足
                temperature=0.6,
            )
            p.critique = llm_out or (
                f"综合 {a.overall}/10。亮点在视觉元素({a.visual_elements})与"
                f"格式塔({a.gestalt})。可提升:{weakest[0]}({weakest[1]})。"
                f"建议下次在 {p.exif.focal_length_mm}mm 焦段尝试调整前景平衡。"
            )
    return {
        "photos": photos,
        "messages": [{"role": "critic", "content": f"已点评 {len(state.kept_photos())} 张精选片"}],
    }


# --------------------------------------------------------------------------- #
# Story:结合 EXIF 时序 + 天气,生成游记 markdown
# --------------------------------------------------------------------------- #
def story_node(state: GraphState) -> dict:
    kept = state.kept_photos()
    hike = state.hike
    if hike.gps_lat is None and kept and kept[0].exif.gps_lat:
        hike = hike.model_copy(
            update={"gps_lat": kept[0].exif.gps_lat, "gps_lon": kept[0].exif.gps_lon}
        )
    weather = (
        clients.fetch_weather(hike.gps_lat, hike.gps_lon)
        if hike.gps_lat is not None
        else "未知"
    )

    lines = [
        f"# {hike.location_name or '一次徒步'}的影像记录",
        "",
        f"天气:{weather}。本次共精选 {len(kept)} 张。",
        "",
    ]
    for i, p in enumerate(kept, 1):
        # photo_id 是 UUID(36 字符)时截短只取头 8 位,看起来像"片段编号"
        pid = p.photo_id
        short_id = pid[:8] if len(pid) >= 32 and "-" in pid else pid
        lines.append(
            f"{i}. `{short_id}` — {p.exif.focal_length_mm}mm "
            f"f/{p.exif.aperture_f} ISO{p.exif.iso}。{p.critique or ''}"
        )
    return {
        "travelogue_md": "\n".join(lines),
        "hike": hike,
        "messages": [{"role": "story", "content": "游记已生成"}],
    }


# --------------------------------------------------------------------------- #
# Planner:为"下次再来同一地点"生成拍摄计划
# --------------------------------------------------------------------------- #
def planner_node(state: GraphState) -> dict:
    hike = state.hike
    # 推荐焦段:从用户保留片里推断偏好,没有就用经典风光焦段
    focal = sorted({p.exif.focal_length_mm for p in state.kept_photos()
                    if p.exif.focal_length_mm}) or [24.0, 35.0, 70.0]

    plan: dict = {
        "recommended_focal_mm": focal,
        "gear_checklist": ["三脚架", "ND 滤镜", "渐变滤镜", "备用电池", "头灯"],
    }

    if hike.gps_lat is not None:
        # 有 GPS:接真实日月 + 天气 API
        times = clients.sun_moon_times(hike.gps_lat, hike.gps_lon, "2026-06-01")
        plan["best_windows"] = [
            times["golden_hour_am"],
            times["golden_hour_pm"],
            times["blue_hour_pm"],
        ]
        plan["weather_note"] = clients.fetch_weather(hike.gps_lat, hike.gps_lon)
        msg = "下次拍摄计划已生成(基于 GPS)"
    else:
        # 无 GPS:按 location_name 给通用建议(不调外部 API)
        plan["best_windows"] = ["日出前 30 min(蓝调时刻)", "日出后 60 min(金色时刻)",
                                "日落前 60 min(金色时刻)"]
        plan["weather_note"] = "建议查询当地天气 APP;阴天云层有戏剧感,晴天利于通透"
        plan["note"] = (f"基于地点「{hike.location_name or '该 trail'}」的通用建议;"
                        f"上传带 GPS 的照片可获得精确日月时刻 + 实时天气")
        msg = "下次拍摄计划已生成(无 GPS,通用建议)"

    return {
        "next_trip_plan": plan,
        "messages": [{"role": "planner", "content": msg}],
    }


# --------------------------------------------------------------------------- #
# HumanReview:HITL 占位 —— 真实部署中此节点会 interrupt 等待前端输入
# --------------------------------------------------------------------------- #
def human_review_node(state: GraphState) -> dict:
    """[STUB] 自动把待审照片按分数裁决。

    [REAL] 用 langgraph 的 interrupt() 挂起,前端展示待审照片,
    用户裁决后 resume。用户的驳回写回 user_pref.rejected_photo_ids,
    实现个性化记忆闭环(PIAA)。
    """
    photos = [p.model_copy(deep=True) for p in state.photos]
    resolved = 0
    for p in photos:
        if p.verdict == PhotoVerdict.REVIEW:
            if p.aesthetic and p.aesthetic.overall >= 6.0:
                p.verdict = PhotoVerdict.KEEP
                action, reason = "human_keep", "auto_promoted_high_score"
            else:
                p.verdict, p.reject_reason = PhotoVerdict.REJECT, "human_rejected"
                action, reason = "human_reject", "low_score_at_review"
            p.decision_trace.append(
                DecisionStep(
                    actor="human_review",
                    action=action,
                    reason=reason,
                    evidence={"overall": p.aesthetic.overall if p.aesthetic else None},
                    at=_now(),
                )
            )
            resolved += 1
    return {
        "photos": photos,
        "pending_review_ids": [],
        "messages": [{"role": "human_review", "content": f"人工裁决 {resolved} 张"}],
    }
