import Link from "next/link";
import { getTranslations } from "next-intl/server";

/**
 * Landing page。一屏内说清:是什么 / 怎么用 / 凭什么相信。
 * 文案由 messages/{zh,en}.json 提供;参考 PRODUCT_PLAN.md §2.2 视觉系统。
 */
export default async function HomePage() {
  const t = await getTranslations("Landing");
  return (
    <main className="min-h-dvh px-6 py-24 md:px-12">
      <div className="mx-auto max-w-3xl">
        <p className="mono mb-8">v0.0.1 · build in public</p>

        <h1 className="font-display text-5xl leading-tight text-fg-primary md:text-7xl">
          {t("tagline_l1")}
          <br />
          <span className="text-accent-aurora">{t("tagline_l2")}</span>
          <br />
          {t("tagline_l3")}
        </h1>

        <p className="mt-8 text-lg text-fg-secondary md:text-xl">{t("subtitle")}</p>

        <div className="mt-12 flex flex-wrap items-center gap-3">
          <Link
            href="/trails/demo"
            className="rounded-md bg-accent-aurora px-5 py-3 text-sm font-medium text-bg-base
                       transition-all duration-DEFAULT ease-trail hover:bg-accent-aurora/90"
          >
            {t("cta_demo")}
          </Link>
          <Link
            href="https://github.com/your-handle/traillens"
            target="_blank"
            className="rounded-md border border-divider px-5 py-3 text-sm text-fg-primary
                       transition-all hover:border-accent-glacier hover:text-accent-glacier"
          >
            {t("cta_github")}
          </Link>
        </div>

        <div className="mt-24 grid gap-8 text-sm text-fg-secondary md:grid-cols-3">
          <Feature title={t("feature_agents_title")} body={t("feature_agents_body")} />
          <Feature title={t("feature_model_title")} body={t("feature_model_body")} />
          <Feature title={t("feature_mcp_title")} body={t("feature_mcp_body")} />
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
