"use client";

/**
 * /app/settings — 账号、API token、PIAA 偏好、订阅。
 */

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { UpgradeButton } from "@/components/ui/UpgradeButton";
import { Copy, Trash2, Plus } from "lucide-react";

type TokenInfo = { id: string; label: string; prefix: string; created_at: string };

export default function SettingsPage() {
  const [tokens, setTokens] = useState<TokenInfo[]>([]);
  const [newSecret, setNewSecret] = useState<string | null>(null);
  const [newLabel, setNewLabel] = useState("Lightroom Plugin");

  useEffect(() => {
    fetch("/v1/settings/tokens").then((r) => r.json()).then(setTokens).catch(() => {});
  }, []);

  async function createToken() {
    if (!newLabel.trim()) return;
    const r = await fetch("/v1/settings/tokens", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: newLabel }),
    });
    if (!r.ok) return;
    const data = await r.json();
    setNewSecret(data.token);
    setTokens((prev) => [...prev, data]);
  }

  async function revoke(id: string) {
    if (!confirm("撤销后不可恢复。继续?")) return;
    const r = await fetch(`/v1/settings/tokens/${id}`, { method: "DELETE" });
    if (r.ok) setTokens((prev) => prev.filter((t) => t.id !== id));
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <header className="mb-12">
        <h1 className="font-display text-4xl text-fg-primary">Settings</h1>
      </header>

      <Section title="订阅">
        <div className="rounded-md border border-divider p-4">
          <p className="text-fg-secondary text-sm mb-3">当前 Free 计划 · 50 张/月</p>
          <div className="flex gap-2">
            <UpgradeButton plan="pro">升级 Pro · $19/月</UpgradeButton>
            <UpgradeButton plan="pro_plus">升级 Pro+ · $49/月</UpgradeButton>
          </div>
        </div>
      </Section>

      <Section title="API Tokens">
        <p className="text-fg-secondary text-sm mb-3">用于 Lightroom 插件 / 自动化脚本 / 自研工具。</p>

        <div className="flex gap-2 mb-4">
          <input
            className="flex-1 rounded-md bg-bg-raised border border-divider px-3 py-2 text-sm"
            placeholder="Lightroom"
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
          />
          <Button onClick={createToken}><Plus size={14} /> 创建</Button>
        </div>

        {newSecret && (
          <div className="mb-4 rounded-md border border-accent-aurora bg-accent-aurora/10 p-3">
            <p className="mono text-xs text-fg-secondary mb-2">⚠ 这是 token 唯一显示的机会。立即复制。</p>
            <div className="flex items-center gap-2">
              <code className="mono text-xs text-accent-aurora flex-1 break-all">{newSecret}</code>
              <Button variant="ghost" onClick={() => navigator.clipboard.writeText(newSecret)}>
                <Copy size={14} />
              </Button>
            </div>
          </div>
        )}

        <ul className="flex flex-col gap-1">
          {tokens.map((tok) => (
            <li
              key={tok.id}
              className="flex items-center justify-between rounded-md bg-bg-raised px-3 py-2 text-sm"
            >
              <div>
                <span className="text-fg-primary">{tok.label}</span>{" "}
                <code className="mono ml-2">{tok.prefix}…</code>
              </div>
              <Button variant="danger" onClick={() => revoke(tok.id)}>
                <Trash2 size={14} />
              </Button>
            </li>
          ))}
          {tokens.length === 0 && (
            <li className="text-fg-tertiary text-sm">尚无 token</li>
          )}
        </ul>
      </Section>

      <Section title="个人风格偏好(PIAA)">
        <p className="text-fg-secondary text-sm mb-3">标注 50 张以上后,我们会为你训练专属美学评分模型。</p>
        <div className="status-pill">0 / 50</div>
      </Section>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-12">
      <h2 className="font-display text-xl text-fg-primary mb-3 border-b border-divider pb-2">
        {title}
      </h2>
      {children}
    </section>
  );
}
