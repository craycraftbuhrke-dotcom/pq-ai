"use client";

import { FlaskConical, LoaderCircle, Pencil, Plus, RefreshCw, Trash2, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { BulkDataActions } from "@/components/bulk-data-actions";
import { ModalShell } from "@/components/modal-shell";
import { JsonObjectEditor } from "@/components/structured-json-editor";
import { physicalDeleteDisabledMessage } from "@/lib/delete-policy";
import { qualityTypeLabel, reliabilityLabel, stageLabel, statusLabel } from "@/lib/display-labels";

type Kind = "definitions" | "methods" | "specifications" | "applicabilities" | "results";
type FormState = Record<string, string | boolean>;
type Resource = {
  id: string;
  code?: string;
  name?: string;
  category?: string;
  canonical_unit?: string;
  target_families?: string[];
  is_model_feature?: boolean;
  characteristic_definition_id?: string;
  version?: string;
  method_type?: string;
  result_unit?: string;
  procedure_uri?: string | null;
  conditions?: Record<string, unknown> | null;
  material_code?: string;
  method_id?: string;
  lower_limit?: number | null;
  upper_limit?: number | null;
  source_uri?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  process_stage?: string;
  material_type?: string;
  target_family?: string;
  is_required?: boolean;
  result_no?: string;
  material_batch_id?: string;
  result_value?: number;
  unit?: string;
  tested_at?: string;
  tested_by?: string | null;
  raw_values?: Record<string, unknown> | null;
  reliability_status?: string;
  reliability_issues?: string[] | null;
  is_within_spec?: boolean | null;
  status?: string;
  approved_by?: string | null;
  remark?: string | null;
  description?: string | null;
};
type MaterialBatch = { id: string; batch_no: string; material_code: string; material_name: string; material_type: string };
type Summary = {
  definitions: number;
  methods: number;
  specifications: number;
  active_specifications: number;
  applicabilities: number;
  active_applicabilities: number;
  results: number;
  verified_results: number;
  failed_results: number;
};

const kinds: Array<[Kind, string]> = [
  ["definitions", "特性定义"],
  ["methods", "检测方法"],
  ["specifications", "材料规格"],
  ["applicabilities", "工序/目标族适用关系"],
  ["results", "批次检测结果"],
];
const stageOptions: Array<[string, string]> = [["MIDCOAT_EXT", "中涂外喷"], ["BASECOAT_1", "色漆一站"], ["BASECOAT_2", "色漆二站"], ["CLEARCOAT_1", "清漆一站"], ["CLEARCOAT_2", "清漆二站"]];
const qualityOptions: Array<[string, string]> = [["ORANGE_PEEL", "橘皮"], ["COLOR_DIFFERENCE", "色差/效应"], ["THICKNESS", "膜厚"]];
const statusOptions: Array<[string, string]> = [["DRAFT", "草稿"], ["APPROVED", "已批准"], ["ACTIVE", "生效"], ["RETIRED", "退役"]];
const MATERIAL_TYPE_LABELS: Record<string, string> = { MIDCOAT: "中涂", BASECOAT: "色漆", CLEARCOAT: "清漆" };

function materialTypeLabel(code: string | null | undefined): string {
  if (!code) return "—";
  return MATERIAL_TYPE_LABELS[code] ?? code;
}

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

function jsonObject(value: string, label: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(value || "{}") as unknown;
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") throw new Error();
    return parsed as Record<string, unknown>;
  } catch {
    throw new Error(`${label}必须是 JSON 对象`);
  }
}

