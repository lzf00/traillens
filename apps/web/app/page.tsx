import Link from "next/link";
import { cookies } from "next/headers";
import { Network, Sparkles, Plug, ArrowRight, Github } from "lucide-react";

// 强制每请求 SSR — cookies() 应自动让页面变 dynamic,但 Next 15
// build 时 cookie store 空 → 把空态版本 prerender 出来 + 1 年缓存
// 显式 force-dynamic 才能在每请求读 cookie
export const dynamic = "force-dynamic";

/**
 * Landing page。一屏内说清:是什么 / 怎么用 / 凭什么相信。
 * 已登录用户:CTA 换成"继续到我的 Trails",突出主流程入口
 */
export default async function HomePage() {
  const c = await cookies();
  const loggedIn = Boolean(c.get("traillens_session")?.value || c.get("traillens_user_id")?.value);
  return (
    <main className="min-h-dvh px-6 py-24 md:px-12">
      <div className="mx-auto max-w-5xl">
        {/* ─────────── Hero ─────────── */}
        <div className="max-w-3xl">
          <p className="mono mb-8">v0.0.1 · build in public</p>

          <h1 className="font-display text-5xl leading-[1.05] text-fg-primary md:text-7xl">
            给徒步的
            <br />
            <span className="text-accent-aurora">风光摄影师</span>
            <br />
            造一间 AI 暗房。
          </h1>

          <p className="mt-8 text-lg text-fg-secondary md:text-xl leading-relaxed">
            把一整次徒步的素材丢进去 — AI 自动选片、点评、生成游记,
            并规划你下次的拍摄计划。
          </p>

          {/* CTA */}
          <div className="mt-12 flex flex-wrap items-center gap-3">
            {loggedIn ? (
              <>
                <Link
                  href="/trails"
                  className="group inline-flex items-center gap-2 rounded-md bg-accent-aurora px-5 py-3 text-sm font-medium text-bg-base transition-all hover:bg-accent-aurora/90"
                >
                  继续到我的 Trails
                  <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
                </Link>
                <Link
                  href="/trails/new"
                  className="rounded-md border border-divider px-5 py-3 text-sm text-fg-primary transition-all hover:border-accent-glacier hover:text-accent-glacier"
                >
                  新建 Trail
                </Link>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="rounded-md bg-accent-aurora px-5 py-3 text-sm font-medium text-bg-base transition-all hover:bg-accent-aurora/90"
                >
                  登录开始使用
                </Link>
                <Link
                  href="/trails/demo"
                  className="group inline-flex items-center gap-2 rounded-md border border-divider px-5 py-3 text-sm text-fg-primary transition-all hover:border-accent-glacier hover:text-accent-glacier"
                >
                  看示例作品集
                  <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
                </Link>
                <Link
                  href="https://github.com/lzf00/traillens"
                  target="_blank"
                  className="inline-flex items-center gap-1.5 text-xs text-fg-tertiary hover:text-fg-secondary px-2 py-3"
                >
                  <Github size={12} /> GitHub
                </Link>
              </>
            )}
          </div>
        </div>

        {/* ─────────── 三个卡片 · 卡片风(hover 提亮+微浮) ─────────── */}
        <section className="mt-24 md:mt-32">
          <p className="mono mb-6 text-fg-tertiary">技术亮点</p>
          <div className="grid gap-4 md:grid-cols-3">
            <FeatureCard
              icon={<Network size={20} />}
              title="多智能体协作"
              body="Culling · Critic · Story · Planner 四个 agent 由 LangGraph 编排,人机中断可恢复,每步决策留痕。"
              tag="LangGraph"
            />
            <FeatureCard
              icon={<Sparkles size={20} />}
              title="自研美学模型"
              body="Q-Align + landscape LoRA,专为风光摄影微调。开源权重,可自托管,PLCC 目标 > 0.78。"
              tag="Q-Align · LoRA"
            />
            <FeatureCard
              icon={<Plug size={20} />}
              title="MCP 工具链开源"
              body="EXIF / 天气 / 日月轨迹 三个独立 MCP server,可直接挂到 Claude Desktop、Cursor 等 LLM 客户端。"
              tag="MCP"
            />
          </div>
        </section>

        {/* ─────────── 流程解说(3 步走) ─────────── */}
        <section className="mt-24">
          <p className="mono mb-6 text-fg-tertiary">怎么用</p>
          <div className="grid gap-6 md:grid-cols-3">
            <StepCard
              n="01"
              title="上传一次徒步的素材"
              body="拖入 RAW / JPG,后台自动解析 EXIF + 生成缩略图。支持批量。"
            />
            <StepCard
              n="02"
              title="AI 选片 · 点评 · 写游记"
              body="豆包 Vision + 自研美学模型给每张打分;critic 生成 80 字点评;planner 规划下次拍摄。"
            />
            <StepCard
              n="03"
              title="导出 · 分享 · 索引"
              body="下载精选 zip、导出小红书图文、生成 SEO 分享页;整库支持中文语义搜索。"
            />
          </div>
        </section>

        {/* Footer */}
        <footer className="mt-32 border-t border-divider pt-8 text-xs text-fg-tertiary flex flex-wrap gap-4 items-center justify-between">
          <p className="mono">© 2026 TrailLens · MIT 开源</p>
          <div className="flex gap-4">
            <Link href="/trails/demo" className="hover:text-fg-secondary">示例</Link>
            <Link href="/library" className="hover:text-fg-secondary">语义搜索</Link>
            <a href="https://github.com/lzf00/traillens" target="_blank" rel="noreferrer" className="hover:text-fg-secondary">
              GitHub
            </a>
          </div>
        </footer>
      </div>
    </main>
  );
}

/* ─────────── 组件 ─────────── */
function FeatureCard({
  icon, title, body, tag,
}: { icon: React.ReactNode; title: string; body: string; tag?: string }) {
  return (
    <div
      className="group relative rounded-lg border border-divider bg-bg-raised/40 p-5
                 transition-all duration-DEFAULT ease-trail
                 hover:border-accent-aurora/60 hover:bg-bg-raised
                 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-accent-aurora/5"
    >
      <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-md
                      bg-accent-aurora/10 text-accent-aurora
                      transition-colors group-hover:bg-accent-aurora/20">
        {icon}
      </div>
      <div className="flex items-baseline justify-between gap-2 mb-2">
        <h3 className="font-display text-lg text-fg-primary">{title}</h3>
        {tag && <span className="mono text-fg-tertiary shrink-0">{tag}</span>}
      </div>
      <p className="text-sm text-fg-secondary leading-relaxed">{body}</p>
    </div>
  );
}

function StepCard({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div className="relative rounded-lg border border-divider p-5 bg-bg-raised/20">
      <div className="mono text-2xl text-accent-glacier mb-3">{n}</div>
      <h4 className="font-display text-base text-fg-primary mb-2">{title}</h4>
      <p className="text-sm text-fg-secondary leading-relaxed">{body}</p>
    </div>
  );
}
