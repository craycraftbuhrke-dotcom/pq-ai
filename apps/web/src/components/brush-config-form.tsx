"use client";

import { LoaderCircle, Plus } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

import { ModalShell } from "@/components/modal-shell";
import { stageLabel } from "@/lib/display-labels";
import { definitionsForProcessStage } from "@/lib/parameter-stage-scope";

type Resource = { id: string; code: string; name: string };
type Point = Resource & {
  vehicle_model_id: string;
  part_id: string;
  point_type?: string;
};
type ParameterDefinition = Resource & {
  category: string;
  unit: string;
  hard_min?: number | null;
  hard_max?: number | null;
  is_recommendable: boolean;
};
type Program = {
  id: string;
  program_code: string;
  name: string;
  process_stage: string;
};
type Version = {
  id: string;
  version: string;
  vehicle_model_ids?: string[];
};
type Brush = {
  id: string;
  brush_no: string;
  brush_table_no: string;
  spray_position?: string | null;
  part_id?: string | null;
  remark?: string | null;
};
type BrushParameter = {
  id: string;
  parameter_definition_id?: string | null;
  parameter_code: string;
  parameter_name: string;
  configured_value: number;
  unit: string;
  soft_min?: number | null;
  soft_max?: number | null;
  is_recommendable: boolean;
};
type Contribution = {
  id: string;
  measurement_point_id: string;
  overlap_ratio: number;
  contribution_weight: number;
  source: string;
  version: string;
  is_approved: boolean;
};

type ParamRow = {
  definitionId: string;
  code: string;
  name: string;
  unit: string;
  hardMin?: number | null;
  hardMax?: number | null;
  existingId?: string;
  configuredValue: string;
  softMin: string;
  softMax: string;
  isRecommendable: boolean;
  enabled: boolean;
};

type ContribRow = {
  pointId: string;
  pointLabel: string;
  existing: boolean;
  overlapRatio: string;
  contributionWeight: string;
  source: string;
  version: string;
  isApproved: boolean;
  enabled: boolean;
};

type BrushConfigFormProps = {
  open: boolean;
  editingBrush?: Brush | null;
  program: Program;
  version: Version;
  parts: Resource[];
  points: Point[];
  definitions: ParameterDefinition[];
  existingParameters: BrushParameter[];
  existingContributions: Contribution[];
  busy?: boolean;
  onClose: () => void;
  onSaved: (brushId: string) => void;
  onError: (message: string) => void;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new Error(payload.error ?? `请求失败（${response.status}）`);
  return payload;
}

function buildParamRows(
  processStage: string,
  definitions: ParameterDefinition[],
  existing: BrushParameter[],
  isEdit: boolean,
): ParamRow[] {
  const scoped = definitionsForProcessStage(definitions, processStage);
  return scoped.map((definition) => {
    const found =
      existing.find((item) => item.parameter_definition_id === definition.id) ??
      existing.find((item) => item.parameter_code === definition.code);
    return {
      definitionId: definition.id,
      code: definition.code,
      name: definition.name,
      unit: definition.unit,
      hardMin: definition.hard_min,
      hardMax: definition.hard_max,
      existingId: found?.id,
      configuredValue: found ? String(found.configured_value) : "",
      softMin: found?.soft_min == null ? "" : String(found.soft_min),
      softMax: found?.soft_max == null ? "" : String(found.soft_max),
      isRecommendable: found?.is_recommendable ?? definition.is_recommendable,
      // 新建默认勾选本工序全部参数；编辑仅勾选已有配置
      enabled: isEdit ? Boolean(found) : true,
    };
  });
}

function contributionPointsFor(points: Point[], partId: string, version: Version): Point[] {
  return points.filter((point) => {
    if (point.point_type && point.point_type !== "QUALITY") return false;
    if (partId && point.part_id !== partId) return false;
    if (version.vehicle_model_ids?.length && !version.vehicle_model_ids.includes(point.vehicle_model_id)) {
      return false;
    }
    return true;
  });
}

