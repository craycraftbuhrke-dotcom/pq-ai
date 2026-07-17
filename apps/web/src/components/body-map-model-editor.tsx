"use client";

import { Box, LoaderCircle, RefreshCw, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { ModalShell } from "@/components/modal-shell";
import type { BodyModelBounds, BodyModelEntry } from "@/lib/body-map-models";

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

export function BodyMapModelEditor({ open, modelCode, modelName, onClose, onChanged }: Props) {
  const [entry, setEntry] = useState<BodyModelEntry | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
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

  async function postAction(action: "upload" | "reset", file?: File) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const form = new FormData();
      form.set("modelCode", modelCode);
      form.set("action", action);
      if (action === "upload") {
        if (file) form.set("file", file);
        form.set("upAxis", upAxis);
        form.set("unitScale", unitScale);
        if (boundsInput.trim()) form.set("bounds", boundsInput.trim());
      }
      const response = await fetch("/api/body-map-models", { method: "POST", body: form });
      const payload = (await response.json().catch(() => ({}))) as {
        error?: string;
        convert_engine?: string | null;
        source_format?: string;
      };
      if (!response.ok) throw new Error(payload.error ?? `请求失败（${response.status}）`);
      if (action === "reset") {
        setMessage("已恢复内置/无模型");
      } else if (payload.source_format === "stp") {
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
    }
  }

  if (!open) return null;

  return (
    <ModalShell
      eyebrow="数模管理"
      title="3D 车身数模"
      description={`${modelCode}${modelName ? ` · ${modelName}` : ""} — 上传 GLB/GLTF，或上传 STP/STEP（服务端自动转 GLB）到 public/body-models/custom，并写入 view-models.json。`}
      onClose={onClose}
      className="body-map-model-editor-modal"
    >
      <div className="body-map-model-editor">
        <div className="body-map-model-editor-toolbar">
          <button type="button" className="button button-secondary" onClick={() => void load()} disabled={loading}>
            {loading ? <LoaderCircle className="spin" /> : <RefreshCw />}
            刷新
          </button>
          <small className="muted">GLB/GLTF ≤ 80MB；STP/STEP ≤ 250MB（转换可能需数分钟）</small>
        </div>
        {error ? <div className="form-error">{error}</div> : null}
        {message ? <div className="form-success">{message}</div> : null}

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
              if (file) void postAction("upload", file);
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
            onClick={() => void postAction("reset")}
          >
            <Box />
            恢复内置
          </button>
        </div>
      </div>
    </ModalShell>
  );
}
