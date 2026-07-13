/**
 * 公开分享页 — Trail 的精选 + 游记 + 拍摄计划。
 *
 * 设计:
 * - **不需要登录**:这是 growth loop 的入口
 * - **SSR + 长缓存**:有助 SEO,被搜索引擎抓取后沉淀地点+照片流量
 * - **JSON-LD**:Schema.org Photograph 让 Google Images 收录单张照片
 * - **OG card 动态化**:/og?kind=trail&title=...&kept=...
 *
 * 参考 PRODUCT_PLAN §5.3 Anti-churn:每次跑完 trail 自动生成分享卡片 → 用户分享到小红书。
 */

import type { Metadata } from "next";
import Image from "next/image";
import { notFound } from "next/navigation";

// 分享页不需要登录,SSR 直接走 server-side 内网 URL,不走 apiFetch
// (apiFetch 会调 cookies() 让 ISR 报错)
const API = process.env.TRAILLENS_API_INTERNAL_BASE || process.env.NEXT_PUBLIC_API_BASE || "";

// Next.js 15: dynamic route params are Promise-wrapped
type PageProps = { params: Promise<{ id: string }> };

type Trail = {
  id: string;
  name: string;
  location_name?: string | null;
  travelogue_md?: string | null;
  next_trip_plan?: Record<string, any> | null;
  photo_count: number;
  created_at: string;
};

type Photo = {
  photo_id: string;
  uri: string;
  verdict?: string;
  aesthetic?: { overall: number };
};

async function fetchTrail(id: string): Promise<Trail | null> {
  try {
    const r = await fetch(`${API}/v1/trails/${id}/public`, { next: { revalidate: 60 } });
    if (!r.ok) return null;
    return r.json();
  } catch {
    return null;
  }
}

