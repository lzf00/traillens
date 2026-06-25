/**
 * 顶部全局导航 — SSR 调 /v1/auth/me 判断登录态。
 *
 * 走 cookie(traillens_session,HttpOnly) → 后端 deps.get_current_user 解码 JWT
 */

import Link from "next/link";
import { cookies, headers } from "next/headers";
import { ThemeToggle } from "./ThemeToggle";

async function fetchMe(): Promise<{ email: string; name: string | null } | null> {
  const base = process.env.TRAILLENS_API_INTERNAL_BASE || process.env.NEXT_PUBLIC_API_BASE || "";
  const c = await cookies();
  const cookieHeader = c.getAll().map((x) => `${x.name}=${x.value}`).join("; ");
  try {
    const r = await fetch(`${base}/v1/auth/me`, {
      headers: { Cookie: cookieHeader },
      cache: "no-store",
    });
    if (!r.ok) return null;
    return r.json();
  } catch {
    return null;
  }
}

export async function Nav() {
  const me = await fetchMe();

  return (
    <nav className="flex items-center justify-between border-b border-divider px-6 py-3">
      <Link href="/" className="font-display text-lg text-fg-primary">
        TrailLens
      </Link>

      <div className="flex items-center gap-5 text-sm">
        <Link href="/trails" className="text-fg-secondary hover:text-fg-primary transition-colors">
          Trails
        </Link>
        <Link href="/library" className="text-fg-secondary hover:text-fg-primary transition-colors">
          Library
        </Link>
        <Link href="/settings" className="text-fg-secondary hover:text-fg-primary transition-colors">
          Settings
        </Link>
      </div>

      <div className="flex items-center gap-3 text-sm">
        <ThemeToggle />
        {me ? (
          <>
            <span className="mono text-xs text-fg-tertiary">{me.email}</span>
            <form action="/v1/auth/sign-out" method="POST">
              <button
                type="submit"
                className="text-fg-secondary hover:text-accent-aurora transition-colors"
              >
                登出
              </button>
            </form>
          </>
        ) : (
          <>
            <Link
              href="/login"
              className="text-fg-secondary hover:text-fg-primary transition-colors"
            >
              登录
            </Link>
            <Link
              href="/signup"
              className="rounded-md bg-accent-aurora px-3 py-1.5 text-xs font-medium text-bg-base hover:bg-accent-aurora/90"
            >
              注册
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
