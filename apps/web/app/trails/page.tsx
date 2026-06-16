/**
 * /trails — 用户自己的 trail 列表。
 *
 * 未登录跳 /login。
 * 空列表显示 onboarding 提示 + "新建" CTA。
 */

import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Plus } from "lucide-react";

type Trail = {
  id: string;
  name: string;
  location_name: string | null;
  photo_count: number;
  created_at: string;
  updated_at: string;
};

async function fetchTrails(userId: string): Promise<Trail[]> {
  try {
    const r = await apiFetch("/v1/trails", { cache: "no-store" }, userId);
    if (!r.ok) return [];
    return r.json();
  } catch {
    return [];
  }
}

export default async function TrailsPage() {
  const c = await cookies();
  const userId = c.get("traillens_user_id")?.value;
  if (!userId) redirect("/login");

  const trails = await fetchTrails(userId);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-10 flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl text-fg-primary">我的 Trails</h1>
          <p className="mt-1 text-sm text-fg-tertiary">
            {trails.length === 0
              ? "还没有 trail。开始上传一组照片吧。"
              : `${trails.length} 条记录`}
          </p>
        </div>
        <Link
          href="/trails/new"
          className="flex items-center gap-1.5 rounded-md bg-accent-aurora px-4 py-2 text-sm font-medium text-bg-base hover:bg-accent-aurora/90 transition-colors"
        >
          <Plus size={14} />
          新建 Trail
        </Link>
      </header>

      {trails.length === 0 ? (
        <div className="rounded-md border border-dashed border-divider px-6 py-16 text-center">
          <p className="mono text-xs text-fg-tertiary mb-3">EMPTY</p>
          <h2 className="font-display text-xl text-fg-primary mb-2">
            开始你的第一次徒步整理
          </h2>
          <p className="text-sm text-fg-secondary mb-6">
            上传一组照片，AI 自动选片、点评、写游记，规划你下次再来该地点的拍摄计划。
          </p>
          <Link
            href="/trails/new"
            className="inline-flex items-center gap-1.5 rounded-md bg-accent-aurora px-5 py-2.5 text-sm font-medium text-bg-base hover:bg-accent-aurora/90 transition-colors"
          >
            <Plus size={14} />
            创建第一个 Trail
          </Link>
        </div>
      ) : (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {trails.map((t) => (
            <Link
              key={t.id}
              href={`/trails/${t.id}`}
              className="block rounded-md border border-divider bg-bg-raised p-4 hover:border-accent-aurora transition-colors"
            >
              <h3 className="font-display text-lg text-fg-primary mb-1 truncate">
                {t.name}
              </h3>
              <p className="text-sm text-fg-secondary mb-3 truncate">
                {t.location_name || "未指定位置"}
              </p>
              <div className="flex items-center justify-between text-xs">
                <span className="status-pill">{t.photo_count} 张</span>
                <time className="mono text-fg-tertiary" dateTime={t.updated_at}>
                  {new Date(t.updated_at).toLocaleDateString("zh-CN")}
                </time>
              </div>
            </Link>
          ))}
        </section>
      )}
    </main>
  );
}
