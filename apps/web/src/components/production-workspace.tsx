"use client";

import {
  Activity,
  Boxes,
  LoaderCircle,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Resource = { id: string; code: string; name: string };
type Program = { id: string; program_code: string; name: string; process_stage: string };
type ProgramVersion = { id: string; spray_program_id: string; version: string; status: string; program_name?: string; process_stage?: string };
type Material = {
  id: string; batch_no: string; material_code: string; material_name: string; material_type: string;
  supplier?: string | null; viscosity?: number | null; solid_ratio?: number | null; coa_values?: Record<string, unknown> | null;
};
type ProductionRun = {
  id: string; run_no: string; body_no?: string | null; factory_id: string; vehicle_model_id: string; color_id: string;
  shift?: string | null; started_at: string; completed_at?: string | null; context_values?: Record<string, unknown> | null;
};
type StageRun = {
  id: string; production_run_id: string; process_stage: string; program_version_id: string; material_batch_id?: string | null;
  actual_parameters?: Record<string, unknown> | null; status: string;
};
type ActualParameter = {
  id: string; production_stage_run_id: string; parameter_code: string; actual_value: number; unit: string;
  sampled_at: string; source_system?: string | null;
};
type Definition = { id: string; code: string; name: string; unit: string };
type ModalKind = "run" | "material" | "stage" | "actual";
type Modal = { kind: ModalKind; record?: ProductionRun | Material | StageRun | ActualParameter } | null;
type FormState = Record<string, string>;

const stages = [
  ["MIDCOAT_EXT", "中涂外喷"],
  ["BASECOAT_1", "色漆一站"],
  ["BASECOAT_2", "色漆二站"],
  ["CLEARCOAT_1", "清漆一站"],
  ["CLEARCOAT_2", "清漆二站"],
];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new Error(payload.error ?? `请求失败（${response.status}）`);
  return payload;
}

