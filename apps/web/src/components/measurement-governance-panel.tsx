"use client";

import { LoaderCircle, Pencil, Plus, RefreshCw, ShieldCheck, Trash2, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { BulkDataActions } from "@/components/bulk-data-actions";
import { ModalShell } from "@/components/modal-shell";
import { JsonObjectEditor } from "@/components/structured-json-editor";
import { physicalDeleteDisabledMessage } from "@/lib/delete-policy";

type Kind = "instruments" | "methods" | "references" | "calibrations" | "import-profiles";
type FormState = Record<string, string | boolean>;
type GovernanceResource = {
  id: string;
  code?: string;
  name?: string;
  version?: string;
  status?: string;
  is_active?: boolean;
  instrument_type?: string;
  quality_type?: string;
  serial_no?: string;
  calibration_no?: string;
  instrument_id?: string;
  method_id?: string | null;
  reference_standard_id?: string | null;
  calibrated_at?: string;
  valid_until?: string;
  result?: string;
  supported_quality_types?: string[];
  schema_version?: string;
  manufacturer?: string;
  model?: string;
  firmware_version?: string | null;
  calibration_required?: boolean;
  method_type?: string;
  probe_code?: string | null;
  substrate_type?: string | null;
  geometry_class?: string | null;
  layer_scope?: string | null;
  requires_reference?: boolean;
  requires_direction?: boolean;
  minimum_repeats?: number;
  performed_by?: string;
  certificate_no?: string | null;
  valid_from?: string | null;
  reference_values?: Record<string, unknown> | null;
  check_values?: Record<string, unknown> | null;
  field_mapping?: Record<string, unknown>;
};
type Summary = {
  instruments: number;
  active_instruments: number;
  methods: number;
  references: number;
  calibrations: number;
  valid_calibrations: number;
  import_profiles: number;
};

const kindLabels: Record<Kind, string> = {
  instruments: "测量仪器",
  methods: "测量方法",
  references: "参考件",
  calibrations: "校准/检查",
  "import-profiles": "导入模板",
};
const qualityOptions = [["ORANGE_PEEL", "橘皮"], ["COLOR_DIFFERENCE", "色差/效应"], ["THICKNESS", "膜厚"]] as const;
const instrumentOptions = [["BYK_ORANGE_PEEL", "BYK 橘皮仪"], ["BYK_COLOR", "BYK 色差仪"], ["FISCHER_THICKNESS", "Fischer 膜厚仪"]] as const;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new Error(payload.error ?? `请求失败（${response.status}）`);
  return payload;
}

function localDateTime(value?: string): string {
  const date = value ? new Date(value) : new Date();
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function jsonValue(value: string, label: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(value || "{}") as unknown;
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") throw new Error();
    return parsed as Record<string, unknown>;
  } catch {
    throw new Error(`${label}必须是 JSON 对象`);
  }
}

