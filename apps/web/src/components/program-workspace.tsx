"use client";

import {
  CheckCircle2,
  ChevronRight,
  CircleDot,
  LoaderCircle,
  Pencil,
  Plus,
  RefreshCw,
  Send,
  Settings2,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { BrushConfigForm } from "@/components/brush-config-form";
import { BulkDataActions } from "@/components/bulk-data-actions";
import { DurrTrajectoryPanel } from "@/components/durr-trajectory-panel";
import { ModalShell } from "@/components/modal-shell";
import { VersionDiffPanel } from "@/components/version-diff-panel";
import { useAuth } from "@/lib/auth-context";
import { stageLabel } from "@/lib/display-labels";
import { definitionsForProcessStage } from "@/lib/parameter-stage-scope";
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

function relationName(resources: Resource[], id?: string | null): string {
  const resource = resources.find((item) => item.id === id);
  return resource ? `${resource.code} / ${resource.name}` : "未关联";
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

  const closeModal = useCallback(() => {
    if (submitting) return;
    setModal(null);
  }, [submitting]);
  const selectedProgram = programs.find((item) => item.id === selectedProgramId);
  const selectedVersion = versions.find((item) => item.id === selectedVersionId);
  const selectedBrush = brushes.find((item) => item.id === selectedBrushId);
  const stageDefinitions = useMemo(
    () => definitionsForProcessStage(definitions, selectedProgram?.process_stage),
    [definitions, selectedProgram?.process_stage],
  );
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
  const versionImportQuery = selectedProgramId
    ? { default_values: JSON.stringify({ spray_program_id: selectedProgramId }) }
    : undefined;
  const brushImportQuery = selectedVersionId
    ? { default_values: JSON.stringify({ program_version_id: selectedVersionId }) }
    : undefined;
  const brushParameterImportQuery = selectedBrushId
    ? { default_values: JSON.stringify({ brush_id: selectedBrushId }) }
    : undefined;
  const contributionImportQuery = selectedBrushId
    ? { default_values: JSON.stringify({ brush_id: selectedBrushId }) }
    : undefined;
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

  const stats = useMemo(() => {
    return [
      ["喷涂程序", filteredPrograms.length, "覆盖五个工艺阶段"],
      ["当前程序版本", filteredVersions.length, selectedProgram?.program_code ?? "请选择程序"],
      ["刷子号", brushes.length, selectedVersion?.version ?? "请选择版本"],
      ["参数 / 贡献", parameters.length + contributions.length, `${parameters.length} 参数 · ${contributions.length} 贡献`],
    ] as const;
  }, [brushes.length, contributions.length, filteredPrograms.length, filteredVersions.length, parameters.length, selectedProgram, selectedVersion]);

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

  async function handleBrushConfigSaved(brushId: string) {
    setBrushConfig(null);
    setNotice("刷子、参数与点位贡献已保存");
    await reload();
    await loadBrush(brushId);
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

  return (
    <div className={showChrome ? "page-stack" : "embedded-stack"}>
      {showChrome ? (
      <header className="page-header">
        <div>
          <span className="page-kicker">程序与刷子</span>
          <h1>喷涂程序中心</h1>
          <p>按程序版本管理五段工艺、刷子参数和测量点贡献权重，所有变更写入业务数据并进入审计。</p>
        </div>
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
      <div className="freshness"><span className="live-dot" /> 实时程序配置 · 版本状态受控</div>
      <section className="module-stat-strip">
        {stats.map(([label, value, note]) => (
          <article key={label}><span>{label}</span><strong>{loading ? "…" : value}</strong><small>{note}</small></article>
        ))}
      </section>
      {error ? <div className="message-banner message-error">{error}</div> : null}
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}
      <div className="freshness">程序、版本、刷子采用版本化与替换治理；当前页面不提供物理删除。</div>
      <div className="freshness">建议顺序：先程序 → 再版本 → 再一次填完刷子身份、本工序参数与测量点贡献。参数列表会按当前程序工序自动过滤（如中涂只显示中涂参数）。</div>

      {!hideOuterTabs ? (
      <div className="master-tabs program-workspace-tabs">
        <button className={workspaceTab === "programs" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setWorkspaceTab("programs")}>程序、刷子与参数</button>
        <button className={workspaceTab === "durr" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setWorkspaceTab("durr")}>机器人设备与轨迹</button>
        <button className={workspaceTab === "diff" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setWorkspaceTab("diff")}>版本对比</button>
        {contextFilterActive && workspaceTab === "programs" ? <span className="context-filter-hint">已按顶部作业范围筛选</span> : null}
      </div>
      ) : workspaceTab === "programs" ? (
        <div className="master-tabs program-workspace-tabs">
          <BulkDataActions resourceKey="process.spray-programs" resourceLabel="喷涂程序" disabled={loading || submitting} onImported={reload} onResult={bulkResult} />
          <button className="button button-primary" onClick={() => openModal("program")}><Plus aria-hidden="true" />新建喷涂程序</button>
          <button className="button button-secondary" onClick={() => void reload()} disabled={loading}><RefreshCw className={loading ? "spin" : ""} aria-hidden="true" />刷新</button>
          {contextFilterActive ? <span className="context-filter-hint">已按顶部作业范围筛选</span> : null}
        </div>
      ) : null}

      {workspaceTab === "programs" ? <section className="program-config-grid">
        <article className="panel program-column">
          <div className="program-column-heading"><div><span className="eyebrow">第 1 步</span><h2>喷涂程序</h2></div><span>{filteredPrograms.length}</span></div>
          <div className="program-list">
            {filteredPrograms.map((program) => (
              <button
                className={program.id === selectedProgramId ? "program-list-item selected" : "program-list-item"}
                key={program.id}
                onClick={() => void loadProgram(program.id)}
              >
                <div><strong>{program.program_code}</strong><span>{program.name}</span><small>{program.station_code} · {stageLabel(program.process_stage)}</small></div>
                <ChevronRight />
              </button>
            ))}
            {!filteredPrograms.length ? <div className="program-empty large-empty"><Settings2 />暂无喷涂程序，请先创建程序主档，再继续维护版本与刷子。</div> : null}
          </div>
          {selectedProgram ? (
            <div className="program-column-actions">
              <button className="button button-secondary" onClick={() => openModal("program", selectedProgram)}><Pencil />编辑</button>
            </div>
          ) : filteredPrograms.length ? <div className="program-empty">请先从左侧明确选择一个喷涂程序，再进入版本维护。</div> : null}
        </article>

        <article className="panel program-column">
          <div className="program-column-heading">
            <div><span className="eyebrow">第 2 步</span><h2>受控版本</h2><small>{selectedProgram ? `当前归属 ${selectedProgram.program_code}` : "先选择左侧程序后，才能新建或导入版本"}</small></div>
            <div className="row-actions program-heading-actions">
              <BulkDataActions
                resourceKey="process.program-versions"
                resourceLabel="程序版本"
                disabled={loading || submitting || !selectedProgram}
                onImported={reload}
                onResult={bulkResult}
                importQuery={versionImportQuery}
                className="program-version-bulk-actions"
              />
              <button className="button button-secondary" onClick={() => openModal("version")} disabled={!selectedProgram}>
                <Plus />
                新建版本
              </button>
            </div>
          </div>
          <div className="program-list">
            {filteredVersions.map((version) => (
              <button
                className={version.id === selectedVersionId ? "program-list-item selected" : "program-list-item"}
                key={version.id}
                onClick={() => void loadVersion(version.id)}
              >
                <div><strong>{version.version}</strong><span>{statusLabels[version.status] ?? version.status}</span><small>{{ MANUAL: "人工配置", AI: "智能推荐", IMPORT: "外部导入" }[version.source_type] ?? version.source_type}{version.is_master_sample ? " · 封样" : ""}</small></div>
                <span className={`version-dot version-${version.status.toLowerCase()}`} />
              </button>
            ))}
            {!filteredVersions.length ? <div className="program-empty">当前程序暂无版本，请先新建受控版本并补齐适用范围。</div> : null}
          </div>
          {selectedVersion ? (
            <div className="program-column-actions stacked-actions">
              {["DRAFT", "PENDING", "APPROVED"].includes(selectedVersion.status) ? (
                <button className="button button-primary" onClick={() => void advanceVersion(selectedVersion)} disabled={submitting}>
                  {selectedVersion.status === "DRAFT" ? <Send /> : <CheckCircle2 />}
                  {selectedVersion.status === "DRAFT" ? "提交审批" : selectedVersion.status === "PENDING" ? "批准版本" : "激活版本"}
                </button>
              ) : null}
              <div>
                <button className="button button-secondary" onClick={() => openModal("version", selectedVersion)}><Pencil />编辑</button>
              </div>
            </div>
          ) : selectedProgram ? <div className="program-empty">请先选择一个程序版本，再维护刷子和审批流转。</div> : null}
        </article>

        <article className="panel program-detail-column">
          <div className="program-column-heading">
            <div><span className="eyebrow">第 3 步</span><h2>刷子与点位贡献</h2><small>{selectedVersion ? `当前归属 ${selectedVersion.version}${selectedProgram ? ` · ${stageLabel(selectedProgram.process_stage)}` : ""}` : "先选择受控版本后，才能导入或新建刷子"}</small></div>
            <div className="row-actions program-heading-actions">
              <BulkDataActions
                resourceKey="process.brushes"
                resourceLabel="刷子"
                disabled={loading || submitting || !selectedVersion}
                onImported={reload}
                onResult={bulkResult}
                importQuery={brushImportQuery}
                className="program-version-bulk-actions"
              />
              <button className="button button-primary" onClick={() => openBrushConfig("create")} disabled={!selectedVersion}><Plus />配置刷子（参数+贡献）</button>
            </div>
          </div>
          {!selectedVersion ? <div className="program-empty">先选择程序版本，再一次填完刷子身份、本工序参数与测量点贡献。</div> : null}
          <div className="brush-selector">
            {brushes.map((brush) => (
              <button className={brush.id === selectedBrushId ? "brush-chip selected" : "brush-chip"} key={brush.id} onClick={() => void loadBrush(brush.id)}>
                <CircleDot />{brush.brush_no}<span>{brush.brush_table_no}</span>
              </button>
            ))}
            {!brushes.length ? <span className="program-empty">当前版本暂无刷子号。</span> : null}
          </div>
          {selectedBrush ? (
            <>
              <div className="brush-summary">
                <div><span>刷子号</span><strong>{selectedBrush.brush_no}</strong></div>
                <div><span>刷子表号</span><strong>{selectedBrush.brush_table_no}</strong></div>
                <div><span>喷涂位置</span><strong>{selectedBrush.spray_position ?? "待维护"}</strong></div>
                <div><span>负责零件</span><strong>{relationName(parts, selectedBrush.part_id)}</strong></div>
                <div className="row-actions">
                  <button className="button button-secondary" onClick={() => openBrushConfig("edit", selectedBrush)}><Pencil />编辑完整配置</button>
                </div>
              </div>
              <div className="program-subsection">
                <div className="program-subheading">
                  <div>
                    <span className="eyebrow">参数矩阵</span>
                    <h3>配置参数</h3>
                    <small>
                      {selectedProgram
                        ? `仅展示 ${stageLabel(selectedProgram.process_stage)} 相关参数（目录 ${stageDefinitions.length} 项）· 刷子 ${selectedBrush.brush_no}`
                        : `当前归属刷子 ${selectedBrush.brush_no}`}
                    </small>
                  </div>
                  <div className="row-actions program-heading-actions">
                    <BulkDataActions resourceKey="process.brush-parameters" resourceLabel="刷子参数" disabled={loading || submitting || !selectedBrush} onImported={reload} onResult={bulkResult} importQuery={brushParameterImportQuery} className="program-version-bulk-actions" />
                    <button className="button button-secondary" onClick={() => openBrushConfig("edit", selectedBrush)}><Pencil />在表单中改</button>
                  </div>
                </div>
                <div className="compact-table">
                  <div className="compact-row compact-head"><span>参数</span><span>配置值</span><span>软边界</span><span>可推荐</span></div>
                  {parameters.map((parameter) => (
                    <div className="compact-row" key={parameter.id}>
                      <span><strong>{parameter.parameter_name}</strong><small>{parameter.parameter_code}</small></span>
                      <span className="mono">{parameter.configured_value} {parameter.unit}</span>
                      <span className="mono">{parameter.soft_min ?? "—"} ~ {parameter.soft_max ?? "—"}</span>
                      <span>{parameter.is_recommendable ? "是" : "否"}</span>
                    </div>
                  ))}
                  {!parameters.length ? <div className="program-empty">当前刷子暂无配置参数，请点「编辑完整配置」一次填完本工序参数。</div> : null}
                </div>
              </div>
              <div className="program-subsection">
                <div className="program-subheading">
                  <div>
                    <span className="eyebrow">点位贡献</span>
                    <h3>测量点贡献权重</h3>
                    <small>当前归属刷子 {selectedBrush.brush_no} · 与参数同表单维护</small>
                  </div>
                  <div className="row-actions program-heading-actions">
                    <BulkDataActions resourceKey="process.brush-contributions" resourceLabel="点位贡献" disabled={loading || submitting || !selectedBrush} onImported={reload} onResult={bulkResult} importQuery={contributionImportQuery} className="program-version-bulk-actions" />
                    <button className="button button-secondary" onClick={() => openBrushConfig("edit", selectedBrush)}><Pencil />在表单中改</button>
                  </div>
                </div>
                <div className="compact-table">
                  <div className="compact-row contribution-row compact-head"><span>测量点</span><span>重叠率</span><span>贡献权重</span><span>审批</span></div>
                  {contributions.map((item) => (
                    <div className="compact-row contribution-row" key={item.id}>
                      <span><strong>{relationName(points, item.measurement_point_id)}</strong><small>{item.source} · {item.version}</small></span>
                      <span className="mono">{(item.overlap_ratio * 100).toFixed(1)}%</span>
                      <span className="mono">{(item.contribution_weight * 100).toFixed(1)}%</span>
                      <span>{item.is_approved ? "已审批" : "待审批"}</span>
                    </div>
                  ))}
                  {!contributions.length ? <div className="program-empty">当前刷子暂无点位贡献，请在统一表单中勾选测量点并填写权重。</div> : null}
                </div>
              </div>
            </>
          ) : <div className="program-empty large-empty"><Settings2 />请选择刷子查看摘要，或点「配置刷子（参数+贡献）」一次填完。</div>}
        </article>
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
          onClose={() => setBrushConfig(null)}
          onSaved={(brushId) => void handleBrushConfigSaved(brushId)}
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