function localDateTime(value?: string | null): string {
  const date = value ? new Date(value) : new Date();
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function relationName(resources: Resource[], id?: string | null): string {
  const item = resources.find((resource) => resource.id === id);
  return item ? `${item.code} / ${item.name}` : "—";
}

export function ProductionWorkspace() {
  const [tab, setTab] = useState<"runs" | "materials">("runs");
  const [runs, setRuns] = useState<ProductionRun[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [factories, setFactories] = useState<Resource[]>([]);
  const [vehicleModels, setVehicleModels] = useState<Resource[]>([]);
  const [colors, setColors] = useState<Resource[]>([]);
  const [programVersions, setProgramVersions] = useState<ProgramVersion[]>([]);
  const [definitions, setDefinitions] = useState<Definition[]>([]);
  const [stageRuns, setStageRuns] = useState<StageRun[]>([]);
  const [actualParameters, setActualParameters] = useState<ActualParameter[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedStageId, setSelectedStageId] = useState("");
  const [query, setQuery] = useState("");
  const [modal, setModal] = useState<Modal>(null);
  const [form, setForm] = useState<FormState>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextRuns, nextMaterials, nextFactories, nextModels, nextColors, programs, nextDefinitions] = await Promise.all([
        request<ProductionRun[]>("/api/process/production-runs?limit=500"),
        request<Material[]>("/api/process/material-batches"),
        request<Resource[]>("/api/master-data/factories"),
        request<Resource[]>("/api/master-data/vehicle-models"),
        request<Resource[]>("/api/master-data/colors"),
        request<Program[]>("/api/process/spray-programs"),
        request<Definition[]>("/api/process/parameter-definitions"),
      ]);
      const versions = (await Promise.all(
        programs.map(async (program) =>
          (await request<ProgramVersion[]>(`/api/process/spray-programs/${program.id}/versions`)).map((version) => ({
            ...version,
            program_name: program.name,
            process_stage: program.process_stage,
          })),
        ),
      )).flat();
      setRuns(nextRuns);
      setMaterials(nextMaterials);
      setFactories(nextFactories);
      setVehicleModels(nextModels);
      setColors(nextColors);
      setProgramVersions(versions);
      setDefinitions(nextDefinitions);
      setSelectedRunId((current) => current || nextRuns[0]?.id || "");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "生产实绩加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadStages = useCallback(async (runId: string) => {
    if (!runId) {
      setStageRuns([]);
      setActualParameters([]);
      return;
    }
    try {
      const nextStages = await request<StageRun[]>(`/api/process/production-runs/${runId}/stages`);
      setStageRuns(nextStages);
      setSelectedStageId((current) => nextStages.some((stage) => stage.id === current) ? current : nextStages[0]?.id || "");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "工序实绩加载失败");
    }
  }, []);

  const loadActuals = useCallback(async (stageId: string) => {
    if (!stageId) {
      setActualParameters([]);
      return;
    }
    try {
      setActualParameters(await request<ActualParameter[]>(`/api/process/production-stage-runs/${stageId}/actual-parameters`));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "实际参数加载失败");
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, [reload]);
  useEffect(() => {
    const timer = window.setTimeout(() => void loadStages(selectedRunId), 0);
    return () => window.clearTimeout(timer);
  }, [loadStages, selectedRunId]);
  useEffect(() => {
    const timer = window.setTimeout(() => void loadActuals(selectedStageId), 0);
    return () => window.clearTimeout(timer);
  }, [loadActuals, selectedStageId]);

  const selectedRun = runs.find((run) => run.id === selectedRunId);
  const selectedStage = stageRuns.find((stage) => stage.id === selectedStageId);
  const filteredRuns = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return runs.filter((run) => !normalized || [run.run_no, run.body_no, run.shift].some((value) => String(value ?? "").toLowerCase().includes(normalized)));
  }, [query, runs]);
  const filteredMaterials = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return materials.filter((material) => !normalized || [material.batch_no, material.material_code, material.material_name, material.supplier].some((value) => String(value ?? "").toLowerCase().includes(normalized)));
  }, [materials, query]);

  function openModal(kind: ModalKind, record?: ProductionRun | Material | StageRun | ActualParameter) {
    setModal({ kind, record });
    if (kind === "run") {
      const item = record as ProductionRun | undefined;
      setForm({ run_no: item?.run_no ?? `RUN-${Date.now()}`, body_no: item?.body_no ?? "", factory_id: item?.factory_id ?? factories[0]?.id ?? "", vehicle_model_id: item?.vehicle_model_id ?? vehicleModels[0]?.id ?? "", color_id: item?.color_id ?? colors[0]?.id ?? "", shift: item?.shift ?? "", started_at: localDateTime(item?.started_at), completed_at: item?.completed_at ? localDateTime(item.completed_at) : "", context_values: JSON.stringify(item?.context_values ?? {}, null, 2) });
    } else if (kind === "material") {
      const item = record as Material | undefined;
      setForm({ batch_no: item?.batch_no ?? `LOT-${Date.now()}`, material_code: item?.material_code ?? "", material_name: item?.material_name ?? "", material_type: item?.material_type ?? "CLEARCOAT", supplier: item?.supplier ?? "", viscosity: item?.viscosity == null ? "" : String(item.viscosity), solid_ratio: item?.solid_ratio == null ? "" : String(item.solid_ratio), coa_values: JSON.stringify(item?.coa_values ?? {}, null, 2) });
    } else if (kind === "stage") {
      const item = record as StageRun | undefined;
      setForm({ process_stage: item?.process_stage ?? "MIDCOAT_EXT", program_version_id: item?.program_version_id ?? programVersions[0]?.id ?? "", material_batch_id: item?.material_batch_id ?? "", status: item?.status ?? "COMPLETED", actual_parameters: JSON.stringify(item?.actual_parameters ?? {}, null, 2) });
    } else {
      const item = record as ActualParameter | undefined;
      const definition = definitions.find((entry) => entry.code === item?.parameter_code) ?? definitions[0];
      setForm({ parameter_code: item?.parameter_code ?? definition?.code ?? "", actual_value: item ? String(item.actual_value) : "", unit: item?.unit ?? definition?.unit ?? "", sampled_at: localDateTime(item?.sampled_at), source_system: item?.source_system ?? "PLC" });
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!modal) return;
    setSubmitting(true);
    setError("");
    try {
      const isEdit = Boolean(modal.record);
      let path = "";
      let body: Record<string, unknown> = {};
      if (modal.kind === "run") {
        path = isEdit ? `/api/process/production-runs/${modal.record?.id}` : "/api/process/production-runs";
        body = { ...form, body_no: form.body_no || null, shift: form.shift || null, completed_at: form.completed_at ? new Date(form.completed_at).toISOString() : null, started_at: new Date(form.started_at).toISOString(), context_values: form.context_values.trim() ? JSON.parse(form.context_values) : null };
      } else if (modal.kind === "material") {
        path = isEdit ? `/api/process/material-batches/${modal.record?.id}` : "/api/process/material-batches";
        body = { ...form, supplier: form.supplier || null, viscosity: form.viscosity === "" ? null : Number(form.viscosity), solid_ratio: form.solid_ratio === "" ? null : Number(form.solid_ratio), coa_values: form.coa_values.trim() ? JSON.parse(form.coa_values) : null };
      } else if (modal.kind === "stage") {
        path = isEdit ? `/api/process/production-stage-runs/${modal.record?.id}` : `/api/process/production-runs/${selectedRunId}/stages`;
        body = { ...form, material_batch_id: form.material_batch_id || null, actual_parameters: form.actual_parameters.trim() ? JSON.parse(form.actual_parameters) : null };
      } else {
        path = isEdit ? `/api/process/actual-parameters/${modal.record?.id}` : `/api/process/production-stage-runs/${selectedStageId}/actual-parameters`;
        body = { ...form, actual_value: Number(form.actual_value), sampled_at: new Date(form.sampled_at).toISOString() };
      }
      await request(path, { method: isEdit ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setModal(null);
      setNotice("生产实绩已保存到 MySQL");
      await reload();
      await loadStages(selectedRunId);
      await loadActuals(selectedStageId);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function remove(kind: ModalKind, id: string) {
    if (!window.confirm("确认删除该记录？被下游数据引用时系统会阻止删除。")) return;
    const paths = { run: "production-runs", material: "material-batches", stage: "production-stage-runs", actual: "actual-parameters" };
    setSubmitting(true);
    try {
      await request(`/api/process/${paths[kind]}/${id}`, { method: "DELETE" });
      setNotice("记录已删除");
      if (kind === "run") setSelectedRunId("");
      if (kind === "stage") setSelectedStageId("");
      await reload();
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : "删除失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header"><div><span className="page-kicker">PRODUCTION TRACEABILITY</span><h1>生产实绩中心</h1><p>维护生产事件、五工序程序实绩、材料批次与实际参数，作为点位特征和 AI 建模的真实输入。</p></div><button className="button button-secondary" onClick={() => void reload()}><RefreshCw className={loading ? "spin" : ""} /> 刷新实时数据</button></header>
      {error ? <button className="message-banner message-error" onClick={() => setError("")}>{error}<X /></button> : null}
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}
      <section className="module-stat-strip"><article><span>生产事件</span><strong>{runs.length}</strong><small>按车身/批次追溯</small></article><article><span>当前事件工序</span><strong>{stageRuns.length}/5</strong><small>五个喷涂执行阶段</small></article><article><span>实际参数</span><strong>{actualParameters.length}</strong><small>PLC / 机器人采样</small></article><article><span>材料批次</span><strong>{materials.length}</strong><small>粘度、固含与 COA</small></article></section>
      <section className="panel production-workspace">
        <div className="master-tabs"><button className={tab === "runs" ? "active" : ""} onClick={() => setTab("runs")}>生产事件与工序</button><button className={tab === "materials" ? "active" : ""} onClick={() => setTab("materials")}>材料批次</button><label className="master-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索生产事件或材料" /></label><button className="button button-primary" onClick={() => openModal(tab === "runs" ? "run" : "material")}><Plus /> 新建{tab === "runs" ? "生产事件" : "材料批次"}</button></div>
        {tab === "runs" ? <div className="production-grid"><div className="production-run-list">{filteredRuns.map((run) => <button key={run.id} className={`program-list-item ${run.id === selectedRunId ? "selected" : ""}`} onClick={() => setSelectedRunId(run.id)}><div><strong>{run.run_no}</strong><span>{run.body_no || "未维护车身号"} · {run.shift || "未维护班次"}</span><small>{new Date(run.started_at).toLocaleString("zh-CN")}</small></div><Activity /></button>)}{!filteredRuns.length ? <div className="master-empty"><Activity /> 暂无生产事件</div> : null}</div><div className="production-detail">{selectedRun ? <><div className="production-run-summary"><div><span>生产事件</span><strong>{selectedRun.run_no}</strong></div><div><span>工厂</span><strong>{relationName(factories, selectedRun.factory_id)}</strong></div><div><span>车型 / 颜色</span><strong>{relationName(vehicleModels, selectedRun.vehicle_model_id)} · {relationName(colors, selectedRun.color_id)}</strong></div><div className="row-actions"><button className="icon-button" onClick={() => openModal("run", selectedRun)}><Pencil /></button><button className="icon-button icon-button-danger" onClick={() => void remove("run", selectedRun.id)}><Trash2 /></button></div></div><div className="production-stage-heading"><div><span className="eyebrow">FIVE PROCESS STAGES</span><h3>工序实绩</h3></div><button className="button button-primary" onClick={() => openModal("stage")} disabled={stageRuns.length >= 5}><Plus /> 添加工序</button></div><div className="production-stage-list">{stageRuns.map((stage) => <button className={`production-stage-card ${stage.id === selectedStageId ? "selected" : ""}`} key={stage.id} onClick={() => setSelectedStageId(stage.id)}><span>{stages.find(([code]) => code === stage.process_stage)?.[1] ?? stage.process_stage}</span><strong>{stage.status}</strong><small>{programVersions.find((version) => version.id === stage.program_version_id)?.program_name ?? "程序版本"} · {programVersions.find((version) => version.id === stage.program_version_id)?.version}</small></button>)}</div>{selectedStage ? <><div className="production-stage-heading"><div><span className="eyebrow">ACTUAL PARAMETERS</span><h3>实际参数</h3></div><div className="row-actions"><button className="button button-secondary" onClick={() => openModal("stage", selectedStage)}><Pencil /> 编辑工序</button><button className="button button-secondary danger-button" onClick={() => void remove("stage", selectedStage.id)}><Trash2 /> 删除工序</button><button className="button button-primary" onClick={() => openModal("actual")}><Plus /> 添加实绩参数</button></div></div><div className="compact-table"><div className="production-actual-row compact-head"><span>参数</span><span>实际值</span><span>来源</span><span>采样时间</span><span>操作</span></div>{actualParameters.map((parameter) => <div className="production-actual-row" key={parameter.id}><span><strong>{definitions.find((item) => item.code === parameter.parameter_code)?.name ?? parameter.parameter_code}</strong><small>{parameter.parameter_code}</small></span><span>{parameter.actual_value} {parameter.unit}</span><span>{parameter.source_system || "—"}</span><span>{new Date(parameter.sampled_at).toLocaleString("zh-CN")}</span><span className="row-actions"><button className="icon-button" onClick={() => openModal("actual", parameter)}><Pencil /></button><button className="icon-button icon-button-danger" onClick={() => void remove("actual", parameter.id)}><Trash2 /></button></span></div>)}</div></> : null}</> : <div className="large-empty"><Activity /> 请选择生产事件</div>}</div></div> : <div className="master-table-wrap"><table className="master-table production-material-table"><thead><tr><th>批次号</th><th>材料</th><th>类型</th><th>供应商</th><th>粘度</th><th>固含比</th><th>操作</th></tr></thead><tbody>{filteredMaterials.map((material) => <tr key={material.id}><td>{material.batch_no}</td><td>{material.material_code} / {material.material_name}</td><td>{material.material_type}</td><td>{material.supplier ?? "—"}</td><td>{material.viscosity ?? "—"}</td><td>{material.solid_ratio ?? "—"}</td><td><div className="row-actions"><button className="icon-button" onClick={() => openModal("material", material)}><Pencil /></button><button className="icon-button icon-button-danger" onClick={() => void remove("material", material.id)}><Trash2 /></button></div></td></tr>)}</tbody></table>{!filteredMaterials.length ? <div className="master-empty"><Boxes /> 暂无材料批次</div> : null}</div>}
      </section>
      {modal ? <ProductionModal modal={modal} form={form} setForm={setForm} submit={submit} close={() => setModal(null)} submitting={submitting} factories={factories} vehicleModels={vehicleModels} colors={colors} materials={materials} versions={programVersions} definitions={definitions} /> : null}
    </div>
  );
}

function ProductionModal({ modal, form, setForm, submit, close, submitting, factories, vehicleModels, colors, materials, versions, definitions }: { modal: NonNullable<Modal>; form: FormState; setForm: (form: FormState) => void; submit: (event: FormEvent<HTMLFormElement>) => void; close: () => void; submitting: boolean; factories: Resource[]; vehicleModels: Resource[]; colors: Resource[]; materials: Material[]; versions: ProgramVersion[]; definitions: Definition[] }) {
  const input = (key: string, label: string, type = "text", required = false) => <label className="form-field"><span>{label}{required ? <b>*</b> : null}</span><input type={type} step={type === "number" ? "any" : undefined} required={required} value={form[key] ?? ""} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>;
  const select = (key: string, label: string, options: [string, string][]) => <label className="form-field"><span>{label}<b>*</b></span><select required value={form[key] ?? ""} onChange={(event) => { const value = event.target.value; const definition = key === "parameter_code" ? definitions.find((item) => item.code === value) : undefined; setForm({ ...form, [key]: value, ...(definition ? { unit: definition.unit } : {}) }); }}>{options.map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></label>;
  return <div className="modal-backdrop" onMouseDown={close}><section className="modal-card quality-modal" role="dialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}><div className="modal-heading"><div><span className="eyebrow">PRODUCTION DATA</span><h2>{modal.record ? "编辑" : "新建"}{{ run: "生产事件", material: "材料批次", stage: "工序实绩", actual: "实际参数" }[modal.kind]}</h2></div><button className="icon-button" onClick={close}><X /></button></div><form onSubmit={submit}><div className="form-grid">{modal.kind === "run" ? <>{input("run_no", "生产事件编号", "text", true)}{input("body_no", "车身号")}{select("factory_id", "工厂", factories.map((item) => [item.id, `${item.code} / ${item.name}`]))}{select("vehicle_model_id", "车型", vehicleModels.map((item) => [item.id, `${item.code} / ${item.name}`]))}{select("color_id", "颜色", colors.map((item) => [item.id, `${item.code} / ${item.name}`]))}{input("shift", "班次")}{input("started_at", "开始时间", "datetime-local", true)}{input("completed_at", "完成时间", "datetime-local")}<TextArea keyName="context_values" label="追溯上下文 JSON（不进入 AI 特征）" form={form} setForm={setForm} /></> : null}{modal.kind === "material" ? <>{input("batch_no", "批次号", "text", true)}{input("material_code", "材料代码", "text", true)}{input("material_name", "材料名称", "text", true)}{select("material_type", "材料类型", [["MIDCOAT", "中涂"], ["BASECOAT", "色漆"], ["CLEARCOAT", "清漆"]])}{input("supplier", "供应商")}{input("viscosity", "粘度", "number")}{input("solid_ratio", "固含比", "number")}<TextArea keyName="coa_values" label="COA JSON（受范围策略校验）" form={form} setForm={setForm} /></> : null}{modal.kind === "stage" ? <>{select("process_stage", "工序", stages as [string, string][])}{select("program_version_id", "程序版本", versions.map((item) => [item.id, `${item.program_name} / ${item.version} / ${item.status}`]))}<label className="form-field"><span>材料批次</span><select value={form.material_batch_id ?? ""} onChange={(event) => setForm({ ...form, material_batch_id: event.target.value })}><option value="">无</option>{materials.map((item) => <option value={item.id} key={item.id}>{item.batch_no} / {item.material_name}</option>)}</select></label>{input("status", "状态", "text", true)}<TextArea keyName="actual_parameters" label="工序汇总参数 JSON（受范围策略校验）" form={form} setForm={setForm} /></> : null}{modal.kind === "actual" ? <>{select("parameter_code", "参数", definitions.map((item) => [item.code, `${item.name} / ${item.code}`]))}{input("actual_value", "实际值", "number", true)}{input("unit", "单位", "text", true)}{input("sampled_at", "采样时间", "datetime-local", true)}{input("source_system", "来源系统")}</> : null}</div><div className="modal-actions"><button type="button" className="button button-secondary" onClick={close}>取消</button><button className="button button-primary" disabled={submitting}>{submitting ? <LoaderCircle className="spin" /> : null} 保存到 MySQL</button></div></form></section></div>;
}

function TextArea({ keyName, label, form, setForm }: { keyName: string; label: string; form: FormState; setForm: (form: FormState) => void }) {
  return <label className="form-field form-field-wide"><span>{label}</span><textarea rows={6} value={form[keyName] ?? ""} onChange={(event) => setForm({ ...form, [keyName]: event.target.value })} /></label>;
}