export function MeasurementGovernancePanel() {
  const [kind, setKind] = useState<Kind>("instruments");
  const [resources, setResources] = useState<Record<Kind, GovernanceResource[]>>({
    instruments: [], methods: [], references: [], calibrations: [], "import-profiles": [],
  });
  const [summary, setSummary] = useState<Summary | null>(null);
  const [modal, setModal] = useState<GovernanceResource | "new" | null>(null);
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
      const [nextSummary, instruments, methods, references, calibrations, profiles] = await Promise.all([
        request<Summary>("/api/quality/governance/summary"),
        request<GovernanceResource[]>("/api/quality/governance/instruments"),
        request<GovernanceResource[]>("/api/quality/governance/methods"),
        request<GovernanceResource[]>("/api/quality/governance/references"),
        request<GovernanceResource[]>("/api/quality/governance/calibrations"),
        request<GovernanceResource[]>("/api/quality/governance/import-profiles"),
      ]);
      setSummary(nextSummary);
      setResources({ instruments, methods, references, calibrations, "import-profiles": profiles });
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "仪器治理数据加载失败" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  const rows = resources[kind];
  const lookup = useMemo(() => ({
    instruments: new Map(resources.instruments.map((item) => [item.id, item])),
    methods: new Map(resources.methods.map((item) => [item.id, item])),
    references: new Map(resources.references.map((item) => [item.id, item])),
  }), [resources]);

  function open(record?: GovernanceResource) {
    setModal(record ?? "new");
    setForm(initialForm(kind, record));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!modal) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const body = buildBody(kind, form);
      const editing = modal !== "new";
      await request(`/api/quality/governance/${kind}${editing ? `/${modal.id}` : ""}`, {
        method: editing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setMessage({ type: "success", text: `${kindLabels[kind]}已${editing ? "更新" : "创建"}` });
      setModal(null);
      await reload();
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "保存失败" });
    } finally {
      setSubmitting(false);
    }
  }

  function remove(_record: GovernanceResource) {
    void _record;
    setMessage({ type: "error", text: `${kindLabels[kind]}不能物理删除。${physicalDeleteDisabledMessage}` });
  }

  function bulkResult(message: string, type: "success" | "error") {
    setMessage({ type, text: message });
  }

  return (
    <div className="measurement-governance">
      {message ? <button className={`message-banner message-${message.type}`} onClick={() => setMessage(null)}>{message.text}<X /></button> : null}
      <section className="quality-analytics-stat-grid">
        <article><span>仪器 / 在用</span><strong>{summary?.instruments ?? 0} / {summary?.active_instruments ?? 0}</strong><small>BYK 与 Fischer 受治理设备</small></article>
        <article><span>方法 / 参考件</span><strong>{summary?.methods ?? 0} / {summary?.references ?? 0}</strong><small>版本化方法与参考状态</small></article>
        <article><span>有效校准</span><strong>{summary?.valid_calibrations ?? 0} / {summary?.calibrations ?? 0}</strong><small>PASS 且未过期</small></article>
        <article><span>导入模板</span><strong>{summary?.import_profiles ?? 0}</strong><small>固件/导出结构映射</small></article>
      </section>
      <div className="governance-toolbar">
        <div className="master-tabs">
          {(Object.keys(kindLabels) as Kind[]).map((item) => <button key={item} className={kind === item ? "master-tab master-tab-active" : "master-tab"} onClick={() => setKind(item)}>{kindLabels[item]} <span>{resources[item].length}</span></button>)}
        </div>
        <div className="page-actions"><button className="button button-secondary" onClick={() => void reload()} disabled={loading}><RefreshCw className={loading ? "spin" : ""} />刷新</button><BulkDataActions resourceKey={`measurement-governance.${kind}`} resourceLabel={kindLabels[kind]} disabled={loading || submitting} onImported={reload} onResult={bulkResult} /><button className="button button-primary" onClick={() => open()}><Plus />新建{kindLabels[kind]}</button></div>
      </div>
      <div className="master-table-wrap">
        <table className="master-table governance-table">
          <thead><tr><th>编号 / 名称</th><th>类型与适用范围</th><th>版本 / 有效性</th><th>追溯详情</th><th>操作</th></tr></thead>
          <tbody>{rows.map((row) => <tr key={row.id}>
            <td><strong>{row.calibration_no ?? row.code}</strong><small>{row.name ?? row.performed_by ?? "—"}</small></td>
            <td>{row.instrument_type ?? row.quality_type ?? lookup.instruments.get(row.instrument_id ?? "")?.name ?? "—"}</td>
            <td>{row.version ?? row.result ?? row.status ?? (row.is_active ? "ACTIVE" : "INACTIVE")}</td>
            <td>{governanceDetail(kind, row, lookup)}</td>
            <td><div className="row-actions"><button className="icon-button" onClick={() => open(row)} aria-label={`编辑${kindLabels[kind]}`}><Pencil /></button><button className="icon-button icon-button-danger" onClick={() => void remove(row)} aria-label={`删除${kindLabels[kind]}`}><Trash2 /></button></div></td>
          </tr>)}</tbody>
        </table>
        {!rows.length ? <div className="large-empty"><ShieldCheck />暂无{kindLabels[kind]}，可靠性门禁会将相关测量标记为未验证</div> : null}
      </div>
      {modal ? <ModalShell className="quality-modal" eyebrow="MEASUREMENT GOVERNANCE" title={`${modal === "new" ? "新建" : "编辑"}${kindLabels[kind]}`} description="统一维护仪器、方法、参考件、校准和导入模板的治理弹窗结构。" onClose={closeModal} busy={submitting}><form onSubmit={submit}><div className="form-grid">{renderFields(kind, form, setForm, resources)}</div><div className="modal-actions"><button type="button" className="button button-secondary" onClick={closeModal} disabled={submitting}>取消</button><button className="button button-primary" disabled={submitting}>{submitting ? <LoaderCircle className="spin" aria-hidden="true" /> : null}{submitting ? "正在保存" : "保存到 MySQL"}</button></div></form></ModalShell> : null}
    </div>
  );
}

