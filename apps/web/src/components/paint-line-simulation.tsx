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
type ProductionRun = {
  id: string;
  run_no: string;
  body_no?: string | null;
  factory_id: string;
  vehicle_model_id: string;
  color_id: string;
  shift?: string | null;
  started_at: string;
};
type StageRun = {
  id: string;
  production_run_id: string;
  process_stage: string;
  program_version_id: string;
  status: string;
};
type ActualParameter = {
  id: string;
  production_stage_run_id: string;
  brush_id?: string | null;
  parameter_code: string;
  actual_value: number;
  unit: string;
};
type TrajectoryProgram = {
  id: string;
  program_version_id: string;
  trajectory_code: string;
  name: string;
  version: string;
  checksum: string;
  tcp_name?: string | null;
  status?: string;
};
type PathSegment = {
  id: string;
  trajectory_program_id: string;
  segment_no: number;
  name: string;
  brush_id?: string | null;
  configured_speed?: number | null;
  speed_unit?: string | null;
  start_position?: Record<string, unknown> | null;
  end_position?: Record<string, unknown> | null;
  trigger_state: string;
};
type DeviceExecution = {
  id: string;
  production_stage_run_id: string;
  trajectory_program_id: string;
  executed_checksum: string;
  status: string;
};
type SegmentExecution = {
  id: string;
  device_execution_id: string;
  path_segment_id: string;
  actual_speed?: number | null;
  speed_unit?: string | null;
  trigger_state?: string | null;
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

type Point2D = { x: number; y: number };

type NormalizedSegment = {
  segment: PathSegment;
  start: Point2D;
  end: Point2D;
  placeholder: boolean;
};

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
const PATH_VIEW_W = 320;
const PATH_VIEW_H = 180;
const PATH_PAD = 16;

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

function formatDelta(delta: number | null): string {
  if (delta == null || Number.isNaN(delta)) return "—";
  const sign = delta > 0 ? "+" : "";
  const text = Number.isInteger(delta) ? String(delta) : delta.toFixed(2);
  return `${sign}${text}`;
}

function matchesContextId(recordId?: string | null, contextId?: string): boolean {
  if (!contextId) return true;
  if (!recordId) return true;
  return recordId === contextId;
}

function extractPoint(position?: Record<string, unknown> | null): Point2D | null {
  if (!position || typeof position !== "object") return null;
  const x = Number(position.x);
  const yRaw = position.y != null ? Number(position.y) : Number(position.z);
  if (!Number.isFinite(x) || !Number.isFinite(yRaw)) return null;
  return { x, y: yRaw };
}

function synthesizeZigzag(index: number): { start: Point2D; end: Point2D } {
  const row = Math.floor(index / 2);
  const goingRight = index % 2 === 0;
  const y = row * 40;
  return goingRight
    ? { start: { x: 0, y }, end: { x: 100, y } }
    : { start: { x: 100, y }, end: { x: 0, y: y + 40 } };
}

function normalizeSegments(segments: PathSegment[]): NormalizedSegment[] {
  const sorted = [...segments].sort((a, b) => a.segment_no - b.segment_no);
  return sorted.map((segment, index) => {
    const start = extractPoint(segment.start_position);
    const end = extractPoint(segment.end_position);
    if (start && end) {
      return { segment, start, end, placeholder: false };
    }
    const zigzag = synthesizeZigzag(index);
    return {
      segment,
      start: start ?? zigzag.start,
      end: end ?? zigzag.end,
      placeholder: true,
    };
  });
}

function buildPolyline(normalized: NormalizedSegment[]): Point2D[] {
  if (!normalized.length) return [];
  const points: Point2D[] = [normalized[0].start];
  for (const item of normalized) {
    const last = points[points.length - 1];
    if (last.x !== item.start.x || last.y !== item.start.y) {
      points.push(item.start);
    }
    points.push(item.end);
  }
  return points;
}

function polylineLength(points: Point2D[]): number {
  let total = 0;
  for (let i = 1; i < points.length; i += 1) {
    const dx = points[i].x - points[i - 1].x;
    const dy = points[i].y - points[i - 1].y;
    total += Math.hypot(dx, dy);
  }
  return total;
}

function pointAlongPolyline(points: Point2D[], t: number): Point2D | null {
  if (!points.length) return null;
  if (points.length === 1) return points[0];
  const total = polylineLength(points);
  if (total <= 0) return points[0];
  let remaining = Math.max(0, Math.min(1, t)) * total;
  for (let i = 1; i < points.length; i += 1) {
    const a = points[i - 1];
    const b = points[i];
    const segLen = Math.hypot(b.x - a.x, b.y - a.y);
    if (remaining <= segLen || i === points.length - 1) {
      const ratio = segLen > 0 ? remaining / segLen : 0;
      return { x: a.x + (b.x - a.x) * ratio, y: a.y + (b.y - a.y) * ratio };
    }
    remaining -= segLen;
  }
  return points[points.length - 1];
}

function activeSegmentAt(normalized: NormalizedSegment[], t: number): NormalizedSegment | null {
  if (!normalized.length) return null;
  const points = buildPolyline(normalized);
  const total = polylineLength(points);
  if (total <= 0) return normalized[0];
  const target = Math.max(0, Math.min(1, t)) * total;
  let walked = 0;
  for (const item of normalized) {
    const segLen = Math.hypot(item.end.x - item.start.x, item.end.y - item.start.y);
    if (target <= walked + segLen || item === normalized[normalized.length - 1]) {
      return item;
    }
    walked += segLen;
  }
  return normalized[normalized.length - 1];
}

function projectPoints(points: Point2D[]): { projected: Point2D[]; width: number; height: number } {
  if (!points.length) {
    return { projected: [], width: PATH_VIEW_W, height: PATH_VIEW_H };
  }
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = Math.max(1e-6, maxX - minX);
  const spanY = Math.max(1e-6, maxY - minY);
  const innerW = PATH_VIEW_W - PATH_PAD * 2;
  const innerH = PATH_VIEW_H - PATH_PAD * 2;
  const scale = Math.min(innerW / spanX, innerH / spanY);
  const offsetX = PATH_PAD + (innerW - spanX * scale) / 2;
  const offsetY = PATH_PAD + (innerH - spanY * scale) / 2;
  return {
    projected: points.map((p) => ({
      x: offsetX + (p.x - minX) * scale,
      y: offsetY + (p.y - minY) * scale,
    })),
    width: PATH_VIEW_W,
    height: PATH_VIEW_H,
  };
}

function findActualParameter(
  actuals: ActualParameter[],
  brushId: string,
  parameterCode: string,
): ActualParameter | undefined {
  return (
    actuals.find((item) => item.brush_id === brushId && item.parameter_code === parameterCode) ??
    actuals.find((item) => item.parameter_code === parameterCode)
  );
}

export function PaintLineSimulation() {
  const { factoryId, modelId, colorId, stage: contextStage } = useWorkspaceContext();
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
  const [productionRuns, setProductionRuns] = useState<ProductionRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [stageRuns, setStageRuns] = useState<StageRun[]>([]);
  const [actualParameters, setActualParameters] = useState<ActualParameter[]>([]);
  const [trajectoryProgram, setTrajectoryProgram] = useState<TrajectoryProgram | null>(null);
  const [pathSegments, setPathSegments] = useState<PathSegment[]>([]);
  const [deviceExecution, setDeviceExecution] = useState<DeviceExecution | null>(null);
  const [segmentExecutions, setSegmentExecutions] = useState<SegmentExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [pathLoading, setPathLoading] = useState(false);
  const [actualLoading, setActualLoading] = useState(false);
  const [error, setError] = useState("");
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const [pathPlaying, setPathPlaying] = useState(false);
  const [pathProgress, setPathProgress] = useState(0);
  const rafRef = useRef<number | null>(null);
  const lastTsRef = useRef<number | null>(null);
  const pathRafRef = useRef<number | null>(null);
  const pathLastTsRef = useRef<number | null>(null);

  const filteredRobots = useMemo(
    () => robots.filter((item) => !factoryId || item.factory_id === factoryId),
    [robots, factoryId],
  );
  const filteredAtomizers = useMemo(
    () => atomizers.filter((item) => !factoryId || item.factory_id === factoryId),
    [atomizers, factoryId],
  );

  const filteredRuns = useMemo(
    () =>
      productionRuns.filter(
        (run) =>
          matchesContextId(run.factory_id, factoryId) &&
          matchesContextId(run.vehicle_model_id, modelId) &&
          matchesContextId(run.color_id, colorId),
      ),
    [productionRuns, factoryId, modelId, colorId],
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

  const matchedStageRun = useMemo(() => {
    if (!selectedStage || !selectedRunId) return null;
    return stageRuns.find((item) => item.process_stage === selectedStage) ?? null;
  }, [stageRuns, selectedStage, selectedRunId]);

  const normalizedPath = useMemo(() => normalizeSegments(pathSegments), [pathSegments]);
  const pathUsesPlaceholder = useMemo(
    () => normalizedPath.some((item) => item.placeholder),
    [normalizedPath],
  );
  const activePathSegment = useMemo(
    () => activeSegmentAt(normalizedPath, pathProgress),
    [normalizedPath, pathProgress],
  );
  const activeSegmentExecution = useMemo(() => {
    if (!activePathSegment) return null;
    return segmentExecutions.find((item) => item.path_segment_id === activePathSegment.segment.id) ?? null;
  }, [activePathSegment, segmentExecutions]);

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextRobots, nextAtomizers, nextPrograms, nextRuns] = await Promise.all([
        request<Robot[]>("/api/process/robot-governance/robots"),
        request<Atomizer[]>("/api/process/robot-governance/atomizers"),
        request<SprayProgram[]>("/api/process/spray-programs"),
        request<ProductionRun[]>("/api/process/production-runs?limit=500"),
      ]);
      setRobots(nextRobots);
      setAtomizers(nextAtomizers);
      setPrograms(nextPrograms);
      setProductionRuns(nextRuns);
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
    if (selectedRunId && !filteredRuns.some((run) => run.id === selectedRunId)) {
      setSelectedRunId("");
    }
  }, [filteredRuns, selectedRunId]);

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

  useEffect(() => {
    if (!pathPlaying || !normalizedPath.length) {
      if (pathRafRef.current != null) cancelAnimationFrame(pathRafRef.current);
      pathRafRef.current = null;
      pathLastTsRef.current = null;
      return;
    }
    const tick = (ts: number) => {
      if (pathLastTsRef.current == null) pathLastTsRef.current = ts;
      const delta = (ts - pathLastTsRef.current) / 1000;
      pathLastTsRef.current = ts;
      setPathProgress((current) => {
        const next = current + delta * 0.22;
        if (next >= 1) {
          setPathPlaying(false);
          return 1;
        }
        return next;
      });
      pathRafRef.current = requestAnimationFrame(tick);
    };
    pathRafRef.current = requestAnimationFrame(tick);
    return () => {
      if (pathRafRef.current != null) cancelAnimationFrame(pathRafRef.current);
    };
  }, [pathPlaying, normalizedPath.length]);

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

  const loadTrajectory = useCallback(async (programVersionId?: string) => {
    setTrajectoryProgram(null);
    setPathSegments([]);
    setPathProgress(0);
    setPathPlaying(false);
    if (!programVersionId) return;
    setPathLoading(true);
    try {
      const programsList = await request<TrajectoryProgram[]>(
        `/api/process/robot-governance/trajectory-programs?program_version_id=${encodeURIComponent(programVersionId)}`,
      );
      const preferred =
        programsList.find((item) => item.status === "ACTIVE") ??
        programsList.find((item) => item.status === "APPROVED") ??
        programsList[0] ??
        null;
      setTrajectoryProgram(preferred);
      if (!preferred) return;
      const segments = await request<PathSegment[]>(
        `/api/process/robot-governance/path-segments?trajectory_program_id=${encodeURIComponent(preferred.id)}`,
      );
      setPathSegments(segments);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载轨迹路径失败");
    } finally {
      setPathLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTrajectory(selectedAssignment?.programVersionId);
  }, [selectedAssignment?.programVersionId, loadTrajectory]);

  useEffect(() => {
    if (!selectedRunId) {
      setStageRuns([]);
      setActualParameters([]);
      setDeviceExecution(null);
      setSegmentExecutions([]);
      return;
    }
    let cancelled = false;
    (async () => {
      setActualLoading(true);
      try {
        const stages = await request<StageRun[]>(`/api/process/production-runs/${selectedRunId}/stages`);
        if (cancelled) return;
        setStageRuns(stages);
      } catch (err) {
        if (!cancelled) {
          setStageRuns([]);
          setError(err instanceof Error ? err.message : "加载生产工序实绩失败");
        }
      } finally {
        if (!cancelled) setActualLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedRunId]);

  useEffect(() => {
    setActualParameters([]);
    setDeviceExecution(null);
    setSegmentExecutions([]);
    if (!matchedStageRun) return;
    let cancelled = false;
    (async () => {
      setActualLoading(true);
      try {
        const [actuals, executions] = await Promise.all([
          request<ActualParameter[]>(
            `/api/process/production-stage-runs/${matchedStageRun.id}/actual-parameters`,
          ),
          request<DeviceExecution[]>(
            `/api/process/robot-governance/device-executions?production_stage_run_id=${encodeURIComponent(matchedStageRun.id)}`,
          ),
        ]);
        if (cancelled) return;
        setActualParameters(actuals);
        const execution = executions[0] ?? null;
        setDeviceExecution(execution);
        if (execution) {
          const segs = await request<SegmentExecution[]>(
            `/api/process/robot-governance/device-executions/${execution.id}/segments`,
          );
          if (!cancelled) setSegmentExecutions(segs);
        } else {
          setSegmentExecutions([]);
        }
      } catch (err) {
        if (!cancelled) {
          setActualParameters([]);
          setDeviceExecution(null);
          setSegmentExecutions([]);
          setError(err instanceof Error ? err.message : "加载实绩参数失败");
        }
      } finally {
        if (!cancelled) setActualLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [matchedStageRun]);

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
    setPathPlaying(false);
    setPathProgress(0);
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

  const showBoothPathOverlay =
    selection?.kind === "slot" && Boolean(selectedAssignment?.programVersionId) && normalizedPath.length > 0;

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
        <div className="row-actions paint-line-toolbar">
          <label className="paint-line-run-select">
            <span>生产事件</span>
            <select
              value={selectedRunId}
              onChange={(event) => setSelectedRunId(event.target.value)}
              disabled={loading}
            >
              <option value="">未选择（仅看设定）</option>
              {filteredRuns.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.run_no}
                  {run.body_no ? ` · ${run.body_no}` : ""}
                </option>
              ))}
            </select>
          </label>
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

        <div className="paint-line-stage is-3d">
          <div className="paint-line-scene">
            <div className="paint-line-sky" aria-hidden="true" />
            <div className="paint-line-ceiling" aria-hidden="true" />

            <div className="paint-line-conveyor-plane" aria-hidden="true">
              <div className="paint-line-conveyor">
                <i />
                <i />
                <i />
              </div>
              <div
                className={`paint-line-body ${playing ? "is-moving" : ""}`}
                style={{ left: bodyLeft }}
              >
                <div className="paint-line-skid" />
                <div className="paint-line-biw">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            </div>

            <div className="paint-line-booths">
              {STAGE_ORDER.map((stage, index) => {
                const meta = STAGE_META[stage];
                const isActive = activeStageIndex === index && (playing || progress > 0);
                const isSelected = selectedStage === stage;
                const showOverlay =
                  showBoothPathOverlay &&
                  selection?.kind === "slot" &&
                  selection.stage === stage;
                return (
                  <article
                    key={stage}
                    className={`paint-line-booth ${isActive ? "is-active" : ""} ${isSelected ? "is-selected" : ""}`}
                    style={{ "--booth-tone": meta.tone } as CSSProperties}
                    onClick={() => setSelection({ kind: "stage", stage })}
                  >
                    <div className="paint-line-booth-3d">
                      <div className="paint-line-booth-back" aria-hidden="true" />
                      <div className="paint-line-booth-side is-left" aria-hidden="true" />
                      <div className="paint-line-booth-side is-right" aria-hidden="true" />
                      <div className="paint-line-booth-floor" aria-hidden="true" />
                      <div className="paint-line-booth-face">
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
                          {showOverlay ? (
                            <div className="paint-line-booth-path-overlay" aria-hidden="true">
                              <TrajectoryPathCanvas
                                normalized={normalizedPath}
                                progress={pathProgress}
                                compact
                              />
                            </div>
                          ) : null}
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
                                  selection?.kind === "slot" &&
                                  selection.stage === stage &&
                                  selection.side === side
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
                                title={
                                  robot
                                    ? `${robot.code} / ${robot.name}`
                                    : `安装${side === "L" ? "左侧" : "右侧"}机器人`
                                }
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
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
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
            {selectedRunId
              ? ` · 对照生产事件 ${filteredRuns.find((run) => run.id === selectedRunId)?.run_no ?? selectedRunId}`
              : ""}
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
                matchedStageRun={matchedStageRun}
                actualLoading={actualLoading}
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
                actualParameters={actualParameters}
                loading={detailLoading}
                actualLoading={actualLoading}
                hasProductionRun={Boolean(selectedRunId)}
                matchedStageRun={matchedStageRun}
                deviceExecution={deviceExecution}
                trajectoryProgram={trajectoryProgram}
                pathLoading={pathLoading}
                normalizedPath={normalizedPath}
                pathUsesPlaceholder={pathUsesPlaceholder}
                pathProgress={pathProgress}
                pathPlaying={pathPlaying}
                activePathSegment={activePathSegment}
                activeSegmentExecution={activeSegmentExecution}
                onTogglePathPlay={() => {
                  if (!normalizedPath.length) return;
                  if (pathProgress >= 1) setPathProgress(0);
                  setPathPlaying((value) => !value);
                }}
                onResetPath={() => {
                  setPathPlaying(false);
                  setPathProgress(0);
                }}
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

function projectWorldPoint(points: Point2D[], point: Point2D): Point2D | null {
  if (!points.length) return null;
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = Math.max(1e-6, maxX - minX);
  const spanY = Math.max(1e-6, maxY - minY);
  const innerW = PATH_VIEW_W - PATH_PAD * 2;
  const innerH = PATH_VIEW_H - PATH_PAD * 2;
  const scale = Math.min(innerW / spanX, innerH / spanY);
  const offsetX = PATH_PAD + (innerW - spanX * scale) / 2;
  const offsetY = PATH_PAD + (innerH - spanY * scale) / 2;
  return {
    x: offsetX + (point.x - minX) * scale,
    y: offsetY + (point.y - minY) * scale,
  };
}

function TrajectoryPathCanvas({
  normalized,
  progress,
  compact = false,
}: {
  normalized: NormalizedSegment[];
  progress: number;
  compact?: boolean;
}) {
  const points = useMemo(() => buildPolyline(normalized), [normalized]);
  const { projected, width, height } = useMemo(() => projectPoints(points), [points]);
  const marker = useMemo(() => {
    const raw = pointAlongPolyline(points, progress);
    if (!raw) return null;
    return projectWorldPoint(points, raw);
  }, [points, progress]);

  if (!projected.length) {
    return <div className="paint-line-path-empty">暂无路径段坐标</div>;
  }

  const d = projected
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
    .join(" ");

  return (
    <svg
      className={`paint-line-path-svg ${compact ? "is-compact" : ""}`}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="轨迹路径"
    >
      <path d={d} className="paint-line-path-line" />
      {marker ? (
        <circle cx={marker.x} cy={marker.y} r={compact ? 3.5 : 5} className="paint-line-path-tcp" />
      ) : null}
    </svg>
  );
}

function StageSummary({
  stage,
  layout,
  robots,
  matchedStageRun,
  actualLoading,
  onInstall,
  onSelectSlot,
}: {
  stage: StageCode;
  layout: LineLayout;
  robots: Robot[];
  matchedStageRun: StageRun | null;
  actualLoading: boolean;
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
        {actualLoading
          ? "正在加载工序实绩…"
          : matchedStageRun
            ? `已匹配生产工序实绩（${matchedStageRun.status}）。选择槽位可对照刷子设定与实绩。`
            : "本页仅做产线布局与参数只读仿真。选择生产事件后，可在槽位中对照设定与实绩；设备限值、TDS 与推荐变更仍以受控主数据 / AI 闭环为准，不在此编造。"}
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
  actualParameters,
  loading,
  actualLoading,
  hasProductionRun,
  matchedStageRun,
  deviceExecution,
  trajectoryProgram,
  pathLoading,
  normalizedPath,
  pathUsesPlaceholder,
  pathProgress,
  pathPlaying,
  activePathSegment,
  activeSegmentExecution,
  onTogglePathPlay,
  onResetPath,
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
  actualParameters: ActualParameter[];
  loading: boolean;
  actualLoading: boolean;
  hasProductionRun: boolean;
  matchedStageRun: StageRun | null;
  deviceExecution: DeviceExecution | null;
  trajectoryProgram: TrajectoryProgram | null;
  pathLoading: boolean;
  normalizedPath: NormalizedSegment[];
  pathUsesPlaceholder: boolean;
  pathProgress: number;
  pathPlaying: boolean;
  activePathSegment: NormalizedSegment | null;
  activeSegmentExecution: SegmentExecution | null;
  onTogglePathPlay: () => void;
  onResetPath: () => void;
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

  const checksumMismatch = deviceExecution?.status === "CHECKSUM_MISMATCH";

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
          {checksumMismatch ? (
            <span className="status-badge status-danger">CHECKSUM_MISMATCH</span>
          ) : null}
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

      {assignment.programVersionId ? (
        <div className="paint-line-path-panel">
          <div className="program-subheading compact">
            <div>
              <span className="eyebrow">轨迹回放</span>
              <h4>{trajectoryProgram ? trajectoryProgram.name : "路径段"}</h4>
            </div>
            <div className="row-actions">
              <button
                className="button button-secondary"
                type="button"
                disabled={!normalizedPath.length || pathLoading}
                onClick={onResetPath}
              >
                复位
              </button>
              <button
                className={`button ${pathPlaying ? "button-secondary" : "button-primary"}`}
                type="button"
                disabled={!normalizedPath.length || pathLoading}
                onClick={onTogglePathPlay}
              >
                {pathPlaying ? <Pause /> : <Play />}
                {pathPlaying ? "暂停路径" : "播放路径"}
              </button>
            </div>
          </div>

          {pathLoading ? (
            <div className="program-empty">
              <LoaderCircle className="spin" />
              正在加载轨迹…
            </div>
          ) : !trajectoryProgram ? (
            <div className="program-empty">该程序版本暂无轨迹程序。请到「机器人与轨迹」维护。</div>
          ) : !normalizedPath.length ? (
            <div className="program-empty">轨迹程序下暂无路径段。</div>
          ) : (
            <>
              {pathUsesPlaceholder ? (
                <p className="paint-line-path-note">几何占位，非实测坐标</p>
              ) : null}
              <TrajectoryPathCanvas normalized={normalizedPath} progress={pathProgress} />
              <div className="paint-line-path-status">
                <div>
                  <span>当前段</span>
                  <strong>{activePathSegment?.segment.name ?? "—"}</strong>
                </div>
                <div>
                  <span>设定速度</span>
                  <strong className="mono">
                    {formatValue(
                      activePathSegment?.segment.configured_speed,
                      activePathSegment?.segment.speed_unit,
                    )}
                  </strong>
                </div>
                <div>
                  <span>触发</span>
                  <strong className="mono">{activePathSegment?.segment.trigger_state ?? "—"}</strong>
                </div>
                <div>
                  <span>实绩速度</span>
                  <strong className="mono">
                    {activeSegmentExecution
                      ? formatValue(
                          activeSegmentExecution.actual_speed,
                          activeSegmentExecution.speed_unit ??
                            activePathSegment?.segment.speed_unit,
                        )
                      : "—"}
                  </strong>
                </div>
              </div>
              {trajectoryProgram.tcp_name ? (
                <small className="muted mono">TCP · {trajectoryProgram.tcp_name}</small>
              ) : null}
            </>
          )}
        </div>
      ) : null}

      <div className="program-subheading compact">
        <div>
          <span className="eyebrow">喷涂参数</span>
          <h4>刷子设定 / 实绩对照</h4>
        </div>
        {hasProductionRun && !matchedStageRun && !actualLoading ? (
          <small className="muted">本工序无实绩</small>
        ) : null}
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
                  <div className="body-map-param-table paint-line-param-table">
                    {params.map((parameter) => {
                      const actual = findActualParameter(
                        actualParameters,
                        brush.id,
                        parameter.parameter_code,
                      );
                      const actualValue = actual?.actual_value ?? null;
                      const delta =
                        actualValue != null && parameter.configured_value != null
                          ? actualValue - parameter.configured_value
                          : null;
                      const hasDelta = delta != null && Math.abs(delta) > 0;
                      return (
                        <div className="body-map-param-row paint-line-param-row" key={parameter.id}>
                          <span>
                            <strong>{parameter.parameter_name}</strong>
                            <small className="mono">{parameter.parameter_code}</small>
                          </span>
                          <span className="mono">
                            <em>设定</em> {formatValue(parameter.configured_value, parameter.unit)}
                          </span>
                          <span className="mono">
                            <em>实绩</em>{" "}
                            {actualLoading && hasProductionRun
                              ? "…"
                              : formatValue(actualValue, actual?.unit ?? parameter.unit)}
                          </span>
                          <span className={`mono paint-line-delta ${hasDelta ? "has-delta" : ""}`}>
                            <em>Δ</em> {formatDelta(delta)}
                          </span>
                        </div>
                      );
                    })}
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
