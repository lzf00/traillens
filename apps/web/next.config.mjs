/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "*.cos.ap-shanghai.myqcloud.com" },
      { protocol: "https", hostname: "photos.traillens.zorotreeking.online" },
      { protocol: "https", hostname: "*.r2.cloudflarestorage.com" },
    ],
  },
  async rewrites() {
    if (process.env.NODE_ENV === "production") return [];
    return [
      { source: "/v1/:path*", destination: "http://localhost:8000/v1/:path*" },
    ];
  },
};

export default nextConfig;
