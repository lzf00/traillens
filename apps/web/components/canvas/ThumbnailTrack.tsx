"use client";

import { useRef } from "react";
import { cn } from "@/lib/cn";
import { Check, X, AlertCircle, Plus, Trash2 } from "lucide-react";

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
  thumb_uri?: string | null;
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
  onAppend,
  onDelete,
  selectedIds,
  onToggleMulti,
}: {
  items: ThumbnailItem[];
  selectedId?: string | null;
  onSelect: (id: string) => void;
  onAppend?: (files: FileList) => void;
  onDelete?: (id: string) => void;
  selectedIds?: Set<string>;
  onToggleMulti?: (id: string) => void;
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  return (
    <aside className="flex w-56 shrink-0 flex-col gap-1 overflow-y-auto border-r border-divider bg-bg-base p-2">
      <div className="flex items-center justify-between mb-2 px-2">
        <h2 className="mono">缩略图 · {items.length}</h2>
        {onAppend && (
          <>
            <button
              onClick={() => fileInput.current?.click()}
              className="text-fg-tertiary hover:text-accent-aurora transition-colors"
              title="补传照片"
            >
              <Plus size={14} />
            </button>
            <input
              ref={fileInput}
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.length) onAppend(e.target.files);
                e.target.value = "";
              }}
            />
          </>
        )}
      </div>
      {items.map((it) => {
        const isSelected = it.photo_id === selectedId;
        const isChecked = selectedIds?.has(it.photo_id) ?? false;
        return (
          <div
            key={it.photo_id}
            className={cn(
              "group relative flex items-center gap-2 rounded-md p-1.5",
              "transition-colors duration-DEFAULT ease-trail",
              isSelected ? "bg-bg-overlay ring-1 ring-accent-glacier" : "hover:bg-bg-raised",
              isChecked && "ring-1 ring-accent-aurora",
            )}
          >
            {onToggleMulti && (
              <input
                type="checkbox"
                checked={isChecked}
                onChange={() => onToggleMulti(it.photo_id)}
                className="accent-accent-aurora cursor-pointer"
                onClick={(e) => e.stopPropagation()}
              />
            )}
            <button
              onClick={() => onSelect(it.photo_id)}
              className="flex flex-1 items-center gap-2 text-left min-w-0"
            >
              <div className="photo-frame h-12 w-16 shrink-0 overflow-hidden bg-bg-overlay">
                {it.uri ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={it.thumb_uri || it.uri}
                    alt={it.photo_id}
                    loading="lazy"
                    className="h-full w-full object-cover"
                  />
                ) : null}
              </div>
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="truncate text-xs text-fg-primary">{it.photo_id.slice(0, 8)}</span>
                <span className="mono">
                  {it.verdict ? verdictIcon[it.verdict] : "·"}
                  <span className="ml-1">{it.overall?.toFixed(1) ?? "—"}</span>
                </span>
              </div>
            </button>
            {onDelete && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(it.photo_id);
                }}
                className="opacity-0 group-hover:opacity-100 text-fg-tertiary hover:text-accent-danger transition-opacity"
                title="删除这张照片"
              >
                <Trash2 size={12} />
              </button>
            )}
          </div>
        );
      })}
    </aside>
  );
}
