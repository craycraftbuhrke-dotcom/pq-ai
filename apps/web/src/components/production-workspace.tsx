"use client";

import {
  Activity,
  Boxes,
  LoaderCircle,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Upload,
  X,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import { BulkDataActions } from "@/components/bulk-data-actions";
import { BodyMapQualitySummaryGrid, type BodyMapQualitySummary } from "@/components/body-map-quality-summary-grid";
import { ModalShell } from "@/components/modal-shell";
import { JsonObjectEditor } from "@/components/structured-json-editor";
import { MaterialGovernancePanel } from "@/components/material-governance-panel";
import {
  QUALITY_TYPE_LABELS,
  stageLabel,
  statusLabel,
} from "@/lib/display-labels";
import { useWorkspaceContext } from "@/lib/workspace-context";

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
type MeasurementGroup = Resource & {
  vehicle_model_id: string;
  quality_type: string;
  expected_point_count?: number | null;
};
type MeasurementPoint = Resource & {
  vehicle_model_id: string;
  part_id: string;
  region?: string | null;
  quality_types?: string[];
};
type GroupPointRelation = {
  measurement_group_id: string;
  measurement_point_id: string;
  sequence_no: number;
};
type QualitySummary = BodyMapQualitySummary;
type BrushParameter = {
  parameter_code: string;
  parameter_name: string;
  configured_value?: number | null;
  actual_value?: number | null;
  unit: string;
};
type BrushContribution = {
  brush_id: string;
  brush_no: string;
  brush_table_no: string;
  process_stage: string;
  coating_system: string;
  overlap_ratio: number;
  contribution_weight: number;
  contribution_source?: string;
  is_approved: boolean;
  target_family?: string | null;
  parameters: BrushParameter[];
};
type PointDetail = {
  measurement_point_id: string;
  code: string;
  name: string;
  part_code?: string | null;
  part_name?: string | null;
  region?: string | null;
  quality_summaries: QualitySummary[];
  brush_contributions: BrushContribution[];
};
type ModalKind = "run" | "material" | "stage" | "actual";
type Modal = { kind: ModalKind; record?: ProductionRun | Material | StageRun | ActualParameter } | null;
type FormState = Record<string, string>;

const COATING_LABELS: Record<string, string> = {
  MIDCOAT: "中涂",
  BASECOAT: "色漆",
  CLEARCOAT: "清漆",
};

function formatMetricValue(value?: number | null, unit?: string | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  const text = Number.isInteger(value) ? String(value) : value.toFixed(2);
  return unit ? `${text} ${unit}` : text;
}

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

/** Soft context match: missing record ids stay visible; conflicting ids are hidden. */
function matchesContextId(recordId?: string | null, contextId?: string): boolean {
  if (!contextId) return true;
  if (!recordId) return true;
  return recordId === contextId;
}

type ProductionMode = "full" | "runs" | "materials" | "material-governance";

export function ProductionWorkspace({ mode = "full" }: { mode?: ProductionMode }) {
  const { factoryId, modelId, colorId } = useWorkspaceContext();
  const contextFilterActive = Boolean(factoryId || modelId || colorId);
  const initialTab =
    mode === "materials" || mode === "material-governance" ? mode : "runs";
  const [tab, setTab] = useState<"runs" | "materials" | "material-governance">(initialTab);
  const showChrome = mode === "full";
  const lockedTab = mode !== "full";
  const [runs, setRuns] = useState<ProductionRun[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [factories, setFactories] = useState<Resource[]>([]);
  const [vehicleModels, setVehicleModels] = useState<Resource[]>([]);
  const [colors, setColors] = useState<Resource[]>([]);
  const [programVersions, setProgramVersions] = useState<ProgramVersion[]>([]);
  const [definitions, setDefinitions] = useState<Definition[]>([]);
  const [stagesByRunId, setStagesByRunId] = useState<Record<string, StageRun[]>>({});
  const [actualParameters, setActualParameters] = useState<ActualParameter[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedStageId, setSelectedStageId] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [modal, setModal] = useState<Modal>(null);
  const [form, setForm] = useState<FormState>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [measurementGroups, setMeasurementGroups] = useState<MeasurementGroup[]>([]);
  const [measurementPoints, setMeasurementPoints] = useState<MeasurementPoint[]>([]);
  const [groupPointRelations, setGroupPointRelations] = useState<GroupPointRelation[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [selectedPointId, setSelectedPointId] = useState("");
  const [pointDetail, setPointDetail] = useState<PointDetail | null>(null);
  const [pointDetailLoading, setPointDetailLoading] = useState(false);
  const [measurementLoading, setMeasurementLoading] = useState(false);

  const loadStagesForRuns = useCallback(async (runList: ProductionRun[]) => {
    if (!runList.length) {
      setStagesByRunId({});
      return;
    }
    const entries = await Promise.all(
      runList.map(async (run) => {
        try {
          const stages = await request<StageRun[]>(`/api/process/production-runs/${run.id}/stages`);
          return [run.id, stages] as const;
        } catch {
          return [run.id, [] as StageRun[]] as const;
        }
      }),
    );
    setStagesByRunId(Object.fromEntries(entries));
  }, []);

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
      setSelectedRunId((current) => (current && nextRuns.some((run) => run.id === current) ? current : ""));
      await loadStagesForRuns(nextRuns);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "生产实绩加载失败");
    } finally {
      setLoading(false);
    }
  }, [loadStagesForRuns]);

  const loadStages = useCallback(async (runId: string) => {
    if (!runId) return;
    try {
      const nextStages = await request<StageRun[]>(`/api/process/production-runs/${runId}/stages`);
      setStagesByRunId((prev) => ({ ...prev, [runId]: nextStages }));
      setSelectedStageId((current) => (current && nextStages.some((stage) => stage.id === current) ? current : nextStages[0]?.id ?? ""));
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

  const loadMeasurementCatalog = useCallback(async () => {
    setMeasurementLoading(true);
    try {
      const [groups, points, relations] = await Promise.all([
        request<MeasurementGroup[]>("/api/master-data/measurement-groups"),
        request<MeasurementPoint[]>("/api/master-data/measurement-points"),
        request<GroupPointRelation[]>("/api/master-data/measurement-group-points"),
      ]);
      setMeasurementGroups(groups);
      setMeasurementPoints(points);
      setGroupPointRelations(relations);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "测量编组加载失败");
    } finally {
      setMeasurementLoading(false);
    }
  }, []);

  const loadPointDetail = useCallback(async (pointId: string, runId: string) => {
    if (!pointId || !runId) {
      setPointDetail(null);
      return;
    }
    setPointDetailLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ production_run_id: runId });
      const detail = await request<PointDetail>(
        `/api/quality/body-map/points/${pointId}/detail?${params.toString()}`,
      );
      setPointDetail(detail);
    } catch (loadError) {
      setPointDetail(null);
      setError(loadError instanceof Error ? loadError.message : "点位质量详情加载失败");
    } finally {
      setPointDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, [reload]);
  useEffect(() => {
    if (!drawerOpen || !selectedRunId) return;
    const timer = window.setTimeout(() => void loadStages(selectedRunId), 0);
    return () => window.clearTimeout(timer);
  }, [drawerOpen, loadStages, selectedRunId]);
  useEffect(() => {
    if (!drawerOpen) return;
    const timer = window.setTimeout(() => void loadActuals(selectedStageId), 0);
    return () => window.clearTimeout(timer);
  }, [drawerOpen, loadActuals, selectedStageId]);
  useEffect(() => {
    if (!drawerOpen) return;
    const timer = window.setTimeout(() => void loadMeasurementCatalog(), 0);
    return () => window.clearTimeout(timer);
  }, [drawerOpen, loadMeasurementCatalog]);
  useEffect(() => {
    if (!drawerOpen || !selectedPointId || !selectedRunId) {
      setPointDetail(null);
      return;
    }
    const timer = window.setTimeout(() => void loadPointDetail(selectedPointId, selectedRunId), 0);
    return () => window.clearTimeout(timer);
  }, [drawerOpen, loadPointDetail, selectedPointId, selectedRunId]);

  const selectedRun = runs.find((run) => run.id === selectedRunId);
  const stageRuns = selectedRunId ? stagesByRunId[selectedRunId] ?? [] : [];
  const selectedStage = stageRuns.find((stage) => stage.id === selectedStageId);
  const runGroups = useMemo(() => {
    if (!selectedRun) return [];
    return measurementGroups
      .filter((group) => group.vehicle_model_id === selectedRun.vehicle_model_id)
      .sort((a, b) => a.code.localeCompare(b.code, "zh-CN"));
  }, [measurementGroups, selectedRun]);
  const runGroupPoints = useMemo(() => {
    if (!selectedGroupId) return [];
    const pointIds = groupPointRelations
      .filter((item) => item.measurement_group_id === selectedGroupId)
      .sort((a, b) => a.sequence_no - b.sequence_no)
      .map((item) => item.measurement_point_id);
    const byId = new Map(measurementPoints.map((point) => [point.id, point]));
    return pointIds
      .map((id) => byId.get(id))
      .filter((point): point is MeasurementPoint => Boolean(point));
  }, [groupPointRelations, measurementPoints, selectedGroupId]);
  const selectedGroup = runGroups.find((group) => group.id === selectedGroupId);
  const filteredRuns = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return runs.filter((run) => {
      if (
        normalized &&
        ![run.run_no, run.body_no, run.shift].some((value) => String(value ?? "").toLowerCase().includes(normalized))
      ) {
        return false;
      }
      if (!matchesContextId(run.factory_id, factoryId)) return false;
      if (!matchesContextId(run.vehicle_model_id, modelId)) return false;
      if (!matchesContextId(run.color_id, colorId)) return false;
      return true;
    });
  }, [colorId, factoryId, modelId, query, runs]);
  const filteredMaterials = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return materials.filter((material) => !normalized || [material.batch_no, material.material_code, material.material_name, material.supplier].some((value) => String(value ?? "").toLowerCase().includes(normalized)));
  }, [materials, query]);

  const closeModal = useCallback(() => {
    setModal(null);
  }, []);

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
      setNotice("生产实绩已保存");
      await reload();
      if (selectedRunId) {
        await loadStages(selectedRunId);
        await loadActuals(selectedStageId);
      }
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

  function openRunDrawer(runId: string, stageId?: string) {
    setSelectedRunId(runId);
    setSelectedStageId(stageId ?? "");
    setSelectedGroupId("");
    setSelectedPointId("");
    setPointDetail(null);
    setDrawerOpen(true);
  }

  function closeRunDrawer() {
    setDrawerOpen(false);
    setSelectedGroupId("");
    setSelectedPointId("");
    setPointDetail(null);
  }

  function selectMeasurementGroup(groupId: string) {
    setSelectedGroupId(groupId);
    setSelectedPointId("");
    setPointDetail(null);
  }

  function selectMeasurementPoint(pointId: string) {
    setSelectedPointId(pointId);
  }

  function stageForRun(runId: string, processStage: string): StageRun | undefined {
    return (stagesByRunId[runId] ?? []).find((stage) => stage.process_stage === processStage);
  }

  const content = (
    <>
      {error ? <button className="message-banner message-error" onClick={() => setError("")}>{error}<X /></button> : null}
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}
      {showChrome ? <div className="freshness">质量「批量上传」可自动创建生产事件；本页重点补录工序实绩与材料追溯。记录采用停用、替换或追加治理，不提供物理删除。</div> : null}
      {showChrome ? <section className="module-stat-strip"><article><span>生产事件</span><strong>{runs.length}</strong><small>按车身/批次追溯</small></article><article><span>已录工序</span><strong>{Object.values(stagesByRunId).reduce((sum, list) => sum + list.length, 0)}</strong><small>五个喷涂执行阶段</small></article><article><span>实际参数</span><strong>{actualParameters.length}</strong><small>PLC / 机器人采样</small></article><article><span>材料批次</span><strong>{materials.length}</strong><small>粘度、固含与 COA</small></article></section> : null}
      <section className={showChrome ? "panel production-workspace" : "production-workspace embedded-workspace"}>
        {!lockedTab ? (
          <div className="master-tabs">
            <button className={tab === "runs" ? "active" : ""} onClick={() => setTab("runs")}>生产事件与工序</button>
            <button className={tab === "materials" ? "active" : ""} onClick={() => setTab("materials")}>材料批次</button>
            <button className={tab === "material-governance" ? "active" : ""} onClick={() => setTab("material-governance")}>材料特性治理</button>
            {tab !== "material-governance" ? (
              <>
                <label className="master-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索生产事件或材料" /></label>
                {contextFilterActive && tab === "runs" ? <span className="context-filter-hint">已按顶部作业范围筛选</span> : null}
                <button className="button button-primary" onClick={() => openModal(tab === "runs" ? "run" : "material")}><Plus /> 新建{tab === "runs" ? "生产事件" : "材料批次"}</button>
              </>
            ) : null}
          </div>
        ) : tab !== "material-governance" ? (
          <div className="master-tabs">
            <label className="master-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={tab === "runs" ? "搜索生产事件" : "搜索材料批次"} /></label>
            {contextFilterActive && tab === "runs" ? <span className="context-filter-hint">已按顶部作业范围筛选</span> : null}
            <BulkDataActions
              resourceKey={tab === "materials" ? "process.material-batches" : "process.production-runs"}
              resourceLabel={tab === "materials" ? "材料批次" : "生产事件"}
              disabled={loading || submitting}
              defaultValues={
                tab === "runs"
                  ? {
                      factory_id: factoryId || undefined,
                      vehicle_model_id: modelId || undefined,
                      color_id: colorId || undefined,
                    }
                  : undefined
              }
              onImported={reload}
              onResult={bulkResult}
            />
            <button className="button button-primary" onClick={() => openModal(tab === "runs" ? "run" : "material")}><Plus /> 新建{tab === "runs" ? "生产事件" : "材料批次"}</button>
            <button className="button button-secondary" onClick={() => void reload()}><RefreshCw className={loading ? "spin" : ""} /> 刷新</button>
          </div>
        ) : null}
        {tab === "runs" ? (
          <>
            <div className="master-table-wrap production-wide-wrap">
              <table className="master-table production-wide-table">
                <thead>
                  <tr>
                    <th>生产事件</th>
                    <th>车身号</th>
                    <th>工厂</th>
                    <th>车型</th>
                    <th>颜色</th>
                    <th>班次</th>
                    <th>开始时间</th>
                    {stages.map(([code, label]) => (
                      <th key={code}>{label}</th>
                    ))}
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRuns.map((run) => (
                    <tr key={run.id} className={run.id === selectedRunId && drawerOpen ? "is-selected" : undefined}>
                      <td>
                        <button type="button" className="link-button" onClick={() => openRunDrawer(run.id)}>
                          <strong>{run.run_no}</strong>
                        </button>
                      </td>
                      <td>{run.body_no || "—"}</td>
                      <td>{relationName(factories, run.factory_id)}</td>
                      <td>{relationName(vehicleModels, run.vehicle_model_id)}</td>
                      <td>{relationName(colors, run.color_id)}</td>
                      <td>{run.shift || "—"}</td>
                      <td>{new Date(run.started_at).toLocaleString("zh-CN")}</td>
                      {stages.map(([code]) => {
                        const stage = stageForRun(run.id, code);
                        return (
                          <td key={code}>
                            {stage ? (
                              <button
                                type="button"
                                className={`production-stage-chip status-${stage.status.toLowerCase()}`}
                                onClick={() => openRunDrawer(run.id, stage.id)}
                              >
                                {statusLabel(stage.status)}
                              </button>
                            ) : (
                              <button
                                type="button"
                                className="production-stage-chip is-empty"
                                onClick={() => {
                                  openRunDrawer(run.id);
                                  setForm({
                                    process_stage: code,
                                    program_version_id: programVersions.find((item) => item.process_stage === code)?.id ?? "",
                                    material_batch_id: "",
                                    status: "COMPLETED",
                                    actual_parameters: "{}",
                                  });
                                  setModal({ kind: "stage" });
                                }}
                              >
                                未录
                              </button>
                            )}
                          </td>
                        );
                      })}
                      <td>
                        <div className="row-actions">
                          <button type="button" className="button button-secondary" onClick={() => openRunDrawer(run.id)}>
                            详情
                          </button>
                          <button type="button" className="icon-button" onClick={() => openModal("run", run)} aria-label="编辑生产事件">
                            <Pencil aria-hidden="true" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!filteredRuns.length ? (
                <div className="master-empty">
                  <Activity /> 暂无生产事件。日常请先到质量管理「批量上传」上传质量数据（可自动建档）；若只需补工序实绩，也可在此手工新建生产事件。
                </div>
              ) : null}
            </div>

            {drawerOpen && selectedRun && !modal ? (
              <div className="production-drawer-backdrop" role="presentation" onMouseDown={closeRunDrawer}>
                <aside
                  className="production-drawer"
                  role="dialog"
                  aria-modal="true"
                  aria-label={`生产事件 ${selectedRun.run_no}`}
                  onMouseDown={(event) => event.stopPropagation()}
                >
                  <div className="production-drawer-head">
                    <div>
                      <span className="eyebrow">生产事件详情</span>
                      <h3>{selectedRun.run_no}</h3>
                      <p>
                        {relationName(factories, selectedRun.factory_id)} ·{" "}
                        {relationName(vehicleModels, selectedRun.vehicle_model_id)} ·{" "}
                        {relationName(colors, selectedRun.color_id)}
                      </p>
                    </div>
                    <div className="row-actions">
                      <button type="button" className="button button-secondary" onClick={() => openModal("run", selectedRun)}>
                        <Pencil /> 编辑事件
                      </button>
                      <button type="button" className="icon-button" onClick={closeRunDrawer} aria-label="关闭">
                        <X aria-hidden="true" />
                      </button>
                    </div>
                  </div>

                  <div className="production-drawer-section">
                    <div className="production-stage-heading">
                      <div>
                        <span className="eyebrow">质量追溯</span>
                        <h4>测量编组与点位</h4>
                      </div>
                      <Link className="button button-secondary" href="/quality?tab=body-map">
                        车身点位图
                      </Link>
                    </div>
                    {measurementLoading ? (
                      <div className="master-empty"><LoaderCircle className="spin" /> 正在加载测量编组…</div>
                    ) : !runGroups.length ? (
                      <div className="master-empty">当前车型还没有测量编组，请先在车身点位图维护编组与点位。</div>
                    ) : (
                      <>
                        <div className="production-measure-chip-row" role="list" aria-label="测量编组">
                          {runGroups.map((group) => (
                            <button
                              key={group.id}
                              type="button"
                              role="listitem"
                              className={`production-measure-chip ${group.id === selectedGroupId ? "is-active" : ""}`}
                              onClick={() => selectMeasurementGroup(group.id)}
                            >
                              <strong>{group.code}</strong>
                              <span>
                                {group.name}
                                {group.quality_type
                                  ? ` · ${QUALITY_TYPE_LABELS[group.quality_type] ?? group.quality_type}`
                                  : ""}
                              </span>
                            </button>
                          ))}
                        </div>
                        {selectedGroup ? (
                          <div className="production-measure-points">
                            <div className="production-measure-points-label">
                              编组点位 · {selectedGroup.code} / {selectedGroup.name}
                            </div>
                            {!runGroupPoints.length ? (
                              <div className="master-empty">该编组尚未绑定测量点位。</div>
                            ) : (
                              <div className="production-measure-chip-row" role="list" aria-label="测量点位">
                                {runGroupPoints.map((point) => (
                                  <button
                                    key={point.id}
                                    type="button"
                                    role="listitem"
                                    className={`production-measure-chip ${point.id === selectedPointId ? "is-active" : ""}`}
                                    onClick={() => selectMeasurementPoint(point.id)}
                                  >
                                    <strong>{point.code}</strong>
                                    <span>{point.name}</span>
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        ) : (
                          <p className="production-measure-hint">请选择测量编组，再点开点位查看本车质量与喷涂参数。</p>
                        )}
                        {selectedPointId ? (
                          <div className="production-point-detail">
                            {pointDetailLoading ? (
                              <div className="master-empty"><LoaderCircle className="spin" /> 正在加载点位详情…</div>
                            ) : pointDetail ? (
                              <>
                                <div className="production-point-detail-head">
                                  <div>
                                    <span className="eyebrow">点位质量与喷涂</span>
                                    <h4>
                                      {pointDetail.code} · {pointDetail.name}
                                    </h4>
                                    <small>
                                      {[pointDetail.part_code, pointDetail.part_name, pointDetail.region]
                                        .filter(Boolean)
                                        .join(" · ") || "未标注零件/区域"}
                                    </small>
                                  </div>
                                </div>
                                <BodyMapQualitySummaryGrid
                                  summaries={pointDetail.quality_summaries}
                                  emptyText="本生产事件暂无该点位质量数据。"
                                />
                                <div className="body-map-brush-block">
                                  <div className="program-subheading compact">
                                    <div>
                                      <span className="eyebrow">喷涂关联</span>
                                      <h4>刷子号与参数</h4>
                                    </div>
                                  </div>
                                  {!pointDetail.brush_contributions.length ? (
                                    <div className="program-empty">暂无点位喷涂参数贡献。</div>
                                  ) : (
                                    pointDetail.brush_contributions.map((brush) => (
                                      <div
                                        className="body-map-brush-card"
                                        key={`${brush.brush_id}-${brush.process_stage}-${brush.target_family ?? brush.brush_no}`}
                                      >
                                        <div className="body-map-brush-head">
                                          <div className="body-map-brush-title">
                                            <strong>
                                              {COATING_LABELS[brush.coating_system] ?? brush.coating_system} · {brush.brush_no}
                                            </strong>
                                          </div>
                                          <small>
                                            {stageLabel(brush.process_stage)} · 表 {brush.brush_table_no} · 重叠{" "}
                                            {(brush.overlap_ratio * 100).toFixed(0)}% · 权重{" "}
                                            {(brush.contribution_weight * 100).toFixed(0)}%
                                            {brush.is_approved ? " · 已审批" : " · 待审批"}
                                          </small>
                                        </div>
                                        {brush.parameters.length ? (
                                          <div className="body-map-param-table">
                                            {brush.parameters.map((parameter) => (
                                              <div className="body-map-param-row" key={parameter.parameter_code}>
                                                <span>
                                                  <strong>{parameter.parameter_name}</strong>
                                                  <small>{parameter.unit || "无单位"}</small>
                                                </span>
                                                <span className="mono">
                                                  <em>设定</em> {formatMetricValue(parameter.configured_value, parameter.unit)}
                                                </span>
                                                <span className="mono">
                                                  <em>实绩</em> {formatMetricValue(parameter.actual_value, parameter.unit)}
                                                </span>
                                              </div>
                                            ))}
                                          </div>
                                        ) : (
                                          <div className="program-empty">该刷子暂无参数明细。</div>
                                        )}
                                      </div>
                                    ))
                                  )}
                                </div>
                              </>
                            ) : (
                              <div className="master-empty">未能加载点位详情。</div>
                            )}
                          </div>
                        ) : null}
                      </>
                    )}
                  </div>

                  <div className="production-drawer-section">
                    <div className="production-stage-heading">
                      <div>
                        <span className="eyebrow">五站工序</span>
                        <h4>工序实绩</h4>
                      </div>
                      <div className="row-actions">
                        <BulkDataActions
                          resourceKey="process.production-stage-runs"
                          resourceLabel="工序实绩"
                          disabled={loading || submitting}
                          defaultValues={{ production_run_id: selectedRunId || undefined }}
                          onImported={async () => {
                            await reload();
                            await loadStages(selectedRunId);
                          }}
                          onResult={bulkResult}
                        />
                        <button
                          type="button"
                          className="button button-primary"
                          onClick={() => openModal("stage")}
                          disabled={stageRuns.length >= 5}
                        >
                          <Plus /> 添加工序
                        </button>
                      </div>
                    </div>
                    <div className="master-table-wrap">
                      <table className="master-table production-stage-table">
                        <thead>
                          <tr>
                            <th>工序</th>
                            <th>状态</th>
                            <th>程序版本</th>
                            <th>材料批次</th>
                            <th>操作</th>
                          </tr>
                        </thead>
                        <tbody>
                          {stageRuns.map((stage) => {
                            const version = programVersions.find((item) => item.id === stage.program_version_id);
                            const material = materials.find((item) => item.id === stage.material_batch_id);
                            return (
                              <tr
                                key={stage.id}
                                className={stage.id === selectedStageId ? "is-selected" : undefined}
                                onClick={() => setSelectedStageId(stage.id)}
                              >
                                <td>{stageLabel(stage.process_stage)}</td>
                                <td>{statusLabel(stage.status)}</td>
                                <td>{version ? `${version.program_name} / ${version.version}` : "—"}</td>
                                <td>{material ? `${material.batch_no} / ${material.material_name}` : "—"}</td>
                                <td>
                                  <div className="row-actions">
                                    <button
                                      type="button"
                                      className="button button-secondary"
                                      onClick={(event) => {
                                        event.stopPropagation();
                                        setSelectedStageId(stage.id);
                                        openModal("stage", stage);
                                      }}
                                    >
                                      编辑
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                      {!stageRuns.length ? (
                        <div className="master-empty">当前生产事件还没有工序实绩，请通过「添加工序」或宽表导入补录五个执行阶段。</div>
                      ) : null}
                    </div>
                  </div>

                  {selectedStage ? (
                    <div className="production-drawer-section">
                      <div className="production-stage-heading">
                        <div>
                          <span className="eyebrow">实际参数</span>
                          <h4>{stageLabel(selectedStage.process_stage)}</h4>
                        </div>
                        <div className="row-actions">
                          <BulkDataActions
                            resourceKey="process.actual-parameters"
                            resourceLabel="实际参数"
                            disabled={loading || submitting}
                            defaultValues={{ production_stage_run_id: selectedStageId || undefined }}
                            onImported={async () => {
                              await loadActuals(selectedStageId);
                            }}
                            onResult={bulkResult}
                          />
                          <button type="button" className="button button-primary" onClick={() => openModal("actual")}>
                            <Plus /> 添加实绩参数
                          </button>
                        </div>
                      </div>
                      <div className="master-table-wrap">
                        <table className="master-table">
                          <thead>
                            <tr>
                              <th>参数</th>
                              <th>实际值</th>
                              <th>来源</th>
                              <th>采样时间</th>
                              <th>操作</th>
                            </tr>
                          </thead>
                          <tbody>
                            {actualParameters.map((parameter) => (
                              <tr key={parameter.id}>
                                <td>
                                  <strong>
                                    {definitions.find((item) => item.code === parameter.parameter_code)?.name
                                      ?? parameter.parameter_code}
                                  </strong>
                                  <small className="mono">{parameter.parameter_code}</small>
                                </td>
                                <td>
                                  {parameter.actual_value} {parameter.unit}
                                </td>
                                <td>{parameter.source_system || "—"}</td>
                                <td>{new Date(parameter.sampled_at).toLocaleString("zh-CN")}</td>
                                <td>
                                  <button
                                    type="button"
                                    className="icon-button"
                                    onClick={() => openModal("actual", parameter)}
                                    aria-label="编辑实际参数"
                                  >
                                    <Pencil aria-hidden="true" />
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {!actualParameters.length ? (
                          <div className="master-empty">当前工序还没有实绩参数，请继续补录 PLC / 机器人采样值。</div>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                </aside>
              </div>
            ) : null}
          </>
        ) : tab === "materials" ? <div className="master-table-wrap"><table className="master-table production-material-table"><thead><tr><th>批次号</th><th>材料</th><th>类型</th><th>供应商</th><th>粘度</th><th>固含量</th><th>操作</th></tr></thead><tbody>{filteredMaterials.map((material) => <tr key={material.id}><td>{material.batch_no}</td><td>{material.material_code} / {material.material_name}</td><td>{{ MIDCOAT: "中涂", BASECOAT: "色漆", CLEARCOAT: "清漆" }[material.material_type] ?? material.material_type}</td><td>{material.supplier ?? "—"}</td><td>{material.viscosity ?? "—"}</td><td>{material.solid_ratio ?? "—"}</td><td><div className="row-actions"><button className="icon-button" onClick={() => openModal("material", material)} aria-label="编辑材料批次"><Pencil aria-hidden="true" /></button></div></td></tr>)}</tbody></table>{!filteredMaterials.length ? <div className="master-empty"><Boxes /> 暂无材料批次，请先维护批次，再绑定到对应工艺阶段。</div> : null}</div> : <MaterialGovernancePanel />}
      </section>
      {modal ? <ProductionModal modal={modal} form={form} setForm={setForm} submit={submit} close={closeModal} submitting={submitting} factories={factories} vehicleModels={vehicleModels} colors={colors} materials={materials} versions={programVersions} definitions={definitions} selectedRun={selectedRun} /> : null}
    </>
  );

  if (!showChrome) return <div className="embedded-stack">{content}</div>;

  return (
    <div className="page-stack">
      <header className="page-header">
        <div className="page-actions">
          <Link className="button button-secondary" href="/quality?tab=upload">
            <Upload /> 批量上传质量
          </Link>
          <BulkDataActions
            resourceKey={tab === "materials" ? "process.material-batches" : "process.production-runs"}
            resourceLabel={tab === "materials" ? "材料批次" : "生产事件"}
            disabled={loading || submitting}
            defaultValues={
              tab === "runs"
                ? {
                    factory_id: factoryId || undefined,
                    vehicle_model_id: modelId || undefined,
                    color_id: colorId || undefined,
                  }
                : undefined
            }
            onImported={reload}
            onResult={bulkResult}
          />
          <button className="button button-secondary" onClick={() => void reload()}>
            <RefreshCw className={loading ? "spin" : ""} /> 刷新实时数据
          </button>
        </div>
      </header>
      {content}
    </div>
  );
}

function ProductionModal({ modal, form, setForm, submit, close, submitting, factories, vehicleModels, colors, materials, versions, definitions, selectedRun }: { modal: NonNullable<Modal>; form: FormState; setForm: (form: FormState) => void; submit: (event: FormEvent<HTMLFormElement>) => void; close: () => void; submitting: boolean; factories: Resource[]; vehicleModels: Resource[]; colors: Resource[]; materials: Material[]; versions: ProgramVersion[]; definitions: Definition[]; selectedRun?: ProductionRun }) {
  const input = (key: string, label: string, type = "text", required = false) => <label className="form-field"><span>{label}{required ? <b>*</b> : null}</span><input type={type} step={type === "number" ? "any" : undefined} required={required} value={form[key] ?? ""} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>;
  const select = (key: string, label: string, options: [string, string][], required = true) => <label className="form-field"><span>{label}{required ? <b>*</b> : null}</span><select required={required} value={form[key] ?? ""} onChange={(event) => { const value = event.target.value; const definition = key === "parameter_code" ? definitions.find((item) => item.code === value) : undefined; setForm({ ...form, [key]: value, ...(definition ? { unit: definition.unit } : {}) }); }}>{options.map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></label>;
  const stageMaterialTypeMap: Record<string, string> = {
    MIDCOAT_EXT: "MIDCOAT",
    BASECOAT_1: "BASECOAT",
    BASECOAT_2: "BASECOAT",
    CLEARCOAT_1: "CLEARCOAT",
    CLEARCOAT_2: "CLEARCOAT",
  };
  const filteredVersions = modal.kind === "stage"
    ? versions.filter((item) => item.process_stage === form.process_stage)
    : versions;
  const filteredMaterials = modal.kind === "stage"
    ? materials.filter((item) => item.material_type === stageMaterialTypeMap[form.process_stage])
    : materials;
  const currentStageLabel = stages.find(([value]) => value === form.process_stage)?.[1] ?? form.process_stage ?? "当前工序";
  const expectedMaterialLabel = { MIDCOAT: "中涂", BASECOAT: "色漆", CLEARCOAT: "清漆" }[stageMaterialTypeMap[form.process_stage] ?? ""] ?? "未限定";
  useEffect(() => {
    if (modal.kind !== "stage") return;
    const nextProgramVersionId = filteredVersions.some((item) => item.id === form.program_version_id)
      ? form.program_version_id
      : filteredVersions[0]?.id ?? "";
    const nextMaterialBatchId = filteredMaterials.some((item) => item.id === form.material_batch_id)
      ? form.material_batch_id
      : "";
    if (nextProgramVersionId !== form.program_version_id || nextMaterialBatchId !== form.material_batch_id) {
      setForm({ ...form, program_version_id: nextProgramVersionId, material_batch_id: nextMaterialBatchId });
    }
  }, [filteredMaterials, filteredVersions, form, modal.kind, setForm]);
  return <ModalShell className="quality-modal" eyebrow="生产数据" title={`${modal.record ? "编辑" : "新建"}${{ run: "生产记录", material: "材料批次", stage: "工序实绩", actual: "实际参数" }[modal.kind]}`} description="按业务步骤填写；系统会自动检查工序、程序版本和材料批次是否匹配。" onClose={close} busy={submitting}><form onSubmit={submit}><div className="form-grid">{modal.kind === "run" ? <><FormSection title="生产信息" description="确认车号以及所属工厂、车型和颜色。"><div className="modal-section-grid">{input("run_no", "生产记录编号", "text", true)}{input("body_no", "车号")}{select("factory_id", "工厂", factories.map((item) => [item.id, `${item.code} / ${item.name}`]))}{select("vehicle_model_id", "车型", vehicleModels.map((item) => [item.id, `${item.code} / ${item.name}`]))}{select("color_id", "颜色", colors.map((item) => [item.id, `${item.code} / ${item.name}`]))}{input("shift", "班次")}</div></FormSection><FormSection title="生产时间与补充信息" description="填写生产时间；其他追溯信息可按行补充。"><div className="modal-section-grid">{input("started_at", "开始时间", "datetime-local", true)}{input("completed_at", "完成时间", "datetime-local")}<label className="form-field form-field-wide"><span>其他追溯信息</span><JsonObjectEditor value={String(form.context_values ?? "")} onChange={(value) => setForm({ ...form, context_values: value })} keyLabel="信息名称" valueLabel="信息内容" addLabel="新增一项" /></label></div></FormSection></> : null}{modal.kind === "material" ? <><FormSection title="批次基础信息" description="维护当前材料批次的身份、类型和供应商信息。"><div className="modal-section-grid">{input("batch_no", "批次号", "text", true)}{input("material_code", "材料代码", "text", true)}{input("material_name", "材料名称", "text", true)}{select("material_type", "材料类型", [["MIDCOAT", "中涂"], ["BASECOAT", "色漆"], ["CLEARCOAT", "清漆"]])}{input("supplier", "供应商")}</div></FormSection><FormSection title="批次检测结果" description="按表格维护粘度、固含量和供应商批次检验结果。"><div className="modal-section-grid">{input("viscosity", "粘度", "number")}{input("solid_ratio", "固含量", "number")}<label className="form-field form-field-wide"><span>供应商批次检验结果</span><JsonObjectEditor value={String(form.coa_values ?? "")} onChange={(value) => setForm({ ...form, coa_values: value })} keyLabel="检测项目" valueLabel="检测结果" addLabel="新增检测项目" /></label></div></FormSection></> : null}{modal.kind === "stage" ? <><FormSection title="工序与前置条件" description="先确认当前工序、可用程序版本和材料批次。"><div className="modal-section-grid"><label className="form-field form-field-wide"><span>系统已自动筛选</span><div className="master-empty">当前工序：{currentStageLabel}，只展示匹配该工序的程序版本与{expectedMaterialLabel}材料批次。{selectedRun ? `当前生产记录：${selectedRun.run_no}` : "请先选定生产记录。"} </div></label>{select("process_stage", "工序", stages as [string, string][])}{select("program_version_id", "程序版本", filteredVersions.map((item) => [item.id, `${item.program_name} / ${item.version} / ${statusLabel(item.status)}`]))}{filteredVersions.length === 0 ? <label className="form-field form-field-wide"><span>暂时无法填写</span><div className="master-empty">{currentStageLabel} 暂无可用程序版本，请先到“程序与刷子参数”补齐该工序的程序和版本。</div></label> : null}<label className="form-field"><span>材料批次</span><select value={form.material_batch_id ?? ""} onChange={(event) => setForm({ ...form, material_batch_id: event.target.value })}><option value="">暂不关联</option>{filteredMaterials.map((item) => <option value={item.id} key={item.id}>{item.batch_no} / {item.material_name}</option>)}</select></label>{filteredMaterials.length === 0 ? <label className="form-field form-field-wide"><span>暂未找到材料批次</span><div className="master-empty">当前工序需要{expectedMaterialLabel}材料，请先补录对应类型的材料批次。</div></label> : null}</div></FormSection><FormSection title="执行结果" description="填写工序状态；汇总参数可按行补充。"><div className="modal-section-grid">{select("status", "状态", [["COMPLETED","已完成"],["RUNNING","进行中"],["PLANNED","已计划"],["CANCELLED","已取消"]], true)}<label className="form-field form-field-wide"><span>工序汇总参数</span><JsonObjectEditor value={String(form.actual_parameters ?? "")} onChange={(value) => setForm({ ...form, actual_parameters: value })} keyLabel="参数名称" valueLabel="实际值" addLabel="新增参数" /></label></div></FormSection></> : null}{modal.kind === "actual" ? <FormSection title="实际参数采样" description="逐条维护已采集的参数值、单位和采样时间。"><div className="modal-section-grid">{select("parameter_code", "参数", definitions.map((item) => [item.code, `${item.name} / ${item.code}`]))}{input("actual_value", "实际值", "number", true)}{input("unit", "单位", "text", true)}{input("sampled_at", "采样时间", "datetime-local", true)}{input("source_system", "数据来源")}</div></FormSection> : null}</div><div className="modal-actions"><button type="button" className="button button-secondary" onClick={close} disabled={submitting}>取消</button><button className="button button-primary" disabled={submitting}>{submitting ? <LoaderCircle className="spin" aria-hidden="true" /> : null}{submitting ? "正在保存" : "保存"}</button></div></form></ModalShell>;
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
