"use client";

import {
  Bot,
  Cable,
  LoaderCircle,
  Pause,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Sparkles,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";

import { ModalShell } from "@/components/modal-shell";
import { stageLabel } from "@/lib/display-labels";
import { useWorkspaceContext } from "@/lib/workspace-context";

type Named = { id: string; code?: string; name?: string; factory_id?: string; status?: string };
type Robot = Named & {
  model?: string;
  serial_no?: string;
  controller_software_version?: string | null;
};
type Atomizer = Named & {
  model?: string;
  serial_no?: string;
  bell_cup_type?: string | null;
  bell_cup_code?: string | null;
};
type SprayProgram = Named & {
  program_code: string;
  process_stage: string;
  factory_id: string;
  station_code?: string;
  station_name?: string;
};
type ProgramVersion = Named & {
  version: string;
  status?: string;
  vehicle_model_ids?: string[];
};
type Brush = {
  id: string;
  brush_no: string;
  brush_table_no: string;
  program_version_id: string;
  part_id?: string | null;
};
type BrushParameter = {
  id: string;
  brush_id: string;
  parameter_code: string;
  parameter_name: string;
  configured_value: number;
  unit: string;
};

type StageCode =
  | "MIDCOAT_EXT"
  | "BASECOAT_1"
  | "BASECOAT_2"
  | "CLEARCOAT_1"
  | "CLEARCOAT_2";

type SlotSide = "L" | "R";

type SlotAssignment = {
  robotId: string;
  atomizerId?: string;
  programId?: string;
  programVersionId?: string;
};

type LineLayout = Record<StageCode, Partial<Record<SlotSide, SlotAssignment | null>>>;

type Selection =
  | { kind: "stage"; stage: StageCode }
  | { kind: "slot"; stage: StageCode; side: SlotSide }
  | null;

const STAGE_ORDER: StageCode[] = [
  "MIDCOAT_EXT",
  "BASECOAT_1",
  "BASECOAT_2",
  "CLEARCOAT_1",
  "CLEARCOAT_2",
];

const STAGE_META: Record<
  StageCode,
  { coating: string; coatingLabel: string; tone: string; stationHint: string }
> = {
  MIDCOAT_EXT: {
    coating: "MIDCOAT",
    coatingLabel: "中涂",
    tone: "#1687a1",
    stationHint: "中涂外喷工位 · 旋杯静电",
  },
  BASECOAT_1: {
    coating: "BASECOAT",
    coatingLabel: "色漆",
    tone: "#0f9f83",
    stationHint: "色漆一站 · 效果取向",
  },
  BASECOAT_2: {
    coating: "BASECOAT",
    coatingLabel: "色漆",
    tone: "#0d8a72",
    stationHint: "色漆二站 · 覆盖与均匀",
  },
  CLEARCOAT_1: {
    coating: "CLEARCOAT",
    coatingLabel: "清漆",
    tone: "#b97918",
    stationHint: "清漆一站 · 流平与 DOI",
  },
  CLEARCOAT_2: {
    coating: "CLEARCOAT",
    coatingLabel: "清漆",
    tone: "#996516",
    stationHint: "清漆二站 · 外观收口",
  },
};

const LAYOUT_STORAGE_KEY = "pq-ai-paint-line-layout-v1";

function emptyLayout(): LineLayout {
  return {
    MIDCOAT_EXT: { L: null, R: null },
    BASECOAT_1: { L: null, R: null },
    BASECOAT_2: { L: null, R: null },
    CLEARCOAT_1: { L: null, R: null },
    CLEARCOAT_2: { L: null, R: null },
  };
}

function loadLayout(factoryId: string): LineLayout {
  if (typeof window === "undefined") return emptyLayout();
  try {
    const raw = window.localStorage.getItem(`${LAYOUT_STORAGE_KEY}:${factoryId || "default"}`);
    if (!raw) return emptyLayout();
    return { ...emptyLayout(), ...(JSON.parse(raw) as LineLayout) };
  } catch {
    return emptyLayout();
  }
}

function saveLayout(factoryId: string, layout: LineLayout) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(`${LAYOUT_STORAGE_KEY}:${factoryId || "default"}`, JSON.stringify(layout));
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });
  const payload = (await response.json().catch(() => ({}))) as T & { error?: string; detail?: string };
  if (!response.ok) {
    throw new Error(payload.error ?? payload.detail ?? `请求失败（${response.status}）`);
  }
  return payload;
}

