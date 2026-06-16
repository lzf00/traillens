/**
 * 顶部全局导航。
 * - logo 跳 /
 * - 主链接：Trails / Library / Settings
 * - 右侧：已登录显示 email + 登出；未登录显示 登录
 *
 * 当前认证：dev 桥 — cookie `traillens_user_email` 写入即视为已登录
 * （Sprint 5 末换 Better Auth 真签）
 */

import Link from "next/link";
import { cookies } from "next/headers";

export async function Nav() {
  const c = await cookies();
  const email = c.get("traillens_user_email")?.value;

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
        {email ? (
          <>
            <span className="mono text-xs text-fg-tertiary">{email}</span>
            <form action="/api/auth/sign-out" method="POST">
              <button
                type="submit"
                className="text-fg-secondary hover:text-accent-aurora transition-colors"
              >
                登出
              </button>
            </form>
          </>
        ) : (
          <Link
            href="/login"
            className="rounded-md bg-accent-aurora px-3 py-1.5 text-xs font-medium text-bg-base hover:bg-accent-aurora/90"
          >
            登录
          </Link>
        )}
      </div>
    </nav>
  );
}
