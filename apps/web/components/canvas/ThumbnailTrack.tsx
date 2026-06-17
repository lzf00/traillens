"use client";

import { cn } from "@/lib/cn";
import { Check, X, AlertCircle } from "lucide-react";

export type AestheticScores = {
  overall: number;
  composition: number;
  visual_elements: number;
  technical: number;
  originality: number;
  theme: number;
  emotion: number;
  gestalt: number;
};

export type ThumbnailItem = {
  photo_id: string;
  uri: string;
  verdict?: "keep" | "reject" | "review" | null;
  overall?: number | null;
  aesthetic?: AestheticScores | null;
  critique?: string | null;
};

const verdictIcon = {
  keep: <Check size={12} className="text-accent-aurora" />,
  reject: <X size={12} className="text-accent-danger" />,
  review: <AlertCircle size={12} className="text-accent-golden" />,
};

export function ThumbnailTrack({
  items,
  selectedId,
  onSelect,
}: {
  items: ThumbnailItem[];
  selectedId?: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <aside className="flex w-56 shrink-0 flex-col gap-1 overflow-y-auto border-r border-divider bg-bg-base p-2">
      <h2 className="mono mb-2 px-2">缩略图 · {items.length}</h2>
      {items.map((it) => {
        const isSelected = it.photo_id === selectedId;
        return (
          <button
            key={it.photo_id}
            onClick={() => onSelect(it.photo_id)}
            className={cn(
              "flex items-center gap-2 rounded-md p-1.5 text-left",
              "transition-colors duration-DEFAULT ease-trail",
              isSelected ? "bg-bg-overlay ring-1 ring-accent-glacier" : "hover:bg-bg-raised",
            )}
          >
            <div className="photo-frame h-12 w-16 shrink-0 overflow-hidden bg-bg-overlay">
              {it.uri ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={it.uri}
                  alt={it.photo_id}
                  loading="lazy"
                  className="h-full w-full object-cover"
                />
              ) : null}
            </div>
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-xs text-fg-primary">{it.photo_id}</span>
              <span className="mono">
                {it.verdict ? verdictIcon[it.verdict] : "·"}
                <span className="ml-1">{it.overall?.toFixed(1) ?? "—"}</span>
              </span>
            </div>
          </button>
        );
      })}
    </aside>
  );
}
