"""TrailLens 多智能体共享状态定义。

设计要点
--------
1. State 是整个 LangGraph 图的"单一事实来源"(single source of truth)。
   每个节点读取 state、返回 *部分* 更新(partial update),由 reducer 合并。
2. 用 Pydantic v2 BaseModel 做强类型契约 —— 这是面试时"工程成熟度"的直接信号,
   也方便后续直接复用为 FastAPI 的 response_model。
3. 与 README/ARCHITECTURE.md 中的 5 节点架构严格对应:
   Orchestrator -> Culling -> Critic -> Story -> Planner
   这个对应关系是三块交付物"融会贯通"的关键锚点。

依赖: langgraph>=0.2, pydantic>=2.7
"""

from __future__ import annotations

import operator
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

# --------------------------------------------------------------------------- #
# 兼容层:优先用 pydantic v2;无 pydantic 时降级到 dataclass。
# 生产环境务必安装 pydantic(强校验 + FastAPI 复用);此降级仅为零依赖 demo。
# --------------------------------------------------------------------------- #
try:
    from pydantic import BaseModel, ConfigDict, Field  # type: ignore

    _HAS_PYDANTIC = True
except ImportError:  # pragma: no cover - fallback path
    _HAS_PYDANTIC = False
    import dataclasses
    from dataclasses import dataclass, field as _dc_field

    def Field(default=None, default_factory=None, **_kwargs):  # noqa: N802
        """最小化的 Field 垫片,忽略校验参数(ge/le/description 等)。"""
        if default_factory is not None:
            return _dc_field(default_factory=default_factory)
        if isinstance(default, (list, dict, set)):
            return _dc_field(default_factory=lambda d=default: type(d)(d))
        return default

    def ConfigDict(**_kwargs):  # noqa: N802
        """无 pydantic 时的占位,什么也不做。"""
        return {}

    class _Meta(type):
        def __new__(mcs, name, bases, ns):
            cls = super().__new__(mcs, name, bases, ns)
            return dataclass(cls) if name != "BaseModel" else cls

    class BaseModel(metaclass=_Meta):  # type: ignore
        def model_dump(self, exclude_none: bool = False, **_):
            out = {}
            for f in dataclasses.fields(self):
                v = getattr(self, f.name)
                if exclude_none and v is None:
                    continue
                out[f.name] = v
            return out

        def model_copy(self, update: dict | None = None, deep: bool = False):
            import copy

            new = copy.deepcopy(self) if deep else copy.copy(self)
            for k, v in (update or {}).items():
                setattr(new, k, v)
            return new


# --------------------------------------------------------------------------- #
# 枚举与原子结构
# --------------------------------------------------------------------------- #
class PhotoVerdict(str, Enum):
    """Culling 节点对单张照片的处置决定。"""

    KEEP = "keep"
    REJECT = "reject"
    REVIEW = "review"  # 介于之间,交人工(HITL)裁决


class AestheticScore(BaseModel):
    """美学评分模型的结构化输出。

    *** 这是与第二块(美学微调方案)的接口契约 ***
    微调产出的模型推理服务必须返回这个 schema,否则 Critic 节点无法消费。
    8 个维度对齐 ArtiMuse 的细粒度评估体系。
    """

    overall: float = Field(..., ge=0, le=10, description="综合美学分 0-10")
    composition: float = Field(..., ge=0, le=10, description="构图")
    visual_elements: float = Field(..., ge=0, le=10, description="视觉元素")
    technical: float = Field(..., ge=0, le=10, description="技术执行(曝光/对焦/噪点)")
    originality: float = Field(..., ge=0, le=10, description="原创性")
    theme: float = Field(..., ge=0, le=10, description="主题表达")
    emotion: float = Field(..., ge=0, le=10, description="情感")
    gestalt: float = Field(..., ge=0, le=10, description="整体格式塔")
    # 模型置信度,用于 Orchestrator 决定是否走 REVIEW 分支
    confidence: float = Field(default=0.0, ge=0, le=1)
    model_version: str = Field(default="qalign-landscape-lora-v0")


class ExifMeta(BaseModel):
    """从 EXIF MCP server 解析出的关键元数据(精简版)。

    允许 extra 字段:_tech_metrics(上传时 cv2 算的 blur/exposure/dhash)等扩展信息
    透过 model_extra 访问,detect_technical_defects 用。
    """

    model_config = ConfigDict(extra="allow")

    focal_length_mm: float | None = None
    aperture_f: float | None = None
    iso: int | None = None
    shutter: str | None = None
    captured_at: datetime | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    camera_model: str | None = None


