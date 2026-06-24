"use client";

/**
 * /app/library — 跨 trail 的语义搜索界面。
 *
 * URL query 支持 ?trail=<uuid>:进入页面时预选该 trail(从 Canvas 跳过来)。
 */

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Search, RefreshCw } from "lucide-react";
import { apiFetch } from "@/lib/api";

export const dynamic = "force-dynamic";

type Hit = {
  photo_id: string;
  trail_id: string;
  trail_name: string;
  uri: string;
  verdict?: string | null;
  overall?: number | null;
  score: number;
};

type Trail = { id: string; name: string; photo_count: number };

const EXAMPLES = ["雅拉", "雪山", "构图", "技术", "焦段"];

export default function LibraryPage() {
  const params = useSearchParams();
  const initialTrail = params?.get("trail") ?? "";

  const [q, setQ] = useState("");
  const [trailId, setTrailId] = useState<string>(initialTrail);
  const [trails, setTrails] = useState<Trail[]>([]);
  const [hits, setHits] = useState<Hit[]>([]);
  const [loading, setLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [reindexMsg, setReindexMsg] = useState<string | null>(null);

  // 加载用户全部 trails 给筛选下拉
  useEffect(() => {
    apiFetch("/v1/trails")
      .then((r) => (r.ok ? r.json() : []))
      .then(setTrails)
      .catch(() => {});
  }, []);

  // 防抖搜
  useEffect(() => {
    if (!q.trim()) {
      setHits([]);
      return;
    }
    const handle = setTimeout(async () => {
      setLoading(true);
      const url = `/v1/library/search?q=${encodeURIComponent(q)}&limit=30${
        trailId ? `&trail_id=${trailId}` : ""
      }`;
      const r = await apiFetch(url);
      if (r.ok) setHits(await r.json());
      setLoading(false);
    }, 300);
    return () => clearTimeout(handle);
  }, [q, trailId]);

  async function reindex() {
    if (reindexing) return;
    setReindexing(true);
    setReindexMsg(null);
    try {
      const r = await apiFetch(
        trailId ? `/v1/library/embed/${trailId}` : "/v1/library/embed/all",
        { method: "POST" }
      );
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

  // 按 trail 分组结果
  const grouped = useMemo(() => {
    const m = new Map<string, { name: string; items: Hit[] }>();
    for (const h of hits) {
      const k = h.trail_id;
      if (!m.has(k)) m.set(k, { name: h.trail_name, items: [] });
      m.get(k)!.items.push(h);
    }
    return Array.from(m.entries()).map(([id, v]) => ({ id, ...v }));
  }, [hits]);

  const activeTrailName = trails.find((t) => t.id === trailId)?.name;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <header className="mb-8">
        <div className="flex items-start justify-between mb-4 gap-4">
          <div>
            <h1 className="font-display text-3xl text-fg-primary">语义搜索</h1>
            {activeTrailName && (
              <p className="mt-1 text-sm text-fg-tertiary">
                范围:{activeTrailName} ·
                <button
                  onClick={() => setTrailId("")}
                  className="ml-2 text-accent-aurora hover:underline"
                >
                  清除筛选
                </button>
              </p>
            )}
          </div>
          <button
            onClick={reindex}
            disabled={reindexing}
            className="flex items-center gap-1.5 rounded-md border border-divider px-3 py-1.5 text-xs text-fg-secondary hover:border-accent-aurora hover:text-accent-aurora transition-colors disabled:opacity-50"
            title={trailId ? "重建当前 trail 的索引" : "重建所有 trail 的索引"}
          >
            <RefreshCw size={12} className={reindexing ? "animate-spin" : ""} />
            {reindexing ? "重建中…" : "重建索引"}
          </button>
        </div>
        {reindexMsg && (
          <div className="mb-3 mono text-xs text-fg-secondary">{reindexMsg}</div>
        )}

        <div className="flex gap-2 items-stretch">
          <div className="relative flex-1">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-tertiary"
            />
            <input
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="试试:川西秋天逆光 / 冰川蓝时刻 / 风光极简留白..."
              className="w-full rounded-lg bg-bg-raised border border-divider pl-10 pr-4 py-3 text-fg-primary placeholder:text-fg-tertiary"
            />
          </div>
          {trails.length > 0 && (
            <select
              value={trailId}
              onChange={(e) => setTrailId(e.target.value)}
              className="rounded-lg bg-bg-raised border border-divider px-3 py-3 text-sm text-fg-primary max-w-[200px]"
              title="按 trail 筛选"
            >
              <option value="">全部 trails ({trails.length})</option>
              {trails.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.photo_count})
                </option>
              ))}
            </select>
          )}
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
          暂无结果。新加的照片如果没出现,试试右上「重建索引」。
        </div>
      )}

      {grouped.map((g) => (
        <section key={g.id} className="mb-10">
          <h2 className="font-display text-lg text-fg-primary mb-3 flex items-baseline gap-3">
            <a
              href={`/trails/${g.id}`}
              className="hover:text-accent-aurora transition-colors"
            >
              {g.name}
            </a>
            <span className="text-xs text-fg-tertiary mono">{g.items.length} 张</span>
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {g.items.map((h) => (
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
                  <span className="status-pill backdrop-blur text-accent-aurora text-xs shrink-0">
                    {h.overall != null
                      ? h.overall.toFixed(1)
                      : (h.score * 100).toFixed(0) + "%"}
                  </span>
                </div>
              </a>
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}
