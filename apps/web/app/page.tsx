import Link from "next/link";
import Image from "next/image";
import { cookies } from "next/headers";
import { ArrowRight, Github, ChevronDown, Check } from "lucide-react";
import { apiFetch } from "@/lib/api";

export const dynamic = "force-dynamic";

type Aesthetic = {
  overall?: number;
  composition?: number;
  visual_elements?: number;
  technical?: number;
  originality?: number;
  theme?: number;
  emotion?: number;
  gestalt?: number;
};

type Photo = {
  photo_id: string;
  uri: string;
  thumb_uri?: string | null;
  verdict?: string | null;
  aesthetic?: Aesthetic | null;
  critique?: string | null;
};

type DemoData = {
  hero_photo: Photo | null;
  gallery: Photo[];
  demo_trail_id: string | null;
};

async function fetchDemo(): Promise<DemoData> {
  const pinned = process.env.LANDING_TRAIL_ID;
  try {
    const trailUrl = pinned
      ? `/v1/trails/${pinned}/public`
      : `/v1/trails/_demo/public`;
    const r = await apiFetch(trailUrl, { cache: "no-store" });
    if (!r.ok) return { hero_photo: null, gallery: [], demo_trail_id: null };
    const trail = await r.json();
    const p = await apiFetch(`/v1/trails/${trail.id}/photos/public`, { cache: "no-store" });
    const arr: Photo[] = p.ok ? await p.json() : [];
    const keeps = arr.filter((x) => x.verdict === "keep");
    const pool = keeps.length ? keeps : arr;
    pool.sort((a, b) => (b.aesthetic?.overall ?? 0) - (a.aesthetic?.overall ?? 0));
    const heroPhoto = pool.find((x) => (x.aesthetic?.overall ?? 0) >= 6.5);
    const gridPhotos = pool.filter((x) => (x.aesthetic?.overall ?? 0) >= 7.5);
    return {
      hero_photo: heroPhoto ?? pool[0] ?? null,
      gallery: gridPhotos.length >= 3 ? gridPhotos.slice(0, 6) : [],
      demo_trail_id: trail.id,
    };
  } catch {
    return { hero_photo: null, gallery: [], demo_trail_id: null };
  }
}

