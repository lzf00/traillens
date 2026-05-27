"""LLM 客户端统一抽象(OpenAI 兼容协议)。

支持的供应商优先级(自动 fallback):
  1. 豆包(火山引擎,DOUBAO_API_KEY) — 国内首选,Critic/Story/Vision 全包
  2. DeepSeek — 纯文本任务的便宜备份
  3. Anthropic Claude — 海外备份
  4. stub — 全部不可用时返回写死文案,保证 demo 不崩

为什么用 OpenAI 兼容协议:
  豆包 / DeepSeek / SiliconFlow / 智谱 / Qwen 全都暴露 OpenAI 兼容 endpoint,
  一个 client 接所有,切换供应商只改 env。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

log = logging.getLogger("traillens.llm")

_STUBS = {
    "critic": "综合 {overall}/10。亮点在视觉元素与格式塔。建议下次尝试调整前景平衡。",
    "story": "今日山行:晨光初现,云雾未散,记录数张影像。后续详细复盘留给下次。",
}


def chat(
    *,
    messages: list[dict[str, Any]],
    purpose: str = "critic",   # critic / story / vision
    max_tokens: int = 512,
    temperature: float = 0.7,
) -> str:
    """统一聊天入口,返回 assistant 文本(已剥外层 JSON)。"""
    if os.environ.get("TRAILLENS_USE_STUBS") == "1":
        return _STUBS.get(purpose, "")

    for fn in (_chat_doubao, _chat_deepseek, _chat_anthropic):
        try:
            out = fn(messages, purpose, max_tokens, temperature)
            if out:
                return out
        except Exception as e:  # noqa: BLE001
            log.warning("%s failed: %s", fn.__name__, e)

    log.warning("all LLM providers failed; returning stub for %s", purpose)
    return _STUBS.get(purpose, "")


# --------------------------------------------------------------------------- #
# 豆包(火山引擎)— OpenAI 兼容
# --------------------------------------------------------------------------- #
def _chat_doubao(messages, purpose, max_tokens, temperature):
    key = os.environ.get("DOUBAO_API_KEY")
    if not key:
        return None
    base = os.environ.get("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    if purpose == "vision":
        endpoint = os.environ.get("DOUBAO_VISION_ENDPOINT", "")
    else:
        endpoint = os.environ.get("DOUBAO_TEXT_ENDPOINT", "")
    if not endpoint:
        return None

    try:
        import httpx
    except ImportError:
        return None

    r = httpx.post(
        f"{base}/chat/completions",
        json={
            "model": endpoint,        # 火山引擎用"推理接入点 ID"作 model
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# --------------------------------------------------------------------------- #
# DeepSeek
# --------------------------------------------------------------------------- #
def _chat_deepseek(messages, purpose, max_tokens, temperature):
    if purpose == "vision":   # DeepSeek 暂无 vision
        return None
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    try:
        import httpx
    except ImportError:
        return None
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    r = httpx.post(
        "https://api.deepseek.com/v1/chat/completions",
        json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature},
        headers={"Authorization": f"Bearer {key}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# --------------------------------------------------------------------------- #
# Anthropic Claude(海外备份)
# --------------------------------------------------------------------------- #
def _chat_anthropic(messages, purpose, max_tokens, temperature):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import httpx
    except ImportError:
        return None
    # Anthropic 协议略不同,system 消息要单拎
    system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
    chat_messages = [m for m in messages if m["role"] != "system"]
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        json={
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7"),
            "max_tokens": max_tokens,
            "system": system_msg,
            "messages": chat_messages,
        },
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"]