export function MaterialGovernancePanel() {
  const [kind, setKind] = useState<Kind>("definitions");
  const [resources, setResources] = useState<Record<Kind, Resource[]>>({ definitions: [], methods: [], specifications: [], applicabilities: [], results: [] });
  const [materials, setMaterials] = useState<MaterialBatch[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [modal, setModal] = useState<Resource | "new" | null>(null);
  const [form, setForm] = useState<FormState>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "error" | "success"; text: string } | null>(null);

  const closeModal = useCallback(() => {
    if (submitting) return;
    setModal(null);
  }, [submitting]);
  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [nextSummary, definitions, methods, specifications, applicabilities, results, nextMaterials] = await Promise.all([
        request<Summary>("/api/process/material-governance/summary"),
        request<Resource[]>("/api/process/material-governance/definitions"),
        request<Resource[]>("/api/process/material-governance/methods"),
        request<Resource[]>("/api/process/material-governance/specifications"),
        request<Resource[]>("/api/process/material-governance/applicabilities"),
        request<Resource[]>("/api/process/material-governance/results"),
        request<MaterialBatch[]>("/api/process/material-batches"),
      ]);
      setSummary(nextSummary);
      setResources({ definitions, methods, specifications, applicabilities, results });
      setMaterials(nextMaterials);
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "材料治理数据加载失败" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  const maps = useMemo(() => ({
    definitions: new Map(resources.definitions.map((item) => [item.id, item])),
    methods: new Map(resources.methods.map((item) => [item.id, item])),
    materials: new Map(materials.map((item) => [item.id, item])),
  }), [materials, resources.definitions, resources.methods]);

  function open(record?: Resource) {
    const next = initialForm(kind, record);
    if (!record) {
      if (kind === "methods" || kind === "applicabilities") next.characteristic_definition_id = resources.definitions[0]?.id ?? "";
      if (kind === "specifications") {
        next.material_code = materials[0]?.material_code ?? "";
        next.characteristic_definition_id = resources.definitions[0]?.id ?? "";
        next.method_id = resources.methods[0]?.id ?? "";
      }
      if (kind === "results") {
        next.material_batch_id = materials[0]?.id ?? "";
        next.characteristic_definition_id = resources.definitions[0]?.id ?? "";
        next.method_id = resources.methods[0]?.id ?? "";
      }
    }
    setForm(next);
    setModal(record ?? "new");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!modal) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const editing = modal !== "new";
      await request(`/api/process/material-governance/${kind}${editing ? `/${modal.id}` : ""}`, {
        method: editing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildBody(kind, form)),
      });
      setMessage({ type: "success", text: `${kindName(kind)}已${editing ? "更新" : "创建"}并重新判定材料可靠性` });
      setModal(null);
      await reload();
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "保存失败" });
    } finally {
      setSubmitting(false);
    }
  }

  function remove(_record: Resource) {
    void _record;
    setMessage({ type: "error", text: `${kindName(kind)}不能物理删除。${physicalDeleteDisabledMessage}` });
  }

  function bulkResult(message: string, type: "success" | "error") {
    setMessage({ type, text: message });
  }

  return (
    <div className="measurement-governance material-governance">
      {message ? <button className={`message-banner message-${message.type}`} onClick={() => setMessage(null)}>{message.text}<X /></button> : null}
      <section className="quality-analytics-stat-grid">
        <article><span>特性定义 / 方法</span><strong>{summary?.definitions ?? 0} / {summary?.methods ?? 0}</strong><small>稳定字段语义、单位与检测方法版本</small></article>
        <article><span>生效规格 / 总规格</span><strong>{summary?.active_specifications ?? 0} / {summary?.specifications ?? 0}</strong><small>来源、有效期、批准人与可选上下限</small></article>
        <article><span>生效适用关系</span><strong>{summary?.active_applicabilities ?? 0} / {summary?.applicabilities ?? 0}</strong><small>按材料类型、工序和质量目标族治理</small></article>
        <article><span>可信结果 / 失败结果</span><strong>{summary?.verified_results ?? 0} / {summary?.failed_results ?? 0}</strong><small>只有「已验证」且在投产前完成的检测结果才会进入智能分析</small></article>
      </section>
      <div className="governance-toolbar">
        <div className="master-tabs">{kinds.map(([key, text]) => <button key={key} className={kind === key ? "master-tab master-tab-active" : "master-tab"} onClick={() => setKind(key)}>{text}<span>{resources[key].length}</span></button>)}</div>
        <div className="page-actions"><button className="button button-secondary" onClick={() => void reload()} disabled={loading}><RefreshCw className={loading ? "spin" : ""} />刷新</button><BulkDataActions resourceKey={`material-governance.${kind}`} resourceLabel={kindName(kind)} disabled={loading || submitting} onImported={reload} onResult={bulkResult} /><button className="button button-primary" onClick={() => open()}><Plus />新建{kindName(kind)}</button></div>
      </div>
      <div className="master-table-wrap">
        <table className="master-table governance-table material-governance-table">
          <thead><tr><th>编号 / 名称</th><th>受控关系</th><th>状态</th><th>规格、方法与追溯</th><th>操作</th></tr></thead>
          <tbody>{resources[kind].map((row) => <tr key={row.id}><td><strong>{primary(row)}</strong><small>{row.name ?? row.description ?? row.remark ?? "—"}</small></td><td>{relation(kind, row, maps)}</td><td><span className={`status-badge ${row.reliability_status === "FAILED" ? "status-danger" : ""}`}>{row.reliability_status ? reliabilityLabel(row.reliability_status) : row.status ? statusLabel(row.status) : "受控"}</span></td><td>{detail(kind, row)}</td><td><div className="row-actions"><button className="icon-button" onClick={() => open(row)} aria-label={`编辑${kindName(kind)}`}><Pencil /></button><button className="icon-button icon-button-danger" onClick={() => void remove(row)} aria-label={`删除${kindName(kind)}`}><Trash2 /></button></div></td></tr>)}</tbody>
        </table>
        {!resources[kind].length ? <div className="large-empty"><FlaskConical />暂无{kindName(kind)}，自由 COA 字段不会进入批准 AI 特征。</div> : null}
      </div>
      {modal ? <ModalShell className="quality-modal" eyebrow="材料特性" title={`${modal === "new" ? "新建" : "编辑"}${kindName(kind)}`} description="统一维护材料特性、方法、规格、适用关系和结果的治理弹窗结构。" onClose={closeModal} busy={submitting}><form onSubmit={submit}><div className="form-grid">{renderFields(kind, form, setForm, resources, materials)}</div><div className="modal-actions"><button type="button" className="button button-secondary" onClick={closeModal} disabled={submitting}>取消</button><button className="button button-primary" disabled={submitting}>{submitting ? <LoaderCircle className="spin" aria-hidden="true" /> : null}{submitting ? "正在保存" : "保存"}</button></div></form></ModalShell> : null}
    </div>
  );
}

