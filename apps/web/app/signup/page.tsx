"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const r = await fetch("/v1/auth/sign-up", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name: name || null }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({ detail: "注册失败" }));
        setErr(j.detail || "注册失败");
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
        <h1 className="font-display text-3xl text-fg-primary mb-2">注册</h1>
        <p className="text-sm text-fg-tertiary">
          已有账号?{" "}
          <Link href="/login" className="text-accent-aurora hover:underline">
            登录 →
          </Link>
        </p>
      </header>

      <form onSubmit={submit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-xs text-fg-secondary mono">名字(可选)</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="昵称"
            className="rounded-md bg-bg-raised border border-divider px-3 py-2.5 text-fg-primary placeholder:text-fg-tertiary"
          />
        </label>

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
          {busy ? "注册中…" : "注册"}
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
