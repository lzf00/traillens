"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/cn";

export type TraceEntry = {
  ts: number;
  event: string;
  data: any;
};

const eventColor: Record<string, string> = {
  "orchestrator.routed": "text-accent-glacier",
  "culling.progress": "text-fg-secondary",
  "culling.photo_scored": "text-accent-aurora",
  "human_review.required": "text-accent-golden",
  "critic.photo_critiqued": "text-fg-primary",
  "story.delta": "text-fg-primary",
  "planner.plan_ready": "text-accent-glacier",
  "run.finished": "text-accent-aurora",
  "run.error": "text-accent-danger",
};

export function AgentTrace({ entries }: { entries: TraceEntry[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [entries.length]);

  return (
    <aside className="flex w-80 shrink-0 flex-col border-l border-divider bg-bg-base">
      <header className="border-b border-divider p-3">
        <h2 className="mono">Agent Trace · {entries.length}</h2>
      </header>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 text-xs">
        {entries.map((e, i) => (
          <div key={i} className="mb-2 font-mono">
            <div className={cn("font-medium", eventColor[e.event] ?? "text-fg-secondary")}>
              {e.event}
            </div>
            <div className="ml-2 text-fg-tertiary break-all">
              {typeof e.data === "string" ? e.data : JSON.stringify(e.data)}
            </div>
          </div>
        ))}
        {entries.length === 0 && (
          <div className="text-fg-tertiary">等待 agent 启动…</div>
        )}
      </div>
    </aside>
  );
}