class DecisionStep(BaseModel):
    """单步决策痕迹。前端按时间线渲染"为什么留/拒"。

    每一步对应"哪个节点 / 用什么判据 / 得到什么结论"。
    *** 与前端 §3.1 M4 Auditable Decisions 模式直接对接 ***
    """

    actor: str  # 节点名:culling / human_review / critic ...
    action: str  # 简短结论:keep / reject / review / critique_generated ...
    reason: str | None = None  # 人类可读理由
    evidence: dict[str, Any] = Field(default_factory=dict)  # 数值/分数等结构化证据
    at: datetime | None = None  # 时间戳,前端时间线用


class Photo(BaseModel):
    """流经整个 pipeline 的照片对象。"""

    photo_id: str
    uri: str  # R2/B2 对象存储 URL 或本地路径
    exif: ExifMeta = Field(default_factory=ExifMeta)
    # 由 Culling 节点填充
    verdict: PhotoVerdict | None = None
    reject_reason: str | None = None  # blur / closed_eyes / duplicate / over_exposed ...
    # 由美学模型填充
    aesthetic: AestheticScore | None = None
    # 由 Critic 节点填充(自然语言点评)
    critique: str | None = None
    embedding_id: str | None = None  # pgvector 中的 id,供 RAG 检索
    # 决策审计:每个节点写一条,前端可视化为时间线(§3.1 M4)
    decision_trace: list[DecisionStep] = Field(default_factory=list)


class HikeContext(BaseModel):
    """一次徒步的上下文,由 Story / Planner 节点消费。"""

    gpx_uri: str | None = None
    location_name: str | None = None
    distance_km: float | None = None
    elevation_gain_m: float | None = None
    date: datetime | None = None
    weather_summary: str | None = None  # 由 weather MCP server 回填
    # GPS:Story/Planner 节点据此调天气与天文 MCP;通常从首张照片 EXIF 回填
    gps_lat: float | None = None
    gps_lon: float | None = None


class UserPreference(BaseModel):
    """个性化记忆(Mem0/pgvector 回灌)。

    支撑 PIAA(个性化美学评估)。HITL 中用户驳回选片时,
    反馈写回这里,实现"个人风格助理"而非"客观评分"的定位。
    """

    favorite_focal_lengths: list[float] = Field(default_factory=list)
    style_keywords: list[str] = Field(default_factory=list)  # e.g. ["moody", "high-contrast"]
    rejected_photo_ids: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# 顶层 GraphState
# --------------------------------------------------------------------------- #
class GraphState(BaseModel):
    """LangGraph 全局状态。

    reducer 说明
    -----------
    - `photos` 用自定义 merge(按 photo_id 覆盖),因为不同节点会增量补字段。
    - `messages` / `errors` 用 operator.add 追加。
    - 标量字段(next_agent 等)默认"后写覆盖"。
    """

    # 路由控制
    next_agent: Literal[
        "culling", "critic", "story", "planner", "human_review", "FINISH"
    ] | None = None
    # 业务数据
    photos: list[Photo] = Field(default_factory=list)
    hike: HikeContext = Field(default_factory=HikeContext)
    user_pref: UserPreference = Field(default_factory=UserPreference)
    # 产出
    travelogue_md: str | None = None  # Story 节点产出的游记
    next_trip_plan: dict[str, Any] | None = None  # Planner 节点产出
    # 运行时
    messages: Annotated[list[dict], operator.add] = Field(default_factory=list)
    errors: Annotated[list[str], operator.add] = Field(default_factory=list)
    # HITL: 当 Culling 把某些照片标 REVIEW 时,这里挂起等人工
    pending_review_ids: list[str] = Field(default_factory=list)
    # 运行串联与计费(§4.2 agent_runs 表)
    run_id: str | None = None
    quota_used: int = 0  # 本次 run 已消耗的额度;由 middleware 在超额时 raise

    def kept_photos(self) -> list[Photo]:
        return [p for p in self.photos if p.verdict == PhotoVerdict.KEEP]

    def merge_photo_updates(self, updates: list[Photo]) -> list[Photo]:
        """按 photo_id 合并增量更新(供节点内部使用)。"""
        index = {p.photo_id: p for p in self.photos}
        for u in updates:
            if u.photo_id in index:
                merged = index[u.photo_id].model_copy(
                    update=u.model_dump(exclude_none=True)
                )
                index[u.photo_id] = merged
            else:
                index[u.photo_id] = u
        return list(index.values())
