/**
 * next-intl 配置入口(供 RSC 用)。
 * Sprint 5 末:把所有 page.tsx 的硬编码字符串切换到 useTranslations。
 */

import { getRequestConfig } from "next-intl/server";

export const locales = ["zh", "en"] as const;
export const defaultLocale = "zh" as const;

export type Locale = (typeof locales)[number];

export default getRequestConfig(async ({ locale }) => {
  const safeLocale: Locale = (locales as readonly string[]).includes(locale)
    ? (locale as Locale)
    : defaultLocale;

  return {
    locale: safeLocale,
    messages: (await import(`./messages/${safeLocale}.json`)).default,
    timeZone: "Asia/Shanghai",
  };
});
