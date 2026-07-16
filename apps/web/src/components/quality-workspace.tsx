"use client";

import {
  Activity,
  Download,
  LoaderCircle,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Upload,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { CSSProperties, FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import { BulkDataActions } from "@/components/bulk-data-actions";
import { ModalShell } from "@/components/modal-shell";
import { QualityImportPanel } from "@/components/quality-import-panel";
import { WorkspaceEmptyState } from "@/components/workspace-empty-state";
import {
  MEASUREMENT_STATUS_FILTERS,
  QUALITY_ANALYTICS_TYPE_KEY,
  type MeasurementStatusFilter,
} from "@/lib/quality-hub";
import { useWorkspaceContext } from "@/lib/workspace-context";

type Resource = {
  id: string;
  code: string;
  name: string;
  vehicle_model_id?: string;
  quality_type?: string;
  quality_types?: string[];
};
type MeasurementGroupPointRelation = {
  measurement_group_id: string;
  measurement_point_id: string;
};
type ProductionRun = {
  id: string;
  run_no: string;
  body_no?: string | null;
  started_at: string;
  factory_id?: string;
  vehicle_model_id?: string;
  color_id?: string;
};
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
type Tab = "upload" | "measurements" | "standards" | "analytics";

const TAB_VALUES: Tab[] = ["upload", "measurements", "standards", "analytics"];

function parseTab(value: string | null): Tab {
  if (value && TAB_VALUES.includes(value as Tab)) return value as Tab;
  return "upload";
}

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

/** Soft context match: missing record ids stay visible; conflicting ids are hidden. */
function matchesContextId(recordId?: string | null, contextId?: string): boolean {
  if (!contextId) return true;
  if (!recordId) return true;
  return recordId === contextId;
}

function filterMeasurementGroups(runs: ProductionRun[], groups: Resource[], form: FormState): Resource[] {
  const selectedRun = runs.find((item) => item.id === form.production_run_id);
  return groups.filter(
    (item) =>
      (!selectedRun?.vehicle_model_id || item.vehicle_model_id === selectedRun.vehicle_model_id) &&
      (!form.quality_type || item.quality_type === form.quality_type),
  );
}

function filterMeasurementPoints(
  runs: ProductionRun[],
  points: Resource[],
  groupPoints: MeasurementGroupPointRelation[],
  form: FormState,
): Resource[] {
  const selectedRun = runs.find((item) => item.id === form.production_run_id);
  const selectedGroupId = String(form.measurement_group_id ?? "");
  const allowedPointIds = selectedGroupId
    ? new Set(
        groupPoints
          .filter((item) => item.measurement_group_id === selectedGroupId)
          .map((item) => item.measurement_point_id),
      )
    : null;
  return points.filter((item) => {
    if (selectedRun?.vehicle_model_id && item.vehicle_model_id !== selectedRun.vehicle_model_id) return false;
    if (form.quality_type && !item.quality_types?.includes(String(form.quality_type))) return false;
    if (allowedPointIds && !allowedPointIds.has(item.id)) return false;
    return true;
  });
}

function normalizeMeasurementForm(
  runs: ProductionRun[],
  groups: Resource[],
  groupPoints: MeasurementGroupPointRelation[],
  points: Resource[],
  form: FormState,
): FormState {
  const validGroups = filterMeasurementGroups(runs, groups, form);
  let nextGroupId = String(form.measurement_group_id ?? "");
  if (!nextGroupId && validGroups.length === 1) {
    nextGroupId = validGroups[0]?.id ?? "";
  } else if (nextGroupId && !validGroups.some((item) => item.id === nextGroupId)) {
    nextGroupId = validGroups.length === 1 ? validGroups[0]?.id ?? "" : "";
  }
  const validPoints = filterMeasurementPoints(runs, points, groupPoints, {
    ...form,
    measurement_group_id: nextGroupId,
  });
  const currentPointId = String(form.measurement_point_id ?? "");
  return {
    ...form,
    measurement_group_id: nextGroupId,
    measurement_point_id: validPoints.some((item) => item.id === currentPointId)
      ? currentPointId
      : validPoints[0]?.id ?? "",
  };
}

export function QualityWorkspace({
  mode = "full",
  lockedTab,
}: {
  mode?: "full" | "embed";
  lockedTab?: Tab;
} = {}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { factoryId, modelId, colorId } = useWorkspaceContext();
  const contextFilterActive = Boolean(factoryId || modelId || colorId);
  const showChrome = mode === "full";
  const tab = lockedTab ?? parseTab(searchParams.get("tab"));
  const [summary, setSummary] = useState<Summary | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [analyticsMetric, setAnalyticsMetric] = useState("doi");
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [definitions, setDefinitions] = useState<MetricDefinition[]>([]);
  const [runs, setRuns] = useState<ProductionRun[]>([]);
  const [groups, setGroups] = useState<Resource[]>([]);
  const [groupPoints, setGroupPoints] = useState<MeasurementGroupPointRelation[]>([]);
  const [points, setPoints] = useState<Resource[]>([]);
  const [vehicleModels, setVehicleModels] = useState<Resource[]>([]);
  const [colors, setColors] = useState<Resource[]>([]);
  const [parts, setParts] = useState<Resource[]>([]);
  const [factories, setFactories] = useState<Resource[]>([]);
  const [createRunInline, setCreateRunInline] = useState(false);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [methods, setMethods] = useState<Method[]>([]);
  const [calibrations, setCalibrations] = useState<Calibration[]>([]);
  const [references, setReferences] = useState<ReferenceStandard[]>([]);
  const [importProfiles, setImportProfiles] = useState<ImportProfile[]>([]);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const statusFilter = (searchParams.get("filter") as MeasurementStatusFilter | null) ?? "";
  const [modal, setModal] = useState<{ kind: "measurement" | "standard"; record?: Measurement | Standard } | null>(null);
  const [form, setForm] = useState<FormState>({});
  const [metricRows, setMetricRows] = useState<MetricRow[]>([]);
  const [repeatRows, setRepeatRows] = useState<RepeatRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const closeModal = useCallback(() => {
    if (submitting) return;
    setCreateRunInline(false);
    setModal(null);
  }, [submitting]);

  const setTab = useCallback(
    (next: Tab) => {
      // DomainHub owns ?tab= when embedded; navigate to the hub tab instead of rewriting local state.
      if (lockedTab) {
        const params = new URLSearchParams();
        params.set("tab", next);
        router.replace(`/quality?${params}`, { scroll: false });
        return;
      }
      const params = new URLSearchParams(searchParams.toString());
      if (next === "upload") params.delete("tab");
      else params.set("tab", next);
      params.delete("filter");
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [lockedTab, pathname, router, searchParams],
  );

  const setStatusFilter = useCallback(
    (next: MeasurementStatusFilter) => {
      const params = new URLSearchParams(searchParams.toString());
      if (lockedTab) params.set("tab", "measurements");
      if (!next) params.delete("filter");
      else params.set("filter", next);
      const query = params.toString();
      router.replace(query ? (lockedTab ? `/quality?${query}` : `${pathname}?${query}`) : pathname, {
        scroll: false,
      });
    },
    [lockedTab, pathname, router, searchParams],
  );

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextSummary, nextMeasurements, nextStandards, nextDefinitions, nextRuns, nextGroups, nextGroupPoints, nextPoints, nextModels, nextColors, nextParts, nextFactories, nextInstruments, nextMethods, nextCalibrations, nextReferences, nextProfiles] =
        await Promise.all([
          request<Summary>("/api/quality/summary"),
          request<Measurement[]>("/api/quality/measurements?limit=500"),
          request<Standard[]>("/api/quality/standards"),
          request<MetricDefinition[]>("/api/quality/metric-definitions"),
          request<ProductionRun[]>("/api/process/production-runs?limit=500"),
          request<Resource[]>("/api/master-data/measurement-groups"),
          request<MeasurementGroupPointRelation[]>("/api/master-data/measurement-group-points"),
          request<Resource[]>("/api/master-data/measurement-points"),
          request<Resource[]>("/api/master-data/vehicle-models"),
          request<Resource[]>("/api/master-data/colors"),
          request<Resource[]>("/api/master-data/parts"),
          request<Resource[]>("/api/master-data/factories"),
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
      setGroupPoints(nextGroupPoints);
      setPoints(nextPoints);
      setVehicleModels(nextModels);
      setColors(nextColors);
      setParts(nextParts);
      setFactories(nextFactories);
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
  const setMeasurementForm = useCallback(
    (nextForm: FormState) => {
      setForm(normalizeMeasurementForm(runs, groups, groupPoints, points, nextForm));
    },
    [groupPoints, groups, points, runs],
  );

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
    try {
      const saved = window.localStorage.getItem(QUALITY_ANALYTICS_TYPE_KEY);
      if (saved && ["ORANGE_PEEL", "COLOR_DIFFERENCE", "THICKNESS"].includes(saved)) {
        setTypeFilter((current) => current || saved);
      }
    } catch {
      /* ignore */
    }
  }, [tab]);

  useEffect(() => {
    if (tab !== "analytics" || !typeFilter) return;
    try {
      window.localStorage.setItem(QUALITY_ANALYTICS_TYPE_KEY, typeFilter);
    } catch {
      /* ignore */
    }
  }, [tab, typeFilter]);

  useEffect(() => {
    if (tab !== "analytics") return;
    const timer = window.setTimeout(() => void loadAnalytics(), 0);
    return () => window.clearTimeout(timer);
  }, [loadAnalytics, tab]);

  const runById = useMemo(() => new Map(runs.map((run) => [run.id, run])), [runs]);
  const pointById = useMemo(() => new Map(points.map((point) => [point.id, point])), [points]);

  const filteredMeasurements = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return measurements.filter((item) => {
      if (typeFilter && item.quality_type !== typeFilter) return false;
      if (statusFilter === "fail" && item.judgement !== "FAIL") return false;
      if (statusFilter === "pass" && item.judgement !== "PASS") return false;
      if (statusFilter === "no_standard" && item.judgement !== "NO_STANDARD") return false;
      if (statusFilter === "unverified" && item.reliability_status !== "UNVERIFIED") return false;
      if (statusFilter === "reliability_failed" && item.reliability_status !== "FAILED") return false;
      if (
        normalized &&
        ![item.data_no, item.measurement_point_code, item.measurement_point_name, item.measured_by, item.judgement].some(
          (value) => String(value ?? "").toLowerCase().includes(normalized),
        )
      ) {
        return false;
      }
      const run = runById.get(item.production_run_id);
      const point = pointById.get(item.measurement_point_id);
      if (!matchesContextId(run?.factory_id, factoryId)) return false;
      if (!matchesContextId(run?.vehicle_model_id ?? point?.vehicle_model_id, modelId)) return false;
      if (!matchesContextId(run?.color_id, colorId)) return false;
      return true;
    });
  }, [colorId, factoryId, measurements, modelId, pointById, query, runById, statusFilter, typeFilter]);

  const filteredStandards = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return standards.filter((item) => {
      if (typeFilter && item.quality_type !== typeFilter) return false;
      if (
        normalized &&
        ![item.standard_no, item.metric_code, item.version, item.standard_type].some((value) =>
          String(value ?? "").toLowerCase().includes(normalized),
        )
      ) {
        return false;
      }
      if (!matchesContextId(item.vehicle_model_id, modelId)) return false;
      if (!matchesContextId(item.color_id, colorId)) return false;
      return true;
    });
  }, [colorId, modelId, query, standards, typeFilter]);

  const filteredAnalytics = useMemo(() => {
    if (!analytics) return null;
    if (!contextFilterActive) return analytics;
    const series = analytics.series.filter((item) => {
      const point = pointById.get(item.measurement_point_id);
      return matchesContextId(point?.vehicle_model_id, modelId);
    });
    const pointRisks = analytics.point_risks.filter((item) => {
      const point = pointById.get(item.measurement_point_id);
      return matchesContextId(point?.vehicle_model_id, modelId);
    });
    return { ...analytics, series, point_risks: pointRisks };
  }, [analytics, contextFilterActive, modelId, pointById]);

  function definitionsFor(type: string): MetricDefinition[] {
    return definitions.filter((item) => item.quality_type === type);
  }

  function openMeasurement(record?: Measurement) {
    const qualityType = record?.quality_type ?? "ORANGE_PEEL";
    const initialForm: FormState = {
      data_no: record?.data_no ?? `QM-${Date.now()}`,
      production_run_id: record?.production_run_id ?? runs[0]?.id ?? "",
      measurement_group_id: record?.measurement_group_id ?? "",
      measurement_point_id: record?.measurement_point_id ?? "",
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
      new_run_no: `RUN-${Date.now()}`,
      new_body_no: "",
      new_factory_id: factoryId || factories[0]?.id || "",
      new_vehicle_model_id: modelId || vehicleModels[0]?.id || "",
      new_color_id: colorId || colors[0]?.id || "",
      new_shift: "",
      new_started_at: localDateTime(),
    };
    setCreateRunInline(!record && runs.length === 0);
    setModal({ kind: "measurement", record });
    setMeasurementForm(initialForm);
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
        let productionRunId = String(form.production_run_id || "");
        if (!modal.record && createRunInline) {
          const createdRun = await request<ProductionRun>("/api/process/production-runs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              run_no: form.new_run_no,
              body_no: form.new_body_no || null,
              factory_id: form.new_factory_id,
              vehicle_model_id: form.new_vehicle_model_id,
              color_id: form.new_color_id,
              shift: form.new_shift || null,
              started_at: form.new_started_at,
              completed_at: null,
            }),
          });
          productionRunId = createdRun.id;
          setRuns((prev) => [createdRun, ...prev]);
        }
        if (!productionRunId) throw new Error("请选择已有生产事件，或勾选「同时新建生产事件」");
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
          data_no: form.data_no,
          production_run_id: productionRunId,
          measurement_group_id: form.measurement_group_id || null,
          measurement_point_id: form.measurement_point_id,
          quality_type: form.quality_type,
          data_type: form.data_type,
          measured_at: form.measured_at,
          measured_by: form.measured_by || null,
          device_code: form.device_code || null,
          instrument_id: form.instrument_id || null,
          measurement_method_id: form.measurement_method_id || null,
          calibration_record_id: form.calibration_record_id || null,
          reference_standard_id: form.reference_standard_id || null,
          import_profile_id: form.import_profile_id || null,
          measurement_direction: form.measurement_direction || null,
          raw_file_uri: form.raw_file_uri || null,
          status_score: form.status_score === "" ? null : Number(form.status_score),
          is_valid: form.is_valid,
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
        setCreateRunInline(false);
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
        : (filteredAnalytics?.series ?? []).map((item) => [
            item.data_no,
            item.measurement_point_code,
            filteredAnalytics?.metric_code ?? "",
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

  const content = (
    <>
      {showChrome ? (
      <header className="page-header">
        <div>
          <span className="page-kicker">查看与判定</span>
          <h1>质量数据中心</h1>
          <p>
            批量上传质量数据、查看判定结果、维护标准与仪器可靠性。日常上数请用「批量上传」；本页其余 Tab 负责查看、补录与治理。
          </p>
        </div>
        <div className="page-actions">
          {tab !== "upload" ? (
            <button className="button button-secondary" onClick={() => { void reload(); if (tab === "analytics") void loadAnalytics(); }} disabled={loading || analyticsLoading}>
              <RefreshCw className={loading || analyticsLoading ? "spin" : ""} />刷新
            </button>
          ) : null}
          {tab === "upload" ? (
            <button className="button button-secondary" onClick={() => setTab("measurements")}>
              查看已导入质量
            </button>
          ) : null}
          {tab === "measurements" || tab === "standards" ? (
            <button className="button button-primary" onClick={() => (tab === "measurements" ? openMeasurement() : openStandard())}>
              <Plus />新建{tab === "measurements" ? "质量测量" : "质量标准"}
            </button>
          ) : null}
        </div>
      </header>
      ) : (
        <div className="embedded-toolbar">
          {tab !== "upload" ? (
            <button className="button button-secondary" onClick={() => { void reload(); if (tab === "analytics") void loadAnalytics(); }} disabled={loading || analyticsLoading}>
              <RefreshCw className={loading || analyticsLoading ? "spin" : ""} />刷新
            </button>
          ) : null}
          {tab === "measurements" || tab === "standards" ? (
            <button className="button button-primary" onClick={() => (tab === "measurements" ? openMeasurement() : openStandard())}>
              <Plus />新建{tab === "measurements" ? "质量测量" : "质量标准"}
            </button>
          ) : null}
        </div>
      )}
      {showChrome ? <div className="freshness"><span className="live-dot" /> 实时质量数据 · 批量上传可自动创建生产事件</div> : null}
      {showChrome && tab !== "upload" ? (
        <section className="module-stat-strip">
          <article><span>质量测量</span><strong>{loading ? "…" : summary?.measurements ?? 0}</strong><small>{summary?.verified_measurements ?? 0} 条通过可靠性门禁</small></article>
          <article><span>指标值</span><strong>{loading ? "…" : summary?.metric_values ?? 0}</strong><small>当前受治理目录 {definitions.length} 项</small></article>
          <article><span>合格 / 超差</span><strong>{loading ? "…" : `${summary?.pass_measurements ?? 0} / ${summary?.fail_measurements ?? 0}`}</strong><small>按当前生效标准判定</small></article>
          <article><span>可靠性待处理</span><strong>{loading ? "…" : `${summary?.unverified_measurements ?? 0} / ${summary?.failed_reliability_measurements ?? 0}`}</strong><small>未验证 / 失败</small></article>
        </section>
      ) : null}
      {error ? <div className="message-banner message-error">{error}</div> : null}
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}
      {showChrome && tab !== "upload" ? <div className="freshness">记录采用追加与版本修订，不支持直接删除。单条补录可在「查看与判定」中新建；批量请用「批量上传」。</div> : null}

      <section className={showChrome ? "panel quality-workspace" : "quality-workspace embedded-workspace"}>
        {showChrome ? (
        <div className="master-tabs">
          <button className={tab === "upload" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setTab("upload")}>
            <Upload aria-hidden="true" /> 批量上传
          </button>
          <button className={tab === "measurements" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setTab("measurements")}>查看与判定 <span>{measurements.length}</span></button>
          <button className={tab === "standards" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setTab("standards")}>质量标准 <span>{standards.length}</span></button>
          <button className={tab === "analytics" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setTab("analytics")}>SPC 与趋势 <span>{filteredAnalytics?.series.length ?? analytics?.statistics.samples ?? 0}</span></button>
        </div>
        ) : null}
        {tab === "upload" ? (
          <QualityImportPanel embedded onImported={() => void reload()} />
        ) : null}
        {tab !== "upload" ? <div className="quality-toolbar">
          {tab !== "analytics" ? <label className="master-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`搜索质量${tab === "measurements" ? "测量" : "标准"}`} /></label> : <div className="quality-analytics-title"><Activity /><span>实时过程能力与点位风险</span></div>}
          {contextFilterActive ? <span className="context-filter-hint">已按顶部作业范围筛选</span> : null}
          <select value={tab === "analytics" ? typeFilter || "ORANGE_PEEL" : typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>{tab !== "analytics" ? <option value="">全部质量类型</option> : null}{Object.entries(qualityLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select>
          {tab === "analytics" ? <select value={resolvedAnalyticsMetric} onChange={(event) => setAnalyticsMetric(event.target.value)}>{analyticsDefinitions.map((item) => <option value={item.code} key={item.code}>{item.name} · {item.code}</option>)}</select> : null}
          {tab === "measurements" ? (
            <div className="quality-status-filters" role="group" aria-label="判定与可靠性筛选">
              {MEASUREMENT_STATUS_FILTERS.map((item) => (
                <button
                  key={item.key || "all"}
                  type="button"
                  className={`quality-status-chip ${statusFilter === item.key ? "is-active" : ""}`}
                  onClick={() => setStatusFilter(item.key)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          ) : null}
          {tab === "measurements" ? (
            <button className="button button-secondary" type="button" onClick={() => setTab("upload")}>
              <Upload /> 去批量上传
            </button>
          ) : null}
          {tab === "standards" ? (
            <BulkDataActions
              resourceKey="quality.standards"
              resourceLabel="质量标准"
              disabled={loading || submitting}
              onImported={reload}
              onResult={bulkResult}
            />
          ) : null}
          {tab === "analytics" ? (
            <button className="button button-secondary" onClick={exportCsv}><Download />导出 CSV</button>
          ) : null}
        </div> : null}
        {tab === "measurements" ? (
          <div className="quality-card-list">
            {filteredMeasurements.map((measurement) => (
              <article className="quality-measurement-card" key={measurement.id}>
                <div className="quality-record-identity"><span className="mono">{measurement.data_no}</span><strong>{measurement.measurement_point_code} · {measurement.measurement_point_name}</strong><small>{qualityLabels[measurement.quality_type]} · {new Date(measurement.measured_at).toLocaleString("zh-CN", { hour12: false })}</small><small className={`reliability-${measurement.reliability_status.toLowerCase()}`}>{reliabilityLabels[measurement.reliability_status] ?? measurement.reliability_status} · {measurement.instrument_code ?? "未绑定仪器"}</small></div>
                <div className="quality-metrics">{measurement.metrics.slice(0, 5).map((metric) => <span key={metric.id}><small>{metric.metric_name}</small><strong className="mono">{metric.corrected_value ?? metric.raw_value} {metric.unit}</strong></span>)}</div>
                <div className={`quality-judgement judgement-${measurement.judgement.toLowerCase()}`}><strong>{judgementLabels[measurement.judgement] ?? measurement.judgement}</strong><small>{measurement.reliability_issues[0] ?? measurement.violations[0] ?? `${measurement.measured_by ?? "未记录测量人"} · ${{ TEST: "测试数据", MASTER_SAMPLE: "封样数据", STANDARD: "标准数据" }[measurement.data_type] ?? measurement.data_type}`}</small></div>
                <div className="row-actions"><button className="icon-button" onClick={() => openMeasurement(measurement)} aria-label={`编辑测量 ${measurement.data_no}`}><Pencil /></button></div>
              </article>
            ))}
            {!filteredMeasurements.length ? (
              <WorkspaceEmptyState
                icon={Activity}
                title="暂无质量测量记录"
                description="日常请切到「批量上传」一次写入车身上下文与质量数据；也可点新建做单条补录。"
                compact
              />
            ) : null}
          </div>
        ) : tab === "standards" ? (
          <div className="master-table-wrap">
            <table className="master-table quality-standard-table"><thead><tr><th>标准编号</th><th>质量类型 / 指标</th><th>范围</th><th>适用上下文</th><th>状态</th><th>操作</th></tr></thead><tbody>
              {filteredStandards.map((standard) => (
                <tr key={standard.id}><td className="mono">{standard.standard_no} · {standard.version}</td><td>{qualityLabels[standard.quality_type]} · {definitions.find((item) => item.quality_type === standard.quality_type && item.code === standard.metric_code)?.name ?? standard.metric_code}</td><td className="mono">{standard.min_value ?? "—"} ~ {standard.max_value ?? "—"} {standard.unit}</td><td>{[relationName(vehicleModels, standard.vehicle_model_id), relationName(colors, standard.color_id), relationName(parts, standard.part_id), relationName(points, standard.measurement_point_id)].filter((value) => value !== "全部").join(" · ") || "全局标准"}</td><td>{standard.is_active ? "生效" : "停用"}</td><td><div className="row-actions"><button className="icon-button" onClick={() => openStandard(standard)} aria-label={`编辑标准 ${standard.standard_no}`}><Pencil /></button></div></td></tr>
              ))}
            </tbody></table>
          </div>
        ) : tab === "analytics" ? (
          <QualityAnalyticsPanel analytics={filteredAnalytics} loading={analyticsLoading} />
        ) : null}
      </section>

      {modal ? (
        <ModalShell className="quality-modal" eyebrow={modal.record ? "编辑" : "新建"} title={`${modal.record ? "编辑" : "新建"}${modal.kind === "measurement" ? "质量测量" : "质量标准"}`} description={modal.kind === "measurement" ? "可选择已有生产事件，或在本表单内同时新建生产事件后再录入质量数据。日常批量请用「批量上传」Tab。" : "统一维护质量标准的适用范围、上下限和状态信息。"} onClose={closeModal} busy={submitting}>
          <form onSubmit={(event) => void submit(event)}>
            <div className="form-grid">
              {modal.kind === "measurement"
                ? renderMeasurementForm(form, setMeasurementForm, metricRows, setMetricRows, repeatRows, setRepeatRows, { runs, groups, groupPoints, points, definitions, instruments, methods, calibrations, references, importProfiles, factories, vehicleModels, colors }, { createRunInline, setCreateRunInline, isEdit: Boolean(modal.record) })
                : renderStandardForm(form, setForm, { vehicleModels, colors, parts, points, definitions })}
            </div>
            <div className="modal-actions"><button className="button button-secondary" type="button" onClick={closeModal} disabled={submitting}>取消</button><button className="button button-primary" type="submit" disabled={submitting}>{submitting ? <LoaderCircle className="spin" aria-hidden="true" /> : null}{submitting ? "正在保存" : "保存"}</button></div>
          </form>
        </ModalShell>
      ) : null}
    </>
  );

  if (!showChrome) return <div className="embedded-stack">{content}</div>;
  return <div className="page-stack">{content}</div>;
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
      <div className="quality-escalation-strip">
        <span>发现风险后可继续：</span>
        <Link className="button button-secondary" href="/quality?tab=body-map">车身点位图</Link>
        <Link className="button button-secondary" href="/quality?tab=measurements&filter=fail">超差判定</Link>
        <Link className="button button-secondary" href="/ai?tab=predictions">AI 预测诊断</Link>
        <Link className="button button-secondary" href="/ai?tab=issues">问题与调试</Link>
      </div>
      <section className="quality-analytics-stat-grid">
        <article><span>样本 / 失控点</span><strong>{statistics.samples} / {statistics.out_of_control_count}</strong><small>控制界限采用均值 ± 3σ</small></article>
        <article><span>均值 / σ</span><strong>{analyticsNumber(statistics.mean)} / {analyticsNumber(statistics.sigma)}</strong><small>{analytics.metric_name} · {analytics.unit ?? "无单位"}</small></article>
        <article><span>Cp / Cpk</span><strong>{analyticsNumber(statistics.cp)} / {analyticsNumber(statistics.cpk)}</strong><small>仅在统一双边标准下计算</small></article>
        <article><span>趋势斜率</span><strong className={(statistics.trend_slope ?? 0) >= 0 ? "positive" : "negative"}>{analyticsNumber(statistics.trend_slope, 4)}</strong><small>每个样本的线性变化</small></article>
      </section>
      <div className="quality-analytics-grid">
        <section className="quality-analysis-card quality-trend-card">
          <div className="program-subheading"><div><span className="eyebrow">控制图与趋势</span><h3>{analytics.metric_name} 趋势与控制图</h3></div><span className="record-status status-on">{qualityLabels[analytics.quality_type] ?? analytics.quality_type}</span></div>
          <SpcTrendChart analytics={analytics} />
          <div className="quality-chart-legend"><span className="legend-value">测量值</span><span className="legend-mean">均值</span><span className="legend-control">控制界限</span><span className="legend-standard">质量标准</span></div>
        </section>
        <section className="quality-analysis-card">
          <div className="program-subheading"><div><span className="eyebrow">数据质量</span><h3>数据质量监控</h3></div><Activity /></div>
          <div className="quality-data-monitor">
            {dataQualityItems.map(([label, ratio, detail]) => <div key={label}><span><strong>{label}</strong><small>{detail}</small></span><b>{(ratio * 100).toFixed(1)}%</b><span className="quality-progress"><i style={{ width: `${Math.min(100, ratio * 100)}%` }} /></span></div>)}
          </div>
          <div className="quality-data-foot"><span>无效记录 <b>{quality.invalid_measurements}</b></span><span>缺失指标 <b>{quality.missing_metric_count}</b></span><span>无标准 <b>{quality.no_standard_count}</b></span><span>最近测量 <b>{quality.latest_measured_at ? new Date(quality.latest_measured_at).toLocaleString("zh-CN", { hour12: false }) : "—"}</b></span></div>
        </section>
      </div>
      <section className="quality-analysis-card">
        <div className="program-subheading"><div><span className="eyebrow">点位风险</span><h3>测量点风险热力图</h3></div><small>综合超差、失控与无标准风险</small></div>
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
    groupPoints: MeasurementGroupPointRelation[];
    points: Resource[];
    definitions: MetricDefinition[];
    instruments: Instrument[];
    methods: Method[];
    calibrations: Calibration[];
    references: ReferenceStandard[];
    importProfiles: ImportProfile[];
    factories: Resource[];
    vehicleModels: Resource[];
    colors: Resource[];
  },
  inline: { createRunInline: boolean; setCreateRunInline: (value: boolean) => void; isEdit: boolean },
) {
  const metricOptions = refs.definitions.filter((item) => item.quality_type === form.quality_type);
  const groups = filterMeasurementGroups(refs.runs, refs.groups, form);
  const points = filterMeasurementPoints(refs.runs, refs.points, refs.groupPoints, form);
  const selectedInstrument = refs.instruments.find((item) => item.id === form.instrument_id);
  const instruments = refs.instruments.filter((item) => item.supported_quality_types.includes(String(form.quality_type)));
  const methods = refs.methods.filter((item) => item.quality_type === form.quality_type && (!selectedInstrument || item.instrument_type === selectedInstrument.instrument_type));
  const calibrations = refs.calibrations.filter((item) => (!form.instrument_id || item.instrument_id === form.instrument_id) && (!form.measurement_method_id || !item.method_id || item.method_id === form.measurement_method_id));
  const references = refs.references.filter((item) => item.quality_type === form.quality_type);
  const profiles = refs.importProfiles.filter((item) => item.quality_type === form.quality_type && (!selectedInstrument || item.instrument_type === selectedInstrument.instrument_type));
  const { createRunInline, setCreateRunInline, isEdit } = inline;
  return [
    <FormSection key="measurement-basic" title="采集上下文" description="先确认生产事件、质量类型、测量编组和测量点。找不到生产事件时可在本表单内新建；日常批量请用「批量上传」Tab。">
      <div className="modal-section-grid">
        {inputField("数据编号", "data_no", form, setForm, "text", true)}
        {!isEdit ? (
          <label className="form-field form-field-wide">
            <span>生产事件来源</span>
            <span className="checkbox-field">
              <input
                type="checkbox"
                checked={createRunInline}
                onChange={(event) => {
                  setCreateRunInline(event.target.checked);
                  if (event.target.checked) {
                    setForm({ ...form, production_run_id: "" });
                  }
                }}
              />
              同时新建生产事件（车号 / 工厂 / 车型 / 颜色）
            </span>
          </label>
        ) : null}
        {createRunInline && !isEdit ? (
          <>
            {inputField("生产事件编号", "new_run_no", form, setForm, "text", true)}
            {inputField("车身号", "new_body_no", form, setForm)}
            {selectField("工厂", "new_factory_id", form, setForm, options(refs.factories), true)}
            {selectField("车型", "new_vehicle_model_id", form, setForm, options(refs.vehicleModels), true)}
            {selectField("颜色", "new_color_id", form, setForm, options(refs.colors), true)}
            {inputField("班次", "new_shift", form, setForm)}
            {inputField("生产开始时间", "new_started_at", form, setForm, "datetime-local", true)}
          </>
        ) : (
          selectField("生产事件", "production_run_id", form, setForm, refs.runs.map((item) => [item.id, `${item.run_no} / ${item.body_no ?? "无车身号"}`]), true)
        )}
        <label className="form-field form-field-wide"><span>录入提示</span><div className="panel-note">测量编组会按当前生产事件车型与质量类型过滤；若命中单一编组，表单会自动收口到该编组，并同步过滤可选测量点。批量上数请切到「批量上传」。</div></label>
        {selectField("测量编组", "measurement_group_id", form, setForm, options(groups, true))}
        {selectField("测量点", "measurement_point_id", form, setForm, options(points), true)}
        {selectField("质量类型", "quality_type", form, (next) => {
          setForm({ ...next, instrument_id: "", measurement_method_id: "", calibration_record_id: "", reference_standard_id: "", import_profile_id: "" });
          const first = refs.definitions.find((item) => item.quality_type === next.quality_type);
          setMetricRows([{ metric_code: first?.code ?? "", raw_value: "", corrected_value: "" }]);
          setRepeatRows([{ repeat_no: "1", metric_code: first?.code ?? "", raw_value: "", corrected_value: "" }]);
        }, Object.entries(qualityLabels), true)}
        {selectField("数据类型", "data_type", form, setForm, [["TEST", "测试数据"], ["MASTER_SAMPLE", "封样数据"], ["STANDARD", "标准数据"]], true)}
        {inputField("测量时间", "measured_at", form, setForm, "datetime-local", true)}
        {inputField("测量人", "measured_by", form, setForm)}
      </div>
    </FormSection>,
    <FormSection key="measurement-governance" title="治理对象与可靠性" description="补齐受治理仪器、方法、校准、参考件和导入模板，支撑可靠性判定。">
      <div className="modal-section-grid">
        {selectField("受治理仪器", "instrument_id", form, (next) => setForm({ ...next, measurement_method_id: "", calibration_record_id: "", import_profile_id: "" }), options(instruments, true))}
        {selectField("测量方法", "measurement_method_id", form, (next) => setForm({ ...next, calibration_record_id: "" }), options(methods, true))}
        {selectField("校准/检查记录", "calibration_record_id", form, setForm, [["", "未关联"], ...calibrations.map((item) => [item.id, `${item.calibration_no} / ${item.result} / ${new Date(item.valid_until).toLocaleDateString("zh-CN")}`] as [string, string])])}
        {selectField("参考件", "reference_standard_id", form, setForm, options(references, true))}
        {selectField("导入模板", "import_profile_id", form, setForm, [["", "手工录入 / 未关联"], ...profiles.map((item) => [item.id, `${item.code}:${item.version}`] as [string, string])])}
        {selectField("测量方向", "measurement_direction", form, setForm, [["", "未记录"], ["LONGITUDINAL", "纵向"], ["TRANSVERSE", "横向"], ["NORMAL", "法向 / 不适用"]])}
        {inputField("原始文件 URI", "raw_file_uri", form, setForm)}
        {inputField("状态分数", "status_score", form, setForm, "number")}
        {checkboxField("数据有效", "is_valid", form, setForm)}
      </div>
    </FormSection>,
    <FormSection key="measurement-results" title="结果明细" description="按行录入质量指标值和逐次原始读数，不再挤在同一块平铺表单中。">
      <div className="modal-section-grid">
        <div className="metric-editor form-field-wide" key="metrics">
      <div className="program-subheading"><div><span className="eyebrow">测量指标</span><h3>质量指标值</h3></div><button type="button" className="button button-secondary" onClick={() => setMetricRows([...metricRows, { metric_code: metricOptions[0]?.code ?? "", raw_value: "", corrected_value: "" }])}><Plus />新增指标</button></div>
      <div className="panel-note">指标值属于当前表单内容调整，至少保留 1 条有效指标后才能保存。</div>
      {metricRows.map((row, index) => (
        <div className="metric-editor-row" key={`${index}-${row.metric_code}`}>
          <select aria-label={`指标 ${index + 1}`} required value={row.metric_code} onChange={(event) => setMetricRows(metricRows.map((item, rowIndex) => rowIndex === index ? { ...item, metric_code: event.target.value } : item))}>{metricOptions.map((item) => <option value={item.code} key={item.code}>{item.name} · {item.code} ({item.unit})</option>)}</select>
          <input aria-label={`原始值 ${index + 1}`} type="number" step="any" required placeholder="原始值" value={row.raw_value} onChange={(event) => setMetricRows(metricRows.map((item, rowIndex) => rowIndex === index ? { ...item, raw_value: event.target.value } : item))} />
          <input aria-label={`修正值 ${index + 1}`} type="number" step="any" placeholder="修正值（可选）" value={row.corrected_value} onChange={(event) => setMetricRows(metricRows.map((item, rowIndex) => rowIndex === index ? { ...item, corrected_value: event.target.value } : item))} />
          <button
            type="button"
            className="button button-secondary"
            onClick={() => setMetricRows(metricRows.filter((_, rowIndex) => rowIndex !== index))}
            disabled={metricRows.length === 1}
            aria-label={`移除指标行 ${index + 1}`}
          >
            移除此行
          </button>
        </div>
      ))}
    </div>
        <div className="metric-editor form-field-wide" key="repeat-readings">
      <div className="program-subheading"><div><span className="eyebrow">重复读数</span><h3>逐次原始读数</h3></div><button type="button" className="button button-secondary" onClick={() => setRepeatRows([...repeatRows, { repeat_no: String(repeatRows.length + 1), metric_code: metricOptions[0]?.code ?? "", raw_value: "", corrected_value: "" }])}><Plus />新增读数</button></div>
      <div className="master-empty">逐次读数可按需填写；如果当前没有重复测量，可留空或移除未填写的行。</div>
      {repeatRows.length === 0 ? <div className="master-empty">暂未填写逐次读数，可按需新增。</div> : null}
      {repeatRows.map((row, index) => (
        <div className="metric-editor-row repeat-editor-row" key={`${index}-${row.repeat_no}-${row.metric_code}`}>
          <input aria-label={`重复序号 ${index + 1}`} type="number" min="1" value={row.repeat_no} onChange={(event) => setRepeatRows(repeatRows.map((item, rowIndex) => rowIndex === index ? { ...item, repeat_no: event.target.value } : item))} />
          <select aria-label={`逐次指标 ${index + 1}`} value={row.metric_code} onChange={(event) => setRepeatRows(repeatRows.map((item, rowIndex) => rowIndex === index ? { ...item, metric_code: event.target.value } : item))}>{metricOptions.map((item) => <option value={item.code} key={item.code}>{item.name} · {item.code}</option>)}</select>
          <input aria-label={`逐次原始值 ${index + 1}`} type="number" step="any" placeholder="原始值" value={row.raw_value} onChange={(event) => setRepeatRows(repeatRows.map((item, rowIndex) => rowIndex === index ? { ...item, raw_value: event.target.value } : item))} />
          <input aria-label={`逐次修正值 ${index + 1}`} type="number" step="any" placeholder="修正值（可选）" value={row.corrected_value} onChange={(event) => setRepeatRows(repeatRows.map((item, rowIndex) => rowIndex === index ? { ...item, corrected_value: event.target.value } : item))} />
          <button
            type="button"
            className="button button-secondary"
            onClick={() => setRepeatRows(repeatRows.filter((_, rowIndex) => rowIndex !== index))}
            aria-label={`移除逐次读数行 ${index + 1}`}
          >
            移除此行
          </button>
        </div>
      ))}
    </div>
      </div>
    </FormSection>,
  ];
}

function renderStandardForm(
  form: FormState,
  setForm: (value: FormState) => void,
  refs: { vehicleModels: Resource[]; colors: Resource[]; parts: Resource[]; points: Resource[]; definitions: MetricDefinition[] },
) {
  const metricOptions = refs.definitions.filter((item) => item.quality_type === form.quality_type);
  return [
    <FormSection key="standard-basic" title="标准定义" description="先明确标准编号、版本、质量类型和指标口径。">
      <div className="modal-section-grid">
        {inputField("标准编号", "standard_no", form, setForm, "text", true)}
        {inputField("版本号", "version", form, setForm, "text", true)}
        {selectField("标准类型", "standard_type", form, setForm, [["PRODUCTION", "生产标准"], ["MASTER_SAMPLE", "封样标准"], ["LAB", "实验室标准"]], true)}
        {selectField("质量类型", "quality_type", form, (next) => setForm({ ...next, metric_code: refs.definitions.find((item) => item.quality_type === next.quality_type)?.code ?? "" }), Object.entries(qualityLabels), true)}
        {selectField("质量指标", "metric_code", form, setForm, metricOptions.map((item) => [item.code, `${item.name} · ${item.code}`]), true)}
        {inputField("下限", "min_value", form, setForm, "number")}
        {inputField("上限", "max_value", form, setForm, "number")}
        {inputField("单位", "unit", form, setForm)}
      </div>
    </FormSection>,
    <FormSection key="standard-scope" title="适用范围" description="按车型、颜色、零件和测量点收口当前标准的适用边界。">
      <div className="modal-section-grid">
        {selectField("适用车型", "vehicle_model_id", form, setForm, options(refs.vehicleModels, true))}
        {selectField("适用颜色", "color_id", form, setForm, options(refs.colors, true))}
        {selectField("适用零件", "part_id", form, setForm, options(refs.parts, true))}
        {selectField("适用测量点", "measurement_point_id", form, setForm, options(refs.points, true))}
        {checkboxField("标准生效", "is_active", form, setForm)}
      </div>
    </FormSection>,
  ];
}

function FormSection({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <div className="modal-section form-field-wide">
      <div className="modal-section-title">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      {children}
    </div>
  );
}