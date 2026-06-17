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
import { notFound } from "next/navigation";
import { apiFetch } from "@/lib/api";

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
  const r = await apiFetch(`/v1/trails/${id}/public`, { next: { revalidate: 60 } });
  if (!r.ok) return null;
  return r.json();
}

async function fetchPhotos(id: string): Promise<Photo[]> {
  const r = await apiFetch(`/v1/trails/${id}/photos/public`, { next: { revalidate: 60 } });
  if (!r.ok) return [];
  return r.json();
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const trail = await fetchTrail(id);
  if (!trail) return {};
  const title = `${trail.name} · ${trail.location_name ?? "Trail"}`;
  const ogParams = new URLSearchParams({
    kind: "trail",
    title,
    subtitle: trail.location_name ?? "TrailLens",
    kept: String(trail.photo_count),
  });
  return {
    title: `${title} — TrailLens`,
    description: trail.travelogue_md?.slice(0, 200) || `A trail captured with TrailLens.`,
    openGraph: {
      title,
      description: trail.travelogue_md?.slice(0, 200) || "",
      images: [{ url: `/og?${ogParams}`, width: 1200, height: 630 }],
      type: "article",
    },
    twitter: { card: "summary_large_image", title, images: [`/og?${ogParams}`] },
  };
}

export default async function SharePage({ params }: PageProps) {
  const { id } = await params;
  const trail = await fetchTrail(id);
  if (!trail) notFound();
  const photos = (await fetchPhotos(id)).filter((p) => p.verdict === "keep");

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

  return (
    <article className="mx-auto max-w-5xl px-6 py-16">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <header className="mb-12">
        <p className="mono mb-3">{trail.location_name ?? "TrailLens"}</p>
        <h1 className="font-display text-5xl text-fg-primary leading-tight">{trail.name}</h1>
        <p className="mt-4 text-fg-secondary">
          {photos.length} 张精选 ·{" "}
          <time dateTime={trail.created_at}>
            {new Date(trail.created_at).toLocaleDateString("zh-CN", {
              year: "numeric", month: "long", day: "numeric",
            })}
          </time>
        </p>
      </header>

      {/* 照片网格 */}
      <section className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {photos.map((p) => (
          <figure key={p.photo_id} className="photo-frame relative aspect-[3/2] bg-bg-overlay">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={p.uri}
              alt={`${trail.name} — ${p.photo_id}`}
              loading="lazy"
              className="h-full w-full object-cover"
            />
            {p.aesthetic && (
              <figcaption className="absolute bottom-2 right-2 status-pill backdrop-blur">
                {p.aesthetic.overall.toFixed(1)}
              </figcaption>
            )}
          </figure>
        ))}
      </section>

      {/* 游记 */}
      {trail.travelogue_md && (
        <section className="prose prose-invert mt-16 max-w-2xl">
          <h2 className="font-display">游记</h2>
          <div className="whitespace-pre-wrap text-fg-primary">{trail.travelogue_md}</div>
        </section>
      )}

      {/* 下次拍摄计划 */}
      {trail.next_trip_plan && (
        <section className="mt-12 max-w-2xl border-t border-divider pt-12">
          <h2 className="font-display text-2xl">下次再来同一地点</h2>
          <pre className="mono mt-4 rounded-md bg-bg-raised p-4 text-xs">
            {JSON.stringify(trail.next_trip_plan, null, 2)}
          </pre>
        </section>
      )}

      {/* footer:TrailLens 自我宣传 */}
      <footer className="mt-24 border-t border-divider pt-8 text-center">
        <p className="mono text-fg-tertiary">
          由{" "}
          <a className="text-accent-aurora hover:underline" href="https://traillens.zorotreeking.online">
            TrailLens
          </a>{" "}
          自动生成 · AI darkroom for landscape photographers
        </p>
      </footer>
    </article>
  );
}
