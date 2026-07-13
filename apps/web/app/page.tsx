import Link from "next/link";
import Image from "next/image";
import { cookies } from "next/headers";
import { ArrowRight, Github, Cpu, Sparkles, Plug } from "lucide-react";
import { apiFetch } from "@/lib/api";

export const dynamic = "force-dynamic";

type Photo = {
  photo_id: string;
  uri: string;
  thumb_uri?: string | null;
  verdict?: string | null;
  aesthetic?: { overall?: number } | null;
};

type DemoData = {
  hero_uri: string | null;
  gallery: Photo[];
  demo_trail_id: string | null;
};

async function fetchDemo(): Promise<DemoData> {
  // 优先 env(LANDING_TRAIL_ID 手动 pin 一个真风光 trail),否则走后端 _demo/public
  // 后端 pick_demo_trail 目前按 travelogue+photos+recency 排,会选到"名字风光其实
  // 宝可梦"的 trail;env 是最可靠的兜底
  const pinned = process.env.LANDING_TRAIL_ID;
  try {
    const trailUrl = pinned
      ? `/v1/trails/${pinned}/public`
      : `/v1/trails/_demo/public`;
    const r = await apiFetch(trailUrl, { cache: "no-store" });
    if (!r.ok) return { hero_uri: null, gallery: [], demo_trail_id: null };
    const trail = await r.json();
    const p = await apiFetch(`/v1/trails/${trail.id}/photos/public`, { cache: "no-store" });
    const arr: Photo[] = p.ok ? await p.json() : [];
    const keeps = arr.filter((x) => x.verdict === "keep");
    const pool = keeps.length ? keeps : arr;
    pool.sort((a, b) => (b.aesthetic?.overall ?? 0) - (a.aesthetic?.overall ?? 0));
    // 作品网格门槛:>= 7.5 分才配当"精选"露出;不足 3 张就 gallery=[]
    // 首图门槛更宽 >= 6.5,反正会被压暗
    const HERO_MIN = 6.5;
    const GRID_MIN = 7.5;
    const heroPhoto = pool.find((x) => (x.aesthetic?.overall ?? 0) >= HERO_MIN);
    const gridPhotos = pool.filter((x) => (x.aesthetic?.overall ?? 0) >= GRID_MIN);
    return {
      hero_uri: heroPhoto?.uri ?? pool[0]?.uri ?? null,
      gallery: gridPhotos.length >= 3 ? gridPhotos.slice(0, 6) : [],
      demo_trail_id: trail.id,
    };
  } catch {
    return { hero_uri: null, gallery: [], demo_trail_id: null };
  }
}

