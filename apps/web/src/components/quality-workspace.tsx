"use client";

import {
  Activity,
  Download,
  LoaderCircle,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { CSSProperties, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { BulkDataActions } from "@/components/bulk-data-actions";
import { MeasurementGovernancePanel } from "@/components/measurement-governance-panel";
import { SpcChart } from "@/components/spc-chart";
import { physicalDeleteDisabledMessage } from "@/lib/delete-policy";

type Resource = { id: string; code: string; name: string };
type ProductionRun = { id: string; run_no: string; body_no?: string | null; started_at: string };
type Instrument = Resource & { instrument_type: string; status: string; supported_quality_types: string[] };
type Method = Resource & { version: string; quality_type: string; instrument_type: string; minimum_repeats: number };
type Calibration = { id: string; calibration_no: string; instrument_id: string; method_id?: string | null; result: string; valid_until: string };
type ReferenceStandard = Resource & { quality_type: string; status: string };
type ImportProfile = Resource & { version: string; quality_type: string; instrument_type: string; is_active: boolean };
type MetricDefinition = {
  id: string;
  quality_type: string;
  code: string;
  name: string;
  unit?: string | null;
  is_primary: boolean;
};
type MetricValue = {
  id: string;
  metric_code: string;
  metric_name: string;
  raw_value: number;
  corrected_value?: number | null;
  unit?: string | null;
};
type RepeatValue = {
  id: string;
  repeat_no: number;
  metric_code: string;
  raw_value: number;
  corrected_value?: number | null;
  unit?: string | null;
  is_valid: boolean;
  invalid_reason?: string | null;
};
type Measurement = {
  id: string;
  data_no: string;
  production_run_id: string;
  measurement_group_id?: string | null;
  measurement_point_id: string;
  measurement_point_code: string;
  measurement_point_name: string;
  quality_type: string;
  data_type: string;
  measured_at: string;
  measured_by?: string | null;
  device_code?: string | null;
  instrument_id?: string | null;
  instrument_code?: string | null;
  instrument_name?: string | null;
  measurement_method_id?: string | null;
  measurement_method_code?: string | null;
  calibration_record_id?: string | null;
  calibration_no?: string | null;
  reference_standard_id?: string | null;
  reference_standard_code?: string | null;
  import_profile_id?: string | null;
  import_profile_code?: string | null;
  measurement_direction?: string | null;
  raw_file_uri?: string | null;
  reliability_status: string;
  reliability_issues: string[];
  status_score?: number | null;
  is_valid: boolean;
  judgement: string;
  violations: string[];
  metrics: MetricValue[];
  repeat_readings: RepeatValue[];
};
type Standard = {
  id: string;
  standard_no: string;
  version: string;
  standard_type: string;
  quality_type: string;
  metric_code: string;
  vehicle_model_id?: string | null;
  color_id?: string | null;
  part_id?: string | null;
  measurement_point_id?: string | null;
  min_value?: number | null;
  max_value?: number | null;
  unit?: string | null;
  is_active: boolean;
};
type Summary = {
  measurements: number;
  valid_measurements: number;
  metric_values: number;
  standards: number;
  pass_measurements: number;
  fail_measurements: number;
  no_standard_measurements: number;
  verified_measurements: number;
  unverified_measurements: number;
  failed_reliability_measurements: number;
};
type AnalyticsSeriesPoint = {
  measurement_id: string;
  data_no: string;
  measurement_point_id: string;
  measurement_point_code: string;
  measurement_point_name: string;
  measured_at: string;
  value: number;
  judgement: string;
  standard_min?: number | null;
  standard_max?: number | null;
};
type Analytics = {
  quality_type: string;
  metric_code: string;
  metric_name: string;
  unit?: string | null;
  statistics: {
    samples: number;
    mean?: number | null;
    sigma?: number | null;
    minimum?: number | null;
    maximum?: number | null;
    ucl?: number | null;
    lcl?: number | null;
    trend_slope?: number | null;
    cp?: number | null;
    cpk?: number | null;
    pass_rate: number;
    out_of_control_count: number;
  };
  data_quality: {
    total_measurements: number;
    valid_measurements: number;
    invalid_measurements: number;
    measurements_with_metric: number;
    missing_metric_count: number;
    no_standard_count: number;
    valid_rate: number;
    metric_completeness: number;
    standard_coverage: number;
    latest_measured_at?: string | null;
  };
  series: AnalyticsSeriesPoint[];
  point_risks: Array<{
    measurement_point_id: string;
    measurement_point_code: string;
    measurement_point_name: string;
    samples: number;
    failures: number;
    fail_rate: number;
    no_standard_count: number;
    latest_value: number;
    latest_judgement: string;
    risk_score: number;
  }>;
};
type MetricRow = { metric_code: string; raw_value: string; corrected_value: string };
type RepeatRow = { repeat_no: string; metric_code: string; raw_value: string; corrected_value: string };
type FormState = Record<string, string | boolean>;
type Tab = "measurements" | "standards" | "analytics" | "governance";

const qualityLabels: Record<string, string> = {
  ORANGE_PEEL: "橘皮",
  COLOR_DIFFERENCE: "色差",
  THICKNESS: "膜厚",
};

const judgementLabels: Record<string, string> = {
  PASS: "合格",
  FAIL: "超差",
  NO_STANDARD: "无标准",
  INVALID: "无效",
};
const reliabilityLabels: Record<string, string> = {
  VERIFIED: "可靠性已验证",
  UNVERIFIED: "可靠性未验证",
  FAILED: "可靠性失败",
};

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

function relationName(resources: Resource[], id?: string | null): string {
  const item = resources.find((resource) => resource.id === id);
  return item ? `${item.code} / ${item.name}` : "全部";
}

export function QualityWorkspace() {
  const [tab, setTab] = useState<Tab>("measurements");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [analyticsMetric, setAnalyticsMetric] = useState("doi");
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [definitions, setDefinitions] = useState<MetricDefinition[]>([]);
  const [runs, setRuns] = useState<ProductionRun[]>([]);
  const [groups, setGroups] = useState<Resource[]>([]);
  const [points, setPoints] = useState<Resource[]>([]);
  const [vehicleModels, setVehicleModels] = useState<Resource[]>([]);
  const [colors, setColors] = useState<Resource[]>([]);
  const [parts, setParts] = useState<Resource[]>([]);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [methods, setMethods] = useState<Method[]>([]);
  const [calibrations, setCalibrations] = useState<Calibration[]>([]);
  const [references, setReferences] = useState<ReferenceStandard[]>([]);
  const [importProfiles, setImportProfiles] = useState<ImportProfile[]>([]);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [modal, setModal] = useState<{ kind: "measurement" | "standard"; record?: Measurement | Standard } | null>(null);
  const [form, setForm] = useState<FormState>({});
  const [metricRows, setMetricRows] = useState<MetricRow[]>([]);
  const [repeatRows, setRepeatRows] = useState<RepeatRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextSummary, nextMeasurements, nextStandards, nextDefinitions, nextRuns, nextGroups, nextPoints, nextModels, nextColors, nextParts, nextInstruments, nextMethods, nextCalibrations, nextReferences, nextProfiles] =
        await Promise.all([
          request<Summary>("/api/quality/summary"),
          request<Measurement[]>("/api/quality/measurements?limit=500"),
          request<Standard[]>("/api/quality/standards"),
          request<MetricDefinition[]>("/api/quality/metric-definitions"),
          request<ProductionRun[]>("/api/process/production-runs?limit=500"),
          request<Resource[]>("/api/master-data/measurement-groups"),
          request<Resource[]>("/api/master-data/measurement-points"),
          request<Resource[]>("/api/master-data/vehicle-models"),
          request<Resource[]>("/api/master-data/colors"),
          request<Resource[]>("/api/master-data/parts"),
          request<Instrument[]>("/api/quality/governance/instruments"),
          request<Method[]>("/api/quality/governance/methods"),
          request<Calibration[]>("/api/quality/governance/calibrations"),
          request<ReferenceStandard[]>("/api/quality/governance/references"),
          request<ImportProfile[]>("/api/quality/governance/import-profiles"),
        ]);
      setSummary(nextSummary);
      setMeasurements(nextMeasurements);
      setStandards(nextStandards);
      setDefinitions(nextDefinitions);
      setRuns(nextRuns);
      setGroups(nextGroups);
      setPoints(nextPoints);
      setVehicleModels(nextModels);
      setColors(nextColors);
      setParts(nextParts);
      setInstruments(nextInstruments);
      setMethods(nextMethods);
      setCalibrations(nextCalibrations);
      setReferences(nextReferences);
      setImportProfiles(nextProfiles);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "质量数据加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  const analyticsDefinitions = useMemo(
    () => definitions.filter((item) => item.quality_type === (typeFilter || "ORANGE_PEEL")),
    [definitions, typeFilter],
  );
  const resolvedAnalyticsMetric = analyticsDefinitions.some((item) => item.code === analyticsMetric)
    ? analyticsMetric
    : analyticsDefinitions.find((item) => item.is_primary)?.code ?? analyticsDefinitions[0]?.code ?? "";

  const loadAnalytics = useCallback(async () => {
    if (!resolvedAnalyticsMetric) return;
    setAnalyticsLoading(true);
    setAnalytics(null);
    try {
      const parameters = new URLSearchParams({
        quality_type: typeFilter || "ORANGE_PEEL",
        metric_code: resolvedAnalyticsMetric,
        limit: "2000",
      });
      setAnalytics(await request<Analytics>(`/api/quality/analytics?${parameters}`));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "质量分析加载失败");
    } finally {
      setAnalyticsLoading(false);
    }
  }, [resolvedAnalyticsMetric, typeFilter]);

  useEffect(() => {
    if (tab !== "analytics") return;
    const timer = window.setTimeout(() => void loadAnalytics(), 0);
    return () => window.clearTimeout(timer);
  }, [loadAnalytics, tab]);

  const filteredMeasurements = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return measurements.filter(
      (item) =>
        (!typeFilter || item.quality_type === typeFilter) &&
        (!normalized ||
          [item.data_no, item.measurement_point_code, item.measurement_point_name, item.measured_by, item.judgement]
            .some((value) => String(value ?? "").toLowerCase().includes(normalized))),
    );
  }, [measurements, query, typeFilter]);

  const filteredStandards = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return standards.filter(
      (item) =>
        (!typeFilter || item.quality_type === typeFilter) &&
        (!normalized ||
          [item.standard_no, item.metric_code, item.version, item.standard_type]
            .some((value) => String(value ?? "").toLowerCase().includes(normalized))),
    );
  }, [query, standards, typeFilter]);

  function definitionsFor(type: string): MetricDefinition[] {
    return definitions.filter((item) => item.quality_type === type);
  }

  function openMeasurement(record?: Measurement) {
    const qualityType = record?.quality_type ?? "ORANGE_PEEL";
    setModal({ kind: "measurement", record });
    setForm({
      data_no: record?.data_no ?? `QM-${Date.now()}`,
      production_run_id: record?.production_run_id ?? runs[0]?.id ?? "",
      measurement_group_id: record?.measurement_group_id ?? "",
      measurement_point_id: record?.measurement_point_id ?? points[0]?.id ?? "",
      quality_type: qualityType,
      data_type: record?.data_type ?? "TEST",
      measured_at: localDateTime(record?.measured_at),
      measured_by: record?.measured_by ?? "",
      device_code: record?.device_code ?? "",
      instrument_id: record?.instrument_id ?? "",
      measurement_method_id: record?.measurement_method_id ?? "",
      calibration_record_id: record?.calibration_record_id ?? "",
      reference_standard_id: record?.reference_standard_id ?? "",
      import_profile_id: record?.import_profile_id ?? "",
      measurement_direction: record?.measurement_direction ?? "",
      raw_file_uri: record?.raw_file_uri ?? "",
      status_score: record?.status_score === null || record?.status_score === undefined ? "" : String(record.status_score),
      is_valid: record?.is_valid ?? true,
    });
    const firstDefinition = definitionsFor(qualityType)[0];
    setMetricRows(
      record?.metrics.map((metric) => ({
        metric_code: metric.metric_code,
        raw_value: String(metric.raw_value),
        corrected_value: metric.corrected_value === null || metric.corrected_value === undefined ? "" : String(metric.corrected_value),
      })) ?? [{ metric_code: firstDefinition?.code ?? "", raw_value: "", corrected_value: "" }],
    );
    setRepeatRows(
      record?.repeat_readings.map((reading) => ({
        repeat_no: String(reading.repeat_no),
        metric_code: reading.metric_code,
        raw_value: String(reading.raw_value),
        corrected_value: reading.corrected_value === null || reading.corrected_value === undefined ? "" : String(reading.corrected_value),
      })) ?? [{ repeat_no: "1", metric_code: firstDefinition?.code ?? "", raw_value: "", corrected_value: "" }],
    );
  }

  function openStandard(record?: Standard) {
    const qualityType = record?.quality_type ?? "ORANGE_PEEL";
    setModal({ kind: "standard", record });
    setForm({
      standard_no: record?.standard_no ?? `STD-${Date.now()}`,
      version: record?.version ?? "1.0",
      standard_type: record?.standard_type ?? "PRODUCTION",
      quality_type: qualityType,
      metric_code: record?.metric_code ?? definitionsFor(qualityType)[0]?.code ?? "",
      vehicle_model_id: record?.vehicle_model_id ?? "",
      color_id: record?.color_id ?? "",
      part_id: record?.part_id ?? "",
      measurement_point_id: record?.measurement_point_id ?? "",
      min_value: record?.min_value === null || record?.min_value === undefined ? "" : String(record.min_value),
      max_value: record?.max_value === null || record?.max_value === undefined ? "" : String(record.max_value),
      unit: record?.unit ?? "",
      is_active: record?.is_active ?? true,
    });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!modal) return;
    setSubmitting(true);
    setError("");
    try {
      if (modal.kind === "measurement") {
        const metrics = metricRows.map((row) => {
          const definition = definitions.find(
            (item) => item.quality_type === form.quality_type && item.code === row.metric_code,
          );
          if (!definition) throw new Error("存在无效质量指标");
          return {
            metric_code: definition.code,
            metric_name: definition.name,
            raw_value: Number(row.raw_value),
            corrected_value: row.corrected_value === "" ? null : Number(row.corrected_value),
            unit: definition.unit ?? null,
          };
        });
        const repeat_readings = repeatRows
          .filter((row) => row.metric_code && row.raw_value !== "")
          .map((row) => ({
            repeat_no: Number(row.repeat_no),
            metric_code: row.metric_code,
            raw_value: Number(row.raw_value),
            corrected_value: row.corrected_value === "" ? null : Number(row.corrected_value),
            unit: definitions.find((item) => item.quality_type === form.quality_type && item.code === row.metric_code)?.unit ?? null,
            is_valid: true,
          }));
        const body = {
          ...form,
          measurement_group_id: form.measurement_group_id || null,
          instrument_id: form.instrument_id || null,
          measurement_method_id: form.measurement_method_id || null,
          calibration_record_id: form.calibration_record_id || null,
          reference_standard_id: form.reference_standard_id || null,
          import_profile_id: form.import_profile_id || null,
          measurement_direction: form.measurement_direction || null,
          raw_file_uri: form.raw_file_uri || null,
          measured_at: form.measured_at,
          status_score: form.status_score === "" ? null : Number(form.status_score),
          metrics,
          repeat_readings,
        };
        await request(
          modal.record ? `/api/quality/measurements/${modal.record.id}` : "/api/quality/measurements",
          {
            method: modal.record ? "PATCH" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          },
        );
      } else {
        const body = {
          ...form,
          vehicle_model_id: form.vehicle_model_id || null,
          color_id: form.color_id || null,
          part_id: form.part_id || null,
          measurement_point_id: form.measurement_point_id || null,
          min_value: form.min_value === "" ? null : Number(form.min_value),
          max_value: form.max_value === "" ? null : Number(form.max_value),
        };
        await request(
          modal.record ? `/api/quality/standards/${modal.record.id}` : "/api/quality/standards",
          {
            method: modal.record ? "PATCH" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          },
        );
      }
      setNotice(`${modal.kind === "measurement" ? "质量测量" : "质量标准"}${modal.record ? "已更新" : "已创建"}`);
      setModal(null);
      await reload();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  function remove(_path: string, label: string) {
    setNotice("");
    setError(`${label}不能物理删除。${physicalDeleteDisabledMessage}`);
  }

  function bulkResult(message: string, type: "success" | "error") {
    setNotice(type === "success" ? message : "");
    setError(type === "error" ? message : "");
  }

  function exportCsv() {
    const rows = tab === "measurements"
      ? filteredMeasurements.map((item) => [
            item.data_no,
            item.measurement_point_code,
            qualityLabels[item.quality_type] ?? item.quality_type,
            item.metrics.map((metric) => `${metric.metric_code}=${metric.corrected_value ?? metric.raw_value}`).join(";"),
            judgementLabels[item.judgement] ?? item.judgement,
            item.measured_at,
          ])
      : tab === "standards"
        ? filteredStandards.map((item) => [
            item.standard_no,
            item.version,
            qualityLabels[item.quality_type] ?? item.quality_type,
            item.metric_code,
            String(item.min_value ?? ""),
            String(item.max_value ?? ""),
          ])
        : (analytics?.series ?? []).map((item) => [
            item.data_no,
            item.measurement_point_code,
            analytics?.metric_code ?? "",
            String(item.value),
            item.judgement,
            String(item.standard_min ?? ""),
            String(item.standard_max ?? ""),
            item.measured_at,
          ]);
    const headers = tab === "measurements"
      ? ["数据编号", "测量点", "质量类型", "指标值", "判定", "测量时间"]
      : tab === "standards"
        ? ["标准编号", "版本", "质量类型", "指标代码", "下限", "上限"]
        : ["数据编号", "测量点", "指标代码", "指标值", "判定", "标准下限", "标准上限", "测量时间"];
    const content = `\uFEFF${[headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n")}`;
    const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `质量${tab === "measurements" ? "测量" : tab === "standards" ? "标准" : "分析"}-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div><span className="page-kicker">MEASUREMENT · STANDARD · JUDGEMENT</span><h1>质量数据中心</h1><p>维护橘皮、色差/效应和膜厚数据，依据多维质量标准自动判定。</p></div>
        <div className="page-actions">
          <button className="button button-secondary" onClick={() => { void reload(); if (tab === "analytics") void loadAnalytics(); }} disabled={loading || analyticsLoading}><RefreshCw className={loading || analyticsLoading ? "spin" : ""} />刷新</button>
          {tab === "measurements" || tab === "standards" ? <button className="button button-primary" onClick={() => tab === "measurements" ? openMeasurement() : openStandard()}><Plus />新建{tab === "measurements" ? "质量测量" : "质量标准"}</button> : null}
        </div>
      </header>
      <div className="freshness"><span className="live-dot" /> MySQL 实时质量数据 · 自动匹配最具体标准</div>
      <section className="module-stat-strip">
        <article><span>质量测量</span><strong>{loading ? "…" : summary?.measurements ?? 0}</strong><small>{summary?.verified_measurements ?? 0} 条通过可靠性门禁</small></article>
        <article><span>指标值</span><strong>{loading ? "…" : summary?.metric_values ?? 0}</strong><small>当前受治理目录 {definitions.length} 项</small></article>
        <article><span>合格 / 超差</span><strong>{loading ? "…" : `${summary?.pass_measurements ?? 0} / ${summary?.fail_measurements ?? 0}`}</strong><small>按当前生效标准判定</small></article>
        <article><span>可靠性待处理</span><strong>{loading ? "…" : `${summary?.unverified_measurements ?? 0} / ${summary?.failed_reliability_measurements ?? 0}`}</strong><small>未验证 / 失败</small></article>
      </section>
      {error ? <div className="message-banner message-error">{error}</div> : null}
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}

      <section className="panel quality-workspace">
        <div className="master-tabs">
          <button className={tab === "measurements" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setTab("measurements")}>质量测量 <span>{measurements.length}</span></button>
          <button className={tab === "standards" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setTab("standards")}>质量标准 <span>{standards.length}</span></button>
          <button className={tab === "analytics" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setTab("analytics")}>SPC 与趋势 <span>{analytics?.statistics.samples ?? 0}</span></button>
          <button className={tab === "governance" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setTab("governance")}>仪器可靠性 <span>{instruments.length}</span></button>
        </div>
        {tab !== "governance" ? <div className="quality-toolbar">
          {tab !== "analytics" ? <label className="master-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`搜索质量${tab === "measurements" ? "测量" : "标准"}`} /></label> : <div className="quality-analytics-title"><Activity /><span>实时过程能力与点位风险</span></div>}
          <select value={tab === "analytics" ? typeFilter || "ORANGE_PEEL" : typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>{tab !== "analytics" ? <option value="">全部质量类型</option> : null}{Object.entries(qualityLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select>
          {tab === "analytics" ? <select value={resolvedAnalyticsMetric} onChange={(event) => setAnalyticsMetric(event.target.value)}>{analyticsDefinitions.map((item) => <option value={item.code} key={item.code}>{item.name} · {item.code}</option>)}</select> : null}
          {tab === "measurements" || tab === "standards" ? (
            <BulkDataActions
              resourceKey={tab === "measurements" ? "quality.measurements" : "quality.standards"}
              resourceLabel={tab === "measurements" ? "质量测量" : "质量标准"}
              disabled={loading || submitting}
              onImported={reload}
              onResult={bulkResult}
            />
          ) : (
            <button className="button button-secondary" onClick={exportCsv}><Download />导出 CSV</button>
          )}
        </div> : null}
        {tab === "measurements" ? (
          <div className="quality-card-list">
            {filteredMeasurements.map((measurement) => (
              <article className="quality-measurement-card" key={measurement.id}>
                <div className="quality-record-identity"><span className="mono">{measurement.data_no}</span><strong>{measurement.measurement_point_code} · {measurement.measurement_point_name}</strong><small>{qualityLabels[measurement.quality_type]} · {new Date(measurement.measured_at).toLocaleString("zh-CN", { hour12: false })}</small><small className={`reliability-${measurement.reliability_status.toLowerCase()}`}>{reliabilityLabels[measurement.reliability_status] ?? measurement.reliability_status} · {measurement.instrument_code ?? "未绑定仪器"}</small></div>
                <div className="quality-metrics">{measurement.metrics.slice(0, 5).map((metric) => <span key={metric.id}><small>{metric.metric_name}</small><strong className="mono">{metric.corrected_value ?? metric.raw_value} {metric.unit}</strong></span>)}</div>
                <div className={`quality-judgement judgement-${measurement.judgement.toLowerCase()}`}><strong>{judgementLabels[measurement.judgement] ?? measurement.judgement}</strong><small>{measurement.reliability_issues[0] ?? measurement.violations[0] ?? `${measurement.measured_by ?? "未记录测量人"} · ${measurement.data_type}`}</small></div>
                <div className="row-actions"><button className="icon-button" onClick={() => openMeasurement(measurement)} aria-label={`编辑测量 ${measurement.data_no}`}><Pencil /></button><button className="icon-button icon-button-danger" onClick={() => void remove(`/api/quality/measurements/${measurement.id}`, "质量测量")} aria-label={`删除测量 ${measurement.data_no}`}><Trash2 /></button></div>
              </article>
            ))}
          </div>
        ) : tab === "standards" ? (
          <div className="master-table-wrap">
            <table className="master-table quality-standard-table"><thead><tr><th>标准编号</th><th>质量类型 / 指标</th><th>范围</th><th>适用上下文</th><th>状态</th><th>操作</th></tr></thead><tbody>
              {filteredStandards.map((standard) => (
                <tr key={standard.id}><td className="mono">{standard.standard_no} · {standard.version}</td><td>{qualityLabels[standard.quality_type]} / {standard.metric_code}</td><td className="mono">{standard.min_value ?? "—"} ~ {standard.max_value ?? "—"} {standard.unit}</td><td>{[relationName(vehicleModels, standard.vehicle_model_id), relationName(colors, standard.color_id), relationName(parts, standard.part_id), relationName(points, standard.measurement_point_id)].filter((value) => value !== "全部").join(" · ") || "全局标准"}</td><td>{standard.is_active ? "生效" : "停用"}</td><td><div className="row-actions"><button className="icon-button" onClick={() => openStandard(standard)} aria-label={`编辑标准 ${standard.standard_no}`}><Pencil /></button><button className="icon-button icon-button-danger" onClick={() => void remove(`/api/quality/standards/${standard.id}`, "质量标准")} aria-label={`删除标准 ${standard.standard_no}`}><Trash2 /></button></div></td></tr>
              ))}
            </tbody></table>
          </div>
        ) : tab === "analytics" ? <QualityAnalyticsPanel analytics={analytics} loading={analyticsLoading} /> : <MeasurementGovernancePanel />}
      </section>

      {modal ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => !submitting && setModal(null)}>
          <section className="modal-card quality-modal" role="dialog" aria-modal="true" aria-labelledby="quality-modal-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal-heading"><div><span className="eyebrow">{modal.record ? "EDIT" : "CREATE"}</span><h2 id="quality-modal-title">{modal.record ? "编辑" : "新建"}{modal.kind === "measurement" ? "质量测量" : "质量标准"}</h2></div><button className="icon-button" onClick={() => setModal(null)} aria-label="关闭"><X /></button></div>
            <form onSubmit={(event) => void submit(event)}>
              <div className="form-grid">
                {modal.kind === "measurement"
                  ? renderMeasurementForm(form, setForm, metricRows, setMetricRows, repeatRows, setRepeatRows, { runs, groups, points, definitions, instruments, methods, calibrations, references, importProfiles })
                  : renderStandardForm(form, setForm, { vehicleModels, colors, parts, points, definitions })}
              </div>
              <div className="modal-actions"><button className="button button-secondary" type="button" onClick={() => setModal(null)}>取消</button><button className="button button-primary" type="submit" disabled={submitting}>{submitting ? <LoaderCircle className="spin" /> : null}保存到 MySQL</button></div>
            </form>
          </section>
        </div>
      ) : null}
    </div>
  );
}

function analyticsNumber(value?: number | null, digits = 3): string {
  return value === null || value === undefined ? "—" : value.toFixed(digits);
}

function QualityAnalyticsPanel({ analytics, loading }: { analytics: Analytics | null; loading: boolean }) {
  if (loading && !analytics) return <div className="large-empty"><LoaderCircle className="spin" /> 正在聚合质量分析数据</div>;
  if (!analytics || !analytics.series.length) return <div className="large-empty"><Activity /> 当前筛选条件暂无可分析指标数据</div>;
  const statistics = analytics.statistics;
  const quality = analytics.data_quality;
  const dataQualityItems = [
    ["有效数据率", quality.valid_rate, `${quality.valid_measurements}/${quality.total_measurements}`],
    ["指标完整率", quality.metric_completeness, `${quality.measurements_with_metric}/${quality.valid_measurements}`],
    ["标准覆盖率", quality.standard_coverage, `${quality.measurements_with_metric - quality.no_standard_count}/${quality.measurements_with_metric}`],
    ["过程合格率", statistics.pass_rate, `${Math.round(statistics.pass_rate * 100)}%`],
  ] as const;
  return (
    <div className="quality-analytics">
      <section className="quality-analytics-stat-grid">
        <article><span>样本 / 失控点</span><strong>{statistics.samples} / {statistics.out_of_control_count}</strong><small>控制界限采用均值 ± 3σ</small></article>
        <article><span>均值 / σ</span><strong>{analyticsNumber(statistics.mean)} / {analyticsNumber(statistics.sigma)}</strong><small>{analytics.metric_name} · {analytics.unit ?? "无单位"}</small></article>
        <article><span>Cp / Cpk</span><strong>{analyticsNumber(statistics.cp)} / {analyticsNumber(statistics.cpk)}</strong><small>仅在统一双边标准下计算</small></article>
        <article><span>趋势斜率</span><strong className={(statistics.trend_slope ?? 0) >= 0 ? "positive" : "negative"}>{analyticsNumber(statistics.trend_slope, 4)}</strong><small>每个样本的线性变化</small></article>
      </section>
      <div className="quality-analytics-grid">
        <section className="quality-analysis-card quality-trend-card">
          <div className="program-subheading"><div><span className="eyebrow">SPC CONTROL CHART</span><h3>{analytics.metric_name} 趋势与控制图</h3></div><span className="record-status status-on">{qualityLabels[analytics.quality_type] ?? analytics.quality_type}</span></div>
          <SpcTrendChart analytics={analytics} />
          <div className="quality-chart-legend"><span className="legend-value">测量值</span><span className="legend-mean">均值</span><span className="legend-control">控制界限</span><span className="legend-standard">质量标准</span></div>
        </section>
        <section className="quality-analysis-card">
          <div className="program-subheading"><div><span className="eyebrow">DATA QUALITY</span><h3>数据质量监控</h3></div><Activity /></div>
          <div className="quality-data-monitor">
            {dataQualityItems.map(([label, ratio, detail]) => <div key={label}><span><strong>{label}</strong><small>{detail}</small></span><b>{(ratio * 100).toFixed(1)}%</b><span className="quality-progress"><i style={{ width: `${Math.min(100, ratio * 100)}%` }} /></span></div>)}
          </div>
          <div className="quality-data-foot"><span>无效记录 <b>{quality.invalid_measurements}</b></span><span>缺失指标 <b>{quality.missing_metric_count}</b></span><span>无标准 <b>{quality.no_standard_count}</b></span><span>最近测量 <b>{quality.latest_measured_at ? new Date(quality.latest_measured_at).toLocaleString("zh-CN", { hour12: false }) : "—"}</b></span></div>
        </section>
      </div>
      <section className="quality-analysis-card">
        <div className="program-subheading"><div><span className="eyebrow">POINT RISK HEATMAP</span><h3>测量点风险热力图</h3></div><small>综合超差、失控与无标准风险</small></div>
        <div className="quality-risk-heatmap">
          {analytics.point_risks.map((point) => <article key={point.measurement_point_id} style={{ "--risk": `${point.risk_score}%` } as CSSProperties}><span>{point.measurement_point_code}</span><strong>{point.measurement_point_name}</strong><b>{point.risk_score.toFixed(1)}</b><small>{point.samples} 样本 · {point.failures} 超差 · 最新 {analyticsNumber(point.latest_value)}</small></article>)}
        </div>
      </section>
    </div>
  );
}

function SpcTrendChart({ analytics }: { analytics: Analytics }) {
  const width = 960;
  const height = 280;
  const padding = { top: 22, right: 26, bottom: 42, left: 54 };
  const statistics = analytics.statistics;
  const candidates = analytics.series.flatMap((item) => [item.value, item.standard_min, item.standard_max]).filter((value): value is number => value !== null && value !== undefined);
  for (const value of [statistics.ucl, statistics.lcl, statistics.mean]) if (value !== null && value !== undefined) candidates.push(value);
  let minimum = Math.min(...candidates);
  let maximum = Math.max(...candidates);
  if (minimum === maximum) { minimum -= 1; maximum += 1; }
  const margin = (maximum - minimum) * 0.08;
  minimum -= margin;
  maximum += margin;
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const x = (index: number) => padding.left + (analytics.series.length === 1 ? plotWidth / 2 : index / (analytics.series.length - 1) * plotWidth);
  const y = (value: number) => padding.top + (maximum - value) / (maximum - minimum) * plotHeight;
  const path = analytics.series.map((item, index) => `${index ? "L" : "M"} ${x(index)} ${y(item.value)}`).join(" ");
  const referenceLines = [
    ["UCL", statistics.ucl, "control"],
    ["MEAN", statistics.mean, "mean"],
    ["LCL", statistics.lcl, "control"],
  ] as const;
  const standardMinimum = analytics.series.find((item) => item.standard_min !== null && item.standard_min !== undefined)?.standard_min;
  const standardMaximum = analytics.series.find((item) => item.standard_max !== null && item.standard_max !== undefined)?.standard_max;
  return (
    <svg className="quality-spc-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${analytics.metric_name} SPC 控制图`}>
      {[0, 0.25, 0.5, 0.75, 1].map((ratio) => { const value = maximum - ratio * (maximum - minimum); return <g key={ratio}><line className="spc-grid-line" x1={padding.left} x2={width - padding.right} y1={padding.top + ratio * plotHeight} y2={padding.top + ratio * plotHeight} /><text className="spc-axis-label" x={padding.left - 8} y={padding.top + ratio * plotHeight + 3} textAnchor="end">{value.toFixed(2)}</text></g>; })}
      {referenceLines.map(([label, value, kind]) => value === null || value === undefined ? null : <g key={label}><line className={`spc-reference spc-${kind}`} x1={padding.left} x2={width - padding.right} y1={y(value)} y2={y(value)} /><text className={`spc-reference-label spc-${kind}`} x={width - padding.right} y={y(value) - 4} textAnchor="end">{label} {value.toFixed(2)}</text></g>)}
      {[["USL", standardMaximum], ["LSL", standardMinimum]].map(([label, value]) => typeof value !== "number" ? null : <g key={label}><line className="spc-reference spc-standard" x1={padding.left} x2={width - padding.right} y1={y(value)} y2={y(value)} /><text className="spc-reference-label spc-standard" x={padding.left + 4} y={y(value) - 4}>{label} {value.toFixed(2)}</text></g>)}
      <path className="spc-value-line" d={path} />
      {analytics.series.map((item, index) => <g key={item.measurement_id}><circle className={`spc-point spc-point-${item.judgement.toLowerCase()}`} cx={x(index)} cy={y(item.value)} r="4"><title>{item.data_no} · {item.measurement_point_code} · {item.value}</title></circle>{analytics.series.length <= 16 ? <text className="spc-x-label" x={x(index)} y={height - 15} textAnchor="middle">{item.measurement_point_code}</text> : null}</g>)}
    </svg>
  );
}

