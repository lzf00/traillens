"""导出 OpenAPI spec 到磁盘。

用途:
  - CI 当 artifact 发布(给前端 / 第三方 SDK 生成)
  - openapi-typescript 自动生成 TS client(取代手写 fetch)
  - 公开到 docs.traillens.app/api(类似 stripe.com/docs/api)

用法:
    python scripts/export_openapi.py --out apps/web/lib/api/openapi.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="openapi.json")
    args = ap.parse_args()

    from traillens_api.main import app
    spec = app.openapi()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=2, ensure_ascii=False))
    n_paths = len(spec.get("paths", {}))
    n_schemas = len((spec.get("components") or {}).get("schemas") or {})
    print(f"→ {out} ({n_paths} paths, {n_schemas} schemas)")


if __name__ == "__main__":
    main()
