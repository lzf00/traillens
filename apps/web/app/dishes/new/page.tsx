"use client";

/**
 * /dishes/new — Example: recipe-helper 的 hello-world 页。
 *
 * 用户输食材 → POST /v1/recipe/suggest → 显示推荐 markdown。
 * 证明 template 上真能跑另一业务。
 */

import { useState } from "react";
import { ChefHat, Loader2, AlertCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";

export const dynamic = "force-dynamic";

type Dish = {
  name: string;
  difficulty?: number;
  recipe?: string;
  nutrition?: Record<string, any>;
};

export default function DishesNewPage() {
  const [ingredients, setIngredients] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dishes, setDishes] = useState<Dish[]>([]);
  const [md, setMd] = useState<string | null>(null);

  async function submit() {
    if (!ingredients.trim()) {
      setError("先输点食材");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const r = await apiFetch("/v1/recipe/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ingredients: ingredients.trim() }),
      });
      if (!r.ok) {
        setError(`HTTP ${r.status}${r.status === 401 ? "(先登录)" : ""}`);
        setBusy(false);
        return;
      }
      const data = await r.json();
      setDishes(data.dishes || []);
      setMd(data.travelogue_md || null);
    } catch (e: any) {
      setError(e.message || "网络错误");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-8">
        <p className="mono mb-2 text-fg-tertiary">EXAMPLE · recipe-helper</p>
        <h1 className="font-display text-3xl text-fg-primary mb-2 flex items-center gap-3">
          <ChefHat size={28} className="text-accent-golden" />
          今晚吃什么
        </h1>
        <p className="text-sm text-fg-secondary">
          输入你冰箱里有的食材,3 个 agent 节点(search / recipe-gen / nutrition)串行跑,
          出推荐 + 步骤 + 营养。所有节点当前是 stub(见
          <code className="mono text-xs mx-1">examples/recipe-helper/agents/business.py</code>),
          真接豆包/DeepSeek 是 fork 后你的事。
        </p>
      </header>

      <div className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-xs text-fg-secondary mono">食材(空格或逗号分隔)</span>
          <input
            value={ingredients}
            onChange={(e) => setIngredients(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
            placeholder="土豆 牛肉 胡萝卜"
            className="rounded-md bg-bg-raised border border-divider px-3 py-2.5 text-fg-primary placeholder:text-fg-tertiary"
            disabled={busy}
            autoFocus
          />
        </label>

        {error && (
          <div className="flex items-start gap-2 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <button
          onClick={submit}
          disabled={busy || !ingredients.trim()}
          className="rounded-md bg-accent-golden px-4 py-2.5 text-sm font-medium text-bg-base hover:bg-accent-golden/90 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
        >
          {busy && <Loader2 size={14} className="animate-spin" />}
          {busy ? "推荐中…" : "推荐 3 道菜"}
        </button>

        {dishes.length > 0 && (
          <section className="mt-6 flex flex-col gap-4">
            {dishes.map((d, i) => (
              <div key={i} className="rounded-md border border-divider bg-bg-raised p-4">
                <div className="flex items-baseline justify-between mb-2">
                  <h3 className="font-display text-lg text-fg-primary">{d.name}</h3>
                  {d.difficulty && (
                    <span className="status-pill">难度 {d.difficulty}/5</span>
                  )}
                </div>
                {d.recipe && <p className="text-sm text-fg-secondary whitespace-pre-wrap">{d.recipe}</p>}
                {d.nutrition && (
                  <p className="mt-2 mono text-xs text-fg-tertiary">
                    {Object.entries(d.nutrition).map(([k, v]) => `${k}=${v}`).join(" · ")}
                  </p>
                )}
              </div>
            ))}
            {md && (
              <details className="mt-2">
                <summary className="mono text-xs text-fg-tertiary cursor-pointer">看 nutrition_node 输出的 markdown</summary>
                <pre className="mt-2 rounded-md bg-bg-overlay p-3 text-xs whitespace-pre-wrap">{md}</pre>
              </details>
            )}
          </section>
        )}
      </div>
    </main>
  );
}
