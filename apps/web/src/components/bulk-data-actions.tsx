"use client";

import { Download, FileSpreadsheet, LoaderCircle, Upload } from "lucide-react";
import { useRef, useState } from "react";

type BulkImportResult = {
  resource_label?: string;
  total_rows?: number;
  created?: number;
  updated?: number;
  skipped?: number;
  failed?: number;
  errors?: Array<{ row: number; message: string }>;
};

type BulkDataActionsProps = {
  resourceKey: string;
  resourceLabel: string;
  disabled?: boolean;
  onResult?: (message: string, type: "success" | "error") => void;
  onImported?: () => void | Promise<void>;
  importQuery?: Record<string, string | undefined>;
  downloadQuery?: Record<string, string | undefined>;
  defaultValues?: Record<string, string | number | boolean | undefined>;
  className?: string;
};

async function readApiError(response: Response): Promise<string> {
  const payload = (await response.json().catch(() => ({}))) as { error?: string };
  return payload.error ?? `请求失败（${response.status}）`;
}

function downloadUrl(resourceKey: string, action: "template" | "export", format: "xlsx" | "csv") {
  return `/api/bulk/${encodeURIComponent(resourceKey)}/${action}?format=${format}`;
}

function withQuery(path: string, query?: Record<string, string | undefined>): string {
  if (!query) return path;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value) params.set(key, value);
  }
  const text = params.toString();
  return text ? `${path}${path.includes("?") ? "&" : "?"}${text}` : path;
}

export function BulkDataActions({
  resourceKey,
  resourceLabel,
  disabled = false,
  onImported,
  onResult,
  importQuery,
  downloadQuery,
  defaultValues,
  className,
}: BulkDataActionsProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [format, setFormat] = useState<"xlsx" | "csv">("xlsx");
  const [uploading, setUploading] = useState(false);
  const defaultQuery = defaultValues && Object.values(defaultValues).some((value) => value !== undefined)
    ? { default_values: JSON.stringify(defaultValues) }
    : undefined;
  const effectiveImportQuery = { ...defaultQuery, ...importQuery };
  const effectiveDownloadQuery = { ...defaultQuery, ...downloadQuery };

  function notify(message: string, type: "success" | "error" = "success") {
    onResult?.(message, type);
  }

  function download(action: "template" | "export") {
    window.location.href = withQuery(downloadUrl(resourceKey, action, format), effectiveDownloadQuery);
    notify(`${resourceLabel}${action === "template" ? "模板" : "数据"}下载已开始`);
  }

  async function importFile(file: File) {
    setUploading(true);
    try {
      const response = await fetch(
        withQuery(
          `/api/bulk/${encodeURIComponent(resourceKey)}/import?mode=upsert&filename=${encodeURIComponent(file.name)}`,
          effectiveImportQuery,
        ),
        {
          method: "POST",
          headers: { "Content-Type": file.type || "application/octet-stream" },
          body: file,
        },
      );
      if (!response.ok) throw new Error(await readApiError(response));
      const result = (await response.json()) as BulkImportResult;
      const firstError = result.errors?.[0];
      const summary = `已处理 ${result.total_rows ?? 0} 行，新增 ${result.created ?? 0}，更新 ${result.updated ?? 0}，跳过 ${result.skipped ?? 0}，失败 ${result.failed ?? 0}`;
      if ((result.total_rows ?? 0) === 0) {
        notify("导入文件没有可处理的数据行，请先在模板的「数据」页填写记录后再导入", "error");
        return;
      }
      notify(firstError ? `${summary}；首个错误：第 ${firstError.row} 行 ${firstError.message}` : summary, firstError ? "error" : "success");
      await onImported?.();
    } catch (error) {
      notify(error instanceof Error ? error.message : "批量导入失败", "error");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className={className ? `bulk-actions ${className}` : "bulk-actions"} aria-label={`${resourceLabel}批量导入导出`}>
      <select
        aria-label={`${resourceLabel}导入导出格式`}
        value={format}
        onChange={(event) => setFormat(event.target.value as "xlsx" | "csv")}
        disabled={disabled || uploading}
      >
        <option value="xlsx">Excel 表格</option>
        <option value="csv">CSV 文件</option>
      </select>
      <button className="button button-secondary" onClick={() => download("template")} disabled={disabled || uploading}>
        <FileSpreadsheet />
        下载中文模板
      </button>
      <button className="button button-secondary" onClick={() => download("export")} disabled={disabled || uploading}>
        <Download />
        导出当前数据
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.csv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) void importFile(file);
        }}
      />
      <button
        className="button button-primary"
        onClick={() => inputRef.current?.click()}
        disabled={disabled || uploading}
      >
        {uploading ? <LoaderCircle className="spin" /> : <Upload />}
        导入表格
      </button>
    </div>
  );
}
