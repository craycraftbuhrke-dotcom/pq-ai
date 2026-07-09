"use client";

import {
  CheckCircle2,
  Download,
  FileCode,
  FileSpreadsheet,
  LoaderCircle,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";

import { useAuth } from "@/lib/auth-context";
import { useWorkspaceContext } from "@/lib/workspace-context";

type ImportResource = {
  id: string;
  code: string;
  name: string;
  run_no?: string;
};

type ImportResult = {
  total_rows: number;
  created: number;
  updated: number;
  skipped: number;
  failed: number;
  errors: Array<{ row?: number; message: string }>;
};

function getApiKey(): string {
  const match = document.cookie.match(/(?:^|;\s*)pq_api_key=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    cache: "no-store",
    headers: { ...init?.headers, "x-api-key": getApiKey() },
    ...init,
  });
  if (resp.status === 204) return undefined as T;
  const payload = (await resp.json().catch(() => ({}))) as T & { detail?: string };
  if (!resp.ok) throw new Error(payload.detail ?? `请求失败（${resp.status}）`);
  return payload;
}

const CORE_COLUMNS = [
  "data_no",
  "production_run_no",
  "body_no",
  "factory_code",
  "vehicle_model_code",
  "color_code",
  "measurement_group_code",
  "measurement_point_code",
  "quality_type",
  "measured_at",
  "measured_by",
  "data_type",
];

type PreviewRow = Record<string, string>;
type QualityType = "ORANGE_PEEL" | "COLOR_DIFFERENCE" | "THICKNESS";

const QUALITY_TYPE_OPTIONS: Array<{ value: QualityType; label: string; note: string }> = [
  { value: "ORANGE_PEEL", label: "橘皮", note: "下载 DOI、LW、SW 等橘皮指标列模板" },
  { value: "COLOR_DIFFERENCE", label: "色差", note: "下载 DET、DE45 等色差指标列模板" },
  { value: "THICKNESS", label: "膜厚", note: "下载中涂/色漆/清漆/总膜厚指标列模板" },
];

function canAutoCreateRun(row: PreviewRow): boolean {
  return Boolean(
    row.body_no?.trim() &&
      row.factory_code?.trim() &&
      row.vehicle_model_code?.trim() &&
      row.color_code?.trim(),
  );
}

function resolvedRunNo(row: PreviewRow): string {
  const explicit = row.production_run_no?.trim();
  if (explicit) return explicit;
  const body = row.body_no?.trim();
  return body ? `RUN-${body}` : "";
}