function governanceDetail(kind: Kind, row: GovernanceResource, lookup: { instruments: Map<string, GovernanceResource>; methods: Map<string, GovernanceResource>; references: Map<string, GovernanceResource> }): string {
  if (kind === "instruments") return `${row.manufacturer} ${row.model} · SN ${row.serial_no} · FW ${row.firmware_version ?? "—"}`;
  if (kind === "methods") return `${row.method_type} · 重复 ${row.minimum_repeats} · ${row.requires_reference ? "需参考件" : "无需参考件"}`;
  if (kind === "references") return `SN ${row.serial_no ?? "—"} · 有效至 ${row.valid_until ? new Date(row.valid_until).toLocaleDateString("zh-CN") : "未限制"}`;
  if (kind === "calibrations") return `${lookup.instruments.get(row.instrument_id ?? "")?.code ?? "未知仪器"} · ${lookup.methods.get(row.method_id ?? "")?.code ?? "通用检查"} · 有效至 ${row.valid_until ? new Date(row.valid_until).toLocaleString("zh-CN") : "—"}`;
  return `${row.schema_version} · ${row.quality_type}`;
}

function initialForm(kind: Kind, record?: GovernanceResource): FormState {
  if (kind === "instruments") return { code: record?.code ?? "", name: record?.name ?? "", manufacturer: record?.manufacturer ?? "", model: record?.model ?? "", instrument_type: record?.instrument_type ?? "BYK_ORANGE_PEEL", serial_no: record?.serial_no ?? "", firmware_version: record?.firmware_version ?? "", supported_quality_types: (record?.supported_quality_types ?? ["ORANGE_PEEL"]).join(","), calibration_required: record?.calibration_required ?? true, status: record?.status ?? "ACTIVE" };
  if (kind === "methods") return { code: record?.code ?? "", name: record?.name ?? "", version: record?.version ?? "1.0", quality_type: record?.quality_type ?? "ORANGE_PEEL", instrument_type: record?.instrument_type ?? "BYK_ORANGE_PEEL", method_type: record?.method_type ?? "WAVE_SCAN", probe_code: record?.probe_code ?? "", substrate_type: record?.substrate_type ?? "", geometry_class: record?.geometry_class ?? "", layer_scope: record?.layer_scope ?? "", requires_reference: record?.requires_reference ?? true, requires_direction: record?.requires_direction ?? true, minimum_repeats: String(record?.minimum_repeats ?? 1), is_active: record?.is_active ?? true };
  if (kind === "references") return { code: record?.code ?? "", name: record?.name ?? "", quality_type: record?.quality_type ?? "ORANGE_PEEL", serial_no: record?.serial_no ?? "", certificate_no: record?.certificate_no ?? "", valid_from: localDateTime(record?.valid_from ?? undefined), valid_until: localDateTime(record?.valid_until ?? new Date(Date.now() + 365 * 86400000).toISOString()), reference_values: JSON.stringify(record?.reference_values ?? {}, null, 2), status: record?.status ?? "ACTIVE" };
  if (kind === "calibrations") return { calibration_no: record?.calibration_no ?? "", instrument_id: record?.instrument_id ?? "", method_id: record?.method_id ?? "", reference_standard_id: record?.reference_standard_id ?? "", calibrated_at: localDateTime(record?.calibrated_at), valid_until: localDateTime(record?.valid_until ? record.valid_until : new Date(Date.now() + 30 * 86400000).toISOString()), result: record?.result ?? "PASS", performed_by: record?.performed_by ?? "", check_values: JSON.stringify(record?.check_values ?? {}, null, 2) };
  return { code: record?.code ?? "", name: record?.name ?? "", version: record?.version ?? "1.0", instrument_type: record?.instrument_type ?? "BYK_ORANGE_PEEL", quality_type: record?.quality_type ?? "ORANGE_PEEL", schema_version: record?.schema_version ?? "1.0", field_mapping: JSON.stringify(record?.field_mapping ?? {}, null, 2), is_active: record?.is_active ?? true };
}

