"""星空堆栈 PoC — 验证后端能算。

最小可行算法(直接对齐均值,不接 SIFT):
  1. 把所有照片缩到统一尺寸
  2. 第 1 张作 reference
  3. 后续每张 OpenCV phaseCorrelate 算位移 → 平移对齐
  4. 取 median(对噪声/异物如飞机轨迹更鲁棒)

只针对相机三脚架 + 短间隔的星空 — 不抗大旋转(地球自转 5min+ 真要 align star points,
那个上 Astroalign / Sequator 算法,工程量另算)。

复杂度:N 张 6MP 照片 ~ 2N MB 内存 + N×O(WH) 操作,500ms-1s/张。
"""

from __future__ import annotations

import io
from typing import Any, Iterable

import numpy as np  # type: ignore

try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None  # type: ignore


def triage_frame(data: bytes, max_side: int = 800) -> dict[str, Any]:
    """对单张 frame 打技术分,返回 keep/reject 建议。

    检测:
      - blur_score (拉普拉斯方差,<80 通常模糊)
      - exposure_over_pct (>0.4 = 云/雾/过曝)
      - exposure_under_pct (<0.2 但 blur 也低 = 无信号帧)
      - mean_brightness (辅助判断)

    verdict: 'keep' | 'blur' | 'cloud' | 'underexposed'
    """
    if cv2 is None:
        return {"verdict": "keep", "reason": "opencv 未装,跳过检测"}
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"verdict": "reject", "reason": "decode 失败"}
    h, w = img.shape[:2]
    scale = max_side / max(h, w) if max(h, w) > max_side else 1.0
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    total = hist.sum() or 1.0
    over = float(hist[220:].sum() / total)
    under = float(hist[:20].sum() / total)
    brightness = float(gray.mean())

    if over > 0.4:
        verdict, reason = "cloud", f"over_pct={over:.2f} > 0.4(疑云/过曝)"
    elif blur < 80:
        verdict, reason = "blur", f"blur={blur:.0f} < 80"
    elif under > 0.6 and blur < 200:
        verdict, reason = "underexposed", f"under_pct={under:.2f} + blur={blur:.0f}"
    else:
        verdict, reason = "keep", "OK"

    return {
        "verdict": verdict,
        "reason": reason,
        "blur_score": round(blur, 1),
        "exposure_over_pct": round(over, 3),
        "exposure_under_pct": round(under, 3),
        "mean_brightness": round(brightness, 1),
    }


def critic_stack(result: bytes) -> dict[str, Any]:
    """对堆栈成品打分。用于 stargazer 的 critic 节点。

    指标:
      snr_db     信噪比(dB) — 亮部方差 / 暗部方差
      star_roundness  平均星点圆度(1.0 = 完美圆,<0.6 = 拖影)
      dynamic_range   高低灰度差(0-255)
      overall    综合 0-10

    快速算法(全在 gray 图上,不精确但一致):
      1. 找 top 1% 最亮的点当"星点候选"
      2. 对每个 blob 算 (面积)/(π·r²)
    """
    fallback = {"snr_db": None, "star_roundness": None, "dynamic_range": None, "overall": None}
    if cv2 is None:
        return fallback
    arr = np.frombuffer(result, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return fallback
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # dynamic range: 5%-95% 分位差
    lo, hi = np.percentile(gray, [5, 95])
    dr = float(hi - lo)

    # SNR: 暗背景 var vs 亮点 var,dB
    dark_mask = gray < np.percentile(gray, 50)
    bright_mask = gray > np.percentile(gray, 95)
    dark_var = float(gray[dark_mask].var()) if dark_mask.any() else 1.0
    bright_var = float(gray[bright_mask].var()) if bright_mask.any() else 1.0
    snr_db = float(10 * np.log10(bright_var / max(dark_var, 1.0)))

    # 星点圆度: threshold + contour
    _, binmask = cv2.threshold(gray, int(np.percentile(gray, 99)), 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    roundnesses = []
    for c in contours[:200]:
        area = cv2.contourArea(c)
        peri = cv2.arcLength(c, True)
        if area > 3 and peri > 0:
            # 4π·area / peri² = 1 for perfect circle
            r = 4 * np.pi * area / (peri * peri)
            if 0 < r <= 1.5:
                roundnesses.append(r)
    star_r = float(np.mean(roundnesses)) if roundnesses else 0.0

    # 综合:snr 权重 0.4,roundness 0.4,dynamic range 0.2
    snr_norm = max(0, min(1, snr_db / 40.0))
    r_norm = max(0, min(1, star_r))
    dr_norm = max(0, min(1, dr / 200.0))
    overall = round((snr_norm * 0.4 + r_norm * 0.4 + dr_norm * 0.2) * 10, 2)

    return {
        "snr_db": round(snr_db, 1),
        "star_roundness": round(star_r, 3),
        "dynamic_range": round(dr, 1),
        "overall": overall,
    }


def stack_median(images: Iterable[bytes], max_side: int = 1600) -> bytes | None:
    """按 median 合成 N 张照片,先平移对齐第 1 张。

    输入:每张 jpg/png bytes
    输出:合成后的 jpg bytes(quality=88),None=失败

    median 比 mean 对随机噪声 / 飞机轨迹 / 卫星 更鲁棒(异常值不参与中位)。
    """
    if cv2 is None:
        return None

    frames = []
    ref_gray = None
    for raw in images:
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        scale = max_side / max(h, w) if max(h, w) > max_side else 1.0
        if scale < 1.0:
            img = cv2.resize(img, (int(w * scale), int(h * scale)))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)

        if ref_gray is None:
            ref_gray = gray
            frames.append(img)
            continue

        # phaseCorrelate 估全图平移(亚像素精度)
        try:
            dx, dy = cv2.phaseCorrelate(ref_gray, gray)[0]
        except cv2.error:
            dx, dy = 0.0, 0.0
        if abs(dx) < 100 and abs(dy) < 100:  # 大于此就异常,舍
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            img = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]),
                                 flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        frames.append(img)

    if not frames:
        return None

    # median 沿 frame 维(避免大 stack 内存爆,这里 max_side 1600 应可控)
    stacked = np.median(np.stack(frames, axis=0), axis=0).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", stacked, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    return bytes(buf) if ok else None
