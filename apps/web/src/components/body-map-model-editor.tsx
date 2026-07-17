"use client";

import { Box, LoaderCircle, RefreshCw, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { ModalShell } from "@/components/modal-shell";
import type { BodyModelEntry } from "@/lib/body-map-models";

/** Keep each request under common Xiaomi/K8s Ingress body limits (often 1MB). */
const CHUNK_SIZE = 512 * 1024;

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
  onProgress: (label: string) => void;
}): Promise<{
  source_format?: string;
  convert_engine?: string | null;
}> {
  const { modelCode, file, upAxis, unitScale, bounds, onProgress } = options;
  const totalChunks = Math.max(1, Math.ceil(file.size / CHUNK_SIZE));

  onProgress(`创建上传会话（共 ${totalChunks} 片）…`);
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

  for (let index = 0; index < chunks; index++) {
    const start = index * CHUNK_SIZE;
    const end = Math.min(file.size, start + CHUNK_SIZE);
    const blob = file.slice(start, end);
    onProgress(`上传分片 ${index + 1}/${chunks}（${Math.round((end / file.size) * 100)}%）…`);

    let attempt = 0;
    while (true) {
      attempt += 1;
      const chunkResp = await fetch(`/api/body-map-models/uploads/${uploadId}/chunks/${index}`, {
        method: "PUT",
        headers: { "Content-Type": "application/octet-stream" },
        body: blob,
      });
      if (chunkResp.ok) break;
      if (attempt >= 3) {
        throw new Error(await readError(chunkResp));
      }
      onProgress(`分片 ${index + 1} 失败，重试 ${attempt}/3…`);
    }
  }

  onProgress("分片已齐，服务端组装并转换中（可能较久）…");
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
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [progress, setProgress] = useState("");
  const [boundsInput, setBoundsInput] = useState("");
  const [upAxis, setUpAxis] = useState("Y");
  const [unitScale, setUnitScale] = useState("1");
  const fileRef = useRef<HTMLInputElement | null>(null);

  const load = useCallback(async () => {
    if (!modelCode) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/body-map-models?modelCode=${encodeURIComponent(modelCode)}`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error(await readError(response));
      const payload = (await response.json()) as { entry: BodyModelEntry };
      setEntry(payload.entry);
      if (payload.entry.bounds) {
        setBoundsInput(JSON.stringify(payload.entry.bounds, null, 0));
      }
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
    void load();
  }, [load, open]);

  async function resetModel() {
    setBusy(true);
    setError("");
    setMessage("");
    setProgress("");
    try {
      const form = new FormData();
      form.set("modelCode", modelCode);
      form.set("action", "reset");
      const response = await fetch("/api/body-map-models", { method: "POST", body: form });
      const payload = (await response.json().catch(() => ({}))) as { error?: string };
      if (!response.ok) throw new Error(payload.error ?? `请求失败（${response.status}）`);
      setMessage("已恢复内置/无模型");
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setBusy(false);
      setProgress("");
    }
  }

  async function uploadModel(file: File) {
    setBusy(true);
    setError("");
    setMessage("");
    setProgress("");
    try {
      const payload = await uploadFileChunked({
        modelCode,
        file,
        upAxis,
        unitScale,
        bounds: boundsInput.trim(),
        onProgress: setProgress,
      });
      if (payload.source_format === "stp") {
        setMessage(
          `STEP 已转换并保存为 GLB${payload.convert_engine ? `（${payload.convert_engine}）` : ""}；默认单位缩放 0.001（毫米→米）`,
        );
        if (unitScale === "1") setUnitScale("0.001");
      } else {
        setMessage("数模已上传");
      }
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setBusy(false);
      setProgress("");
    }
  }

  if (!open) return null;

  return (
    <ModalShell
      eyebrow="数模管理"
      title="3D 车身数模"
      description={`${modelCode}${modelName ? ` · ${modelName}` : ""} — 大文件自动分片上传（绕过网关 413），STP/STEP 由服务端转 GLB。`}
      onClose={onClose}
      className="body-map-model-editor-modal"
    >
      <div className="body-map-model-editor">
        <div className="body-map-model-editor-toolbar">
          <button type="button" className="button button-secondary" onClick={() => void load()} disabled={loading}>
            {loading ? <LoaderCircle className="spin" /> : <RefreshCw />}
            刷新
          </button>
          <small className="muted">
            支持 GLB/GLTF/STP/STEP；大文件自动 512KB 分片上传，STP 转换可能较久
          </small>
        </div>
        {error ? <div className="form-error">{error}</div> : null}
        {message ? <div className="form-success">{message}</div> : null}
        {progress ? <div className="form-success">{progress}</div> : null}

        <div className="body-map-model-info">
          <div className="body-map-model-info-row">
            <span>当前模型</span>
            <strong className="mono">{entry?.url ?? "未配置"}</strong>
          </div>
          <div className="body-map-model-info-row">
            <span>来源</span>
            <strong>{entry?.url ? "自定义" : "内置/无"}</strong>
          </div>
        </div>

        <div className="body-map-model-form">
          <label className="form-field">
            <span>Up Axis</span>
            <select value={upAxis} onChange={(e) => setUpAxis(e.target.value)}>
              <option value="Y">Y（默认）</option>
              <option value="Z">Z</option>
              <option value="X">X</option>
            </select>
          </label>
          <label className="form-field">
            <span>单位缩放</span>
            <input
              type="number"
              step="any"
              value={unitScale}
              onChange={(e) => setUnitScale(e.target.value)}
            />
          </label>
          <label className="form-field form-field-wide">
            <span>包围盒 bounds (JSON, 可选)</span>
            <input
              type="text"
              placeholder='{"min_x":-2,"max_x":2,"min_y":0,"max_y":1.6,"min_z":-1,"max_z":1}'
              value={boundsInput}
              onChange={(e) => setBoundsInput(e.target.value)}
            />
          </label>
        </div>

        <div className="body-map-model-actions">
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
              if (file) void uploadModel(file);
            }}
          />
          <button
            type="button"
            className="button button-primary"
            disabled={busy || !modelCode}
            onClick={() => fileRef.current?.click()}
          >
            {busy ? <LoaderCircle className="spin" /> : <Upload />}
            {busy ? "处理中…" : "上传 GLB / STP"}
          </button>
          <button
            type="button"
            className="button button-secondary"
            disabled={busy || !entry?.url}
            onClick={() => void resetModel()}
          >
            <Box />
            恢复内置
          </button>
        </div>
      </div>
    </ModalShell>
  );
}
