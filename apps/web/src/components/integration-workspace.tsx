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
] as const;

const payloadTemplates: Record<string, Record<string, unknown>> = {
  MES_PRODUCTION_RUN_UPSERT: {
    run_no: "RUN-EXT-001",
    body_no: "BODY-001",
    factory_code: "M9",
    vehicle_model_code: "MX11",
    color_code: "C-01",
    shift: "DAY",
    started_at: "2026-06-11T08:00:00+08:00",
  },
  MATERIAL_BATCH_UPSERT: {
    batch_no: "LOT-EXT-001",
    material_code: "CC-001",
    material_name: "清漆",
    material_type: "CLEARCOAT",
    supplier: "供应商 A",
    viscosity: 24.2,
    solid_ratio: 0.52,
  },
  QMS_QUALITY_MEASUREMENT_UPSERT: {
    data_no: "QM-EXT-001",
    production_run_no: "RUN-20260610-001",
    measurement_point_code: "P-ROOF-03",
    quality_type: "ORANGE_PEEL",
    measured_at: "2026-06-11T09:00:00+08:00",
    metrics: [{ metric_code: "doi", metric_name: "DOI", raw_value: 82.5 }],
  },
  ROBOT_ACTUAL_PARAMETERS_UPSERT: {
    production_run_no: "RUN-20260610-001",
    process_stage: "CLEARCOAT_2",
    sampled_at: "2026-06-11T08:30:00+08:00",
    parameters: [
      {
        brush_no: "B-005",
        parameter_code: "clearcoat_2_spray_flow",
        actual_value: 318,
        unit: "ml/min",
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
    DEAD_LETTER: "死信",
  }[status] ?? status;
}

function statusClass(status: string): string {
  if (status === "SUCCEEDED") return "integration-success";
  if (status === "FAILED" || status === "DEAD_LETTER") return "integration-failed";
  return "integration-pending";
}

export function IntegrationWorkspace() {
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
      setError(loadError instanceof Error ? loadError.message : "集成中心加载失败");
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
      showSuccess(endpointModal?.id ? "集成端点已更新" : "集成端点已创建");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function deleteEndpoint(endpoint: Endpoint) {
    if (!window.confirm(`确认删除集成端点 ${endpoint.code}？已有事件的端点只能停用。`)) return;
    setSubmitting(`delete-${endpoint.id}`);
    try {
      await request(`/api/integrations/endpoints/${endpoint.id}`, { method: "DELETE" });
      showSuccess("集成端点已删除");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
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
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">MES · QMS · Robot · Material</span>
          <h1>集成与任务中心</h1>
          <p>管理外部系统端点、幂等事件、业务映射、失败重试、死信与人工重放。</p>
        </div>
        <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} /> 刷新任务状态
        </button>
      </header>

      {error ? <button className="message-banner message-error" onClick={() => setError("")}>{error}<X /></button> : null}
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}

      <section className="module-stat-strip">
        <article><span>集成端点</span><strong>{summary?.endpoints ?? 0}</strong><small>{summary?.active_endpoints ?? 0} 个已启用</small></article>
        <article><span>累计事件</span><strong>{summary?.events ?? 0}</strong><small>幂等接收与业务映射</small></article>
        <article><span>处理成功</span><strong>{summary?.events_by_status.SUCCEEDED ?? 0}</strong><small>已落入业务数据表</small></article>
        <article><span>失败 / 死信</span><strong>{summary?.failed_events ?? 0}</strong><small>支持人工重放</small></article>
      </section>

      <section className="panel integration-workspace">
        <div className="master-tabs">
          <button className={tab === "events" ? "active" : ""} onClick={() => setTab("events")}>事件任务</button>
          <button className={tab === "endpoints" ? "active" : ""} onClick={() => setTab("endpoints")}>集成端点</button>
          <label className="master-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索端点或事件" /></label>
          {tab === "events" ? <select className="integration-filter" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">全部状态</option>{["PENDING", "SUCCEEDED", "FAILED", "DEAD_LETTER"].map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}</select> : <button className="button button-primary" onClick={() => openEndpoint()}><Plus /> 新建端点</button>}
        </div>

        {tab === "events" ? <div className="integration-grid">
          <form className="integration-event-form" onSubmit={submitEvent}>
            <div className="program-subheading"><div><span className="eyebrow">Event Inbox</span><h3>提交集成事件</h3></div><PlugZap /></div>
            <div className="ai-form-stack">
              <label className="form-field"><span>集成端点 <b>*</b></span><select required value={eventEndpointId} onChange={(event) => setEventEndpointId(event.target.value)}>{endpoints.filter((item) => item.is_active).map((endpoint) => <option value={endpoint.id} key={endpoint.id}>{endpoint.code} · {endpoint.name}</option>)}</select></label>
              <label className="form-field"><span>事件类型 <b>*</b></span><select value={eventType} onChange={(event) => changeEventType(event.target.value)}>{eventTypes.map((value) => <option value={value} key={value}>{value}</option>)}</select></label>
              <label className="form-field"><span>来源事件 ID / 幂等键 <b>*</b></span><input required value={sourceEventId} onChange={(event) => setSourceEventId(event.target.value)} placeholder="例如 MES-20260611-0001" /></label>
              <label className="form-field"><span>JSON 事件负载 <b>*</b></span><textarea rows={16} required value={eventPayload} onChange={(event) => setEventPayload(event.target.value)} /></label>
              <label className="checkbox-field"><input type="checkbox" checked={processImmediately} onChange={(event) => setProcessImmediately(event.target.checked)} />接收后立即处理</label>
              <button className="button button-primary" disabled={!eventEndpointId || !sourceEventId || submitting === "event"}>{submitting === "event" ? <LoaderCircle className="spin" /> : <Play />} 接收并处理</button>
            </div>
          </form>
          <div className="integration-event-area">
            <div className="integration-event-list">
              {filteredEvents.map((item) => <button key={item.id} className={`integration-event-card ${item.id === selectedEventId ? "selected" : ""}`} onClick={() => setSelectedEventId(item.id)}><span className={`integration-status ${statusClass(item.status)}`}>{statusLabel(item.status)}</span><strong>{item.event_type}</strong><small>{item.event_no}</small><span>尝试 {item.attempt_count}/{item.max_attempts} · {new Date(item.created_at).toLocaleString("zh-CN")}</span>{item.last_error ? <em>{item.last_error}</em> : null}</button>)}
              {!filteredEvents.length ? <div className="master-empty"><PlugZap /> 暂无集成事件</div> : null}
            </div>
            {selectedEvent ? <div className="integration-detail">
              <div className="program-subheading"><div><span className="eyebrow">Event Detail</span><h3>{selectedEvent.source_event_id}</h3></div><span className={`integration-status ${statusClass(selectedEvent.status)}`}>{statusLabel(selectedEvent.status)}</span></div>
              <div className="integration-detail-meta"><span>事件编号 <b>{selectedEvent.event_no}</b></span><span>尝试次数 <b>{selectedEvent.attempt_count}/{selectedEvent.max_attempts}</b></span><span>处理时间 <b>{selectedEvent.processed_at ? new Date(selectedEvent.processed_at).toLocaleString("zh-CN") : "—"}</b></span></div>
              {selectedEvent.last_error ? <div className="integration-error"><CircleAlert />{selectedEvent.last_error}</div> : null}
              <div className="integration-json-grid"><div><span>原始事件负载</span><pre>{JSON.stringify(selectedEvent.payload, null, 2)}</pre></div><div><span>业务映射结果</span><pre>{JSON.stringify(selectedEvent.mapped_payload ?? {}, null, 2)}</pre></div></div>
              {selectedEvent.status === "PENDING" || selectedEvent.status === "FAILED" ? <div className="ai-workflow-actions"><button className="button button-primary" onClick={() => void operateEvent(selectedEvent, "process")}><Play /> 处理任务</button></div> : null}
              {selectedEvent.status === "DEAD_LETTER" || selectedEvent.status === "FAILED" ? <div className="ai-workflow-actions"><button className="button button-secondary" onClick={() => void operateEvent(selectedEvent, "replay")}><RotateCcw /> 重放事件</button></div> : null}
              {selectedEvent.status === "SUCCEEDED" ? <div className="integration-success-box"><CheckCircle2 />事件已成功映射并写入业务表</div> : null}
            </div> : null}
          </div>
        </div> : null}

        {tab === "endpoints" ? <div className="master-table-wrap"><table className="master-table integration-endpoint-table"><thead><tr><th>端点</th><th>系统类型</th><th>方向</th><th>连接配置</th><th>最近成功</th><th>状态</th><th>操作</th></tr></thead><tbody>{filteredEndpoints.map((endpoint) => <tr key={endpoint.id}><td><strong>{endpoint.code}</strong><br /><small>{endpoint.name}</small></td><td>{endpoint.system_type}</td><td>{endpoint.direction}</td><td>{endpoint.base_url ?? "由现场适配器推送"} · {endpoint.auth_type}</td><td>{endpoint.last_success_at ? new Date(endpoint.last_success_at).toLocaleString("zh-CN") : "—"}</td><td><span className={`record-status ${endpoint.is_active ? "status-on" : "status-off"}`}>{endpoint.is_active ? "启用" : "停用"}</span></td><td><div className="row-actions"><button className="icon-button" title="查看或编辑" onClick={() => openEndpoint(endpoint)}><Pencil /></button><button className="icon-button icon-button-danger" title="删除" onClick={() => void deleteEndpoint(endpoint)} disabled={submitting === `delete-${endpoint.id}`}><Trash2 /></button></div></td></tr>)}</tbody></table>{!filteredEndpoints.length ? <div className="master-empty"><PlugZap /> 暂无集成端点</div> : null}</div> : null}
      </section>

      {endpointModal !== undefined ? <div className="modal-backdrop" onMouseDown={() => setEndpointModal(undefined)}><section className="modal-card" role="dialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}><div className="modal-heading"><div><span className="eyebrow">Integration Endpoint</span><h2>{endpointModal?.id ? "编辑集成端点" : "新建集成端点"}</h2></div><button className="icon-button" onClick={() => setEndpointModal(undefined)}><X /></button></div><form onSubmit={saveEndpoint}><div className="form-grid"><EndpointInput label="端点代码" value={endpointForm.code} onChange={(value) => setEndpointForm({ ...endpointForm, code: value })} required /><EndpointInput label="端点名称" value={endpointForm.name} onChange={(value) => setEndpointForm({ ...endpointForm, name: value })} required /><EndpointSelect label="系统类型" value={endpointForm.system_type} onChange={(value) => setEndpointForm({ ...endpointForm, system_type: value })} options={["MES", "QMS", "ROBOT", "MATERIAL", "MEASUREMENT"]} /><EndpointSelect label="数据方向" value={endpointForm.direction} onChange={(value) => setEndpointForm({ ...endpointForm, direction: value })} options={["INBOUND", "OUTBOUND", "BIDIRECTIONAL"]} /><EndpointInput label="基础地址" value={endpointForm.base_url} onChange={(value) => setEndpointForm({ ...endpointForm, base_url: value })} /><EndpointSelect label="认证方式" value={endpointForm.auth_type} onChange={(value) => setEndpointForm({ ...endpointForm, auth_type: value })} options={["API_KEY", "OAUTH2", "BASIC", "NONE"]} /><label className="form-field form-field-wide"><span>非敏感配置 JSON</span><textarea rows={6} value={endpointForm.config} onChange={(event) => setEndpointForm({ ...endpointForm, config: event.target.value })} /></label><label className="form-field"><span>状态</span><span className="checkbox-field"><input type="checkbox" checked={endpointForm.is_active} onChange={(event) => setEndpointForm({ ...endpointForm, is_active: event.target.checked })} />启用端点</span></label></div><div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setEndpointModal(undefined)}>取消</button><button className="button button-primary" disabled={submitting === "endpoint"}>{submitting === "endpoint" ? <LoaderCircle className="spin" /> : <CheckCircle2 />} 保存端点</button></div></form></section></div> : null}
    </div>
  );
}

function EndpointInput({ label, value, onChange, required = false }: { label: string; value: string; onChange: (value: string) => void; required?: boolean }) {
  return <label className="form-field"><span>{label}{required ? <b>*</b> : null}</span><input required={required} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function EndpointSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[] }) {
  return <label className="form-field"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option value={option} key={option}>{option}</option>)}</select></label>;
}
