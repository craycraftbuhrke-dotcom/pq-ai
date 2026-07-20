"use client";

import { Check, LoaderCircle, Pencil } from "lucide-react";
import { FormEvent, useState } from "react";

import { ModalShell } from "@/components/modal-shell";

type PointParameter = {
  parameter_code: string;
  parameter_name: string;
  configured_value?: number | null;
  unit: string;
  hard_min?: number | null;
  hard_max?: number | null;
};

type Contribution = {
  program_version_id?: string | null;
  program_version?: string | null;
  program_code?: string | null;
  program_name?: string | null;
  brush_no: string;
  brush_table_no: string;
};

type Brush = { id: string; brush_no: string; brush_table_no: string };
type BrushParameter = PointParameter & { id: string; brush_id: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  const payload = (await response.json().catch(() => ({}))) as T & { error?: unknown };
  if (!response.ok) throw new Error(typeof payload.error === "string" ? payload.error : `操作失败（${response.status}）`);
  return payload;
}

export function PointParameterVersionEditor({ contribution }: { contribution: Contribution }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [brushes, setBrushes] = useState<Brush[]>([]);
  const [parameters, setParameters] = useState<BrushParameter[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [filter, setFilter] = useState(contribution.brush_no);
  const [newVersion, setNewVersion] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function openEditor() {
    if (!contribution.program_version_id) return;
    setOpen(true);
    setLoading(true);
    setError("");
    setNotice("");
    setNewVersion(`${contribution.program_version ?? "1.0"}.D${Date.now().toString().slice(-6)}`.slice(0, 32));
    try {
      const nextBrushes = await request<Brush[]>(`/api/process/program-versions/${contribution.program_version_id}/brushes`);
      const rows = (await Promise.all(nextBrushes.map((brush) => request<BrushParameter[]>(`/api/process/brushes/${brush.id}/parameters`)))).flat();
      setBrushes(nextBrushes);
      setParameters(rows);
      setValues(Object.fromEntries(rows.map((row) => [row.id, String(row.configured_value ?? "")])))
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "完整刷子表加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!contribution.program_version_id) return;
    const brushById = new Map(brushes.map((brush) => [brush.id, brush]));
    const edits = parameters.flatMap((parameter) => {
      const raw = values[parameter.id];
      if (raw == null || raw.trim() === "") return [];
      const next = Number(raw);
      if (!Number.isFinite(next) || next === parameter.configured_value) return [];
      const brush = brushById.get(parameter.brush_id);
      return brush ? [{ brush_no: brush.brush_no, parameter_code: parameter.parameter_code, new_value: next }] : [];
    });
    if (!edits.length) {
      setError("没有发现参数变化，请先修改至少一个数值");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const result = await request<{ version: string; brush_count: number; parameter_count: number; changed_parameter_count: number }>(`/api/process/program-versions/${contribution.program_version_id}/derive-complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: newVersion, edits }),
      });
      setNotice(`新版本 ${result.version} 已生成：完整复制 ${result.brush_count} 个刷子、${result.parameter_count} 项参数，本次改变 ${result.changed_parameter_count} 项。新版本仍是草稿，不会影响上位机。`);
    } catch (operationError) {
      setError(operationError instanceof Error ? operationError.message : "新版本生成失败");
    } finally {
      setSaving(false);
    }
  }

  const visibleBrushIds = new Set(brushes.filter((brush) => !filter || brush.brush_no.includes(filter) || brush.brush_table_no.includes(filter)).map((brush) => brush.id));

  return (
    <>
      <button type="button" className="button button-secondary" disabled={!contribution.program_version_id} onClick={() => void openEditor()}><Pencil /> 调整本工段参数</button>
      {open ? (
        <ModalShell eyebrow="受控参数调整" title={`${contribution.program_name ?? contribution.program_code ?? "喷涂程序"} · 派生完整新版本`} description="只需修改需要调整的数值。保存时后端会复制原版本的全部刷子、全部参数和点位贡献，原版本及上位机不会被修改。" onClose={() => setOpen(false)} busy={saving}>
          <form onSubmit={(event) => void save(event)}>
            <div className="form-grid">
              <label className="form-field"><span>新版本号</span><input required value={newVersion} onChange={(event) => setNewVersion(event.target.value)} maxLength={32} /></label>
              <label className="form-field"><span>查找刷子号或刷子表</span><input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="留空显示全部" /></label>
            </div>
            {loading ? <div className="program-empty"><LoaderCircle className="spin" /> 正在加载完整刷子表…</div> : (
              <div className="point-parameter-edit-table">
                {brushes.filter((brush) => visibleBrushIds.has(brush.id)).map((brush) => (
                  <section key={brush.id}>
                    <div className="program-subheading compact"><div><strong>刷子表 {brush.brush_table_no} · 刷子 {brush.brush_no}</strong></div></div>
                    {parameters.filter((parameter) => parameter.brush_id === brush.id).map((parameter) => (
                      <label className="point-parameter-edit-row" key={parameter.id}>
                        <span><strong>{parameter.parameter_name}</strong><small>{parameter.hard_min != null || parameter.hard_max != null ? `允许范围 ${parameter.hard_min ?? "不限"} 至 ${parameter.hard_max ?? "不限"} ${parameter.unit}` : parameter.unit}</small></span>
                        <input type="number" step="any" value={values[parameter.id] ?? ""} min={parameter.hard_min ?? undefined} max={parameter.hard_max ?? undefined} onChange={(event) => setValues({ ...values, [parameter.id]: event.target.value })} />
                      </label>
                    ))}
                  </section>
                ))}
              </div>
            )}
            {error ? <div className="form-error">{error}</div> : null}
            {notice ? <div className="form-success">{notice}</div> : null}
            <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setOpen(false)}>关闭</button><button className="button button-primary" disabled={loading || saving || Boolean(notice)}>{saving ? <LoaderCircle className="spin" /> : <Check />} 保存为完整新版本</button></div>
          </form>
        </ModalShell>
      ) : null}
    </>
  );
}
