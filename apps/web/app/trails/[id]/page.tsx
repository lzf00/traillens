"use client";

// Skip prerender — next-intl loads messages per request
export const dynamic = "force-dynamic";

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
import { streamSse } from "@/lib/sse";
import { Play, Square } from "lucide-react";

export default function TrailPage({ params }: { params: Promise<{ id: string }> }) {
  // Next.js 15: params is now a Promise; use React.use() in client components
  const { id: trailId } = use(params);
  const [photos, setPhotos] = useState<ThumbnailItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [running, setRunning] = useState(false);

  const onRun = useCallback(async () => {
    if (running) return;
    setRunning(true);
    setTrace([]);
    try {
      for await (const ev of streamSse(`/v1/trails/${trailId}/run`)) {
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

  return (
    <div className="flex h-dvh flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-divider px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="font-display text-lg">Trail · {trailId}</span>
          <span className="status-pill">{photos.length} 张 · {trace.length} 事件</span>
        </div>
        <div className="flex gap-2">
          {!running ? (
            <Button onClick={onRun}>
              <Play size={14} /> Run
            </Button>
          ) : (
            <Button variant="danger" disabled>
              <Square size={14} /> 运行中
            </Button>
          )}
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <ThumbnailTrack items={photos} selectedId={selected?.photo_id} onSelect={setSelectedId} />

        <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
          <div className="photo-frame flex h-[60vh] w-full max-w-2xl items-center justify-center bg-bg-overlay">
            <span className="font-display text-2xl text-fg-tertiary">
              {selected ? selected.photo_id : "选择一张照片"}
            </span>
          </div>
          {selected?.overall != null && (
            <ScoreRadar
              scores={{
                overall: selected.overall,
                composition: selected.overall,
                visual_elements: selected.overall,
                technical: selected.overall,
                originality: selected.overall,
                theme: selected.overall,
                emotion: selected.overall,
                gestalt: selected.overall,
              }}
            />
          )}
          <div className="mono">
            <kbd>j</kbd>/<kbd>k</kbd> 切换 · <kbd>?</kbd> 帮助
          </div>
        </main>

        <AgentTrace entries={trace} />
      </div>
    </div>
  );
}
