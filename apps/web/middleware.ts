/**
 * next-intl middleware:把 /xxx 当作中文,/en/xxx 走英文。
 *
 * 中文是默认 locale,前缀 "as-needed":
 *   /app/trails    → zh
 *   /en/app/trails → en
 *
 * 把 API 与 OG / 静态资源排除在 i18n 之外。
 */

import createMiddleware from "next-intl/middleware";
import { defaultLocale, locales } from "./i18n";

export default createMiddleware({
  locales: [...locales],
  defaultLocale,
  localePrefix: "as-needed",
});

export const config = {
  // 匹配除了 /api、/og、/_next、/static 之外的所有路径
  matcher: ["/((?!api|og|_next|static|.*\\..*).*)"],
};
