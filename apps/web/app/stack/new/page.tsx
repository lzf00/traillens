"use client";

/**
 * /stack/new — Direction B PoC 前端。
 *
 * 用户拖入 N 张星空照片(同机位长曝) → 后端 phaseCorrelate align + median →
 * 返回 1 张合成 jpg blob → 前端展示 + 下载。
 *
 * stateless,不入库。要持久化等 B Phase 2 接 trails 表。
 */

import { useState } from "react";
import { Upload, Image as ImageIcon, X, AlertCircle, Download, Filter, Check, XCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";

export const dynamic = "force-dynamic";

type TriageFrame = {
  filename: string;
  verdict: "keep" | "blur" | "cloud" | "underexposed" | "reject";
  reason: string;
  blur_score?: number;
  exposure_over_pct?: number;
  exposure_under_pct?: number;
};

export default function StackNewPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [frameCount, setFrameCount] = useState<number | null>(null);
  const [triage, setTriage] = useState<TriageFrame[] | null>(null);

  function addFiles(fl: FileList | null) {
    if (!fl) return;
    const incoming = Array.from(fl).filter((f) => f.type.startsWith("image/"));
    setFiles((prev) => [...prev, ...incoming]);
  }

  async function runTriage() {
    if (files.length < 1) return;
    setBusy(true);
    setError(null);
    setTriage(null);

    const tres = await apiFetch("/v1/trails", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: `Triage ${new Date().toISOString().slice(0, 16)}`, location_name: null, gpx_uri: null }),
    });
    if (!tres.ok) {
      setError("先登录");
      setBusy(false);
      return;
    }
    const trail = await tres.json();

    const form = new FormData();
    for (const f of files) form.append("files", f, f.name);
    const res = await apiFetch(`/v1/trails/${trail.id}/stack:triage`, { method: "POST", body: form });
    if (!res.ok) {
      setError(`triage 失败 HTTP ${res.status}`);
      apiFetch(`/v1/trails/${trail.id}`, { method: "DELETE" }).catch(() => {});
      setBusy(false);
      return;
    }
    const data = await res.json();
    setTriage(data.frames);
    apiFetch(`/v1/trails/${trail.id}`, { method: "DELETE" }).catch(() => {});
    setBusy(false);
  }

  function useKeeps() {
    if (!triage) return;
    const keepNames = new Set(triage.filter((t) => t.verdict === "keep").map((t) => t.filename));
    setFiles((prev) => prev.filter((f) => keepNames.has(f.name)));
    setTriage(null);
  }

  async function submit() {
    if (files.length < 2) {
      setError("至少 2 张才能堆栈");
      return;
    }
    if (files.length > 200) {
      setError("最多 200 张(单次上限)");
      return;
    }
    setBusy(true);
    setError(null);
    setResultUrl(null);

    // 需要一个 trail_id (端点签名要)。这里临时建一个 stateless trail
    const tres = await apiFetch("/v1/trails", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: `Stack ${new Date().toISOString().slice(0, 16)}`, location_name: null, gpx_uri: null }),
    });
    if (!tres.ok) {
      setError("创建临时 trail 失败,先登录?");
      setBusy(false);
      return;
    }
    const trail = await tres.json();

    const form = new FormData();
    for (const f of files) form.append("files", f, f.name);

    const res = await apiFetch(`/v1/trails/${trail.id}/stack:preview`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      setError(`堆栈失败 HTTP ${res.status}`);
      // 顺手删临时 trail
      apiFetch(`/v1/trails/${trail.id}`, { method: "DELETE" }).catch(() => {});
      setBusy(false);
      return;
    }
    setFrameCount(Number(res.headers.get("X-Stack-Frames") || files.length));
    const blob = await res.blob();
    setResultUrl(URL.createObjectURL(blob));

    // 删临时 trail,这是 stateless preview
    apiFetch(`/v1/trails/${trail.id}`, { method: "DELETE" }).catch(() => {});
    setBusy(false);
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-8">
        <p className="mono mb-2 text-fg-tertiary">DIRECTION B · POC</p>
        <h1 className="font-display text-3xl text-fg-primary mb-2">星空堆栈</h1>
        <p className="text-sm text-fg-secondary">
          同机位长曝 2-200 张丢进去 → OpenCV phaseCorrelate 对齐 + median 合成 → 出 1 张降噪后的合片。
          算法见 <code className="mono text-xs">services/stacker.py</code>;真生产版会接 SIFT 旋转对齐 + RAW 解码。
        </p>
      </header>

      <div className="flex flex-col gap-5">
        <label
          className={`flex flex-col items-center justify-center gap-2 rounded-md border border-dashed border-divider px-6 py-10 cursor-pointer hover:border-accent-aurora transition-colors ${
            busy ? "opacity-50 pointer-events-none" : ""
          }`}
        >
          <Upload size={20} className="text-fg-tertiary" />
          <span className="text-sm text-fg-secondary">点击或拖入 2-200 张同机位长曝</span>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => addFiles(e.target.files)}
            className="hidden"
            disabled={busy}
          />
        </label>

        {files.length > 0 && (
          <div className="text-sm text-fg-secondary">
            已选 <span className="text-fg-primary mono">{files.length}</span> 张 ·
            合计 {(files.reduce((s, f) => s + f.size, 0) / 1024 / 1024).toFixed(1)}MB
            <button
              onClick={() => setFiles([])}
              className="ml-2 text-fg-tertiary hover:text-accent-aurora text-xs"
            >
              清空
            </button>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={runTriage}
            disabled={busy || files.length < 1}
            className="flex-1 rounded-md border border-divider px-4 py-2.5 text-sm text-fg-primary hover:border-accent-glacier hover:text-accent-glacier disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
          >
            <Filter size={14} />
            {busy ? "分档中…" : `先分档 ${files.length} 张(过滤 blur/云)`}
          </button>
          <button
            onClick={submit}
            disabled={busy || files.length < 2}
            className="flex-1 rounded-md bg-accent-aurora px-4 py-2.5 text-sm font-medium text-bg-base hover:bg-accent-aurora/90 disabled:opacity-50 transition-colors"
          >
            {busy ? `堆栈中…(${files.length} 张)` : `堆栈 ${files.length} 张`}
          </button>
        </div>

        {triage && (
          <div className="rounded-md border border-divider bg-bg-raised p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="mono text-fg-secondary">
                分档结果:{triage.filter((t) => t.verdict === "keep").length} keep /{" "}
                {triage.length - triage.filter((t) => t.verdict === "keep").length} 剔
              </h3>
              <button
                onClick={useKeeps}
                className="text-xs text-accent-aurora hover:underline"
              >
                只留 keep 那些 →
              </button>
            </div>
            <ul className="flex flex-col gap-1 max-h-72 overflow-auto">
              {triage.map((t, i) => {
                const isKeep = t.verdict === "keep";
                return (
                  <li
                    key={i}
                    className={
                      "flex items-center gap-2 rounded px-2 py-1 text-xs " +
                      (isKeep ? "text-fg-secondary" : "text-fg-tertiary line-through")
                    }
                  >
                    {isKeep
                      ? <Check size={12} className="text-accent-aurora shrink-0" />
                      : <XCircle size={12} className="text-accent-danger shrink-0" />}
                    <span className="flex-1 truncate">{t.filename}</span>
                    <span className="mono">{t.verdict}</span>
                    {t.blur_score != null && <span className="mono">blur={t.blur_score}</span>}
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {resultUrl && (
          <div className="rounded-md border border-divider bg-bg-raised p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="mono text-fg-secondary">合成结果 · {frameCount} 帧 median</h3>
              <a
                href={resultUrl}
                download={`stack-${frameCount}frames.jpg`}
                className="flex items-center gap-1 text-xs text-accent-aurora hover:underline"
              >
                <Download size={12} /> 下载
              </a>
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={resultUrl} alt="stack" className="w-full rounded" />
          </div>
        )}
      </div>
    </main>
  );
}