function buildBody(kind: Kind, form: FormState): Record<string, unknown> {
  const body: Record<string, unknown> = { ...form };
  for (const key of ["firmware_version", "probe_code", "substrate_type", "geometry_class", "layer_scope", "serial_no", "certificate_no", "method_id", "reference_standard_id", "valid_from", "valid_until"]) if (body[key] === "") body[key] = null;
  if (kind === "instruments") body.supported_quality_types = String(form.supported_quality_types).split(",").map((item) => item.trim()).filter(Boolean);
  if (kind === "methods") body.minimum_repeats = Number(form.minimum_repeats);
  if (kind === "references") body.reference_values = jsonValue(String(form.reference_values), "参考值");
  if (kind === "calibrations") body.check_values = jsonValue(String(form.check_values), "检查值");
  if (kind === "import-profiles") body.field_mapping = jsonValue(String(form.field_mapping), "字段映射");
  return body;
}

function input(label: string, key: string, form: FormState, setForm: (value: FormState) => void, type = "text", required = false) {
  return <label className="form-field" key={key}><span>{label}{required ? <b>*</b> : null}</span><input type={type} required={required} value={String(form[key] ?? "")} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>;
}
function select(label: string, key: string, form: FormState, setForm: (value: FormState) => void, choices: readonly (readonly [string, string])[], required = true) {
  return <label className="form-field" key={key}><span>{label}{required ? <b>*</b> : null}</span><select required={required} value={String(form[key] ?? "")} onChange={(event) => setForm({ ...form, [key]: event.target.value })}>{!required ? <option value="">未关联</option> : null}{choices.map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></label>;
}
function checkbox(label: string, key: string, form: FormState, setForm: (value: FormState) => void) {
  return <label className="form-field" key={key}><span>{label}</span><span className="checkbox-field"><input type="checkbox" checked={Boolean(form[key])} onChange={(event) => setForm({ ...form, [key]: event.target.checked })} />{label}</span></label>;
}

function renderFields(kind: Kind, form: FormState, setForm: (value: FormState) => void, resources: Record<Kind, GovernanceResource[]>) {
  if (kind === "instruments") return [input("仪器代码", "code", form, setForm, "text", true), input("仪器名称", "name", form, setForm, "text", true), input("制造商", "manufacturer", form, setForm, "text", true), input("型号", "model", form, setForm, "text", true), select("仪器类型", "instrument_type", form, setForm, instrumentOptions), input("序列号", "serial_no", form, setForm, "text", true), input("固件版本", "firmware_version", form, setForm), input("支持质量类型（逗号分隔）", "supported_quality_types", form, setForm, "text", true), select("状态", "status", form, setForm, [["ACTIVE", "在用"], ["MAINTENANCE", "维护"], ["RETIRED", "退役"]]), checkbox("需要校准/检查", "calibration_required", form, setForm)];
  if (kind === "methods") return [input("方法代码", "code", form, setForm, "text", true), input("方法名称", "name", form, setForm, "text", true), input("版本", "version", form, setForm, "text", true), select("质量类型", "quality_type", form, setForm, qualityOptions), select("仪器类型", "instrument_type", form, setForm, instrumentOptions), input("方法类型", "method_type", form, setForm, "text", true), input("探头代码", "probe_code", form, setForm), input("基材类型", "substrate_type", form, setForm), input("几何类别", "geometry_class", form, setForm), input("层范围", "layer_scope", form, setForm), input("最少重复次数", "minimum_repeats", form, setForm, "number", true), checkbox("需要参考件", "requires_reference", form, setForm), checkbox("需要测量方向", "requires_direction", form, setForm), checkbox("方法生效", "is_active", form, setForm)];
  if (kind === "references") return [input("参考件代码", "code", form, setForm, "text", true), input("参考件名称", "name", form, setForm, "text", true), select("质量类型", "quality_type", form, setForm, qualityOptions), input("序列号", "serial_no", form, setForm), input("证书编号", "certificate_no", form, setForm), input("有效开始", "valid_from", form, setForm, "datetime-local"), input("有效截止", "valid_until", form, setForm, "datetime-local"), select("状态", "status", form, setForm, [["ACTIVE", "在用"], ["EXPIRED", "过期"], ["RETIRED", "退役"]]), <label className="form-field form-field-wide" key="reference_values"><span>参考指标明细</span><JsonObjectEditor value={String(form.reference_values ?? "")} onChange={(value) => setForm({ ...form, reference_values: value })} keyLabel="指标代码" valueLabel="参考值" addLabel="新增参考项" /></label>];
  if (kind === "calibrations") return [input("校准/检查编号", "calibration_no", form, setForm, "text", true), select("仪器", "instrument_id", form, setForm, resources.instruments.map((item) => [item.id, `${item.code} / ${item.name}`])), select("方法", "method_id", form, setForm, resources.methods.map((item) => [item.id, `${item.code}:${item.version}`]), false), select("参考件", "reference_standard_id", form, setForm, resources.references.map((item) => [item.id, `${item.code} / ${item.name}`]), false), input("校准/检查时间", "calibrated_at", form, setForm, "datetime-local", true), input("有效截止", "valid_until", form, setForm, "datetime-local", true), select("结果", "result", form, setForm, [["PASS", "通过"], ["FAIL", "失败"]]), input("执行人", "performed_by", form, setForm, "text", true), <label className="form-field form-field-wide" key="check_values"><span>检查记录明细</span><JsonObjectEditor value={String(form.check_values ?? "")} onChange={(value) => setForm({ ...form, check_values: value })} keyLabel="检查项" valueLabel="结果值" addLabel="新增检查项" /></label>];
  return [input("模板代码", "code", form, setForm, "text", true), input("模板名称", "name", form, setForm, "text", true), input("版本", "version", form, setForm, "text", true), select("仪器类型", "instrument_type", form, setForm, instrumentOptions), select("质量类型", "quality_type", form, setForm, qualityOptions), input("导出结构版本", "schema_version", form, setForm, "text", true), checkbox("模板生效", "is_active", form, setForm), <label className="form-field form-field-wide" key="field_mapping"><span>导入列映射</span><JsonObjectEditor value={String(form.field_mapping ?? "")} onChange={(value) => setForm({ ...form, field_mapping: value })} keyLabel="源列名" valueLabel="目标字段" addLabel="新增映射" /></label>];
}
