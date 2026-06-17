"use client";

/**
 * Trail 主舞台(Canvas)。PRODUCT_PLAN.md §3.2 的实现。
 *
 * 布局:
 *   ┌─────────────────────────────────────────────┐
 *   │ Header(trail 名 / 进度 pill)                  │
 *   ├──────────┬────────────────────┬─────────────┤
 *   │ Track    │ 主舞台(大图+雷达)   │ Agent Trace │
 *   └──────────┴────────────────────┴─────────────┘
 *
 * 键盘:
 *   j/k 上下选片 · x 拒 · k 留 · ? 帮助 · ⌘K 命令面板(Sprint 5)
 */
import { use, useCallback, useEffect, useState } from "react";
import { ThumbnailTrack, type ThumbnailItem } from "@/components/canvas/ThumbnailTrack";
import { ScoreRadar } from "@/components/canvas/ScoreRadar";
import { AgentTrace, type TraceEntry } from "@/components/agent/AgentTrace";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api";
import { streamSse } from "@/lib/sse";
import { Play, Square, MoreVertical, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";

export default function TrailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  // Next.js 15: params is now a Promise; use React.use() in client components
  const { id: trailId } = use(params);
  const [trailName, setTrailName] = useState<string>("");
  const [travelogueMd, setTravelogueMd] = useState<string | null>(null);
  const [nextTripPlan, setNextTripPlan] = useState<Record<string, any> | null>(null);
  const [photos, setPhotos] = useState<ThumbnailItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [running, setRunning] = useState(false);

  // 首次进页面：拉 trail 详情 + 已有照片
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [tr, ph] = await Promise.all([
          apiFetch(`/v1/trails/${trailId}`),
          apiFetch(`/v1/trails/${trailId}/photos`),
        ]);
        if (cancelled) return;
        if (tr.ok) {
          const t = await tr.json();
          setTrailName(t.name);
          setTravelogueMd(t.travelogue_md ?? null);
          setNextTripPlan(t.next_trip_plan ?? null);
        }
        if (ph.ok) {
          const arr: Array<{
            photo_id: string;
            uri: string;
            verdict?: string;
            aesthetic?: any;
            critique?: string;
          }> = await ph.json();
          setPhotos(
            arr.map(
              (p) =>
                ({
                  photo_id: p.photo_id,
                  uri: p.uri,
                  verdict: p.verdict,
                  overall: p.aesthetic?.overall,
                  aesthetic: p.aesthetic ?? null,
                  critique: p.critique ?? null,
                }) as ThumbnailItem
            )
          );
        }
      } catch {}
    })();
    return () => {
      cancelled = true;
    };
  }, [trailId]);

  const onRun = useCallback(async () => {
    if (running) return;
    setRunning(true);
    setTrace([]);
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || "";
      const uid =
        typeof document !== "undefined"
          ? document.cookie.match(/(?:^|;\s*)traillens_user_id=([^;]+)/)?.[1]
          : null;
      for await (const ev of streamSse(`${base}/v1/trails/${trailId}/run`, {
        headers: uid ? { "X-Dev-User-Id": decodeURIComponent(uid) } : undefined,
      })) {
        setTrace((prev) => [...prev, { ts: Date.now(), event: ev.event, data: ev.data }]);

        if (ev.event === "culling.photo_scored" && ev.data?.photo_id) {
          setPhotos((prev) => {
            const next = [...prev];
            const i = next.findIndex((p) => p.photo_id === ev.data.photo_id);
            const item: ThumbnailItem = {
              photo_id: ev.data.photo_id,
              uri: ev.data.uri ?? "",
              verdict: ev.data.verdict,
              overall: ev.data.overall,
            };
            if (i >= 0) next[i] = { ...next[i], ...item };
            else next.push(item);
            return next;
          });
        }

        if (ev.event === "run.finished") {
          setRunning(false);
          // 兜底:即使 SSE 的 culling.photo_scored 漏推,从 DB 拉一次最新分数
          // 同时 refetch trail 拿最新游记 + 拍摄计划
          try {
            const trRes = await apiFetch(`/v1/trails/${trailId}`);
            if (trRes.ok) {
              const t = await trRes.json();
              setTravelogueMd(t.travelogue_md ?? null);
              setNextTripPlan(t.next_trip_plan ?? null);
            }
            const r = await apiFetch(`/v1/trails/${trailId}/photos`);
            if (r.ok) {
              const arr: Array<{
                photo_id: string;
                uri: string;
                verdict?: string;
                aesthetic?: any;
                critique?: string;
              }> = await r.json();
              setPhotos(
                arr.map(
                  (p) =>
                    ({
                      photo_id: p.photo_id,
                      uri: p.uri,
                      verdict: p.verdict,
                      overall: p.aesthetic?.overall,
                      aesthetic: p.aesthetic ?? null,
                      critique: p.critique ?? null,
                    }) as ThumbnailItem
                )
              );
            }
          } catch {}
        }
      }
    } catch (err) {
      console.error(err);
      setRunning(false);
    }
  }, [trailId, running]);

  // 键盘快捷键(Linear/Raycast 风格)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      const idx = photos.findIndex((p) => p.photo_id === selectedId);
      if (e.key === "j" && idx < photos.length - 1) setSelectedId(photos[idx + 1].photo_id);
      if (e.key === "k" && idx > 0) setSelectedId(photos[idx - 1].photo_id);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [photos, selectedId]);

  const selected = photos.find((p) => p.photo_id === selectedId) ?? photos[0];
  const [menuOpen, setMenuOpen] = useState(false);

  async function onRename() {
    const next = prompt("新名称", trailName);
    if (!next || next.trim() === trailName) return;
    const r = await apiFetch(`/v1/trails/${trailId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: next.trim() }),
    });
    if (r.ok) setTrailName(next.trim());
  }

  async function onDelete() {
    if (!confirm(`确定删除「${trailName}」?该 trail 的所有照片也会被删除,不可恢复。`)) return;
    const r = await apiFetch(`/v1/trails/${trailId}`, { method: "DELETE" });
    if (r.ok) router.push("/trails");
  }

  return (
    <div className="flex h-dvh flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-divider px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="font-display text-lg">{trailName || `Trail · ${trailId.slice(0, 8)}`}</span>
          <span className="status-pill">{photos.length} 张 · {trace.length} 事件</span>
        </div>
        <div className="flex gap-2 items-center relative">
          <a
            href={`/trails/${trailId}/share`}
            target="_blank"
            rel="noreferrer"
            className="rounded-md border border-divider px-3 py-1.5 text-xs text-fg-secondary hover:border-accent-aurora hover:text-accent-aurora transition-colors"
          >
            分享页
          </a>
          {!running ? (
            <Button onClick={onRun}>
              <Play size={14} /> Run
            </Button>
          ) : (
            <Button variant="danger" disabled>
              <Square size={14} /> 运行中
            </Button>
          )}
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="rounded-md border border-divider px-2 py-1.5 text-fg-secondary hover:border-accent-aurora hover:text-accent-aurora transition-colors"
            aria-label="trail 菜单"
          >
            <MoreVertical size={14} />
          </button>
          {menuOpen && (
            <div
              className="absolute right-0 top-full mt-1 z-10 min-w-[140px] rounded-md border border-divider bg-bg-raised shadow-lg"
              onMouseLeave={() => setMenuOpen(false)}
            >
              <button
                onClick={() => { setMenuOpen(false); onRename(); }}
                className="flex items-center gap-2 w-full px-3 py-2 text-xs text-fg-secondary hover:bg-bg-overlay hover:text-fg-primary text-left"
              >
                <Pencil size={12} /> 重命名
              </button>
              <button
                onClick={() => { setMenuOpen(false); onDelete(); }}
                className="flex items-center gap-2 w-full px-3 py-2 text-xs text-accent-danger hover:bg-bg-overlay text-left"
              >
                <Trash2 size={12} /> 删除 Trail
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <ThumbnailTrack items={photos} selectedId={selected?.photo_id} onSelect={setSelectedId} />

        <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
          <div className="photo-frame relative flex h-[60vh] w-full max-w-3xl items-center justify-center overflow-hidden bg-bg-overlay">
            {selected?.uri ? (
              <>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={selected.uri}
                  alt={selected.photo_id}
                  className="h-full w-full object-contain"
                />
                {selected.verdict && (
                  <span className="absolute top-3 right-3 status-pill backdrop-blur capitalize">
                    {selected.verdict}
                  </span>
                )}
                {selected.overall != null && (
                  <span className="absolute bottom-3 right-3 status-pill backdrop-blur">
                    {selected.overall.toFixed(1)}
                  </span>
                )}
              </>
            ) : (
              <span className="font-display text-2xl text-fg-tertiary">
                {selected ? selected.photo_id : "选择一张照片"}
              </span>
            )}
          </div>
          {selected?.aesthetic && (
            <ScoreRadar scores={selected.aesthetic} />
          )}
          {selected?.critique && (
            <div className="max-w-2xl w-full rounded-md border border-divider bg-bg-raised p-4">
              <h3 className="mono mb-2 text-fg-secondary">AI 点评</h3>
              <p className="text-sm text-fg-primary leading-relaxed">{selected.critique}</p>
            </div>
          )}
          <div className="mono">
            <kbd>j</kbd>/<kbd>k</kbd> 切换 · <kbd>?</kbd> 帮助
          </div>
        </main>

        <RightPanel
          trace={trace}
          travelogueMd={travelogueMd}
          nextTripPlan={nextTripPlan}
        />
      </div>
    </div>
  );
}

function RightPanel({
  trace,
  travelogueMd,
  nextTripPlan,
}: {
  trace: TraceEntry[];
  travelogueMd: string | null;
  nextTripPlan: Record<string, any> | null;
}) {
  const tabs = [
    { key: "trace" as const, label: `Trace · ${trace.length}` },
    { key: "story" as const, label: travelogueMd ? "游记" : "游记 ·" },
    { key: "plan" as const, label: nextTripPlan ? "拍摄计划" : "计划 ·" },
  ];
  const [active, setActive] = useState<"trace" | "story" | "plan">("trace");
  return (
    <aside className="flex w-96 shrink-0 flex-col border-l border-divider bg-bg-base">
      <div className="flex border-b border-divider">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActive(t.key)}
            className={
              "flex-1 px-3 py-2 text-xs mono transition-colors " +
              (active === t.key
                ? "text-fg-primary border-b-2 border-accent-aurora"
                : "text-fg-tertiary hover:text-fg-secondary")
            }
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto">
        {active === "trace" && <AgentTrace entries={trace} />}
        {active === "story" && (
          <div className="p-4">
            {travelogueMd ? (
              <article className="prose prose-invert prose-sm max-w-none whitespace-pre-wrap text-fg-primary">
                {travelogueMd}
              </article>
            ) : (
              <p className="mono text-fg-tertiary">游记会在 Run 跑完后生成。</p>
            )}
          </div>
        )}
        {active === "plan" && (
          <div className="p-4">
            {nextTripPlan ? (
              <dl className="flex flex-col gap-3 text-sm">
                {Object.entries(nextTripPlan).map(([k, v]) => (
                  <div key={k} className="flex flex-col gap-1">
                    <dt className="mono text-fg-tertiary">{k}</dt>
                    <dd className="text-fg-primary">
                      {Array.isArray(v)
                        ? v.map(String).join("、")
                        : typeof v === "object" && v !== null
                          ? JSON.stringify(v, null, 2)
                          : String(v)}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="mono text-fg-tertiary">下次拍摄计划会在 Run 跑完后生成。</p>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
