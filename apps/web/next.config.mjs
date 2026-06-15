import createNextIntlPlugin from "next-intl/plugin";

// next-intl 找 ./i18n.ts 做请求级 locale 解析
const withNextIntl = createNextIntlPlugin("./i18n.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "*.cos.ap-shanghai.myqcloud.com" },
      { protocol: "https", hostname: "photos.traillens.zorotreeking.online" },
      { protocol: "https", hostname: "*.r2.cloudflarestorage.com" },
    ],
  },
  async rewrites() {
    // dev: 把 /v1/* 反代到本地 FastAPI; prod: 直接走 NEXT_PUBLIC_API_BASE
    if (process.env.NODE_ENV === "production") return [];
    return [
      { source: "/v1/:path*", destination: "http://localhost:8000/v1/:path*" },
    ];
  },
};

export default withNextIntl(nextConfig);
