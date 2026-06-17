"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/cn";
import {
  Play, Route, Filter, MessageCircle, FileText, Map, Check, AlertCircle,
} from "lucide-react";

export type TraceEntry = {
  ts: number;
  event: string;
  data: any;
};

const META: Record<
  string,
  { color: string; icon: any; label: string; summary: (d: any) => string }
> = {
  "run.started":           { color: "text-fg-secondary",   icon: Play,          label: "启动",     summary: () => "agent 已启动" },
  "orchestrator.routed":   { color: "text-accent-glacier", icon: Route,         label: "调度",     summary: (d) => `进入 ${d?.node ?? d?.trace ?? "节点"}` },
  "culling.progress":      { color: "text-fg-secondary",   icon: Filter,        label: "选片中",   summary: (d) => d?.summary ?? "评估照片…" },
  "culling.photo_scored":  { color: "text-accent-aurora",  icon: Check,         label: "打分",     summary: (d) => `${(d?.photo_id ?? "").slice(0, 8)} → ${d?.verdict ?? "?"} (${d?.overall?.toFixed?.(1) ?? "—"})` },
  "human_review.required": { color: "text-accent-golden",  icon: AlertCircle,   label: "需复核",   summary: (d) => d?.summary ?? "等待人工复核" },
  "critic.photo_critiqued":{ color: "text-fg-primary",     icon: MessageCircle, label: "点评",     summary: (d) => d?.summary ?? "AI 点评已写" },
  "story.delta":           { color: "text-fg-primary",     icon: FileText,      label: "游记",     summary: (d) => `+${String(d?.chunk ?? "").slice(0, 40)}…` },
  "planner.plan_ready":    { color: "text-accent-glacier", icon: Map,           label: "拍摄计划", summary: (d) => `已生成 ${Object.keys(d?.plan ?? {}).length} 项建议` },
  "run.finished":          { color: "text-accent-aurora",  icon: Check,         label: "完成",     summary: (d) => `保留 ${d?.kept ?? "?"} / ${d?.total ?? "?"} 张` },
  "run.error":             { color: "text-accent-danger",  icon: AlertCircle,   label: "错误",     summary: (d) => `${d?.phase ?? ""}: ${d?.error ?? "未知"}` },
};

function fmtTime(ts: number) {
  return new Date(ts).toLocaleTimeString("zh-CN", { hour12: false });
}

export function AgentTrace({ entries }: { entries: TraceEntry[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [entries.length]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 text-xs">
      {entries.map((e, i) => {
        const m = META[e.event] ?? {
          color: "text-fg-secondary",
          icon: Route,
          label: e.event,
          summary: (d: any) => (typeof d === "string" ? d : JSON.stringify(d)),
        };
        const Icon = m.icon;
        return (
          <div key={i} className="mb-3 flex gap-2">
            <Icon size={14} className={cn("mt-0.5 shrink-0", m.color)} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className={cn("font-medium", m.color)}>{m.label}</span>
                <span className="mono text-fg-tertiary">{fmtTime(e.ts)}</span>
              </div>
              <div className="mt-0.5 text-fg-secondary break-words">
                {m.summary(e.data)}
              </div>
            </div>
          </div>
        );
      })}
      {entries.length === 0 && (
        <div className="text-fg-tertiary mono">等待 agent 启动…</div>
      )}
    </div>
  );
}
