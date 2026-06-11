"""用豆包视觉模型给一批照片做 8 维预打分。

输出 prefill.jsonl,标注工具前端会读它作为初值,
把"从 5.0 起步"变成"从 AI 预测起步",平均节省 60% 标注时间。

用法:
    python doubao_prefill.py photos/
    # 或者通过 sprint2 自动调用
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

**只回复一段严格的 JSON**(不要任何 markdown 代码块、不要解释、不要前后缀文字)。示例:
{"overall": 7.2, "composition": 8.0, "visual_elements": 6.5, "technical": 7.0, "originality": 6.8, "theme": 7.5, "emotion": 7.0, "gestalt": 7.2}
"""


def _image_to_data_uri(path: Path) -> str:
    """本地图转 base64 data URI(豆包 input_image 支持)。"""
    suffix = path.suffix.lower()
    mime = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
    }.get(suffix, "image/jpeg")
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def _score_one(image_path: Path) -> dict | None:
    """单张照片调豆包,返回 8 维分数 dict 或 None。"""
    api_key = os.environ.get("ARK_API_KEY") or os.environ.get("DOUBAO_API_KEY")
    if not api_key:
        print("✗ 缺 ARK_API_KEY / DOUBAO_API_KEY", file=sys.stderr)
        return None

    base_url = (
        os.environ.get("ARK_BASE_URL")
        or os.environ.get("DOUBAO_BASE_URL")
        or "https://ark.cn-beijing.volces.com/api/v3"
    )
    model = os.environ.get("DOUBAO_MODEL_VISION", "doubao-seed-2-0-pro-260215")
    image_data_uri = _image_to_data_uri(image_path)
    payload = {
        "model": model,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_image", "image_url": image_data_uri},
                {"type": "input_text", "text": PROMPT},
            ],
        }],
        "max_output_tokens": 2048,
        "temperature": 0.3,
    }

    text = None

    # 路径 A:openai SDK(若装了)
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.responses.create(**payload)
        text = getattr(resp, "output_text", None)
        if not text:
            for item in getattr(resp, "output", []) or []:
                for c in getattr(item, "content", []) or []:
                    if getattr(c, "type", None) == "output_text":
                        text = c.text
                        break
    except ImportError:
        # 路径 B:httpx 直调
        try:
            import httpx
        except ImportError:
            print("✗ 缺包: pip install httpx 或 openai", file=sys.stderr)
            return None
        try:
            r = httpx.post(
                f"{base_url.rstrip('/')}/responses",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
            text = data.get("output_text")
            if not text:
                for item in data.get("output", []):
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            text = c.get("text")
                            break
        except Exception as e:  # noqa: BLE001
            print(f"  ! {image_path.name} 网络错误: {type(e).__name__}: {str(e)[:120]}",
                  file=sys.stderr)
            return None
    except Exception as e:  # noqa: BLE001
        print(f"  ! {image_path.name} API 错误: {type(e).__name__}: {str(e)[:120]}",
              file=sys.stderr)
        return None

    if not text:
        print("    (空回复)", file=sys.stderr)
        return None

    # 容错:有时豆包仍带 ```json``` 代码块,提取 JSON 段
    import re
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None

    try:
        scores = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None

    return {d: max(0.0, min(10.0, float(scores.get(d, 5)))) for d in DIMS}


def main():
    if len(sys.argv) != 2:
        print("用法: doubao_prefill.py <photos_dir>", file=sys.stderr)
        sys.exit(1)

    folder = Path(sys.argv[1]).resolve()
    photos_root = (Path(__file__).resolve().parents[1] / "photos").resolve()
    out_dir = Path(__file__).resolve().parents[1] / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "prefill.jsonl"

    photos = sorted(p for p in folder.rglob("*")
                    if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    print(f"  → {len(photos)} 张照片待预打分")
    print(f"  → 豆包模型: {os.environ.get('DOUBAO_MODEL_VISION', 'doubao-seed-2-0-pro-260215')}")
    print(f"  → 估计成本: ¥{len(photos) * 0.02:.2f}(每张约 ¥0.02)")
    print()

    success, failed = 0, 0
    with out.open("w", encoding="utf-8") as f:
        for i, p in enumerate(photos, 1):
            print(f"  [{i}/{len(photos)}] {p.name} ", end="", flush=True)
            scores = _score_one(p)
            if scores is None:
                print("✗")
                failed += 1
                continue
            try:
                rel = str(p.relative_to(photos_root))
            except ValueError:
                rel = p.name
            f.write(json.dumps({
                "image": rel, "scores": scores, "source": "doubao",
            }, ensure_ascii=False) + "\n")
            print(f"✓ overall={scores['overall']}")
            success += 1

    print()
    print(f"  ✓ {success} 张成功 / ✗ {failed} 张失败")
    print(f"  → 预打分写到: {out}")


if __name__ == "__main__":
    main()