function formatValue(value?: number | null, unit?: string | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  const text = Number.isInteger(value) ? String(value) : value.toFixed(2);
  return unit ? `${text} ${unit}` : text;
}

export function PaintLineSimulation() {
  const { factoryId, modelId, stage: contextStage } = useWorkspaceContext();
  const [robots, setRobots] = useState<Robot[]>([]);
  const [atomizers, setAtomizers] = useState<Atomizer[]>([]);
  const [programs, setPrograms] = useState<SprayProgram[]>([]);
  const [versionsByProgram, setVersionsByProgram] = useState<Record<string, ProgramVersion[]>>({});
  const [layout, setLayout] = useState<LineLayout>(() => emptyLayout());
  const [selection, setSelection] = useState<Selection>(null);
  const [installTarget, setInstallTarget] = useState<{ stage: StageCode; side: SlotSide } | null>(null);
  const [installForm, setInstallForm] = useState({
    robotId: "",
    atomizerId: "",
    programId: "",
    programVersionId: "",
  });
  const [brushes, setBrushes] = useState<Brush[]>([]);
  const [parametersByBrush, setParametersByBrush] = useState<Record<string, BrushParameter[]>>({});
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const rafRef = useRef<number | null>(null);
  const lastTsRef = useRef<number | null>(null);

  const filteredRobots = useMemo(
    () => robots.filter((item) => !factoryId || item.factory_id === factoryId),
    [robots, factoryId],
  );
  const filteredAtomizers = useMemo(
    () => atomizers.filter((item) => !factoryId || item.factory_id === factoryId),
    [atomizers, factoryId],
  );

  const installedRobotIds = useMemo(() => {
    const ids = new Set<string>();
    for (const stage of STAGE_ORDER) {
      for (const side of ["L", "R"] as SlotSide[]) {
        const slot = layout[stage][side];
        if (slot?.robotId) ids.add(slot.robotId);
      }
    }
    return ids;
  }, [layout]);

  const selectedStage = selection?.stage ?? null;

  const selectedAssignment = useMemo(() => {
    if (!selection || selection.kind !== "slot") return null;
    return layout[selection.stage][selection.side] ?? null;
  }, [layout, selection]);

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextRobots, nextAtomizers, nextPrograms] = await Promise.all([
        request<Robot[]>("/api/process/robot-governance/robots"),
        request<Atomizer[]>("/api/process/robot-governance/atomizers"),
        request<SprayProgram[]>("/api/process/spray-programs"),
      ]);
      setRobots(nextRobots);
      setAtomizers(nextAtomizers);
      setPrograms(nextPrograms);
      setLayout(loadLayout(factoryId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载虚拟产线数据失败");
    } finally {
      setLoading(false);
    }
  }, [factoryId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    setLayout(loadLayout(factoryId));
  }, [factoryId]);

  useEffect(() => {
    if (!contextStage || !STAGE_ORDER.includes(contextStage as StageCode)) return;
    setSelection({ kind: "stage", stage: contextStage as StageCode });
  }, [contextStage]);

  useEffect(() => {
    saveLayout(factoryId, layout);
  }, [factoryId, layout]);

  useEffect(() => {
    if (!playing) {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      lastTsRef.current = null;
      return;
    }
    const tick = (ts: number) => {
      if (lastTsRef.current == null) lastTsRef.current = ts;
      const delta = (ts - lastTsRef.current) / 1000;
      lastTsRef.current = ts;
      setProgress((current) => {
        const next = current + delta * 8;
        if (next >= 100) {
          setPlaying(false);
          setActiveStageIndex(STAGE_ORDER.length - 1);
          return 100;
        }
        const index = Math.min(STAGE_ORDER.length - 1, Math.floor((next / 100) * STAGE_ORDER.length));
        setActiveStageIndex(index);
        return next;
      });
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, [playing]);

  const loadSlotDetail = useCallback(async (assignment: SlotAssignment | null) => {
    setBrushes([]);
    setParametersByBrush({});
    if (!assignment?.programVersionId) return;
    setDetailLoading(true);
    try {
      const nextBrushes = await request<Brush[]>(
        `/api/process/program-versions/${assignment.programVersionId}/brushes`,
      );
      setBrushes(nextBrushes);
      const entries = await Promise.all(
        nextBrushes.map(async (brush) => {
          const params = await request<BrushParameter[]>(`/api/process/brushes/${brush.id}/parameters`);
          return [brush.id, params] as const;
        }),
      );
      setParametersByBrush(Object.fromEntries(entries));
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载刷子参数失败");
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSlotDetail(selectedAssignment);
  }, [selectedAssignment, loadSlotDetail]);

  async function ensureVersions(programId: string) {
    if (!programId || versionsByProgram[programId]) return;
    try {
      const versions = await request<ProgramVersion[]>(`/api/process/spray-programs/${programId}/versions`);
      setVersionsByProgram((current) => ({ ...current, [programId]: versions }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载程序版本失败");
    }
  }

  function openInstall(stage: StageCode, side: SlotSide) {
    const existing = layout[stage][side];
    setInstallTarget({ stage, side });
    setInstallForm({
      robotId: existing?.robotId ?? "",
      atomizerId: existing?.atomizerId ?? "",
      programId: existing?.programId ?? "",
      programVersionId: existing?.programVersionId ?? "",
    });
    if (existing?.programId) void ensureVersions(existing.programId);
  }

  function confirmInstall() {
    if (!installTarget || !installForm.robotId) return;
    const nextAssignment: SlotAssignment = {
      robotId: installForm.robotId,
      atomizerId: installForm.atomizerId || undefined,
      programId: installForm.programId || undefined,
      programVersionId: installForm.programVersionId || undefined,
    };
    setLayout((current) => ({
      ...current,
      [installTarget.stage]: {
        ...current[installTarget.stage],
        [installTarget.side]: nextAssignment,
      },
    }));
    setSelection({ kind: "slot", stage: installTarget.stage, side: installTarget.side });
    setInstallTarget(null);
  }

  function uninstallSlot(stage: StageCode, side: SlotSide) {
    setLayout((current) => ({
      ...current,
      [stage]: { ...current[stage], [side]: null },
    }));
    if (selection?.kind === "slot" && selection.stage === stage && selection.side === side) {
      setSelection({ kind: "stage", stage });
    }
  }

  function resetLayout() {
    setLayout(emptyLayout());
    setSelection(null);
    setProgress(0);
    setActiveStageIndex(0);
    setPlaying(false);
  }

  const bodyLeft = `${Math.min(94, Math.max(3, progress))}%`;
  const selectedRobot = selectedAssignment
    ? robots.find((item) => item.id === selectedAssignment.robotId)
    : null;
  const selectedAtomizer = selectedAssignment?.atomizerId
    ? atomizers.find((item) => item.id === selectedAssignment.atomizerId)
    : null;
  const selectedProgram = selectedAssignment?.programId
    ? programs.find((item) => item.id === selectedAssignment.programId)
    : null;
  const selectedVersion = selectedAssignment?.programVersionId
    ? (versionsByProgram[selectedAssignment.programId ?? ""] ?? []).find(
        (item) => item.id === selectedAssignment.programVersionId,
      )
    : null;

  const installVersions = installForm.programId ? versionsByProgram[installForm.programId] ?? [] : [];
  const availableRobotsForInstall = filteredRobots.filter(
    (robot) =>
      robot.id === installForm.robotId ||
      !installedRobotIds.has(robot.id) ||
      (installTarget && layout[installTarget.stage][installTarget.side]?.robotId === robot.id),
  );

  return (
    <section className="panel paint-line-panel">
      <div className="program-subheading">
        <div>
          <span className="eyebrow">虚拟产线 · 仿真</span>
          <h3>3C2B 五站喷涂线</h3>
          <small>
            按中涂外喷 → 色漆一/二站 → 清漆一/二站布置旋杯机器人。布局保存在本机；喷涂参数来自已维护的程序版本与刷子设定，不编造设备限值。
          </small>
        </div>
        <div className="row-actions">
          <button className="button button-secondary" type="button" onClick={() => void reload()} disabled={loading}>
            {loading ? <LoaderCircle className="spin" /> : <RefreshCw />}
            刷新主数据
          </button>
          <button className="button button-secondary" type="button" onClick={resetLayout}>
            <RotateCcw />
            清空布局
          </button>
          <button
            className="button button-secondary"
            type="button"
            onClick={() => {
              setProgress(0);
              setActiveStageIndex(0);
              setPlaying(false);
            }}
          >
            复位车身
          </button>
          <button
            className={`button ${playing ? "button-secondary" : "button-primary"}`}
            type="button"
            onClick={() => setPlaying((value) => !value)}
          >
            {playing ? <Pause /> : <Play />}
            {playing ? "暂停仿真" : "开始过线"}
          </button>
        </div>
      </div>

      <div className="paint-line-shell">
        {error ? <div className="form-error">{error}</div> : null}

        <div className="paint-line-legend">
          <span className="body-map-legend-label">涂层</span>
          <span className="paint-line-chip" style={{ "--tone": "#1687a1" } as CSSProperties}>
            中涂
          </span>
          <span className="paint-line-chip" style={{ "--tone": "#0f9f83" } as CSSProperties}>
            色漆
          </span>
          <span className="paint-line-chip" style={{ "--tone": "#b97918" } as CSSProperties}>
            清漆
          </span>
          <span className="paint-line-note">
            <Sparkles />
            点击工位或机器人查看参数；空槽可安装机器人台账中的设备。
          </span>
        </div>

        <div className="paint-line-stage">
          <div className="paint-line-sky" aria-hidden="true" />
          <div className="paint-line-ceiling" aria-hidden="true" />
          <div className="paint-line-conveyor" aria-hidden="true">
            <i />
            <i />
            <i />
          </div>

          <div
            className={`paint-line-body ${playing ? "is-moving" : ""}`}
            style={{ left: bodyLeft }}
            aria-hidden="true"
          >
            <div className="paint-line-skid" />
            <div className="paint-line-biw">
              <span />
              <span />
              <span />
            </div>
          </div>

          <div className="paint-line-booths">
            {STAGE_ORDER.map((stage, index) => {
              const meta = STAGE_META[stage];
              const isActive = activeStageIndex === index && (playing || progress > 0);
              const isSelected = selectedStage === stage;
              return (
                <article
                  key={stage}
                  className={`paint-line-booth ${isActive ? "is-active" : ""} ${isSelected ? "is-selected" : ""}`}
                  style={{ "--booth-tone": meta.tone } as CSSProperties}
                  onClick={() => setSelection({ kind: "stage", stage })}
                >
                  <header className="paint-line-booth-head">
                    <span className="mono">{String(index + 1).padStart(2, "0")}</span>
                    <div>
                      <strong>{stageLabel(stage)}</strong>
                      <small>{meta.stationHint}</small>
                    </div>
                    <em>{meta.coatingLabel}</em>
                  </header>

                  <div className="paint-line-booth-chamber">
                    <div className="paint-line-booth-glass" />
                    {(["L", "R"] as SlotSide[]).map((side) => {
                      const assignment = layout[stage][side];
                      const robot = assignment
                        ? robots.find((item) => item.id === assignment.robotId)
                        : null;
                      const spraying = isActive && Boolean(assignment);
                      return (
                        <button
                          key={side}
                          type="button"
                          className={`paint-line-robot-slot side-${side.toLowerCase()} ${assignment ? "has-robot" : ""} ${
                            selection?.kind === "slot" && selection.stage === stage && selection.side === side
                              ? "is-selected"
                              : ""
                          } ${spraying ? "is-spraying" : ""}`}
                          onClick={(event) => {
                            event.stopPropagation();
                            if (!assignment) {
                              openInstall(stage, side);
                              return;
                            }
                            setSelection({ kind: "slot", stage, side });
                          }}
                          title={robot ? `${robot.code} / ${robot.name}` : `安装${side === "L" ? "左侧" : "右侧"}机器人`}
                        >
                          {assignment && robot ? (
                            <>
                              <span className="paint-line-arm-wrap">
                                <RobotArmSvg spraying={spraying} />
                              </span>
                              <span className="paint-line-robot-tag">
                                <b>{robot.code}</b>
                                <small>{side === "L" ? "左" : "右"}</small>
                              </span>
                              {spraying ? <i className="paint-line-mist" aria-hidden="true" /> : null}
                            </>
                          ) : (
                            <span className="paint-line-slot-empty">
                              <Plus />
                              安装
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </article>
              );
            })}
          </div>
        </div>

        <div className="paint-line-progress">
          <span>过线进度</span>
          <div className="paint-line-progress-track">
            <i style={{ width: `${progress}%` }} />
          </div>
          <strong className="mono">{progress.toFixed(0)}%</strong>
          <small>
            当前工位 · {stageLabel(STAGE_ORDER[activeStageIndex])}
            {modelId ? " · 已按顶部车型上下文过滤程序" : ""}
          </small>
        </div>

        <div className="paint-line-detail-grid">
          <aside className="paint-line-inventory">
            <div className="program-subheading compact">
              <div>
                <span className="eyebrow">设备台账</span>
                <h4>可安装机器人</h4>
              </div>
            </div>
            {loading ? (
              <div className="program-empty">
                <LoaderCircle className="spin" />
                正在加载…
              </div>
            ) : !filteredRobots.length ? (
              <div className="program-empty">
                <Bot />
                当前工厂暂无机器人台账。请先到主数据「机器人与轨迹」维护 Dürr 机器人。
              </div>
            ) : (
              <div className="paint-line-inventory-list">
                {filteredRobots.map((robot) => {
                  const used = installedRobotIds.has(robot.id);
                  return (
                    <button
                      key={robot.id}
                      type="button"
                      className={`paint-line-inventory-card ${used ? "is-used" : ""}`}
                      onClick={() => {
                        const stage = (selectedStage ?? STAGE_ORDER[activeStageIndex]) as StageCode;
                        const emptySide =
                          (["L", "R"] as SlotSide[]).find((side) => !layout[stage][side]) ?? "L";
                        openInstall(stage, emptySide);
                        setInstallForm((current) => ({ ...current, robotId: robot.id }));
                      }}
                    >
                      <strong>{robot.code}</strong>
                      <span>{robot.name}</span>
                      <small className="mono">
                        {robot.model ?? "型号待维护"} · {used ? "已上线" : "空闲"}
                      </small>
                    </button>
                  );
                })}
              </div>
            )}
          </aside>

          <aside className="paint-line-inspector">
            {!selection ? (
              <div className="program-empty body-map-detail-empty">
                <Cable />
                选择工位或已安装机器人，查看程序版本与刷子喷涂参数。
              </div>
            ) : selection.kind === "stage" ? (
              <StageSummary
                stage={selection.stage}
                layout={layout}
                robots={robots}
                onInstall={openInstall}
                onSelectSlot={(side) => setSelection({ kind: "slot", stage: selection.stage, side })}
              />
            ) : (
              <SlotInspector
                stage={selection.stage}
                side={selection.side}
                assignment={selectedAssignment}
                robot={selectedRobot}
                atomizer={selectedAtomizer}
                program={selectedProgram}
                version={selectedVersion}
                brushes={brushes}
                parametersByBrush={parametersByBrush}
                loading={detailLoading}
                onEdit={() => openInstall(selection.stage, selection.side)}
                onUninstall={() => uninstallSlot(selection.stage, selection.side)}
              />
            )}
          </aside>
        </div>
      </div>

      {installTarget ? (
        <ModalShell
          eyebrow="工位装机"
          title={`${stageLabel(installTarget.stage)} · ${installTarget.side === "L" ? "左侧" : "右侧"}槽位`}
          description="从受控台账选择机器人与旋杯；可选绑定本工序喷涂程序版本，以便点击查看刷子设定参数。"
          onClose={() => setInstallTarget(null)}
        >
          <div className="form-grid">
            <label className="form-field">
              <span>
                机器人<b>*</b>
              </span>
              <select
                required
                value={installForm.robotId}
                onChange={(event) => setInstallForm({ ...installForm, robotId: event.target.value })}
              >
                <option value="">请选择</option>
                {availableRobotsForInstall.map((robot) => (
                  <option key={robot.id} value={robot.id}>
                    {robot.code} / {robot.name}
                    {robot.model ? ` · ${robot.model}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>旋杯 / 雾化器</span>
              <select
                value={installForm.atomizerId}
                onChange={(event) => setInstallForm({ ...installForm, atomizerId: event.target.value })}
              >
                <option value="">暂不绑定</option>
                {filteredAtomizers.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.code} / {item.name}
                    {item.bell_cup_type ? ` · ${item.bell_cup_type}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>喷涂程序（本工序）</span>
              <select
                value={installForm.programId}
                onChange={(event) => {
                  const programId = event.target.value;
                  setInstallForm({ ...installForm, programId, programVersionId: "" });
                  void ensureVersions(programId);
                }}
              >
                <option value="">暂不绑定</option>
                {programs
                  .filter((program) => program.process_stage === installTarget.stage)
                  .filter((program) => !factoryId || !program.factory_id || program.factory_id === factoryId)
                  .map((program) => (
                    <option key={program.id} value={program.id}>
                      {program.program_code} / {program.name}
                    </option>
                  ))}
              </select>
            </label>
            <label className="form-field">
              <span>程序版本</span>
              <select
                value={installForm.programVersionId}
                onChange={(event) =>
                  setInstallForm({ ...installForm, programVersionId: event.target.value })
                }
                disabled={!installForm.programId}
              >
                <option value="">暂不绑定</option>
                {installVersions
                  .filter((version) => {
                    if (!modelId || !version.vehicle_model_ids?.length) return true;
                    return version.vehicle_model_ids.includes(modelId);
                  })
                  .map((version) => (
                    <option key={version.id} value={version.id}>
                      {version.version}
                      {version.status ? ` · ${version.status}` : ""}
                    </option>
                  ))}
              </select>
            </label>
          </div>
          <div className="modal-actions">
            <button className="button button-secondary" type="button" onClick={() => setInstallTarget(null)}>
              取消
            </button>
            <button
              className="button button-primary"
              type="button"
              disabled={!installForm.robotId}
              onClick={confirmInstall}
            >
              确认安装
            </button>
          </div>
        </ModalShell>
      ) : null}
    </section>
  );
}

function RobotArmSvg({ spraying }: { spraying: boolean }) {
  return (
    <svg className={`paint-line-arm ${spraying ? "is-spraying" : ""}`} viewBox="0 0 64 80" aria-hidden="true">
      <rect x="26" y="58" width="12" height="16" rx="2" className="arm-base" />
      <path d="M32 58 L32 38 L44 28" className="arm-link" />
      <circle cx="32" cy="38" r="3.5" className="arm-joint" />
      <circle cx="44" cy="28" r="3" className="arm-joint" />
      <circle cx="50" cy="22" r="7" className="arm-bell" />
      <circle cx="50" cy="22" r="3" className="arm-bell-core" />
    </svg>
  );
}

function StageSummary({
  stage,
  layout,
  robots,
  onInstall,
  onSelectSlot,
}: {
  stage: StageCode;
  layout: LineLayout;
  robots: Robot[];
  onInstall: (stage: StageCode, side: SlotSide) => void;
  onSelectSlot: (side: SlotSide) => void;
}) {
  const meta = STAGE_META[stage];
  return (
    <div className="paint-line-inspector-body">
      <div className="body-map-detail-head">
        <div>
          <span className="eyebrow">{meta.coatingLabel}工位</span>
          <h4>{stageLabel(stage)}</h4>
          <small>{meta.stationHint}</small>
        </div>
      </div>
      <div className="paint-line-slot-summary">
        {(["L", "R"] as SlotSide[]).map((side) => {
          const assignment = layout[stage][side];
          const robot = assignment ? robots.find((item) => item.id === assignment.robotId) : null;
          return (
            <button
              key={side}
              type="button"
              className="paint-line-slot-card"
              onClick={() => (assignment ? onSelectSlot(side) : onInstall(stage, side))}
            >
              <span>{side === "L" ? "左侧槽位" : "右侧槽位"}</span>
              <strong>{robot ? robot.code : "空闲"}</strong>
              <small>{robot ? robot.name : "点击安装机器人"}</small>
            </button>
          );
        })}
      </div>
      <p className="paint-line-scope-note">
        本页仅做产线布局与参数只读仿真。设备限值、TDS 与推荐变更仍以受控主数据 / AI 闭环为准，不在此编造。
      </p>
    </div>
  );
}

function SlotInspector({
  stage,
  side,
  assignment,
  robot,
  atomizer,
  program,
  version,
  brushes,
  parametersByBrush,
  loading,
  onEdit,
  onUninstall,
}: {
  stage: StageCode;
  side: SlotSide;
  assignment: SlotAssignment | null;
  robot?: Robot | null;
  atomizer?: Atomizer | null;
  program?: SprayProgram | null;
  version?: ProgramVersion | null;
  brushes: Brush[];
  parametersByBrush: Record<string, BrushParameter[]>;
  loading: boolean;
  onEdit: () => void;
  onUninstall: () => void;
}) {
  if (!assignment || !robot) {
    return (
      <div className="program-empty">
        <Bot />
        槽位为空。
      </div>
    );
  }

  return (
    <div className="paint-line-inspector-body">
      <div className="body-map-detail-head">
        <div>
          <span className="eyebrow">
            {stageLabel(stage)} · {side === "L" ? "左侧" : "右侧"}
          </span>
          <h4>
            {robot.code} · {robot.name}
          </h4>
          <small className="mono">
            {robot.model ?? "型号待维护"} · SN {robot.serial_no ?? "—"}
          </small>
        </div>
        <div className="row-actions">
          <button className="button button-secondary" type="button" onClick={onEdit}>
            更换
          </button>
          <button className="button button-secondary" type="button" onClick={onUninstall}>
            <X />
            卸下
          </button>
        </div>
      </div>

      <div className="paint-line-meta-grid">
        <article>
          <span>旋杯</span>
          <strong>{atomizer ? atomizer.code : "未绑定"}</strong>
          <small>
            {atomizer
              ? `${atomizer.bell_cup_type ?? atomizer.model ?? "杯型待维护"}`
              : "可在装机时关联雾化器台账"}
          </small>
        </article>
        <article>
          <span>程序版本</span>
          <strong>{program ? program.program_code : "未绑定"}</strong>
          <small>
            {program && version
              ? `${program.name} · ${version.version}`
              : "绑定后可下钻刷子设定参数"}
          </small>
        </article>
      </div>

      <div className="program-subheading compact">
        <div>
          <span className="eyebrow">喷涂参数</span>
          <h4>刷子设定值（只读）</h4>
        </div>
      </div>

      {loading ? (
        <div className="program-empty">
          <LoaderCircle className="spin" />
          正在加载刷子参数…
        </div>
      ) : !assignment.programVersionId ? (
        <div className="program-empty">尚未绑定程序版本。点击「更换」关联本工序受控版本后即可查看参数。</div>
      ) : !brushes.length ? (
        <div className="program-empty">该版本下暂无刷子。请到「配方与刷子」维护刷子与参数。</div>
      ) : (
        <div className="paint-line-brush-list">
          {brushes.map((brush) => {
            const params = parametersByBrush[brush.id] ?? [];
            return (
              <div className="body-map-brush-card" key={brush.id}>
                <div className="body-map-brush-head">
                  <div className="body-map-brush-title">
                    <strong>
                      刷子 {brush.brush_no} · 表 {brush.brush_table_no}
                    </strong>
                  </div>
                </div>
                {params.length ? (
                  <div className="body-map-param-table">
                    {params.map((parameter) => (
                      <div className="body-map-param-row" key={parameter.id}>
                        <span>
                          <strong>{parameter.parameter_name}</strong>
                          <small className="mono">{parameter.parameter_code}</small>
                        </span>
                        <span className="mono">
                          <em>设定</em> {formatValue(parameter.configured_value, parameter.unit)}
                        </span>
                        <span className="mono">
                          <em>实绩</em> —
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <small className="muted">该刷子暂无配置参数</small>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
