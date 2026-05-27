"""HuggingFace Space — Landscape Aesthetic Scoring 公开 demo。

部署:
  1. 在 HF 建 Space → SDK = Gradio
  2. 把本目录 push 到 Space repo(`git push hf main`)
  3. (Sprint 3 末)在 Settings → Variables 加 MODEL_REPO=traillens/qalign-landscape-lora-v0
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import gradio as gr

DIMS = [
    ("overall", "综合"),
    ("composition", "构图"),
    ("visual_elements", "视觉元素"),
    ("technical", "技术执行"),
    ("originality", "原创性"),
    ("theme", "主题"),
    ("emotion", "情感"),
    ("gestalt", "格式塔"),
]

EXAMPLE_DESCRIPTION = """
**Drop a landscape photograph** → get 8-dim aesthetic breakdown.

Backbone: Q-Align + landscape LoRA · License: CC BY-NC 4.0
"""


def _load_model():
    """Sprint 3 末把这个换成真实加载:
        from transformers import AutoModelForCausalLM
        from peft import PeftModel
        base = AutoModelForCausalLM.from_pretrained("q-future/one-align", torch_dtype=torch.bfloat16)
        return PeftModel.from_pretrained(base, os.environ["MODEL_REPO"])
    """
    return None


_MODEL = None


def score(image):
    """主推理函数。Gradio 把上传的图传成 PIL.Image。"""
    global _MODEL
    if _MODEL is None:
        _MODEL = _load_model()

    if image is None:
        return {label: 0.0 for _, label in DIMS}, "请上传一张照片"

    # ---- STUB:跟 serve.py 一致的确定性算法,便于 Space 一上线就能演示 ----
    seed = sum(image.size) + (image.getpixel((0, 0))[0] if image.mode == "RGB" else 0)
    base = 4.0 + (seed % 60) / 10.0
    scores = {label: round(min(10, max(0, base + ((seed + i) % 30 - 15) / 10)), 2)
              for i, (_, label) in enumerate(DIMS)}

    rationale = _format_rationale(scores)
    return scores, rationale


def _format_rationale(scores: dict[str, float]) -> str:
    items = sorted(scores.items(), key=lambda x: -x[1])
    top = items[:2]
    bottom = items[-2:]
    return (
        f"**亮点**: {', '.join(f'{k}({v})' for k, v in top)}\n\n"
        f"**可提升**: {', '.join(f'{k}({v})' for k, v in bottom)}\n\n"
        f"_(此为 stub 输出 — 真实 LoRA 权重 Sprint 3 末上线)_"
    )


with gr.Blocks(theme=gr.themes.Soft(primary_hue="emerald"), title="TrailLens — Aesthetic Scoring") as demo:
    gr.Markdown("# TrailLens — Landscape Aesthetic Scoring")
    gr.Markdown(EXAMPLE_DESCRIPTION)

    with gr.Row():
        with gr.Column(scale=1):
            img = gr.Image(type="pil", label="上传一张风光照(JPG/PNG)")
            btn = gr.Button("评分", variant="primary")
        with gr.Column(scale=1):
            scores_out = gr.Label(num_top_classes=8, label="8 维评分")
            rationale_out = gr.Markdown()

    btn.click(score, inputs=img, outputs=[scores_out, rationale_out])

    gr.Markdown("""
---
### 限制与声明
- **本模型带有训练数据的风格偏好**,定位为"个人风格助理",而非客观评分
- 偏向传统风光美学(Outdoor Photographer / National Geographic 风),
  对实验性 / 后现代 / AI-generated 风格判断会失准
- 想要个性化(PIAA)?用完整版 [traillens.zorotreeking.online](https://traillens.zorotreeking.online)
""")


if __name__ == "__main__":
    demo.launch()
