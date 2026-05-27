/**
 * 客户端埋点封装。
 *
 * 设计:
 * - 无 NEXT_PUBLIC_POSTHOG_KEY 时所有调用都是 no-op,不影响 dev / preview
 * - 不直接 import posthog-js 到业务代码,避免每个组件多打 50KB
 * - 事件名遵循 `<domain>.<action>` 命名: trail.created / photo.uploaded
 */

let _ph: any = null;
let _ready: Promise<any> | null = null;

async function load() {
  if (_ready) return _ready;
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  if (!key || typeof window === "undefined") return null;
  _ready = import("posthog-js").then(({ default: posthog }) => {
    posthog.init(key, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com",
      capture_pageview: true,
      capture_pageleave: true,
      autocapture: false,           // 显式埋点更可控
      session_recording: { maskAllInputs: true },
    });
    _ph = posthog;
    return posthog;
  });
  return _ready;
}

export async function track(event: string, props?: Record<string, any>) {
  const p = await load();
  if (!p) return;
  p.capture(event, props);
}

export async function identify(userId: string, traits?: Record<string, any>) {
  const p = await load();
  if (!p) return;
  p.identify(userId, traits);
}

// 主流程的"埋点字典" — 单一来源
export const EVENTS = {
  TRAIL_CREATED: "trail.created",
  PHOTOS_UPLOADED: "photos.uploaded",
  RUN_STARTED: "run.started",
  RUN_FINISHED: "run.finished",
  PHOTO_KEPT: "photo.kept",
  PHOTO_REJECTED: "photo.rejected",
  TRAVELOGUE_GENERATED: "travelogue.generated",
  SHARE_OPENED: "share.opened",
  UPGRADE_CLICKED: "upgrade.clicked",
  CHECKOUT_STARTED: "checkout.started",
  CHECKOUT_COMPLETED: "checkout.completed",
} as const;
