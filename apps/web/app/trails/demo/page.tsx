/**
 * /trails/demo — 重定向到公开 demo trail 的分享页。
 *
 * trail_id 由 NEXT_PUBLIC_DEMO_TRAIL_ID env 配置;
 * 默认指向 "202605 雅拉温泉线"(本人手上的 seed)。
 */
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

const DEMO_ID =
  process.env.NEXT_PUBLIC_DEMO_TRAIL_ID ||
  "3209f766-1090-464c-8d85-e57c1bbc9fa0";

export default function DemoRedirect() {
  redirect(`/trails/${DEMO_ID}/share`);
}
