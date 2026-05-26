import type { Config } from "tailwindcss";

/**
 * 设计 tokens 严格映射自 docs/PRODUCT_PLAN.md §2.2。
 * 任何颜色/字体/间距改动:先改 PRODUCT_PLAN,再同步这里。
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          base: "#0F1115",       // deep slate, 户外夜空感
          raised: "#1A1E25",
          overlay: "#232932",
        },
        fg: {
          primary: "#E8ECF1",
          secondary: "#9AA4B2",
          tertiary: "#5B6573",
        },
        accent: {
          aurora: "#6FBF8B",     // 极光绿,主 CTA / keep
          glacier: "#8FB8D1",    // 冰川蓝,链接 / 选中
          golden: "#E8B96A",     // 金时刻
          danger: "#D97757",     // 落日橙,reject
        },
        divider: "rgba(255,255,255,0.06)",
      },
      fontFamily: {
        display: ["Fraunces", "Songti SC", "serif"],
        sans: ["Inter", "PingFang SC", "HarmonyOS Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
        xl: "24px",
      },
      transitionTimingFunction: {
        trail: "cubic-bezier(0.2, 0.8, 0.2, 1)",
      },
      transitionDuration: {
        DEFAULT: "180ms",
        slow: "240ms",
      },
    },
  },
  plugins: [],
};

export default config;
