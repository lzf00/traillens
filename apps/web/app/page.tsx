import Link from "next/link";

/**
 * Landing page。一屏内说清:是什么 / 怎么用 / 凭什么相信。
 * 参考 PRODUCT_PLAN.md §2.2 视觉系统。
 */
export default function HomePage() {
  return (
    <main className="min-h-dvh px-6 py-24 md:px-12">
      <div className="mx-auto max-w-3xl">
        <p className="mono mb-8">v0.0.1 · build in public</p>

        <h1 className="font-display text-5xl leading-tight text-fg-primary md:text-7xl">
          The AI darkroom for
          <br />
          <span className="text-accent-aurora">landscape photographers</span>
          <br />
          who hike.
        </h1>

        <p className="mt-8 text-lg text-fg-secondary md:text-xl">
          把一整次徒步的素材丢进去 — AI 自动选片、点评、生成游记,并规划你下次的拍摄计划。
        </p>

        <div className="mt-12 flex flex-wrap items-center gap-3">
          <Link
            href="/trails/demo"
            className="rounded-md bg-accent-aurora px-5 py-3 text-sm font-medium text-bg-base
                       transition-all duration-DEFAULT ease-trail hover:bg-accent-aurora/90"
          >
            打开示例 Trail
          </Link>
          <Link
            href="https://github.com/lzf00/traillens"
            target="_blank"
            className="rounded-md border border-divider px-5 py-3 text-sm text-fg-primary
                       transition-all hover:border-accent-glacier hover:text-accent-glacier"
          >
            GitHub →
          </Link>
        </div>

        <div className="mt-24 grid gap-8 text-sm text-fg-secondary md:grid-cols-3">
          <Feature
            title="多智能体"
            body="Culling / Critic / Story / Planner — LangGraph supervisor 编排,HITL 中断可恢复。"
          />
          <Feature
            title="自研美学模型"
            body="Q-Align + landscape LoRA。开源权重,可自托管,PLCC 目标 > 0.78。"
          />
          <Feature
            title="MCP 一等公民"
            body="EXIF / Weather / Sun-Moon 都是独立 MCP server,可被任何 LLM 客户端直接装。"
          />
        </div>
      </div>
    </main>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div className="border-l border-divider pl-4">
      <h3 className="font-display text-lg text-fg-primary">{title}</h3>
      <p className="mt-2 text-fg-secondary">{body}</p>
    </div>
  );
}
