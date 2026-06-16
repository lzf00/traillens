/**
 * Auth dev 桥 — catch-all。
 *
 * 当前支持的 path：
 *   POST /api/auth/sign-in  (form: email)
 *     → 写 cookie traillens_user_email + traillens_user_id (md5-ish hash of email)
 *     → 302 → /trails
 *   POST /api/auth/sign-out
 *     → 清 cookie → 302 → /
 *
 * Sprint 5 末换 Better Auth：替换为 auth.handler，URL/路径不变。
 */

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { createHash } from "crypto";

// email cookie 防泄漏 → httpOnly
const EMAIL_COOKIE_OPTS = {
  httpOnly: true,
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60 * 24 * 30,
  secure: process.env.NODE_ENV === "production",
};
// user_id cookie 客户端 JS 要读出来给跨域 API 加 header → httpOnly:false
const USER_ID_COOKIE_OPTS = {
  httpOnly: false,
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60 * 24 * 30,
  secure: process.env.NODE_ENV === "production",
};

function userIdFromEmail(email: string): string {
  // 把 email 哈希成稳定的 user_id（dev 桥用）
  return "u-" + createHash("sha256").update(email.toLowerCase().trim()).digest("hex").slice(0, 16);
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ all: string[] }> }
) {
  const { all } = await params;
  const path = all.join("/");

  if (path === "sign-in") {
    const form = await req.formData();
    const email = String(form.get("email") || "").trim();
    if (!email) return redirect("/login?error=missing_email");

    const c = await cookies();
    c.set("traillens_user_email", email, EMAIL_COOKIE_OPTS);
    c.set("traillens_user_id", userIdFromEmail(email), USER_ID_COOKIE_OPTS);
    return redirect("/trails");
  }

  if (path === "sign-out") {
    const c = await cookies();
    c.delete("traillens_user_email");
    c.delete("traillens_user_id");
    return redirect("/");
  }

  return Response.json({ error: "unknown_auth_route", path }, { status: 404 });
}

export async function GET() {
  return Response.json({ stub: true, message: "Auth dev bridge active" });
}
