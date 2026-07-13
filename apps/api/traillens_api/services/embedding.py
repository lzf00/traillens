"""文本 embedding — 调 Doubao(Volcengine Ark)兼容 OpenAI embeddings 接口。

设计:
- 复用 ARK_API_KEY / ARK_BASE_URL,不引入新凭证
- 用 dimensions=768 适配 photos.embedding 现有 vector(768) 列
- 失败返回 None,调用方自己 fallback (search 时降级 ILIKE)
"""

from __future__ import annotations

import os
from typing import Iterable

DIM = 768  # 对齐 photos.embedding vector(768)
_DEFAULT_MODEL = "doubao-embedding-text-240715"
# Doubao 模型 dimensions 参数实际被忽略,返回完整 2560d;
# 我们截断到 DIM 再 L2-normalize(精度损失小,常规做法)


def _truncate_normalize(vec):
    import math
    v = vec[:DIM] if len(vec) > DIM else vec + [0.0] * (DIM - len(vec))
    s = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / s for x in v]


def _client():
    api_key = os.environ.get("ARK_API_KEY") or os.environ.get("DOUBAO_API_KEY")
    if not api_key:
        return None
    base_url = (
        os.environ.get("ARK_BASE_URL")
        or os.environ.get("DOUBAO_BASE_URL")
        or "https://ark.cn-beijing.volces.com/api/v3"
    )
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None
    # 与 llm.py 一致的 timeout + retry:防 SDK 默认 600s hang
    return OpenAI(
        api_key=api_key, base_url=base_url,
        timeout=float(os.environ.get("DOUBAO_TIMEOUT", "30")),
        max_retries=int(os.environ.get("DOUBAO_MAX_RETRIES", "2")),
    )


def embed_text(text: str) -> list[float] | None:
    """单条文本 → 768d vector。"""
    if not text or not text.strip():
        return None
    c = _client()
    if not c:
        return None
    model = os.environ.get("DOUBAO_MODEL_EMBED", _DEFAULT_MODEL)
    try:
        resp = c.embeddings.create(model=model, input=text.strip())
        return _truncate_normalize(list(resp.data[0].embedding))
    except Exception:  # noqa: BLE001
        return None


def embed_batch(texts: Iterable[str]) -> list[list[float] | None]:
    """批量 embedding(一次请求多条);失败时该位置返回 None。"""
    items = [t.strip() if t else "" for t in texts]
    nonempty_idx = [i for i, t in enumerate(items) if t]
    if not nonempty_idx:
        return [None] * len(items)
    c = _client()
    if not c:
        return [None] * len(items)
    model = os.environ.get("DOUBAO_MODEL_EMBED", _DEFAULT_MODEL)
    try:
        resp = c.embeddings.create(
            model=model,
            input=[items[i] for i in nonempty_idx],
        )
        vecs: list[list[float] | None] = [None] * len(items)
        for src, d in zip(nonempty_idx, resp.data):
            vecs[src] = _truncate_normalize(list(d.embedding))
        return vecs
    except Exception:  # noqa: BLE001
        return [None] * len(items)
