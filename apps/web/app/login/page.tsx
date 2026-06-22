"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const r = await fetch("/v1/auth/sign-in", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({ detail: "登录失败" }));
        setErr(j.detail || "登录失败");
        setBusy(false);
        return;
      }
      router.push("/trails");
      router.refresh();
    } catch (e: any) {
      setErr(e.message || "网络错误");
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <header className="mb-10">
        <h1 className="font-display text-3xl text-fg-primary mb-2">登录</h1>
        <p className="text-sm text-fg-tertiary">
          没有账号?{" "}
          <Link href="/signup" className="text-accent-aurora hover:underline">
            注册一个 →
          </Link>
        </p>
      </header>

      <form onSubmit={submit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-xs text-fg-secondary mono">EMAIL</span>
          <input
            type="email"
            required
            autoFocus
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="rounded-md bg-bg-raised border border-divider px-3 py-2.5 text-fg-primary placeholder:text-fg-tertiary"
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-xs text-fg-secondary mono">PASSWORD</span>
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="至少 6 位"
            className="rounded-md bg-bg-raised border border-divider px-3 py-2.5 text-fg-primary placeholder:text-fg-tertiary"
          />
        </label>

        {err && (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {err}
          </div>
        )}

        <button
          type="submit"
          disabled={busy}
          className="mt-2 rounded-md bg-accent-aurora px-4 py-2.5 text-sm font-medium text-bg-base hover:bg-accent-aurora/90 disabled:opacity-50 transition-colors"
        >
          {busy ? "登录中…" : "登录"}
        </button>
      </form>

      <div className="mt-6">
        <div className="flex items-center gap-3 my-4">
          <hr className="flex-1 border-divider" />
          <span className="text-xs text-fg-tertiary">或</span>
          <hr className="flex-1 border-divider" />
        </div>
        <div className="flex flex-col gap-2">
          <a
            href="/v1/auth/oauth/google/start"
            className="rounded-md border border-divider px-4 py-2.5 text-sm text-center text-fg-primary hover:border-accent-aurora hover:text-accent-aurora transition-colors"
          >
            用 Google 登录
          </a>
          <a
            href="/v1/auth/oauth/github/start"
            className="rounded-md border border-divider px-4 py-2.5 text-sm text-center text-fg-primary hover:border-accent-aurora hover:text-accent-aurora transition-colors"
          >
            用 GitHub 登录
          </a>
        </div>
      </div>

      <p className="mt-10 text-xs text-fg-tertiary">
        <Link href="/" className="hover:text-fg-secondary">
          ← 回首页
        </Link>
      </p>
    </main>
  );
}
