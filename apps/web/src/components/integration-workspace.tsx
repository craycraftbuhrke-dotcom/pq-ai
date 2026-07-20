"use client";

import {
  CheckCircle2,
  CircleAlert,
  LoaderCircle,
  Pencil,
  Play,
  PlugZap,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { BulkDataActions } from "@/components/bulk-data-actions";
import { ModalShell } from "@/components/modal-shell";
import { JsonObjectEditor, JsonTableEditor } from "@/components/structured-json-editor";
import { physicalDeleteDisabledMessage } from "@/lib/delete-policy";
import { statusLabel as sharedStatusLabel } from "@/lib/display-labels";

type Summary = {
  endpoints: number;
  active_endpoints: number;
  events: number;
  events_by_status: Record<string, number>;
  failed_events: number;
};
type Endpoint = {
  id: string;
  code: string;
  name: string;
  system_type: string;
  direction: string;
  base_url?: string | null;
  auth_type: string;
  config?: Record<string, unknown> | null;
  is_active: boolean;
  last_success_at?: string | null;
  last_failure_at?: string | null;
};
type IntegrationEvent = {
  id: string;
  event_no: string;
  endpoint_id: string;
  source_event_id: string;
  event_type: string;
  direction: string;
  status: string;
  payload: Record<string, unknown>;
  mapped_payload?: Record<string, unknown> | null;
  attempt_count: number;
  max_attempts: number;
  next_retry_at?: string | null;
  last_error?: string | null;
  processed_at?: string | null;
  created_at: string;
};
type EndpointForm = {
  code: string;
  name: string;
  system_type: string;
  direction: string;
  base_url: string;
  auth_type: string;
  config: string;
  is_active: boolean;
};
type Tab = "events" | "endpoints";

const eventTypes = [
  "MES_PRODUCTION_RUN_UPSERT",
  "MATERIAL_BATCH_UPSERT",
  "QMS_QUALITY_MEASUREMENT_UPSERT",
  "ROBOT_ACTUAL_PARAMETERS_UPSERT",
  "ROBOT_TRAJECTORY_EXECUTION_UPSERT",
] as const;

const payloadTemplates: Record<string, Record<string, unknown>> = {
  MES_PRODUCTION_RUN_UPSERT: {
    run_no: "",
    body_no: "",
    factory_code: "",
    vehicle_model_code: "",
    color_code: "",
    shift: "",
    started_at: "",
  },
  MATERIAL_BATCH_UPSERT: {
    batch_no: "",
    material_code: "",
    material_name: "",
    material_type: "",
    supplier: "",
    characteristic_results: [
      {
        result_no: "",
        characteristic_code: "",
        method_code: "",
        method_version: "",
        result_value: null,
        unit: "",
        tested_at: "",
        tested_by: "",
        source_uri: "",
        raw_values: {},
      },
    ],
  },
  QMS_QUALITY_MEASUREMENT_UPSERT: {
    data_no: "",
    production_run_no: "",
    measurement_point_code: "",
    quality_type: "",
    measured_at: "",
    metrics: [{ metric_code: "", metric_name: "", raw_value: null }],
  },
  ROBOT_ACTUAL_PARAMETERS_UPSERT: {
    production_run_no: "",
    process_stage: "",
    sampled_at: "",
    parameters: [
      {
        brush_no: "",
        parameter_code: "",
        actual_value: null,
        unit: "",
      },
    ],
  },
  ROBOT_TRAJECTORY_EXECUTION_UPSERT: {
    production_run_no: "",
    process_stage: "",
    device_configuration_version: "",
    trajectory_code: "",
    trajectory_version: "",
    executed_checksum: "",
    started_at: "",
    completed_at: "",
    source_system: "",
    segments: [
      {
        segment_no: null,
        actual_speed: null,
        speed_unit: "",
        trigger_state: "",
      },
    ],
  },
};

function systemTypeForEvent(eventType: string): string {
  if (eventType.startsWith("MES_")) return "MES";
  if (eventType.startsWith("QMS_")) return "QMS";
  if (eventType.startsWith("ROBOT_")) return "ROBOT";
  return "MATERIAL";
}

function parsePayloadValue(value: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(value) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

function stringifyPayloadValue(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new Error(payload.error ?? `请求失败（${response.status}）`);
  return payload;
}

function statusLabel(status: string): string {
  return {
    PENDING: "待处理",
    PROCESSING: "处理中",
    SUCCEEDED: "成功",
    FAILED: "失败待重试",
    DEAD_LETTER: "需人工处理",
  }[status] ?? sharedStatusLabel(status);
}

function statusClass(status: string): string {
  if (status === "SUCCEEDED") return "integration-success";
  if (status === "FAILED" || status === "DEAD_LETTER") return "integration-failed";
  return "integration-pending";
}

const BUSINESS_FIELD_LABELS: Record<string, string> = {
  run_no: "生产记录编号",
  body_no: "生产车号",
  factory_code: "工厂",
  vehicle_model_code: "车型",
  color_code: "颜色",
  shift: "班次",
  started_at: "开始时间",
  completed_at: "完成时间",
  batch_no: "材料批次号",
  material_code: "材料代码",
  material_name: "材料名称",
  material_type: "材料类型",
  supplier: "供应商",
  characteristic_results: "材料检测结果",
  result_no: "结果编号",
  characteristic_code: "材料特性",
  method_code: "检测方法",
  method_version: "方法版本",
  result_value: "检测结果",
  unit: "单位",
  tested_at: "检测时间",
  tested_by: "检测人员",
  data_no: "质量数据编号",
  production_run_no: "生产记录编号",
  measurement_point_code: "测量点",
  quality_type: "质量指标类型",
  measured_at: "检测时间",
  metrics: "检测结果",
  metric_code: "指标",
  metric_name: "指标名称",
  raw_value: "原始值",
  process_stage: "喷涂工序",
  sampled_at: "采集时间",
  parameters: "实际参数",
  parameter_code: "参数",
  actual_value: "实际值",
  source_system: "数据来源",
  program_version: "程序版本",
  executed_checksum: "执行文件校验",
  segments: "轨迹段",
  segment_no: "轨迹段号",
  actual_speed: "实际速度",
  speed_unit: "速度单位",
  trigger_state: "喷涂触发状态",
};

type BusinessRow = { label: string; value: string };

function businessValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "未填写";
  if (typeof value === "boolean") return value ? "是" : "否";
  const text = String(value);
  if (text.includes("T") && !Number.isNaN(new Date(text).getTime())) {
    return new Date(text).toLocaleString("zh-CN");
  }
  return sharedStatusLabel(text);
}

function businessRows(value: unknown, prefix = ""): BusinessRow[] {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => businessRows(item, `${prefix}第 ${index + 1} 项 · `));
  }
  if (!value || typeof value !== "object") {
    return [{ label: prefix.replace(/ · $/, "") || "内容", value: businessValue(value) }];
  }
  return Object.entries(value as Record<string, unknown>).flatMap(([key, item], index) => {
    const label = `${prefix}${BUSINESS_FIELD_LABELS[key] ?? `扩展信息 ${index + 1}`}`;
    if (item && typeof item === "object") return businessRows(item, `${label} · `);
    return [{ label, value: businessValue(item) }];
  });
}

