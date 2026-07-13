"use client";

/**
 * ConfirmDialog / RenameDialog — 替 window.confirm / window.prompt。
 *
 * 用法(async pattern):
 *   const [confirmState, ask] = useConfirm();
 *   if (await ask({ title: "删?", body: "..." })) { ... }
 *   <ConfirmDialog {...confirmState} />
 */

import { useCallback, useState } from "react";
import { AlertTriangle } from "lucide-react";

type Resolver = (v: boolean | string | null) => void;

export type ConfirmState = {
  open: boolean;
  title: string;
  body?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  inputPlaceholder?: string;
  inputDefault?: string;
  resolver: Resolver | null;
};

const INITIAL: ConfirmState = {
  open: false, title: "",
  resolver: null,
};

export function useConfirm() {
  const [state, setState] = useState<ConfirmState>(INITIAL);

  const ask = useCallback((opts: Omit<ConfirmState, "open" | "resolver">): Promise<boolean> => {
    return new Promise((resolve) => {
      setState({ ...opts, open: true, resolver: (v) => resolve(Boolean(v)) });
    });
  }, []);

  const askText = useCallback((opts: Omit<ConfirmState, "open" | "resolver">): Promise<string | null> => {
    return new Promise((resolve) => {
      setState({ ...opts, open: true, resolver: (v) => resolve(typeof v === "string" ? v : null) });
    });
  }, []);

  const close = useCallback((value: boolean | string | null) => {
    if (state.resolver) state.resolver(value);
    setState(INITIAL);
  }, [state]);

  return { state, ask, askText, close };
}

export function ConfirmDialog({
  state, close,
}: {
  state: ConfirmState;
  close: (v: boolean | string | null) => void;
}) {
  const [text, setText] = useState(state.inputDefault ?? "");
  const isPrompt = state.inputPlaceholder !== undefined;

  if (!state.open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={() => close(null)}
    >
      <div
        className="bg-bg-raised border border-divider rounded-lg p-6 max-w-md w-full mx-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-3 mb-4">
          {state.danger && <AlertTriangle size={20} className="text-red-400 mt-0.5 shrink-0" />}
          <div>
            <h3 className="font-display text-lg text-fg-primary">{state.title}</h3>
            {state.body && <p className="mt-1 text-sm text-fg-secondary">{state.body}</p>}
          </div>
        </div>

        {isPrompt && (
          <input
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={state.inputPlaceholder}
            className="w-full rounded-md bg-bg-base border border-divider px-3 py-2 text-fg-primary mb-4"
            onKeyDown={(e) => {
              if (e.key === "Enter") close(text);
              if (e.key === "Escape") close(null);
            }}
          />
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={() => close(null)}
            className="rounded-md border border-divider px-4 py-2 text-sm text-fg-secondary hover:text-fg-primary transition-colors"
          >
            {state.cancelLabel ?? "取消"}
          </button>
          <button
            onClick={() => close(isPrompt ? text : true)}
            className={
              "rounded-md px-4 py-2 text-sm font-medium transition-colors " +
              (state.danger
                ? "bg-red-500 text-white hover:bg-red-600"
                : "bg-accent-aurora text-bg-base hover:bg-accent-aurora/90")
            }
          >
            {state.confirmLabel ?? "确定"}
          </button>
        </div>
      </div>
    </div>
  );
}