export default async function HomePage() {
  const c = await cookies();
  const loggedIn = Boolean(
    c.get("traillens_session")?.value || c.get("traillens_user_id")?.value
  );
  const demo = await fetchDemo();

  return (
    <main id="top">
      {/* ═════════════ 1. HERO · full-bleed 大照片 + 极简大字 ═════════════ */}
      <section className="relative isolate flex min-h-[calc(100dvh-56px)] items-end px-6 md:px-16 pb-32 md:pb-40">
        {demo.hero_photo?.uri && (
          <Image
            src={demo.hero_photo.uri}
            alt=""
            fill
            priority
            sizes="100vw"
            className="object-cover -z-20"
          />
        )}
        {/* 底部收边过渡到下一屏 */}
        <div className="absolute inset-x-0 bottom-0 h-40 -z-10 bg-gradient-to-b from-transparent to-bg-base pointer-events-none" />
        {!demo.hero_photo?.uri && <div className="absolute inset-0 -z-20 bg-bg-base" />}

        <div className="mx-auto w-full max-w-6xl">
          <p className="mono mb-6 text-white/60" style={{ textShadow: "0 1px 2px rgba(0,0,0,0.5)" }}>
            v0.0.1 · build in public
          </p>

          {/* Apple/xAI 式:克制字号(md:text-6xl = 60px),tracking-tighter 更紧凑 */}
          <h1
            className="font-display text-4xl leading-[1.1] text-white/85 md:text-6xl md:leading-[1.05] tracking-tight max-w-3xl"
            style={{ textShadow: "0 1px 4px rgba(0,0,0,0.55)" }}
          >
            给徒步的<br />
            <span className="text-accent-aurora">风光摄影师</span>,<br />
            造一间 AI 暗房。
          </h1>

          <p
            className="mt-8 max-w-2xl text-sm md:text-base text-white/65 leading-relaxed"
            style={{ textShadow: "0 1px 3px rgba(0,0,0,0.6)" }}
          >
            一整次徒步的素材丢进去,AI 自动选片、点评、写游记、规划下次拍摄。
          </p>

          <div className="mt-12 flex flex-wrap items-center gap-x-8 gap-y-4">
            {loggedIn ? (
              <>
                <CTAPrimary href="/trails">继续到我的 Trails</CTAPrimary>
                <LinkPlain href="/trails/new">新建 Trail →</LinkPlain>
              </>
            ) : (
              <>
                <CTAPrimary href="/login">登录开始使用</CTAPrimary>
                <LinkPlain href="/trails/demo">看示例作品集 →</LinkPlain>
              </>
            )}
          </div>
        </div>

        {/* 底部滚动引导 */}
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 text-white/40 animate-bounce">
          <ChevronDown size={24} />
        </div>
      </section>

      {/* ═════════════ 2. AI 输出示例 · 大照片 + 卡片(Apple 产品照风) ═════════════ */}
      {demo.hero_photo?.aesthetic && (
        <section className="px-6 md:px-16 py-24 md:py-40">
          <div className="mx-auto max-w-6xl">
            {/* 前置说明 */}
            <div className="mb-16 max-w-3xl">
              <p className="mono mb-4 text-fg-tertiary">看它怎么工作</p>
              <h2 className="font-display text-4xl md:text-6xl leading-tight text-fg-primary tracking-tight">
                AI 会这样<br />
                <span className="text-accent-aurora">读你的照片</span>。
              </h2>
              <p className="mt-6 text-base md:text-lg text-fg-secondary max-w-xl leading-relaxed">
                八维评分、自然语言点评、精选建议 —— 全部由模型基于你上传的原图给出。下面是它对这张雪山的真实输出。
              </p>
            </div>

            {/* 大照片 + 浮动卡片 · Apple 产品照式布局 */}
            <div className="relative rounded-2xl overflow-hidden aspect-[16/10] bg-bg-overlay">
              <Image
                src={demo.hero_photo.uri}
                alt=""
                fill
                sizes="(max-width: 1200px) 100vw, 1200px"
                className="object-cover"
              />
              {/* 桌面:右下浮卡;移动:section 下方独立 */}
              <div className="hidden md:block absolute right-6 bottom-6 max-w-[340px]">
                <ScoreCard photo={demo.hero_photo} />
              </div>
            </div>
            {/* 移动:卡片独立成一块 */}
            <div className="mt-6 md:hidden">
              <ScoreCard photo={demo.hero_photo} />
            </div>
          </div>
        </section>
      )}

      {/* ═════════════ 3. 三大能力 · Apple 风极简排列(去卡片装饰) ═════════════ */}
      <section className="px-6 md:px-16 py-24 md:py-40 border-t border-divider">
        <div className="mx-auto max-w-6xl">
          <div className="mb-20 max-w-3xl">
            <p className="mono mb-4 text-fg-tertiary">TrailLens 是什么</p>
            <h2 className="font-display text-4xl md:text-6xl leading-tight text-fg-primary tracking-tight">
              一个专为风光摄影师做的<br />
              <span className="text-accent-aurora">自动化后期助手</span>。
            </h2>
          </div>
          <div className="grid gap-12 md:gap-16 md:grid-cols-3">
            <Feature
              n="04"
              title="智能体协作"
              body="选片、点评、写游记、规划下一次。四个 AI 一起干,每步都留决策痕迹,想手动接管随时打断。"
            />
            <Feature
              n="5K+"
              title="专为风光的美学模型"
              body="5000+ 张风光原片微调,评构图、光线、氛围、情绪比通用模型更懂你。开源权重可自托管。"
            />
            <Feature
              n="03"
              title="打通 Claude · Cursor"
              body="EXIF、天气、日月轨迹三个独立 MCP server,可直接挂到任意 LLM 客户端,不用自己再造工具。"
            />
          </div>
        </div>
      </section>

      {/* ═════════════ 4. 三步走 · 大字克制排版 ═════════════ */}
      <section className="px-6 md:px-16 py-24 md:py-40 border-t border-divider">
        <div className="mx-auto max-w-6xl">
          <div className="mb-20 max-w-3xl">
            <p className="mono mb-4 text-fg-tertiary">怎么用</p>
            <h2 className="font-display text-4xl md:text-6xl leading-tight text-fg-primary tracking-tight">
              三步走。
            </h2>
          </div>
          <div className="grid gap-12 md:gap-8 md:grid-cols-3">
            <Step n="01" title="上传素材" body="拖入一次徒步的 RAW / JPG,后台并行处理,自动解析 EXIF、生成缩略图。" />
            <Step n="02" title="让 AI 干活" body="美学模型逐张打分,critic 写点评,story 生成游记,planner 建议下次机位。" />
            <Step n="03" title="导出 / 分享 / 找回" body="下载精选 zip,一键出小红书文,或用中文语义搜索翻整个照片库。" />
          </div>

          <div className="mt-24 flex justify-center">
            <a
              href="#top"
              className="group inline-flex items-center gap-1.5 text-xs text-fg-tertiary hover:text-fg-primary transition-colors"
            >
              <span className="inline-block rotate-180">↓</span>
              回顶部
            </a>
          </div>
        </div>
      </section>

      {/* ═════════════ Footer · 极简 ═════════════ */}
      <footer className="px-6 md:px-16 py-10 border-t border-divider">
        <div className="mx-auto max-w-6xl flex flex-wrap items-center justify-between gap-4 text-xs text-fg-tertiary">
          <p className="mono">© 2026 TrailLens · MIT 开源</p>
          <div className="flex gap-6">
            <Link href="/trails/demo" className="hover:text-fg-primary">示例</Link>
            <Link href="/library" className="hover:text-fg-primary">语义搜索</Link>
            <a href="https://github.com/lzf00/traillens" target="_blank" rel="noreferrer" className="hover:text-fg-primary">
              GitHub
            </a>
            <a href="https://www.zorotreeking.online/" target="_blank" rel="noreferrer" className="hover:text-fg-primary">
              @zoro ↗
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}

/* ───── 原子 ───── */
function CTAPrimary({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="group inline-flex items-center gap-2 rounded-full bg-white text-black px-6 py-3 text-sm font-medium transition-all hover:bg-white/90"
    >
      {children}
      <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}

function LinkPlain({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="text-sm text-white/70 hover:text-white transition-colors"
      style={{ textShadow: "0 1px 3px rgba(0,0,0,0.5)" }}
    >
      {children}
    </Link>
  );
}

function Feature({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div>
      <div className="font-display text-5xl md:text-6xl font-medium text-accent-aurora tracking-tight leading-none mb-6">
        {n}
      </div>
      <h3 className="font-display text-xl md:text-2xl text-fg-primary mb-3 tracking-tight">
        {title}
      </h3>
      <p className="text-sm md:text-base text-fg-secondary leading-relaxed">{body}</p>
    </div>
  );
}

function Step({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div className="border-t border-divider pt-6">
      <div className="mono text-fg-tertiary mb-3">{n}</div>
      <h4 className="font-display text-xl md:text-2xl text-fg-primary mb-3 tracking-tight">{title}</h4>
      <p className="text-sm md:text-base text-fg-secondary leading-relaxed">{body}</p>
    </div>
  );
}

/* ───── ScoreCard(保留但独立展示) ───── */
const DIM_LABELS: Array<[keyof Aesthetic, string]> = [
  ["composition", "构图"],
  ["visual_elements", "视觉"],
  ["technical", "技术"],
  ["originality", "原创"],
  ["theme", "主题"],
  ["emotion", "情感"],
  ["gestalt", "格式塔"],
];

function ScoreCard({ photo }: { photo: Photo }) {
  const a = photo.aesthetic ?? {};
  const overall = a.overall ?? 0;
  const critique = photo.critique ?? "";

  return (
    <div className="w-full rounded-2xl border border-divider/60 bg-bg-base/90 backdrop-blur-xl shadow-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <span className="inline-flex items-center gap-1 rounded-full bg-accent-aurora/15 text-accent-aurora text-xs px-2.5 py-1 font-medium">
          <Check size={12} /> 精选
        </span>
        <div className="text-right leading-none">
          <div className="mono text-[10px] text-fg-tertiary uppercase tracking-wide">AI 综合分</div>
          <div className="font-display text-4xl font-bold text-fg-primary mt-1 tracking-tight">
            {overall.toFixed(1)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-3 gap-y-2 mb-4">
        {DIM_LABELS.map(([k, label]) => {
          const v = (a[k] as number | undefined) ?? 0;
          const pct = Math.min(100, Math.max(0, v * 10));
          return (
            <div key={k} className="flex items-center gap-2">
              <span className="text-[11px] text-fg-tertiary shrink-0 w-9">{label}</span>
              <div className="h-1 flex-1 rounded-full bg-fg-tertiary/20 overflow-hidden">
                <div className="h-full bg-accent-aurora rounded-full" style={{ width: `${pct}%` }} />
              </div>
              <span className="mono text-[11px] text-fg-secondary w-7 text-right">{v.toFixed(1)}</span>
            </div>
          );
        })}
      </div>

      {critique && (
        <p className="text-xs text-fg-secondary leading-relaxed border-t border-divider/40 pt-3">
          <span className="mono text-fg-tertiary uppercase tracking-wide">AI 点评</span>
          <br />
          <span className="mt-1 block">{critique.length > 90 ? critique.slice(0, 90) + "…" : critique}</span>
        </p>
      )}
    </div>
  );
}
