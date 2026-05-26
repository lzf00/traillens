"""用 GPT-5V(或 Claude Opus 4.7)给一批照片做 8 维预打分。

输出 prefill.jsonl,标注工具前端会读它作为初值,把"从 5.0 起步"变成"从 AI 预测起步",
平均节省 60% 标注时间(参考 RESEARCH §3.2 标注 SOP)。

用法:
    export OPENAI_API_KEY=sk-...
    # 或 export ANTHROPIC_API_KEY=sk-ant-...
    python gpt_prefill.py photos/
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

# 8 维 schema 必须与 AestheticScore 对齐(契约 1)
DIMS = (
    "overall", "composition", "visual_elements", "technical",
    "originality", "theme", "emotion", "gestalt",
)

PROMPT = """你是一位资深风光摄影评审。请对这张照片在 8 个维度上各打 0-10 分(可带 1 位小数):

- overall: 综合美学
- composition: 构图(三分法 / 引导线 / 平衡 / 前景中景后景)
- visual_elements: 视觉元素(光线 / 色彩 / 形状)
- technical: 技术执行(曝光 / 对焦 / 噪点 / 锐度)
- originality: 原创性 / 独特视角
- theme: 主题表达力
- emotion: 情绪 / 氛围
- gestalt: 整体格式塔

只回复严格的 JSON,不要任何解释。示例:
{"overall": 7.2, "composition": 8.0, "visual_elements": 6.5, ...}
"""


def _list(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*")
                  if p.suffix.lower() in {".jpg", ".jpeg", ".png"})


def _img_b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


def _score_openai(p: Path) -> dict | None:
    try:
        import httpx
    except ImportError:
        print("pip install httpx", file=sys.stderr)
        return None
    key = os.environ["OPENAI_API_KEY"]
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-5-vision-preview"),
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_img_b64(p)}"}},
            ],
        }],
        "max_tokens": 200,
        "response_format": {"type": "json_object"},
    }
    r = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        json=payload, timeout=60,
        headers={"Authorization": f"Bearer {key}"},
    )
    if r.status_code != 200:
        print(f"  ! {p.name} HTTP {r.status_code}: {r.text[:120]}", file=sys.stderr)
        return None
    text = r.json()["choices"][0]["message"]["content"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _score_anthropic(p: Path) -> dict | None:
    try:
        import httpx
    except ImportError:
        return None
    key = os.environ["ANTHROPIC_API_KEY"]
    payload = {
        "model": os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7"),
        "max_tokens": 200,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": _img_b64(p)}},
                {"type": "text", "text": PROMPT + "\n\n直接给 JSON,不要 markdown 代码块。"},
            ],
        }],
    }
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        json=payload, timeout=60,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    if r.status_code != 200:
        print(f"  ! {p.name} HTTP {r.status_code}", file=sys.stderr)
        return None
    text = r.json()["content"][0]["text"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 兜底:去掉 markdown 代码块
        import re
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try: return json.loads(m.group(0))
            except json.JSONDecodeError: pass
        return None


def main():
    if len(sys.argv) != 2:
        print("usage: gpt_prefill.py <photos_dir>", file=sys.stderr); sys.exit(1)
    folder = Path(sys.argv[1])
    photos_root = Path(__file__).resolve().parents[1] / "photos"
    out = Path(__file__).resolve().parents[1] / "data" / "prefill.jsonl"
    out.parent.mkdir(exist_ok=True)

    scorer = _score_anthropic if os.environ.get("ANTHROPIC_API_KEY") else _score_openai
    print(f"scorer = {scorer.__name__}, out = {out}")

    photos = _list(folder)
    print(f"  {len(photos)} images to score")
    with out.open("w") as f:
        for i, p in enumerate(photos, 1):
            scores = scorer(p)
            if not scores:
                continue
            # 只留 8 维 + 截断到 0-10
            clean = {d: max(0, min(10, float(scores.get(d, 5)))) for d in DIMS}
            try:
                rel = str(p.relative_to(photos_root))
            except ValueError:
                rel = p.name
            f.write(json.dumps({"image": rel, "scores": clean, "source": scorer.__name__}, ensure_ascii=False) + "\n")
            print(f"  [{i}/{len(photos)}] {p.name} overall={clean['overall']}")


if __name__ == "__main__":
    main()
