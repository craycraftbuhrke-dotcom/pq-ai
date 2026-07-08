"use client";

import {
  CheckCircle2,
  Download,
  FileCode,
  FileSpreadsheet,
  LoaderCircle,
  ShieldCheck,
  Upload,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";

import { useAuth } from "@/lib/auth-context";

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

export default function ImportWizardPage() {
  const { actor } = useAuth();
  const fileInput = useRef<HTMLInputElement>(null);
  const [points, setPoints] = useState<ImportResource[]>([]);
  const [runs, setRuns] = useState<ImportResource[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewRow[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [qualityType, setQualityType] = useState<QualityType>("ORANGE_PEEL");

  useEffect(() => {
    void (async () => {
      try {
        const [nextPoints, nextRuns] = await Promise.all([
          apiRequest<ImportResource[]>("/api/master-data/measurement-points?limit=5000"),
          apiRequest<ImportResource[]>("/api/process/production-runs?limit=5000"),
        ]);
        setPoints(nextPoints || []);
        setRuns(nextRuns || []);
      } catch {
        setError("加载参照数据失败");
      }
    })();
  }, []);

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
        const body = (await resp.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail ?? "导入失败");
      }
      const data = (await resp.json()) as ImportResult;
      setResult(data);
      setNotice(`导入完成：创建 ${data.created}，更新 ${data.updated}，跳过 ${data.skipped}，失败 ${data.failed}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setImporting(false);
    }
  }, [file]);

  function parseFile(file: File) {
    setFile(file);
    setResult(null);
    setError("");
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const lines = text.split(/\r?\n/).filter(Boolean);
      if (lines.length < 2) {
        setError("CSV 文件为空或只有表头");
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
      setPreview(rows);
      setNotice(`预览：共 ${lines.length - 1} 行数据，显示前 ${rows.length} 行`);
    };
    reader.readAsText(file);
  }

  function downloadSample() {
    window.location.href = `/api/bulk/quality.measurements/template?format=csv&quality_type=${encodeURIComponent(qualityType)}`;
  }

  const pointMap = useMemo(() => new Map(points.map((p) => [p.code, p])), [points]);
  const runMap = useMemo(() => new Map(runs.map((r) => [r.run_no || r.code, r])), [runs]);

  if (!actor.isAuthenticated) {
    return <div className="page-stack"><div className="master-empty"><ShieldCheck /> 请先登录。</div></div>;
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">PHASE 4 · DATA IMPORT</span>
          <h1>数据导入向导</h1>
          <p>通过 CSV 文件批量导入质量测量数据，支持预览、校验与错误反馈。</p>
        </div>
      </header>
      {error ? <button className="message-banner message-error" onClick={() => setError("")}>{error}<X /></button> : null}
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}

      <div className="import-layout">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">FILE UPLOAD</span>
              <h2>选择 CSV 文件</h2>
            </div>
            <div className="page-actions">
              <label className="form-field">
                <span>模板质量类型</span>
                <select value={qualityType} onChange={(event) => setQualityType(event.target.value as QualityType)}>
                  {QUALITY_TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <button className="button button-secondary" onClick={downloadSample}>
                <Download /> 下载模板
              </button>
            </div>
          </div>
          <div className="import-upload-area">
            <input
              ref={fileInput}
              type="file"
              accept=".csv,.txt"
              hidden
              onChange={(event: ChangeEvent<HTMLInputElement>) => {
                const f = event.target.files?.[0];
                if (f) parseFile(f);
              }}
            />
            <button className="import-drop-zone" onClick={() => fileInput.current?.click()}>
              <FileSpreadsheet />
              {file ? (
                <>
                  <strong>{file.name}</strong>
                  <span>{(file.size / 1024).toFixed(1)} KB · 点击更换</span>
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
            <p className="panel-note">
              当前模板会按所选质量类型自动带出测量编组、编组内点位和对应质量指标列。
              用户只需要填写生产事件编号、测量时间和各项质量数值，无需再填写 `metrics` JSON。
            </p>
          </div>
          <div className="import-field-guide">
            <h4>必填列说明</h4>
            <table className="master-table compact-table">
              <thead><tr><th>列名</th><th>说明</th><th>填写要求</th></tr></thead>
              <tbody>
                <tr><td className="mono">data_no</td><td>测量编号（唯一）</td><td>填写本次质量数据的业务编号</td></tr>
                <tr><td className="mono">production_run_no</td><td>生产事件编号</td><td>填写系统中已有的生产事件编号</td></tr>
                <tr><td className="mono">measurement_group_code</td><td>测量编组代码</td><td>模板已自动带出，通常无需改动</td></tr>
                <tr><td className="mono">measurement_point_code</td><td>点位编号</td><td>模板已自动带出或填写系统中已有点位编号</td></tr>
                <tr><td className="mono">quality_type</td><td>质量类型</td><td>模板已按当前下载类型预填</td></tr>
                <tr><td className="mono">measured_at</td><td>测量时间（ISO格式）</td><td>填写实际测量时间</td></tr>
                <tr><td className="mono">metric__*</td><td>质量指标列</td><td>直接填写实际质量数值，后端自动转换</td></tr>
              </tbody>
            </table>
            <p className="panel-note">
              模板中的说明列如 `measurement_group_name`、`measurement_point_name`、`part_name` 用于辅助识别，可保留原值。
            </p>
          </div>
        </section>

        {preview.length > 0 ? (
          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">DATA PREVIEW</span>
                <h2>数据预览 ({preview.length} / {file ? "..." : 0} 行)</h2>
              </div>
              <button className="button button-primary" onClick={upload} disabled={importing || !file}>
                {importing ? <LoaderCircle className="spin" /> : <Upload />}
                {importing ? "导入中..." : "确认导入"}
              </button>
            </div>
            <div className="import-preview-table">
              <table className="master-table compact-table">
                <thead>
                  <tr>
                    {columns.map((col) => (
                      <th key={col} className={CORE_COLUMNS.includes(col) || col.startsWith("metric__") ? "" : "col-extra"}>
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.map((row, index) => (
                    <tr key={index}>
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
                  ))}
                </tbody>
              </table>
            </div>
            {result ? (
              <div className="import-result">
                <div className="result-grid">
                  <article className="result-item success"><strong>{result.created}</strong><span>新建</span></article>
                  <article className="result-item"><strong>{result.updated}</strong><span>更新</span></article>
                  <article className="result-item muted"><strong>{result.skipped}</strong><span>跳过</span></article>
                  <article className={`result-item ${result.failed ? "error" : ""}`}><strong>{result.failed}</strong><span>失败</span></article>
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
                ) : null}
              </div>
            ) : null}
          </section>
        ) : (
          <section className="panel">
            <div className="master-empty">
              <FileCode /> 请选择 CSV 文件以预览数据
            </div>
          </section>
        )}
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
