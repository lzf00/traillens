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
from typing import Iterable

import numpy as np  # type: ignore

try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None  # type: ignore


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
