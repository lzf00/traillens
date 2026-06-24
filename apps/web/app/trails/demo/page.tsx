/**
 * /trails/demo — 重定向到当前最适合做 demo 的公开 trail。
 *
 * 后端 /v1/trails/_demo/public 自动选(有 travelogue + photo_count 高 + 最新)。
 * 失败 fallback 到 NEXT_PUBLIC_DEMO_TRAIL_ID env 或硬编码。
 */
import { redirect } from "next/navigation";
import { apiFetch } from "@/lib/api";

export const dynamic = "force-dynamic";

const FALLBACK_ID =
  process.env.NEXT_PUBLIC_DEMO_TRAIL_ID ||
  "eeac6041-5b15-461b-93e9-33244decfbfb";

export default async function DemoRedirect() {
  let demoId = FALLBACK_ID;
  try {
    const r = await apiFetch("/v1/trails/_demo/public", { cache: "no-store" });
    if (r.ok) {
      const t = await r.json();
      if (t?.id) demoId = t.id;
    }
  } catch {}
  redirect(`/trails/${demoId}/share`);
}