function kindName(kind: Kind): string {
  return kinds.find(([key]) => key === kind)?.[1] ?? kind;
}

function primary(row: Resource): string {
  return row.result_no ?? (row.material_code && row.version ? `${row.material_code}:${row.version}` : row.code && row.version ? `${row.code}:${row.version}` : row.code ?? row.id.slice(0, 12));
}

function relation(kind: Kind, row: Resource, maps: { definitions: Map<string, Resource>; methods: Map<string, Resource>; materials: Map<string, MaterialBatch> }): string {
  if (kind === "definitions") {
    const families = (row.target_families ?? []).map((item) => qualityTypeLabel(item));
    return families.length ? families.join(" / ") : "—";
  }
  if (kind === "methods") return maps.definitions.get(row.characteristic_definition_id ?? "")?.name ?? "未知特性";
  if (kind === "specifications") return `${row.material_code} · ${maps.definitions.get(row.characteristic_definition_id ?? "")?.name ?? "未知特性"} · ${maps.methods.get(row.method_id ?? "")?.code ?? "未知方法"}`;
  if (kind === "applicabilities") return `${materialTypeLabel(row.material_type)} · ${stageLabel(row.process_stage)} · ${qualityTypeLabel(row.target_family)}`;
  const batch = maps.materials.get(row.material_batch_id ?? "");
  return `${batch?.batch_no ?? "未知批次"} · ${maps.definitions.get(row.characteristic_definition_id ?? "")?.name ?? "未知特性"}`;
}

function detail(kind: Kind, row: Resource): string {
  if (kind === "definitions") return `${row.category} · ${row.canonical_unit} · ${row.is_model_feature ? "允许进入模型" : "仅追溯"}`;
  if (kind === "methods") return `${row.method_type} · ${row.result_unit} · ${row.procedure_uri ?? "规程来源待维护"}`;
  if (kind === "specifications") return `${row.lower_limit ?? "—"} ~ ${row.upper_limit ?? "—"} · ${row.source_uri ?? "来源待维护"}`;
  if (kind === "applicabilities") return `${row.is_required ? "必需特性" : "可选特性"} · 审批人 ${row.approved_by ?? "待维护"}`;
  return `${row.result_value} ${row.unit} · ${row.tested_at ? new Date(row.tested_at).toLocaleString("zh-CN") : "时间待维护"} · ${(row.reliability_issues ?? []).join("；") || "可靠性通过"}`;
}

