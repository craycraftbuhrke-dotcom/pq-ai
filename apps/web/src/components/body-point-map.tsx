"use client";

import { LoaderCircle, MapPinned, Pencil, Plus, RefreshCw, X } from "lucide-react";
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

import { ModalShell } from "@/components/modal-shell";
import { useWorkspaceContext } from "@/lib/workspace-context";

type Resource = { id: string; code: string; name: string; vehicle_model_id?: string; quality_type?: string };
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

const qualityLabels: Record<string, string> = {
  THICKNESS: "膜厚",
  COLOR_DIFFERENCE: "色差",
  ORANGE_PEEL: "橘皮",
};

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
  // Unverified / empty values stay soft — never teal from raw presence alone.
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

export function BodyPointMap() {
  const { modelId, factoryId, colorId } = useWorkspaceContext();
  const [models, setModels] = useState<Resource[]>([]);
  const [parts, setParts] = useState<Resource[]>([]);
  const [groups, setGroups] = useState<Resource[]>([]);
  const [runs, setRuns] = useState<ProductionRun[]>([]);
  const [vehicleModelId, setVehicleModelId] = useState(modelId || "");
  const [bodyView, setBodyView] = useState<"TOP" | "SIDE">("SIDE");
  const [groupId, setGroupId] = useState("");
  const [runId, setRunId] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [showUngrouped, setShowUngrouped] = useState(true);
  const [overlayMode, setOverlayMode] = useState<OverlayMode>("RISK");
  const [mapData, setMapData] = useState<BodyMapPayload | null>(null);
  const [detail, setDetail] = useState<PointDetail | null>(null);
  const [selectedPointId, setSelectedPointId] = useState("");
  const [pendingPlaceId, setPendingPlaceId] = useState("");
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [createDraft, setCreateDraft] = useState<CreateDraft | null>(null);
  const [createForm, setCreateForm] = useState({ code: "", name: "", part_id: "", region: "" });
  const [submitting, setSubmitting] = useState(false);
  const stageRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ pointId: string; pointerId: number; moved: boolean } | null>(null);

  const closeCreateModal = useCallback(() => {
    if (submitting) return;
    setCreateDraft(null);
  }, [submitting]);

  const gridCols = mapData?.grid_cols ?? 48;
  const gridRows = mapData?.grid_rows ?? 24;
  const backgroundUrl =
    mapData?.background_image_url ?? (bodyView === "TOP" ? "/body-maps/top.jpg" : "/body-maps/side.jpg");

  const filteredGroups = useMemo(
    () => groups.filter((item) => !vehicleModelId || item.vehicle_model_id === vehicleModelId),
    [groups, vehicleModelId],
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

  const visiblePoints = useMemo(() => {
    const points = mapData?.points ?? [];
    return points.filter((point) => {
      if (point.layout_x == null || point.layout_y == null) return false;
      if (groupId && !point.in_group && !showUngrouped) return false;
      return true;
    });
  }, [mapData, groupId, showUngrouped]);

  const unplaced = useMemo(
    () => (mapData?.points ?? []).filter((point) => point.layout_x == null || point.layout_y == null),
    [mapData],
  );

  const loadRefs = useCallback(async () => {
    const [nextModels, nextParts, nextGroups, nextRuns] = await Promise.all([
      request<Resource[]>("/api/master-data/vehicle-models"),
      request<Resource[]>("/api/master-data/parts"),
      request<Resource[]>("/api/master-data/measurement-groups"),
      request<ProductionRun[]>("/api/process/production-runs"),
    ]);
    setModels(nextModels);
    setParts(nextParts);
    setGroups(nextGroups);
    setRuns(nextRuns);
    setVehicleModelId((current) => current || modelId || nextModels[0]?.id || "");
  }, [modelId]);

  const loadMap = useCallback(async () => {
    if (!vehicleModelId) {
      setMapData(null);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        vehicle_model_id: vehicleModelId,
        body_view: bodyView,
      });
      if (groupId) params.set("measurement_group_id", groupId);
      if (runId) params.set("production_run_id", runId);
      const payload = await request<BodyMapPayload>(`/api/quality/body-map?${params}`);
      setMapData(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载车身点位图失败");
      setMapData(null);
    } finally {
      setLoading(false);
    }
  }, [vehicleModelId, bodyView, groupId, runId]);

  const loadDetail = useCallback(
    async (pointId: string, scopedRunId?: string) => {
      setSelectedPointId(pointId);
      setDetailLoading(true);
      try {
        const params = new URLSearchParams();
        const effectiveRunId = scopedRunId || runId;
        if (effectiveRunId) params.set("production_run_id", effectiveRunId);
        const query = params.toString();
        const payload = await request<PointDetail>(
          `/api/quality/body-map/points/${pointId}/detail${query ? `?${query}` : ""}`,
        );
        setDetail(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载点位详情失败");
      } finally {
        setDetailLoading(false);
      }
    },
    [runId],
  );

  useEffect(() => {
    void loadRefs().catch((err) => setError(err instanceof Error ? err.message : "加载主数据失败"));
  }, [loadRefs]);

  useEffect(() => {
    if (modelId) setVehicleModelId(modelId);
  }, [modelId]);

  useEffect(() => {
    void loadMap();
  }, [loadMap]);

  useEffect(() => {
    if (!message) return;
    const timer = window.setTimeout(() => setMessage(""), 3200);
    return () => window.clearTimeout(timer);
  }, [message]);

  useEffect(() => {
    setGroupId("");
    setRunId("");
    setSelectedPointId("");
    setDetail(null);
    setPendingPlaceId("");
  }, [vehicleModelId]);

  function clientToNormalized(clientX: number, clientY: number) {
    const stage = stageRef.current;
    if (!stage) return null;
    const rect = stage.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;
    const rawX = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    const rawY = Math.min(1, Math.max(0, (clientY - rect.top) / rect.height));
    return snapCoords(rawX, rawY, gridCols, gridRows);
  }

  async function saveLayout(pointId: string, x: number, y: number, col: number, row: number) {
    const layout = await request<LayoutRead>(`/api/quality/body-map/layouts/${pointId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        body_view: bodyView,
        layout_x: x,
        layout_y: y,
        grid_col: col,
        grid_row: row,
      }),
    });
    setMapData((current) => {
      if (!current) return current;
      const points = current.points.map((point) =>
        point.measurement_point_id === pointId
          ? {
              ...point,
              layout_id: layout.id,
              layout_x: layout.layout_x,
              layout_y: layout.layout_y,
              grid_col: layout.grid_col,
              grid_row: layout.grid_row,
            }
          : point,
      );
      return {
        ...current,
        placed_count: points.filter((item) => item.layout_x != null).length,
        points,
      };
    });
    return layout;
  }

  async function deactivatePoint(point: MapPoint) {
    if (!point.layout_id) {
      setMessage("该点尚未落在当前视图，无需移除");
      return;
    }
    if (!window.confirm(`从${bodyView === "TOP" ? "俯视" : "侧视"}图移除 ${point.code}？测量点主数据不会删除。`)) {
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await request(`/api/quality/body-map/layouts/${point.layout_id}/deactivate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body_view: bodyView }),
      });
      setMessage(`已从${bodyView === "TOP" ? "俯视" : "侧视"}图移除 ${point.code}`);
      if (selectedPointId === point.measurement_point_id) {
        setSelectedPointId("");
        setDetail(null);
      }
      await loadMap();
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
          body_view: bodyView,
          layout_x: createDraft.layout_x,
          layout_y: createDraft.layout_y,
          grid_col: createDraft.grid_col,
          grid_row: createDraft.grid_row,
          code: createForm.code.trim(),
          name: createForm.name.trim(),
          part_id: createForm.part_id,
          region: createForm.region.trim() || null,
          measurement_group_id: groupId || null,
        }),
      });
      setCreateDraft(null);
      setCreateForm({ code: "", name: "", part_id: "", region: "" });
      setMessage(`已创建测量点 ${created.code}`);
      await loadMap();
      await loadDetail(created.measurement_point_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建测量点失败");
    } finally {
      setSubmitting(false);
    }
  }

  function onStagePointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    if ((event.target as HTMLElement).closest(".body-map-point")) return;
    const coords = clientToNormalized(event.clientX, event.clientY);
    if (!coords) return;

    if (pendingPlaceId) {
      const point = mapData?.points.find((item) => item.measurement_point_id === pendingPlaceId);
      void saveLayout(pendingPlaceId, coords.x, coords.y, coords.col, coords.row)
        .then(() => {
          setMessage(`已放置 ${point?.code ?? "点位"}，可继续拖拽微调`);
          setPendingPlaceId("");
        })
        .catch((err) => setError(err instanceof Error ? err.message : "落图失败"));
      return;
    }

    if (!editMode) return;
    setCreateDraft({
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

  function onPointPointerDown(event: ReactPointerEvent<HTMLButtonElement>, point: MapPoint) {
    event.stopPropagation();
    void loadDetail(point.measurement_point_id, runId || mapData?.production_run_id || undefined);
    if (!editMode) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = { pointId: point.measurement_point_id, pointerId: event.pointerId, moved: false };
  }

  function onPointPointerMove(event: ReactPointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId || !editMode) return;
    const coords = clientToNormalized(event.clientX, event.clientY);
    if (!coords) return;
    drag.moved = true;
    setMapData((current) => {
      if (!current) return current;
      return {
        ...current,
        points: current.points.map((point) =>
          point.measurement_point_id === drag.pointId
            ? {
                ...point,
                layout_x: coords.x,
                layout_y: coords.y,
                grid_col: coords.col,
                grid_row: coords.row,
              }
            : point,
        ),
      };
    });
  }

  async function onPointPointerUp(event: ReactPointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragRef.current = null;
    if (!editMode || !drag.moved) return;
    const coords = clientToNormalized(event.clientX, event.clientY);
    if (!coords) return;
    try {
      await saveLayout(drag.pointId, coords.x, coords.y, coords.col, coords.row);
      setMessage("点位坐标已更新");
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存坐标失败");
      await loadMap();
    }
  }

  return (
    <section className="panel body-map-panel">
      <div className="program-subheading">
        <div>
          <span className="eyebrow">车身点位图</span>
          <h3>白车身网格与质量分布</h3>
          <small>
            按测量编组映射点位；点击查看膜厚 / 色差 / 橘皮与关联刷子参数。编辑模式可拖拽、新增或从图移除（仅停用布局）。
          </small>
        </div>
        <div className="row-actions">
          <button className="button button-secondary" type="button" onClick={() => void loadMap()} disabled={loading}>
            {loading ? <LoaderCircle className="spin" /> : <RefreshCw />}
            刷新
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
        {mapData ? (
          <section className="quality-analytics-stat-grid body-map-stat-grid">
            <article>
              <span>已落图</span>
              <strong>{mapData.placed_count ?? visiblePoints.length}</strong>
              <small>当前视图 ACTIVE 布局</small>
            </article>
            <article>
              <span>编组内</span>
              <strong>{mapData.group_point_count ?? mapData.points.length}</strong>
              <small>{groupId ? "所选测量编组" : "全部质量点位"}</small>
            </article>
            <article className={(mapData.fail_count ?? 0) > 0 ? "stat-alert" : ""}>
              <span>超差（已落图）</span>
              <strong>{mapData.fail_count ?? 0}</strong>
              <small>仅统计 VERIFIED 判定</small>
            </article>
            <article>
              <span>未落图</span>
              <strong>{unplaced.length}</strong>
              <small>可进入编辑后放置</small>
            </article>
            <article className="body-map-stat-scope">
              <span>质量范围</span>
              <strong className="mono">
                {mapData.production_run_no ?? "无生产事件"}
              </strong>
              <small>{mapData.quality_scope ?? "VERIFIED"} · 自动/指定生产事件</small>
            </article>
          </section>
        ) : null}

        <div className="governance-scope-bar body-map-scope-bar">
          <div>
            <strong>工作范围</strong>
            <span>先选车型与视图，再按编组 / 生产事件过滤；着色仅基于已核验质量数据。</span>
          </div>
          <div className="governance-scope-fields body-map-scope-fields">
            <label className="form-field">
              <span>车型</span>
              <select value={vehicleModelId} onChange={(event) => setVehicleModelId(event.target.value)}>
                <option value="">请选择车型</option>
                {models.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.code} / {item.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="form-field">
              <span>车身视图</span>
              <div className="body-map-view-toggle" role="group" aria-label="车身视图">
                <button
                  type="button"
                  className={bodyView === "SIDE" ? "is-active" : ""}
                  onClick={() => setBodyView("SIDE")}
                >
                  侧视
                </button>
                <button
                  type="button"
                  className={bodyView === "TOP" ? "is-active" : ""}
                  onClick={() => setBodyView("TOP")}
                >
                  俯视
                </button>
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
              <span>放置模式：在白车身上点击目标网格，将未落图点位放到该位置。</span>
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
              <div className="body-map-stage-card">
                <div className="body-map-stage-meta">
                  <div>
                    <span className="eyebrow">{bodyView === "TOP" ? "俯视" : "侧视"}白车身</span>
                    <strong>
                      {mapData?.vehicle_model_code ?? "—"} · {mapData?.vehicle_model_name ?? "加载中"}
                    </strong>
                  </div>
                  <small className="mono">
                    网格 {gridCols}×{gridRows}
                    {editMode ? " · 编辑中" : ""}
                  </small>
                </div>
                <div
                  ref={stageRef}
                  className={`body-map-stage ${editMode || pendingPlaceId ? "is-editing" : ""}`}
                  style={{ "--grid-cols": String(gridCols), "--grid-rows": String(gridRows) } as CSSProperties}
                  onPointerDown={onStagePointerDown}
                >
                  <img
                    className="body-map-bg"
                    src={backgroundUrl}
                    alt={`${bodyView === "TOP" ? "俯视" : "侧视"}白车身`}
                    draggable={false}
                  />
                  <div className="body-map-grid" aria-hidden="true" />
                  {visiblePoints.map((point) => (
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
                      onPointerDown={(event) => onPointPointerDown(event, point)}
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
              </div>
              {editMode ? (
                <div className="body-map-hint">
                  <Plus />
                  <span>编辑模式：拖拽点位吸附到网格；点击空白格新建测量点。图上「移除」仅停用当前视图布局。</span>
                </div>
              ) : null}
              {(editMode || unplaced.length > 0) && unplaced.length ? (
                <div className="body-map-unplaced">
                  <div className="body-map-unplaced-head">
                    <strong>未落图点位</strong>
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
                          setMessage(`请在图上点击放置 ${point.code}`);
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
              {!selectedPointId ? (
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
                          const point = mapData?.points.find(
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

                  <div className="body-map-brush-block">
                    <div className="program-subheading compact">
                      <div>
                        <span className="eyebrow">喷涂关联</span>
                        <h4>刷子号与参数</h4>
                      </div>
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
                              {brush.process_stage} · 表 {brush.brush_table_no} · 重叠{" "}
                              {(brush.overlap_ratio * 100).toFixed(0)}% · 权重{" "}
                              {(brush.contribution_weight * 100).toFixed(0)}%
                              {brush.target_family
                                ? ` · ${qualityLabels[brush.target_family] ?? brush.target_family}`
                                : ""}
                              {brush.is_approved ? " · 已审批" : " · 待审批"}
                            </small>
                          </div>
                          {brush.parameters.length ? (
                            <div className="body-map-param-table">
                              {brush.parameters.map((parameter) => (
                                <div className="body-map-param-row" key={parameter.parameter_code}>
                                  <span>
                                    <strong>{parameter.parameter_name}</strong>
                                    <small className="mono">{parameter.parameter_code}</small>
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
          description="将同步写入测量点主数据，并在当前视图落图；若已选测量编组会自动绑定。"
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
              <div className="form-field">
                <span>落点</span>
                <div className="mono">
                  视图 {bodyView} · 格 ({createDraft.grid_col}, {createDraft.grid_row}) · (
                  {createDraft.layout_x.toFixed(3)}, {createDraft.layout_y.toFixed(3)})
                </div>
              </div>
            </div>
            <div className="modal-actions">
              <button className="button button-secondary" type="button" onClick={() => setCreateDraft(null)} disabled={submitting}>
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
    </section>
  );
}
