#!/usr/bin/env bash
# Sprint 2 一键脚本:从"我有一堆风光照"到"训练 manifest 就绪"。
#
# 用法:
#   1. 把照片(jpg/jpeg/png)放到 packages/annotation/photos/
#   2. 跑 bash scripts/sprint2_kickoff.sh
#   3. 浏览器开 http://localhost:5555 标注
#   4. 标完按 Ctrl-C,再跑 bash scripts/sprint2_kickoff.sh --finalize
#
# 中途 Ctrl-C 安全 — 已标的进度保留在 packages/annotation/data/annotations.jsonl
set -euo pipefail
cd "$(dirname "$0")/.."

PHOTOS_DIR="packages/annotation/photos"
DATA_DIR="packages/annotation/data"
mkdir -p "$PHOTOS_DIR" "$DATA_DIR"

FINALIZE=0
if [ "${1:-}" = "--finalize" ]; then FINALIZE=1; fi

# ---------- 0. 检查环境 ----------
echo "──── 0. 环境检查 ────"
python3 -c "import sys; assert sys.version_info >= (3, 10), sys.version" \
  || { echo "✗ Python >= 3.10 required"; exit 1; }
python3 -c "from PIL import Image" 2>/dev/null \
  || { echo "✗ Pillow not installed. 运行: pip install Pillow"; exit 1; }
echo "✓ Python + Pillow OK"

# ---------- 1. 照片清点 ----------
echo ""
echo "──── 1. 照片清点 ────"
COUNT=$(find "$PHOTOS_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l | tr -d ' ')
echo "→ 当前 $PHOTOS_DIR 下有 $COUNT 张照片"
if [ "$COUNT" -lt 10 ]; then
  echo "  ⚠ 太少;我会用 synth_photos 补 30 张合成图先把流水线跑通"
  python3 packages/annotation/server/synth_photos.py --out "$(pwd)/$PHOTOS_DIR" --n 30
  COUNT=$(find "$PHOTOS_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l | tr -d ' ')
  echo "  → 现在 $COUNT 张"
fi

# ---------- 2. EXIF 安全:剥 GPS ----------
echo ""
echo "──── 2. EXIF GPS 隐私剥除 ────"
python3 - <<'PY'
import sys
from pathlib import Path
from PIL import Image, ExifTags

PHOTOS = Path("packages/annotation/photos")
GPS_TAG_ID = next((k for k, v in ExifTags.TAGS.items() if v == "GPSInfo"), None)

stripped = 0
for p in PHOTOS.rglob("*"):
    if p.suffix.lower() not in (".jpg", ".jpeg", ".png"): continue
    try:
        img = Image.open(p)
        exif = img.getexif()
        if GPS_TAG_ID and GPS_TAG_ID in exif:
            del exif[GPS_TAG_ID]
            img.save(p, exif=exif.tobytes() if hasattr(exif, "tobytes") else None)
            stripped += 1
    except Exception as e:
        print(f"  ! skip {p.name}: {e}", file=sys.stderr)
print(f"  → {stripped} 张照片的 GPS 已剥除(其它 EXIF 字段保留)")
PY

# ---------- 3. 预打分 ----------
echo ""
echo "──── 3. AI 预打分(prefill)────"
if [ -n "${OPENAI_API_KEY:-}${ANTHROPIC_API_KEY:-}" ]; then
  echo "→ 检测到 API key,用真实 VLM 预打分"
  python3 packages/annotation/server/gpt_prefill.py "$PHOTOS_DIR"
else
  echo "→ 无 OPENAI_API_KEY / ANTHROPIC_API_KEY,用 stub(确定性)"
  python3 packages/annotation/server/stub_prefill.py "$PHOTOS_DIR"
fi

# ---------- finalize 分支:跳过标注启动,直接出 manifest + α ----------
if [ "$FINALIZE" = "1" ]; then
  echo ""
  echo "──── 4. Finalize: Krippendorff α + export ────"
  if [ ! -f "$DATA_DIR/annotations.jsonl" ]; then
    echo "✗ $DATA_DIR/annotations.jsonl 不存在;还没标注"
    exit 1
  fi
  COUNT_ANNO=$(wc -l < "$DATA_DIR/annotations.jsonl" | tr -d ' ')
  echo "→ 已标 $COUNT_ANNO 条"
  python3 packages/aesthetic/inter_rater.py "$DATA_DIR/annotations.jsonl" || true
  echo ""
  python3 packages/annotation/server/export_manifest.py
  echo ""
  echo "✓ 训练 manifest 就绪:"
  ls -lh "$DATA_DIR"/landscape_*.jsonl
  echo ""
  echo "→ 下一步:"
  echo "    pip install modal && modal token new"
  echo "    modal volume create traillens-data"
  echo "    modal volume put traillens-data $DATA_DIR /"
  echo "    modal volume put traillens-data $PHOTOS_DIR /images"
  echo "    modal run packages/aesthetic/train_modal.py::run --use-exif true"
  exit 0
fi

# ---------- 4. 启标注 server ----------
echo ""
echo "──── 4. 启标注 server ────"
echo "→ 浏览器打开 http://localhost:5555"
echo "→ 标注操作:1-9 给当前维度打分,Tab 下一维度,S 保存,← → 翻页"
echo "→ 中途 Ctrl-C 安全;数据写到 $DATA_DIR/annotations.jsonl"
echo "→ 标完跑: bash scripts/sprint2_kickoff.sh --finalize"
echo ""
cd packages/annotation && exec python3 server/serve.py