function buildContribRows(
  points: Point[],
  partId: string,
  version: Version,
  existing: Contribution[],
): ContribRow[] {
  return contributionPointsFor(points, partId, version).map((point) => {
    const found = existing.find((item) => item.measurement_point_id === point.id);
    return {
      pointId: point.id,
      pointLabel: `${point.code} / ${point.name}`,
      existing: Boolean(found),
      overlapRatio: found ? String(found.overlap_ratio) : "0.5",
      contributionWeight: found ? String(found.contribution_weight) : "0.5",
      source: found?.source ?? "EXPERT",
      version: found?.version ?? "1.0",
      isApproved: found?.is_approved ?? false,
      enabled: Boolean(found),
    };
  });
}

export function BrushConfigForm(props: BrushConfigFormProps) {
  if (!props.open) return null;
  // key 强制在打开/切换刷子时 remount，用 props 直接初始化，避免 effect 内 setState
  const formKey = `${props.editingBrush?.id ?? "new"}:${props.program.id}:${props.version.id}`;
  return <BrushConfigFormBody key={formKey} {...props} />;
}

function BrushConfigFormBody({
  editingBrush,
  program,
  version,
  parts,
  points,
  definitions,
  existingParameters,
  existingContributions,
  busy = false,
  onClose,
  onSaved,
  onError,
}: BrushConfigFormProps) {
  const isEdit = Boolean(editingBrush);
  const [brushNo, setBrushNo] = useState(editingBrush?.brush_no ?? "");
  const [brushTableNo, setBrushTableNo] = useState(editingBrush?.brush_table_no ?? "");
  const [sprayPosition, setSprayPosition] = useState(editingBrush?.spray_position ?? "");
  const [partId, setPartId] = useState(editingBrush?.part_id ?? "");
  const [remark, setRemark] = useState(editingBrush?.remark ?? "");
  const [paramRows, setParamRows] = useState(() =>
    buildParamRows(program.process_stage, definitions, isEdit ? existingParameters : [], isEdit),
  );
  const [contribRows, setContribRows] = useState(() =>
    buildContribRows(points, editingBrush?.part_id ?? "", version, isEdit ? existingContributions : []),
  );
  const [submitting, setSubmitting] = useState(false);

  const scopedCount = useMemo(
    () => definitionsForProcessStage(definitions, program.process_stage).length,
    [definitions, program.process_stage],
  );

  function updateParam(code: string, patch: Partial<ParamRow>) {
    setParamRows((rows) => rows.map((row) => (row.code === code ? { ...row, ...patch } : row)));
  }

  function updateContrib(pointId: string, patch: Partial<ContribRow>) {
    setContribRows((rows) =>
      rows.map((row) => (row.pointId === pointId ? { ...row, ...patch } : row)),
    );
  }

  function onPartChange(nextPartId: string) {
    setPartId(nextPartId);
    setContribRows(buildContribRows(points, nextPartId, version, isEdit ? existingContributions : []));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!brushNo.trim() || !brushTableNo.trim()) {
      onError("请填写刷子号和刷子表号");
      return;
    }
    const enabledParams = paramRows.filter((row) => row.enabled && row.configuredValue !== "");
    if (!enabledParams.length) {
      onError("请至少填写一项本工序配置参数");
      return;
    }
    for (const row of enabledParams) {
      if (Number.isNaN(Number(row.configuredValue))) {
        onError(`参数「${row.name}」的配置值无效`);
        return;
      }
    }
    const enabledContribs = contribRows.filter((row) => row.enabled);
    for (const row of enabledContribs) {
      const weight = Number(row.contributionWeight);
      if (!(weight > 0)) {
        onError(`测量点「${row.pointLabel}」的贡献权重必须大于 0`);
        return;
      }
    }

    setSubmitting(true);
    try {
      const brushBody = {
        brush_no: brushNo.trim(),
        brush_table_no: brushTableNo.trim(),
        spray_position: sprayPosition.trim() || null,
        part_id: partId || null,
        remark: remark.trim() || null,
      };
      const brush = editingBrush
        ? await request<Brush>(`/api/process/brushes/${editingBrush.id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(brushBody),
          })
        : await request<Brush>(`/api/process/program-versions/${version.id}/brushes`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(brushBody),
          });

      await Promise.all(
        enabledParams.map((row) => {
          const body = {
            parameter_definition_id: row.definitionId,
            parameter_code: row.code,
            parameter_name: row.name,
            configured_value: Number(row.configuredValue),
            unit: row.unit,
            soft_min: row.softMin === "" ? null : Number(row.softMin),
            soft_max: row.softMax === "" ? null : Number(row.softMax),
            hard_min: row.hardMin ?? null,
            hard_max: row.hardMax ?? null,
            is_recommendable: row.isRecommendable,
          };
          if (row.existingId) {
            return request(`/api/process/brush-parameters/${row.existingId}`, {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(body),
            });
          }
          return request(`/api/process/brushes/${brush.id}/parameters`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
        }),
      );

      await Promise.all(
        enabledContribs.map((row) =>
          request(`/api/process/brushes/${brush.id}/contributions/${row.pointId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              overlap_ratio: Number(row.overlapRatio),
              contribution_weight: Number(row.contributionWeight),
              source: row.source,
              version: row.version,
              is_approved: row.isApproved,
            }),
          }),
        ),
      );

      onSaved(brush.id);
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "刷子配置保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  const disabled = busy || submitting;

  return (
    <ModalShell
      className="quality-modal brush-config-modal"
      eyebrow={editingBrush ? "编辑刷子配置" : "新建刷子配置"}
      title={editingBrush ? `编辑刷子 ${editingBrush.brush_no}` : "一次填完刷子、参数与点位贡献"}
      description={`当前程序：${program.program_code} · ${stageLabel(program.process_stage)} · 版本 ${version.version}。参数列表已按本工序过滤，共 ${scopedCount} 项。`}
      onClose={onClose}
      busy={disabled}
    >
      <form onSubmit={(event) => void submit(event)}>
        <div className="brush-config-form">
          <section className="brush-config-section">
            <header>
              <h3>1. 刷子身份</h3>
              <p>先确认刷子号与负责零件；零件会决定下方可选测量点。</p>
            </header>
            <div className="form-grid">
              <label className="form-field">
                <span>刷子号 <b>*</b></span>
                <input required value={brushNo} onChange={(event) => setBrushNo(event.target.value)} disabled={disabled} />
              </label>
              <label className="form-field">
                <span>刷子表号 <b>*</b></span>
                <input required value={brushTableNo} onChange={(event) => setBrushTableNo(event.target.value)} disabled={disabled} />
              </label>
              <label className="form-field">
                <span>喷涂位置</span>
                <input value={sprayPosition} onChange={(event) => setSprayPosition(event.target.value)} disabled={disabled} />
              </label>
              <label className="form-field">
                <span>负责零件</span>
                <select value={partId} onChange={(event) => onPartChange(event.target.value)} disabled={disabled}>
                  <option value="">未关联</option>
                  {parts.map((part) => (
                    <option key={part.id} value={part.id}>
                      {part.code} / {part.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field form-field-wide">
                <span>备注</span>
                <input value={remark} onChange={(event) => setRemark(event.target.value)} disabled={disabled} />
              </label>
            </div>
          </section>

          <section className="brush-config-section">
            <header>
              <h3>2. 配置参数（{stageLabel(program.process_stage)}）</h3>
              <p>只显示本工序相关参数。勾选并填写配置值后保存；未勾选的不会写入。</p>
            </header>
            {!paramRows.length ? (
              <div className="program-empty">当前工序暂无参数定义，请先在系统中种子化参数目录。</div>
            ) : (
              <div className="brush-matrix-table">
                <div className="brush-matrix-row brush-matrix-head">
                  <span>选用</span>
                  <span>参数</span>
                  <span>配置值</span>
                  <span>软下限</span>
                  <span>软上限</span>
                  <span>可推荐</span>
                </div>
                {paramRows.map((row) => (
                  <div className={`brush-matrix-row${row.enabled ? "" : " muted"}`} key={row.code}>
                    <label className="checkbox-field">
                      <input
                        type="checkbox"
                        checked={row.enabled}
                        onChange={(event) => updateParam(row.code, { enabled: event.target.checked })}
                        disabled={disabled}
                      />
                    </label>
                    <span>
                      <strong>{row.name}</strong>
                      <small>
                        {row.code} · {row.unit}
                      </small>
                    </span>
                    <input
                      type="number"
                      step="any"
                      value={row.configuredValue}
                      disabled={disabled || !row.enabled}
                      onChange={(event) => updateParam(row.code, { configuredValue: event.target.value })}
                      placeholder="必填"
                    />
                    <input
                      type="number"
                      step="any"
                      value={row.softMin}
                      disabled={disabled || !row.enabled}
                      onChange={(event) => updateParam(row.code, { softMin: event.target.value })}
                    />
                    <input
                      type="number"
                      step="any"
                      value={row.softMax}
                      disabled={disabled || !row.enabled}
                      onChange={(event) => updateParam(row.code, { softMax: event.target.value })}
                    />
                    <label className="checkbox-field">
                      <input
                        type="checkbox"
                        checked={row.isRecommendable}
                        disabled={disabled || !row.enabled}
                        onChange={(event) => updateParam(row.code, { isRecommendable: event.target.checked })}
                      />
                    </label>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="brush-config-section">
            <header>
              <h3>3. 测量点贡献权重</h3>
              <p>
                {partId
                  ? "勾选本刷子覆盖的测量点，填写重叠率与贡献权重。"
                  : "建议先选择负责零件，以过滤出相关测量点；也可直接勾选可用点位。"}
              </p>
            </header>
            {!contribRows.length ? (
              <div className="program-empty">
                暂无可用质量测量点。请检查版本适用车型、刷子负责零件和测量点主数据。
              </div>
            ) : (
              <div className="brush-matrix-table contribution-matrix">
                <div className="brush-matrix-row brush-matrix-head contribution-matrix-head">
                  <span>选用</span>
                  <span>测量点</span>
                  <span>重叠率 (0~1)</span>
                  <span>贡献权重 (0~1)</span>
                  <span>已审批</span>
                </div>
                {contribRows.map((row) => (
                  <div className={`brush-matrix-row contribution-matrix-row${row.enabled ? "" : " muted"}`} key={row.pointId}>
                    <label className="checkbox-field">
                      <input
                        type="checkbox"
                        checked={row.enabled}
                        onChange={(event) => updateContrib(row.pointId, { enabled: event.target.checked })}
                        disabled={disabled}
                      />
                    </label>
                    <span>
                      <strong>{row.pointLabel}</strong>
                    </span>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      max="1"
                      value={row.overlapRatio}
                      disabled={disabled || !row.enabled}
                      onChange={(event) => updateContrib(row.pointId, { overlapRatio: event.target.value })}
                    />
                    <input
                      type="number"
                      step="any"
                      min="0"
                      max="1"
                      value={row.contributionWeight}
                      disabled={disabled || !row.enabled}
                      onChange={(event) =>
                        updateContrib(row.pointId, { contributionWeight: event.target.value })
                      }
                    />
                    <label className="checkbox-field">
                      <input
                        type="checkbox"
                        checked={row.isApproved}
                        disabled={disabled || !row.enabled}
                        onChange={(event) => updateContrib(row.pointId, { isApproved: event.target.checked })}
                      />
                    </label>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
        <div className="modal-actions">
          <button className="button button-secondary" type="button" onClick={onClose} disabled={disabled}>
            取消
          </button>
          <button className="button button-primary" type="submit" disabled={disabled}>
            {submitting ? <LoaderCircle className="spin" aria-hidden="true" /> : <Plus aria-hidden="true" />}
            {submitting ? "正在保存全部" : "保存刷子、参数与贡献"}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}
