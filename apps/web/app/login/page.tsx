/**
 * /login — dev 桥认证。
 *
 * 当前实现：
 *   表单 POST → /api/auth/sign-in → 写 cookie traillens_user_email + traillens_user_id
 *   → 重定向 /trails
 *
 * Sprint 5 末换 Better Auth：换 form action + 加密码校验，前端 UI 不动。
 */

import Link from "next/link";

export default function LoginPage() {
  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <header className="mb-10">
        <h1 className="font-display text-3xl text-fg-primary mb-2">登录</h1>
        <p className="text-sm text-fg-tertiary">
          MVP 阶段：输入邮箱即可进入（无密码、无验证）。
          <br />
          正式版会接 Better Auth。
        </p>
      </header>

      <form
        action="/api/auth/sign-in"
        method="POST"
        className="flex flex-col gap-4"
      >
        <label className="flex flex-col gap-1.5">
          <span className="text-xs text-fg-secondary mono">EMAIL</span>
          <input
            type="email"
            name="email"
            required
            autoFocus
            placeholder="you@example.com"
            className="rounded-md bg-bg-raised border border-divider px-3 py-2.5 text-fg-primary placeholder:text-fg-tertiary"
          />
        </label>

        <button
          type="submit"
          className="mt-2 rounded-md bg-accent-aurora px-4 py-2.5 text-sm font-medium text-bg-base hover:bg-accent-aurora/90 transition-colors"
        >
          进入 TrailLens
        </button>
      </form>

      <p className="mt-10 text-xs text-fg-tertiary">
        <Link href="/" className="hover:text-fg-secondary">
          ← 回首页
        </Link>
      </p>
    </main>
  );
}
