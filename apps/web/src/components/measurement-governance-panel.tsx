"use client";

import { LoaderCircle, Pencil, Plus, RefreshCw, ShieldCheck, Trash2, X } from "lucide-react";
import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import { BulkDataActions } from "@/components/bulk-data-actions";
import { ModalShell } from "@/components/modal-shell";
import { JsonObjectEditor } from "@/components/structured-json-editor";
import { physicalDeleteDisabledMessage } from "@/lib/delete-policy";
import { qualityTypeLabel, statusLabel } from "@/lib/display-labels";

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
type ScopeState = {
  instrumentType: string;
  qualityType: string;
};

const KIND_ORDER: Kind[] = ["instruments", "methods", "references", "calibrations", "import-profiles"];

const kindLabels: Record<Kind, string> = {
  instruments: "1. 仪器台账",
  methods: "2. 测量方法",
  references: "3. 参考件",
  calibrations: "4. 校准记录",
  "import-profiles": "5. 导入模板",
};

const kindHints: Record<Kind, string> = {
  instruments: "先建仪器。后续方法、校准、导入模板都按仪器类型继承。",
  methods: "方法挂在仪器类型 + 质量类型下；会自动带出默认方法类型。",
  references: "参考件按质量类型维护；校准和方法需要时可关联。",
  calibrations: "校准必须选仪器；方法/参考件按仪器类型与质量类型自动过滤并预填。",
  "import-profiles": "导入模板按仪器类型 + 质量类型配置导出列映射。",
};

const qualityOptions = [
  ["ORANGE_PEEL", "橘皮"],
  ["COLOR_DIFFERENCE", "色差/效应"],
  ["THICKNESS", "膜厚"],
] as const;

const instrumentOptions = [
  ["BYK_ORANGE_PEEL", "BYK 橘皮仪"],
  ["BYK_COLOR", "BYK 色差仪"],
  ["FISCHER_THICKNESS", "Fischer 膜厚仪"],
] as const;

const methodTypeOptions = [
  ["WAVE_SCAN", "波纹扫描（橘皮）"],
  ["MULTI_ANGLE_COLOR", "多角度色差/效应"],
  ["MAGNETIC_INDUCTION", "磁感应膜厚"],
  ["EDDY_CURRENT", "涡流膜厚"],
] as const;

const INSTRUMENT_TYPE_LABELS: Record<string, string> = Object.fromEntries(instrumentOptions);
const METHOD_TYPE_LABELS: Record<string, string> = Object.fromEntries(methodTypeOptions);
const QUALITY_BY_INSTRUMENT: Record<string, string> = {
  BYK_ORANGE_PEEL: "ORANGE_PEEL",
  BYK_COLOR: "COLOR_DIFFERENCE",
  FISCHER_THICKNESS: "THICKNESS",
};

function defaultMethodType(instrumentType: string, qualityType: string): string {
  if (instrumentType === "BYK_COLOR" || qualityType === "COLOR_DIFFERENCE") return "MULTI_ANGLE_COLOR";
  if (instrumentType === "FISCHER_THICKNESS" || qualityType === "THICKNESS") return "MAGNETIC_INDUCTION";
  return "WAVE_SCAN";
}

function defaultQualityForInstrument(instrumentType: string): string {
  return QUALITY_BY_INSTRUMENT[instrumentType] ?? "ORANGE_PEEL";
}

function instrumentTypeLabel(code: string | null | undefined): string {
  if (!code) return "—";
  return INSTRUMENT_TYPE_LABELS[code] ?? statusLabel(code);
}

function versionValidityLabel(row: GovernanceResource): string {
  if (row.version) return row.version;
  if (row.result) return statusLabel(row.result);
  if (row.status) return statusLabel(row.status);
  return statusLabel(row.is_active ? "ACTIVE" : "INACTIVE");
}

function typeScopeLabel(row: GovernanceResource, lookup: { instruments: Map<string, GovernanceResource> }): string {
  if (row.instrument_type) return instrumentTypeLabel(row.instrument_type);
  if (row.quality_type) return qualityTypeLabel(row.quality_type);
  return lookup.instruments.get(row.instrument_id ?? "")?.name ?? "—";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => ({}))) as T & { error?: string; detail?: string };
  if (!response.ok) throw new Error(payload.detail ?? payload.error ?? `请求失败（${response.status}）`);
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
    throw new Error(`${label}中的分项内容格式不正确`);
  }
}

