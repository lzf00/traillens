"use client";

import { usePathname, useRouter } from "next/navigation";
import { Languages } from "lucide-react";

const LOCALES = [
  { code: "zh", label: "中文" },
  { code: "en", label: "English" },
];

export function LocaleSwitcher({ current }: { current: string }) {
  const router = useRouter();
  const pathname = usePathname();

  function switchTo(locale: string) {
    // 去掉旧 locale 前缀,加新前缀(默认 locale 不加)
    const segments = pathname.split("/").filter(Boolean);
    if (segments[0] === "zh" || segments[0] === "en") segments.shift();
    const next = locale === "zh" ? "/" + segments.join("/") : `/${locale}/${segments.join("/")}`;
    router.push(next || "/");
  }

  return (
    <div className="inline-flex items-center gap-1 text-xs text-fg-secondary">
      <Languages size={14} />
      {LOCALES.map((l, i) => (
        <span key={l.code}>
          {i > 0 && <span className="mx-1 text-fg-tertiary">·</span>}
          <button
            onClick={() => switchTo(l.code)}
            className={
              current === l.code
                ? "text-fg-primary"
                : "hover:text-fg-primary transition-colors"
            }
          >
            {l.label}
          </button>
        </span>
      ))}
    </div>
  );
}
