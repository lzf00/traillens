/**
 * 类型化 API client。
 *
 * - 路径 / 参数 / 响应 类型来自 OpenAPI(见 README.md)
 * - 自动从 cookie 或 localStorage 拿 Bearer token
 * - 401 自动跳登录
 *
 * 用法见 README.md。
 */

import createClient from "openapi-fetch";
import type { paths } from "./schema";

const baseUrl =
  (typeof window !== "undefined" && (window as any).TL_API_BASE) ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "";

export const api = createClient<paths>({
  baseUrl,
  credentials: "include",   // 带 better-auth cookie
});

// 中间件:401 自动跳登录
api.use({
  async onResponse({ response }) {
    if (response.status === 401 && typeof window !== "undefined") {
      window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
    }
    return response;
  },
});