function BusinessPayloadTable({ title, value }: { title: string; value: unknown }) {
  const rows = businessRows(value);
  return (
    <section className="integration-business-table">
      <h4>{title}</h4>
      <dl>
        {rows.map((row, index) => (
          <div key={`${row.label}-${index}`}>
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function IntegrationWorkspace({ embedded = false }: { embedded?: boolean } = {}) {
  const [tab, setTab] = useState<Tab>("events");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [events, setEvents] = useState<IntegrationEvent[]>([]);
  const [selectedEventId, setSelectedEventId] = useState("");
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [endpointModal, setEndpointModal] = useState<Endpoint | null | undefined>(undefined);
  const [endpointForm, setEndpointForm] = useState<EndpointForm>({
    code: "",
    name: "",
    system_type: "MES",
    direction: "INBOUND",
    base_url: "",
    auth_type: "API_KEY",
    config: "{}",
    is_active: true,
  });
  const [eventType, setEventType] = useState<string>(eventTypes[0]);
  const [eventEndpointId, setEventEndpointId] = useState("");
  const [sourceEventId, setSourceEventId] = useState("");
  const [eventPayload, setEventPayload] = useState(JSON.stringify(payloadTemplates[eventTypes[0]], null, 2));
  const [processImmediately, setProcessImmediately] = useState(true);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const endpointBusy = submitting === "endpoint";
  const closeEndpointModal = useCallback(() => {
    if (endpointBusy) return;
    setEndpointModal(undefined);
  }, [endpointBusy]);
  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextSummary, nextEndpoints, nextEvents] = await Promise.all([
        request<Summary>("/api/integrations/summary"),
        request<Endpoint[]>("/api/integrations/endpoints"),
        request<IntegrationEvent[]>("/api/integrations/events?limit=500"),
      ]);
      setSummary(nextSummary);
      setEndpoints(nextEndpoints);
      setEvents(nextEvents);
      setEventEndpointId(
        (current) =>
          current ||
          nextEndpoints.find(
            (item) => item.is_active && item.system_type === systemTypeForEvent(eventTypes[0]),
          )?.id ||
          nextEndpoints.find((item) => item.is_active)?.id ||
          "",
      );
      setSelectedEventId((current) => current || nextEvents[0]?.id || "");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "外部数据页面加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  const selectedEvent = events.find((item) => item.id === selectedEventId);
  const filteredEvents = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return events.filter(
      (item) =>
        (!statusFilter || item.status === statusFilter) &&
        (!normalized ||
          [item.event_no, item.source_event_id, item.event_type, item.status, item.last_error]
            .some((value) => String(value ?? "").toLowerCase().includes(normalized))),
    );
  }, [events, query, statusFilter]);
  const filteredEndpoints = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return endpoints.filter(
      (item) =>
        !normalized ||
        [item.code, item.name, item.system_type, item.direction, item.base_url]
          .some((value) => String(value ?? "").toLowerCase().includes(normalized)),
    );
  }, [endpoints, query]);

  function showSuccess(message: string) {
    setNotice(message);
    setError("");
  }

  function showError(operationError: unknown) {
    setError(operationError instanceof Error ? operationError.message : "操作失败");
    setNotice("");
  }

  function openEndpoint(endpoint?: Endpoint) {
    setEndpointModal(endpoint ?? null);
    setEndpointForm({
      code: endpoint?.code ?? "",
      name: endpoint?.name ?? "",
      system_type: endpoint?.system_type ?? "MES",
      direction: endpoint?.direction ?? "INBOUND",
      base_url: endpoint?.base_url ?? "",
      auth_type: endpoint?.auth_type ?? "API_KEY",
      config: JSON.stringify(endpoint?.config ?? {}, null, 2),
      is_active: endpoint?.is_active ?? true,
    });
  }

  async function saveEndpoint(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting("endpoint");
    try {
      const body = {
        ...endpointForm,
        base_url: endpointForm.base_url || null,
        config: JSON.parse(endpointForm.config || "{}"),
      };
      await request(endpointModal?.id ? `/api/integrations/endpoints/${endpointModal.id}` : "/api/integrations/endpoints", {
        method: endpointModal?.id ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setEndpointModal(undefined);
      showSuccess(endpointModal?.id ? "外部系统连接已更新" : "外部系统连接已创建");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  function deleteEndpoint(endpoint: Endpoint) {
    showError(new Error(`外部系统连接 ${endpoint.code} 不能物理删除。${physicalDeleteDisabledMessage}`));
  }

  function bulkResult(message: string, type: "success" | "error") {
    if (type === "success") showSuccess(message);
    else showError(new Error(message));
  }

  async function submitEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting("event");
    try {
      const result = await request<IntegrationEvent>("/api/integrations/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endpoint_id: eventEndpointId,
          source_event_id: sourceEventId,
          event_type: eventType,
          payload: JSON.parse(eventPayload),
          process_immediately: processImmediately,
          max_attempts: 3,
        }),
      });
      setSelectedEventId(result.id);
      showSuccess(`事件已接收：${statusLabel(result.status)}`);
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function operateEvent(integrationEvent: IntegrationEvent, operation: "process" | "replay") {
    setSubmitting(`${operation}-${integrationEvent.id}`);
    try {
      const result = await request<IntegrationEvent>(`/api/integrations/events/${integrationEvent.id}/${operation}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      showSuccess(`事件操作完成：${statusLabel(result.status)}`);
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  function changeEventType(value: string) {
    setEventType(value);
    setEventPayload(JSON.stringify(payloadTemplates[value], null, 2));
    const matchingEndpoint = endpoints.find(
      (endpoint) => endpoint.is_active && endpoint.system_type === systemTypeForEvent(value),
    );
    if (matchingEndpoint) setEventEndpointId(matchingEndpoint.id);
  }

  return (
    <div className={embedded ? "embedded-stack" : "page-stack"}>
      {!embedded ? (
      <header className="page-header">
        <div className="page-actions">
          <BulkDataActions
            resourceKey={tab === "events" ? "integrations.events" : "integrations.endpoints"}
            resourceLabel={tab === "events" ? "数据接收任务" : "外部系统连接"}
            disabled={loading || Boolean(submitting)}
            onImported={reload}
            onResult={bulkResult}
          />
          <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
            <RefreshCw className={loading ? "spin" : ""} /> 刷新任务状态
          </button>
        </div>
      </header>
      ) : null}

      {error ? <button className="message-banner message-error" onClick={() => setError("")}>{error}<X /></button> : null}
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}

      <section className="module-stat-strip">
        <article><span>外部系统连接</span><strong>{summary?.endpoints ?? 0}</strong><small>{summary?.active_endpoints ?? 0} 个已启用</small></article>
        <article><span>累计事件</span><strong>{summary?.events ?? 0}</strong><small>自动接收并映射业务数据</small></article>
        <article><span>处理成功</span><strong>{summary?.events_by_status.SUCCEEDED ?? 0}</strong><small>已落入业务数据表</small></article>
        <article><span>失败 / 需人工处理</span><strong>{summary?.failed_events ?? 0}</strong><small>支持人工再次处理</small></article>
      </section>

      <section className="panel integration-workspace">
        <div className="master-tabs">
          <button className={tab === "events" ? "active" : ""} onClick={() => setTab("events")}>数据任务</button>
          <button className={tab === "endpoints" ? "active" : ""} onClick={() => setTab("endpoints")}>外部系统连接</button>
          <label className="master-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索连接或任务" /></label>
          {tab === "events" ? <select className="integration-filter" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">全部状态</option>{["PENDING", "SUCCEEDED", "FAILED", "DEAD_LETTER"].map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}</select> : <button className="button button-primary" onClick={() => openEndpoint()}><Plus /> 新建端点</button>}
        </div>

        {tab === "events" ? <div className="integration-grid">
          <form className="integration-event-form" onSubmit={submitEvent}>
            <div className="program-subheading"><div><span className="eyebrow">手工接收数据</span><h3>提交数据接收任务</h3></div><PlugZap /></div>
            <div className="ai-form-stack">
              <label className="form-field"><span>外部系统连接 <b>*</b></span><select required value={eventEndpointId} onChange={(event) => setEventEndpointId(event.target.value)}>{endpoints.filter((item) => item.is_active).map((endpoint) => <option value={endpoint.id} key={endpoint.id}>{endpoint.code} · {endpoint.name}</option>)}</select></label>
              <label className="form-field"><span>数据类型 <b>*</b></span><select value={eventType} onChange={(event) => changeEventType(event.target.value)}>{eventTypes.map((value) => <option value={value} key={value}>{sharedStatusLabel(value)}</option>)}</select></label>
              <label className="form-field"><span>来源记录编号（防止重复导入） <b>*</b></span><input required value={sourceEventId} onChange={(event) => setSourceEventId(event.target.value)} placeholder="例如 MES-20260611-0001" /></label>
              <label className="form-field form-field-wide"><span>事件数据明细 <b>*</b></span><IntegrationEventPayloadEditor eventType={eventType} value={eventPayload} onChange={setEventPayload} /></label>
              <label className="checkbox-field"><input type="checkbox" checked={processImmediately} onChange={(event) => setProcessImmediately(event.target.checked)} />接收后立即处理</label>
              <button className="button button-primary" disabled={!eventEndpointId || !sourceEventId || submitting === "event"}>{submitting === "event" ? <LoaderCircle className="spin" /> : <Play />} 接收并处理</button>
            </div>
          </form>
          <div className="integration-event-area">
            <div className="integration-event-list">
              {filteredEvents.map((item) => <button key={item.id} className={`integration-event-card ${item.id === selectedEventId ? "selected" : ""}`} onClick={() => setSelectedEventId(item.id)}><span className={`integration-status ${statusClass(item.status)}`}>{statusLabel(item.status)}</span><strong>{sharedStatusLabel(item.event_type)}</strong><small>{item.event_no}</small><span>尝试 {item.attempt_count}/{item.max_attempts} · {new Date(item.created_at).toLocaleString("zh-CN")}</span>{item.last_error ? <em>{item.last_error}</em> : null}</button>)}
              {!filteredEvents.length ? <div className="master-empty"><PlugZap /> 暂无数据接收任务</div> : null}
            </div>
            {selectedEvent ? <div className="integration-detail">
              <div className="program-subheading"><div><span className="eyebrow">事件详情</span><h3>{selectedEvent.source_event_id}</h3></div><span className={`integration-status ${statusClass(selectedEvent.status)}`}>{statusLabel(selectedEvent.status)}</span></div>
              <div className="integration-detail-meta"><span>任务编号 <b>{selectedEvent.event_no}</b></span><span>尝试次数 <b>{selectedEvent.attempt_count}/{selectedEvent.max_attempts}</b></span><span>处理时间 <b>{selectedEvent.processed_at ? new Date(selectedEvent.processed_at).toLocaleString("zh-CN") : "—"}</b></span></div>
              {selectedEvent.last_error ? <div className="integration-error"><CircleAlert />{selectedEvent.last_error}</div> : null}
              <div className="integration-business-grid">
                <BusinessPayloadTable title="接收到的业务内容" value={selectedEvent.payload} />
                <BusinessPayloadTable title="系统识别结果" value={selectedEvent.mapped_payload ?? {}} />
              </div>
              {selectedEvent.status === "PENDING" || selectedEvent.status === "FAILED" ? <div className="ai-workflow-actions"><button className="button button-primary" onClick={() => void operateEvent(selectedEvent, "process")}><Play /> 处理任务</button></div> : null}
              {selectedEvent.status === "DEAD_LETTER" || selectedEvent.status === "FAILED" ? <div className="ai-workflow-actions"><button className="button button-secondary" onClick={() => void operateEvent(selectedEvent, "replay")}><RotateCcw /> 再次处理</button></div> : null}
              {selectedEvent.status === "SUCCEEDED" ? <div className="integration-success-box"><CheckCircle2 />事件已成功整理并保存为业务数据</div> : null}
            </div> : null}
          </div>
        </div> : null}

        {tab === "endpoints" ? <div className="master-table-wrap"><table className="master-table integration-endpoint-table"><thead><tr><th>端点</th><th>系统类型</th><th>方向</th><th>连接配置</th><th>最近成功</th><th>状态</th><th>操作</th></tr></thead><tbody>{filteredEndpoints.map((endpoint) => <tr key={endpoint.id}><td><strong>{endpoint.code}</strong><br /><small>{endpoint.name}</small></td><td>{sharedStatusLabel(endpoint.system_type)}</td><td>{sharedStatusLabel(endpoint.direction)}</td><td>{endpoint.base_url ?? "由现场数据程序推送"} · {sharedStatusLabel(endpoint.auth_type)}</td><td>{endpoint.last_success_at ? new Date(endpoint.last_success_at).toLocaleString("zh-CN") : "—"}</td><td><span className={`record-status ${endpoint.is_active ? "status-on" : "status-off"}`}>{endpoint.is_active ? "启用" : "停用"}</span></td><td><div className="row-actions"><button className="icon-button" title="查看或编辑" aria-label="查看或编辑外部系统连接" onClick={() => openEndpoint(endpoint)}><Pencil aria-hidden="true" /></button><button className="icon-button icon-button-danger" title="删除" aria-label="删除外部系统连接" onClick={() => void deleteEndpoint(endpoint)} disabled={submitting === `delete-${endpoint.id}`}><Trash2 aria-hidden="true" /></button></div></td></tr>)}</tbody></table>{!filteredEndpoints.length ? <div className="master-empty"><PlugZap /> 暂无外部系统连接</div> : null}</div> : null}
      </section>

      {endpointModal !== undefined ? <ModalShell eyebrow="外部系统连接" title={endpointModal?.id ? "编辑外部系统连接" : "新建外部系统连接"} description="统一维护外部系统连接的连接信息、认证方式和非敏感配置。" onClose={closeEndpointModal} busy={endpointBusy}><form onSubmit={saveEndpoint}><div className="form-grid"><EndpointInput label="连接代码" value={endpointForm.code} onChange={(value) => setEndpointForm({ ...endpointForm, code: value })} required /><EndpointInput label="连接名称" value={endpointForm.name} onChange={(value) => setEndpointForm({ ...endpointForm, name: value })} required /><EndpointSelect label="系统类型" value={endpointForm.system_type} onChange={(value) => setEndpointForm({ ...endpointForm, system_type: value })} options={["MES", "QMS", "ROBOT", "MATERIAL", "MEASUREMENT"]} /><EndpointSelect label="数据方向" value={endpointForm.direction} onChange={(value) => setEndpointForm({ ...endpointForm, direction: value })} options={["INBOUND", "OUTBOUND", "BIDIRECTIONAL"]} /><EndpointInput label="基础地址" value={endpointForm.base_url} onChange={(value) => setEndpointForm({ ...endpointForm, base_url: value })} /><EndpointSelect label="认证方式" value={endpointForm.auth_type} onChange={(value) => setEndpointForm({ ...endpointForm, auth_type: value })} options={["API_KEY", "OAUTH2", "BASIC", "NONE"]} /><label className="form-field form-field-wide"><span>连接补充配置</span><JsonObjectEditor value={endpointForm.config} onChange={(value) => setEndpointForm({ ...endpointForm, config: value })} keyLabel="配置项" valueLabel="配置值" addLabel="新增配置项" /></label><label className="form-field"><span>状态</span><span className="checkbox-field"><input type="checkbox" checked={endpointForm.is_active} onChange={(event) => setEndpointForm({ ...endpointForm, is_active: event.target.checked })} />启用此连接</span></label></div><div className="modal-actions"><button type="button" className="button button-secondary" onClick={closeEndpointModal} disabled={endpointBusy}>取消</button><button className="button button-primary" disabled={endpointBusy}>{endpointBusy ? <LoaderCircle className="spin" aria-hidden="true" /> : <CheckCircle2 aria-hidden="true" />}{endpointBusy ? "正在保存" : "保存连接"}</button></div></form></ModalShell> : null}
    </div>
  );
}

function EndpointInput({ label, value, onChange, required = false }: { label: string; value: string; onChange: (value: string) => void; required?: boolean }) {
  return <label className="form-field"><span>{label}{required ? <b>*</b> : null}</span><input required={required} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function EndpointSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[] }) {
  return <label className="form-field"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option value={option} key={option}>{sharedStatusLabel(option)}</option>)}</select></label>;
}

function IntegrationEventPayloadEditor({ eventType, value, onChange }: { eventType: string; value: string; onChange: (value: string) => void }) {
  const payload = parsePayloadValue(value);
  const setField = (key: string, nextValue: unknown) => onChange(stringifyPayloadValue({ ...payload, [key]: nextValue }));

  if (eventType === "MES_PRODUCTION_RUN_UPSERT") {
    return (
      <div className="modal-section-grid">
        <PayloadInput label="生产任务编号" value={String(payload.run_no ?? "")} onChange={(nextValue) => setField("run_no", nextValue)} />
        <PayloadInput label="车身号" value={String(payload.body_no ?? "")} onChange={(nextValue) => setField("body_no", nextValue)} />
        <PayloadInput label="工厂代码" value={String(payload.factory_code ?? "")} onChange={(nextValue) => setField("factory_code", nextValue)} />
        <PayloadInput label="车型代码" value={String(payload.vehicle_model_code ?? "")} onChange={(nextValue) => setField("vehicle_model_code", nextValue)} />
        <PayloadInput label="颜色代码" value={String(payload.color_code ?? "")} onChange={(nextValue) => setField("color_code", nextValue)} />
        <PayloadInput label="班次" value={String(payload.shift ?? "")} onChange={(nextValue) => setField("shift", nextValue)} />
        <PayloadInput label="开始时间" type="datetime-local" value={String(payload.started_at ?? "")} onChange={(nextValue) => setField("started_at", nextValue)} />
      </div>
    );
  }

  if (eventType === "MATERIAL_BATCH_UPSERT") {
    return (
      <div className="structured-editor">
        <div className="modal-section-grid">
          <PayloadInput label="批次号" value={String(payload.batch_no ?? "")} onChange={(nextValue) => setField("batch_no", nextValue)} />
          <PayloadInput label="材料代码" value={String(payload.material_code ?? "")} onChange={(nextValue) => setField("material_code", nextValue)} />
          <PayloadInput label="材料名称" value={String(payload.material_name ?? "")} onChange={(nextValue) => setField("material_name", nextValue)} />
          <PayloadInput label="材料类型" value={String(payload.material_type ?? "")} onChange={(nextValue) => setField("material_type", nextValue)} />
          <PayloadInput label="供应商" value={String(payload.supplier ?? "")} onChange={(nextValue) => setField("supplier", nextValue)} />
        </div>
        <JsonTableEditor
          value={JSON.stringify(Array.isArray(payload.characteristic_results) ? payload.characteristic_results : [], null, 2)}
          onChange={(nextValue) => setField("characteristic_results", JSON.parse(nextValue))}
          columns={[
            { key: "result_no", label: "结果编号" },
            { key: "characteristic_code", label: "特性代码" },
            { key: "method_code", label: "方法代码" },
            { key: "method_version", label: "方法版本" },
            { key: "result_value", label: "结果值", type: "number" },
            { key: "unit", label: "单位" },
            { key: "tested_at", label: "检测时间", type: "datetime-local" },
            { key: "tested_by", label: "检测人" },
          ]}
          addLabel="新增检测结果"
        />
      </div>
    );
  }

  if (eventType === "QMS_QUALITY_MEASUREMENT_UPSERT") {
    return (
      <div className="structured-editor">
        <div className="modal-section-grid">
          <PayloadInput label="数据编号" value={String(payload.data_no ?? "")} onChange={(nextValue) => setField("data_no", nextValue)} />
          <PayloadInput label="生产任务编号" value={String(payload.production_run_no ?? "")} onChange={(nextValue) => setField("production_run_no", nextValue)} />
          <PayloadInput label="测量点代码" value={String(payload.measurement_point_code ?? "")} onChange={(nextValue) => setField("measurement_point_code", nextValue)} />
          <PayloadInput label="质量类型" value={String(payload.quality_type ?? "")} onChange={(nextValue) => setField("quality_type", nextValue)} />
          <PayloadInput label="测量时间" type="datetime-local" value={String(payload.measured_at ?? "")} onChange={(nextValue) => setField("measured_at", nextValue)} />
        </div>
        <JsonTableEditor
          value={JSON.stringify(Array.isArray(payload.metrics) ? payload.metrics : [], null, 2)}
          onChange={(nextValue) => setField("metrics", JSON.parse(nextValue))}
          columns={[
            { key: "metric_code", label: "指标代码" },
            { key: "metric_name", label: "指标名称" },
            { key: "raw_value", label: "原始值", type: "number" },
          ]}
          addLabel="新增指标"
        />
      </div>
    );
  }

  if (eventType === "ROBOT_ACTUAL_PARAMETERS_UPSERT") {
    return (
      <div className="structured-editor">
        <div className="modal-section-grid">
          <PayloadInput label="生产任务编号" value={String(payload.production_run_no ?? "")} onChange={(nextValue) => setField("production_run_no", nextValue)} />
          <PayloadInput label="工序" value={String(payload.process_stage ?? "")} onChange={(nextValue) => setField("process_stage", nextValue)} />
          <PayloadInput label="采样时间" type="datetime-local" value={String(payload.sampled_at ?? "")} onChange={(nextValue) => setField("sampled_at", nextValue)} />
        </div>
        <JsonTableEditor
          value={JSON.stringify(Array.isArray(payload.parameters) ? payload.parameters : [], null, 2)}
          onChange={(nextValue) => setField("parameters", JSON.parse(nextValue))}
          columns={[
            { key: "brush_no", label: "刷子号" },
            { key: "parameter_code", label: "参数代码" },
            { key: "actual_value", label: "实际值", type: "number" },
            { key: "unit", label: "单位" },
          ]}
          addLabel="新增参数"
        />
      </div>
    );
  }

  return (
    <div className="structured-editor">
      <div className="modal-section-grid">
        <PayloadInput label="生产任务编号" value={String(payload.production_run_no ?? "")} onChange={(nextValue) => setField("production_run_no", nextValue)} />
        <PayloadInput label="工序" value={String(payload.process_stage ?? "")} onChange={(nextValue) => setField("process_stage", nextValue)} />
        <PayloadInput label="设备配置版本" value={String(payload.device_configuration_version ?? "")} onChange={(nextValue) => setField("device_configuration_version", nextValue)} />
        <PayloadInput label="轨迹代码" value={String(payload.trajectory_code ?? "")} onChange={(nextValue) => setField("trajectory_code", nextValue)} />
        <PayloadInput label="轨迹版本" value={String(payload.trajectory_version ?? "")} onChange={(nextValue) => setField("trajectory_version", nextValue)} />
        <PayloadInput label="执行校验和" value={String(payload.executed_checksum ?? "")} onChange={(nextValue) => setField("executed_checksum", nextValue)} />
        <PayloadInput label="开始时间" type="datetime-local" value={String(payload.started_at ?? "")} onChange={(nextValue) => setField("started_at", nextValue)} />
        <PayloadInput label="完成时间" type="datetime-local" value={String(payload.completed_at ?? "")} onChange={(nextValue) => setField("completed_at", nextValue)} />
        <PayloadInput label="来源系统" value={String(payload.source_system ?? "")} onChange={(nextValue) => setField("source_system", nextValue)} />
      </div>
      <JsonTableEditor
        value={JSON.stringify(Array.isArray(payload.segments) ? payload.segments : [], null, 2)}
        onChange={(nextValue) => setField("segments", JSON.parse(nextValue))}
        columns={[
          { key: "segment_no", label: "路径段序号", type: "number" },
          { key: "actual_speed", label: "实际速度", type: "number" },
          { key: "speed_unit", label: "速度单位" },
          { key: "trigger_state", label: "触发状态" },
        ]}
        addLabel="新增路径段"
      />
    </div>
  );
}

function PayloadInput({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return <label className="form-field"><span>{label}</span><input type={type} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}
