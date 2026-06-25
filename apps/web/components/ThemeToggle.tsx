"use client";

/**
 * 主题切换:dark(默认) <-> light
 * - localStorage 持久化 traillens_theme
 * - 渲染前由 RootLayout 的 inline script 同步设 html.theme-light,防 FOUC
 */

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export function ThemeToggle() {
  const [light, setLight] = useState(false);

  useEffect(() => {
    setLight(document.documentElement.classList.contains("theme-light"));
  }, []);

  function toggle() {
    const next = !light;
    setLight(next);
    document.documentElement.classList.toggle("theme-light", next);
    try { localStorage.setItem("traillens_theme", next ? "light" : "dark"); } catch {}
  }

  return (
    <button
      onClick={toggle}
      aria-label="切换主题"
      title={light ? "切到暗色" : "切到亮色"}
      className="rounded-md p-1.5 text-fg-secondary hover:text-fg-primary hover:bg-bg-raised transition-colors"
    >
      {light ? <Moon size={14} /> : <Sun size={14} />}
    </button>
  );
}
