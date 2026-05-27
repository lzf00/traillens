"""美学评分推理服务 — Modal endpoint。

部署:
    modal deploy serve.py
    # → endpoint URL 写入 .env 的 TRAILLENS_AESTHETIC_ENDPOINT

本地测试:
    uvicorn serve:web --reload --port 9000
    curl -X POST localhost:9000/score \\
         -H "Content-Type: application/json" \\
         -d '{"image_url": "https://example.com/test.jpg"}'

设计要点
--------
- 返回 schema 与 traillens_agents.state.schema.AestheticScore 严格对齐(契约 1)。
- Modal 与本地 uvicorn *共用同一 FastAPI app*,避免双实现漂移。
- 模型权重加载在容器 cold-start 时一次性完成,后续推理走 in-memory 模型。
- 推理失败统一返回 status=500 + 错误描述,*不抛出*——agent 端 fallback 友好。
"""

from __future__ import annotations

import os
from typing import Any

# fastapi / pydantic 在无 deps 环境(CI contract-tests job)中不可用 → 优雅降级
try:
    from fastapi import FastAPI, HTTPException
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

    class HTTPException(Exception):  # type: ignore  # 让 raise HTTPException 不崩
        def __init__(self, status_code=500, detail=None):
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

try:
    from pydantic import BaseModel, Field
except ImportError:
    # 极简 stub:只支持本文件用到的字段定义,够单测拿字段名
    class BaseModel:  # type: ignore
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

        def model_dump(self):
            return {k: getattr(self, k) for k in self.__class__.__annotations__}

    def Field(default=None, **kw):  # type: ignore  # noqa: N802
        return default

# --------------------------------------------------------------------------- #
# 1. 输入/输出 schema(与 AestheticScore 对齐)
# --------------------------------------------------------------------------- #
class ScoreRequest(BaseModel):
    image_url: str | None = None
    image_b64: str | None = None  # 大批量时直传 base64 省 R2 一次往返
    exif_hint: dict[str, Any] | None = None  # H2 消融:EXIF 注入


class ScoreResponse(BaseModel):
    overall: float = Field(..., ge=0, le=10)
    composition: float = Field(..., ge=0, le=10)
    visual_elements: float = Field(..., ge=0, le=10)
    technical: float = Field(..., ge=0, le=10)
    originality: float = Field(..., ge=0, le=10)
    theme: float = Field(..., ge=0, le=10)
    emotion: float = Field(..., ge=0, le=10)
    gestalt: float = Field(..., ge=0, le=10)
    confidence: float = Field(default=0.0, ge=0, le=1)
    model_version: str = "qalign-landscape-lora-v0"


# --------------------------------------------------------------------------- #
# 2. 模型加载(cold-start 时)— 当前是 stub
# --------------------------------------------------------------------------- #
_MODEL = None  # 真实实现 = 已加载的 Q-Align + LoRA


def load_model():
    """[TODO] 训练完成后填入真实加载逻辑。

        from transformers import AutoModelForCausalLM
        from peft import PeftModel
        base = AutoModelForCausalLM.from_pretrained("q-future/one-align", torch_dtype=torch.bfloat16)
        model = PeftModel.from_pretrained(base, "runs/qalign-landscape-lora-v0")
        model.eval()
        return model
    """
    return "STUB-MODEL"


def score_image(req: ScoreRequest) -> ScoreResponse:
    """单图推理。

    [STUB] 返回带噪声的固定分数(便于 e2e 调试 + agent 端集成测试)。
    [REAL] 用 _MODEL 推理 → 5 token 期望 → 0-10 → 返回。
    """
    global _MODEL
    if _MODEL is None:
        _MODEL = load_model()

    if not req.image_url and not req.image_b64:
        raise HTTPException(400, "image_url or image_b64 required")

    # 确定性 stub:用 url hash 给一个稳定但看起来真实的分数,
    # 便于前端调试时不要每次刷新分数都跳。
    seed = sum(ord(c) for c in (req.image_url or req.image_b64 or ""))
    base = 4.0 + (seed % 60) / 10.0  # 4.0 - 10.0
    jitter = lambda offset: round(max(0.0, min(10.0, base + (offset % 30 - 15) / 10)), 2)  # noqa: E731

    return ScoreResponse(
        overall=round(base, 2),
        composition=jitter(seed + 1),
        visual_elements=jitter(seed + 2),
        technical=jitter(seed + 3),
        originality=jitter(seed + 4),
        theme=jitter(seed + 5),
        emotion=jitter(seed + 6),
        gestalt=jitter(seed + 7),
        confidence=round(0.6 + (seed % 35) / 100, 2),
        model_version=os.environ.get("MODEL_VERSION", "stub-v0"),
    )


# --------------------------------------------------------------------------- #
# 3. FastAPI app(Modal 与 本地 uvicorn 共用) — 无 fastapi 时 web = None
# --------------------------------------------------------------------------- #
web = FastAPI(title="TrailLens Aesthetic API", version="0.0.1") if HAS_FASTAPI else None


if web is not None:
    @web.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "model_loaded": _MODEL is not None}

    @web.post("/score", response_model=ScoreResponse)
    def score(req: ScoreRequest) -> ScoreResponse:
        return score_image(req)


# --------------------------------------------------------------------------- #
# 4. Modal 部署适配(只在装了 modal 时生效)
# --------------------------------------------------------------------------- #
try:
    import modal  # type: ignore

    image = (
        modal.Image.debian_slim(python_version="3.11")
        .pip_install(
            "fastapi>=0.110",
            "pydantic>=2.7",
            # 真实启用时取消注释:
            # "torch>=2.2", "transformers>=4.40", "peft>=0.10",
            # "pillow>=10", "scipy", "accelerate",
        )
    )

    app = modal.App("traillens-aesthetic")

    @app.function(
        image=image,
        gpu="A10G",          # 训练完成后改为 A10G/A100,当前 stub 不需要
        timeout=300,
        keep_warm=0,         # 零保留,按调用计费
        secrets=[modal.Secret.from_name("traillens-aesthetic")],
    )
    @modal.asgi_app()
    def fastapi_app():
        return web

except ImportError:
    # 本地 dev / 无 modal 包时:web app 仍可被 uvicorn 直接启
    pass
