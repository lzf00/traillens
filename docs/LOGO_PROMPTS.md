# Logo / OG / 视觉素材生成 prompt

> v0 出来的 vector logo 用 [Recraft.ai](https://recraft.ai) 矢量化。
> 全部素材都放到 `apps/web/public/`。
> 视觉系统已锁定见 [BRAND.md](BRAND.md) + [PRODUCT_PLAN §2.2](PRODUCT_PLAN.md#22-视觉系统直接定下来避免每个页面重新设计)。

## 1. Wordmark Logo(主 logo)

**目标平台**: v0.dev / Midjourney v7 / DALL-E 3

```
Minimal wordmark logo for "TrailLens" — single line of text, serif typography
in the style of Fraunces 600 weight. The capital T has subtle bracket serifs;
the capital L is widened to evoke a mountain ridge silhouette. Letterforms in
warm desaturated white (#E8ECF1). Background pure deep slate (#0F1115).
Centered, generous whitespace, vector illustration aesthetic, 16:9.
No decorative elements. No emoji. No gradients. No 3D effects.
```

变体(竖排):
```
... same as above but stacked: TRAIL on top, LENS below, kerning -2%.
```

## 2. Mark / Favicon

**目标**: 单色 SVG,32x32 + 512x512 都清晰

```
Geometric monogram combining a mountain ridge line and a camera aperture iris.
The mountain forms the lower half (3 peaks of unequal height, sharp edges),
the aperture (8 blades) forms the upper half overlapping the highest peak.
Single color: aurora green #6FBF8B on transparent. Flat, vector, no shading.
Stroke width consistent. Optical centering: align to bounding box center, not
geometric center.
```

## 3. Open Graph 卡片(分享时的 1200x630)

**用动态生成而非静图** — 每个 trail / changelog / blog 都生成独有 OG。
实现见 [`apps/web/app/og/route.tsx`](../apps/web/app/og/route.tsx) (Satori-based)。

### 静态 fallback(品牌主页用)的设计 prompt

```
Open Graph card 1200x630 for landscape photography AI tool TrailLens.
Top half: minimal silhouette of a mountain range with thin contour lines
(National Geographic atlas style). Bottom half: dark deep slate #0F1115
with text:
  Headline (Fraunces serif, 64pt, #E8ECF1):
    "The AI darkroom for
    landscape photographers who hike."
  Subtext (Inter, 20pt, #9AA4B2):
    "Multi-agent photo culling, critique, and trip planning."
  Bottom-left tag (Inter mono, 14pt, #6FBF8B):
    "traillens.app"
Single accent: a small aurora-green dot before "traillens.app".
No icons, no UI mockups, no rainbow, no AI glow.
```

## 4. Hero illustration(landing 顶部)

```
Wide horizontal scene illustration for hero section, 2:1 aspect ratio.
Pre-dawn alpine scene: silhouette of jagged ridge against a glacier-blue
to aurora-green vertical gradient sky (top: deep blue #0F1115 fading to
glacier #8FB8D1 mid, with a thin warm horizon band #E8B96A near the peaks).
A single photographer figure stands on a foreground ridge, tripod set up,
looking right. No text. Cinematic, painterly, low contrast (NOT digital glossy).
Inspired by Caspar David Friedrich + James Turrell color palette.
```

## 5. Sprint 录屏 GIF 模板

每次 release 录一个 ≤30 秒的 demo GIF,放 `apps/web/public/demo/{vYYY}.gif`:

```
1. Open Canvas page → upload 30 photos → 缩略图轨道 fade in
2. SSE 流过来,分数滚动跳出
3. 鼠标点一张照片 → 雷达图淡入 + decision timeline 展开
4. 切换游记 tab → markdown 流式生成
5. 最后 1 秒:logo + "traillens.app"

工具:CleanShot X / LICEcap / Kap。
压缩:gifsicle -O3 --colors 64 → < 2MB。
```

## 6. 拒绝列表(明确不做)

- ❌ 不出现 AI 机器人脸 / 大脑图标 / 神经网络节点
- ❌ 不用渐变背景在 landing(已在 BRAND.md 写明)
- ❌ 不用紫色到粉色的"AI typical"配色
- ❌ logo 不含相机本身(太具象 + 跟 photo AI 雷同)
- ❌ 不在 OG 卡用 emoji 装饰
