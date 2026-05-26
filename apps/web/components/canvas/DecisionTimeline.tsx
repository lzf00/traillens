"use client";

/**
 * Decision Timeline — PRODUCT_PLAN §3.1 M4(Auditable Decisions)的前端组件。
 *
 * 用户点照片右上角的 (i) icon → 弹出此组件:
 *   每个 culling/human_review 节点写的 DecisionStep 按时间排开,
 *   evidence 字段(分数/置信度)展开为 mini-chart。
 */

import { cn } from "@/lib/cn";

export type DecisionStep = {
  actor: string;
  action: string;
  reason?: string | null;
  evidence?: Record<string, any>;
  at?: string | null;
};

const actorColor: Record<string, string> = {
  culling: "border-l-accent-glacier",
  human_review: "border-l-accent-golden",
  critic: "border-l-fg-primary",
};

export function DecisionTimeline({ steps }: { steps: DecisionStep[] }) {
  if (!steps || steps.length === 0) {
    return <div className="text-fg-tertiary text-sm">尚无决策记录</div>;
  }
  return (
    <ol className="flex flex-col gap-2">
      {steps.map((s, i) => (
        <li
          key={i}
          className={cn(
            "rounded-md border-l-2 bg-bg-raised p-3 text-sm",
            actorColor[s.actor] ?? "border-l-fg-tertiary",
          )}
        >
          <div className="flex items-center justify-between">
            <span className="mono">
              {s.actor} · <strong className="text-fg-primary">{s.action}</strong>
            </span>
            {s.at && <span className="mono text-fg-tertiary">{fmtTime(s.at)}</span>}
          </div>
          {s.reason && <div className="mt-1 text-fg-secondary">{s.reason}</div>}
          {s.evidence && Object.keys(s.evidence).length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(s.evidence).map(([k, v]) => (
                <span key={k} className="status-pill">
                  <span className="text-fg-tertiary">{k}</span>
                  <span className="text-fg-primary">{fmtValue(v)}</span>
                </span>
              ))}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return iso;
  }
}

function fmtValue(v: any): string {
  if (typeof v === "number") return v.toFixed(2);
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}
