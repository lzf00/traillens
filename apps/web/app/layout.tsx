import "@/styles/globals.css";
import type { Metadata } from "next";
import { Nav } from "@/components/Nav";

const SITE = "https://traillens.zorotreeking.online";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: "TrailLens — AI darkroom for landscape photographers",
  description: "把一整次徒步的素材,自动选片、点评、生成游记,并规划你下次的拍摄计划。",
  openGraph: {
    title: "TrailLens",
    description: "The AI darkroom for landscape photographers who hike.",
    url: SITE,
    siteName: "TrailLens",
    images: [{ url: "/og", width: 1200, height: 630 }],
    locale: "zh_CN",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "TrailLens",
    description: "The AI darkroom for landscape photographers who hike.",
    images: ["/og"],
  },
};

// 防 FOUC:在 hydration 之前同步设 html.theme-light
// 必须 inline + 同步;Next 会把 dangerouslySetInnerHTML 放到 head 早执行
const THEME_BOOT = `
(function() {
  try {
    var t = localStorage.getItem('traillens_theme');
    if (t === 'light') document.documentElement.classList.add('theme-light');
  } catch(e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT }} />
      </head>
      <body>
        <Nav />
        {children}
      </body>
    </html>
  );
}
