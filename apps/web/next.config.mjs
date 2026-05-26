/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "*.r2.cloudflarestorage.com" },
      { protocol: "https", hostname: "photos.traillens.example" },
    ],
  },
  async rewrites() {
    // dev: 把 /v1/* 反代到本地 FastAPI,避免跨域
    return [
      { source: "/v1/:path*", destination: "http://localhost:8000/v1/:path*" },
    ];
  },
};

export default nextConfig;
