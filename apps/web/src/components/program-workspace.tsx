"use client";

import {
  LoaderCircle,
  Pencil,
  Plus,
  RefreshCw,
  Settings2,
  Upload,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { BrushConfigForm } from "@/components/brush-config-form";
import { BulkDataActions } from "@/components/bulk-data-actions";
import { DurrTrajectoryPanel } from "@/components/durr-trajectory-panel";
import { ModalShell } from "@/components/modal-shell";
import { VersionDiffPanel } from "@/components/version-diff-panel";
import { useAuth } from "@/lib/auth-context";
import { useWorkspaceContext } from "@/lib/workspace-context";

type Resource = { id: string; code: string; name: string };
type Factory = Resource;
type VehicleModel = Resource;
type Color = Resource;
type Part = Resource;
type Point = Resource & {
  vehicle_model_id: string;
  part_id: string;
  point_type?: string;
  quality_types?: string[];
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
  factory_id: string;
  process_stage: string;
  station_code: string;
  station_name: string;
  robot_model?: string | null;
  remark?: string | null;
};
type Version = {
  id: string;
  spray_program_id: string;
  version: string;
  status: string;
  source_type: string;
  is_master_sample: boolean;
  approved_by?: string | null;
  approved_at?: string | null;
  effective_from?: string | null;
  vehicle_model_ids?: string[];
  color_ids?: string[];
};
type Brush = {
  id: string;
  program_version_id: string;
  brush_no: string;
  brush_table_no: string;
  spray_position?: string | null;
  part_id?: string | null;
  remark?: string | null;
};
type BrushParameter = {
  id: string;
  brush_id: string;
  parameter_definition_id?: string | null;
  parameter_code: string;
  parameter_name: string;
  configured_value: number;
  unit: string;
  soft_min?: number | null;
  soft_max?: number | null;
  hard_min?: number | null;
  hard_max?: number | null;
  is_recommendable: boolean;
};
type Contribution = {
  id: string;
  brush_id: string;
  measurement_point_id: string;
  overlap_ratio: number;
  contribution_weight: number;
  source: string;
  version: string;
  is_approved: boolean;
};
type ModalKind = "program" | "version";
type ModalState = { kind: ModalKind; record?: Program | Version };
type FormValue = string | boolean | string[];
type FormState = Record<string, FormValue>;
type BrushConfigState = { mode: "create" | "edit"; brush?: Brush } | null;

const stageOptions = [
  ["MIDCOAT_EXT", "中涂外喷"],
  ["BASECOAT_1", "色漆一站"],
  ["BASECOAT_2", "色漆二站"],
  ["CLEARCOAT_1", "清漆一站"],
  ["CLEARCOAT_2", "清漆二站"],
];

const statusLabels: Record<string, string> = {
  DRAFT: "草稿",
  PENDING: "待审批",
  APPROVED: "已批准",
  ACTIVE: "已生效",
  RETIRED: "已退役",
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new Error(payload.error ?? `请求失败（${response.status}）`);
  return payload;
}

/** Soft context match: missing record ids stay visible; conflicting ids are hidden. */
function matchesContextId(recordId?: string | null, contextId?: string): boolean {
  if (!contextId) return true;
  if (!recordId) return true;
  return recordId === contextId;
}

function matchesContextIdList(recordIds?: string[] | null, contextId?: string): boolean {
  if (!contextId) return true;
  if (!recordIds?.length) return true;
  return recordIds.includes(contextId);
}

const STAGE_PARAM_PREFIX: Record<string, string> = {
  MIDCOAT_EXT: "midcoat",
  BASECOAT_1: "basecoat_1",
  BASECOAT_2: "basecoat_2",
  CLEARCOAT_1: "clearcoat_1",
  CLEARCOAT_2: "clearcoat_2",
};

const PARAM_SUFFIXES: Array<[string, string]> = [
  ["spray_flow", "喷涂流量"],
  ["outer_air", "外成型空气流量"],
  ["inner_air", "内成型空气流量"],
  ["bell_speed", "旋杯转速"],
  ["voltage", "静电高压"],
];

function stageParamCodes(processStage: string): Array<[string, string]> {
  const prefix = STAGE_PARAM_PREFIX[processStage];
  if (!prefix) return [];
  return PARAM_SUFFIXES.map(([suffix, label]) => [`${prefix}_${suffix}`, label] as [string, string]);
}

export function ProgramWorkspace({
  mode = "full",
}: {
  mode?: "full" | "recipes" | "durr";
}) {
  const { actor } = useAuth();
  const { factoryId, modelId, colorId, stage } = useWorkspaceContext();
  const contextFilterActive = Boolean(factoryId || modelId || colorId || stage);
  const actorName = actor.isAuthenticated ? actor.displayName : "";
  const [workspaceTab, setWorkspaceTab] = useState<"programs" | "durr" | "diff">(
    mode === "durr" ? "durr" : "programs",
  );
  const showChrome = mode === "full";
  const hideOuterTabs = mode !== "full";
  const [programs, setPrograms] = useState<Program[]>([]);
  const [versions, setVersions] = useState<Version[]>([]);
  const [brushes, setBrushes] = useState<Brush[]>([]);
  const [parameters, setParameters] = useState<BrushParameter[]>([]);
  const [contributions, setContributions] = useState<Contribution[]>([]);
  const [factories, setFactories] = useState<Factory[]>([]);
  const [vehicleModels, setVehicleModels] = useState<VehicleModel[]>([]);
  const [colors, setColors] = useState<Color[]>([]);
  const [parts, setParts] = useState<Part[]>([]);
  const [points, setPoints] = useState<Point[]>([]);
  const [definitions, setDefinitions] = useState<ParameterDefinition[]>([]);
  const [selectedProgramId, setSelectedProgramId] = useState("");
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [selectedBrushId, setSelectedBrushId] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [modal, setModal] = useState<ModalState | null>(null);
  const [form, setForm] = useState<FormState>({});
  const [brushConfig, setBrushConfig] = useState<BrushConfigState>(null);
  const [selectedBrushTableNo, setSelectedBrushTableNo] = useState("");
  const [allBrushData, setAllBrushData] = useState<
    Record<string, { parameters: BrushParameter[]; contributions: Contribution[] }>
  >({});
  const [editingRowKey, setEditingRowKey] = useState<string | null>(null);
  const [rowDraft, setRowDraft] = useState<Record<string, string>>({});
  const [wideUploading, setWideUploading] = useState(false);
  const [wideFormat, setWideFormat] = useState<"xlsx" | "csv">("xlsx");
  const wideInputRef = useRef<HTMLInputElement>(null);

  const closeModal = useCallback(() => {
    if (submitting) return;
    setModal(null);
  }, [submitting]);
  const closeBrushConfig = useCallback(() => {
    setBrushConfig(null);
  }, []);
  const selectedProgram = programs.find((item) => item.id === selectedProgramId);
  const selectedVersion = versions.find((item) => item.id === selectedVersionId);
  const filteredPrograms = useMemo(
    () =>
      programs.filter(
        (program) =>
          matchesContextId(program.factory_id, factoryId) && matchesContextId(program.process_stage, stage),
      ),
    [factoryId, programs, stage],
  );
  const filteredVersions = useMemo(
    () =>
      versions.filter(
        (version) =>
          matchesContextIdList(version.vehicle_model_ids, modelId) &&
          matchesContextIdList(version.color_ids, colorId),
      ),
    [colorId, modelId, versions],
  );
  const loadBrush = useCallback(async (brushId: string) => {
    if (!brushId) {
      setParameters([]);
      setContributions([]);
      setSelectedBrushId("");
      return;
    }
    const [nextParameters, nextContributions] = await Promise.all([
      request<BrushParameter[]>(`/api/process/brushes/${brushId}/parameters`),
      request<Contribution[]>(`/api/process/brushes/${brushId}/contributions`),
    ]);
    setSelectedBrushId(brushId);
    setParameters(nextParameters);
    setContributions(nextContributions);
  }, []);

  const loadBrushTable = useCallback(async (versionId: string, brushTableNo: string) => {
    if (!versionId || !brushTableNo) {
      setAllBrushData({});
      return;
    }
    const versionBrushes = await request<Brush[]>(`/api/process/program-versions/${versionId}/brushes`);
    const tableBrushes = versionBrushes.filter((b) => b.brush_table_no === brushTableNo);
    const entries = await Promise.all(
      tableBrushes.map(async (brush) => {
        const [params, contribs] = await Promise.all([
          request<BrushParameter[]>(`/api/process/brushes/${brush.id}/parameters`),
          request<Contribution[]>(`/api/process/brushes/${brush.id}/contributions`),
        ]);
        return [brush.id, { parameters: params, contributions: contribs }] as const;
      }),
    );
    setAllBrushData(Object.fromEntries(entries));
  }, []);

  const loadVersion = useCallback(async (versionId: string, preferredBrushId = "") => {
    if (!versionId) {
      setBrushes([]);
      await loadBrush("");
      setSelectedVersionId("");
      return;
    }
    const nextBrushes = await request<Brush[]>(`/api/process/program-versions/${versionId}/brushes`);
    const nextBrushId =
      nextBrushes.find((item) => item.id === preferredBrushId)?.id ?? "";
    setSelectedVersionId(versionId);
    setBrushes(nextBrushes);
    await loadBrush(nextBrushId);
  }, [loadBrush]);

  const loadProgram = useCallback(async (programId: string, preferredVersionId = "", preferredBrushId = "") => {
    if (!programId) {
      setSelectedProgramId("");
      setVersions([]);
      setBrushes([]);
      await loadBrush("");
      return;
    }
    const rawVersions = await request<Version[]>(`/api/process/spray-programs/${programId}/versions`);
    const nextVersions = await Promise.all(
      rawVersions.map(async (version) => ({
        ...version,
        ...(await request<{ vehicle_model_ids: string[]; color_ids: string[] }>(
          `/api/process/program-versions/${version.id}/applicability`,
        )),
      })),
    );
    const nextVersionId =
      nextVersions.find((item) => item.id === preferredVersionId)?.id ?? "";
    setSelectedProgramId(programId);
    setVersions(nextVersions);
    await loadVersion(nextVersionId, preferredBrushId);
  }, [loadBrush, loadVersion]);

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextPrograms, nextFactories, nextModels, nextColors, nextParts, nextPoints, nextDefinitions] =
        await Promise.all([
          request<Program[]>("/api/process/spray-programs"),
          request<Factory[]>("/api/master-data/factories"),
          request<VehicleModel[]>("/api/master-data/vehicle-models"),
          request<Color[]>("/api/master-data/colors"),
          request<Part[]>("/api/master-data/parts"),
          request<Point[]>("/api/master-data/measurement-points"),
          request<ParameterDefinition[]>("/api/process/parameter-definitions"),
        ]);
      setPrograms(nextPrograms);
      setFactories(nextFactories);
      setVehicleModels(nextModels);
      setColors(nextColors);
      setParts(nextParts);
      setPoints(nextPoints);
      setDefinitions(nextDefinitions);
      const programId =
        nextPrograms.find((item) => item.id === selectedProgramId)?.id ?? "";
      await loadProgram(programId, selectedVersionId, selectedBrushId);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "程序配置加载失败");
    } finally {
      setLoading(false);
    }
  }, [loadProgram, selectedBrushId, selectedProgramId, selectedVersionId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
    // Initial load only; subsequent refreshes preserve the current hierarchy explicitly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function openModal(kind: ModalKind, record?: ModalState["record"]) {
    setError("");
    if (kind === "version" && !record && !selectedProgram) {
      setError("请先选择喷涂程序，再新建程序版本");
      return;
    }
    setModal({ kind, record });
    if (kind === "program") {
      const item = record as Program | undefined;
      setForm({
        program_code: item?.program_code ?? "",
        name: item?.name ?? "",
        factory_id: item?.factory_id ?? selectedProgram?.factory_id ?? factories[0]?.id ?? "",
        process_stage: item?.process_stage ?? selectedProgram?.process_stage ?? "MIDCOAT_EXT",
        station_code: item?.station_code ?? "",
        station_name: item?.station_name ?? "",
        robot_model: item?.robot_model ?? "",
        remark: item?.remark ?? "",
      });
      return;
    }
    const item = record as Version | undefined;
    setForm({
      version: item?.version ?? "",
      status: item?.status ?? "DRAFT",
      source_type: item?.source_type ?? "MANUAL",
      is_master_sample: item?.is_master_sample ?? false,
      approved_by: item?.approved_by ?? "",
      vehicle_model_ids: item?.vehicle_model_ids ?? [],
      color_ids: item?.color_ids ?? [],
    });
  }

  function openBrushConfig(mode: "create" | "edit", brush?: Brush) {
    setError("");
    if (!selectedProgram || !selectedVersion) {
      setError("请先选择喷涂程序和受控版本，再配置刷子");
      return;
    }
    if (mode === "edit" && !brush) {
      setError("请先选择要编辑的刷子");
      return;
    }
    setBrushConfig({ mode, brush });
  }

  async function submitModal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!modal) return;
    setSubmitting(true);
    setError("");
    const editing = Boolean(modal.record);
    try {
      if (modal.kind === "program") {
        const path = editing
          ? `/api/process/spray-programs/${(modal.record as Program).id}`
          : "/api/process/spray-programs";
        await request(path, {
          method: editing ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
      } else {
        const path = editing
          ? `/api/process/program-versions/${(modal.record as Version).id}`
          : `/api/process/spray-programs/${selectedProgramId}/versions`;
        await request(path, {
          method: editing ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
      }
      setNotice(`${modalTitle(modal.kind)}${editing ? "已更新" : "已创建"}`);
      setModal(null);
      await reload();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleBrushConfigSaved() {
    setBrushConfig(null);
    setNotice("刷子、参数与点位贡献已保存");
    await reload();
    if (selectedVersionId && selectedBrushTableNo) {
      await loadBrushTable(selectedVersionId, selectedBrushTableNo);
    }
  }

  function bulkResult(message: string, type: "success" | "error") {
    setNotice(type === "success" ? message : "");
    setError(type === "error" ? message : "");
  }

  async function advanceVersion(version: Version) {
    const next =
      version.status === "DRAFT"
        ? { status: "PENDING" }
        : version.status === "PENDING"
          ? { status: "APPROVED", approved_by: actorName }
        : version.status === "APPROVED"
            ? { status: "ACTIVE", approved_by: version.approved_by ?? actorName }
            : null;
    if (!next) return;
    setSubmitting(true);
    try {
      await request(`/api/process/program-versions/${version.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(next),
      });
      setNotice(`版本状态已更新为${statusLabels[next.status]}`);
      await reload();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "状态更新失败");
    } finally {
      setSubmitting(false);
    }
  }

  const brushTableOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const brush of brushes) {
      if (!seen.has(brush.brush_table_no)) seen.set(brush.brush_table_no, brush.brush_table_no);
    }
    return Array.from(seen.entries());
  }, [brushes]);

  function handleProgramChange(programId: string) {
    setSelectedBrushTableNo("");
    setAllBrushData({});
    setEditingRowKey(null);
    void loadProgram(programId);
  }

  function handleVersionChange(versionId: string) {
    setSelectedBrushTableNo("");
    setAllBrushData({});
    setEditingRowKey(null);
    void loadVersion(versionId);
  }

  function handleBrushTableChange(tableNo: string) {
    setEditingRowKey(null);
    setSelectedBrushTableNo(tableNo);
    if (selectedVersionId && tableNo) {
      void loadBrushTable(selectedVersionId, tableNo);
    } else {
      setAllBrushData({});
    }
  }

  const paramCodes = useMemo(
    () => stageParamCodes(selectedProgram?.process_stage ?? ""),
    [selectedProgram?.process_stage],
  );

  const recipeRows = useMemo(() => {
    if (!selectedBrushTableNo || !brushes.length) return [];
    const tableBrushes = brushes.filter((b) => b.brush_table_no === selectedBrushTableNo);
    const rows: Array<{
      key: string;
      brush: Brush;
      pointId: string;
      pointLabel: string;
      params: BrushParameter[];
      contribution: Contribution | null;
    }> = [];
    for (const brush of tableBrushes) {
      const data = allBrushData[brush.id] ?? { parameters: [], contributions: [] };
      const pointRows = data.contributions.length ? data.contributions : [null];
      for (const contrib of pointRows) {
        const point = points.find((p) => p.id === contrib?.measurement_point_id);
        rows.push({
          key: `${brush.id}__${contrib?.measurement_point_id ?? "none"}`,
          brush,
          pointId: contrib?.measurement_point_id ?? "",
          pointLabel: point ? `${point.code} / ${point.name}` : "",
          params: data.parameters,
          contribution: contrib ?? null,
        });
      }
    }
    return rows;
  }, [allBrushData, brushes, points, selectedBrushTableNo]);

  function startEditRow(row: (typeof recipeRows)[number]) {
    const draft: Record<string, string> = { spray_position: row.brush.spray_position ?? "" };
    for (const [code] of paramCodes) {
      const param = row.params.find((p) => p.parameter_code === code);
      draft[code] = param ? String(param.configured_value) : "";
      draft[`${code}__min`] = param && param.soft_min != null ? String(param.soft_min) : "";
      draft[`${code}__max`] = param && param.soft_max != null ? String(param.soft_max) : "";
    }
    draft.weight = row.contribution ? String(row.contribution.contribution_weight) : "";
    setEditingRowKey(row.key);
    setRowDraft(draft);
  }

  function cancelEditRow() {
    setEditingRowKey(null);
    setRowDraft({});
  }

  async function saveRow(row: (typeof recipeRows)[number]) {
    setSubmitting(true);
    setError("");
    try {
      const sprayPosition = rowDraft.spray_position ?? "";
      if (sprayPosition !== (row.brush.spray_position ?? "")) {
        await request(`/api/process/brushes/${row.brush.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ spray_position: sprayPosition || null }),
        });
      }
      for (const [code] of paramCodes) {
        const param = row.params.find((p) => p.parameter_code === code);
        const valueStr = rowDraft[code] ?? "";
        const minStr = rowDraft[`${code}__min`] ?? "";
        const maxStr = rowDraft[`${code}__max`] ?? "";
        const configuredValue = valueStr === "" ? null : Number(valueStr);
        const softMin = minStr === "" ? null : Number(minStr);
        const softMax = maxStr === "" ? null : Number(maxStr);
        if (configuredValue === null && softMin === null && softMax === null) continue;
        if (param) {
          const patch: Record<string, number | null> = {};
          if (configuredValue !== null && configuredValue !== param.configured_value) patch.configured_value = configuredValue;
          if (softMin !== (param.soft_min ?? null)) patch.soft_min = softMin;
          if (softMax !== (param.soft_max ?? null)) patch.soft_max = softMax;
          if (Object.keys(patch).length) {
            await request(`/api/process/brush-parameters/${param.id}`, {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(patch),
            });
          }
        }
      }
      if (row.pointId) {
        const weightStr = rowDraft.weight ?? "";
        if (weightStr !== "") {
          const weight = Number(weightStr);
          if (row.contribution && weight !== row.contribution.contribution_weight) {
            await request(`/api/process/brushes/${row.brush.id}/contributions/${row.pointId}`, {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                overlap_ratio: row.contribution.overlap_ratio,
                contribution_weight: weight,
                source: row.contribution.source,
                version: row.contribution.version,
                is_approved: row.contribution.is_approved,
              }),
            });
          }
        }
      }
      setNotice("已保存");
      setEditingRowKey(null);
      setRowDraft({});
      if (selectedVersionId && selectedBrushTableNo) {
        await loadBrushTable(selectedVersionId, selectedBrushTableNo);
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  function wideDownloadUrl(action: "template" | "export"): string {
    const params = new URLSearchParams();
    params.set("format", wideFormat);
    if (selectedProgramId) params.set("spray_program_id", selectedProgramId);
    if (selectedVersionId) params.set("program_version_id", selectedVersionId);
    if (selectedBrushTableNo) params.set("brush_table_no", selectedBrushTableNo);
    return `/api/recipe-wide/${action}?${params.toString()}`;
  }

  async function wideImportFile(file: File) {
    setWideUploading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      params.set("filename", file.name);
      if (selectedProgramId) params.set("spray_program_id", selectedProgramId);
      if (selectedVersionId) params.set("program_version_id", selectedVersionId);
      if (selectedBrushTableNo) params.set("brush_table_no", selectedBrushTableNo);
      const response = await fetch(`/api/recipe-wide/import?${params.toString()}`, {
        method: "POST",
        headers: { "Content-Type": file.type || "application/octet-stream" },
        body: file,
      });
      const result = (await response.json().catch(() => ({}))) as {
        error?: string;
        total_rows?: number;
        created?: number;
        updated?: number;
        skipped?: number;
        failed?: number;
        errors?: Array<{ row: number; message: string }>;
      };
      if (!response.ok) throw new Error(result.error ?? `导入失败（${response.status}）`);
      const firstError = result.errors?.[0];
      const summary = `已处理 ${result.total_rows ?? 0} 行，新增 ${result.created ?? 0}，更新 ${result.updated ?? 0}，跳过 ${result.skipped ?? 0}，失败 ${result.failed ?? 0}`;
      if (firstError) {
        setError(`${summary}；首个错误：第 ${firstError.row} 行 ${firstError.message}`);
      } else {
        setNotice(summary);
      }
      await reload();
      if (selectedVersionId && selectedBrushTableNo) {
        await loadBrushTable(selectedVersionId, selectedBrushTableNo);
      }
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "宽表导入失败");
    } finally {
      setWideUploading(false);
    }
  }

  return (
    <div className={showChrome ? "page-stack" : "embedded-stack"}>
      {showChrome ? (
      <header className="page-header">
        <div className="page-actions">
          <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
            <RefreshCw className={loading ? "spin" : ""} aria-hidden="true" />
            刷新
          </button>
          {workspaceTab === "programs" ? (
            <BulkDataActions
              resourceKey="process.spray-programs"
              resourceLabel="喷涂程序"
              disabled={loading || submitting}
              onImported={reload}
              onResult={bulkResult}
            />
          ) : null}
          {workspaceTab === "programs" ? <button className="button button-primary" onClick={() => openModal("program")}>
            <Plus aria-hidden="true" />
            新建喷涂程序
          </button> : null}
        </div>
      </header>
      ) : null}
      {error ? <div className="message-banner message-error">{error}</div> : null}
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}

      {!hideOuterTabs ? (
      <div className="master-tabs program-workspace-tabs">
        <button className={workspaceTab === "programs" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setWorkspaceTab("programs")}>程序、刷子与参数</button>
        <button className={workspaceTab === "durr" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setWorkspaceTab("durr")}>机器人设备与轨迹</button>
        <button className={workspaceTab === "diff" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setWorkspaceTab("diff")}>版本对比</button>
        {contextFilterActive && workspaceTab === "programs" ? <span className="context-filter-hint">已按顶部作业范围筛选</span> : null}
      </div>
      ) : null}

      {workspaceTab === "programs" ? <section className="recipe-workspace">
        <div className="recipe-cascading-bar">
          <div className="recipe-select">
            <span>喷涂程序</span>
            <select value={selectedProgramId} onChange={(e) => handleProgramChange(e.target.value)} disabled={loading}>
              <option value="">选择喷涂程序</option>
              {filteredPrograms.map((p) => (
                <option key={p.id} value={p.id}>{p.program_code} · {p.name}</option>
              ))}
            </select>
            <div className="recipe-select-actions">
              <button className="button button-secondary" type="button" onClick={() => openModal("program")} disabled={submitting}><Plus />新建</button>
              {selectedProgram ? <button className="button button-secondary" type="button" onClick={() => openModal("program", selectedProgram)}><Pencil />编辑</button> : null}
            </div>
          </div>
          <div className="recipe-select">
            <span>版本</span>
            <select value={selectedVersionId} onChange={(e) => handleVersionChange(e.target.value)} disabled={loading || !selectedProgram}>
              <option value="">{selectedProgram ? "选择版本" : "先选喷涂程序"}</option>
              {filteredVersions.map((v) => (
                <option key={v.id} value={v.id}>{v.version} · {statusLabels[v.status] ?? v.status}{v.is_master_sample ? " · 封样" : ""}</option>
              ))}
            </select>
            <div className="recipe-select-actions">
              <button className="button button-secondary" type="button" onClick={() => openModal("version")} disabled={submitting || !selectedProgram}><Plus />新建</button>
              {selectedVersion ? <button className="button button-secondary" type="button" onClick={() => openModal("version", selectedVersion)}><Pencil />编辑</button> : null}
              {selectedVersion && ["DRAFT", "PENDING", "APPROVED"].includes(selectedVersion.status) ? (
                <button className="button button-primary" type="button" onClick={() => void advanceVersion(selectedVersion)} disabled={submitting}>
                  {selectedVersion.status === "DRAFT" ? "提交审批" : selectedVersion.status === "PENDING" ? "批准版本" : "激活版本"}
                </button>
              ) : null}
            </div>
          </div>
          <div className="recipe-select">
            <span>刷子表</span>
            <select value={selectedBrushTableNo} onChange={(e) => handleBrushTableChange(e.target.value)} disabled={loading || !selectedVersion}>
              <option value="">{selectedVersion ? "选择刷子表" : "先选版本"}</option>
              {brushTableOptions.map(([no]) => (
                <option key={no} value={no}>{no}</option>
              ))}
            </select>
            <div className="recipe-select-actions">
              <button className="button button-secondary" type="button" onClick={() => openBrushConfig("create")} disabled={submitting || !selectedVersion}><Plus />新建刷子</button>
            </div>
          </div>
          <div className="recipe-wide-actions">
            <select value={wideFormat} onChange={(e) => setWideFormat(e.target.value as "xlsx" | "csv")} disabled={wideUploading || !selectedVersion} aria-label="宽表格式">
              <option value="xlsx">Excel</option>
              <option value="csv">CSV</option>
            </select>
            <a className="button button-secondary" href={selectedVersion ? wideDownloadUrl("template") : undefined} aria-disabled={!selectedVersion}>模板</a>
            <a className="button button-secondary" href={selectedVersion ? wideDownloadUrl("export") : undefined} aria-disabled={!selectedVersion}>导出</a>
            <input ref={wideInputRef} type="file" accept=".xlsx,.csv" hidden onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) void wideImportFile(f); }} />
            <button className="button button-primary" type="button" onClick={() => wideInputRef.current?.click()} disabled={wideUploading || !selectedVersion}>
              {wideUploading ? <LoaderCircle className="spin" /> : <Upload />}导入宽表
            </button>
            <button className="button button-secondary" type="button" onClick={() => void reload()} disabled={loading}><RefreshCw className={loading ? "spin" : ""} />刷新</button>
          </div>
        </div>

        {!selectedBrushTableNo ? (
          <div className="program-empty large-empty"><Settings2 />请依次选择喷涂程序、版本、刷子表后查看与编辑刷子参数及点位贡献。</div>
        ) : !recipeRows.length ? (
          <div className="program-empty">当前刷子表暂无刷子，请通过宽表导入或「配置刷子」新建。</div>
        ) : (
          <div className="recipe-table-wrap">
            <table className="recipe-table">
              <thead>
                <tr>
                  <th>刷子号</th>
                  <th>喷涂点位</th>
                  <th>测量点</th>
                  {paramCodes.map(([, label]) => (
                    <th key={label}>{label}</th>
                  ))}
                  <th>下限</th>
                  <th>上限</th>
                  <th>权重</th>
                  <th className="recipe-action-col">操作</th>
                </tr>
              </thead>
              <tbody>
                {recipeRows.map((row) => {
                  const isEditing = editingRowKey === row.key;
                  const sprayParam = row.params.find((p) => p.parameter_code === paramCodes[0]?.[0]);
                  return (
                    <tr key={row.key}>
                      <td>{row.brush.brush_no}</td>
                      <td>
                        {isEditing ? (
                          <input value={rowDraft.spray_position ?? ""} onChange={(e) => setRowDraft({ ...rowDraft, spray_position: e.target.value })} />
                        ) : (row.brush.spray_position ?? "—")}
                      </td>
                      <td>{row.pointLabel || "—"}</td>
                      {paramCodes.map(([code]) => {
                        const param = row.params.find((p) => p.parameter_code === code);
                        return (
                          <td key={code} className="mono">
                            {isEditing ? (
                              <input type="number" step="any" value={rowDraft[code] ?? ""} onChange={(e) => setRowDraft({ ...rowDraft, [code]: e.target.value })} />
                            ) : (param ? param.configured_value : "—")}
                          </td>
                        );
                      })}
                      <td className="mono">
                        {isEditing ? (
                          <input type="number" step="any" value={rowDraft[`${paramCodes[0]?.[0]}__min`] ?? ""} onChange={(e) => setRowDraft({ ...rowDraft, [`${paramCodes[0]?.[0]}__min`]: e.target.value })} />
                        ) : (sprayParam?.soft_min ?? "—")}
                      </td>
                      <td className="mono">
                        {isEditing ? (
                          <input type="number" step="any" value={rowDraft[`${paramCodes[0]?.[0]}__max`] ?? ""} onChange={(e) => setRowDraft({ ...rowDraft, [`${paramCodes[0]?.[0]}__max`]: e.target.value })} />
                        ) : (sprayParam?.soft_max ?? "—")}
                      </td>
                      <td className="mono">
                        {isEditing ? (
                          <input type="number" step="any" value={rowDraft.weight ?? ""} onChange={(e) => setRowDraft({ ...rowDraft, weight: e.target.value })} />
                        ) : (row.contribution ? row.contribution.contribution_weight : "—")}
                      </td>
                      <td className="recipe-action-col">
                        {isEditing ? (
                          <div className="row-actions">
                            <button className="button button-primary" type="button" onClick={() => void saveRow(row)} disabled={submitting}>保存</button>
                            <button className="button button-secondary" type="button" onClick={cancelEditRow} disabled={submitting}>取消</button>
                          </div>
                        ) : (
                          <button className="button button-secondary" type="button" onClick={() => startEditRow(row)}><Pencil />编辑</button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section> : workspaceTab === "durr" ? <section className="panel"><DurrTrajectoryPanel /></section> : <section className="panel"><VersionDiffPanel versions={versions} programId={selectedProgramId} /></section>}

      {modal ? (
        <ModalShell eyebrow={modal.record ? "编辑" : "新建"} title={`${modal.record ? "编辑" : "新建"}${modalTitle(modal.kind)}`} description="维护喷涂程序或受控版本。刷子、参数与点位贡献请使用统一配置表单。" onClose={closeModal} busy={submitting}>
          <form onSubmit={(event) => void submitModal(event)}>
            <div className="form-grid">{renderFields(modal.kind, form, setForm, { factories, vehicleModels, colors, selectedProgram })}</div>
            <div className="modal-actions"><button className="button button-secondary" type="button" onClick={closeModal} disabled={submitting}>取消</button><button className="button button-primary" type="submit" disabled={submitting}>{submitting ? <LoaderCircle className="spin" aria-hidden="true" /> : null}{submitting ? "正在保存" : "保存"}</button></div>
          </form>
        </ModalShell>
      ) : null}

      {brushConfig && selectedProgram && selectedVersion ? (
        <BrushConfigForm
          open
          editingBrush={brushConfig.mode === "edit" ? brushConfig.brush : null}
          program={selectedProgram}
          version={selectedVersion}
          parts={parts}
          points={points}
          definitions={definitions}
          existingParameters={brushConfig.mode === "edit" ? parameters : []}
          existingContributions={brushConfig.mode === "edit" ? contributions : []}
          busy={loading || submitting}
          onClose={closeBrushConfig}
          onSaved={() => void handleBrushConfigSaved()}
          onError={setError}
        />
      ) : null}
    </div>
  );
}

function modalTitle(kind: ModalKind): string {
  return { program: "喷涂程序", version: "程序版本" }[kind];
}

function field(label: string, key: string, form: FormState, setForm: (value: FormState) => void, options?: { required?: boolean; type?: string }) {
  return (
    <label className="form-field" key={key}><span>{label}{options?.required ? <b>*</b> : null}</span><input type={options?.type ?? "text"} step={options?.type === "number" ? "any" : undefined} required={options?.required} value={String(form[key] ?? "")} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>
  );
}

function selectField(label: string, key: string, form: FormState, setForm: (value: FormState) => void, options: Array<[string, string]>, multiple = false, required = true) {
  const value = form[key] ?? (multiple ? [] : "");
  return (
    <label className="form-field" key={key}><span>{label}{required ? <b>*</b> : null}</span><select multiple={multiple} required={required} value={value as string | string[]} onChange={(event) => setForm({ ...form, [key]: multiple ? Array.from(event.target.selectedOptions, (option) => option.value) : event.target.value })}>{options.map(([optionValue, optionLabel]) => <option value={optionValue} key={optionValue}>{optionLabel}</option>)}</select></label>
  );
}

function checkField(label: string, key: string, form: FormState, setForm: (value: FormState) => void) {
  return <label className="form-field" key={key}><span>{label}</span><span className="checkbox-field"><input type="checkbox" checked={Boolean(form[key])} onChange={(event) => setForm({ ...form, [key]: event.target.checked })} />{label}</span></label>;
}

function renderFields(
  kind: ModalKind,
  form: FormState,
  setForm: (value: FormState) => void,
  refs: { factories: Factory[]; vehicleModels: VehicleModel[]; colors: Color[]; selectedProgram?: Program },
) {
  const relationOptions = (items: Resource[]) => items.map((item) => [item.id, `${item.code} / ${item.name}`] as [string, string]);
  if (kind === "program") return [
    <label className="form-field form-field-wide" key="program-hint"><span>录入提示</span><div className="master-empty">新建程序会优先继承当前已选程序的工艺阶段与工厂上下文；提交前请再次确认站点、阶段和工厂。</div></label>,
    field("程序编号", "program_code", form, setForm, { required: true }),
    field("程序名称", "name", form, setForm, { required: true }),
    selectField("工厂", "factory_id", form, setForm, relationOptions(refs.factories)),
    selectField("工艺阶段", "process_stage", form, setForm, stageOptions.map(([value, label]) => [value, label])),
    field("站点编号", "station_code", form, setForm, { required: true }),
    field("站点名称", "station_name", form, setForm, { required: true }),
    field("机器人型号", "robot_model", form, setForm),
    field("备注", "remark", form, setForm),
  ];
  return [
    <label className="form-field form-field-wide" key="version-hint"><span>录入提示</span><div className="master-empty">适用车型和适用颜色可暂时留空；若当前版本已对外使用，收缩适用范围需要新建版本，不建议直接在原版本删减。</div></label>,
    field("版本号", "version", form, setForm, { required: true }),
    selectField("版本状态", "status", form, setForm, Object.entries(statusLabels)),
    selectField("来源类型", "source_type", form, setForm, [["MANUAL", "人工配置"], ["AI", "AI 推荐"], ["IMPORT", "外部导入"]]),
    field("审批人", "approved_by", form, setForm),
    selectField("适用车型（可多选）", "vehicle_model_ids", form, setForm, relationOptions(refs.vehicleModels), true, false),
    selectField("适用颜色（可多选）", "color_ids", form, setForm, relationOptions(refs.colors), true, false),
    checkField("是否封样版本", "is_master_sample", form, setForm),
  ];
}
