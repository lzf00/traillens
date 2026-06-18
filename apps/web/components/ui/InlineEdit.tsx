"use client";

import { useEffect, useRef, useState } from "react";
import { Pencil } from "lucide-react";

/**
 * 点击文字 → 变 input → 回车/失焦保存,Esc 取消。
 * 空值仍允许保存(由父组件 onSave 决定是否拦截)。
 */
export function InlineEdit({
  value,
  onSave,
  className = "",
  placeholder = "未填",
}: {
  value: string;
  onSave: (v: string) => void;
  className?: string;
  placeholder?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!editing) setDraft(value);
  }, [value, editing]);

  useEffect(() => {
    if (editing) ref.current?.focus();
  }, [editing]);

  function commit() {
    setEditing(false);
    if (draft !== value) onSave(draft);
  }
  function cancel() {
    setEditing(false);
    setDraft(value);
  }

  if (!editing) {
    return (
      <button
        onClick={() => setEditing(true)}
        className={`group inline-flex items-center gap-1 cursor-text hover:text-fg-primary transition-colors ${className}`}
      >
        <span className={value ? "" : "italic text-fg-tertiary"}>
          {value || placeholder}
        </span>
        <Pencil
          size={11}
          className="opacity-0 group-hover:opacity-60 text-fg-tertiary transition-opacity"
        />
      </button>
    );
  }

  return (
    <input
      ref={ref}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          commit();
        } else if (e.key === "Escape") {
          e.preventDefault();
          cancel();
        }
      }}
      className={`bg-bg-raised border border-accent-aurora rounded px-2 py-0.5 outline-none ${className}`}
    />
  );
}