function inputField(label: string, key: string, form: FormState, setForm: (value: FormState) => void, type = "text", required = false) {
  return <label className="form-field" key={key}><span>{label}{required ? <b>*</b> : null}</span><input type={type} step={type === "number" ? "any" : undefined} required={required} value={String(form[key] ?? "")} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>;
}

function selectField(label: string, key: string, form: FormState, setForm: (value: FormState) => void, options: Array<[string, string]>, required = false) {
  return <label className="form-field" key={key}><span>{label}{required ? <b>*</b> : null}</span><select required={required} value={String(form[key] ?? "")} onChange={(event) => setForm({ ...form, [key]: event.target.value })}>{options.map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></label>;
}

function checkboxField(label: string, key: string, form: FormState, setForm: (value: FormState) => void) {
  return <label className="form-field" key={key}><span>{label}</span><span className="checkbox-field"><input type="checkbox" checked={Boolean(form[key])} onChange={(event) => setForm({ ...form, [key]: event.target.checked })} />{label}</span></label>;
}

function options(items: Resource[], empty = false): Array<[string, string]> {
  return [...(empty ? [["", "全部 / 未关联"] as [string, string]] : []), ...items.map((item) => [item.id, `${item.code} / ${item.name}`] as [string, string])];
}

function renderMeasurementForm(
  form: FormState,
  setForm: (value: FormState) => void,
  metricRows: MetricRow[],
  setMetricRows: (value: MetricRow[]) => void,
  repeatRows: RepeatRow[],
  setRepeatRows: (value: RepeatRow[]) => void,
  refs: {
    runs: ProductionRun[];
    groups: Resource[];
    points: Resource[];
    definitions: MetricDefinition[];
    instruments: Instrument[];
    methods: Method[];
    calibrations: Calibration[];
    references: ReferenceStandard[];
    importProfiles: ImportProfile[];
  },
) {
  const metricOptions = refs.definitions.filter((item) => item.quality_type === form.quality_type);
  const selectedInstrument = refs.instruments.find((item) => item.id === form.instrument_id);
  const instruments = refs.instruments.filter((item) => item.supported_quality_types.includes(String(form.quality_type)));
  const methods = refs.methods.filter((item) => item.quality_type === form.quality_type && (!selectedInstrument || item.instrument_type === selectedInstrument.instrument_type));
  const calibrations = refs.calibrations.filter((item) => (!form.instrument_id || item.instrument_id === form.instrument_id) && (!form.measurement_method_id || !item.method_id || item.method_id === form.measurement_method_id));
  const references = refs.references.filter((item) => item.quality_type === form.quality_type);
  const profiles = refs.importProfiles.filter((item) => item.quality_type === form.quality_type && (!selectedInstrument || item.instrument_type === selectedInstrument.instrument_type));
  return [
    inputField("数据编号", "data_no", form, setForm, "text", true),
    selectField("生产事件", "production_run_id", form, setForm, refs.runs.map((item) => [item.id, `${item.run_no} / ${item.body_no ?? "无车身号"}`]), true),
    selectField("测量编组", "measurement_group_id", form, setForm, options(refs.groups, true)),
    selectField("测量点", "measurement_point_id", form, setForm, options(refs.points), true),
    selectField("质量类型", "quality_type", form, (next) => {
      setForm({ ...next, instrument_id: "", measurement_method_id: "", calibration_record_id: "", reference_standard_id: "", import_profile_id: "" });
      const first = refs.definitions.find((item) => item.quality_type === next.quality_type);
      setMetricRows([{ metric_code: first?.code ?? "", raw_value: "", corrected_value: "" }]);
      setRepeatRows([{ repeat_no: "1", metric_code: first?.code ?? "", raw_value: "", corrected_value: "" }]);
    }, Object.entries(qualityLabels), true),
    selectField("数据类型", "data_type", form, setForm, [["TEST", "测试数据"], ["MASTER_SAMPLE", "封样数据"], ["STANDARD", "标准数据"]], true),
    inputField("测量时间", "measured_at", form, setForm, "datetime-local", true),
    inputField("测量人", "measured_by", form, setForm),
    selectField("受治理仪器", "instrument_id", form, (next) => setForm({ ...next, measurement_method_id: "", calibration_record_id: "", import_profile_id: "" }), options(instruments, true)),
    selectField("测量方法", "measurement_method_id", form, (next) => setForm({ ...next, calibration_record_id: "" }), options(methods, true)),
    selectField("校准/检查记录", "calibration_record_id", form, setForm, [["", "未关联"], ...calibrations.map((item) => [item.id, `${item.calibration_no} / ${item.result} / ${new Date(item.valid_until).toLocaleDateString("zh-CN")}`] as [string, string])]),
    selectField("参考件", "reference_standard_id", form, setForm, options(references, true)),
    selectField("导入模板", "import_profile_id", form, setForm, [["", "手工录入 / 未关联"], ...profiles.map((item) => [item.id, `${item.code}:${item.version}`] as [string, string])]),
    selectField("测量方向", "measurement_direction", form, setForm, [["", "未记录"], ["LONGITUDINAL", "纵向"], ["TRANSVERSE", "横向"], ["NORMAL", "法向 / 不适用"]]),
    inputField("原始文件 URI", "raw_file_uri", form, setForm),
    inputField("状态分数", "status_score", form, setForm, "number"),
    checkboxField("数据有效", "is_valid", form, setForm),
    <div className="metric-editor form-field-wide" key="metrics">
      <div className="program-subheading"><div><span className="eyebrow">METRIC VALUES</span><h3>质量指标值</h3></div><button type="button" className="button button-secondary" onClick={() => setMetricRows([...metricRows, { metric_code: metricOptions[0]?.code ?? "", raw_value: "", corrected_value: "" }])}><Plus />新增指标</button></div>
      {metricRows.map((row, index) => (
        <div className="metric-editor-row" key={`${index}-${row.metric_code}`}>
          <select aria-label={`指标 ${index + 1}`} required value={row.metric_code} onChange={(event) => setMetricRows(metricRows.map((item, rowIndex) => rowIndex === index ? { ...item, metric_code: event.target.value } : item))}>{metricOptions.map((item) => <option value={item.code} key={item.code}>{item.name} · {item.code} ({item.unit})</option>)}</select>
          <input aria-label={`原始值 ${index + 1}`} type="number" step="any" required placeholder="原始值" value={row.raw_value} onChange={(event) => setMetricRows(metricRows.map((item, rowIndex) => rowIndex === index ? { ...item, raw_value: event.target.value } : item))} />
          <input aria-label={`修正值 ${index + 1}`} type="number" step="any" placeholder="修正值（可选）" value={row.corrected_value} onChange={(event) => setMetricRows(metricRows.map((item, rowIndex) => rowIndex === index ? { ...item, corrected_value: event.target.value } : item))} />
          <button type="button" className="icon-button icon-button-danger" onClick={() => setMetricRows(metricRows.filter((_, rowIndex) => rowIndex !== index))} disabled={metricRows.length === 1} aria-label={`删除指标 ${index + 1}`}><Trash2 /></button>
        </div>
      ))}
    </div>,
    <div className="metric-editor form-field-wide" key="repeat-readings">
      <div className="program-subheading"><div><span className="eyebrow">REPEAT READINGS</span><h3>逐次原始读数</h3></div><button type="button" className="button button-secondary" onClick={() => setRepeatRows([...repeatRows, { repeat_no: String(repeatRows.length + 1), metric_code: metricOptions[0]?.code ?? "", raw_value: "", corrected_value: "" }])}><Plus />新增读数</button></div>
      {repeatRows.map((row, index) => (
        <div className="metric-editor-row repeat-editor-row" key={`${index}-${row.repeat_no}-${row.metric_code}`}>
          <input aria-label={`重复序号 ${index + 1}`} type="number" min="1" required value={row.repeat_no} onChange={(event) => setRepeatRows(repeatRows.map((item, rowIndex) => rowIndex === index ? { ...item, repeat_no: event.target.value } : item))} />
          <select aria-label={`逐次指标 ${index + 1}`} required value={row.metric_code} onChange={(event) => setRepeatRows(repeatRows.map((item, rowIndex) => rowIndex === index ? { ...item, metric_code: event.target.value } : item))}>{metricOptions.map((item) => <option value={item.code} key={item.code}>{item.name} · {item.code}</option>)}</select>
          <input aria-label={`逐次原始值 ${index + 1}`} type="number" step="any" required placeholder="原始值" value={row.raw_value} onChange={(event) => setRepeatRows(repeatRows.map((item, rowIndex) => rowIndex === index ? { ...item, raw_value: event.target.value } : item))} />
          <input aria-label={`逐次修正值 ${index + 1}`} type="number" step="any" placeholder="修正值（可选）" value={row.corrected_value} onChange={(event) => setRepeatRows(repeatRows.map((item, rowIndex) => rowIndex === index ? { ...item, corrected_value: event.target.value } : item))} />
          <button type="button" className="icon-button icon-button-danger" onClick={() => setRepeatRows(repeatRows.filter((_, rowIndex) => rowIndex !== index))} aria-label={`删除逐次读数 ${index + 1}`}><Trash2 /></button>
        </div>
      ))}
    </div>,
  ];
}

function renderStandardForm(
  form: FormState,
  setForm: (value: FormState) => void,
  refs: { vehicleModels: Resource[]; colors: Resource[]; parts: Resource[]; points: Resource[]; definitions: MetricDefinition[] },
) {
  const metricOptions = refs.definitions.filter((item) => item.quality_type === form.quality_type);
  return [
    inputField("标准编号", "standard_no", form, setForm, "text", true),
    inputField("版本号", "version", form, setForm, "text", true),
    selectField("标准类型", "standard_type", form, setForm, [["PRODUCTION", "生产标准"], ["MASTER_SAMPLE", "封样标准"], ["LAB", "实验室标准"]], true),
    selectField("质量类型", "quality_type", form, (next) => setForm({ ...next, metric_code: refs.definitions.find((item) => item.quality_type === next.quality_type)?.code ?? "" }), Object.entries(qualityLabels), true),
    selectField("质量指标", "metric_code", form, setForm, metricOptions.map((item) => [item.code, `${item.name} · ${item.code}`]), true),
    inputField("下限", "min_value", form, setForm, "number"),
    inputField("上限", "max_value", form, setForm, "number"),
    inputField("单位", "unit", form, setForm),
    selectField("适用车型", "vehicle_model_id", form, setForm, options(refs.vehicleModels, true)),
    selectField("适用颜色", "color_id", form, setForm, options(refs.colors, true)),
    selectField("适用零件", "part_id", form, setForm, options(refs.parts, true)),
    selectField("适用测量点", "measurement_point_id", form, setForm, options(refs.points, true)),
    checkboxField("标准生效", "is_active", form, setForm),
  ];
}
