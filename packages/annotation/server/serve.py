"""极简标注 server。

设计原则:
- 不引入 fastapi / flask,只用 Python stdlib(http.server),保证零安装即用。
- 标注实时 append 到 JSONL(每行一条),崩溃不丢数据。
- GPT-5V 预打分如果存在(prefill.jsonl),前端用它作初值;否则空白。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
PHOTOS = ROOT / "photos"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
ANNOT_FILE = DATA / "annotations.jsonl"
PREFILL_FILE = DATA / "prefill.jsonl"

DIMS = (
    "overall", "composition", "visual_elements", "technical",
    "originality", "theme", "emotion", "gestalt",
)


def _list_photos() -> list[str]:
    if not PHOTOS.exists():
        return []
    return sorted(
        str(p.relative_to(PHOTOS))
        for p in PHOTOS.rglob("*")
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )


def _load_prefill() -> dict[str, dict]:
    if not PREFILL_FILE.exists():
        return {}
    out = {}
    for line in PREFILL_FILE.read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["image"]] = d.get("scores", {})
    return out


def _existing_annotations() -> dict[str, dict]:
    """每张照片取最新一条标注。"""
    if not ANNOT_FILE.exists():
        return {}
    out = {}
    for line in ANNOT_FILE.read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["image"]] = d
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 静默
        return

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/" or u.path == "/index.html":
            self._send(200, "text/html; charset=utf-8", (ROOT / "static/index.html").read_bytes())
        elif u.path == "/api/state":
            photos = _list_photos()
            payload = {
                "photos": photos,
                "dims": DIMS,
                "prefill": _load_prefill(),
                "existing": _existing_annotations(),
                "progress": len(_existing_annotations()),
            }
            self._send(200, "application/json", json.dumps(payload).encode())
        elif u.path.startswith("/photos/"):
            # 中文文件名是 URL percent-encoded,需要 unquote 才能找到文件
            from urllib.parse import unquote
            rel = unquote(u.path[len("/photos/"):])
            if ".." in rel:
                self._send(400, "text/plain", b"bad path")
                return
            p = PHOTOS / rel
            if not p.exists():
                self._send(404, "text/plain", b"not found")
                return
            mime = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
            self._send(200, mime, p.read_bytes())
        else:
            self._send(404, "text/plain", b"404")

    def do_POST(self):
        if self.path != "/api/annotate":
            self._send(404, "text/plain", b"404")
            return
        n = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(n))
        # 验证
        if not body.get("image"):
            self._send(400, "text/plain", b"image required")
            return
        for d in DIMS:
            v = body.get("scores", {}).get(d)
            if v is None or not (0 <= float(v) <= 10):
                self._send(400, "text/plain", f"bad score for {d}".encode())
                return
        body["ts"] = datetime.now(timezone.utc).isoformat()
        body.setdefault("annotator", "self")
        with ANNOT_FILE.open("a") as f:
            f.write(json.dumps(body, ensure_ascii=False) + "\n")
        self._send(200, "application/json", b'{"ok":true}')

    def _send(self, status, mime, body):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"→ photos dir : {PHOTOS}")
    print(f"→ data dir   : {DATA}")
    print(f"→ annotations: {ANNOT_FILE}")
    print(f"→ open       : http://localhost:5555")
    ThreadingHTTPServer(("127.0.0.1", 5555), Handler).serve_forever()
