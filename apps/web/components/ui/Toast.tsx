"use client";

/**
 * Toast — 替 window.alert/confirm/prompt 的非阻塞提示。
 *
 * 用法:
 *   const { toast, setToast } = useTrailApi(...);
 *   <Toast toast={toast} onClose={() => setToast(null)} />
 */

import { useEffect } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

export type ToastMsg = {
  level: "info" | "error" | "success";
  text: string;
};

const STYLE: Record<ToastMsg["level"], { bg: string; icon: any; border: string }> = {
  info:    { bg: "bg-blue-500/10  text-blue-300",  border: "border-blue-500/30",  icon: Info },
  error:   { bg: "bg-red-500/10   text-red-300",   border: "border-red-500/30",   icon: AlertCircle },
  success: { bg: "bg-green-500/10 text-green-300", border: "border-green-500/30", icon: CheckCircle2 },
};

export function Toast({
  toast, onClose, autoHideMs = 4000,
}: {
  toast: ToastMsg | null;
  onClose: () => void;
  autoHideMs?: number;
}) {
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(onClose, autoHideMs);
    return () => clearTimeout(t);
  }, [toast, onClose, autoHideMs]);

  if (!toast) return null;
  const s = STYLE[toast.level];
  const Icon = s.icon;
  return (
    <div className="fixed bottom-6 right-6 z-50 max-w-md">
      <div
        role="status"
        aria-live="polite"
        className={`flex items-start gap-3 rounded-md border ${s.border} ${s.bg} px-4 py-3 shadow-lg backdrop-blur`}
      >
        <Icon size={16} className="mt-0.5 shrink-0" />
        <p className="flex-1 text-sm">{toast.text}</p>
        <button onClick={onClose} className="text-fg-tertiary hover:text-fg-primary">
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
