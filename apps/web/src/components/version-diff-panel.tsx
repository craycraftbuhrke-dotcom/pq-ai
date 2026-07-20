"use client";

import { ArrowDown, ArrowRight, ArrowUp, GitCompareArrows, Minus } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { statusLabel } from "@/lib/display-labels";

type BrushParam = {
  id: string;
  brush_no: string;
  parameter_code: string;
  parameter_name: string;
  configured_value: number;
  unit: string;
  soft_min?: number | null;
  soft_max?: number | null;
};

type ProgramVersion = {
  id: string;
  version: string;
  status: string;
  source_type: string;
  spray_program_id: string;
};

type DiffResult = {
  same_count: number;
  changed_count: number;
  added_count: number;
  removed_count: number;
  rows: DiffRow[];
};

type DiffRow = {
  brush_no: string;
  parameter_code: string;
  parameter_name: string;
  source_value: number | null;
  target_value: number | null;
  unit: string;
  change_type: "same" | "changed" | "added" | "removed";
  change_percent?: number;
};

async function apiRequest<T>(path: string): Promise<T> {
  const resp = await fetch(path, {
    cache: "no-store",
  });
  if (!resp.ok) throw new Error(`请求失败 (${resp.status})`);
  return resp.json() as Promise<T>;
}

