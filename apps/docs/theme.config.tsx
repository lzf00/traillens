import type { DocsThemeConfig } from "nextra-theme-docs";

const config: DocsThemeConfig = {
  logo: <strong>TrailLens · Docs</strong>,
  project: { link: "https://github.com/lzf00/traillens" },
  chat: { link: "https://discord.gg/your-discord" },
  docsRepositoryBase: "https://github.com/lzf00/traillens/tree/main/apps/docs",
  footer: {
    content: (
      <span>
        © {new Date().getFullYear()} TrailLens · MIT.
      </span>
    ),
  },
  i18n: [
    { locale: "zh", name: "中文" },
    { locale: "en", name: "English" },
  ],
  sidebar: { defaultMenuCollapseLevel: 2 },
  head: (
    <>
      <link rel="icon" href="/favicon.ico" />
      <meta property="og:image" content="https://traillens.zorotreeking.online/og?kind=docs&title=Docs" />
    </>
  ),
};

export default config;