function initialForm(kind: Kind, row?: Resource): FormState {
  if (kind === "definitions") return { code: row?.code ?? "", name: row?.name ?? "", category: row?.category ?? "VISCOSITY_RHEOLOGY", canonical_unit: row?.canonical_unit ?? "", target_families: (row?.target_families ?? ["ORANGE_PEEL"]).join(","), is_model_feature: row?.is_model_feature ?? true, status: row?.status ?? "ACTIVE", description: row?.description ?? "" };
  if (kind === "methods") return { characteristic_definition_id: row?.characteristic_definition_id ?? "", code: row?.code ?? "", name: row?.name ?? "", version: row?.version ?? "1.0", method_type: row?.method_type ?? "", result_unit: row?.result_unit ?? "", procedure_uri: row?.procedure_uri ?? "", conditions: JSON.stringify(row?.conditions ?? {}, null, 2), status: row?.status ?? "ACTIVE", remark: row?.remark ?? "" };
  if (kind === "specifications") return { material_code: row?.material_code ?? "", characteristic_definition_id: row?.characteristic_definition_id ?? "", method_id: row?.method_id ?? "", version: row?.version ?? "1.0", lower_limit: row?.lower_limit == null ? "" : String(row.lower_limit), upper_limit: row?.upper_limit == null ? "" : String(row.upper_limit), status: row?.status ?? "DRAFT", source_uri: row?.source_uri ?? "", effective_from: row?.effective_from ? localDateTime(row.effective_from) : "", effective_to: row?.effective_to ? localDateTime(row.effective_to) : "", approved_by: row?.approved_by ?? "", remark: row?.remark ?? "" };
  if (kind === "applicabilities") return { characteristic_definition_id: row?.characteristic_definition_id ?? "", material_type: row?.material_type ?? "CLEARCOAT", process_stage: row?.process_stage ?? "CLEARCOAT_2", target_family: row?.target_family ?? "ORANGE_PEEL", is_required: row?.is_required ?? false, status: row?.status ?? "DRAFT", approved_by: row?.approved_by ?? "", remark: row?.remark ?? "" };
  return { result_no: row?.result_no ?? `MAT-${Date.now()}`, material_batch_id: row?.material_batch_id ?? "", characteristic_definition_id: row?.characteristic_definition_id ?? "", method_id: row?.method_id ?? "", result_value: row?.result_value == null ? "" : String(row.result_value), unit: row?.unit ?? "", tested_at: localDateTime(row?.tested_at), tested_by: row?.tested_by ?? "", source_uri: row?.source_uri ?? "", raw_values: JSON.stringify(row?.raw_values ?? {}, null, 2), remark: row?.remark ?? "" };
}

function buildBody(kind: Kind, form: FormState): Record<string, unknown> {
  const body: Record<string, unknown> = { ...form };
  for (const key of ["description", "procedure_uri", "source_uri", "effective_from", "effective_to", "approved_by", "tested_by", "remark"]) if (body[key] === "") body[key] = null;
  for (const key of ["lower_limit", "upper_limit", "result_value"]) if (body[key] !== undefined) body[key] = body[key] === "" ? null : Number(body[key]);
  if (kind === "definitions") body.target_families = String(form.target_families).split(",").map((item) => item.trim()).filter(Boolean);
  if (kind === "methods") body.conditions = jsonObject(String(form.conditions), "检测条件");
  if (kind === "results") body.raw_values = jsonObject(String(form.raw_values), "原始结果");
  return body;
}

