# traillens-annotation

> 给 LoRA 训练用的轻量人工标注工具(2026 Sprint 2 工具)。
> 不接 React/Next,纯 HTML + 80 行 vanilla JS,**单文件可用**。

## 用法

```bash
# 1. 把要标注的照片放到 packages/annotation/photos/
#    (子目录任意,递归扫描;支持 jpg/jpeg/png)
cp ~/Pictures/landscape/*.jpg packages/annotation/photos/

# 2. (可选)用 GPT-5V 做预打分,生成 prefill.jsonl
python server/gpt_prefill.py photos/  # 需 OPENAI_API_KEY

# 3. 启动标注 server
python server/serve.py
# → 浏览器打开 http://localhost:5555

# 4. 按 1-9 给每个维度打分,按 → 下一张,按 ← 上一张
#    所有标注实时存到 data/annotations.jsonl

# 5. 导出训练 manifest(filter low-confidence + 80/10/10 split)
python server/export_manifest.py
# → 产出 data/{train,val,test}.jsonl,可直接喂给 train_qalign_lora.py
```

## 标注一致性 SOP(参考 RESEARCH.md §3.2)

- **多人独立标 100 张子集** → 算 Krippendorff's α
- α < 0.6 的维度 → 修 rubric,重标
- 自标注前先读完 [`docs/RUBRIC.md`](../../docs/RUBRIC.md)

## 数据格式

```jsonl
{"image": "p001.jpg", "scores": {"overall": 7.5, "composition": 8.0, ...}, "exif": {...}, "annotator": "self", "ts": "2026-05-26T18:00:00Z"}
```
