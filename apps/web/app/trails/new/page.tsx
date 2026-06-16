"use client";

/**
 * /trails/new — 创建 Trail + 上传照片。
 *
 * 流程：
 *  1. 用户输 name + location + 选 N 张照片
 *  2. POST /v1/trails → 拿 trail_id
 *  3. POST /v1/trails/{id}/photos:presign → 拿 N 个 PUT URL
 *  4. 浏览器并行 PUT 每张到 COS（可能受 CORS 限制）
 *  5. 全部成功 → POST /v1/trails/{id}/photos:bulk 注册 URI
 *  6. 跳 /trails/{id}
 *
 * 如果 PUT 失败：显示具体错误 + 一键重试。
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Upload, Image as ImageIcon, X, AlertCircle } from "lucide-react";

type Stage = "form" | "creating" | "presigning" | "uploading" | "registering" | "done" | "error";

export default function NewTrailPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [stage, setStage] = useState<Stage>("form");
  const [progress, setProgress] = useState({ uploaded: 0, total: 0 });
  const [error, setError] = useState<string | null>(null);

  function addFiles(fl: FileList | null) {
    if (!fl) return;
    const incoming = Array.from(fl).filter((f) => f.type.startsWith("image/"));
    setFiles((prev) => [...prev, ...incoming]);
  }

  function removeFile(idx: number) {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!name.trim() || files.length === 0) {
      setError("名称和至少一张照片是必填");
      return;
    }

    // 1. 创建 trail
    setStage("creating");
    const createRes = await apiFetch("/v1/trails", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name.trim(),
        location_name: location.trim() || null,
        gpx_uri: null,
      }),
    });
    if (!createRes.ok) {
      setStage("error");
      setError(`创建 Trail 失败：HTTP ${createRes.status}`);
      return;
    }
    const trail = await createRes.json();

    // 2. presign
    setStage("presigning");
    const presignRes = await apiFetch(`/v1/trails/${trail.id}/photos:presign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        files: files.map((f) => ({
          filename: f.name,
          content_type: f.type || "image/jpeg",
        })),
      }),
    });
    if (!presignRes.ok) {
      setStage("error");
      setError(`获取上传地址失败：HTTP ${presignRes.status}`);
      return;
    }
    const presign = await presignRes.json();
    const uploads: Array<{ photo_id: string; put_url: string | null; public_url: string | null }> =
      presign.uploads;

    // 3. PUT to COS (并行)
    setStage("uploading");
    setProgress({ uploaded: 0, total: files.length });
    const results: { uri: string }[] = [];
    let uploaded = 0;
    let firstError: string | null = null;

    await Promise.all(
      files.map(async (file, i) => {
        const u = uploads[i];
        if (!u.put_url || !u.public_url) {
          if (!firstError) firstError = "后端未配置对象存储 (presigned URL 为空)";
          return;
        }
        try {
          const r = await fetch(u.put_url, {
            method: "PUT",
            headers: { "Content-Type": file.type || "image/jpeg" },
            body: file,
          });
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          results.push({ uri: u.public_url });
          uploaded++;
          setProgress({ uploaded, total: files.length });
        } catch (err) {
          if (!firstError) firstError = `照片 ${file.name} 上传失败：${(err as Error).message}（可能是 COS CORS 未配置）`;
        }
      })
    );

    if (firstError && results.length === 0) {
      setStage("error");
      setError(firstError);
      return;
    }

    // 4. 注册到 trail
    setStage("registering");
    const bulkRes = await apiFetch(`/v1/trails/${trail.id}/photos:bulk`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ photos: results }),
    });
    if (!bulkRes.ok) {
      setStage("error");
      setError(`注册照片失败：HTTP ${bulkRes.status}`);
      return;
    }

    setStage("done");
    router.push(`/trails/${trail.id}`);
  }

  const stageLabel: Record<Stage, string> = {
    form: "",
    creating: "创建 Trail…",
    presigning: "申请上传地址…",
    uploading: `上传中 ${progress.uploaded}/${progress.total}`,
    registering: "注册照片…",
    done: "完成,跳转…",
    error: "出错了",
  };

  const isBusy = stage !== "form" && stage !== "error";

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <header className="mb-8">
        <h1 className="font-display text-3xl text-fg-primary mb-1">新建 Trail</h1>
        <p className="text-sm text-fg-tertiary">
          每次徒步=一个 Trail。先输入名字、选位置,然后上传一组照片(JPG/PNG/RAW)。
        </p>
      </header>

      <form onSubmit={submit} className="flex flex-col gap-5">
        <label className="flex flex-col gap-1.5">
          <span className="text-xs text-fg-secondary mono">名称 *</span>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="2026.06 川西理塘"
            className="rounded-md bg-bg-raised border border-divider px-3 py-2.5 text-fg-primary placeholder:text-fg-tertiary"
            disabled={isBusy}
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-xs text-fg-secondary mono">位置(可选)</span>
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="四川 · 理塘 · 海子山"
            className="rounded-md bg-bg-raised border border-divider px-3 py-2.5 text-fg-primary placeholder:text-fg-tertiary"
            disabled={isBusy}
          />
        </label>

        <div className="flex flex-col gap-2">
          <span className="text-xs text-fg-secondary mono">照片 *</span>

          <label
            className={`flex flex-col items-center justify-center gap-2 rounded-md border border-dashed border-divider px-6 py-10 cursor-pointer hover:border-accent-aurora transition-colors ${
              isBusy ? "opacity-50 pointer-events-none" : ""
            }`}
          >
            <Upload size={20} className="text-fg-tertiary" />
            <span className="text-sm text-fg-secondary">点击或拖入文件 · 支持多选</span>
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(e) => addFiles(e.target.files)}
              className="hidden"
              disabled={isBusy}
            />
          </label>

          {files.length > 0 && (
            <ul className="flex flex-col gap-1 max-h-64 overflow-auto">
              {files.map((f, i) => (
                <li
                  key={i}
                  className="flex items-center gap-2 rounded-md bg-bg-raised px-3 py-2 text-sm"
                >
                  <ImageIcon size={14} className="text-fg-tertiary" />
                  <span className="flex-1 truncate">{f.name}</span>
                  <span className="mono text-xs text-fg-tertiary">
                    {(f.size / 1024 / 1024).toFixed(1)}M
                  </span>
                  {!isBusy && (
                    <button
                      type="button"
                      onClick={() => removeFile(i)}
                      className="text-fg-tertiary hover:text-accent-aurora"
                    >
                      <X size={14} />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-sm text-red-300">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {isBusy && (
          <div className="rounded-md bg-bg-raised px-3 py-2.5 text-sm text-fg-secondary mono">
            {stageLabel[stage]}
          </div>
        )}

        <button
          type="submit"
          disabled={isBusy}
          className="rounded-md bg-accent-aurora px-4 py-2.5 text-sm font-medium text-bg-base hover:bg-accent-aurora/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isBusy ? stageLabel[stage] : `创建并上传 ${files.length} 张`}
        </button>
      </form>
    </main>
  );
}