async function fetchPhotos(id: string): Promise<Photo[]> {
  try {
    const r = await fetch(`${API}/v1/trails/${id}/photos/public`, { next: { revalidate: 60 } });
    if (!r.ok) return [];
    return r.json();
  } catch {
    return [];
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const [trail, photos] = await Promise.all([fetchTrail(id), fetchPhotos(id)]);
  if (!trail) return {};

  const title = `${trail.name}${trail.location_name ? ` · ${trail.location_name}` : ""}`;
  const desc = trail.travelogue_md?.slice(0, 200) || `用 TrailLens 整理的一次徒步影像。`;

  // 优先用首张 keep 照片做封面(微信/小红书视觉冲击);没有就用任意第一张;再没有走 /og 文字卡
  const cover =
    photos.find((p) => p.verdict === "keep") || photos[0];
  const ogImage = cover?.uri ?? `/og?${new URLSearchParams({
    kind: "trail",
    title,
    subtitle: trail.location_name ?? "TrailLens",
    kept: String(trail.photo_count),
  })}`;

  return {
    title: `${title} — TrailLens`,
    description: desc,
    openGraph: {
      title,
      description: desc,
      images: [{ url: ogImage, width: 1200, height: 630 }],
      type: "article",
      siteName: "TrailLens",
    },
    twitter: { card: "summary_large_image", title, images: [ogImage] },
    other: {
      // 微信内置浏览器额外认这两个
      "itemprop:image": ogImage,
      "weixin:image": ogImage,
    },
  };
}

export default async function SharePage({ params }: PageProps) {
  const { id } = await params;
  const trail = await fetchTrail(id);
  if (!trail) notFound();
  const allPhotos = await fetchPhotos(id);
  const keepPhotos = allPhotos.filter((p) => p.verdict === "keep");
  // 优先精选 keep;若无 keep 但有照片,fallback 显示全部并加横幅
  const showingAll = keepPhotos.length === 0 && allPhotos.length > 0;
  const photos = showingAll ? allPhotos : keepPhotos;

  // JSON-LD: schema.org/ImageGallery + Photograph,助 Google Images 收录
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ImageGallery",
    name: trail.name,
    description: trail.travelogue_md?.slice(0, 500),
    dateCreated: trail.created_at,
    contentLocation: trail.location_name ? { "@type": "Place", name: trail.location_name } : undefined,
    image: photos.map((p) => ({
      "@type": "Photograph",
      "@id": p.uri,
      contentUrl: p.uri,
    })),
  };

  const hero = photos[0];
  const rest = photos.slice(1);
  const planEntries = Object.entries(trail.next_trip_plan ?? {});

  return (
    <article>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Hero 大图: 全屏宽,带遮罩 + 标题叠加 */}
      {hero && (
        <section className="relative w-full h-[70vh] min-h-[480px] overflow-hidden bg-bg-overlay">
          <Image
            src={hero.uri}
            alt={trail.name}
            fill
            priority
            sizes="100vw"
            className="object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-bg-base via-bg-base/30 to-transparent" />
          <div className="absolute inset-x-0 bottom-0 px-6 py-12 md:px-16">
            <div className="mx-auto max-w-5xl">
              <p className="mono mb-3 text-fg-secondary">{trail.location_name ?? "TrailLens"}</p>
              <h1 className="font-display text-4xl md:text-6xl text-fg-primary leading-tight drop-shadow-2xl">
                {trail.name}
              </h1>
              <p className="mt-4 text-sm text-fg-secondary">
                {showingAll
                  ? `${photos.length} 张 · 作者尚未标记精选`
                  : `${photos.length} 张精选`}
                {" · "}
                <time dateTime={trail.created_at}>
                  {new Date(trail.created_at).toLocaleDateString("zh-CN", {
                    year: "numeric", month: "long", day: "numeric",
                  })}
                </time>
              </p>
            </div>
          </div>
        </section>
      )}

      <div className="mx-auto max-w-5xl px-6 py-16">
        {/* 空状态: trail 完全没照片 */}
        {photos.length === 0 && (
          <div className="rounded-md border border-dashed border-divider px-6 py-16 text-center">
            <p className="mono text-xs text-fg-tertiary mb-3">EMPTY</p>
            <p className="text-fg-secondary">作者还没上传照片。</p>
          </div>
        )}

        {/* 剩余照片网格(hero 之外) */}
        {rest.length > 0 && (
          <section className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {rest.map((p) => (
              <figure key={p.photo_id} className="photo-frame relative aspect-[3/2] bg-bg-overlay overflow-hidden">
                <Image
                  src={p.uri}
                  alt={`${trail.name} — ${p.photo_id}`}
                  fill
                  sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw"
                  className="object-cover transition-transform duration-DEFAULT ease-trail hover:scale-[1.03]"
                />
                {showingAll && p.verdict && (
                  <figcaption className="absolute top-2 left-2 status-pill backdrop-blur capitalize">
                    {p.verdict}
                  </figcaption>
                )}
                {p.aesthetic && (
                  <figcaption className="absolute bottom-2 right-2 status-pill backdrop-blur">
                    {p.aesthetic.overall.toFixed(1)}
                  </figcaption>
                )}
              </figure>
            ))}
          </section>
        )}

        {/* 游记 */}
        {trail.travelogue_md && (
          <section className="prose prose-invert mt-16 max-w-2xl">
            <h2 className="font-display">游记</h2>
            <div className="whitespace-pre-wrap text-fg-primary">{trail.travelogue_md}</div>
          </section>
        )}

        {/* 下次拍摄计划 — 结构化渲染 */}
        {planEntries.length > 0 && (
          <section className="mt-16 max-w-2xl border-t border-divider pt-12">
            <h2 className="font-display text-2xl mb-6">下次再来同一地点</h2>
            <dl className="flex flex-col gap-5">
              {planEntries.map(([k, v]) => (
                <div key={k} className="grid grid-cols-[120px_1fr] gap-4 items-baseline">
                  <dt className="mono text-fg-tertiary text-xs uppercase">
                    {(
                      {
                        best_windows: "最佳时间窗",
                        weather_note: "天气备注",
                        gear_checklist: "装备清单",
                        recommended_focal_mm: "推荐焦段",
                        note: "备注",
                        location: "地点",
                        season: "季节",
                        best_time: "最佳时段",
                        tips: "小贴士",
                      } as Record<string, string>
                    )[k] ?? k}
                  </dt>
                  <dd className="text-fg-primary text-sm">
                    {Array.isArray(v)
                      ? v.map(String).join("、")
                      : typeof v === "object" && v !== null
                        ? JSON.stringify(v)
                        : String(v)}
                  </dd>
                </div>
              ))}
            </dl>
          </section>
        )}

        {/* 引流 CTA */}
        <section className="mt-20 border-t border-divider pt-12">
          <div className="rounded-lg border border-divider bg-bg-raised p-8 text-center">
            <p className="mono text-xs text-fg-tertiary mb-2">用 TrailLens 整理你自己的徒步</p>
            <h3 className="font-display text-2xl text-fg-primary mb-4">
              AI 自动选片 · 八维评分 · 写游记 · 规划下次拍摄
            </h3>
            <div className="flex justify-center gap-3 flex-wrap">
              <a
                href="/signup"
                className="rounded-md bg-accent-aurora px-5 py-2.5 text-sm font-medium text-bg-base hover:bg-accent-aurora/90 transition-colors"
              >
                免费注册
              </a>
              <a
                href="/"
                className="rounded-md border border-divider px-5 py-2.5 text-sm text-fg-primary hover:border-accent-glacier hover:text-accent-glacier transition-colors"
              >
                了解更多
              </a>
            </div>
          </div>
        </section>

        {/* footer */}
        <footer className="mt-12 pt-8 text-center">
          <p className="mono text-fg-tertiary text-xs">
            由{" "}
            <a className="text-accent-aurora hover:underline" href="https://traillens.zorotreeking.online">
              TrailLens
            </a>{" "}
            自动生成 · AI darkroom for landscape photographers
          </p>
        </footer>
      </div>
    </article>
  );
}
