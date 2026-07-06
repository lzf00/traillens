"use client";

/**
 * 主题切换:三态循环 system → light → dark → system
 * - localStorage 持久化 traillens_theme(值:auto/light/dark)
 * - 渲染前由 RootLayout 的 inline script 同步设 html.theme-light,防 FOUC
 * - system 模式:监听 prefers-color-scheme media query
 */

import { useEffect, useState } from "react";
import { Moon, Sun, MonitorSmartphone } from "lucide-react";

type Theme = "auto" | "light" | "dark";

function applyTheme(t: Theme) {
  const light =
    t === "light" ||
    (t === "auto" && typeof window !== "undefined" &&
      window.matchMedia("(prefers-color-scheme: light)").matches);
  document.documentElement.classList.toggle("theme-light", light);
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("auto");

  useEffect(() => {
    let cur: Theme = "auto";
    try {
      const v = localStorage.getItem("traillens_theme");
      if (v === "light" || v === "dark" || v === "auto") cur = v;
    } catch {}
    setTheme(cur);

    // auto 模式监听系统主题变化
    if (cur === "auto") {
      const mq = window.matchMedia("(prefers-color-scheme: light)");
      const handler = () => applyTheme("auto");
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
  }, []);

  function cycle() {
    // 用 localStorage 作 source of truth,防 React state 异步 / stale closure
    let cur: Theme = theme;
    try {
      const v = localStorage.getItem("traillens_theme");
      if (v === "light" || v === "dark" || v === "auto") cur = v;
    } catch {}
    const next: Theme = cur === "auto" ? "light" : cur === "light" ? "dark" : "auto";
    setTheme(next);
    applyTheme(next);
    try { localStorage.setItem("traillens_theme", next); } catch {}
  }

  const meta = {
    auto: { Icon: MonitorSmartphone, label: "自动(跟系统)", next: "切到亮色" },
    light: { Icon: Sun, label: "亮色", next: "切到暗色" },
    dark: { Icon: Moon, label: "暗色", next: "跟随系统" },
  }[theme];
  const Icon = meta.Icon;

  return (
    <button
      onClick={cycle}
      aria-label="切换主题"
      title={`当前:${meta.label} · 点击${meta.next}`}
      className="rounded-md p-1.5 text-fg-secondary hover:text-fg-primary hover:bg-bg-raised transition-colors"
    >
      <Icon size={14} />
    </button>
  );
}
