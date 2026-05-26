import "@/styles/globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TrailLens — AI darkroom for landscape photographers",
  description:
    "把一整次徒步的素材,自动选片、点评、生成游记,并规划你下次的拍摄计划。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
