"""Playwright 自动录 demo:浏览 demo trail share 页 → 一些主页面切换 →
ffmpeg 合成 GIF + MP4 嵌 README。

需要:playwright + ffmpeg(brew install ffmpeg / apt install ffmpeg)。

产出:
  docs/screenshots/demo.gif    README 嵌入
  docs/screenshots/demo.mp4    分享到社交平台用
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/screenshots"
FRAMES = OUT / "_frames"
BASE = "https://traillens.zorotreeking.online"

# 录制脚本:每一步 (url, dwell_seconds, scroll_to_pct)
STEPS = [
    ("/", 2.0, 0.0),                              # Landing
    ("/trails/demo", 3.0, 0.0),                   # Demo share 顶部 Hero
    ("/trails/demo", 2.0, 0.5),                   # share 中部 (滚到照片网格)
    ("/trails/demo", 2.0, 0.9),                   # share 底部 (游记+计划+CTA)
    ("/library", 2.5, 0.0),                       # Library 入口
    ("/settings", 2.5, 0.5),                      # Settings 数据健康
]


def shoot(headless=True, viewport=(1280, 720), fps=2):
    """每个 step 按 fps 截 N 帧;最后 ffmpeg 拼。"""
    if shutil.which("ffmpeg") is None:
        print("✗ ffmpeg 未装:brew install ffmpeg / apt install ffmpeg")
        sys.exit(1)

    FRAMES.mkdir(parents=True, exist_ok=True)
    for f in FRAMES.iterdir():
        f.unlink()

    idx = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})

        for url, dwell, scroll in STEPS:
            page.goto(BASE + url, wait_until="networkidle")
            if scroll > 0:
                page.evaluate(f"window.scrollTo({{top: document.body.scrollHeight * {scroll}, behavior: 'smooth'}})")
                page.wait_for_timeout(700)
            n_frames = max(2, int(dwell * fps))
            for _ in range(n_frames):
                page.screenshot(path=str(FRAMES / f"f_{idx:04d}.png"))
                idx += 1
                page.wait_for_timeout(int(1000 / fps))
        browser.close()
    print(f"  共截 {idx} 帧 → {FRAMES}/")

    # 合成 MP4(高清,投社交平台用)
    mp4 = OUT / "demo.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(fps),
        "-i", str(FRAMES / "f_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
        "-vf", "scale=1280:-2", str(mp4),
    ], check=True, capture_output=True)
    print(f"  ✓ {mp4} ({mp4.stat().st_size // 1024}KB)")

    # 合成 GIF(README 嵌入,小一点)
    gif = OUT / "demo.gif"
    palette = FRAMES / "_palette.png"
    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(fps),
        "-i", str(FRAMES / "f_%04d.png"),
        "-vf", "scale=900:-1,palettegen", str(palette),
    ], check=True, capture_output=True)
    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(fps),
        "-i", str(FRAMES / "f_%04d.png"), "-i", str(palette),
        "-lavfi", "scale=900:-1,paletteuse",
        str(gif),
    ], check=True, capture_output=True)
    print(f"  ✓ {gif} ({gif.stat().st_size // 1024}KB)")

    # 清理 frames
    for f in FRAMES.iterdir():
        f.unlink()
    FRAMES.rmdir()


if __name__ == "__main__":
    print("══ TrailLens demo 自动录制 ══")
    shoot()
    print("\n下一步:在 README 顶部加")
    print('  <img src="docs/screenshots/demo.gif" />')
    print("社交平台贴 demo.mp4 (Twitter 限 512MB / 即刻无限)")