function parseSupportedQualityTypes(value: string | boolean | undefined): string[] {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function MeasurementGovernancePanel() {
  const [kind, setKind] = useState<Kind>("instruments");
  const [scope, setScope] = useState<ScopeState>({
    instrumentType: "BYK_ORANGE_PEEL",
    qualityType: "ORANGE_PEEL",
  });
  const [resources, setResources] = useState<Record<Kind, GovernanceResource[]>>({
    instruments: [],
    methods: [],
    references: [],
    calibrations: [],
    "import-profiles": [],
  });
  const [summary, setSummary] = useState<Summary | null>(null);
  const [modal, setModal] = useState<GovernanceResource | "new" | null>(null);
  const [form, setForm] = useState<FormState>({});
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "error" | "success"; text: string } | null>(null);

  const closeModal = useCallback(() => {
    if (submitting) return;
    setModal(null);
    setFormError("");
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

  const lookup = useMemo(
    () => ({
      instruments: new Map(resources.instruments.map((item) => [item.id, item])),
      methods: new Map(resources.methods.map((item) => [item.id, item])),
      references: new Map(resources.references.map((item) => [item.id, item])),
    }),
    [resources],
  );

  const filteredRows = useMemo(() => {
    const rows = resources[kind];
    return rows.filter((row) => {
      if (kind === "instruments") {
        if (scope.instrumentType && row.instrument_type !== scope.instrumentType) return false;
        if (scope.qualityType && !(row.supported_quality_types ?? []).includes(scope.qualityType)) return false;
        return true;
      }
      if (kind === "methods" || kind === "import-profiles") {
        if (scope.instrumentType && row.instrument_type !== scope.instrumentType) return false;
        if (scope.qualityType && row.quality_type !== scope.qualityType) return false;
        return true;
      }
      if (kind === "references") {
        return !scope.qualityType || row.quality_type === scope.qualityType;
      }
      if (kind === "calibrations") {
        const instrument = lookup.instruments.get(row.instrument_id ?? "");
        if (scope.instrumentType && instrument?.instrument_type !== scope.instrumentType) return false;
        if (scope.qualityType) {
          const method = lookup.methods.get(row.method_id ?? "");
          const reference = lookup.references.get(row.reference_standard_id ?? "");
          const quality = method?.quality_type ?? reference?.quality_type;
          if (quality && quality !== scope.qualityType) return false;
          if (!quality && instrument && !(instrument.supported_quality_types ?? []).includes(scope.qualityType)) {
            return false;
          }
        }
        return true;
      }
      return true;
    });
  }, [kind, lookup, resources, scope]);

  function changeScopeInstrument(nextType: string) {
    setScope({
      instrumentType: nextType,
      qualityType: defaultQualityForInstrument(nextType),
    });
  }

  function open(record?: GovernanceResource) {
    setFormError("");
    setModal(record ?? "new");
    setForm(initialForm(kind, scope, resources, record));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!modal) return;
    setSubmitting(true);
    setMessage(null);
    setFormError("");
    try {
      const validationError = validateForm(kind, form, resources, lookup);
      if (validationError) {
        setFormError(validationError);
        return;
      }
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
      setFormError(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  function remove(_record: GovernanceResource) {
    void _record;
    setMessage({ type: "error", text: `${kindLabels[kind]}不能物理删除。${physicalDeleteDisabledMessage}` });
  }

  function bulkResult(text: string, type: "success" | "error") {
    setMessage({ type, text });
  }

  const missingParents = useMemo(() => {
    if (kind === "methods" && !resources.instruments.some((item) => item.instrument_type === scope.instrumentType)) {
      return "当前仪器类型下还没有仪器台账，建议先建仪器。";
    }
    if (kind === "calibrations" && !resources.instruments.length) {
      return "还没有仪器台账，校准记录必须先选择仪器。";
    }
    if (kind === "calibrations" && !resources.instruments.some((item) => item.instrument_type === scope.instrumentType)) {
      return "当前仪器类型下还没有仪器，请先切换范围或新建仪器。";
    }
    return "";
  }, [kind, resources.instruments, scope.instrumentType]);

  return (
    <div className="measurement-governance">
      {message ? (
        <button className={`message-banner message-${message.type}`} onClick={() => setMessage(null)}>
          {message.text}
          <X />
        </button>
      ) : null}

      <section className="quality-analytics-stat-grid">
        <article>
          <span>仪器 / 在用</span>
          <strong>
            {summary?.instruments ?? 0} / {summary?.active_instruments ?? 0}
          </strong>
          <small>BYK 与 Fischer 受治理设备</small>
        </article>
        <article>
          <span>方法 / 参考件</span>
          <strong>
            {summary?.methods ?? 0} / {summary?.references ?? 0}
          </strong>
          <small>版本化方法与参考状态</small>
        </article>
        <article>
          <span>有效校准</span>
          <strong>
            {summary?.valid_calibrations ?? 0} / {summary?.calibrations ?? 0}
          </strong>
          <small>PASS 且未过期</small>
        </article>
        <article>
          <span>导入模板</span>
          <strong>{summary?.import_profiles ?? 0}</strong>
          <small>固件/导出结构映射</small>
        </article>
      </section>

      <div className="governance-scope-bar">
        <div>
          <strong>工作范围</strong>
          <span>先选仪器类型与质量类型；列表会过滤，新建时会按父子关系预填，仍可手动改。</span>
        </div>
        <div className="governance-scope-fields">
          <label className="form-field">
            <span>仪器类型</span>
            <select value={scope.instrumentType} onChange={(event) => changeScopeInstrument(event.target.value)}>
              {instrumentOptions.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>质量类型</span>
            <select
              value={scope.qualityType}
              onChange={(event) => setScope((current) => ({ ...current, qualityType: event.target.value }))}
            >
              {qualityOptions.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="governance-flow-hint">
        <span>建议顺序</span>
        <strong>仪器台账 → 测量方法 → 参考件 → 校准记录 → 导入模板</strong>
        <small>{kindHints[kind]}</small>
      </div>

      <div className="governance-toolbar">
        <div className="master-tabs" role="tablist" aria-label="仪器可靠性步骤">
          {KIND_ORDER.map((item) => (
            <button
              key={item}
              type="button"
              role="tab"
              aria-selected={kind === item}
              className={kind === item ? "master-tab master-tab-active" : "master-tab"}
              onClick={() => setKind(item)}
            >
              {kindLabels[item]} <span>{resources[item].length}</span>
            </button>
          ))}
        </div>
        <div className="page-actions">
          <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
            <RefreshCw className={loading ? "spin" : ""} />
            刷新
          </button>
          <BulkDataActions
            resourceKey={`measurement-governance.${kind}`}
            resourceLabel={kindLabels[kind]}
            disabled={loading || submitting}
            onImported={reload}
            onResult={bulkResult}
          />
          <button className="button button-primary" onClick={() => open()} disabled={Boolean(missingParents) && kind === "calibrations" && !resources.instruments.length}>
            <Plus />
            新建{kindLabels[kind].replace(/^\d+\.\s*/, "")}
          </button>
        </div>
      </div>

      {missingParents ? <div className="governance-prerequisite">{missingParents}</div> : null}

      <div className="master-table-wrap">
        <table className="master-table governance-table">
          <thead>
            <tr>
              <th>编号 / 名称</th>
              <th>类型与适用范围</th>
              <th>版本 / 有效性</th>
              <th>追溯详情</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>{row.calibration_no ?? row.code}</strong>
                  <small>{row.name ?? row.performed_by ?? "—"}</small>
                </td>
                <td>{typeScopeLabel(row, lookup)}</td>
                <td>{versionValidityLabel(row)}</td>
                <td>{governanceDetail(kind, row, lookup)}</td>
                <td>
                  <div className="row-actions">
                    <button className="icon-button" onClick={() => open(row)} aria-label={`编辑${kindLabels[kind]}`}>
                      <Pencil />
                    </button>
                    <button className="icon-button icon-button-danger" onClick={() => void remove(row)} aria-label={`删除${kindLabels[kind]}`}>
                      <Trash2 />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!filteredRows.length ? (
          <div className="large-empty">
            <ShieldCheck />
            {resources[kind].length
              ? `当前工作范围下暂无${kindLabels[kind].replace(/^\d+\.\s*/, "")}，可切换范围或新建。`
              : `暂无${kindLabels[kind].replace(/^\d+\.\s*/, "")}，可靠性门禁会将相关测量标记为未验证`}
          </div>
        ) : null}
      </div>

      {modal ? (
        <ModalShell
          className="quality-modal"
          eyebrow="仪器可靠性"
          title={`${modal === "new" ? "新建" : "编辑"}${kindLabels[kind].replace(/^\d+\.\s*/, "")}`}
          description={kindHints[kind]}
          onClose={closeModal}
          busy={submitting}
        >
          <form onSubmit={(event) => void submit(event)}>
            <div className="form-grid">
              {renderFields(kind, form, setForm, resources, lookup)}
            </div>
            {formError ? <div className="message-banner message-error">{formError}</div> : null}
            <div className="modal-actions">
              <button type="button" className="button button-secondary" onClick={closeModal} disabled={submitting}>
                取消
              </button>
              <button className="button button-primary" disabled={submitting}>
                {submitting ? <LoaderCircle className="spin" aria-hidden="true" /> : null}
                {submitting ? "正在保存" : "保存"}
              </button>
            </div>
          </form>
        </ModalShell>
      ) : null}
    </div>
  );
}

function governanceDetail(
  kind: Kind,
  row: GovernanceResource,
  lookup: { instruments: Map<string, GovernanceResource>; methods: Map<string, GovernanceResource>; references: Map<string, GovernanceResource> },
): string {
  if (kind === "instruments") {
    return `${row.manufacturer} ${row.model} · SN ${row.serial_no} · FW ${row.firmware_version ?? "—"}`;
  }
  if (kind === "methods") {
    return `${METHOD_TYPE_LABELS[row.method_type ?? ""] ?? row.method_type} · 重复 ${row.minimum_repeats} · ${row.requires_reference ? "需参考件" : "无需参考件"}`;
  }
  if (kind === "references") {
    return `SN ${row.serial_no ?? "—"} · 有效至 ${row.valid_until ? new Date(row.valid_until).toLocaleDateString("zh-CN") : "未限制"}`;
  }
  if (kind === "calibrations") {
    return `${lookup.instruments.get(row.instrument_id ?? "")?.code ?? "未知仪器"} · ${lookup.methods.get(row.method_id ?? "")?.code ?? "通用检查"} · 有效至 ${row.valid_until ? new Date(row.valid_until).toLocaleString("zh-CN") : "—"}`;
  }
  return `${row.schema_version} · ${qualityTypeLabel(row.quality_type)}`;
}

function initialForm(
  kind: Kind,
  scope: ScopeState,
  resources: Record<Kind, GovernanceResource[]>,
  record?: GovernanceResource,
): FormState {
  if (kind === "instruments") {
    return {
      code: record?.code ?? "",
      name: record?.name ?? "",
      manufacturer: record?.manufacturer ?? "",
      model: record?.model ?? "",
      instrument_type: record?.instrument_type ?? scope.instrumentType,
      serial_no: record?.serial_no ?? "",
      firmware_version: record?.firmware_version ?? "",
      supported_quality_types: (record?.supported_quality_types ?? [scope.qualityType || defaultQualityForInstrument(scope.instrumentType)]).join(","),
      calibration_required: record?.calibration_required ?? true,
      status: record?.status ?? "ACTIVE",
    };
  }

  if (kind === "methods") {
    const qualityType = record?.quality_type ?? scope.qualityType;
    const instrumentType = record?.instrument_type ?? scope.instrumentType;
    return {
      code: record?.code ?? "",
      name: record?.name ?? "",
      version: record?.version ?? "1.0",
      quality_type: qualityType,
      instrument_type: instrumentType,
      method_type: record?.method_type ?? defaultMethodType(instrumentType, qualityType),
      probe_code: record?.probe_code ?? "",
      substrate_type: record?.substrate_type ?? "",
      geometry_class: record?.geometry_class ?? "",
      layer_scope: record?.layer_scope ?? "",
      requires_reference: record?.requires_reference ?? true,
      requires_direction: record?.requires_direction ?? qualityType !== "THICKNESS",
      minimum_repeats: String(record?.minimum_repeats ?? (qualityType === "THICKNESS" ? 3 : 1)),
      is_active: record?.is_active ?? true,
    };
  }

  if (kind === "references") {
    return {
      code: record?.code ?? "",
      name: record?.name ?? "",
      quality_type: record?.quality_type ?? scope.qualityType,
      serial_no: record?.serial_no ?? "",
      certificate_no: record?.certificate_no ?? "",
      valid_from: localDateTime(record?.valid_from ?? undefined),
      valid_until: localDateTime(record?.valid_until ?? new Date(Date.now() + 365 * 86400000).toISOString()),
      reference_values: JSON.stringify(record?.reference_values ?? {}, null, 2),
      status: record?.status ?? "ACTIVE",
    };
  }

  if (kind === "calibrations") {
    const scopedInstruments = resources.instruments.filter((item) => item.instrument_type === scope.instrumentType);
    const instrumentId = record?.instrument_id ?? scopedInstruments[0]?.id ?? resources.instruments[0]?.id ?? "";
    const instrument = resources.instruments.find((item) => item.id === instrumentId);
    const instrumentType = instrument?.instrument_type ?? scope.instrumentType;
    const qualityType = scope.qualityType || defaultQualityForInstrument(instrumentType);
    const methods = resources.methods.filter(
      (item) => item.instrument_type === instrumentType && item.quality_type === qualityType && item.is_active !== false,
    );
    const references = resources.references.filter(
      (item) => item.quality_type === qualityType && item.status !== "RETIRED" && item.status !== "EXPIRED",
    );
    return {
      calibration_no: record?.calibration_no ?? "",
      instrument_id: instrumentId,
      method_id: record?.method_id ?? methods[0]?.id ?? "",
      reference_standard_id: record?.reference_standard_id ?? references[0]?.id ?? "",
      calibrated_at: localDateTime(record?.calibrated_at),
      valid_until: localDateTime(record?.valid_until ? record.valid_until : new Date(Date.now() + 30 * 86400000).toISOString()),
      result: record?.result ?? "PASS",
      performed_by: record?.performed_by ?? "",
      check_values: JSON.stringify(record?.check_values ?? {}, null, 2),
    };
  }

  return {
    code: record?.code ?? "",
    name: record?.name ?? "",
    version: record?.version ?? "1.0",
    instrument_type: record?.instrument_type ?? scope.instrumentType,
    quality_type: record?.quality_type ?? scope.qualityType,
    schema_version: record?.schema_version ?? "1.0",
    field_mapping: JSON.stringify(record?.field_mapping ?? {}, null, 2),
    is_active: record?.is_active ?? true,
  };
}

function validateForm(
  kind: Kind,
  form: FormState,
  resources: Record<Kind, GovernanceResource[]>,
  lookup: { instruments: Map<string, GovernanceResource>; methods: Map<string, GovernanceResource>; references: Map<string, GovernanceResource> },
): string {
  if (kind === "instruments") {
    if (!String(form.code).trim() || !String(form.name).trim() || !String(form.serial_no).trim()) {
      return "请填写仪器代码、名称和序列号";
    }
    if (!String(form.manufacturer).trim() || !String(form.model).trim()) {
      return "请填写制造商和型号";
    }
    const qualities = parseSupportedQualityTypes(form.supported_quality_types);
    if (!qualities.length) return "请至少选择一个支持的质量类型";
  }

  if (kind === "methods") {
    if (!String(form.code).trim() || !String(form.name).trim() || !String(form.version).trim()) {
      return "请填写方法代码、名称和版本";
    }
    if (!String(form.method_type).trim()) return "请选择方法类型";
    const repeats = Number(form.minimum_repeats);
    if (!Number.isFinite(repeats) || repeats < 1) return "最少重复次数至少为 1";
  }

  if (kind === "references") {
    if (!String(form.code).trim() || !String(form.name).trim()) return "请填写参考件代码和名称";
    if (form.valid_from && form.valid_until && new Date(String(form.valid_until)) <= new Date(String(form.valid_from))) {
      return "参考件有效截止必须晚于有效开始";
    }
    try {
      jsonValue(String(form.reference_values ?? "{}"), "参考指标明细");
    } catch (error) {
      return error instanceof Error ? error.message : "参考指标明细格式不正确";
    }
  }

  if (kind === "calibrations") {
    if (!String(form.calibration_no).trim()) return "请填写校准/检查编号";
    if (!String(form.instrument_id).trim()) return "请选择仪器";
    if (!String(form.performed_by).trim()) return "请填写执行人";
    if (!String(form.calibrated_at).trim() || !String(form.valid_until).trim()) {
      return "请填写校准时间和有效截止";
    }
    if (new Date(String(form.valid_until)) <= new Date(String(form.calibrated_at))) {
      return "校准有效截止必须晚于校准时间";
    }
    const instrument = lookup.instruments.get(String(form.instrument_id));
    if (!instrument) return "所选仪器不存在";
    const methodId = String(form.method_id || "");
    if (methodId) {
      const method = lookup.methods.get(methodId);
      if (!method) return "所选测量方法不存在";
      if (method.instrument_type !== instrument.instrument_type) {
        return "测量方法与仪器类型不匹配，请重新选择";
      }
      const referenceId = String(form.reference_standard_id || "");
      if (referenceId) {
        const reference = lookup.references.get(referenceId);
        if (!reference) return "所选参考件不存在";
        if (reference.quality_type !== method.quality_type) {
          return "参考件质量类型与测量方法不一致";
        }
      }
    }
    try {
      jsonValue(String(form.check_values ?? "{}"), "检查记录明细");
    } catch (error) {
      return error instanceof Error ? error.message : "检查记录明细格式不正确";
    }
  }

  if (kind === "import-profiles") {
    if (!String(form.code).trim() || !String(form.name).trim() || !String(form.version).trim()) {
      return "请填写模板代码、名称和版本";
    }
    try {
      jsonValue(String(form.field_mapping ?? "{}"), "导入列映射");
    } catch (error) {
      return error instanceof Error ? error.message : "导入列映射格式不正确";
    }
  }

  void resources;
  return "";
}

function buildBody(kind: Kind, form: FormState): Record<string, unknown> {
  const body: Record<string, unknown> = { ...form };
  for (const key of [
    "firmware_version",
    "probe_code",
    "substrate_type",
    "geometry_class",
    "layer_scope",
    "serial_no",
    "certificate_no",
    "method_id",
    "reference_standard_id",
    "valid_from",
    "valid_until",
  ]) {
    if (body[key] === "") body[key] = null;
  }
  if (kind === "instruments") {
    body.supported_quality_types = parseSupportedQualityTypes(form.supported_quality_types);
  }
  if (kind === "methods") body.minimum_repeats = Number(form.minimum_repeats);
  if (kind === "references") body.reference_values = jsonValue(String(form.reference_values), "参考值");
  if (kind === "calibrations") body.check_values = jsonValue(String(form.check_values), "检查值");
  if (kind === "import-profiles") body.field_mapping = jsonValue(String(form.field_mapping), "字段映射");
  return body;
}

function FormSection({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <div className="modal-section form-field-wide">
      <div className="modal-section-title">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      <div className="modal-section-grid">{children}</div>
    </div>
  );
}

function input(label: string, key: string, form: FormState, setForm: (value: FormState) => void, type = "text", required = false) {
  return (
    <label className="form-field" key={key}>
      <span>
        {label}
        {required ? <b>*</b> : null}
      </span>
      <input
        type={type}
        required={required}
        value={String(form[key] ?? "")}
        onChange={(event) => setForm({ ...form, [key]: event.target.value })}
      />
    </label>
  );
}

function select(
  label: string,
  key: string,
  form: FormState,
  setForm: (value: FormState) => void,
  choices: readonly (readonly [string, string])[],
  required = true,
) {
  return (
    <label className="form-field" key={key}>
      <span>
        {label}
        {required ? <b>*</b> : null}
      </span>
      <select
        required={required}
        value={String(form[key] ?? "")}
        onChange={(event) => setForm({ ...form, [key]: event.target.value })}
      >
        {!required ? <option value="">未关联</option> : null}
        {choices.map(([value, text]) => (
          <option value={value} key={value}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}

function checkbox(label: string, key: string, form: FormState, setForm: (value: FormState) => void) {
  return (
    <label className="form-field" key={key}>
      <span>{label}</span>
      <span className="checkbox-field">
        <input
          type="checkbox"
          checked={Boolean(form[key])}
          onChange={(event) => setForm({ ...form, [key]: event.target.checked })}
        />
        {label}
      </span>
    </label>
  );
}

function qualityTypeCheckboxes(form: FormState, setForm: (value: FormState) => void) {
  const selected = new Set(parseSupportedQualityTypes(form.supported_quality_types));
  return (
    <div className="form-field form-field-wide" key="supported_quality_types">
      <span>
        支持质量类型 <b>*</b>
      </span>
      <div className="governance-chip-group">
        {qualityOptions.map(([value, label]) => {
          const checked = selected.has(value);
          return (
            <label key={value} className={checked ? "governance-chip governance-chip-active" : "governance-chip"}>
              <input
                type="checkbox"
                checked={checked}
                onChange={(event) => {
                  const next = new Set(selected);
                  if (event.target.checked) next.add(value);
                  else next.delete(value);
                  setForm({ ...form, supported_quality_types: [...next].join(",") });
                }}
              />
              {label}
            </label>
          );
        })}
      </div>
    </div>
  );
}

function renderFields(
  kind: Kind,
  form: FormState,
  setForm: (value: FormState) => void,
  resources: Record<Kind, GovernanceResource[]>,
  lookup: { instruments: Map<string, GovernanceResource>; methods: Map<string, GovernanceResource>; references: Map<string, GovernanceResource> },
) {
  if (kind === "instruments") {
    return [
      <FormSection key="identity" title="仪器身份" description="先确认仪器类型；支持的质量类型会按类型预填，可再勾选调整。">
        {input("仪器代码", "code", form, setForm, "text", true)}
        {input("仪器名称", "name", form, setForm, "text", true)}
        {select("仪器类型", "instrument_type", form, (next) => {
          const instrumentType = String(next.instrument_type);
          const quality = defaultQualityForInstrument(instrumentType);
          setForm({
            ...next,
            supported_quality_types: quality,
          });
        }, instrumentOptions)}
        {select("状态", "status", form, setForm, [
          ["ACTIVE", "在用"],
          ["MAINTENANCE", "维护"],
          ["RETIRED", "退役"],
        ])}
        {qualityTypeCheckboxes(form, setForm)}
        {checkbox("需要校准/检查", "calibration_required", form, setForm)}
      </FormSection>,
      <FormSection key="device" title="设备追溯" description="制造商、型号、序列号和固件用于测量可靠性追溯。">
        {input("制造商", "manufacturer", form, setForm, "text", true)}
        {input("型号", "model", form, setForm, "text", true)}
        {input("序列号", "serial_no", form, setForm, "text", true)}
        {input("固件版本", "firmware_version", form, setForm)}
      </FormSection>,
    ];
  }

  if (kind === "methods") {
    const currentMethodType = String(form.method_type ?? "");
    const methodChoices =
      currentMethodType && !methodTypeOptions.some(([value]) => value === currentMethodType)
        ? ([[currentMethodType, currentMethodType], ...methodTypeOptions] as const)
        : methodTypeOptions;
    return [
      <FormSection key="method-scope" title="适用范围" description="仪器类型与质量类型决定默认方法类型；可手动改。">
        {input("方法代码", "code", form, setForm, "text", true)}
        {input("方法名称", "name", form, setForm, "text", true)}
        {input("版本", "version", form, setForm, "text", true)}
        {select("质量类型", "quality_type", form, (next) => {
          const qualityType = String(next.quality_type);
          const instrumentType = String(next.instrument_type);
          setForm({
            ...next,
            method_type: defaultMethodType(instrumentType, qualityType),
            requires_direction: qualityType !== "THICKNESS",
            minimum_repeats: qualityType === "THICKNESS" ? "3" : String(next.minimum_repeats || "1"),
          });
        }, qualityOptions)}
        {select("仪器类型", "instrument_type", form, (next) => {
          const instrumentType = String(next.instrument_type);
          const qualityType = defaultQualityForInstrument(instrumentType);
          setForm({
            ...next,
            quality_type: qualityType,
            method_type: defaultMethodType(instrumentType, qualityType),
            requires_direction: qualityType !== "THICKNESS",
            minimum_repeats: qualityType === "THICKNESS" ? "3" : String(next.minimum_repeats || "1"),
          });
        }, instrumentOptions)}
        {select("方法类型", "method_type", form, setForm, methodChoices)}
      </FormSection>,
      <FormSection key="method-rules" title="测量规则" description="探头、基材、重复次数和参考件要求会影响可靠性门禁。">
        {input("探头代码", "probe_code", form, setForm)}
        {input("基材类型", "substrate_type", form, setForm)}
        {input("几何类别", "geometry_class", form, setForm)}
        {input("层范围", "layer_scope", form, setForm)}
        {input("最少重复次数", "minimum_repeats", form, setForm, "number", true)}
        {checkbox("需要参考件", "requires_reference", form, setForm)}
        {checkbox("需要测量方向", "requires_direction", form, setForm)}
        {checkbox("方法生效", "is_active", form, setForm)}
      </FormSection>,
    ];
  }

  if (kind === "references") {
    return [
      <FormSection key="reference-basic" title="参考件身份" description="参考件按质量类型维护，供校准和测量可靠性引用。">
        {input("参考件代码", "code", form, setForm, "text", true)}
        {input("参考件名称", "name", form, setForm, "text", true)}
        {select("质量类型", "quality_type", form, setForm, qualityOptions)}
        {select("状态", "status", form, setForm, [
          ["ACTIVE", "在用"],
          ["EXPIRED", "过期"],
          ["RETIRED", "退役"],
        ])}
        {input("序列号", "serial_no", form, setForm)}
        {input("证书编号", "certificate_no", form, setForm)}
        {input("有效开始", "valid_from", form, setForm, "datetime-local")}
        {input("有效截止", "valid_until", form, setForm, "datetime-local")}
      </FormSection>,
      <FormSection key="reference-values" title="参考指标" description="按指标代码维护参考值，提交时校验为对象结构。">
        <label className="form-field form-field-wide" key="reference_values">
          <span>参考指标明细</span>
          <JsonObjectEditor
            value={String(form.reference_values ?? "")}
            onChange={(value) => setForm({ ...form, reference_values: value })}
            keyLabel="指标代码"
            valueLabel="参考值"
            addLabel="新增参考项"
          />
        </label>
      </FormSection>,
    ];
  }

  if (kind === "calibrations") {
    const instrumentId = String(form.instrument_id ?? "");
    const instrument = lookup.instruments.get(instrumentId);
    const instrumentType = instrument?.instrument_type ?? "";
    const methodId = String(form.method_id ?? "");
    const method = lookup.methods.get(methodId);
    const qualityType = method?.quality_type ?? (instrument ? defaultQualityForInstrument(instrument.instrument_type ?? "") : "");
    const methodChoices = resources.methods
      .filter((item) => (!instrumentType || item.instrument_type === instrumentType) && item.is_active !== false)
      .map((item) => [item.id, `${item.code}:${item.version} · ${qualityTypeLabel(item.quality_type)}`] as const);
    const referenceChoices = resources.references
      .filter((item) => (!qualityType || item.quality_type === qualityType) && item.status !== "RETIRED" && item.status !== "EXPIRED")
      .map((item) => [item.id, `${item.code} / ${item.name}`] as const);

    return [
      <FormSection key="calibration-link" title="关联对象" description="先选仪器；方法与参考件会按仪器类型/质量类型过滤，并尽量预填。">
        {input("校准/检查编号", "calibration_no", form, setForm, "text", true)}
        {select(
          "仪器",
          "instrument_id",
          form,
          (next) => {
            const nextInstrument = lookup.instruments.get(String(next.instrument_id));
            const nextType = nextInstrument?.instrument_type ?? "";
            const nextQuality = defaultQualityForInstrument(nextType);
            const nextMethods = resources.methods.filter(
              (item) => item.instrument_type === nextType && item.quality_type === nextQuality && item.is_active !== false,
            );
            const nextReferences = resources.references.filter(
              (item) => item.quality_type === nextQuality && item.status !== "RETIRED" && item.status !== "EXPIRED",
            );
            setForm({
              ...next,
              method_id: nextMethods[0]?.id ?? "",
              reference_standard_id: nextReferences[0]?.id ?? "",
            });
          },
          resources.instruments.map((item) => [item.id, `${item.code} / ${item.name}`] as const),
        )}
        {select(
          "测量方法",
          "method_id",
          form,
          (next) => {
            const nextMethod = lookup.methods.get(String(next.method_id));
            const nextQuality = nextMethod?.quality_type ?? "";
            const nextReferences = resources.references.filter(
              (item) => (!nextQuality || item.quality_type === nextQuality) && item.status !== "RETIRED" && item.status !== "EXPIRED",
            );
            const currentRef = String(next.reference_standard_id || "");
            const stillValid = nextReferences.some((item) => item.id === currentRef);
            setForm({
              ...next,
              reference_standard_id: stillValid ? currentRef : nextReferences[0]?.id ?? "",
            });
          },
          methodChoices,
          false,
        )}
        {select("参考件", "reference_standard_id", form, setForm, referenceChoices, false)}
      </FormSection>,
      <FormSection key="calibration-result" title="校准结果" description="有效期内且结果为通过，才会计入有效校准。">
        {input("校准/检查时间", "calibrated_at", form, setForm, "datetime-local", true)}
        {input("有效截止", "valid_until", form, setForm, "datetime-local", true)}
        {select("结果", "result", form, setForm, [
          ["PASS", "通过"],
          ["FAIL", "失败"],
        ])}
        {input("执行人", "performed_by", form, setForm, "text", true)}
        <label className="form-field form-field-wide" key="check_values">
          <span>检查记录明细</span>
          <JsonObjectEditor
            value={String(form.check_values ?? "")}
            onChange={(value) => setForm({ ...form, check_values: value })}
            keyLabel="检查项"
            valueLabel="结果值"
            addLabel="新增检查项"
          />
        </label>
      </FormSection>,
    ];
  }

  return [
    <FormSection key="profile-basic" title="模板范围" description="导入模板按仪器类型与质量类型配置，供仪器导出文件映射。">
      {input("模板代码", "code", form, setForm, "text", true)}
      {input("模板名称", "name", form, setForm, "text", true)}
      {input("版本", "version", form, setForm, "text", true)}
      {select("仪器类型", "instrument_type", form, (next) => {
        const instrumentType = String(next.instrument_type);
        setForm({
          ...next,
          quality_type: defaultQualityForInstrument(instrumentType),
        });
      }, instrumentOptions)}
      {select("质量类型", "quality_type", form, setForm, qualityOptions)}
      {input("导出结构版本", "schema_version", form, setForm, "text", true)}
      {checkbox("模板生效", "is_active", form, setForm)}
    </FormSection>,
    <FormSection key="profile-mapping" title="列映射" description="把仪器导出列映射到系统字段；提交时校验对象结构。">
      <label className="form-field form-field-wide" key="field_mapping">
        <span>导入列映射</span>
        <JsonObjectEditor
          value={String(form.field_mapping ?? "")}
          onChange={(value) => setForm({ ...form, field_mapping: value })}
          keyLabel="源列名"
          valueLabel="目标字段"
          addLabel="新增映射"
        />
      </label>
    </FormSection>,
  ];
}
