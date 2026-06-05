"""LLM 客户端 — 豆包(火山引擎)默认,DeepSeek / Claude fallback。

设计要点
--------
- 豆包用**新的 OpenAI Responses API**(`client.responses.create`),不是 chat.completions
  · 直接传模型 ID(如 `doubao-seed-2-0-pro-260215`),不再依赖"推理接入点 ID"
  · 视觉输入直接传 `input_image` + `input_text`,无需 base64 编码本地图
  · 参考: https://www.volcengine.com/docs/82379/1399008
- DeepSeek / Claude 仍用 chat.completions(兼容性广)
- 全部第三方 SDK try/except — 没装也能 import,fallback 到 stub 文案
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("traillens.llm")

_STUBS = {
    "critic": "综合 {overall}/10。亮点在视觉元素与格式塔。建议下次尝试调整前景平衡。",
    "story": "今日山行:晨光初现,云雾未散,记录数张影像。后续详细复盘留给下次。",
    "vision": "[stub] 一张风光照,无法在 stub 模式下做视觉理解。",
}


# --------------------------------------------------------------------------- #
# 公共入口
# --------------------------------------------------------------------------- #
def chat(
    *,
    messages: list[dict] | None = None,
    image_url: str | None = None,
    text: str | None = None,
    purpose: str = "critic",
    max_tokens: int = 1024,   # 豆包 thinking 模型 reasoning 占一半,默认要大
    temperature: float = 0.7,
) -> str:
    """统一聊天入口。

    两种用法:
    1) 纯文本 / 多轮对话:
         chat(messages=[{"role":"user","content":"..."}], purpose="critic")
    2) 视觉(豆包多模态):
         chat(image_url="https://...", text="你看见了什么?", purpose="vision")
    """
    if os.environ.get("TRAILLENS_USE_STUBS") == "1":
        return _STUBS.get(purpose, "")

    for fn in (_chat_doubao, _chat_deepseek, _chat_anthropic):
        try:
            out = fn(messages, image_url, text, purpose, max_tokens, temperature)
            if out:
                return out
        except Exception as e:  # noqa: BLE001
            log.warning("%s failed: %s", fn.__name__, e)

    log.warning("all LLM providers failed; returning stub for %s", purpose)
    return _STUBS.get(purpose, "")


# --------------------------------------------------------------------------- #
# 豆包 — OpenAI SDK + Responses API
# --------------------------------------------------------------------------- #
def _chat_doubao(messages, image_url, text, purpose, max_tokens, temperature):
    """优先用官方 openai SDK 调豆包 Responses API。无 openai 时降级 httpx。

    模型选择:
      vision/critic → doubao-seed-2-0-pro-260215 (多模态强推理)
      story         → doubao-seed-1-6-thinking-250715 (纯文本长上下文)
    """
    # 接受两套命名(ARK_* 是官方推荐,DOUBAO_* 是早期文档遗留)
    api_key = os.environ.get("ARK_API_KEY") or os.environ.get("DOUBAO_API_KEY")
    if not api_key:
        return None

    base_url = (
        os.environ.get("ARK_BASE_URL")
        or os.environ.get("DOUBAO_BASE_URL")
        or "https://ark.cn-beijing.volces.com/api/v3"
    )
    model = _doubao_model(purpose)
    inputs = _build_doubao_input(messages, image_url, text)

    # 优先 openai SDK(用户示例形态)
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return _chat_doubao_via_httpx(api_key, base_url, model, inputs, max_tokens, temperature)

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.responses.create(
        model=model,
        input=inputs,
        max_output_tokens=max_tokens,
        temperature=temperature,
    )
    text_out = getattr(resp, "output_text", None)
    if text_out:
        return text_out
    # 兜底:从 output 列表里拼第一个 text
    for item in getattr(resp, "output", []) or []:
        for c in getattr(item, "content", []) or []:
            if getattr(c, "type", None) == "output_text":
                return c.text
    return None


def _doubao_model(purpose: str) -> str:
    """按用途选模型 — 可被 env 覆盖。"""
    if purpose in ("vision", "critic"):
        return os.environ.get("DOUBAO_MODEL_VISION", "doubao-seed-2-0-pro-260215")
    return os.environ.get("DOUBAO_MODEL_TEXT", "doubao-seed-1-6-thinking-250715")


def _build_doubao_input(messages, image_url, text):
    """构造 Responses API 的 input 数组。"""
    if image_url:
        # 视觉模式 — 与用户给的示例完全一致
        return [{
            "role": "user",
            "content": [
                {"type": "input_image", "image_url": image_url},
                {"type": "input_text", "text": text or "请描述这张照片。"},
            ],
        }]
    # 文本模式 — 把 chat.completions 的 messages 转成 Responses 的 input_text
    out = []
    for m in messages or []:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, str):
            out.append({"role": role, "content": [{"type": "input_text", "text": content}]})
        else:
            out.append({"role": role, "content": content})
    return out


def _chat_doubao_via_httpx(api_key, base_url, model, inputs, max_tokens, temperature):
    """无 openai SDK 时用 httpx 调同一 Responses endpoint。"""
    try:
        import httpx
    except ImportError:
        return None
    r = httpx.post(
        f"{base_url.rstrip('/')}/responses",
        json={
            "model": model, "input": inputs,
            "max_output_tokens": max_tokens, "temperature": temperature,
        },
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("output_text"):
        return data["output_text"]
    for item in data.get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                return c.get("text")
    return None


# --------------------------------------------------------------------------- #
# DeepSeek(纯文本备份)
# --------------------------------------------------------------------------- #
def _chat_deepseek(messages, image_url, text, purpose, max_tokens, temperature):
    if image_url or not messages:    # DeepSeek 暂无 vision
        return None
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    try:
        import httpx
    except ImportError:
        return None
    r = httpx.post(
        "https://api.deepseek.com/v1/chat/completions",
        json={
            "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature,
        },
        headers={"Authorization": f"Bearer {key}"},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# --------------------------------------------------------------------------- #
# Anthropic Claude(海外备份)
# --------------------------------------------------------------------------- #
def _chat_anthropic(messages, image_url, text, purpose, max_tokens, temperature):
    if image_url or not messages:
        return None
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import httpx
    except ImportError:
        return None
    system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
    chat_messages = [m for m in messages if m["role"] != "system"]
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        json={
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7"),
            "max_tokens": max_tokens, "system": system_msg, "messages": chat_messages,
        },
        headers={
            "x-api-key": key, "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"]
