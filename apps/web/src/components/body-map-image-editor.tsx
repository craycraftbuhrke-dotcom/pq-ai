"use client";

import { Image as ImageIcon, LoaderCircle, RefreshCw, Upload, Wand2 } from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";

import { ModalShell } from "@/components/modal-shell";
import {
  BODY_MAP_VIEWS,
  type BodyMapView,
  withCacheBust,
} from "@/lib/body-map-images";

type ViewAsset = {
  body_view: BodyMapView;
  label: string;
  url: string;
  builtin_url: string;
  source: "builtin" | "custom";
};

type Props = {
  open: boolean;
  modelCode: string;
  modelName?: string;
  onClose: () => void;
  onChanged: () => void;
};

async function readError(response: Response): Promise<string> {
  const payload = (await response.json().catch(() => ({}))) as { error?: string };
  return payload.error ?? `请求失败（${response.status}）`;
}

export function BodyMapImageEditor({ open, modelCode, modelName, onClose, onChanged }: Props) {
  const [views, setViews] = useState<ViewAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyView, setBusyView] = useState<BodyMapView | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const fileRefs = useRef<Partial<Record<BodyMapView, HTMLInputElement | null>>>({});

  const load = useCallback(async () => {
    if (!modelCode) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/body-map-images?modelCode=${encodeURIComponent(modelCode)}`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error(await readError(response));
      const payload = (await response.json()) as { views: ViewAsset[] };
      setViews(
        payload.views.map((item) => ({
          ...item,
          url: withCacheBust(item.url, Date.now()),
        })),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载底图配置失败");
    } finally {
      setLoading(false);
    }
  }, [modelCode]);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load, open]);

  async function postAction(view: BodyMapView, action: "upload" | "reset" | "mirror-from-right", file?: File) {
    setBusyView(view);
    setError("");
    setMessage("");
    try {
      const form = new FormData();
      form.set("modelCode", modelCode);
      form.set("bodyView", view);
      form.set("action", action);
      if (file) form.set("file", file);
      const response = await fetch("/api/body-map-images", { method: "POST", body: form });
      if (!response.ok) throw new Error(await readError(response));
      const payload = (await response.json()) as { url?: string };
      setMessage(
        action === "reset"
          ? `${view} 已恢复内置底图`
          : action === "mirror-from-right"
            ? "已从右侧视图镜像生成左侧底图"
            : `${view} 底图已更新`,
      );
      await load();
      if (payload.url) onChanged();
      else onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setBusyView(null);
    }
  }

  if (!open) return null;

  return (
    <ModalShell
      eyebrow="底图管理"
      title="四视图白车身照片"
      description={`${modelName || modelCode}：为前、后、左、右四个方向上传清晰的白车身底图。`}
      onClose={onClose}
      className="body-map-image-editor-modal"
    >
      <div className="body-map-image-editor">
        <div className="body-map-image-editor-toolbar">
          <button type="button" className="button button-secondary" onClick={() => void load()} disabled={loading}>
            {loading ? <LoaderCircle className="spin" /> : <RefreshCw />}
            刷新预览
          </button>
          <small className="muted">支持 JPG / PNG / WebP，单张 ≤ 8MB。左侧视图也可一键镜像右侧照片。</small>
        </div>
        {error ? <div className="form-error">{error}</div> : null}
        {message ? <div className="form-success">{message}</div> : null}
        <div className="body-map-image-grid">
          {BODY_MAP_VIEWS.map((view) => {
            const item = views.find((entry) => entry.body_view === view);
            const busy = busyView === view;
            return (
              <article key={view} className="body-map-image-card">
                <div className="body-map-image-card-head">
                  <div>
                    <span className="eyebrow">{item?.label ?? view}</span>
                    <strong>当前底图</strong>
                  </div>
                  <span className={`status-badge ${item?.source === "custom" ? "" : "status-muted"}`}>
                    {item?.source === "custom" ? "已自定义" : "内置"}
                  </span>
                </div>
                <div className="body-map-image-preview">
                  {item?.url ? (
                    <Image
                      src={item.url}
                      alt={item.label}
                      width={640}
                      height={360}
                      unoptimized
                    />
                  ) : (
                    <div className="body-map-image-preview-empty">
                      <ImageIcon />
                      {loading ? "加载中…" : "暂无预览"}
                    </div>
                  )}
                </div>
                <div className="body-map-image-actions">
                  <input
                    ref={(node) => {
                      fileRefs.current[view] = node;
                    }}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    hidden
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      event.target.value = "";
                      if (file) void postAction(view, "upload", file);
                    }}
                  />
                  <button
                    type="button"
                    className="button button-secondary"
                    disabled={busy || !modelCode}
                    onClick={() => fileRefs.current[view]?.click()}
                  >
                    {busy ? <LoaderCircle className="spin" /> : <Upload />}
                    更换
                  </button>
                  {view === "LEFT" ? (
                    <button
                      type="button"
                      className="button button-secondary"
                      disabled={busy || !modelCode}
                      onClick={() => void postAction(view, "mirror-from-right")}
                    >
                      <Wand2 />
                      镜像右侧
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="button button-secondary"
                    disabled={busy || item?.source !== "custom"}
                    onClick={() => void postAction(view, "reset")}
                  >
                    恢复内置
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </ModalShell>
  );
}
