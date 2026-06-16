/**
 * 简单的 fetch wrapper —— SSR 和客户端通用。
 *
 * - server-side（RSC / route handler）：从 next/headers cookies 读 user_id
 * - client-side：从 document.cookie 读 traillens_user_id（非 httpOnly）
 * - 都把 user_id 通过 X-Dev-User-Id header 传给后端
 *   后端 deps.py 在 TRAILLENS_ENV=local 时使用这个 header
 *
 * Sprint 5 末换 Better Auth：替换为 Bearer token。
 */

const CLIENT_API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";
const SERVER_API_BASE =
  process.env.TRAILLENS_API_INTERNAL_BASE || process.env.NEXT_PUBLIC_API_BASE || "";
const isServer = typeof window === "undefined";

function readClientUserId(): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(/(?:^|;\s*)traillens_user_id=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : null;
}

export async function apiFetch(path: string, init?: RequestInit, userIdOverride?: string | null) {
  const headers = new Headers(init?.headers);
  let userId = userIdOverride ?? readClientUserId();

  // server-side fallback：从 next/headers 读
  if (!userId && typeof window === "undefined") {
    const { cookies } = await import("next/headers");
    const c = await cookies();
    userId = c.get("traillens_user_id")?.value ?? null;
  }

  if (userId) headers.set("X-Dev-User-Id", userId);

  const base = isServer ? SERVER_API_BASE : CLIENT_API_BASE;
  return fetch(base + path, { ...init, headers, credentials: "include" });
}
