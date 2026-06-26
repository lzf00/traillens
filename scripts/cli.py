#!/usr/bin/env python3
"""TrailLens CLI — fork 项目跑 demo / 健康检查 / 重建索引。

子命令:
  seed              注册一个 demo 账号 + 上传 N 张 + 跑 Run(走 seed_demo.py)
  health [BASE]     列出该用户所有 trail 的数据健康度
  embed-all         对所有 trail 的 critique 文字补 embedding
  ping              健康检查 BASE/healthz

设计:纯 stdlib (urllib + getpass),0 依赖,任何 Python 3.11 装好就能跑。
用法:
  python scripts/cli.py seed --base https://your.host --email demo@example.com
  python scripts/cli.py health --base http://localhost:8000 \\
        --email me@example.com --password ****
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _opener(jar: CookieJar):
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _post(opener, url, body=None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with opener.open(req) as r:
        try:
            return json.loads(r.read().decode())
        except json.JSONDecodeError:
            return {}


def _get(opener, url):
    with opener.open(url) as r:
        return json.loads(r.read().decode())


def _sign_in(opener, base, email, password):
    try:
        return _post(opener, f"{base}/v1/auth/sign-in", {"email": email, "password": password})
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        raise SystemExit(f"sign-in 失败: HTTP {e.code} {body}")


# --------------------------------------------------------------------------- #
# 子命令
# --------------------------------------------------------------------------- #

def cmd_seed(args):
    """委托给 scripts/seed_demo.py(已存在,功能更全)。"""
    import subprocess
    fwd = [sys.executable, str(HERE / "seed_demo.py")]
    for k in ("base", "email", "password", "trail_name", "location", "count", "photo_dir"):
        v = getattr(args, k, None)
        if v is not None and v != "":
            fwd += [f"--{k.replace('_', '-')}", str(v)]
    if args.no_run:
        fwd.append("--no-run")
    subprocess.run(fwd, check=False)


def cmd_health(args):
    base = args.base.rstrip("/")
    jar = CookieJar()
    opener = _opener(jar)
    _sign_in(opener, base, args.email, args.password)
    out = _get(opener, f"{base}/v1/trails/_health")
    trails = out.get("trails", [])
    if not trails:
        print("(没有 trail)")
        return
    name_w = max(8, min(40, max(len(t["name"]) for t in trails)))
    print(f'{"name":<{name_w}}  total  scored  keep  crit  emb')
    for t in trails:
        warn = " ⚠" if t["critiqued"] > 0 and t["embedded"] < t["critiqued"] else ""
        print(
            f'{t["name"][:name_w]:<{name_w}}  '
            f'{t["total"]:>5}  {t["scored"]:>6}  {t["keeps"]:>4}  '
            f'{t["critiqued"]:>4}  {t["embedded"]:>3}{warn}'
        )


def cmd_embed_all(args):
    base = args.base.rstrip("/")
    jar = CookieJar()
    opener = _opener(jar)
    _sign_in(opener, base, args.email, args.password)
    out = _post(opener, f"{base}/v1/library/embed/all")
    print(f'embedded={out.get("embedded", "?")}  skipped={out.get("skipped", "?")}')


def cmd_ping(args):
    base = args.base.rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/healthz", timeout=5) as r:
            print(f"healthz {r.status} {r.read().decode()[:80]}")
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"ping 失败: {e}")


# --------------------------------------------------------------------------- #
# argparse
# --------------------------------------------------------------------------- #

def _add_creds(sp):
    sp.add_argument("--base", default="http://localhost:8000")
    sp.add_argument("--email", required=True)
    sp.add_argument(
        "--password",
        default=None,
        help="留空时从环境变量 TRAILLENS_PASSWORD 或交互式输入读",
    )


def main():
    ap = argparse.ArgumentParser(prog="traillens", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_seed = sub.add_parser("seed", help="一键 seed 演示数据")
    p_seed.add_argument("--base", default="http://localhost:8000")
    p_seed.add_argument("--email", default="demo@example.com")
    p_seed.add_argument("--password", default="demo1234")
    p_seed.add_argument("--trail-name", default="Demo · CLI seed")
    p_seed.add_argument("--location", default="")
    p_seed.add_argument("--count", type=int, default=5)
    p_seed.add_argument("--photo-dir", default=None)
    p_seed.add_argument("--no-run", action="store_true")
    p_seed.set_defaults(func=cmd_seed)

    p_health = sub.add_parser("health", help="列每 trail 数据健康度")
    _add_creds(p_health)
    p_health.set_defaults(func=cmd_health)

    p_embed = sub.add_parser("embed-all", help="为所有 critique 补 embedding")
    _add_creds(p_embed)
    p_embed.set_defaults(func=cmd_embed_all)

    p_ping = sub.add_parser("ping", help="健康检查 BASE/healthz")
    p_ping.add_argument("--base", default="http://localhost:8000")
    p_ping.set_defaults(func=cmd_ping)

    args = ap.parse_args()

    # 统一密码读取(子命令带 --password 才需要)
    if hasattr(args, "password") and args.password is None:
        import os as _os
        args.password = _os.environ.get("TRAILLENS_PASSWORD") or getpass.getpass("密码: ")

    args.func(args)


if __name__ == "__main__":
    main()
