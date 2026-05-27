/**
 * 动态 Open Graph 卡片(1200x630)。
 *
 * 用法:
 *   /og?title=贡嘎环线&subtitle=2026-05-15&kept=42&kind=trail
 *   /og?title=Beyond AVA&subtitle=Sprint 3 blog&kind=blog
 *   /og  → 品牌默认卡
 *
 * 实现:Next 内置 ImageResponse(基于 Satori),不需要 puppeteer。
 * 字体:这里走系统 fallback;Sprint 5 末从 R2 加载真正的 Fraunces / Inter woff2。
 */

import { ImageResponse } from "next/og";
import type { NextRequest } from "next/server";

export const runtime = "edge";

const COLORS = {
  bg: "#0F1115",
  bgRaised: "#1A1E25",
  fgPrimary: "#E8ECF1",
  fgSecondary: "#9AA4B2",
  fgTertiary: "#5B6573",
  aurora: "#6FBF8B",
  glacier: "#8FB8D1",
  golden: "#E8B96A",
  divider: "rgba(255,255,255,0.06)",
};

const KIND_LABEL: Record<string, string> = {
  trail: "Trail",
  blog: "Blog",
  changelog: "Changelog",
  default: "TrailLens",
};

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const kind = searchParams.get("kind") ?? "default";
  const title =
    searchParams.get("title") ?? "The AI darkroom for landscape photographers who hike.";
  const subtitle = searchParams.get("subtitle") ?? "traillens.zorotreeking.online";
  const kept = searchParams.get("kept");

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%", height: "100%",
          display: "flex", flexDirection: "column",
          background: COLORS.bg,
          padding: "64px 80px",
          position: "relative",
        }}
      >
        {/* 顶部:类别 chip + 品牌字 */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div
            style={{
              display: "flex",
              padding: "8px 16px",
              borderRadius: 8,
              background: COLORS.bgRaised,
              color: COLORS.fgSecondary,
              fontSize: 22,
              fontFamily: "system-ui",
              letterSpacing: "0.05em",
              textTransform: "uppercase",
            }}
          >
            {KIND_LABEL[kind] ?? KIND_LABEL.default}
          </div>
          <div
            style={{
              display: "flex", alignItems: "center", gap: 12,
              color: COLORS.fgPrimary, fontSize: 26, fontFamily: "serif",
            }}
          >
            <div style={{ width: 12, height: 12, background: COLORS.aurora, borderRadius: 999 }} />
            TrailLens
          </div>
        </div>

        {/* 中间:大标题 */}
        <div
          style={{
            flex: 1,
            display: "flex", flexDirection: "column", justifyContent: "center",
            color: COLORS.fgPrimary,
            fontSize: 76, fontFamily: "serif",
            lineHeight: 1.1,
            marginTop: 16,
          }}
        >
          {title}
        </div>

        {/* 底部:subtitle + 可选指标 */}
        <div
          style={{
            display: "flex", justifyContent: "space-between", alignItems: "flex-end",
            borderTop: `1px solid ${COLORS.divider}`,
            paddingTop: 24,
          }}
        >
          <div style={{ color: COLORS.fgSecondary, fontSize: 28, fontFamily: "system-ui" }}>
            {subtitle}
          </div>
          {kept != null && (
            <div style={{ display: "flex", gap: 24, alignItems: "baseline" }}>
              <div style={{ color: COLORS.aurora, fontSize: 52, fontFamily: "system-ui", fontWeight: 600 }}>
                {kept}
              </div>
              <div style={{ color: COLORS.fgTertiary, fontSize: 22, fontFamily: "system-ui" }}>
                kept
              </div>
            </div>
          )}
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
