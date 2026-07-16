"use client";

import {
  CheckCircle2,
  Download,
  Eraser,
  FileCode,
  FileSpreadsheet,
  LoaderCircle,
  PencilLine,
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

type FieldIssue = { field?: string; message: string };
type RowIssueMap = Record<number, FieldIssue[]>;

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

const EDITABLE_HINT_COLUMNS = new Set([
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
  "shift",
  "production_started_at",
]);

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

function csvEscape(value: string): string {
  if (/[",\r\n]/.test(value)) return `"${value.replaceAll('"', '""')}"`;
  return value;
}

function serializePreviewCsv(columns: string[], rows: PreviewRow[]): string {
  const header = columns.map(csvEscape).join(",");
  const body = rows.map((row) => columns.map((col) => csvEscape(row[col] ?? "")).join(",")).join("\n");
  return `${header}\n${body}\n`;
}

function validatePreviewRow(row: PreviewRow, columns: string[]): FieldIssue[] {
  const issues: FieldIssue[] = [];
  const pointCode = row.measurement_point_code?.trim() ?? "";
  const measuredAt = row.measured_at?.trim() ?? "";
  const runNo = row.production_run_no?.trim() ?? "";
  const bodyNo = row.body_no?.trim() ?? "";

  if (!pointCode) issues.push({ field: "measurement_point_code", message: "缺少 measurement_point_code" });
  if (!measuredAt) issues.push({ field: "measured_at", message: "缺少 measured_at" });
  if (!runNo && !bodyNo) {
    issues.push({ field: "body_no", message: "请填写 production_run_no，或填写 body_no" });
  }
  if (!runNo && bodyNo && !canAutoCreateRun(row)) {
    if (!row.factory_code?.trim()) issues.push({ field: "factory_code", message: "自动建档需填写 factory_code" });
    if (!row.vehicle_model_code?.trim()) {
      issues.push({ field: "vehicle_model_code", message: "自动建档需填写 vehicle_model_code" });
    }
    if (!row.color_code?.trim()) issues.push({ field: "color_code", message: "自动建档需填写 color_code" });
  }

  const hasMetric = columns.some((col) => col.startsWith("metric__") && (row[col] ?? "").trim() !== "");
  if (!hasMetric) issues.push({ message: "至少填写 1 个质量指标列（metric__*）" });

  return issues;
}

function inferIssueField(message: string): string | undefined {
  const fields = [
    "production_run_no",
    "body_no",
    "factory_code",
    "vehicle_model_code",
    "color_code",
    "measurement_group_code",
    "measurement_point_code",
    "quality_type",
    "measured_at",
  ];
  return fields.find((field) => message.includes(field));
}

function issuesFromImportErrors(errors: ImportResult["errors"]): RowIssueMap {
  const map: RowIssueMap = {};
  for (const err of errors) {
    if (!err.row || err.row < 2) continue;
    const index = err.row - 2;
    const list = map[index] ?? [];
    list.push({ field: inferIssueField(err.message), message: err.message });
    map[index] = list;
  }
  return map;
}

type QualityImportPanelProps = {
  embedded?: boolean;
  onImported?: () => void;
};

export function QualityImportPanel({ embedded = false, onImported }: QualityImportPanelProps) {
  const { actor } = useAuth();
  const { factoryId, modelId, colorId } = useWorkspaceContext();
  const fileInput = useRef<HTMLInputElement>(null);
  const [points, setPoints] = useState<ImportResource[]>([]);
  const [runs, setRuns] = useState<ImportResource[]>([]);
  const [factories, setFactories] = useState<ImportResource[]>([]);
  const [vehicleModels, setVehicleModels] = useState<ImportResource[]>([]);
  const [colors, setColors] = useState<ImportResource[]>([]);
  const [fileName, setFileName] = useState("");
  const [preview, setPreview] = useState<PreviewRow[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [dirty, setDirty] = useState(false);
  const [editingCell, setEditingCell] = useState<{ row: number; col: string } | null>(null);
  const [rowIssues, setRowIssues] = useState<RowIssueMap>({});
  const [showProblemsOnly, setShowProblemsOnly] = useState(false);
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

  const clearPreview = useCallback((opts?: { openPicker?: boolean; keepNotice?: string }) => {
    setFileName("");
    setPreview([]);
    setColumns([]);
    setDirty(false);
    setEditingCell(null);
    setRowIssues({});
    setShowProblemsOnly(false);
    setResult(null);
    setError("");
    setNotice(opts?.keepNotice ?? "");
    if (fileInput.current) fileInput.current.value = "";
    if (opts?.openPicker) {
      window.setTimeout(() => fileInput.current?.click(), 0);
    }
  }, []);

  const revalidateLocal = useCallback(
    (rows: PreviewRow[], cols: string[]) => {
      const next: RowIssueMap = {};
      rows.forEach((row, index) => {
        const issues = validatePreviewRow(row, cols);
        if (issues.length) next[index] = issues;
      });
      setRowIssues(next);
      return next;
    },
    [],
  );

  const upload = useCallback(async () => {
    if (!preview.length || !columns.length) return;
    const localIssues = revalidateLocal(preview, columns);
    const localFailed = Object.keys(localIssues).length;
    if (localFailed > 0) {
      setShowProblemsOnly(true);
      setError(`预览中仍有 ${localFailed} 行未通过校验，请先在表格中改正后再确认导入。`);
      setResult(null);
      return;
    }

    setImporting(true);
    setError("");
    setResult(null);
    try {
      const content = serializePreviewCsv(columns, preview);
      const name = dirty
        ? fileName.replace(/(\.csv)?$/i, "") + "-edited.csv"
        : fileName || "quality-import.csv";
      const resp = await fetch(
        `/api/bulk/quality.measurements/import?filename=${encodeURIComponent(name)}&mode=upsert`,
        {
          method: "POST",
          headers: {
            "x-api-key": getApiKey(),
            "Content-Type": "text/csv; charset=utf-8",
          },
          body: content,
        },
      );
      if (!resp.ok) {
        const body = (await resp.json().catch(() => ({}))) as { detail?: string; error?: string };
        throw new Error(body.detail ?? body.error ?? "导入失败");
      }
      const data = (await resp.json()) as ImportResult;
      setResult(data);
      if (data.failed > 0) {
        const mapped = issuesFromImportErrors(data.errors);
        setRowIssues(mapped);
        setShowProblemsOnly(true);
        setError(`导入完成但有 ${data.failed} 行失败。可直接在预览表中改正后再次确认导入，或清除预览后重新上传。`);
        setNotice("");
      } else {
        setRowIssues({});
        setShowProblemsOnly(false);
        setNotice(`导入完成：创建 ${data.created}，更新 ${data.updated}，跳过 ${data.skipped}，失败 ${data.failed}`);
        setDirty(false);
      }
      const nextRuns = await apiRequest<ImportResource[]>("/api/process/production-runs?limit=5000");
      setRuns(nextRuns || []);
      if (data.failed === 0) onImported?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setImporting(false);
    }
  }, [columns, dirty, fileName, onImported, preview, revalidateLocal]);

  function parseFile(nextFile: File) {
    setFileName(nextFile.name);
    setResult(null);
    setError("");
    setDirty(false);
    setEditingCell(null);
    setShowProblemsOnly(false);
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
      if (lines.length < 2) {
        setError("CSV 文件为空或只有表头");
        setPreview([]);
        setColumns([]);
        setRowIssues({});
        return;
      }
      const headers = parseCsvLine(lines[0]);
      const rows: PreviewRow[] = [];
      for (let i = 1; i < lines.length; i++) {
        const values = parseCsvLine(lines[i]);
        const row: PreviewRow = {};
        headers.forEach((header, index) => {
          row[header] = values[index] ?? "";
        });
        rows.push(row);
      }
      setColumns(headers);
      setPreview(rows);
      const issues = revalidateLocal(rows, headers);
      const issueCount = Object.keys(issues).length;
      if (issueCount > 0) {
        setShowProblemsOnly(true);
        setNotice(`已加载 ${rows.length} 行。发现 ${issueCount} 行可在预览中直接改正；改正后点「确认导入」。`);
      } else {
        setNotice(`已加载 ${rows.length} 行。可直接确认导入；若有问题也可在表格中点单元格修改。`);
      }
    };
    reader.readAsText(nextFile);
  }

  function updateCell(rowIndex: number, col: string, value: string) {
    setPreview((current) => {
      const next = current.map((row, index) => (index === rowIndex ? { ...row, [col]: value } : row));
      const issues = validatePreviewRow(next[rowIndex], columns);
      setRowIssues((prev) => {
        const copy = { ...prev };
        if (issues.length) copy[rowIndex] = issues;
        else delete copy[rowIndex];
        return copy;
      });
      return next;
    });
    setDirty(true);
    setResult(null);
    setError("");
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
      if (runNo && runMap.has(runNo)) existing += 1;
      else if (canAutoCreateRun(row)) willCreate += 1;
      else incomplete += 1;
    }
    return { existing, willCreate, incomplete };
  }, [preview, runMap]);

  const problemCount = Object.keys(rowIssues).length;
  const visibleRows = useMemo(() => {
    if (!showProblemsOnly || problemCount === 0) {
      return preview.map((row, index) => ({ row, index }));
    }
    return preview
      .map((row, index) => ({ row, index }))
      .filter(({ index }) => Boolean(rowIssues[index]));
  }, [preview, problemCount, rowIssues, showProblemsOnly]);

  if (!actor.isAuthenticated) {
    return (
      <div className={embedded ? "quality-import-embedded" : "page-stack"}>
        <div className="master-empty">
          <ShieldCheck /> 请先登录。
        </div>
      </div>
    );
  }

  return (
    <div className={embedded ? "quality-import-embedded" : "page-stack"}>
      {embedded ? null : (
        <header className="page-header">
          <div className="page-actions">
            <Link className="button button-secondary" href="/quality?tab=measurements">
              查看已导入质量
            </Link>
            <Link className="button button-secondary" href="/process?tab=runs">
              补录工序实绩
            </Link>
          </div>
        </header>
      )}
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

      {embedded ? (
        <div className="quality-import-intro">
          <div>
            <strong>批量上传质量数据</strong>
            <span>同一份 CSV 填写车号、工厂、车型、颜色与指标；生产事件不存在时自动创建。单条补录请切到「查看与判定」。</span>
          </div>
          <Link className="button button-secondary" href="/process?tab=runs">
            补录工序实绩
          </Link>
        </div>
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
            <strong>预览、改正后确认导入</strong>
            <small>有错误时可直接改单元格再导入，或清除预览后重新上传</small>
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
              {fileName ? (
                <>
                  <strong>{fileName}</strong>
                  <span>
                    {preview.length} 行已载入{dirty ? " · 已在预览中修改" : ""} · 点击可更换文件
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
                    <td>车号，建议必填；未填生产事件编号时用于自动生成，并参与自动生成 data_no</td>
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
                    <td className="mono">data_no</td>
                    <td>模板无需填写；后端按 `QM-车号-测量点-质量类型` 自动生成（如 QM-BODY-0001-PT1-OP）</td>
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
              <Link href="/process?tab=runs"> 生产实绩中心 </Link>
              补录。
            </p>
          </div>
        </section>

        <section className="panel">
          {preview.length > 0 ? (
            <>
              <div className="panel-heading import-preview-heading">
                <div>
                  <span className="eyebrow">第 2–3 步</span>
                  <h2>
                    数据预览（{preview.length} 行）
                    {dirty ? <span className="import-dirty-tag">已编辑</span> : null}
                  </h2>
                  <small className="import-preview-meta">
                    已有事件 {previewStats.existing} · 将自动创建 {previewStats.willCreate}
                    {previewStats.incomplete ? ` · 上下文不完整 ${previewStats.incomplete}` : ""}
                    {problemCount ? ` · 待改正 ${problemCount}` : ""}
                  </small>
                </div>
                <div className="import-preview-actions">
                  {problemCount > 0 ? (
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => setShowProblemsOnly((value) => !value)}
                    >
                      <PencilLine />
                      {showProblemsOnly ? "显示全部行" : "仅看问题行"}
                    </button>
                  ) : null}
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => clearPreview({ openPicker: true, keepNotice: "已清除预览，请重新选择文件。" })}
                    disabled={importing}
                  >
                    <Eraser />
                    清除并重选
                  </button>
                  <button className="button button-primary" onClick={() => void upload()} disabled={importing}>
                    {importing ? <LoaderCircle className="spin" /> : <Upload />}
                    {importing ? "导入中..." : dirty || problemCount ? "改正后确认导入" : "确认导入"}
                  </button>
                </div>
              </div>

              {problemCount > 0 ? (
                <div className="import-fix-hint">
                  <PencilLine />
                  <div>
                    <strong>发现 {problemCount} 行需要改正</strong>
                    <span>点击单元格直接编辑；改完后点「改正后确认导入」。若想换一份文件，点「清除并重选」。</span>
                  </div>
                </div>
              ) : (
                <div className="import-fix-hint import-fix-hint-ok">
                  <CheckCircle2 />
                  <div>
                    <strong>预览校验通过</strong>
                    <span>仍可点击单元格微调；确认无误后导入。也可随时清除预览重新上传。</span>
                  </div>
                </div>
              )}

              <div className="import-preview-table">
                <table className="import-preview-grid">
                  <thead>
                    <tr>
                      <th>行</th>
                      <th>状态</th>
                      {columns.map((col) => (
                        <th
                          key={col}
                          className={CORE_COLUMNS.includes(col) || col.startsWith("metric__") ? "" : "col-extra"}
                        >
                          {col}
                        </th>
                      ))}
                      <th>问题</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleRows.map(({ row, index }) => {
                      const runNo = resolvedRunNo(row);
                      const exists = Boolean(runNo && runMap.has(runNo));
                      const willCreate = !exists && canAutoCreateRun(row);
                      const issues = rowIssues[index] ?? [];
                      const issueFields = new Set(issues.map((item) => item.field).filter(Boolean));
                      return (
                        <tr key={index} className={issues.length ? "import-row-error" : ""}>
                          <td className="mono">{index + 2}</td>
                          <td>
                            {issues.length ? (
                              <span className="run-badge run-badge-error">需改正</span>
                            ) : exists ? (
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
                            const isEditing = editingCell?.row === index && editingCell.col === col;
                            const isProblem = issueFields.has(col);
                            const canEdit = EDITABLE_HINT_COLUMNS.has(col) || col.startsWith("metric__");
                            return (
                              <td
                                key={col}
                                className={[
                                  hasRef ? "cell-verified" : "",
                                  isProblem ? "cell-error" : "",
                                  canEdit ? "cell-editable" : "",
                                ]
                                  .filter(Boolean)
                                  .join(" ")}
                                onClick={() => {
                                  if (canEdit) setEditingCell({ row: index, col });
                                }}
                              >
                                {isEditing ? (
                                  <input
                                    className="import-cell-input"
                                    autoFocus
                                    value={value}
                                    onChange={(event) => updateCell(index, col, event.target.value)}
                                    onBlur={() => setEditingCell(null)}
                                    onKeyDown={(event) => {
                                      if (event.key === "Enter" || event.key === "Escape") {
                                        setEditingCell(null);
                                      }
                                    }}
                                  />
                                ) : (
                                  <>
                                    {value.length > 36 ? `${value.slice(0, 36)}…` : value || "—"}
                                    {hasRef ? <CheckCircle2 className="cell-check" /> : null}
                                  </>
                                )}
                              </td>
                            );
                          })}
                          <td className="import-row-issue">
                            {issues.length ? issues.map((item) => item.message).join("；") : "—"}
                          </td>
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
                      <h4>服务端错误详情（可对照左侧行号在预览中改正）</h4>
                      {result.errors.slice(0, 12).map((err, i) => (
                        <p key={i} className="error-line">
                          {err.row ? `第 ${err.row} 行 · ` : ""}
                          {err.message}
                        </p>
                      ))}
                      {result.errors.length > 12 ? <p>...共 {result.errors.length} 条错误</p> : null}
                      <div className="import-error-actions">
                        <button
                          className="button button-secondary"
                          type="button"
                          onClick={() => clearPreview({ openPicker: true })}
                        >
                          <Eraser /> 清除预览并重新导入
                        </button>
                        <button className="button button-primary" type="button" onClick={() => void upload()} disabled={importing}>
                          <Upload /> 改正后再次导入
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="panel-note">
                      导入成功。如需补录五段工序实绩或材料批次，请前往
                      <Link href="/process?tab=runs"> 生产实绩中心</Link>。
                    </p>
                  )}
                </div>
              ) : null}
            </>
          ) : (
            <div className="import-empty-panel">
              <FileCode />
              <strong>上传 CSV 后在此预览</strong>
              <span>预览会标出哪些行将关联已有生产事件，哪些行会自动创建新事件；有错误时可直接改单元格。</span>
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
