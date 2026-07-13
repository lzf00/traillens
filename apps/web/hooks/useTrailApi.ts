"use client";

/**
 * useTrailApi — 集中 trail CRUD + photos 操作 + 统一 error/loading。
 *
 * 之前 trails/[id]/page.tsx 里 refetchPhotos/patchTrail/patchPhoto/
 * appendPhotos/deletePhoto 各自 apiFetch + await + setState + catch 逻辑
 * 重复 5+ 次;这里抽干净。
 */

import { useCallback, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { ThumbnailItem } from "@/components/canvas/ThumbnailTrack";

export type TrailMeta = {
  id: string;
  name: string;
  location_name: string;
  travelogue_md: string | null;
  next_trip_plan: Record<string, any> | null;
};

type Toast = { level: "info" | "error" | "success"; text: string };

export function useTrailApi(trailId: string) {
  const [trail, setTrail] = useState<TrailMeta>({
    id: trailId, name: "", location_name: "",
    travelogue_md: null, next_trip_plan: null,
  });
  const [photos, setPhotos] = useState<ThumbnailItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);

  const mapPhoto = (p: any): ThumbnailItem => ({
    photo_id: p.photo_id,
    uri: p.uri,
    thumb_uri: p.thumb_uri ?? null,
    verdict: p.verdict,
    overall: p.aesthetic?.overall,
    aesthetic: p.aesthetic ?? null,
    critique: p.critique ?? null,
  });

  const refetchPhotos = useCallback(async () => {
    try {
      const r = await apiFetch(`/v1/trails/${trailId}/photos`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const arr: any[] = await r.json();
      setPhotos(arr.map(mapPhoto));
    } catch (e: any) {
      setToast({ level: "error", text: `拉照片失败:${e.message}` });
    }
  }, [trailId]);

  const refetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [tr, ph] = await Promise.all([
        apiFetch(`/v1/trails/${trailId}`),
        apiFetch(`/v1/trails/${trailId}/photos`),
      ]);
      if (tr.ok) {
        const t = await tr.json();
        setTrail({
          id: t.id, name: t.name, location_name: t.location_name ?? "",
          travelogue_md: t.travelogue_md ?? null,
          next_trip_plan: t.next_trip_plan ?? null,
        });
      }
      if (ph.ok) {
        setPhotos((await ph.json()).map(mapPhoto));
      }
    } catch (e: any) {
      setToast({ level: "error", text: `加载失败:${e.message}` });
    } finally {
      setLoading(false);
    }
  }, [trailId]);

  const patchTrail = useCallback(async (patch: Record<string, any>) => {
    try {
      const r = await apiFetch(`/v1/trails/${trailId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const t = await r.json();
      setTrail({
        id: t.id, name: t.name, location_name: t.location_name ?? "",
        travelogue_md: t.travelogue_md ?? null,
        next_trip_plan: t.next_trip_plan ?? null,
      });
      setToast({ level: "success", text: "已保存" });
    } catch (e: any) {
      setToast({ level: "error", text: `保存失败:${e.message}` });
    }
  }, [trailId]);

  const patchPhoto = useCallback(async (photoId: string, patch: Record<string, any>) => {
    try {
      const r = await apiFetch(`/v1/trails/${trailId}/photos/${photoId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      await refetchPhotos();
    } catch (e: any) {
      setToast({ level: "error", text: `改照片失败:${e.message}` });
    }
  }, [trailId, refetchPhotos]);

  const deletePhoto = useCallback(async (photoId: string) => {
    try {
      const r = await apiFetch(`/v1/trails/${trailId}/photos/${photoId}`, { method: "DELETE" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setPhotos((prev) => prev.filter((p) => p.photo_id !== photoId));
    } catch (e: any) {
      setToast({ level: "error", text: `删照片失败:${e.message}` });
    }
  }, [trailId]);

  const appendPhotos = useCallback(async (files: FileList) => {
    const fd = new FormData();
    for (const f of Array.from(files)) fd.append("files", f, f.name);
    try {
      const r = await apiFetch(`/v1/trails/${trailId}/photos:upload`, { method: "POST", body: fd });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      await refetchPhotos();
      setToast({ level: "success", text: `上传成功` });
    } catch (e: any) {
      setToast({ level: "error", text: `上传失败:${e.message}` });
    }
  }, [trailId, refetchPhotos]);

  const bulkVerdict = useCallback(async (ids: string[], v: "keep" | "review" | "reject") => {
    try {
      await Promise.all(ids.map((pid) =>
        apiFetch(`/v1/trails/${trailId}/photos/${pid}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ verdict: v }),
        })
      ));
      await refetchPhotos();
      setToast({ level: "success", text: `已标 ${ids.length} 张为 ${v}` });
    } catch (e: any) {
      setToast({ level: "error", text: `批量改失败:${e.message}` });
    }
  }, [trailId, refetchPhotos]);

  const bulkDelete = useCallback(async (ids: string[]) => {
    try {
      await Promise.all(ids.map((pid) =>
        apiFetch(`/v1/trails/${trailId}/photos/${pid}`, { method: "DELETE" })
      ));
      setPhotos((prev) => prev.filter((p) => !ids.includes(p.photo_id)));
      setToast({ level: "success", text: `已删 ${ids.length} 张` });
    } catch (e: any) {
      setToast({ level: "error", text: `批量删失败:${e.message}` });
    }
  }, [trailId]);

  return {
    trail, setTrail,
    photos, setPhotos,
    loading, toast, setToast,
    refetchPhotos, refetchAll,
    patchTrail, patchPhoto, deletePhoto,
    appendPhotos, bulkVerdict, bulkDelete,
  };
}
