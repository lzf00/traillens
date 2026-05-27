/**
 * 客户端 Sentry 初始化(动态 import,SSR / 无 DSN 时 no-op)。
 *
 * 用法(在最顶层 layout.tsx 引一次):
 *   import { initSentry } from "@/lib/sentry";
 *   initSentry();
 */

let initialized = false;

export async function initSentry() {
  if (initialized) return;
  if (typeof window === "undefined") return;
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!dsn) return;
  initialized = true;
  try {
    const Sentry = await import("@sentry/nextjs");
    Sentry.init({
      dsn,
      environment: process.env.NEXT_PUBLIC_VERCEL_ENV || "development",
      tracesSampleRate: 0.1,
      replaysSessionSampleRate: 0.05,
      replaysOnErrorSampleRate: 1.0,
    });
  } catch {
    // SDK 不在,no-op
  }
}
