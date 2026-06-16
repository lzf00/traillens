"use client";

/**
 * /app/library — 跨 trail 的语义搜索界面。
 */

import { useEffect, useState } from "react";
import { Search } from "lucide-react";

type Hit = {
  photo_id: string;
  trail_id: string;
  trail_name: string;
  uri: string;
  score: number;
};

const EXAMPLES = ["秋天 川西 逆光", "冰川 蓝时刻 长曝", "草原 三分法 黄昏"];

export default function LibraryPage() {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!q.trim()) return;
    const handle = setTimeout(async () => {
      setLoading(true);
      const r = await fetch(`/v1/library/search?q=${encodeURIComponent(q)}&limit=30`);
      if (r.ok) setHits(await r.json());
      setLoading(false);
    }, 300);
    return () => clearTimeout(handle);
  }, [q]);

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <header className="mb-8">
        <h1 className="font-display text-3xl text-fg-primary mb-4">语义搜索</h1>

        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-tertiary" />
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="试试:川西秋天逆光 / 冰川蓝时刻 / 风光极简留白..."
            className="w-full rounded-lg bg-bg-raised border border-divider pl-10 pr-4 py-3 text-fg-primary placeholder:text-fg-tertiary"
          />
        </div>

        {!q && (
          <div className="mt-4 flex gap-2 flex-wrap">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => setQ(ex)}
                className="status-pill hover:text-fg-primary transition-colors"
              >
                {ex}
              </button>
            ))}
          </div>
        )}
      </header>

      {loading && <div className="mono">搜索中…</div>}

      {!loading && q && hits.length === 0 && (
        <div className="text-fg-tertiary text-sm">
          暂无结果。语义搜索 Sprint 5 末才接 pgvector,当前是 stub。
        </div>
      )}

      <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {hits.map((h) => (
          <a
            key={h.photo_id}
            href={`/app/trails/${h.trail_id}`}
            className="photo-frame aspect-square bg-bg-overlay relative group"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={h.uri} alt="" loading="lazy" className="h-full w-full object-cover" />
            <div className="absolute inset-x-2 bottom-2 flex justify-between opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="status-pill">{h.trail_name}</span>
              <span className="status-pill text-accent-aurora">{h.score.toFixed(2)}</span>
            </div>
          </a>
        ))}
      </section>
    </main>
  );
}
