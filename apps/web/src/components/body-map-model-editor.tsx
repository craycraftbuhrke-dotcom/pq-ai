"use client";

import { FileBox, LoaderCircle, RefreshCw, RotateCcw, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { ModalBody, ModalNote, ModalShell } from "@/components/modal-shell";
import type { BodyModelBounds, BodyModelEntry } from "@/lib/body-map-models";

/** Keep each request under common Xiaomi/K8s Ingress body limits (often 1MB). */
const CHUNK_SIZE = 512 * 1024;
type BoundsForm = Record<keyof BodyModelBounds, string>;
const EMPTY_BOUNDS: BoundsForm = {
  min_x: "",
  max_x: "",
  min_y: "",
  max_y: "",
  min_z: "",
  max_z: "",
};

const BOUND_FIELDS: Array<[keyof BodyModelBounds, string]> = [
  ["min_x", "左右最小"],
  ["max_x", "左右最大"],
  ["min_y", "高度最小"],
  ["max_y", "高度最大"],
  ["min_z", "前后最小"],
  ["max_z", "前后最大"],
];

type StorageStatus = {
  using_shared_runtime_dir?: boolean;
  writable?: boolean;
  warning?: string | null;
};

function boundsForm(bounds?: BodyModelBounds | null): BoundsForm {
  if (!bounds) return { ...EMPTY_BOUNDS };
  return Object.fromEntries(
    Object.entries(bounds).map(([key, value]) => [key, String(value)]),
  ) as BoundsForm;
}

function serializeBounds(form: BoundsForm): string {
  const entries = Object.entries(form) as Array<[keyof BodyModelBounds, string]>;
  if (entries.every(([, value]) => value.trim() === "")) return "";
  if (entries.some(([, value]) => value.trim() === "")) {
    throw new Error("尺寸边界需要六项全部填写，或全部留空由系统自动识别");
  }
  const values = Object.fromEntries(entries.map(([key, value]) => [key, Number(value)]));
  if (Object.values(values).some((value) => !Number.isFinite(value))) {
    throw new Error("尺寸边界必须填写有效数值");
  }
  return JSON.stringify(values);
}

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

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

async function uploadFileChunked(options: {
  modelCode: string;
  file: File;
  upAxis: string;
  unitScale: string;
  bounds: string;
  onProgress: (label: string, percent: number) => void;
}): Promise<{
  source_format?: string;
  convert_engine?: string | null;
}> {
  const { modelCode, file, upAxis, unitScale, bounds, onProgress } = options;
  const totalChunks = Math.max(1, Math.ceil(file.size / CHUNK_SIZE));

  onProgress("正在准备上传…", 0);
  const initResp = await fetch("/api/body-map-models/uploads", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      modelCode,
      fileName: file.name,
      totalSize: file.size,
      chunkSize: CHUNK_SIZE,
    }),
  });
  const initPayload = (await initResp.json().catch(() => ({}))) as {
    error?: string;
    uploadId?: string;
    totalChunks?: number;
  };
  if (!initResp.ok || !initPayload.uploadId) {
    throw new Error(initPayload.error ?? `创建上传失败（${initResp.status}）`);
  }

  const uploadId = initPayload.uploadId;
  const chunks = initPayload.totalChunks ?? totalChunks;
  // 给共享盘（JuiceFS）一点时间让其它副本看到刚创建的会话
  await new Promise((resolve) => setTimeout(resolve, 300));

  for (let index = 0; index < chunks; index++) {
    const start = index * CHUNK_SIZE;
    const end = Math.min(file.size, start + CHUNK_SIZE);
    const blob = file.slice(start, end);
    const percent = Math.round((end / file.size) * 100);
    onProgress(`正在上传 ${percent}%`, percent);

    let attempt = 0;
    const maxAttempts = 6;
    while (true) {
      attempt += 1;
      const form = new FormData();
      form.set("chunk", blob, `chunk-${index}.part`);
      const chunkResp = await fetch(`/api/body-map-models/uploads/${uploadId}/chunks/${index}`, {
        method: "POST",
        body: form,
      });
      if (chunkResp.ok) break;
      if (attempt >= maxAttempts) {
        throw new Error(await readError(chunkResp));
      }
      // 404 多为跨 Pod 元数据延迟，退避重试；其它错误也短暂重试
      const delayMs = chunkResp.status === 404 ? 200 * attempt : 150 * attempt;
      onProgress(`上传中断，正在重试（${attempt}/${maxAttempts}）…`, percent);
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }

  onProgress("上传完成，正在校验与转换…", 100);
  const completeResp = await fetch(`/api/body-map-models/uploads/${uploadId}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ upAxis, unitScale, bounds }),
  });
  const completePayload = (await completeResp.json().catch(() => ({}))) as {
    error?: string;
    source_format?: string;
    convert_engine?: string | null;
  };
  if (!completeResp.ok) {
    throw new Error(completePayload.error ?? `完成上传失败（${completeResp.status}）`);
  }
  return completePayload;
}

export function BodyMapModelEditor({ open, modelCode, modelName, onClose, onChanged }: Props) {
  const [entry, setEntry] = useState<BodyModelEntry | null>(null);
  const [storage, setStorage] = useState<StorageStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [progress, setProgress] = useState("");
  const [progressPercent, setProgressPercent] = useState(0);
  const [bounds, setBounds] = useState<BoundsForm>({ ...EMPTY_BOUNDS });
  const [upAxis, setUpAxis] = useState("Y");
  const [unitScale, setUnitScale] = useState("1");
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const fileName = entry?.url?.split("/").at(-1) ?? "";
  const hasCustomModel = Boolean(entry?.url);

  const load = useCallback(async () => {
    if (!modelCode) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/body-map-models?modelCode=${encodeURIComponent(modelCode)}`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error(await readError(response));
      const payload = (await response.json()) as {
        entry: BodyModelEntry;
        storage?: StorageStatus;
      };
      setEntry(payload.entry);
      setStorage(payload.storage ?? null);
      setBounds(boundsForm(payload.entry.bounds));
      setUpAxis(payload.entry.up_axis ?? "Y");
      setUnitScale(String(payload.entry.unit_scale ?? "1"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载数模配置失败");
    } finally {
      setLoading(false);
    }
  }, [modelCode]);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load, open]);

  async function resetModel() {
    setBusy(true);
    setError("");
    setMessage("");
    setProgress("");
    setProgressPercent(0);
    try {
      const form = new FormData();
      form.set("modelCode", modelCode);
      form.set("action", "reset");
      const response = await fetch("/api/body-map-models", { method: "POST", body: form });
      const payload = (await response.json().catch(() => ({}))) as { error?: string };
      if (!response.ok) throw new Error(payload.error ?? `请求失败（${response.status}）`);
      setMessage("已恢复内置模型配置");
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setBusy(false);
      setProgress("");
      setProgressPercent(0);
    }
  }

  async function uploadModel(file: File) {
    setBusy(true);
    setError("");
    setMessage("");
    setProgress("");
    setProgressPercent(0);
    try {
      const payload = await uploadFileChunked({
        modelCode,
        file,
        upAxis,
        unitScale,
        bounds: serializeBounds(bounds),
        onProgress: (label, percent) => {
          setProgress(label);
          setProgressPercent(percent);
        },
      });
      if (payload.source_format === "stp") {
        setMessage(
          `STEP 已转换为 GLB${payload.convert_engine ? `（${payload.convert_engine}）` : ""}，建议尺寸换算使用 0.001（毫米→米）`,
        );
        if (unitScale === "1") setUnitScale("0.001");
      } else {
        setMessage(`已保存 ${file.name}（${formatBytes(file.size)}）`);
      }
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setBusy(false);
      setProgress("");
      setProgressPercent(0);
    }
  }

  function acceptFile(file: File | undefined) {
    if (!file || busy || !modelCode) return;
    void uploadModel(file);
  }

  if (!open) return null;

  return (
    <ModalShell
      eyebrow="质量管理 · 3D 车身"
      title="车身数模"
      description={`${modelName || modelCode} · 上传 GLB / STEP，大文件自动分片`}
      onClose={onClose}
      busy={busy}
      className="body-map-model-editor-modal"
      actions={
        <>
          <button
            type="button"
            className="button button-secondary"
            disabled={busy || !hasCustomModel}
            onClick={() => void resetModel()}
          >
            <RotateCcw />
            恢复内置
          </button>
          <button
            type="button"
            className="button button-primary"
            disabled={busy || !modelCode || Boolean(storage?.warning)}
            onClick={() => fileRef.current?.click()}
          >
            {busy ? <LoaderCircle className="spin" /> : <Upload />}
            {busy ? "处理中…" : "选择文件上传"}
          </button>
        </>
      }
    >
      <ModalBody className="body-map-model-editor">
        <div className="bmm-status-card">
          <div className="bmm-status-icon" aria-hidden="true">
            <FileBox />
          </div>
          <div className="bmm-status-copy">
            <div className="bmm-status-label">当前数模</div>
            <div className="bmm-status-title">{hasCustomModel ? fileName : "尚未配置自定义数模"}</div>
            <div className="bmm-status-meta">
              <span className={`bmm-chip ${hasCustomModel ? "bmm-chip-active" : ""}`}>
                {hasCustomModel ? "自定义" : "内置 / 空"}
              </span>
              <span className="bmm-chip">{modelCode}</span>
            </div>
          </div>
          <button
            type="button"
            className="button button-secondary bmm-refresh"
            onClick={() => void load()}
            disabled={loading || busy}
            aria-label="刷新"
          >
            {loading ? <LoaderCircle className="spin" /> : <RefreshCw />}
          </button>
        </div>

        {storage?.warning ? (
          <ModalNote className="bmm-storage-warning">{storage.warning}</ModalNote>
        ) : (
          <ModalNote>
            支持 <strong>GLB / GLTF / STP / STEP</strong>
            。STEP 转换可能需要几分钟；毫米单位的 STEP 建议尺寸换算填 <strong>0.001</strong>。
          </ModalNote>
        )}

        {error ? <div className="message-banner message-error bmm-banner">{error}</div> : null}
        {message ? <div className="message-banner message-success bmm-banner">{message}</div> : null}

        {busy && progress ? (
          <div className="bmm-progress" role="status" aria-live="polite">
            <div className="bmm-progress-head">
              <span>{progress}</span>
              <strong>{progressPercent}%</strong>
            </div>
            <div className="bmm-progress-track">
              <div className="bmm-progress-fill" style={{ width: `${progressPercent}%` }} />
            </div>
          </div>
        ) : null}

        <div className="bmm-section">
          <div className="bmm-section-title">
            <h3>姿态与比例</h3>
            <p>影响 3D 视图中车身朝向与尺寸</p>
          </div>
          <div className="bmm-form-grid">
            <label className="form-field">
              <span>向上方向</span>
              <select value={upAxis} onChange={(e) => setUpAxis(e.target.value)} disabled={busy}>
                <option value="Y">Y（默认）</option>
                <option value="Z">Z</option>
                <option value="X">X</option>
              </select>
            </label>
            <label className="form-field">
              <span>尺寸换算</span>
              <input
                type="number"
                step="any"
                value={unitScale}
                disabled={busy}
                onChange={(e) => setUnitScale(e.target.value)}
              />
            </label>
          </div>
        </div>

        <div className="bmm-section">
          <div className="bmm-section-title">
            <h3>尺寸边界</h3>
            <p>可选；六项全留空时由系统自动识别</p>
          </div>
          <div className="bmm-bounds-grid">
            {BOUND_FIELDS.map(([key, label]) => (
              <label key={key} className="form-field">
                <span>{label}</span>
                <input
                  type="number"
                  step="any"
                  value={bounds[key]}
                  disabled={busy}
                  onChange={(event) =>
                    setBounds((current) => ({ ...current, [key]: event.target.value }))
                  }
                />
              </label>
            ))}
          </div>
        </div>

        <div
          className={`bmm-dropzone${dragOver ? " is-dragover" : ""}${busy ? " is-busy" : ""}`}
          onDragEnter={(event) => {
            event.preventDefault();
            if (!busy) setDragOver(true);
          }}
          onDragOver={(event) => {
            event.preventDefault();
            if (!busy) setDragOver(true);
          }}
          onDragLeave={(event) => {
            event.preventDefault();
            setDragOver(false);
          }}
          onDrop={(event) => {
            event.preventDefault();
            setDragOver(false);
            acceptFile(event.dataTransfer.files?.[0]);
          }}
          onClick={() => {
            if (!busy && !storage?.warning) fileRef.current?.click();
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              if (!busy && !storage?.warning) fileRef.current?.click();
            }
          }}
          role="button"
          tabIndex={busy || storage?.warning ? -1 : 0}
          aria-disabled={busy || Boolean(storage?.warning)}
        >
          <Upload />
          <div>
            <strong>拖拽文件到此处，或点击选择</strong>
            <p>GLB / GLTF / STP / STEP · 大文件自动分片上传</p>
          </div>
        </div>

        <input
          ref={(node) => {
            fileRef.current = node;
          }}
          type="file"
          accept=".glb,.gltf,.stp,.step,model/gltf-binary,model/gltf+json,application/step,model/step"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            acceptFile(file);
          }}
        />
      </ModalBody>
    </ModalShell>
  );
}
