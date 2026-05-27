/**
 * Feature flags(PostHog 后端) + 本地 override。
 *
 * 设计:
 * - 无 PostHog → flag 永远 false(保守默认)
 * - URL ?flag=name 临时打开/关闭 flag,用于 demo/debug
 * - 同一会话内 flag 值缓存,避免反复请求 PostHog 慢死页面
 */

let cache: Record<string, boolean> = {};

export async function isEnabled(flag: string): Promise<boolean> {
  if (typeof window === "undefined") return false;

  // URL override 优先
  const url = new URL(window.location.href);
  const param = url.searchParams.get(`flag.${flag}`);
  if (param === "1" || param === "true") return true;
  if (param === "0" || param === "false") return false;

  if (flag in cache) return cache[flag];

  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  if (!key) {
    cache[flag] = false;
    return false;
  }
  try {
    const ph = (await import("posthog-js")).default;
    // posthog-js 已经在 lib/analytics.ts 初始化过;这里只读
    const v = ph.isFeatureEnabled(flag);
    cache[flag] = !!v;
    return cache[flag];
  } catch {
    cache[flag] = false;
    return false;
  }
}

/** A/B 测试变体读取 — "control" / "test" / "variant_b" 等。 */
export async function variant(flag: string, fallback = "control"): Promise<string> {
  if (typeof window === "undefined") return fallback;
  const url = new URL(window.location.href);
  const param = url.searchParams.get(`flag.${flag}`);
  if (param) return param;

  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  if (!key) return fallback;
  try {
    const ph = (await import("posthog-js")).default;
    const v = ph.getFeatureFlag(flag);
    return typeof v === "string" ? v : fallback;
  } catch {
    return fallback;
  }
}

// 项目内 flag 字典 — 让 grep 容易找
export const FLAGS = {
  NEW_LANDING_HERO: "new_landing_hero",
  CANVAS_KEYBOARD_PALETTE: "canvas_keyboard_palette",
  PIAA_FAST_TRACK: "piaa_fast_track",
  PRICING_19_VS_29: "pricing_19_vs_29",
} as const;