export function VersionDiffPanel({
  versions,
  programId: _programId,
}: {
  versions: ProgramVersion[];
  programId: string;
}) {
  void _programId;
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [sourceParams, setSourceParams] = useState<BrushParam[]>([]);
  const [targetParams, setTargetParams] = useState<BrushParam[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const effectiveSourceId = sourceId || versions[0]?.id || "";
  const effectiveTargetId = targetId || versions[1]?.id || "";

  const loadParams = useCallback(async (versionId: string, setter: (p: BrushParam[]) => void) => {
    setLoading(true);
    setError("");
    try {
      const brushes = await apiRequest<{ id: string; brush_no: string }[]>(
        `/api/process/program-versions/${versionId}/brushes`,
      );
      const allParams: BrushParam[] = [];
      for (const brush of (brushes || [])) {
        const params = await apiRequest<BrushParam[]>(
          `/api/process/brushes/${brush.id}/parameters`,
        );
        for (const param of params || []) {
          allParams.push({ ...param, brush_no: brush.brush_no });
        }
      }
      setter(allParams);
    } catch (err) {
      setter([]);
      setError(err instanceof Error ? err.message : "版本参数加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (effectiveSourceId) {
        void loadParams(effectiveSourceId, setSourceParams);
      } else {
        setSourceParams([]);
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [effectiveSourceId, loadParams]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (effectiveTargetId) {
        void loadParams(effectiveTargetId, setTargetParams);
      } else {
        setTargetParams([]);
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [effectiveTargetId, loadParams]);

  const diff = useMemo((): DiffResult => {
    const sourceMap = new Map<string, BrushParam>();
    const targetMap = new Map<string, BrushParam>();

    for (const param of sourceParams) {
      sourceMap.set(`${param.brush_no}:${param.parameter_code}`, param);
    }
    for (const param of targetParams) {
      targetMap.set(`${param.brush_no}:${param.parameter_code}`, param);
    }

    const rows: DiffRow[] = [];
    const allKeys = new Set([...sourceMap.keys(), ...targetMap.keys()]);

    for (const key of allKeys) {
      const source = sourceMap.get(key);
      const target = targetMap.get(key);
      const brushNo = source?.brush_no ?? target?.brush_no ?? "—";
      const paramCode = source?.parameter_code ?? target?.parameter_code ?? "";
      const paramName = source?.parameter_name ?? target?.parameter_name ?? "";
      const unit = source?.unit ?? target?.unit ?? "";

      if (source && target) {
        const same = source.configured_value === target.configured_value;
        rows.push({
          brush_no: brushNo,
          parameter_code: paramCode,
          parameter_name: paramName,
          source_value: source.configured_value,
          target_value: target.configured_value,
          unit,
          change_type: same ? "same" : "changed",
          change_percent: same ? 0 : ((target.configured_value - source.configured_value) / Math.abs(source.configured_value || 1)) * 100,
        });
      } else if (source && !target) {
        rows.push({
          brush_no: brushNo,
          parameter_code: paramCode,
          parameter_name: paramName,
          source_value: source.configured_value,
          target_value: null,
          unit,
          change_type: "removed",
        });
      } else {
        rows.push({
          brush_no: brushNo,
          parameter_code: paramCode,
          parameter_name: paramName,
          source_value: null,
          target_value: target!.configured_value,
          unit,
          change_type: "added",
        });
      }
    }

    return {
      same_count: rows.filter((r) => r.change_type === "same").length,
      changed_count: rows.filter((r) => r.change_type === "changed").length,
      added_count: rows.filter((r) => r.change_type === "added").length,
      removed_count: rows.filter((r) => r.change_type === "removed").length,
      rows: rows.sort((a, b) => {
        if (a.change_type !== b.change_type) {
          const order = { changed: 0, added: 1, removed: 2, same: 3 };
          return order[a.change_type] - order[b.change_type];
        }
        return a.brush_no.localeCompare(b.brush_no) || a.parameter_code.localeCompare(b.parameter_code);
      }),
    };
  }, [sourceParams, targetParams]);

  if (versions.length < 2) {
    return (
      <div className="program-empty">
        <GitCompareArrows /> 至少需要两个程序版本才能对比（当前 {versions.length} 个）
      </div>
    );
  }

  return (
    <div className="version-diff-panel">
      <div className="diff-controls">
        <label className="form-field">
          <span>基准版本</span>
          <select value={effectiveSourceId} onChange={(e) => setSourceId(e.target.value)}>
            {versions.map((v) => <option key={v.id} value={v.id}>{v.version}（{statusLabel(v.status)}）</option>)}
          </select>
        </label>
        <ArrowRight className="diff-arrow-icon" />
        <label className="form-field">
          <span>对比版本</span>
          <select value={effectiveTargetId} onChange={(e) => setTargetId(e.target.value)}>
            {versions.map((v) => <option key={v.id} value={v.id}>{v.version}（{statusLabel(v.status)}）</option>)}
          </select>
        </label>
      </div>
      <div className="section-subtitle">当前程序</div>
      {loading ? <div className="message-banner">正在加载版本参数...</div> : null}
      {error ? <div className="message-banner message-error">{error}</div> : null}
      <div className="diff-stats">
        <article className="diff-stat changed"><strong>{diff.changed_count}</strong><span>已变更</span></article>
        <article className="diff-stat added"><strong>{diff.added_count}</strong><span>已新增</span></article>
        <article className="diff-stat removed"><strong>{diff.removed_count}</strong><span>已删除</span></article>
        <article className="diff-stat same"><strong>{diff.same_count}</strong><span>未变更</span></article>
      </div>
      <div className="diff-table-wrap">
        <table className="master-table diff-table">
          <thead>
            <tr>
              <th>刷子</th>
              <th>参数</th>
              <th>基准值</th>
              <th>对比值</th>
              <th>变化</th>
              <th>百分比</th>
            </tr>
          </thead>
          <tbody>
            {diff.rows.map((row, index) => {
              const changeIcon =
                row.change_type === "changed"
                  ? (row.change_percent ?? 0) > 0
                    ? <ArrowUp className="diff-up" />
                    : <ArrowDown className="diff-down" />
                  : row.change_type === "added"
                    ? <span className="diff-tag diff-tag-added">新增</span>
                    : row.change_type === "removed"
                      ? <span className="diff-tag diff-tag-removed">删除</span>
                      : <Minus className="diff-same" />;

              return (
                <tr key={index} className={`diff-row-${row.change_type}`}>
                  <td className="mono">{row.brush_no}</td>
                  <td>{row.parameter_name}</td>
                  <td className="mono">{row.source_value != null ? `${row.source_value} ${row.unit}` : "—"}</td>
                  <td className="mono">{row.target_value != null ? `${row.target_value} ${row.unit}` : "—"}</td>
                  <td>{changeIcon}</td>
                  <td className={`mono ${(row.change_percent ?? 0) > 0 ? "diff-up" : (row.change_percent ?? 0) < 0 ? "diff-down" : ""}`}>
                    {row.change_percent != null && row.change_percent !== 0 ? `${row.change_percent > 0 ? "+" : ""}${row.change_percent.toFixed(1)}%` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