function input(text: string, key: string, form: FormState, setForm: (form: FormState) => void, type = "text", required = false) {
  return <label className="form-field" key={key}><span>{text}{required ? <b>*</b> : null}</span><input required={required} type={type} step={type === "number" ? "any" : undefined} value={String(form[key] ?? "")} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>;
}
function select(text: string, key: string, form: FormState, setForm: (form: FormState) => void, choices: Array<[string, string]>) {
  return <label className="form-field" key={key}><span>{text}<b>*</b></span><select required value={String(form[key] ?? "")} onChange={(event) => setForm({ ...form, [key]: event.target.value })}>{choices.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>;
}
function checkbox(text: string, key: string, form: FormState, setForm: (form: FormState) => void) {
  return <label className="form-field" key={key}><span>{text}</span><span className="checkbox-field"><input type="checkbox" checked={Boolean(form[key])} onChange={(event) => setForm({ ...form, [key]: event.target.checked })} />{text}</span></label>;
}
function textarea(text: string, key: string, form: FormState, setForm: (form: FormState) => void) {
  return <label className="form-field form-field-wide" key={key}><span>{text}</span><textarea rows={5} value={String(form[key] ?? "")} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>;
}

function renderFields(kind: Kind, form: FormState, setForm: (form: FormState) => void, resources: Record<Kind, Resource[]>, materials: MaterialBatch[]) {
  const definitions = resources.definitions.map((item) => [item.id, `${item.code} / ${item.name}`] as [string, string]);
  const methods = resources.methods.map((item) => [item.id, `${item.code}:${item.version} / ${item.name}`] as [string, string]);
  if (kind === "definitions") return [input("特性代码", "code", form, setForm, "text", true), input("特性名称", "name", form, setForm, "text", true), select("类别", "category", form, setForm, [["VISCOSITY_RHEOLOGY", "粘度/流变"], ["SOLIDS", "固含"], ["DENSITY", "密度"], ["PIGMENT_EFFECT", "颜料/效应"], ["LEVELING_SURFACE", "流平/表面"]]), input("规范单位", "canonical_unit", form, setForm, "text", true), input("批准目标族（逗号分隔）", "target_families", form, setForm, "text", true), select("状态", "status", form, setForm, [["ACTIVE", "生效"], ["RETIRED", "退役"]]), checkbox("允许进入模型", "is_model_feature", form, setForm), textarea("定义说明", "description", form, setForm)];
  if (kind === "methods") return [select("材料特性", "characteristic_definition_id", form, setForm, definitions), input("方法代码", "code", form, setForm, "text", true), input("方法名称", "name", form, setForm, "text", true), input("版本", "version", form, setForm, "text", true), input("方法类型", "method_type", form, setForm, "text", true), input("结果单位", "result_unit", form, setForm, "text", true), input("规程来源 URI", "procedure_uri", form, setForm), select("状态", "status", form, setForm, [["ACTIVE", "生效"], ["RETIRED", "退役"]]), <label className="form-field form-field-wide" key="conditions"><span>检测条件明细</span><JsonObjectEditor value={String(form.conditions ?? "")} onChange={(value) => setForm({ ...form, conditions: value })} keyLabel="条件项" valueLabel="条件值" addLabel="新增条件" /></label>, textarea("备注", "remark", form, setForm)];
  if (kind === "specifications") return [select("材料代码", "material_code", form, setForm, Array.from(new Set(materials.map((item) => item.material_code))).map((code) => [code, code])), select("材料特性", "characteristic_definition_id", form, setForm, definitions), select("检测方法", "method_id", form, setForm, methods), input("规格版本", "version", form, setForm, "text", true), input("下限", "lower_limit", form, setForm, "number"), input("上限", "upper_limit", form, setForm, "number"), select("状态", "status", form, setForm, statusOptions), input("规格来源 URI", "source_uri", form, setForm), input("有效开始", "effective_from", form, setForm, "datetime-local"), input("有效截止", "effective_to", form, setForm, "datetime-local"), input("审批人", "approved_by", form, setForm), textarea("备注", "remark", form, setForm)];
  if (kind === "applicabilities") return [select("材料特性", "characteristic_definition_id", form, setForm, definitions), select("材料类型", "material_type", form, setForm, [["MIDCOAT", "中涂"], ["BASECOAT", "色漆"], ["CLEARCOAT", "清漆"]]), select("执行工序", "process_stage", form, setForm, stageOptions), select("质量目标族", "target_family", form, setForm, qualityOptions), checkbox("该工序/目标族必需", "is_required", form, setForm), select("状态", "status", form, setForm, statusOptions), input("审批人", "approved_by", form, setForm), textarea("备注", "remark", form, setForm)];
  return [input("结果编号", "result_no", form, setForm, "text", true), select("材料批次", "material_batch_id", form, setForm, materials.map((item) => [item.id, `${item.batch_no} / ${item.material_name}`])), select("材料特性", "characteristic_definition_id", form, setForm, definitions), select("检测方法", "method_id", form, setForm, methods), input("结果值", "result_value", form, setForm, "number", true), input("单位", "unit", form, setForm, "text", true), input("检测时间", "tested_at", form, setForm, "datetime-local", true), input("检测人", "tested_by", form, setForm), input("来源文件 URI", "source_uri", form, setForm), <label className="form-field form-field-wide" key="raw_values"><span>原始结果明细</span><JsonObjectEditor value={String(form.raw_values ?? "")} onChange={(value) => setForm({ ...form, raw_values: value })} keyLabel="原始项" valueLabel="原始值" addLabel="新增原始项" /></label>, textarea("备注", "remark", form, setForm)];
}
