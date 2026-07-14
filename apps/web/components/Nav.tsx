/**
 * 顶部全局导航 — SSR 调 /v1/auth/me 判断登录态。
 *
 * 走 cookie(traillens_session,HttpOnly) → 后端 deps.get_current_user 解码 JWT
 */

import Link from "next/link";
import { cookies, headers } from "next/headers";
import { ExternalLink } from "lucide-react";
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
    <nav className="flex items-center justify-between gap-4 border-b border-divider px-4 md:px-6 py-3">
      <Link href="/" className="font-display text-lg text-fg-primary shrink-0">
        TrailLens
      </Link>

      {/* 中间链接:mobile 隐藏,md 起显示 */}
      <div className="hidden md:flex items-center gap-6 text-sm">
        <Link href="/trails" className="text-fg-secondary hover:text-fg-primary transition-colors">
          作品集
        </Link>
        <Link href="/library" className="text-fg-secondary hover:text-fg-primary transition-colors">
          语义搜索
        </Link>
        <Link href="/settings" className="text-fg-secondary hover:text-fg-primary transition-colors">
          设置
        </Link>
      </div>

      <div className="flex items-center gap-2 md:gap-3 text-sm shrink-0">
        {/* 作者主页 · 外链 */}
        <a
          href="https://www.zorotreeking.online/"
          target="_blank"
          rel="noreferrer"
          title="作者主页 · zorotreeking.online"
          className="inline-flex items-center gap-1 text-xs text-fg-tertiary hover:text-accent-aurora transition-colors"
        >
          <span className="hidden sm:inline">@zoro</span>
          <ExternalLink size={12} />
        </a>
        <ThemeToggle />
        {me ? (
          <>
            {/* email 只在 sm 起显示 */}
            <span className="hidden sm:inline mono text-xs text-fg-tertiary truncate max-w-[160px]">
              {me.email}
            </span>
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
