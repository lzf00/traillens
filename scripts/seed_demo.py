"""一键 seed demo 数据 — 给新部署 / fork 项目快速跑通。

做 4 件事:
  1) 注册一个 demo 账号(如果不存在)
  2) 创建一个 demo trail
  3) 上传 N 张本地照片(默认 packages/annotation/photos/ 前 5 张)
  4) 触发 Run 跑 agent → critique + travelogue + plan + embedding

用法:
  # 本地 dev(对默认 http://localhost:8000):
  python scripts/seed_demo.py

  # 跨网线上(传 base url):
  python scripts/seed_demo.py --base https://traillens.zorotreeking.online \
    --email demo@example.com --password demo1234 --count 5

  # 跳过 Run(只上传):
  python scripts/seed_demo.py --no-run

输出 trail_id 可直接拿去做 share 链接演示。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PHOTO_DIR = ROOT / "packages" / "annotation" / "photos"


def _opener(jar: CookieJar):
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _post_json(opener, url: str, body: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req) as r:
        return json.loads(r.read().decode())


def _get_json(opener, url: str) -> dict:
    with opener.open(url) as r:
        return json.loads(r.read().decode())


def _upload_multipart(opener, url: str, files: list[Path]) -> dict:
    boundary = "----TrailLensSeed" + str(int(time.time()))
    body = b""
    for f in files:
        ctype = "image/jpeg" if f.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="files"; filename="{f.name}"\r\n'.encode()
        body += f"Content-Type: {ctype}\r\n\r\n".encode()
        body += f.read_bytes()
        body += b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with opener.open(req) as r:
        return json.loads(r.read().decode())


def _sign_up_or_in(opener, base: str, email: str, password: str) -> dict:
    """优先尝试注册;已存在则登录。"""
    try:
        return _post_json(opener, f"{base}/v1/auth/sign-up",
                          {"email": email, "password": password, "name": "Demo"})
    except urllib.error.HTTPError as e:
        if e.code == 409:
            print(f"  账号已存在,改登录...")
            return _post_json(opener, f"{base}/v1/auth/sign-in",
                              {"email": email, "password": password})
        raise


def _run_and_wait(opener, base: str, trail_id: str) -> None:
    """触发 Run 并消费 SSE 直到 run.finished/error。"""
    req = urllib.request.Request(f"{base}/v1/trails/{trail_id}/run", method="POST")
    with opener.open(req) as r:
        events = 0
        for line in r:
            line = line.decode().strip()
            if line.startswith("event:"):
                ev = line[6:].strip()
                events += 1
                print(f"  [SSE] {ev}")
                if ev in ("run.finished", "run.error"):
                    print(f"  共 {events} 事件")
                    return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--email", default="demo@example.com")
    ap.add_argument("--password", default="demo1234")
    ap.add_argument("--trail-name", default="Demo · 川西雪山样片")
    ap.add_argument("--location", default="四川 · 雅拉雪山")
    ap.add_argument("--photo-dir", type=Path, default=DEFAULT_PHOTO_DIR)
    ap.add_argument("--count", type=int, default=5, help="上传几张")
    ap.add_argument("--no-run", action="store_true", help="跳过 agent run")
    args = ap.parse_args()

    if not args.photo_dir.exists():
        print(f"✗ 照片目录不存在: {args.photo_dir}")
        sys.exit(1)

    photos = sorted(
        p for p in args.photo_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )[: args.count]
    if not photos:
        print(f"✗ {args.photo_dir} 里没有 jpg/png 照片")
        sys.exit(1)

    print(f"→ 目标 API: {args.base}")
    print(f"→ 用户: {args.email}")
    print(f"→ 照片: {len(photos)} 张")

    jar = CookieJar()
    opener = _opener(jar)

    print("\n[1/4] sign-up or sign-in")
    me = _sign_up_or_in(opener, args.base, args.email, args.password)
    print(f"  user_id: {me.get('user_id')}")

    print("\n[2/4] 创建 trail")
    trail = _post_json(opener, f"{args.base}/v1/trails", {
        "name": args.trail_name,
        "location_name": args.location,
        "gpx_uri": None,
    })
    tid = trail["id"]
    print(f"  trail_id: {tid}")

    print(f"\n[3/4] 上传 {len(photos)} 张")
    res = _upload_multipart(opener, f"{args.base}/v1/trails/{tid}/photos:upload", photos)
    print(f"  accepted={res['accepted']} failed={res['failed']}")

    if args.no_run:
        print("\n[4/4] --no-run,跳过 agent")
    else:
        print(f"\n[4/4] 触发 Run(豆包打分,约 {len(photos)*15}s)")
        _run_and_wait(opener, args.base, tid)

    print(f"\n✓ Done")
    print(f"  share URL: {args.base.replace('//api.', '//').replace(':8000', '')}/trails/{tid}/share")


if __name__ == "__main__":
    main()
