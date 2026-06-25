"use client";

/**
 * /app/settings — 账号、API token、PIAA 偏好、订阅。
 */

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { UpgradeButton } from "@/components/ui/UpgradeButton";
import { Copy, Trash2, Plus, Cpu } from "lucide-react";

type TokenInfo = { id: string; label: string; prefix: string; created_at: string };

type TrainStats = {
  total_photos: number;
  annotated: number;
  prefilled: number;
  target: number;
  ready_to_train: boolean;
};

type TrailHealth = {
  id: string;
  name: string;
  total: number;
  scored: number;
  keeps: number;
  critiqued: number;
  embedded: number;
};

export default function SettingsPage() {
  const [tokens, setTokens] = useState<TokenInfo[]>([]);
  const [newSecret, setNewSecret] = useState<string | null>(null);
  const [newLabel, setNewLabel] = useState("Lightroom Plugin");
  const [trainStats, setTrainStats] = useState<TrainStats | null>(null);
  const [health, setHealth] = useState<TrailHealth[]>([]);
  const [reembedAllBusy, setReembedAllBusy] = useState(false);
  const [reembedMsg, setReembedMsg] = useState<string | null>(null);

  useEffect(() => {
    fetch("/v1/settings/tokens").then((r) => r.json()).then(setTokens).catch(() => {});
    fetch("/annotate/api/stats")
      .then((r) => (r.ok ? r.json() : null))
      .then(setTrainStats)
      .catch(() => {});
    fetch("/v1/trails/_health")
      .then((r) => (r.ok ? r.json() : { trails: [] }))
      .then((d) => setHealth(d.trails ?? []))
      .catch(() => {});
  }, []);

  async function reembedAll() {
    if (reembedAllBusy) return;
    setReembedAllBusy(true);
    setReembedMsg(null);
    try {
      const r = await fetch("/v1/library/embed/all", { method: "POST" });
      if (r.ok) {
        const j = await r.json();
        setReembedMsg(`已索引 ${j.embedded} 张,跳过 ${j.skipped} 张`);
        // 刷新健康面板
        const hr = await fetch("/v1/trails/_health");
        if (hr.ok) setHealth((await hr.json()).trails ?? []);
      } else {
        setReembedMsg(`失败 HTTP ${r.status}`);
      }
    } catch (e: any) {
      setReembedMsg(`网络错误: ${e.message}`);
    } finally {
      setReembedAllBusy(false);
    }
  }

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
        <div className="status-pill">{trainStats?.annotated ?? 0} / 50</div>
      </Section>

      <Section title="数据健康">
        <p className="text-fg-secondary text-sm mb-3 flex items-center justify-between gap-3">
          <span>每个 trail 的 photos / scored / keep / critique / embedding 计数。embedding 不齐全的话语义搜索会漏。</span>
          <button
            onClick={reembedAll}
            disabled={reembedAllBusy}
            className="shrink-0 rounded-md border border-divider px-3 py-1 text-xs text-fg-secondary hover:border-accent-aurora hover:text-accent-aurora disabled:opacity-50 transition-colors"
          >
            {reembedAllBusy ? "重建中…" : "一键重建全部索引"}
          </button>
        </p>
        {reembedMsg && (
          <div className="mono text-xs text-fg-secondary mb-2">{reembedMsg}</div>
        )}
        {health.length === 0 ? (
          <p className="text-fg-tertiary text-sm">还没有 trail。</p>
        ) : (
          <div className="rounded-md border border-divider overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-bg-raised text-fg-tertiary mono">
                <tr>
                  <th className="text-left px-3 py-2 font-normal">名称</th>
                  <th className="text-right px-3 py-2 font-normal">总数</th>
                  <th className="text-right px-3 py-2 font-normal">已评</th>
                  <th className="text-right px-3 py-2 font-normal">keep</th>
                  <th className="text-right px-3 py-2 font-normal">点评</th>
                  <th className="text-right px-3 py-2 font-normal">索引</th>
                </tr>
              </thead>
              <tbody>
                {health.map((t) => {
                  const allEmbed = t.critiqued > 0 && t.embedded === t.critiqued;
                  return (
                    <tr key={t.id} className="border-t border-divider">
                      <td className="px-3 py-2">
                        <a href={`/trails/${t.id}`} className="text-fg-primary hover:text-accent-aurora truncate inline-block max-w-[260px]">
                          {t.name}
                        </a>
                      </td>
                      <td className="text-right px-3 py-2 mono text-fg-secondary">{t.total}</td>
                      <td className="text-right px-3 py-2 mono text-fg-secondary">{t.scored}</td>
                      <td className="text-right px-3 py-2 mono text-accent-aurora">{t.keeps}</td>
                      <td className="text-right px-3 py-2 mono text-fg-secondary">{t.critiqued}</td>
                      <td className={"text-right px-3 py-2 mono " + (allEmbed ? "text-accent-aurora" : "text-fg-tertiary")}>
                        {t.embedded}{t.critiqued > 0 && t.embedded < t.critiqued ? "⚠" : ""}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {/* Aesthetic LoRA 训练状态 */}
      <Section title="美学模型 LoRA 训练">
        {trainStats ? (
          <div className="flex flex-col gap-4">
            <div className="rounded-md border border-divider p-4 bg-bg-raised">
              <div className="flex items-center gap-2 mb-3 text-fg-secondary">
                <Cpu size={14} />
                <span className="text-sm">数据集进度</span>
                <span className="ml-auto mono text-xs text-fg-tertiary">
                  目标 {trainStats.target} 张
                </span>
              </div>
              <div className="h-2 rounded-full bg-bg-overlay overflow-hidden mb-2">
                <div
                  className="h-full bg-accent-aurora transition-all"
                  style={{
                    width: `${Math.min(100, (trainStats.annotated / trainStats.target) * 100)}%`,
                  }}
                />
              </div>
              <div className="flex justify-between text-xs text-fg-tertiary mono">
                <span>已标 {trainStats.annotated}</span>
                <span>预填 {trainStats.prefilled}</span>
                <span>总样本 {trainStats.total_photos}</span>
              </div>
            </div>

            <div className="rounded-md border border-divider p-4 text-sm">
              <p className="text-fg-secondary mb-3">
                {trainStats.ready_to_train
                  ? "✅ 数据量足够,可启动 LoRA 训练。"
                  : `还需 ${Math.max(0, trainStats.target - trainStats.annotated)} 张标注。`}
              </p>
              <p className="text-fg-tertiary text-xs mb-3 mono">
                下一步(本地 / Modal GPU):
              </p>
              <pre className="mono text-xs bg-bg-raised rounded p-3 overflow-x-auto text-fg-secondary">
{`# 1. 导出训练 manifest(80/10/10 split)
ssh root@traillens '\\
  docker exec traillens-annotation \\
  python /app/server/export_manifest.py'

# 2. 本地 LoRA 训练(需要 GPU)
python packages/aesthetic/train_qalign_lora.py

# 3. Modal 云上训练(无需本地 GPU)
modal run packages/aesthetic/train_modal.py`}
              </pre>
            </div>
          </div>
        ) : (
          <p className="text-fg-tertiary text-sm">标注后台离线,无法读取训练状态。</p>
        )}
      </Section>

      <Section title="数据集标注工具">
        <p className="text-fg-secondary text-sm mb-3">
          给 LoRA 训练造真值标签 · 8 维评分 · 键盘快捷键打分 · 仅限授权邮箱访问
        </p>
        <a
          href="/annotate/"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-md bg-bg-raised border border-divider px-4 py-2 text-sm text-fg-primary hover:border-accent-aurora hover:text-accent-aurora transition-colors"
        >
          打开标注后台 →
        </a>
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
