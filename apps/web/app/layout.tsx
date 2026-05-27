import "@/styles/globals.css";
import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";

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

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
