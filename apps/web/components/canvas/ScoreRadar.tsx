/**
 * 8 维美学评分雷达图,纯 SVG,无依赖。
 * Generative UI(§3.1 M2)的样板:agent 把 8 维分作为工具调用结果传回,前端渲染此组件。
 */

const DIMS = [
  { key: "composition", label: "构图" },
  { key: "visual_elements", label: "视觉" },
  { key: "technical", label: "技术" },
  { key: "originality", label: "原创" },
  { key: "theme", label: "主题" },
  { key: "emotion", label: "情感" },
  { key: "gestalt", label: "格式塔" },
  { key: "overall", label: "综合" },
] as const;

type Scores = Partial<Record<(typeof DIMS)[number]["key"], number>>;

export function ScoreRadar({ scores, size = 220 }: { scores: Scores; size?: number }) {
  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 24;
  const n = DIMS.length;

  const points = DIMS.map((d, i) => {
    const v = (scores[d.key] ?? 0) / 10;
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
    return [cx + Math.cos(angle) * radius * v, cy + Math.sin(angle) * radius * v];
  });

  const path =
    points.map((p, i) => `${i === 0 ? "M" : "L"} ${p[0]} ${p[1]}`).join(" ") + " Z";

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      aria-label="美学评分雷达图"
      style={{ flexShrink: 0, overflow: "visible" }}
    >
      {/* 网格 */}
      {[0.25, 0.5, 0.75, 1].map((r) => (
        <polygon
          key={r}
          points={DIMS.map((_, i) => {
            const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
            return `${cx + Math.cos(angle) * radius * r},${cy + Math.sin(angle) * radius * r}`;
          }).join(" ")}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
        />
      ))}
      {/* 数据多边形 */}
      <path d={path} fill="rgba(111,191,139,0.18)" stroke="#6FBF8B" strokeWidth={1.5} />
      {/* 标签 */}
      {DIMS.map((d, i) => {
        const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
        const lx = cx + Math.cos(angle) * (radius + 14);
        const ly = cy + Math.sin(angle) * (radius + 14);
        return (
          <text
            key={d.key}
            x={lx}
            y={ly}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={10}
            fill="#9AA4B2"
          >
            {d.label}
          </text>
        );
      })}
    </svg>
  );
}
