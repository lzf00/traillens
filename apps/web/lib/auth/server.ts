/**
 * Better-Auth(better-auth.com)server-side 配置。
 *
 * 为什么选 Better-Auth(决策 D6):
 *  - 开源、零供应商锁定(对比 Clerk)
 *  - 与 Drizzle / Prisma / 自带 SQLAlchemy 都能配
 *  - 内置 magic link / OAuth / passkey,与产品定位匹配
 *
 * Sprint 5 末把 stub 换成真实:
 *   import { betterAuth } from "better-auth";
 *   import { drizzleAdapter } from "better-auth/adapters/drizzle";
 */

export type Session = {
  user: { id: string; email: string; plan: "free" | "pro" | "pro_plus" };
  expiresAt: Date;
};

// 临时 stub(开发期);Sprint 5 末替换。
export async function getSession(): Promise<Session | null> {
  if (process.env.NODE_ENV === "production") {
    // [TODO] 真实:从 Better-Auth cookie 读 session,验证后返回
    return null;
  }
  // dev:固定假用户,与 apps/api/traillens_api/deps.py 保持一致
  return {
    user: {
      id: process.env.DEV_USER_ID || "dev-user-001",
      email: process.env.DEV_USER_EMAIL || "dev@traillens.local",
      plan: (process.env.DEV_USER_PLAN as Session["user"]["plan"]) || "free",
    },
    expiresAt: new Date(Date.now() + 86400000),
  };
}

/**
 * 在 RSC / Server Action 里:
 *   const session = await requireSession();
 *   if (!session) redirect("/login");
 */
export async function requireSession(): Promise<Session> {
  const s = await getSession();
  if (!s) throw new Error("not_authenticated");
  return s;
}
