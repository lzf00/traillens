import Link from "next/link";
import Image from "next/image";
import { cookies } from "next/headers";
import { ArrowRight, Github, Users, Mountain, Cable, ChevronDown, ChevronUp, Check } from "lucide-react";
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
  // 优先 env(LANDING_TRAIL_ID 手动 pin 一个真风光 trail),否则走后端 _demo/public
  // 后端 pick_demo_trail 目前按 travelogue+photos+recency 排,会选到"名字风光其实
  // 宝可梦"的 trail;env 是最可靠的兜底
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
    const HERO_MIN = 6.5;
    const GRID_MIN = 7.5;
    const heroPhoto = pool.find((x) => (x.aesthetic?.overall ?? 0) >= HERO_MIN);
    const gridPhotos = pool.filter((x) => (x.aesthetic?.overall ?? 0) >= GRID_MIN);
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
      {/* ═════════════ HERO · 全屏照片 + 蒙层 + 中央文字 + 评分卡 ═════════════ */}
      <section className="relative isolate flex min-h-[calc(100dvh-56px)] items-center px-6 md:px-12 pb-24 md:pb-32">
        {/* 背景照片 */}
        {demo.hero_photo?.uri && (
          <Image
            src={demo.hero_photo.uri}
            alt="风光摄影示例"
            fill
            priority
            sizes="100vw"
            className="object-cover -z-20"
          />
        )}
        {/* 蒙层:左侧压暗给文字对比,右侧透明让主体照片完整露出;
           底部保留一点渐变过渡到下方 section 不硬切 */}
        <div className="absolute inset-0 -z-10 pointer-events-none">
          {/* 左→右:文字区暗,山峰主体亮 */}
          <div className="absolute inset-0 bg-gradient-to-r from-bg-base/75 via-bg-base/25 to-transparent" />
          {/* 底部渐变:hero 到下方 section 平滑过渡 */}
          <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-b from-transparent to-bg-base" />
        </div>
        {!demo.hero_photo?.uri && <div className="absolute inset-0 -z-20 bg-bg-base" />}

        <div className="mx-auto w-full max-w-5xl">
          <p className="mono mb-6 text-fg-secondary">v0.0.1 · build in public</p>

          {/* h1: mobile text-4xl 避免"AI 暗房"换行,md 起 text-7xl */}
          <h1 className="font-display text-4xl leading-[1.1] text-fg-primary md:text-7xl md:leading-[1.05] drop-shadow-[0_2px_20px_rgba(0,0,0,0.6)]">
            给徒步的
            <br />
            <span className="text-accent-aurora">风光摄影师</span>
            <br />
            <span className="whitespace-nowrap">造一间 AI 暗房。</span>
          </h1>

          <p className="mt-8 max-w-xl text-base md:text-xl text-fg-primary/90 leading-relaxed drop-shadow-[0_1px_8px_rgba(0,0,0,0.6)]">
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

        {/* 评分卡:浮在右下(桌面) / 底部(mobile),展示 AI 对 hero 图的真实分析 */}
        {demo.hero_photo?.aesthetic && (
          <ScoreCard photo={demo.hero_photo} className="absolute md:right-12 md:bottom-24 right-6 bottom-20 hidden md:block" />
        )}

        {/* 向下滚动引导 */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-fg-tertiary animate-bounce">
          <ChevronDown size={20} />
        </div>
      </section>

      {/* mobile 评分卡:hero 下方独立 section(避免 overlap 主标题) */}
      {demo.hero_photo?.aesthetic && (
        <section className="md:hidden px-6 -mt-6 mb-12">
          <ScoreCard photo={demo.hero_photo} />
        </section>
      )}

      {/* ═════════════ 作品网格 · 让人看见效果 ═════════════ */}
      {demo.gallery.length > 0 && (
        <section className="px-6 md:px-12 py-24">
          <div className="mx-auto max-w-6xl">
            <div className="mb-8 flex items-baseline justify-between gap-4 flex-wrap">
              <div>
                <p className="mono mb-2 text-fg-tertiary">看看它出什么样</p>
                <h2 className="font-display text-3xl md:text-4xl font-bold text-fg-primary">
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
            <h2 className="font-display text-3xl md:text-4xl font-bold text-fg-primary">
              一个专为风光摄影师做的
              <br />
              自动化后期助手。
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <Card
              badge="04"
              icon={<Users size={22} />}
              title="四个 AI 智能体协作"
              body="选片、点评、写游记、规划下一次 —— 每步都留决策痕迹。想手动接管随时打断,继续跑不丢进度。"
              tags={["选片", "点评", "游记", "计划"]}
            />
            <Card
              badge="5K+"
              icon={<Mountain size={22} />}
              title="专为风光调过的美学模型"
              body="5000+ 张风光原片微调,评构图、光线、氛围、情绪比通用模型更懂你。开源权重可自托管。"
              tags={["构图", "光线", "氛围", "情感"]}
            />
            <Card
              badge="3"
              icon={<Cable size={22} />}
              title="打通 Claude / Cursor"
              body="EXIF、天气、日月轨迹三个 MCP server 开源,直接挂到 Claude Desktop 或 Cursor,不用再自己造工具。"
              tags={["EXIF", "天气", "日月轨迹"]}
            />
          </div>
        </div>
      </section>

      {/* ═════════════ 3 步流程 ═════════════ */}
      <section className="px-6 md:px-12 py-24 border-t border-divider">
        <div className="mx-auto max-w-6xl">
          <p className="mono mb-2 text-fg-tertiary">怎么用</p>
          <h2 className="font-display text-3xl md:text-4xl font-bold text-fg-primary mb-12">
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

          {/* 回顶部 */}
          <div className="mt-16 flex justify-center">
            <a
              href="#top"
              className="group inline-flex items-center gap-1.5 rounded-full border border-divider bg-bg-raised/40 px-4 py-2 text-xs text-fg-secondary hover:text-fg-primary hover:border-accent-aurora/60 transition-all"
            >
              <ChevronUp size={14} className="transition-transform group-hover:-translate-y-0.5" />
              回顶部
            </a>
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
  badge, icon, title, body, tags,
}: {
  badge: string;
  icon: React.ReactNode;
  title: string;
  body: string;
  tags: string[];
}) {
  return (
    <div className="landing-card group relative overflow-hidden rounded-xl border border-divider bg-bg-raised p-6
                    shadow-sm
                    transition-all duration-DEFAULT ease-trail
                    hover:border-accent-aurora hover:-translate-y-1
                    hover:shadow-xl hover:shadow-accent-aurora/10">
      {/* 顶部装饰细线,hover 时变绿(light 常态就有淡绿:见 globals.css) */}
      <div className="landing-card-topline absolute inset-x-0 top-0 h-0.5 bg-divider transition-colors group-hover:bg-accent-aurora" />

      {/* 头部:大数字 + 实心 icon */}
      <div className="mb-6 flex items-center justify-between">
        <div className="font-display text-4xl font-bold leading-none text-accent-aurora tracking-tight">
          {badge}
        </div>
        <div className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-accent-aurora text-bg-base shadow-lg shadow-accent-aurora/40">
          {icon}
        </div>
      </div>

      {/* 标题 */}
      <h3 className="font-display text-xl font-semibold text-fg-primary mb-2 leading-snug">
        {title}
      </h3>
      <p className="text-sm text-fg-secondary leading-relaxed mb-5">{body}</p>

      {/* 底部技术栈 tag(中文不用 mono,字号 12,更清晰) */}
      <div className="flex flex-wrap gap-2 pt-4 border-t border-divider">
        {tags.map((t) => (
          <span
            key={t}
            className="landing-tag text-xs rounded-full border border-divider bg-bg-base px-2.5 py-1 text-fg-secondary transition-colors group-hover:border-accent-aurora/40 group-hover:text-accent-aurora"
          >
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}

function Step({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div className="relative">
      {/* 大号编号 · 抢眼但克制 */}
      <div className="mono text-6xl md:text-7xl font-bold text-accent-glacier/20 leading-none mb-2 select-none">
        {n}
      </div>
      <h4 className="font-display text-xl md:text-2xl text-fg-primary mb-3">{title}</h4>
      <p className="text-sm text-fg-secondary leading-relaxed">{body}</p>
    </div>
  );
}

/* ───── ScoreCard · AI 对 hero 照片的实测输出卡 ───── */
const DIM_LABELS: Array<[keyof Aesthetic, string]> = [
  ["composition", "构图"],
  ["visual_elements", "视觉"],
  ["technical", "技术"],
  ["originality", "原创"],
  ["theme", "主题"],
  ["emotion", "情感"],
  ["gestalt", "格式塔"],
];

function ScoreCard({ photo, className = "" }: { photo: Photo; className?: string }) {
  const a = photo.aesthetic ?? {};
  const overall = a.overall ?? 0;
  const critique = photo.critique ?? "";

  return (
    <div
      className={
        "w-[300px] rounded-lg border border-divider/60 bg-bg-base/85 backdrop-blur-md shadow-2xl p-4 " +
        className
      }
    >
      {/* 头部:verdict + 分数 */}
      <div className="flex items-center justify-between mb-3">
        <span className="inline-flex items-center gap-1 rounded-md bg-accent-aurora/15 text-accent-aurora text-xs px-2 py-0.5">
          <Check size={12} /> keep
        </span>
        <div className="text-right leading-none">
          <div className="mono text-[10px] text-fg-tertiary">AI 综合</div>
          <div className="font-display text-3xl text-fg-primary">
            {overall.toFixed(1)}
          </div>
        </div>
      </div>

      {/* 8 维 bar */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 mb-3">
        {DIM_LABELS.map(([k, label]) => {
          const v = (a[k] as number | undefined) ?? 0;
          const pct = Math.min(100, Math.max(0, v * 10));
          return (
            <div key={k} className="flex items-center gap-1.5">
              <span className="text-[10px] text-fg-tertiary shrink-0 w-8">{label}</span>
              <div className="h-1 flex-1 rounded-full bg-fg-tertiary/20 overflow-hidden">
                <div
                  className="h-full bg-accent-aurora rounded-full"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="mono text-[10px] text-fg-secondary w-6 text-right">
                {v.toFixed(1)}
              </span>
            </div>
          );
        })}
      </div>

      {/* critique 摘要 */}
      {critique && (
        <p className="text-xs text-fg-secondary leading-snug border-t border-divider/40 pt-3">
          <span className="mono text-fg-tertiary">AI 点评 · </span>
          {critique.length > 70 ? critique.slice(0, 70) + "…" : critique}
        </p>
      )}
    </div>
  );
}
