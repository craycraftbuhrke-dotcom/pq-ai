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

import { BulkDataActions } from "@/components/bulk-data-actions";
import { DurrTrajectoryPanel } from "@/components/durr-trajectory-panel";
import { VersionDiffPanel } from "@/components/version-diff-panel";
import { useAuth } from "@/lib/auth-context";
import { useModalDismiss } from "@/lib/use-modal-dismiss";

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
type ModalKind = "program" | "version" | "brush" | "parameter" | "contribution";
type ModalState = { kind: ModalKind; record?: Program | Version | Brush | BrushParameter | Contribution };
type FormValue = string | boolean | string[];
type FormState = Record<string, FormValue>;

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

export function ProgramWorkspace() {
  const { actor } = useAuth();
  const actorName = actor.isAuthenticated ? actor.displayName : "";
  const [workspaceTab, setWorkspaceTab] = useState<"programs" | "durr" | "diff">("programs");
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

  const closeModal = useCallback(() => {
    if (submitting) return;
    setModal(null);
  }, [submitting]);
  useModalDismiss({ open: modal !== null, onClose: closeModal, busy: submitting });

  const selectedProgram = programs.find((item) => item.id === selectedProgramId);
  const selectedVersion = versions.find((item) => item.id === selectedVersionId);
  const selectedBrush = brushes.find((item) => item.id === selectedBrushId);
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
  const selectableContributionPoints = points.filter((point) => {
    if (point.point_type && point.point_type !== "QUALITY") return false;
    if (selectedBrush?.part_id && point.part_id !== selectedBrush.part_id) return false;
    if (selectedVersion?.vehicle_model_ids?.length && !selectedVersion.vehicle_model_ids.includes(point.vehicle_model_id)) return false;
    return true;
  });

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
      ["喷涂程序", programs.length, "覆盖五个工艺阶段"],
      ["当前程序版本", versions.length, selectedProgram?.program_code ?? "请选择程序"],
      ["刷子号", brushes.length, selectedVersion?.version ?? "请选择版本"],
      ["参数 / 贡献", parameters.length + contributions.length, `${parameters.length} 参数 · ${contributions.length} 贡献`],
    ] as const;
  }, [brushes.length, contributions.length, parameters.length, programs.length, selectedProgram, selectedVersion, versions]);

  function openModal(kind: ModalKind, record?: ModalState["record"]) {
    setError("");
    if (kind === "version" && !record && !selectedProgram) {
      setError("请先选择喷涂程序，再新建程序版本");
      return;
    }
    if (kind === "brush" && !record && !selectedVersion) {
      setError("请先选择程序版本，再新增刷子");
      return;
    }
    if (kind === "parameter" && !record && !selectedBrush) {
      setError("请先选择刷子，再维护刷子参数");
      return;
    }
    if (kind === "contribution" && !record) {
      if (!selectedBrush) {
        setError("请先选择刷子，再配置点位贡献");
        return;
      }
      if (!selectableContributionPoints.length) {
        setError("当前刷子下暂无可配置的质量测量点；请先补齐版本适用车型、刷子负责零件或测量点主数据");
        return;
      }
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
    } else if (kind === "version") {
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
    } else if (kind === "brush") {
      const item = record as Brush | undefined;
      setForm({
        brush_no: item?.brush_no ?? "",
        brush_table_no: item?.brush_table_no ?? "",
        spray_position: item?.spray_position ?? "",
        part_id: item?.part_id ?? "",
        remark: item?.remark ?? "",
      });
    } else if (kind === "parameter") {
      const item = record as BrushParameter | undefined;
      setForm({
        parameter_definition_id: item?.parameter_definition_id ?? definitions[0]?.id ?? "",
        configured_value: item ? String(item.configured_value) : "",
        soft_min: item?.soft_min === null || item?.soft_min === undefined ? "" : String(item.soft_min),
        soft_max: item?.soft_max === null || item?.soft_max === undefined ? "" : String(item.soft_max),
        is_recommendable: item?.is_recommendable ?? true,
      });
    } else {
      const item = record as Contribution | undefined;
      setForm({
        measurement_point_id: item?.measurement_point_id ?? selectableContributionPoints[0]?.id ?? "",
        overlap_ratio: item ? String(item.overlap_ratio) : "0.5",
        contribution_weight: item ? String(item.contribution_weight) : "0.5",
        source: item?.source ?? "EXPERT",
        version: item?.version ?? "1.0",
        is_approved: item?.is_approved ?? false,
      });
    }
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
      } else if (modal.kind === "version") {
        const path = editing
          ? `/api/process/program-versions/${(modal.record as Version).id}`
          : `/api/process/spray-programs/${selectedProgramId}/versions`;
        await request(path, {
          method: editing ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
      } else if (modal.kind === "brush") {
        const body = { ...form, part_id: form.part_id || null };
        const path = editing
          ? `/api/process/brushes/${(modal.record as Brush).id}`
          : `/api/process/program-versions/${selectedVersionId}/brushes`;
        await request(path, {
          method: editing ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      } else if (modal.kind === "parameter") {
        const definition = definitions.find((item) => item.id === form.parameter_definition_id);
        if (!definition) throw new Error("请选择有效参数定义");
        const body = {
          parameter_definition_id: definition.id,
          parameter_code: definition.code,
          parameter_name: definition.name,
          configured_value: Number(form.configured_value),
          unit: definition.unit,
          soft_min: form.soft_min === "" ? null : Number(form.soft_min),
          soft_max: form.soft_max === "" ? null : Number(form.soft_max),
          hard_min: definition.hard_min ?? null,
          hard_max: definition.hard_max ?? null,
          is_recommendable: form.is_recommendable,
        };
        const path = editing
          ? `/api/process/brush-parameters/${(modal.record as BrushParameter).id}`
          : `/api/process/brushes/${selectedBrushId}/parameters`;
        await request(path, {
          method: editing ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      } else {
        const pointId = String(form.measurement_point_id);
        if (!pointId) throw new Error("请先选择可用测量点，再配置点位贡献");
        const body = {
          overlap_ratio: Number(form.overlap_ratio),
          contribution_weight: Number(form.contribution_weight),
          source: form.source,
          version: form.version,
          is_approved: form.is_approved,
        };
        await request(`/api/process/brushes/${selectedBrushId}/contributions/${pointId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
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
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">PROGRAM · BRUSH · CONTRIBUTION</span>
          <h1>喷涂程序中心</h1>
          <p>按程序版本管理五段工艺、刷子参数和测量点贡献权重，所有变更写入 MySQL 并进入审计。</p>
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
      <div className="freshness"><span className="live-dot" /> MySQL 实时程序配置 · 版本状态受控</div>
      <section className="module-stat-strip">
        {stats.map(([label, value, note]) => (
          <article key={label}><span>{label}</span><strong>{loading ? "…" : value}</strong><small>{note}</small></article>
        ))}
      </section>
      {error ? <div className="message-banner message-error">{error}</div> : null}
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}
      <div className="freshness">程序、版本、刷子、参数和点位贡献采用版本化与替换治理；当前页面不提供物理删除。</div>
      <div className="freshness">当前流程建议按“先程序，再版本，再刷子，最后参数与点位贡献”顺序维护；点位贡献会按版本适用车型和刷子负责零件过滤候选点位。</div>

      <div className="master-tabs program-workspace-tabs">
        <button className={workspaceTab === "programs" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setWorkspaceTab("programs")}>程序、刷子与参数</button>
        <button className={workspaceTab === "durr" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setWorkspaceTab("durr")}>Dürr 设备、轨迹与贡献治理</button>
        <button className={workspaceTab === "diff" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setWorkspaceTab("diff")}>版本对比</button>
      </div>

      {workspaceTab === "programs" ? <section className="program-config-grid">
        <article className="panel program-column">
          <div className="program-column-heading"><div><span className="eyebrow">01 PROGRAM</span><h2>喷涂程序</h2></div><span>{programs.length}</span></div>
          <div className="program-list">
            {programs.map((program) => (
              <button
                className={program.id === selectedProgramId ? "program-list-item selected" : "program-list-item"}
                key={program.id}
                onClick={() => void loadProgram(program.id)}
              >
                <div><strong>{program.program_code}</strong><span>{program.name}</span><small>{program.station_code} · {program.process_stage}</small></div>
                <ChevronRight />
              </button>
            ))}
            {!programs.length ? <div className="program-empty large-empty"><Settings2 />暂无喷涂程序，请先创建程序主档，再继续维护版本与刷子。</div> : null}
          </div>
          {selectedProgram ? (
            <div className="program-column-actions">
              <button className="button button-secondary" onClick={() => openModal("program", selectedProgram)}><Pencil />编辑</button>
            </div>
          ) : programs.length ? <div className="program-empty">请先从左侧明确选择一个喷涂程序，再进入版本维护。</div> : null}
        </article>

        <article className="panel program-column">
          <div className="program-column-heading">
            <div><span className="eyebrow">02 VERSION</span><h2>受控版本</h2><small>{selectedProgram ? `当前归属 ${selectedProgram.program_code}` : "先选择左侧程序后，才能新建或导入版本"}</small></div>
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
            {versions.map((version) => (
              <button
                className={version.id === selectedVersionId ? "program-list-item selected" : "program-list-item"}
                key={version.id}
                onClick={() => void loadVersion(version.id)}
              >
                <div><strong>{version.version}</strong><span>{statusLabels[version.status] ?? version.status}</span><small>{version.source_type}{version.is_master_sample ? " · 封样" : ""}</small></div>
                <span className={`version-dot version-${version.status.toLowerCase()}`} />
              </button>
            ))}
            {!versions.length ? <div className="program-empty">当前程序暂无版本，请先新建受控版本并补齐适用范围。</div> : null}
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
            <div><span className="eyebrow">03 BRUSH & POINT</span><h2>刷子与点位贡献</h2><small>{selectedVersion ? `当前归属 ${selectedVersion.version}` : "先选择受控版本后，才能导入或新建刷子"}</small></div>
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
              <button className="button button-secondary" onClick={() => openModal("brush")} disabled={!selectedVersion}><Plus />新增刷子</button>
            </div>
          </div>
          {!selectedVersion ? <div className="program-empty">先选择程序版本，才能新增刷子、参数和点位贡献。</div> : null}
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
                  <button className="icon-button" onClick={() => openModal("brush", selectedBrush)} aria-label="编辑刷子"><Pencil /></button>
                </div>
              </div>
              <div className="program-subsection">
                <div className="program-subheading"><div><span className="eyebrow">PARAMETER MATRIX</span><h3>配置参数</h3><small>{selectedBrush ? `当前归属刷子 ${selectedBrush.brush_no}` : "先选择刷子后，才能导入或新增参数"}</small></div><div className="row-actions program-heading-actions"><BulkDataActions resourceKey="process.brush-parameters" resourceLabel="刷子参数" disabled={loading || submitting || !selectedBrush} onImported={reload} onResult={bulkResult} importQuery={brushParameterImportQuery} className="program-version-bulk-actions" /><button className="button button-secondary" onClick={() => openModal("parameter")}><Plus />新增参数</button></div></div>
                <div className="compact-table">
                  <div className="compact-row compact-head"><span>参数</span><span>配置值</span><span>软边界</span><span>可推荐</span><span /></div>
                  {parameters.map((parameter) => (
                    <div className="compact-row" key={parameter.id}>
                      <span><strong>{parameter.parameter_name}</strong><small>{parameter.parameter_code}</small></span>
                      <span className="mono">{parameter.configured_value} {parameter.unit}</span>
                      <span className="mono">{parameter.soft_min ?? "—"} ~ {parameter.soft_max ?? "—"}</span>
                      <span>{parameter.is_recommendable ? "是" : "否"}</span>
                      <span className="row-actions"><button className="icon-button" onClick={() => openModal("parameter", parameter)} aria-label={`编辑参数 ${parameter.parameter_code}`}><Pencil /></button></span>
                    </div>
                  ))}
                  {!parameters.length ? <div className="program-empty">当前刷子暂无配置参数，请先补齐参数定义与配置值。</div> : null}
                </div>
              </div>
              <div className="program-subsection">
                <div className="program-subheading"><div><span className="eyebrow">POINT CONTRIBUTION</span><h3>测量点贡献权重</h3><small>{selectedBrush ? `当前归属刷子 ${selectedBrush.brush_no}` : "先选择刷子后，才能导入或配置贡献"}</small></div><div className="row-actions program-heading-actions"><BulkDataActions resourceKey="process.brush-contributions" resourceLabel="点位贡献" disabled={loading || submitting || !selectedBrush} onImported={reload} onResult={bulkResult} importQuery={contributionImportQuery} className="program-version-bulk-actions" /><button className="button button-secondary" onClick={() => openModal("contribution")}><Plus />配置贡献</button></div></div>
                {!selectableContributionPoints.length ? <div className="program-empty">当前刷子下暂无可用质量测量点。请检查版本适用车型、刷子负责零件和测量点主数据是否已补齐。</div> : null}
                <div className="compact-table">
                  <div className="compact-row contribution-row compact-head"><span>测量点</span><span>重叠率</span><span>贡献权重</span><span>审批</span><span /></div>
                  {contributions.map((item) => (
                    <div className="compact-row contribution-row" key={item.id}>
                      <span><strong>{relationName(points, item.measurement_point_id)}</strong><small>{item.source} · {item.version}</small></span>
                      <span className="mono">{(item.overlap_ratio * 100).toFixed(1)}%</span>
                      <span className="mono">{(item.contribution_weight * 100).toFixed(1)}%</span>
                      <span>{item.is_approved ? "已审批" : "待审批"}</span>
                      <span className="row-actions"><button className="icon-button" onClick={() => openModal("contribution", item)} aria-label={`编辑贡献 ${item.measurement_point_id}`}><Pencil /></button></span>
                    </div>
                  ))}
                  {!contributions.length ? <div className="program-empty">当前刷子暂无点位贡献，请从可用测量点中显式选择后再配置。</div> : null}
                </div>
              </div>
            </>
          ) : <div className="program-empty large-empty"><Settings2 />请选择或新增刷子以维护参数和点位贡献。</div>}
        </article>
      </section> : workspaceTab === "durr" ? <section className="panel"><DurrTrajectoryPanel /></section> : <section className="panel"><VersionDiffPanel versions={versions} programId={selectedProgramId} /></section>}

      {modal ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={closeModal}>
          <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="program-modal-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal-heading"><div><span className="eyebrow">{modal.record ? "EDIT" : "CREATE"}</span><h2 id="program-modal-title">{modal.record ? "编辑" : "新建"}{modalTitle(modal.kind)}</h2></div><button className="icon-button" onClick={closeModal} aria-label="关闭"><X aria-hidden="true" /></button></div>
            <form onSubmit={(event) => void submitModal(event)}>
              <div className="form-grid">{renderFields(modal.kind, form, setForm, { factories, vehicleModels, colors, parts, points: selectableContributionPoints, definitions, selectedProgram, selectedVersion, selectedBrush })}</div>
              <div className="modal-actions"><button className="button button-secondary" type="button" onClick={closeModal} disabled={submitting}>取消</button><button className="button button-primary" type="submit" disabled={submitting}>{submitting ? <LoaderCircle className="spin" aria-hidden="true" /> : null}{submitting ? "正在保存" : "保存到 MySQL"}</button></div>
            </form>
          </section>
        </div>
      ) : null}
    </div>
  );
}

function modalTitle(kind: ModalKind): string {
  return { program: "喷涂程序", version: "程序版本", brush: "刷子", parameter: "刷子参数", contribution: "点位贡献" }[kind];
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
  refs: { factories: Factory[]; vehicleModels: VehicleModel[]; colors: Color[]; parts: Part[]; points: Point[]; definitions: ParameterDefinition[]; selectedProgram?: Program; selectedVersion?: Version; selectedBrush?: Brush },
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
  if (kind === "version") return [
    <label className="form-field form-field-wide" key="version-hint"><span>录入提示</span><div className="master-empty">适用车型和适用颜色可暂时留空；若当前版本已对外使用，收缩适用范围需要新建版本，不建议直接在原版本删减。</div></label>,
    field("版本号", "version", form, setForm, { required: true }),
    selectField("版本状态", "status", form, setForm, Object.entries(statusLabels)),
    selectField("来源类型", "source_type", form, setForm, [["MANUAL", "人工配置"], ["AI", "AI 推荐"], ["IMPORT", "外部导入"]]),
    field("审批人", "approved_by", form, setForm),
    selectField("适用车型（可多选）", "vehicle_model_ids", form, setForm, relationOptions(refs.vehicleModels), true, false),
    selectField("适用颜色（可多选）", "color_ids", form, setForm, relationOptions(refs.colors), true, false),
    checkField("是否封样版本", "is_master_sample", form, setForm),
  ];
  if (kind === "brush") return [
    <label className="form-field form-field-wide" key="brush-hint"><span>录入提示</span><div className="master-empty">刷子属于当前已选程序版本；建议同步维护负责零件，后续点位贡献会按该零件过滤候选测量点。</div></label>,
    field("刷子号", "brush_no", form, setForm, { required: true }),
    field("刷子表号", "brush_table_no", form, setForm, { required: true }),
    field("喷涂位置", "spray_position", form, setForm),
    selectField("负责零件", "part_id", form, setForm, [["", "未关联"], ...relationOptions(refs.parts)], false, false),
    field("备注", "remark", form, setForm),
  ];
  if (kind === "parameter") return [
    <label className="form-field form-field-wide" key="parameter-hint"><span>录入提示</span><div className="master-empty">参数将绑定到当前已选刷子；请优先选用受治理参数定义，避免同一刷子重复维护相同参数代码。</div></label>,
    selectField("参数定义", "parameter_definition_id", form, setForm, refs.definitions.map((item) => [item.id, `${item.name} · ${item.code} (${item.unit})`])),
    field("配置值", "configured_value", form, setForm, { required: true, type: "number" }),
    field("软下限", "soft_min", form, setForm, { type: "number" }),
    field("软上限", "soft_max", form, setForm, { type: "number" }),
    checkField("允许 AI 推荐", "is_recommendable", form, setForm),
  ];
  return [
    <label className="form-field form-field-wide" key="contribution-hint"><span>录入提示</span><div className="master-empty">候选测量点会按当前版本适用车型、刷子负责零件和质量点类型自动过滤；如无可选点，请先补齐主数据或版本适用范围。</div></label>,
    selectField("测量点", "measurement_point_id", form, setForm, relationOptions(refs.points)),
    field("重叠率（0~1）", "overlap_ratio", form, setForm, { required: true, type: "number" }),
    field("贡献权重（0~1）", "contribution_weight", form, setForm, { required: true, type: "number" }),
    field("来源", "source", form, setForm, { required: true }),
    field("权重版本", "version", form, setForm, { required: true }),
    checkField("已审批", "is_approved", form, setForm),
  ];
}
