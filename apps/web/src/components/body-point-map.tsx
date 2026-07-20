"use client";

import { Image as ImageIcon, Layers, Link2, ListTree, LoaderCircle, MapPinned, Pencil, Plus, RefreshCw, X } from "lucide-react";
import {
  FormEvent,
  PointerEvent as ReactPointerEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";

import Link from "next/link";
import Image from "next/image";

import { BodyMapImageEditor } from "@/components/body-map-image-editor";
import { ModalShell } from "@/components/modal-shell";
import { PointAiActions } from "@/components/point-ai-actions";
import { PointParameterVersionEditor } from "@/components/point-parameter-version-editor";
import { DEFAULT_BODY_MAP_IMAGES } from "@/lib/body-map-images";
import { stageLabel } from "@/lib/display-labels";
import { useWorkspaceContext } from "@/lib/workspace-context";

type BodyView = "RIGHT" | "LEFT" | "TOP" | "REAR";
type SideTab = "governance" | "detail";

type Resource = { id: string; code: string; name: string; vehicle_model_id?: string; quality_type?: string };

type MeasurementGroup = Resource & {
  vehicle_model_id: string;
  quality_type: string;
  expected_point_count?: number | null;
  remark?: string | null;
};

type MeasurementPoint = Resource & {
  vehicle_model_id: string;
  part_id: string;
  region?: string | null;
  quality_types: string[];
  point_type?: string;
};

type GroupPointRelation = {
  id: string;
  measurement_group_id: string;
  measurement_point_id: string;
  sequence_no: number;
};

type ProductionRun = {
  id: string;
  run_no: string;
  body_no?: string | null;
  vehicle_model_id?: string;
  factory_id?: string;
  color_id?: string;
};

type QualitySummary = {
  quality_type: string;
  metric_code?: string | null;
  metric_name?: string | null;
  value?: number | null;
  unit?: string | null;
  measured_at?: string | null;
  data_no?: string | null;
  judgement?: string | null;
  reliability_status?: string | null;
};

type MapPoint = {
  measurement_point_id: string;
  layout_id?: string | null;
  code: string;
  name: string;
  part_id: string;
  part_code?: string | null;
  part_name?: string | null;
  region?: string | null;
  quality_types: string[];
  layout_x?: number | null;
  layout_y?: number | null;
  grid_col?: number | null;
  grid_row?: number | null;
  in_group: boolean;
  quality_summaries: QualitySummary[];
  risk_score: number;
};

type BodyMapPayload = {
  vehicle_model_id: string;
  vehicle_model_code: string;
  vehicle_model_name: string;
  body_view: string;
  background_image_url: string;
  grid_cols: number;
  grid_rows: number;
  measurement_group_id?: string | null;
  production_run_id?: string | null;
  production_run_no?: string | null;
  quality_scope?: string;
  placed_count?: number;
  group_point_count?: number;
  fail_count?: number;
  points: MapPoint[];
};

type CanvasPayload = {
  vehicle_model_id: string;
  vehicle_model_code: string;
  vehicle_model_name: string;
  view_order: string[];
  view_labels: Record<string, string>;
  grid_cols: number;
  grid_rows: number;
  measurement_group_id?: string | null;
  production_run_id?: string | null;
  production_run_no?: string | null;
  quality_scope?: string;
  placed_count: number;
  group_point_count: number;
  fail_count: number;
  views: BodyMapPayload[];
};

type BrushParameter = {
  parameter_code: string;
  parameter_name: string;
  configured_value?: number | null;
  actual_value?: number | null;
  unit: string;
  soft_min?: number | null;
  soft_max?: number | null;
  hard_min?: number | null;
  hard_max?: number | null;
};

type BrushContribution = {
  brush_id: string;
  brush_no: string;
  brush_table_no: string;
  program_version_id?: string | null;
  program_version?: string | null;
  program_code?: string | null;
  program_name?: string | null;
  process_stage: string;
  coating_system: string;
  overlap_ratio: number;
  contribution_weight: number;
  source: string;
  version: string;
  is_approved: boolean;
  contribution_source?: string;
  target_family?: string | null;
  validation_score?: number | null;
  parameters: BrushParameter[];
};

type PointDetail = {
  measurement_point_id: string;
  code: string;
  name: string;
  part_id: string;
  part_code?: string | null;
  part_name?: string | null;
  region?: string | null;
  quality_types: string[];
  quality_summaries: QualitySummary[];
  brush_contributions: BrushContribution[];
};

type CreateDraft = {
  body_view: BodyView;
  layout_x: number;
  layout_y: number;
  grid_col: number;
  grid_row: number;
};

type LayoutRead = {
  id: string;
  measurement_point_id: string;
  body_view: string;
  layout_x: number;
  layout_y: number;
  grid_col?: number | null;
  grid_row?: number | null;
  status: string;
};

type OverlayMode = "RISK" | "THICKNESS" | "COLOR_DIFFERENCE" | "ORANGE_PEEL";

type GroupForm = {
  code: string;
  name: string;
  quality_type: string;
  expected_point_count: string;
  remark: string;
};

type PointForm = {
  code: string;
  name: string;
  part_id: string;
  region: string;
  quality_types: string[];
  bind_to_group: boolean;
};

const BODY_VIEWS: BodyView[] = ["RIGHT", "LEFT", "TOP", "REAR"];

const DEFAULT_VIEW_LABELS: Record<BodyView, string> = {
  RIGHT: "右侧视图",
  LEFT: "左侧视图",
  TOP: "俯视图",
  REAR: "后视图",
};

const DEFAULT_VIEW_IMAGES = DEFAULT_BODY_MAP_IMAGES;

const qualityLabels: Record<string, string> = {
  THICKNESS: "膜厚",
  COLOR_DIFFERENCE: "色差",
  ORANGE_PEEL: "橘皮",
};

const QUALITY_TYPE_OPTIONS = ["THICKNESS", "COLOR_DIFFERENCE", "ORANGE_PEEL"] as const;

const coatingLabels: Record<string, string> = {
  MIDCOAT: "中涂",
  BASECOAT: "色漆",
  CLEARCOAT: "清漆",
  UNKNOWN: "未归类",
};

const judgementLabels: Record<string, string> = {
  PASS: "合格",
  FAIL: "超差",
  NO_STANDARD: "无标准",
  INVALID: "无效",
};

const reliabilityLabels: Record<string, string> = {
  VERIFIED: "已核验",
  UNVERIFIED: "未核验",
  FAILED: "核验失败",
};

const emptyGroupForm = (): GroupForm => ({
  code: "",
  name: "",
  quality_type: "THICKNESS",
  expected_point_count: "",
  remark: "",
});

const emptyPointForm = (): PointForm => ({
  code: "",
  name: "",
  part_id: "",
  region: "",
  quality_types: ["THICKNESS", "COLOR_DIFFERENCE", "ORANGE_PEEL"],
  bind_to_group: true,
});

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  if (response.status === 204) return undefined as T;
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

function riskColor(score: number, judgement?: string | null): string {
  if (judgement === "FAIL" || score >= 40) return "var(--red)";
  if (judgement === "INVALID" || score >= 25) return "var(--amber)";
  if (judgement === "NO_STANDARD" || score >= 10) return "var(--amber)";
  if (judgement === "PASS") return "var(--teal)";
  return "var(--text-soft)";
}

function pointColor(point: MapPoint, overlay: OverlayMode): string {
  if (overlay === "RISK") {
    const primary =
      point.quality_summaries.find((item) => item.judgement === "FAIL") ??
      point.quality_summaries.find((item) => item.judgement === "PASS") ??
      point.quality_summaries.find((item) => item.value != null) ??
      point.quality_summaries[0];
    return riskColor(point.risk_score, primary?.judgement);
  }
  const summary = point.quality_summaries.find((item) => item.quality_type === overlay);
  if (!summary) return "var(--text-soft)";
  if (summary.judgement === "FAIL") return "var(--red)";
  if (summary.judgement === "INVALID") return "var(--amber)";
  if (summary.judgement === "PASS") return "var(--teal)";
  if (summary.judgement === "NO_STANDARD") return "var(--amber)";
  return "var(--text-soft)";
}

function snapCoords(
  x: number,
  y: number,
  gridCols: number,
  gridRows: number,
): { x: number; y: number; col: number; row: number } {
  const col = Math.min(gridCols - 1, Math.max(0, Math.floor(x * gridCols)));
  const row = Math.min(gridRows - 1, Math.max(0, Math.floor(y * gridRows)));
  return {
    col,
    row,
    x: (col + 0.5) / gridCols,
    y: (row + 0.5) / gridRows,
  };
}

function isBodyView(value: string): value is BodyView {
  return BODY_VIEWS.includes(value as BodyView);
}

function viewLabel(view: BodyView, labels?: Record<string, string> | null): string {
  return labels?.[view] ?? DEFAULT_VIEW_LABELS[view];
}

export function BodyPointMap() {
  const { modelId, factoryId, colorId } = useWorkspaceContext();
  const [models, setModels] = useState<Resource[]>([]);
  const [parts, setParts] = useState<Resource[]>([]);
  const [groups, setGroups] = useState<MeasurementGroup[]>([]);
  const [masterPoints, setMasterPoints] = useState<MeasurementPoint[]>([]);
  const [groupPointRelations, setGroupPointRelations] = useState<GroupPointRelation[]>([]);
  const [runs, setRuns] = useState<ProductionRun[]>([]);
  const [vehicleModelId, setVehicleModelId] = useState(modelId || "");
  const [activeView, setActiveView] = useState<BodyView>("RIGHT");
  const [groupId, setGroupId] = useState("");
  const [runId, setRunId] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [imageEditorOpen, setImageEditorOpen] = useState(false);
  const [imageRevision, setImageRevision] = useState(0);
  const [showUngrouped, setShowUngrouped] = useState(true);
  const [overlayMode, setOverlayMode] = useState<OverlayMode>("RISK");
  const [canvas, setCanvas] = useState<CanvasPayload | null>(null);
  const [detail, setDetail] = useState<PointDetail | null>(null);
  const [selectedPointId, setSelectedPointId] = useState("");
  const [pendingPlaceId, setPendingPlaceId] = useState("");
  const [sideTab, setSideTab] = useState<SideTab>("detail");
  const [sideTabPinned, setSideTabPinned] = useState(false);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [createDraft, setCreateDraft] = useState<CreateDraft | null>(null);
  const [createForm, setCreateForm] = useState({
    code: "",
    name: "",
    part_id: "",
    region: "",
    quality_types: ["THICKNESS", "COLOR_DIFFERENCE", "ORANGE_PEEL"] as string[],
  });
  const [groupModal, setGroupModal] = useState<"create" | "edit" | null>(null);
  const [groupForm, setGroupForm] = useState<GroupForm>(emptyGroupForm);
  const [editingGroupId, setEditingGroupId] = useState("");
  const [pointModal, setPointModal] = useState<"create" | "edit" | null>(null);
  const [pointForm, setPointForm] = useState<PointForm>(emptyPointForm);
  const [editingPointId, setEditingPointId] = useState("");
  const [selectedGovPointId, setSelectedGovPointId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const stageRefs = useRef<Partial<Record<BodyView, HTMLDivElement | null>>>({});
  const dragRef = useRef<{
    pointId: string;
    pointerId: number;
    moved: boolean;
    view: BodyView;
  } | null>(null);
  const paneRefs = useRef<Partial<Record<BodyView, HTMLElement | null>>>({});
  const canvasRequestIdRef = useRef(0);
  const detailRequestIdRef = useRef(0);

  const closeCreateModal = useCallback(() => {
    if (submitting) return;
    setCreateDraft(null);
  }, [submitting]);

  const closeGroupModal = useCallback(() => {
    if (submitting) return;
    setGroupModal(null);
    setEditingGroupId("");
  }, [submitting]);

  const closePointModal = useCallback(() => {
    if (submitting) return;
    setPointModal(null);
    setEditingPointId("");
  }, [submitting]);

  const gridCols = canvas?.grid_cols ?? 48;
  const gridRows = canvas?.grid_rows ?? 24;
  const viewOrder = useMemo(() => {
    const fromApi = (canvas?.view_order ?? []).filter(isBodyView);
    return fromApi.length ? fromApi : BODY_VIEWS;
  }, [canvas?.view_order]);
  const viewLabels = canvas?.view_labels ?? DEFAULT_VIEW_LABELS;

  const viewsByKey = useMemo(() => {
    const map = new Map<BodyView, BodyMapPayload>();
    for (const view of canvas?.views ?? []) {
      if (isBodyView(view.body_view)) map.set(view.body_view, view);
    }
    return map;
  }, [canvas]);

  const activeViewData = viewsByKey.get(activeView) ?? null;

  const filteredGroups = useMemo(
    () => groups.filter((item) => !vehicleModelId || item.vehicle_model_id === vehicleModelId),
    [groups, vehicleModelId],
  );

  const filteredMasterPoints = useMemo(
    () => masterPoints.filter((item) => !vehicleModelId || item.vehicle_model_id === vehicleModelId),
    [masterPoints, vehicleModelId],
  );

  const filteredRuns = useMemo(
    () =>
      runs.filter(
        (item) =>
          (!vehicleModelId || item.vehicle_model_id === vehicleModelId) &&
          (!factoryId || !item.factory_id || item.factory_id === factoryId) &&
          (!colorId || !item.color_id || item.color_id === colorId),
      ),
    [runs, vehicleModelId, factoryId, colorId],
  );

  const boundPointIds = useMemo(() => {
    if (!groupId) return new Set<string>();
    return new Set(
      groupPointRelations
        .filter((item) => item.measurement_group_id === groupId)
        .map((item) => item.measurement_point_id),
    );
  }, [groupPointRelations, groupId]);

  const visiblePointsForView = useCallback(
    (view: BodyView) => {
      const payload = viewsByKey.get(view);
      const points = payload?.points ?? [];
      return points.filter((point) => {
        if (point.layout_x == null || point.layout_y == null) return false;
        if (groupId && !point.in_group && !showUngrouped) return false;
        return true;
      });
    },
    [viewsByKey, groupId, showUngrouped],
  );

  const unplaced = useMemo(() => {
    const points = activeViewData?.points ?? [];
    return points.filter((point) => point.layout_x == null || point.layout_y == null);
  }, [activeViewData]);

  const loadRefs = useCallback(async () => {
    const [nextModels, nextParts, nextGroups, nextPoints, nextRelations, nextRuns] = await Promise.all([
      request<Resource[]>("/api/master-data/vehicle-models"),
      request<Resource[]>("/api/master-data/parts"),
      request<MeasurementGroup[]>("/api/master-data/measurement-groups"),
      request<MeasurementPoint[]>("/api/master-data/measurement-points"),
      request<GroupPointRelation[]>("/api/master-data/measurement-group-points"),
      request<ProductionRun[]>("/api/process/production-runs"),
    ]);
    setModels(nextModels);
    setParts(nextParts);
    setGroups(nextGroups);
    setMasterPoints(nextPoints);
    setGroupPointRelations(nextRelations);
    setRuns(nextRuns);
    setVehicleModelId((current) => current || modelId || nextModels[0]?.id || "");
  }, [modelId]);

  const loadCanvas = useCallback(async (signal?: AbortSignal) => {
    const requestId = ++canvasRequestIdRef.current;
    if (!vehicleModelId) {
      setCanvas(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ vehicle_model_id: vehicleModelId });
      if (groupId) params.set("measurement_group_id", groupId);
      if (runId) params.set("production_run_id", runId);
      const payload = await request<CanvasPayload>(`/api/quality/body-map/canvas?${params}`, { signal });
      if (signal?.aborted || requestId !== canvasRequestIdRef.current) return;
      setCanvas(payload);
    } catch (err) {
      if (signal?.aborted || requestId !== canvasRequestIdRef.current) return;
      setError(err instanceof Error ? err.message : "加载车身点位图失败");
      setCanvas(null);
    } finally {
      if (requestId === canvasRequestIdRef.current) setLoading(false);
    }
  }, [vehicleModelId, groupId, runId]);

  const changeVehicleModel = useCallback((nextModelId: string) => {
    canvasRequestIdRef.current += 1;
    detailRequestIdRef.current += 1;
    setCanvas(null);
    setLoading(Boolean(nextModelId));
    setGroupId("");
    setRunId("");
    setSelectedPointId("");
    setDetail(null);
    setDetailLoading(false);
    setPendingPlaceId("");
    setSelectedGovPointId("");
    setSideTab("detail");
    setSideTabPinned(false);
    setVehicleModelId(nextModelId);
  }, []);

  const reloadAll = useCallback(async () => {
    await loadRefs();
    await loadCanvas();
  }, [loadRefs, loadCanvas]);

  const loadDetail = useCallback(
    async (pointId: string, scopedRunId?: string) => {
      const requestId = ++detailRequestIdRef.current;
      setSelectedPointId(pointId);
      if (!sideTabPinned) setSideTab("detail");
      setDetailLoading(true);
      try {
        const params = new URLSearchParams();
        const effectiveRunId = scopedRunId || runId;
        if (effectiveRunId) params.set("production_run_id", effectiveRunId);
        const query = params.toString();
        const payload = await request<PointDetail>(
          `/api/quality/body-map/points/${pointId}/detail${query ? `?${query}` : ""}`,
        );
        if (requestId !== detailRequestIdRef.current) return;
        setDetail(payload);
      } catch (err) {
        if (requestId !== detailRequestIdRef.current) return;
        setError(err instanceof Error ? err.message : "加载点位详情失败");
      } finally {
        if (requestId === detailRequestIdRef.current) setDetailLoading(false);
      }
    },
    [runId, sideTabPinned],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadRefs().catch((err) => setError(err instanceof Error ? err.message : "加载主数据失败"));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadRefs]);

  useEffect(() => {
    if (!modelId) return;
    const timer = window.setTimeout(() => changeVehicleModel(modelId), 0);
    return () => window.clearTimeout(timer);
  }, [modelId, changeVehicleModel]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void loadCanvas(controller.signal), 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [loadCanvas]);

  useEffect(() => {
    if (!message) return;
    const timer = window.setTimeout(() => setMessage(""), 3200);
    return () => window.clearTimeout(timer);
  }, [message]);

  useEffect(() => {
    if (!selectedPointId && !sideTabPinned) {
      const timer = window.setTimeout(() => setSideTab("detail"), 0);
      return () => window.clearTimeout(timer);
    }
  }, [selectedPointId, sideTabPinned]);

  function clientToNormalized(view: BodyView, clientX: number, clientY: number) {
    const stage = stageRefs.current[view];
    if (!stage) return null;
    const rect = stage.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;
    const rawX = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    const rawY = Math.min(1, Math.max(0, (clientY - rect.top) / rect.height));
    return snapCoords(rawX, rawY, gridCols, gridRows);
  }

  function updateCanvasPoint(view: BodyView, pointId: string, patch: Partial<MapPoint>) {
    setCanvas((current) => {
      if (!current) return current;
      const views = current.views.map((item) => {
        if (item.body_view !== view) return item;
        const points = item.points.map((point) =>
          point.measurement_point_id === pointId ? { ...point, ...patch } : point,
        );
        const placed_count = points.filter((p) => p.layout_x != null).length;
        return { ...item, points, placed_count };
      });
      return {
        ...current,
        views,
        placed_count: views.reduce((sum, item) => sum + (item.placed_count ?? 0), 0),
      };
    });
  }

  async function saveLayout(view: BodyView, pointId: string, x: number, y: number, col: number, row: number) {
    const layout = await request<LayoutRead>(`/api/quality/body-map/layouts/${pointId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        body_view: view,
        layout_x: x,
        layout_y: y,
        grid_col: col,
        grid_row: row,
      }),
    });
    updateCanvasPoint(view, pointId, {
      layout_id: layout.id,
      layout_x: layout.layout_x,
      layout_y: layout.layout_y,
      grid_col: layout.grid_col,
      grid_row: layout.grid_row,
    });
    return layout;
  }

  async function deactivatePoint(point: MapPoint) {
    if (!point.layout_id) {
      setMessage("该点尚未落在当前视图，无需移除");
      return;
    }
    const label = viewLabel(activeView, viewLabels);
    if (!window.confirm(`从${label}移除 ${point.code}？测量点主数据不会删除。`)) {
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await request(`/api/quality/body-map/layouts/${point.layout_id}/deactivate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body_view: activeView }),
      });
      setMessage(`已从${label}移除 ${point.code}`);
      if (selectedPointId === point.measurement_point_id) {
        setSelectedPointId("");
        setDetail(null);
      }
      await loadCanvas();
    } catch (err) {
      setError(err instanceof Error ? err.message : "移除点位失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitCreate(event: FormEvent) {
    event.preventDefault();
    if (!createDraft || !vehicleModelId) return;
    setSubmitting(true);
    setError("");
    try {
      const created = await request<MapPoint>("/api/quality/body-map/points", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vehicle_model_id: vehicleModelId,
          body_view: createDraft.body_view,
          layout_x: createDraft.layout_x,
          layout_y: createDraft.layout_y,
          grid_col: createDraft.grid_col,
          grid_row: createDraft.grid_row,
          code: createForm.code.trim(),
          name: createForm.name.trim(),
          part_id: createForm.part_id,
          region: createForm.region.trim() || null,
          quality_types: createForm.quality_types,
          measurement_group_id: groupId || null,
        }),
      });
      setCreateDraft(null);
      setCreateForm({
        code: "",
        name: "",
        part_id: "",
        region: "",
        quality_types: ["THICKNESS", "COLOR_DIFFERENCE", "ORANGE_PEEL"],
      });
      setMessage(`已创建测量点 ${created.code}`);
      await reloadAll();
      await loadDetail(created.measurement_point_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建测量点失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitGroupForm(event: FormEvent) {
    event.preventDefault();
    if (!vehicleModelId) return;
    setSubmitting(true);
    setError("");
    try {
      const body = {
        code: groupForm.code.trim(),
        name: groupForm.name.trim(),
        vehicle_model_id: vehicleModelId,
        quality_type: groupForm.quality_type,
        expected_point_count: groupForm.expected_point_count.trim()
          ? Number(groupForm.expected_point_count)
          : null,
        remark: groupForm.remark.trim() || null,
      };
      if (groupModal === "edit" && editingGroupId) {
        await request(`/api/master-data/measurement-groups/${editingGroupId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        setMessage(`已更新测量编组 ${body.code}`);
      } else {
        const created = await request<MeasurementGroup>("/api/master-data/measurement-groups", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        setGroupId(created.id);
        setMessage(`已创建测量编组 ${created.code}`);
      }
      setGroupModal(null);
      setEditingGroupId("");
      await reloadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存测量编组失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitPointForm(event: FormEvent) {
    event.preventDefault();
    if (!vehicleModelId) return;
    if (!pointForm.quality_types.length) {
      setError("请至少选择一种质量类型");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const body = {
        code: pointForm.code.trim(),
        name: pointForm.name.trim(),
        vehicle_model_id: vehicleModelId,
        part_id: pointForm.part_id,
        region: pointForm.region.trim() || null,
        quality_types: pointForm.quality_types,
        point_type: "QUALITY",
      };
      let pointId = editingPointId;
      if (pointModal === "edit" && editingPointId) {
        await request(`/api/master-data/measurement-points/${editingPointId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        setMessage(`已更新测量点 ${body.code}`);
      } else {
        const created = await request<MeasurementPoint>("/api/master-data/measurement-points", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        pointId = created.id;
        setMessage(`已创建测量点 ${created.code}`);
        if (pointForm.bind_to_group && groupId) {
          await request("/api/master-data/measurement-group-points", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              measurement_group_id: groupId,
              measurement_point_id: created.id,
              sequence_no: 0,
            }),
          });
        }
      }
      setPointModal(null);
      setEditingPointId("");
      setSelectedGovPointId(pointId);
      await reloadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存测量点失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function bindPointToGroup(pointId: string) {
    if (!groupId) {
      setMessage("请先选择测量编组");
      return;
    }
    if (boundPointIds.has(pointId)) {
      setMessage("该点已绑定到当前编组");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await request("/api/master-data/measurement-group-points", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          measurement_group_id: groupId,
          measurement_point_id: pointId,
          sequence_no: 0,
        }),
      });
      setMessage("已绑定到当前编组");
      await reloadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "绑定失败");
    } finally {
      setSubmitting(false);
    }
  }

  function openCreateGroup() {
    setGroupForm(emptyGroupForm());
    setEditingGroupId("");
    setGroupModal("create");
  }

  function openEditGroup() {
    const group = filteredGroups.find((item) => item.id === groupId);
    if (!group) {
      setMessage("请先选择要编辑的编组");
      return;
    }
    setGroupForm({
      code: group.code,
      name: group.name,
      quality_type: group.quality_type,
      expected_point_count: group.expected_point_count != null ? String(group.expected_point_count) : "",
      remark: group.remark ?? "",
    });
    setEditingGroupId(group.id);
    setGroupModal("edit");
  }

  function openCreatePoint() {
    setPointForm({
      ...emptyPointForm(),
      part_id: parts[0]?.id || "",
      bind_to_group: Boolean(groupId),
    });
    setEditingPointId("");
    setPointModal("create");
  }

  function openEditPoint(pointId?: string) {
    const id = pointId || selectedGovPointId;
    const point = filteredMasterPoints.find((item) => item.id === id);
    if (!point) {
      setMessage("请先选择要编辑的测量点");
      return;
    }
    setPointForm({
      code: point.code,
      name: point.name,
      part_id: point.part_id,
      region: point.region ?? "",
      quality_types: point.quality_types?.length ? [...point.quality_types] : ["THICKNESS"],
      bind_to_group: false,
    });
    setEditingPointId(point.id);
    setPointModal("edit");
  }

  function focusPane(view: BodyView) {
    setActiveView(view);
    paneRefs.current[view]?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
  }

  function onStagePointerDown(view: BodyView, event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    setActiveView(view);
    if ((event.target as HTMLElement).closest(".body-map-point")) return;
    const coords = clientToNormalized(view, event.clientX, event.clientY);
    if (!coords) return;

    if (pendingPlaceId) {
      const point = viewsByKey.get(view)?.points.find((item) => item.measurement_point_id === pendingPlaceId);
      void saveLayout(view, pendingPlaceId, coords.x, coords.y, coords.col, coords.row)
        .then(() => {
          setMessage(`已放置 ${point?.code ?? "点位"}，可继续拖拽微调`);
          setPendingPlaceId("");
        })
        .catch((err) => setError(err instanceof Error ? err.message : "落图失败"));
      return;
    }

    if (!editMode) return;
    setCreateDraft({
      body_view: view,
      layout_x: coords.x,
      layout_y: coords.y,
      grid_col: coords.col,
      grid_row: coords.row,
    });
    setCreateForm((current) => ({
      ...current,
      code: current.code || `P-${coords.col}-${coords.row}`,
      name: current.name || `点位 ${coords.col},${coords.row}`,
      part_id: current.part_id || parts[0]?.id || "",
    }));
  }

  function onPointPointerDown(view: BodyView, event: ReactPointerEvent<HTMLButtonElement>, point: MapPoint) {
    event.stopPropagation();
    setActiveView(view);
    void loadDetail(point.measurement_point_id, runId || canvas?.production_run_id || undefined);
    if (!editMode) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointId: point.measurement_point_id,
      pointerId: event.pointerId,
      moved: false,
      view,
    };
  }

  function onPointPointerMove(event: ReactPointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId || !editMode) return;
    const coords = clientToNormalized(drag.view, event.clientX, event.clientY);
    if (!coords) return;
    drag.moved = true;
    updateCanvasPoint(drag.view, drag.pointId, {
      layout_x: coords.x,
      layout_y: coords.y,
      grid_col: coords.col,
      grid_row: coords.row,
    });
  }

  async function onPointPointerUp(event: ReactPointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragRef.current = null;
    if (!editMode || !drag.moved) return;
    const coords = clientToNormalized(drag.view, event.clientX, event.clientY);
    if (!coords) return;
    try {
      await saveLayout(drag.view, drag.pointId, coords.x, coords.y, coords.col, coords.row);
      setMessage("点位坐标已更新");
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存坐标失败");
      await loadCanvas();
    }
  }

  function toggleQualityType(list: string[], value: string): string[] {
    return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
  }

  const selectedGroup = filteredGroups.find((item) => item.id === groupId) ?? null;

  return (
    <section className="panel body-map-panel">
      <div className="program-subheading">
        <div>
          <span className="eyebrow">车身点位图</span>
          <h3>白车身网格与质量分布</h3>
          <small>四视图 canvas + 测量编组/点位一站式治理（主数据测量体系已迁入此页）。</small>
        </div>
        <div className="row-actions">
          <button
            className="button button-secondary"
            type="button"
            onClick={() => void loadCanvas()}
            disabled={loading}
          >
            {loading ? <LoaderCircle className="spin" /> : <RefreshCw />}
            刷新
          </button>
          <button
            className="button button-secondary"
            type="button"
            disabled={!vehicleModelId || !canvas?.vehicle_model_code}
            onClick={() => setImageEditorOpen(true)}
          >
            <ImageIcon />
            底图管理
          </button>
          <button
            className={`button ${editMode ? "button-primary" : "button-secondary"}`}
            type="button"
            onClick={() => {
              setEditMode((value) => !value);
              setPendingPlaceId("");
            }}
          >
            <Pencil />
            {editMode ? "退出编辑" : "编辑布局"}
          </button>
        </div>
      </div>

      <div className="body-map-shell">
        {canvas ? (
          <section className="quality-analytics-stat-grid body-map-stat-grid">
            <article>
              <span>已落图</span>
              <strong>{canvas.placed_count}</strong>
              <small>四视图 ACTIVE 布局合计</small>
            </article>
            <article>
              <span>编组内</span>
              <strong>{canvas.group_point_count}</strong>
              <small>{groupId ? "所选测量编组" : "全部质量点位"}</small>
            </article>
            <article className={canvas.fail_count > 0 ? "stat-alert" : ""}>
              <span>超差（已落图）</span>
              <strong>{canvas.fail_count}</strong>
              <small>仅统计 VERIFIED 判定</small>
            </article>
            <article>
              <span>未落图</span>
              <strong>{unplaced.length}</strong>
              <small>当前活动视图 · {viewLabel(activeView, viewLabels)}</small>
            </article>
            <article className="body-map-stat-scope">
              <span>质量范围</span>
              <strong className="mono">{canvas.production_run_no ?? "无生产事件"}</strong>
              <small>{canvas.quality_scope ?? "VERIFIED"} · 自动/指定生产事件</small>
            </article>
          </section>
        ) : null}

        <div className="governance-scope-bar body-map-scope-bar">
          <div>
            <strong>工作范围</strong>
            <span>四视图同屏；先选车型与编组 / 生产事件，再点击视图进行编辑落图。着色仅基于已核验质量数据。</span>
          </div>
          <div className="governance-scope-fields body-map-scope-fields">
            <label className="form-field">
              <span>车型</span>
              <select value={vehicleModelId} onChange={(event) => changeVehicleModel(event.target.value)}>
                <option value="">请选择车型</option>
                {models.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.code} / {item.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="form-field">
              <span>聚焦视图</span>
              <div className="body-map-view-toggle" role="group" aria-label="聚焦视图">
                {BODY_VIEWS.map((view) => (
                  <button
                    key={view}
                    type="button"
                    className={activeView === view ? "is-active" : ""}
                    onClick={() => focusPane(view)}
                  >
                    {viewLabel(view, viewLabels).replace("视图", "")}
                  </button>
                ))}
              </div>
            </div>
            <label className="form-field">
              <span>测量编组</span>
              <select value={groupId} onChange={(event) => setGroupId(event.target.value)}>
                <option value="">全部点位</option>
                {filteredGroups.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.code} / {item.name}
                    {item.quality_type ? ` · ${qualityLabels[item.quality_type] ?? item.quality_type}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>生产事件</span>
              <select value={runId} onChange={(event) => setRunId(event.target.value)}>
                <option value="">最新生产事件（自动）</option>
                {filteredRuns.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.run_no}
                    {item.body_no ? ` · ${item.body_no}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>着色</span>
              <select value={overlayMode} onChange={(event) => setOverlayMode(event.target.value as OverlayMode)}>
                <option value="RISK">综合风险</option>
                <option value="THICKNESS">膜厚</option>
                <option value="COLOR_DIFFERENCE">色差</option>
                <option value="ORANGE_PEEL">橘皮</option>
              </select>
            </label>
            <label className="governance-chip body-map-check-chip">
              <input
                type="checkbox"
                checked={showUngrouped}
                onChange={(event) => setShowUngrouped(event.target.checked)}
              />
              显示编组外点位
            </label>
          </div>
        </div>

        <div className="body-map-legend">
          <span className="body-map-legend-label">图例</span>
          <span className="body-map-legend-item">
            <i style={{ background: "var(--teal)" }} />
            合格（已核验）
          </span>
          <span className="body-map-legend-item">
            <i style={{ background: "var(--amber)" }} />
            无标准 / 无效
          </span>
          <span className="body-map-legend-item">
            <i style={{ background: "var(--red)" }} />
            超差
          </span>
          <span className="body-map-legend-item">
            <i style={{ background: "var(--text-muted)" }} />
            无已核验数据
          </span>
        </div>

        {error ? <div className="form-error">{error}</div> : null}
        {message ? <div className="form-success">{message}</div> : null}
        {pendingPlaceId ? (
          <div className="body-map-hint is-active">
            <div className="body-map-hint-copy">
              <MapPinned />
              <span>
                放置模式：在「{viewLabel(activeView, viewLabels)}」点击目标网格，将未落图点位放到该位置。
              </span>
            </div>
            <button type="button" className="button button-secondary" onClick={() => setPendingPlaceId("")}>
              取消
            </button>
          </div>
        ) : null}

        {!vehicleModelId ? (
          <div className="program-empty large-empty body-map-empty">
            <MapPinned />
            请先选择车型以加载白车身点位图。
          </div>
        ) : (
          <div className="body-map-layout">
            <div className="body-map-stage-wrap">
              <div
                className="body-map-canvas"
                style={{ "--grid-cols": String(gridCols), "--grid-rows": String(gridRows) } as CSSProperties}
              >
                {viewOrder.map((view) => {
                  const payload = viewsByKey.get(view);
                  const baseUrl = payload?.background_image_url ?? DEFAULT_VIEW_IMAGES[view];
                  const backgroundUrl = imageRevision
                    ? `${baseUrl}${baseUrl.includes("?") ? "&" : "?"}v=${imageRevision}`
                    : baseUrl;
                  const points = visiblePointsForView(view);
                  const isActive = activeView === view;
                  return (
                    <article
                      key={view}
                      ref={(node) => {
                        paneRefs.current[view] = node;
                      }}
                      className={`body-map-pane ${isActive ? "is-active-pane" : ""}`}
                      onClick={() => setActiveView(view)}
                    >
                      <div className="body-map-stage-meta">
                        <div>
                          <span className="eyebrow">{viewLabel(view, viewLabels)}</span>
                          <strong>
                            {canvas?.vehicle_model_code ?? "—"} · {canvas?.vehicle_model_name ?? "加载中"}
                          </strong>
                        </div>
                        <small className="mono">
                          {payload?.placed_count ?? points.length} 点
                          {isActive && editMode ? " · 编辑中" : ""}
                        </small>
                      </div>
                      <div
                        ref={(node) => {
                          stageRefs.current[view] = node;
                        }}
                        className={`body-map-stage ${editMode || pendingPlaceId ? "is-editing" : ""}`}
                        onPointerDown={(event) => onStagePointerDown(view, event)}
                      >
                        <Image
                          className="body-map-bg"
                          src={backgroundUrl}
                          alt={viewLabel(view, viewLabels)}
                          width={1600}
                          height={900}
                          unoptimized
                          draggable={false}
                        />
                        <div className="body-map-grid" aria-hidden="true" />
                        {points.map((point) => (
                          <button
                            key={point.measurement_point_id}
                            type="button"
                            className={`body-map-point ${selectedPointId === point.measurement_point_id ? "is-selected" : ""} ${point.in_group ? "in-group" : "out-group"}`}
                            style={{
                              left: `${(point.layout_x ?? 0) * 100}%`,
                              top: `${(point.layout_y ?? 0) * 100}%`,
                              ["--point-color" as string]: pointColor(point, overlayMode),
                            }}
                            title={`${point.code} / ${point.name}`}
                            onPointerDown={(event) => onPointPointerDown(view, event, point)}
                            onPointerMove={onPointPointerMove}
                            onPointerUp={(event) => void onPointPointerUp(event)}
                          >
                            <span>{point.code}</span>
                          </button>
                        ))}
                        {loading ? (
                          <div className="body-map-loading">
                            <LoaderCircle className="spin" />
                            正在加载点位…
                          </div>
                        ) : null}
                      </div>
                    </article>
                  );
                })}
              </div>

              {editMode ? (
                <div className="body-map-hint">
                  <Plus />
                  <span>
                    编辑模式：先点击激活视图，再拖拽点位吸附到网格；点击空白格新建测量点。图上「移除」仅停用当前活动视图布局。
                  </span>
                </div>
              ) : null}

              {(editMode || unplaced.length > 0) && unplaced.length ? (
                <div className="body-map-unplaced">
                  <div className="body-map-unplaced-head">
                    <strong>未落图点位 · {viewLabel(activeView, viewLabels)}</strong>
                    <span>{unplaced.length}</span>
                  </div>
                  <div className="body-map-unplaced-list">
                    {unplaced.map((point) => (
                      <button
                        key={point.measurement_point_id}
                        type="button"
                        className={`button button-secondary ${pendingPlaceId === point.measurement_point_id ? "is-pending" : ""}`}
                        onClick={() => {
                          setEditMode(true);
                          setPendingPlaceId(point.measurement_point_id);
                          setMessage(`请在「${viewLabel(activeView, viewLabels)}」点击放置 ${point.code}`);
                        }}
                      >
                        放置 {point.code}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>

            <aside className="body-map-detail">
              <div className="body-map-side-tabs" role="tablist" aria-label="侧栏">
                <button
                  type="button"
                  role="tab"
                  aria-selected={sideTab === "governance"}
                  className={sideTab === "governance" ? "is-active" : ""}
                  onClick={() => {
                    setSideTab("governance");
                    setSideTabPinned(true);
                  }}
                >
                  <ListTree />
                  测量治理
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={sideTab === "detail"}
                  className={sideTab === "detail" ? "is-active" : ""}
                  onClick={() => {
                    setSideTab("detail");
                    setSideTabPinned(true);
                  }}
                >
                  <Layers />
                  点位详情
                </button>
              </div>

              {sideTab === "governance" ? (
                <div className="body-map-governance">
                  <div className="body-map-detail-head">
                    <div>
                      <span className="eyebrow">测量编组</span>
                      <h4>{selectedGroup ? `${selectedGroup.code} · ${selectedGroup.name}` : "未选择编组"}</h4>
                      <small>
                        {selectedGroup
                          ? `${qualityLabels[selectedGroup.quality_type] ?? selectedGroup.quality_type}${selectedGroup.expected_point_count != null ? ` · 预期 ${selectedGroup.expected_point_count} 点` : ""}`
                          : "选择或新建编组后可绑定点位"}
                      </small>
                    </div>
                    <div className="row-actions">
                      <button className="button button-secondary" type="button" onClick={openCreateGroup}>
                        <Plus />
                        新建
                      </button>
                      <button
                        className="button button-secondary"
                        type="button"
                        disabled={!groupId}
                        onClick={openEditGroup}
                      >
                        <Pencil />
                        编辑
                      </button>
                    </div>
                  </div>

                  <div className="body-map-gov-list">
                    {filteredGroups.length ? (
                      filteredGroups.map((group) => (
                        <button
                          key={group.id}
                          type="button"
                          className={`body-map-gov-item ${groupId === group.id ? "is-selected" : ""}`}
                          onClick={() => setGroupId(group.id)}
                        >
                          <strong>
                            {group.code} / {group.name}
                          </strong>
                          <small>
                            {qualityLabels[group.quality_type] ?? group.quality_type}
                            {group.expected_point_count != null ? ` · 预期 ${group.expected_point_count}` : ""}
                          </small>
                        </button>
                      ))
                    ) : (
                      <div className="program-empty">当前车型暂无测量编组</div>
                    )}
                  </div>

                  <div className="program-subheading compact">
                    <div>
                      <span className="eyebrow">测量点</span>
                      <h4>车型点位主数据</h4>
                    </div>
                    <div className="row-actions">
                      <button className="button button-secondary" type="button" onClick={openCreatePoint}>
                        <Plus />
                        新建点
                      </button>
                      <button
                        className="button button-secondary"
                        type="button"
                        disabled={!selectedGovPointId}
                        onClick={() => openEditPoint()}
                      >
                        <Pencil />
                        编辑
                      </button>
                    </div>
                  </div>

                  <div className="body-map-gov-list body-map-gov-points">
                    {filteredMasterPoints.length ? (
                      filteredMasterPoints.map((point) => {
                        const bound = boundPointIds.has(point.id);
                        return (
                          <div
                            key={point.id}
                            className={`body-map-gov-item ${selectedGovPointId === point.id ? "is-selected" : ""}`}
                          >
                            <button
                              type="button"
                              className="body-map-gov-point-main"
                              onClick={() => {
                                setSelectedGovPointId(point.id);
                                void loadDetail(point.id, runId || canvas?.production_run_id || undefined);
                              }}
                            >
                              <strong>
                                {point.code} / {point.name}
                              </strong>
                              <small>
                                {(point.quality_types ?? [])
                                  .map((item) => qualityLabels[item] ?? item)
                                  .join(" · ") || "未设质量类型"}
                                {point.region ? ` · ${point.region}` : ""}
                              </small>
                            </button>
                            <button
                              type="button"
                              className={`button button-secondary body-map-bind-btn ${bound ? "is-bound" : ""}`}
                              disabled={!groupId || bound || submitting}
                              title={bound ? "已绑定" : "绑定到当前编组"}
                              onClick={() => void bindPointToGroup(point.id)}
                            >
                              <Link2 />
                              {bound ? "已绑" : "绑定"}
                            </button>
                          </div>
                        );
                      })
                    ) : (
                      <div className="program-empty">当前车型暂无测量点</div>
                    )}
                  </div>
                </div>
              ) : !selectedPointId ? (
                <div className="program-empty body-map-detail-empty">
                  <MapPinned />
                  点击图上点位查看质量与刷子参数。
                </div>
              ) : detailLoading || !detail ? (
                <div className="program-empty body-map-detail-empty">
                  <LoaderCircle className="spin" />
                  正在加载点位详情…
                </div>
              ) : (
                <>
                  <div className="body-map-detail-head">
                    <div>
                      <span className="eyebrow">测量点</span>
                      <h4>
                        {detail.code} · {detail.name}
                      </h4>
                      <small>
                        {[detail.part_code, detail.part_name, detail.region].filter(Boolean).join(" · ") ||
                          "未标注零件/区域"}
                      </small>
                    </div>
                    {editMode ? (
                      <button
                        className="button button-secondary"
                        type="button"
                        disabled={submitting}
                        onClick={() => {
                          const point = activeViewData?.points.find(
                            (item) => item.measurement_point_id === detail.measurement_point_id,
                          );
                          if (point) void deactivatePoint(point);
                        }}
                      >
                        <X />
                        从图移除
                      </button>
                    ) : null}
                  </div>

                  <div className="body-map-quality-grid">
                    {detail.quality_summaries.map((item) => (
                      <article key={item.quality_type} data-judgement={item.judgement ?? "EMPTY"}>
                        <span>{qualityLabels[item.quality_type] ?? item.quality_type}</span>
                        <strong className="mono">{formatValue(item.value, item.unit)}</strong>
                        <small>
                          {item.metric_name ?? item.metric_code ?? "—"}
                          {item.judgement
                            ? ` · ${judgementLabels[item.judgement] ?? item.judgement}`
                            : " · 无已核验数据"}
                        </small>
                        {item.reliability_status ? (
                          <span
                            className={`body-map-reliability reliability-${item.reliability_status.toLowerCase()}`}
                          >
                            {reliabilityLabels[item.reliability_status] ?? item.reliability_status}
                          </span>
                        ) : null}
                        {item.measured_at ? (
                          <small className="mono">
                            {new Date(item.measured_at).toLocaleString("zh-CN", { hour12: false })}
                          </small>
                        ) : null}
                      </article>
                    ))}
                  </div>

                  <PointAiActions
                    productionRunId={runId || canvas?.production_run_id}
                    measurementPointId={detail.measurement_point_id}
                  />

                  <div className="body-map-brush-block">
                    <div className="program-subheading compact">
                      <div>
                        <span className="eyebrow">喷涂关联</span>
                        <h4>刷子号与参数</h4>
                      </div>
                      <Link className="button button-secondary" href="/process?tab=recipes">
                        去工艺配方
                      </Link>
                    </div>
                    {!detail.brush_contributions.length ? (
                      <div className="program-empty">
                        暂无点位贡献；请在工艺管理中维护 ACTIVE 贡献版本或遗留刷子贡献。
                      </div>
                    ) : (
                      detail.brush_contributions.map((brush) => (
                        <div
                          className="body-map-brush-card"
                          key={`${brush.brush_id}-${brush.process_stage}-${brush.target_family ?? brush.version}`}
                        >
                          <div className="body-map-brush-head">
                            <div className="body-map-brush-title">
                              <strong>
                                {coatingLabels[brush.coating_system] ?? brush.coating_system} · {brush.brush_no}
                              </strong>
                              <span
                                className={`status-badge ${brush.contribution_source === "GOVERNED" ? "" : "status-muted"}`}
                              >
                                {brush.contribution_source === "GOVERNED" ? "治理贡献" : "遗留贡献"}
                              </span>
                            </div>
                            <small>
                              {stageLabel(brush.process_stage)} · 表 {brush.brush_table_no} · 重叠{" "}
                              {(brush.overlap_ratio * 100).toFixed(0)}% · 权重{" "}
                              {(brush.contribution_weight * 100).toFixed(0)}%
                              {brush.target_family
                                ? ` · ${qualityLabels[brush.target_family] ?? brush.target_family}`
                                : ""}
                              {brush.is_approved ? " · 已审批" : " · 待审批"}
                            </small>
                            <PointParameterVersionEditor contribution={brush} />
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
                                    <em>设定</em> {formatValue(parameter.configured_value, parameter.unit)}
                                  </span>
                                  <span className="mono">
                                    <em>实绩</em>{" "}
                                    {parameter.actual_value != null
                                      ? formatValue(parameter.actual_value, parameter.unit)
                                      : "—"}
                                  </span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <small className="muted">该刷子暂无配置参数</small>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </>
              )}
            </aside>
          </div>
        )}
      </div>

      {createDraft ? (
        <ModalShell
          eyebrow="新建测量点"
          title="在网格上创建点位"
          description={`将同步写入测量点主数据，并在${viewLabel(createDraft.body_view, viewLabels)}落图；若已选测量编组会自动绑定。`}
          onClose={closeCreateModal}
          busy={submitting}
        >
          <form onSubmit={(event) => void submitCreate(event)}>
            <div className="form-grid">
              <label className="form-field">
                <span>
                  点位代码<b>*</b>
                </span>
                <input
                  required
                  value={createForm.code}
                  onChange={(event) => setCreateForm({ ...createForm, code: event.target.value })}
                />
              </label>
              <label className="form-field">
                <span>
                  点位名称<b>*</b>
                </span>
                <input
                  required
                  value={createForm.name}
                  onChange={(event) => setCreateForm({ ...createForm, name: event.target.value })}
                />
              </label>
              <label className="form-field">
                <span>
                  零件<b>*</b>
                </span>
                <select
                  required
                  value={createForm.part_id}
                  onChange={(event) => setCreateForm({ ...createForm, part_id: event.target.value })}
                >
                  <option value="">请选择</option>
                  {parts.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.code} / {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span>区域</span>
                <input
                  value={createForm.region}
                  onChange={(event) => setCreateForm({ ...createForm, region: event.target.value })}
                />
              </label>
              <div className="form-field form-field-wide">
                <span>质量类型</span>
                <div className="body-map-multiselect">
                  {QUALITY_TYPE_OPTIONS.map((type) => (
                    <label key={type} className="governance-chip">
                      <input
                        type="checkbox"
                        checked={createForm.quality_types.includes(type)}
                        onChange={() =>
                          setCreateForm({
                            ...createForm,
                            quality_types: toggleQualityType(createForm.quality_types, type),
                          })
                        }
                      />
                      {qualityLabels[type]}
                    </label>
                  ))}
                </div>
              </div>
              <div className="form-field">
                <span>落点</span>
                <div className="mono">
                  视图 {createDraft.body_view} · 格 ({createDraft.grid_col}, {createDraft.grid_row}) · (
                  {createDraft.layout_x.toFixed(3)}, {createDraft.layout_y.toFixed(3)})
                </div>
              </div>
            </div>
            <div className="modal-actions">
              <button
                className="button button-secondary"
                type="button"
                onClick={() => setCreateDraft(null)}
                disabled={submitting}
              >
                取消
              </button>
              <button className="button button-primary" type="submit" disabled={submitting}>
                {submitting ? <LoaderCircle className="spin" /> : null}
                创建并落图
              </button>
            </div>
          </form>
        </ModalShell>
      ) : null}

      {groupModal ? (
        <ModalShell
          eyebrow={groupModal === "create" ? "新建编组" : "编辑编组"}
          title={groupModal === "create" ? "创建测量编组" : "更新测量编组"}
          description="编组用于质量录入与车身点位图过滤；质量类型取自系统目录，不写入设备极限。"
          onClose={closeGroupModal}
          busy={submitting}
        >
          <form onSubmit={(event) => void submitGroupForm(event)}>
            <div className="form-grid">
              <label className="form-field">
                <span>
                  编组代码<b>*</b>
                </span>
                <input
                  required
                  value={groupForm.code}
                  onChange={(event) => setGroupForm({ ...groupForm, code: event.target.value })}
                />
              </label>
              <label className="form-field">
                <span>
                  编组名称<b>*</b>
                </span>
                <input
                  required
                  value={groupForm.name}
                  onChange={(event) => setGroupForm({ ...groupForm, name: event.target.value })}
                />
              </label>
              <label className="form-field">
                <span>
                  质量类型<b>*</b>
                </span>
                <select
                  required
                  value={groupForm.quality_type}
                  onChange={(event) => setGroupForm({ ...groupForm, quality_type: event.target.value })}
                >
                  {QUALITY_TYPE_OPTIONS.map((type) => (
                    <option key={type} value={type}>
                      {qualityLabels[type]}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span>预期点位数</span>
                <input
                  type="number"
                  min={0}
                  value={groupForm.expected_point_count}
                  onChange={(event) =>
                    setGroupForm({ ...groupForm, expected_point_count: event.target.value })
                  }
                />
              </label>
              <label className="form-field form-field-wide">
                <span>备注</span>
                <input
                  value={groupForm.remark}
                  onChange={(event) => setGroupForm({ ...groupForm, remark: event.target.value })}
                />
              </label>
            </div>
            <div className="modal-actions">
              <button
                className="button button-secondary"
                type="button"
                onClick={closeGroupModal}
                disabled={submitting}
              >
                取消
              </button>
              <button className="button button-primary" type="submit" disabled={submitting}>
                {submitting ? <LoaderCircle className="spin" /> : null}
                保存
              </button>
            </div>
          </form>
        </ModalShell>
      ) : null}

      {pointModal ? (
        <ModalShell
          eyebrow={pointModal === "create" ? "新建测量点" : "编辑测量点"}
          title={pointModal === "create" ? "创建测量点主数据" : "更新测量点主数据"}
          description="质量类型多选；创建时可选择绑定到当前测量编组。落图请在左侧四视图编辑模式中操作。"
          onClose={closePointModal}
          busy={submitting}
        >
          <form onSubmit={(event) => void submitPointForm(event)}>
            <div className="form-grid">
              <label className="form-field">
                <span>
                  点位代码<b>*</b>
                </span>
                <input
                  required
                  value={pointForm.code}
                  onChange={(event) => setPointForm({ ...pointForm, code: event.target.value })}
                />
              </label>
              <label className="form-field">
                <span>
                  点位名称<b>*</b>
                </span>
                <input
                  required
                  value={pointForm.name}
                  onChange={(event) => setPointForm({ ...pointForm, name: event.target.value })}
                />
              </label>
              <label className="form-field">
                <span>
                  零件<b>*</b>
                </span>
                <select
                  required
                  value={pointForm.part_id}
                  onChange={(event) => setPointForm({ ...pointForm, part_id: event.target.value })}
                >
                  <option value="">请选择</option>
                  {parts.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.code} / {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span>区域</span>
                <input
                  value={pointForm.region}
                  onChange={(event) => setPointForm({ ...pointForm, region: event.target.value })}
                />
              </label>
              <div className="form-field form-field-wide">
                <span>
                  质量类型<b>*</b>
                </span>
                <div className="body-map-multiselect">
                  {QUALITY_TYPE_OPTIONS.map((type) => (
                    <label key={type} className="governance-chip">
                      <input
                        type="checkbox"
                        checked={pointForm.quality_types.includes(type)}
                        onChange={() =>
                          setPointForm({
                            ...pointForm,
                            quality_types: toggleQualityType(pointForm.quality_types, type),
                          })
                        }
                      />
                      {qualityLabels[type]}
                    </label>
                  ))}
                </div>
              </div>
              {pointModal === "create" ? (
                <label className="governance-chip form-field-wide">
                  <input
                    type="checkbox"
                    checked={pointForm.bind_to_group && Boolean(groupId)}
                    disabled={!groupId}
                    onChange={(event) =>
                      setPointForm({ ...pointForm, bind_to_group: event.target.checked })
                    }
                  />
                  {groupId
                    ? `创建后绑定到编组 ${selectedGroup?.code ?? groupId}`
                    : "创建后绑定到当前编组（请先选择编组）"}
                </label>
              ) : null}
            </div>
            <div className="modal-actions">
              <button
                className="button button-secondary"
                type="button"
                onClick={closePointModal}
                disabled={submitting}
              >
                取消
              </button>
              <button className="button button-primary" type="submit" disabled={submitting}>
                {submitting ? <LoaderCircle className="spin" /> : null}
                保存
              </button>
            </div>
          </form>
        </ModalShell>
      ) : null}

      <BodyMapImageEditor
        open={imageEditorOpen}
        modelCode={canvas?.vehicle_model_code ?? ""}
        modelName={canvas?.vehicle_model_name}
        onClose={() => setImageEditorOpen(false)}
        onChanged={() => {
          setImageRevision(Date.now());
          void loadCanvas();
        }}
      />
    </section>
  );
}
