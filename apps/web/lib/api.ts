/**
 * fetch wrapper — SSR 和客户端通用。
 *
 * 认证策略:
 * - client-side: 同域 fetch /v1/...,浏览器自动带 HttpOnly cookie(traillens_session)
 * - server-side(RSC): 走 docker 内网 http://api:8000,需要显式透传 Cookie header
 *
 * 兼容 dev 桥旧 cookie(traillens_user_id) — 后端 local 模式仍接受 X-Dev-User-Id header
 */

const CLIENT_API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";
const SERVER_API_BASE =
  process.env.TRAILLENS_API_INTERNAL_BASE || process.env.NEXT_PUBLIC_API_BASE || "";
const isServer = typeof window === "undefined";

export async function apiFetch(path: string, init?: RequestInit) {
  const headers = new Headers(init?.headers);

  // SSR: 把 next/headers 里的 cookies 全部透传给后端
  if (isServer) {
    const { cookies } = await import("next/headers");
    const c = await cookies();
    const cookieStr = c.getAll().map((x) => `${x.name}=${x.value}`).join("; ");
    if (cookieStr) headers.set("Cookie", cookieStr);

    // 兼容旧 dev 桥
    const uid = c.get("traillens_user_id")?.value;
    if (uid) headers.set("X-Dev-User-Id", uid);
  }
  // client-side: 走同域 + credentials:include,浏览器自动带 cookie,无需手动操作

  const base = isServer ? SERVER_API_BASE : CLIENT_API_BASE;
  return fetch(base + path, { ...init, headers, credentials: "include" });
}