export default function ImportWizardPage() {
  const { actor } = useAuth();
  const { factoryId, modelId, colorId } = useWorkspaceContext();
  const fileInput = useRef<HTMLInputElement>(null);
  const [points, setPoints] = useState<ImportResource[]>([]);
  const [runs, setRuns] = useState<ImportResource[]>([]);
  const [factories, setFactories] = useState<ImportResource[]>([]);
  const [vehicleModels, setVehicleModels] = useState<ImportResource[]>([]);
  const [colors, setColors] = useState<ImportResource[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewRow[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [totalRows, setTotalRows] = useState(0);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [qualityType, setQualityType] = useState<QualityType>("ORANGE_PEEL");
  const [shiftPrefill, setShiftPrefill] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        const [nextPoints, nextRuns, nextFactories, nextModels, nextColors] = await Promise.all([
          apiRequest<ImportResource[]>("/api/master-data/measurement-points?limit=5000"),
          apiRequest<ImportResource[]>("/api/process/production-runs?limit=5000"),
          apiRequest<ImportResource[]>("/api/master-data/factories"),
          apiRequest<ImportResource[]>("/api/master-data/vehicle-models"),
          apiRequest<ImportResource[]>("/api/master-data/colors"),
        ]);
        setPoints(nextPoints || []);
        setRuns(nextRuns || []);
        setFactories(nextFactories || []);
        setVehicleModels(nextModels || []);
        setColors(nextColors || []);
      } catch {
        setError("加载参照数据失败");
      }
    })();
  }, []);

  const contextCodes = useMemo(() => {
    const factory = factories.find((item) => item.id === factoryId);
    const model = vehicleModels.find((item) => item.id === modelId);
    const color = colors.find((item) => item.id === colorId);
    return {
      factory_code: factory?.code ?? "",
      vehicle_model_code: model?.code ?? "",
      color_code: color?.code ?? "",
    };
  }, [colorId, colors, factories, factoryId, modelId, vehicleModels]);

  const contextSummary = useMemo(() => {
    const parts = [
      contextCodes.factory_code && `工厂 ${contextCodes.factory_code}`,
      contextCodes.vehicle_model_code && `车型 ${contextCodes.vehicle_model_code}`,
      contextCodes.color_code && `颜色 ${contextCodes.color_code}`,
      shiftPrefill && `班次 ${shiftPrefill}`,
    ].filter(Boolean);
    return parts.length ? parts.join(" · ") : "未设置（可在顶部作业范围选择，或下载后手工填写）";
  }, [contextCodes, shiftPrefill]);

  const upload = useCallback(async () => {
    if (!file) return;
    setImporting(true);
    setError("");
    setResult(null);
    try {
      const content = await file.text();
      const resp = await fetch(`/api/bulk/quality.measurements/import?filename=${encodeURIComponent(file.name)}&mode=upsert`, {
        method: "POST",
        headers: {
          "x-api-key": getApiKey(),
          "Content-Type": "text/csv; charset=utf-8",
        },
        body: content,
      });
      if (!resp.ok) {
        const body = (await resp.json().catch(() => ({}))) as { detail?: string; error?: string };
        throw new Error(body.detail ?? body.error ?? "导入失败");
      }
      const data = (await resp.json()) as ImportResult;
      setResult(data);
      setNotice(`导入完成：创建 ${data.created}，更新 ${data.updated}，跳过 ${data.skipped}，失败 ${data.failed}`);
      const nextRuns = await apiRequest<ImportResource[]>("/api/process/production-runs?limit=5000");
      setRuns(nextRuns || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setImporting(false);
    }
  }, [file]);

  function parseFile(nextFile: File) {
    setFile(nextFile);
    setResult(null);
    setError("");
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const lines = text.split(/\r?\n/).filter(Boolean);
      if (lines.length < 2) {
        setError("CSV 文件为空或只有表头");
        setPreview([]);
        setColumns([]);
        setTotalRows(0);
        return;
      }
      const headers = parseCsvLine(lines[0]);
      setColumns(headers);
      const rows: PreviewRow[] = [];
      for (let i = 1; i < Math.min(lines.length, 51); i++) {
        const values = parseCsvLine(lines[i]);
        const row: PreviewRow = {};
        headers.forEach((header, index) => {
          row[header] = values[index] ?? "";
        });
        rows.push(row);
      }
      const dataRowCount = lines.length - 1;
      setTotalRows(dataRowCount);
      setPreview(rows);
      setNotice(`预览：共 ${dataRowCount} 行数据，显示前 ${rows.length} 行。生产事件不存在时，将按车号/工厂/车型/颜色自动创建。`);
    };
    reader.readAsText(nextFile);
  }

  function downloadSample() {
    const params = new URLSearchParams({
      format: "csv",
      quality_type: qualityType,
    });
    if (contextCodes.factory_code) params.set("factory_code", contextCodes.factory_code);
    if (contextCodes.color_code) params.set("color_code", contextCodes.color_code);
    if (contextCodes.vehicle_model_code) params.set("vehicle_model_code", contextCodes.vehicle_model_code);
    if (shiftPrefill.trim()) params.set("shift", shiftPrefill.trim());
    window.location.href = `/api/bulk/quality.measurements/template?${params.toString()}`;
  }

  const pointMap = useMemo(() => new Map(points.map((p) => [p.code, p])), [points]);
  const runMap = useMemo(() => new Map(runs.map((r) => [r.run_no || r.code, r])), [runs]);

  const previewStats = useMemo(() => {
    let existing = 0;
    let willCreate = 0;
    let incomplete = 0;
    for (const row of preview) {
      const runNo = resolvedRunNo(row);
      if (runNo && runMap.has(runNo)) {
        existing += 1;
      } else if (canAutoCreateRun(row)) {
        willCreate += 1;
      } else {
        incomplete += 1;
      }
    }
    return { existing, willCreate, incomplete };
  }, [preview, runMap]);

  if (!actor.isAuthenticated) {
    return (
      <div className="page-stack">
        <div className="master-empty">
          <ShieldCheck /> 请先登录。
        </div>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">批量导入测量</span>
          <h1>数据导入向导</h1>
          <p>
            一次上传即可带上车号、工厂、车型、颜色与质量指标。生产事件不存在时会自动创建，无需先去生产实绩中心建档。
          </p>
        </div>
        <div className="page-actions">
          <Link className="button button-secondary" href="/production">
            查看 / 补录工序实绩
          </Link>
        </div>
      </header>
      {error ? (
        <button className="message-banner message-error" onClick={() => setError("")}>
          {error}
          <X />
        </button>
      ) : null}
      {notice ? (
        <button className="message-banner message-success" onClick={() => setNotice("")}>
          {notice}
          <X />
        </button>
      ) : null}

      <div className="import-flow-steps">
        <article>
          <span>1</span>
          <div>
            <strong>选质量类型并下载模板</strong>
            <small>模板已带测量点与指标列，并预填作业范围中的工厂/车型/颜色</small>
          </div>
        </article>
        <article>
          <span>2</span>
          <div>
            <strong>填车号与质量数值</strong>
            <small>同一文件写完车身上下文和指标；生产事件编号可留空，将按车号自动生成</small>
          </div>
        </article>
        <article>
          <span>3</span>
          <div>
            <strong>预览后确认导入</strong>
            <small>预览会标出「已有事件」或「将自动创建」；工序实绩可事后在生产中心补录</small>
          </div>
        </article>
      </div>

      <div className="import-layout">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">第 1 步</span>
              <h2>准备模板与文件</h2>
            </div>
          </div>

          <div className="import-setup">
            <label className="form-field">
              <span>质量类型</span>
              <select value={qualityType} onChange={(event) => setQualityType(event.target.value as QualityType)}>
                {QUALITY_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <small className="field-hint">{QUALITY_TYPE_OPTIONS.find((item) => item.value === qualityType)?.note}</small>
            </label>
            <label className="form-field">
              <span>班次预填（可选）</span>
              <input value={shiftPrefill} onChange={(event) => setShiftPrefill(event.target.value)} placeholder="如 A / B" />
            </label>
            <div className="import-context-card">
              <Sparkles aria-hidden="true" />
              <div>
                <strong>模板将预填作业范围</strong>
                <span>{contextSummary}</span>
              </div>
            </div>
            <button className="button button-secondary" type="button" onClick={downloadSample}>
              <Download /> 下载 CSV 模板
            </button>
          </div>

          <div className="import-upload-area">
            <input
              ref={fileInput}
              type="file"
              accept=".csv,.txt"
              hidden
              onChange={(event: ChangeEvent<HTMLInputElement>) => {
                const next = event.target.files?.[0];
                if (next) parseFile(next);
              }}
            />
            <button className="import-drop-zone" type="button" onClick={() => fileInput.current?.click()}>
              <FileSpreadsheet />
              {file ? (
                <>
                  <strong>{file.name}</strong>
                  <span>
                    {(file.size / 1024).toFixed(1)} KB · 点击更换
                  </span>
                </>
              ) : (
                <>
                  <strong>点击选择 CSV 文件</strong>
                  <span>建议先下载模板，再按模板列填写后上传</span>
                </>
              )}
            </button>
          </div>

          <div className="import-field-guide">
            <h4>怎么填（一次带上生产上下文）</h4>
            <div className="import-guide-table-wrap">
              <table className="import-guide-table">
                <thead>
                  <tr>
                    <th>列</th>
                    <th>说明</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="mono">body_no</td>
                    <td>车号，建议必填；未填生产事件编号时用于自动生成</td>
                  </tr>
                  <tr>
                    <td className="mono">factory_code / vehicle_model_code / color_code</td>
                    <td>工厂、车型、颜色代码；生产事件不存在时必填，模板可按作业范围预填</td>
                  </tr>
                  <tr>
                    <td className="mono">production_run_no</td>
                    <td>可留空；留空时按 `RUN-车号` 自动创建。已存在则直接关联</td>
                  </tr>
                  <tr>
                    <td className="mono">shift / production_started_at</td>
                    <td>班次与生产开始时间可选；开始时间留空时回落到测量时间</td>
                  </tr>
                  <tr>
                    <td className="mono">measured_at + metric__*</td>
                    <td>测量时间与质量指标数值；模板已带出点位与指标列</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="panel-note">
              同一车身多点位时，请保持车号与工厂/车型/颜色一致。五段工序实绩、材料批次请导入成功后到
              <Link href="/production"> 生产实绩中心 </Link>
              补录。
            </p>
          </div>
        </section>

        <section className="panel">
          {preview.length > 0 ? (
            <>
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">第 2–3 步</span>
                  <h2>
                    数据预览（{preview.length} / {totalRows} 行）
                  </h2>
                  <small className="import-preview-meta">
                    已有事件 {previewStats.existing} · 将自动创建 {previewStats.willCreate}
                    {previewStats.incomplete ? ` · 上下文不完整 ${previewStats.incomplete}` : ""}
                  </small>
                </div>
                <button className="button button-primary" onClick={() => void upload()} disabled={importing || !file}>
                  {importing ? <LoaderCircle className="spin" /> : <Upload />}
                  {importing ? "导入中..." : "确认导入"}
                </button>
              </div>
              <div className="import-preview-table">
                <table className="import-preview-grid">
                  <thead>
                    <tr>
                      <th>生产事件</th>
                      {columns.map((col) => (
                        <th
                          key={col}
                          className={CORE_COLUMNS.includes(col) || col.startsWith("metric__") ? "" : "col-extra"}
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.map((row, index) => {
                      const runNo = resolvedRunNo(row);
                      const exists = Boolean(runNo && runMap.has(runNo));
                      const willCreate = !exists && canAutoCreateRun(row);
                      return (
                        <tr key={index}>
                          <td>
                            {exists ? (
                              <span className="run-badge run-badge-existing">
                                <CheckCircle2 /> 已有
                              </span>
                            ) : willCreate ? (
                              <span className="run-badge run-badge-create">
                                <Sparkles /> 将自动创建
                              </span>
                            ) : (
                              <span className="run-badge run-badge-warn">缺上下文</span>
                            )}
                          </td>
                          {columns.map((col) => {
                            const value = row[col] ?? "";
                            const hasRef =
                              (col === "measurement_point_code" && pointMap.has(value)) ||
                              (col === "production_run_no" && runMap.has(value));
                            return (
                              <td key={col} className={hasRef ? "cell-verified" : ""}>
                                {value.length > 30 ? `${value.slice(0, 30)}...` : value || "—"}
                                {hasRef ? <CheckCircle2 className="cell-check" /> : null}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {result ? (
                <div className="import-result">
                  <div className="result-grid">
                    <article className="result-item success">
                      <strong>{result.created}</strong>
                      <span>新建</span>
                    </article>
                    <article className="result-item">
                      <strong>{result.updated}</strong>
                      <span>更新</span>
                    </article>
                    <article className="result-item muted">
                      <strong>{result.skipped}</strong>
                      <span>跳过</span>
                    </article>
                    <article className={`result-item ${result.failed ? "error" : ""}`}>
                      <strong>{result.failed}</strong>
                      <span>失败</span>
                    </article>
                  </div>
                  {result.errors.length > 0 ? (
                    <div className="import-errors">
                      <h4>错误详情</h4>
                      {result.errors.slice(0, 10).map((err, i) => (
                        <p key={i} className="error-line">
                          {err.row ? `第 ${err.row} 行 · ` : ""}
                          {err.message}
                        </p>
                      ))}
                      {result.errors.length > 10 ? <p>...共 {result.errors.length} 条错误</p> : null}
                    </div>
                  ) : (
                    <p className="panel-note">
                      导入成功。如需补录五段工序实绩或材料批次，请前往
                      <Link href="/production"> 生产实绩中心</Link>。
                    </p>
                  )}
                </div>
              ) : null}
            </>
          ) : (
            <div className="import-empty-panel">
              <FileCode />
              <strong>上传 CSV 后在此预览</strong>
              <span>预览会标出哪些行将关联已有生产事件，哪些行会自动创建新事件。</span>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function parseCsvLine(line: string): string[] {
  const result: string[] = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      result.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  result.push(current.trim());
  return result;
}
