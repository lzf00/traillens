"use client";

/**
 * /app/library — 跨 trail 的语义搜索界面。
 */

import { useEffect, useState } from "react";
import { Search, RefreshCw } from "lucide-react";
import { apiFetch } from "@/lib/api";

type Hit = {
  photo_id: string;
  trail_id: string;
  trail_name: string;
  uri: string;
  verdict?: string | null;
  overall?: number | null;
  score: number;
};

const EXAMPLES = ["雅拉", "雪山", "构图", "技术", "焦段"];

export default function LibraryPage() {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [loading, setLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [reindexMsg, setReindexMsg] = useState<string | null>(null);

  async function reindex() {
    if (reindexing) return;
    setReindexing(true);
    setReindexMsg(null);
    try {
      const r = await apiFetch("/v1/library/embed/all", { method: "POST" });
      if (r.ok) {
        const j = await r.json();
        setReindexMsg(`已索引 ${j.embedded} 张,跳过 ${j.skipped} 张`);
      } else if (r.status === 401) {
        setReindexMsg("请先登录");
      } else {
        setReindexMsg(`失败 HTTP ${r.status}`);
      }
    } catch (e: any) {
      setReindexMsg(`网络错误: ${e.message}`);
    } finally {
      setReindexing(false);
    }
  }

  useEffect(() => {
    if (!q.trim()) return;
    const handle = setTimeout(async () => {
      setLoading(true);
      const r = await apiFetch(`/v1/library/search?q=${encodeURIComponent(q)}&limit=30`);
      if (r.ok) setHits(await r.json());
      setLoading(false);
    }, 300);
    return () => clearTimeout(handle);
  }, [q]);

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <header className="mb-8">
        <div className="flex items-start justify-between mb-4 gap-4">
          <h1 className="font-display text-3xl text-fg-primary">语义搜索</h1>
          <button
            onClick={reindex}
            disabled={reindexing}
            className="flex items-center gap-1.5 rounded-md border border-divider px-3 py-1.5 text-xs text-fg-secondary hover:border-accent-aurora hover:text-accent-aurora transition-colors disabled:opacity-50"
            title="把所有 trail 的照片重新编码进语义索引(Run 跑完会自动做)"
          >
            <RefreshCw size={12} className={reindexing ? "animate-spin" : ""} />
            {reindexing ? "重建中…" : "重建索引"}
          </button>
        </div>
        {reindexMsg && (
          <div className="mb-3 mono text-xs text-fg-secondary">{reindexMsg}</div>
        )}

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
          暂无结果。如果是新加的照片,试试右上「重建索引」让它们进入语义搜索。
        </div>
      )}

      <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {hits.map((h) => (
          <a
            key={h.photo_id}
            href={`/trails/${h.trail_id}`}
            className="photo-frame aspect-square bg-bg-overlay relative group block overflow-hidden"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={h.uri}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover transition-transform duration-DEFAULT ease-trail group-hover:scale-[1.03]"
            />
            {h.verdict && (
              <span className="absolute top-2 left-2 status-pill backdrop-blur text-xs">
                {h.verdict}
              </span>
            )}
            <div className="absolute inset-x-2 bottom-2 flex justify-between gap-2">
              <span className="status-pill backdrop-blur truncate text-xs">
                {h.trail_name}
              </span>
              <span className="status-pill backdrop-blur text-accent-aurora text-xs shrink-0">
                {h.overall != null ? h.overall.toFixed(1) : (h.score * 100).toFixed(0) + "%"}
              </span>
            </div>
          </a>
        ))}
      </section>
    </main>
  );
}