export default async function HomePage() {
  const c = await cookies();
  const loggedIn = Boolean(
    c.get("traillens_session")?.value || c.get("traillens_user_id")?.value
  );
  const demo = await fetchDemo();

  return (
    <main>
      {/* ═════════════ HERO · 全屏照片 + 蒙层 + 中央文字 ═════════════ */}
      <section className="relative isolate flex min-h-[calc(100dvh-56px)] items-center px-6 md:px-12">
        {/* 背景照片 */}
        {demo.hero_uri && (
          <Image
            src={demo.hero_uri}
            alt="风光摄影示例"
            fill
            priority
            sizes="100vw"
            className="object-cover -z-20"
          />
        )}
        {/* 蒙层:整体压暗 + 顶部到底渐变提高文字对比 */}
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-bg-base/70 via-bg-base/50 to-bg-base pointer-events-none" />
        {/* 兜底(照片没拉到时的深色背景) */}
        {!demo.hero_uri && <div className="absolute inset-0 -z-20 bg-bg-base" />}

        <div className="mx-auto w-full max-w-5xl">
          <p className="mono mb-6 text-fg-secondary">v0.0.1 · build in public</p>

          <h1 className="font-display text-5xl leading-[1.05] text-fg-primary md:text-7xl drop-shadow-[0_2px_20px_rgba(0,0,0,0.6)]">
            给徒步的
            <br />
            <span className="text-accent-aurora">风光摄影师</span>
            <br />
            造一间 AI 暗房。
          </h1>

          <p className="mt-8 max-w-xl text-lg text-fg-primary/90 md:text-xl leading-relaxed drop-shadow-[0_1px_8px_rgba(0,0,0,0.6)]">
            一整次徒步的素材丢进去,AI 自动选片、点评、写游记,
            规划下次拍摄计划。
          </p>

          {/* CTA */}
          <div className="mt-10 flex flex-wrap items-center gap-3">
            {loggedIn ? (
              <>
                <CTAPrimary href="/trails">继续到我的 Trails</CTAPrimary>
                <CTAGhost href="/trails/new">新建 Trail</CTAGhost>
              </>
            ) : (
              <>
                <CTAPrimary href="/login">登录开始使用</CTAPrimary>
                <CTAGhost href="/trails/demo">看示例作品集</CTAGhost>
                <Link
                  href="https://github.com/lzf00/traillens"
                  target="_blank"
                  className="inline-flex items-center gap-1.5 text-xs text-fg-secondary hover:text-fg-primary px-2 py-3"
                >
                  <Github size={12} /> GitHub
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* ═════════════ 作品网格 · 让人看见效果 ═════════════ */}
      {demo.gallery.length > 0 && (
        <section className="px-6 md:px-12 py-24">
          <div className="mx-auto max-w-6xl">
            <div className="mb-8 flex items-baseline justify-between gap-4 flex-wrap">
              <div>
                <p className="mono mb-2 text-fg-tertiary">看看它出什么样</p>
                <h2 className="font-display text-3xl md:text-4xl text-fg-primary">
                  AI 从这一组照片里挑出的精选。
                </h2>
              </div>
              {demo.demo_trail_id && (
                <Link
                  href={`/trails/${demo.demo_trail_id}/share`}
                  className="group inline-flex items-center gap-1.5 text-sm text-accent-aurora hover:underline"
                >
                  看完整分享页
                  <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
                </Link>
              )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {demo.gallery.map((p) => (
                <a
                  key={p.photo_id}
                  href={
                    demo.demo_trail_id
                      ? `/trails/${demo.demo_trail_id}/share#p-${p.photo_id}`
                      : "#"
                  }
                  className="group photo-frame relative aspect-[3/2] bg-bg-overlay overflow-hidden"
                >
                  <Image
                    src={p.uri}
                    alt=""
                    fill
                    sizes="(max-width: 768px) 50vw, 33vw"
                    className="object-cover transition-transform duration-DEFAULT ease-trail group-hover:scale-[1.03]"
                  />
                  {p.aesthetic?.overall != null && (
                    <span className="absolute bottom-2 right-2 status-pill backdrop-blur text-xs text-accent-aurora">
                      {p.aesthetic.overall.toFixed(1)}
                    </span>
                  )}
                </a>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ═════════════ 三大能力 · 卡片 ═════════════ */}
      <section className="px-6 md:px-12 py-24 border-t border-divider">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-2xl">
            <p className="mono mb-2 text-fg-tertiary">TrailLens 是什么</p>
            <h2 className="font-display text-3xl md:text-4xl text-fg-primary">
              一个专为风光摄影师做的
              <br />
              自动化后期助手。
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <Card
              icon={<Cpu size={20} />}
              title="四个 AI 智能体协作"
              body="选片、点评、写游记、规划下一次 —— 每步都留决策痕迹。想手动接管随时打断,继续跑不丢进度。"
            />
            <Card
              icon={<Sparkles size={20} />}
              title="专为风光调过的美学模型"
              body="用 5000+ 张风光原片微调,评构图、光线、氛围、情绪比通用模型更懂你。开源权重可自托管。"
            />
            <Card
              icon={<Plug size={20} />}
              title="打通 Claude / Cursor"
              body="EXIF、天气、日月轨迹三个 MCP server 开源,直接挂到 Claude Desktop 或 Cursor,不用再自己造工具。"
            />
          </div>
        </div>
      </section>

      {/* ═════════════ 3 步流程 ═════════════ */}
      <section className="px-6 md:px-12 py-24 border-t border-divider">
        <div className="mx-auto max-w-6xl">
          <p className="mono mb-2 text-fg-tertiary">怎么用</p>
          <h2 className="font-display text-3xl md:text-4xl text-fg-primary mb-12">
            三步走。
          </h2>
          <div className="grid gap-8 md:grid-cols-3">
            <Step
              n="01"
              title="上传一次徒步的所有照片"
              body="拖入 RAW / JPG,后台并行处理,自动解析 EXIF、生成缩略图。"
            />
            <Step
              n="02"
              title="按 Run,让 AI 干活"
              body="美学模型逐张打分,critic 写点评,story 生成游记,planner 建议下次拍摄光线与机位。"
            />
            <Step
              n="03"
              title="导出、分享、找回"
              body="下载精选 zip,一键出小红书文,或用中文语义搜索翻整个照片库。"
            />
          </div>
        </div>
      </section>

      {/* ═════════════ Footer ═════════════ */}
      <footer className="px-6 md:px-12 py-8 border-t border-divider">
        <div className="mx-auto max-w-6xl flex flex-wrap items-center justify-between gap-4 text-xs text-fg-tertiary">
          <p className="mono">© 2026 TrailLens · MIT 开源</p>
          <div className="flex gap-4">
            <Link href="/trails/demo" className="hover:text-fg-primary">示例</Link>
            <Link href="/library" className="hover:text-fg-primary">语义搜索</Link>
            <a
              href="https://github.com/lzf00/traillens"
              target="_blank"
              rel="noreferrer"
              className="hover:text-fg-primary"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}

/* ───── UI 原子 ───── */
function CTAPrimary({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="group inline-flex items-center gap-2 rounded-md bg-accent-aurora px-5 py-3 text-sm font-medium text-bg-base transition-all hover:bg-accent-aurora/90 shadow-lg shadow-accent-aurora/20"
    >
      {children}
      <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}

function CTAGhost({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="rounded-md border border-fg-primary/30 backdrop-blur px-5 py-3 text-sm text-fg-primary transition-all hover:border-accent-glacier hover:text-accent-glacier"
    >
      {children}
    </Link>
  );
}

function Card({
  icon, title, body,
}: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="group rounded-lg border border-divider bg-bg-raised/40 p-6 transition-all hover:border-accent-aurora/60 hover:bg-bg-raised hover:-translate-y-0.5">
      <div className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-md bg-accent-aurora/10 text-accent-aurora">
        {icon}
      </div>
      <h3 className="font-display text-xl text-fg-primary mb-2">{title}</h3>
      <p className="text-sm text-fg-secondary leading-relaxed">{body}</p>
    </div>
  );
}

function Step({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div>
      <div className="mono text-3xl text-accent-glacier mb-3">{n}</div>
      <h4 className="font-display text-xl text-fg-primary mb-2">{title}</h4>
      <p className="text-sm text-fg-secondary leading-relaxed">{body}</p>
    </div>
  );
}
