/**
 * Better-Auth 的 catch-all route handler。
 * Sprint 5 末:
 *   import { auth } from "@/lib/auth/server";
 *   export const { GET, POST } = auth.handler;
 *
 * 当前 stub:返回 200 stub session,前端不会因为 auth 端点 404 而崩。
 */

export async function GET(req: Request) {
  return Response.json({
    stub: true,
    message: "Better-Auth not wired yet; see Sprint 5 in PRODUCT_PLAN.md",
  });
}

export async function POST(req: Request) {
  return Response.json({ stub: true });
}
