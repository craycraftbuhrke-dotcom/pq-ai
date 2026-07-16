"use client";

import {
  Box,
  LoaderCircle,
  MapPinned,
  Pencil,
  RefreshCw,
  Upload,
} from "lucide-react";
import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { BodyMapModelEditor } from "@/components/body-map-model-editor";
import { ModalShell } from "@/components/modal-shell";
import { useWorkspaceContext } from "@/lib/workspace-context";

type Resource = { id: string; code: string; name: string };
type MeasurementGroup = Resource & { vehicle_model_id: string; quality_type: string };
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
  metric_code: string | null;
  metric_name: string | null;
  value: number | null;
  unit: string | null;
  judgement: string | null;
  reliability_status: string | null;
};

type Point3D = {
  measurement_point_id: string;
  layout_3d_id: string | null;
  code: string;
  name: string;
  part_id: string;
  part_code: string | null;
  part_name: string | null;
  region: string | null;
  quality_types: string[];
  pos_x: number | null;
  pos_y: number | null;
  pos_z: number | null;
  in_group: boolean;
  has_2d_only: boolean;
  quality_summaries: QualitySummary[];
  risk_score: number;
};

type Scene3D = {
  vehicle_model_id: string;
  vehicle_model_code: string;
  vehicle_model_name: string;
  model_url: string | null;
  model_asset_key: string | null;
  up_axis: string;
  unit_scale: number;
  bounds: Record<string, number>;
  measurement_group_id: string | null;
  production_run_id: string | null;
  production_run_no: string | null;
  quality_scope: string;
  placed_count: number;
  group_point_count: number;
  fail_count: number;
  points: Point3D[];
};

type PointDetail = {
  measurement_point_id: string;
  code: string;
  name: string;
  part_code: string | null;
  part_name: string | null;
  region: string | null;
  quality_types: string[];
  quality_summaries: QualitySummary[];
  brush_contributions: BrushContribution[];
};

type BrushContribution = {
  brush_id: string;
  brush_no: string;
  brush_table_no: string;
  process_stage: string;
  coating_system: string;
  overlap_ratio: number;
  contribution_weight: number;
  contribution_source: string;
  is_approved: boolean;
  target_family: string | null;
  parameters: BrushParameter[];
};

type BrushParameter = {
  parameter_code: string;
  parameter_name: string;
  configured_value: number | null;
  actual_value: number | null;
  unit: string;
};

type OverlayMode = "RISK" | "THICKNESS" | "COLOR_DIFFERENCE" | "ORANGE_PEEL";

const QUALITY_LABELS: Record<string, string> = {
  ORANGE_PEEL: "橘皮",
  COLOR_DIFFERENCE: "色差",
  THICKNESS: "膜厚",
};

const COATING_LABELS: Record<string, string> = {
  MIDCOAT: "中涂",
  BASECOAT: "色漆",
  CLEARCOAT: "清漆",
};

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { error?: string; detail?: string };
    throw new Error(payload.error ?? payload.detail ?? `请求失败（${response.status}）`);
  }
  return (await response.json()) as T;
}

function riskColor(score: number, judgement?: string | null): string {
  if (judgement === "FAIL" || score >= 40) return "#ef4444";
  if (judgement === "INVALID" || score >= 25) return "#f59e0b";
  if (judgement === "NO_STANDARD" || score >= 10) return "#f59e0b";
  if (judgement === "PASS") return "#14b8a6";
  return "#94a3b8";
}

function pointColor(point: Point3D, overlay: OverlayMode): string {
  if (overlay === "RISK") {
    const primary =
      point.quality_summaries.find((s) => s.judgement === "FAIL") ??
      point.quality_summaries.find((s) => s.judgement === "PASS") ??
      point.quality_summaries.find((s) => s.value != null) ??
      point.quality_summaries[0];
    return riskColor(point.risk_score, primary?.judgement);
  }
  const summary = point.quality_summaries.find((s) => s.quality_type === overlay);
  if (!summary) return "#94a3b8";
  if (summary.judgement === "FAIL") return "#ef4444";
  if (summary.judgement === "INVALID") return "#f59e0b";
  if (summary.judgement === "PASS") return "#14b8a6";
  if (summary.judgement === "NO_STANDARD") return "#f59e0b";
  return "#94a3b8";
}

function formatValue(value: number | null | undefined, unit?: string | null): string {
  if (value == null) return "—";
  const text = Number.isInteger(value) ? String(value) : value.toFixed(2);
  return unit ? `${text} ${unit}` : text;
}

// --- 3D scene (dynamically imported three.js to keep initial bundle small) ---

function Scene3DInner({
  scene,
  editMode,
  overlayMode,
  selectedPointId,
  onPointClick,
  onSurfacePick,
}: {
  scene: Scene3D;
  editMode: boolean;
  overlayMode: OverlayMode;
  selectedPointId: string;
  onPointClick: (pointId: string) => void;
  onSurfacePick: (pos: [number, number, number], normal: [number, number, number] | null) => void;
}) {
  const [Canvas, setCanvas] = useState<null | typeof import("@react-three/fiber").Canvas>(null);
  const [OrbitControls, setOrbitControls] = useState<null | typeof import("@react-three/drei").OrbitControls>(null);
  const [Environment, setEnvironment] = useState<null | typeof import("@react-three/drei").Environment>(null);
  const [Grid, setGrid] = useState<null | typeof import("@react-three/drei").Grid>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const fiber = await import("@react-three/fiber");
      const drei = await import("@react-three/drei");
      if (!cancelled) {
        setCanvas(() => fiber.Canvas);
        setOrbitControls(() => drei.OrbitControls);
        setEnvironment(() => drei.Environment);
        setGrid(() => drei.Grid);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const bounds = scene.bounds;
  const center = useMemo<[number, number, number]>(() => {
    if (!bounds || !bounds.min_x) return [0, 0.8, 0];
    return [
      (bounds.min_x + bounds.max_x) / 2,
      (bounds.min_y + bounds.max_y) / 2,
      (bounds.min_z + bounds.max_z) / 2,
    ];
  }, [bounds]);

  if (!Canvas) {
    return (
      <div className="body-map-3d-loading">
        <LoaderCircle className="spin" /> 正在加载 3D 渲染引擎…
      </div>
    );
  }

  return (
    <Canvas
      camera={{ position: [4, 3, 5], fov: 45 }}
      style={{ height: "100%", width: "100%", background: "#1a1a2e" }}
      onPointerMissed={() => {}}
    >
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 10, 5]} intensity={1.2} castShadow />
      <directionalLight position={[-5, 5, -5]} intensity={0.4} />

      {Environment ? <Environment preset="warehouse" /> : null}

      {Grid ? (
        <Grid
          args={[10, 10]}
          position={[center[0], bounds?.min_y ?? 0, center[2]]}
          cellColor="#3a3a5e"
          sectionColor="#5a5a8e"
          infiniteGrid
          fadeDistance={15}
        />
      ) : null}

      {scene.model_url ? (
        <Suspense fallback={null}>
          <ModelMesh
            url={scene.model_url}
            onSurfacePick={editMode ? onSurfacePick : undefined}
          />
        </Suspense>
      ) : (
        <PlaceholderBody center={center} onSurfacePick={editMode ? onSurfacePick : undefined} />
      )}

      {scene.points
        .filter((p) => p.pos_x != null)
        .map((point) => (
          <PointMarker
            key={point.measurement_point_id}
            position={[point.pos_x!, point.pos_y!, point.pos_z!]}
            color={pointColor(point, overlayMode)}
            label={point.code}
            selected={selectedPointId === point.measurement_point_id}
            onClick={() => onPointClick(point.measurement_point_id)}
          />
        ))}

      {OrbitControls ? <OrbitControls makeDefault enableDamping /> : null}
    </Canvas>
  );
}

function ModelMesh({
  url,
  onSurfacePick,
}: {
  url: string;
  onSurfacePick?: (pos: [number, number, number], normal: [number, number, number] | null) => void;
}) {
  const [geometry, setGeometry] = useState<import("three").BufferGeometry | null>(null);
  const meshRef = useRef<import("three").Mesh>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const THREE = await import("three");
      const { GLTFLoader } = await import("three/examples/jsm/loaders/GLTFLoader.js");
      const loader = new GLTFLoader();
      loader.load(
        url,
        (gltf) => {
          if (cancelled) return;
          gltf.scene.traverse((child) => {
            if ((child as import("three").Mesh).isMesh) {
              const mesh = child as import("three").Mesh;
              setGeometry(mesh.geometry);
            }
          });
        },
        undefined,
        (err) => console.error("GLB load error:", err),
      );
    })();
    return () => {
      cancelled = true;
    };
  }, [url]);

  if (!geometry) return null;

  return (
    <mesh
      ref={meshRef as never}
      geometry={geometry}
      onPointerDown={(e) => {
        if (!onSurfacePick) return;
        e.stopPropagation();
        const point = e.point;
        const normal = e.face?.normal
          ? ([e.face.normal.x, e.face.normal.y, e.face.normal.z] as [number, number, number])
          : null;
        onSurfacePick([point.x, point.y, point.z], normal);
      }}
    >
      <meshStandardMaterial color="#8a8a9a" metalness={0.3} roughness={0.7} />
    </mesh>
  );
}

function PlaceholderBody({
  center,
  onSurfacePick,
}: {
  center: [number, number, number];
  onSurfacePick?: (pos: [number, number, number], normal: [number, number, number] | null) => void;
}) {
  return (
    <mesh
      position={center}
      onPointerDown={(e) => {
        if (!onSurfacePick) return;
        e.stopPropagation();
        onSurfacePick([e.point.x, e.point.y, e.point.z], null);
      }}
    >
      <boxGeometry args={[4, 1.4, 1.8]} />
      <meshStandardMaterial color="#6a6a7a" metalness={0.2} roughness={0.8} wireframe={false} />
    </mesh>
  );
}

function PointMarker({
  position,
  color,
  label,
  selected,
  onClick,
}: {
  position: [number, number, number];
  color: string;
  label: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <group position={position}>
      <mesh
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
      >
        <sphereGeometry args={[selected ? 0.06 : 0.04, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={selected ? 0.6 : 0.3}
        />
      </mesh>
      {selected ? (
        <mesh position={[0, 0.12, 0]}>
          <sphereGeometry args={[0.02, 8, 8]} />
          <meshBasicMaterial color={color} />
        </mesh>
      ) : null}
    </group>
  );
}

// --- Main component ---

export function BodyPointMap3D() {
  const { modelId, factoryId, colorId } = useWorkspaceContext();
  const [models, setModels] = useState<Resource[]>([]);
  const [groups, setGroups] = useState<MeasurementGroup[]>([]);
  const [runs, setRuns] = useState<ProductionRun[]>([]);
  const [vehicleModelId, setVehicleModelId] = useState(modelId || "");
  const [groupId, setGroupId] = useState("");
  const [runId, setRunId] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [modelEditorOpen, setModelEditorOpen] = useState(false);
  const [overlayMode, setOverlayMode] = useState<OverlayMode>("RISK");
  const [scene, setScene] = useState<Scene3D | null>(null);
  const [detail, setDetail] = useState<PointDetail | null>(null);
  const [selectedPointId, setSelectedPointId] = useState("");
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pendingPick, setPendingPick] = useState<{ pos: [number, number, number]; normal: [number, number, number] | null } | null>(null);

  const filteredGroups = useMemo(
    () => groups.filter((g) => !vehicleModelId || g.vehicle_model_id === vehicleModelId),
    [groups, vehicleModelId],
  );

  const filteredRuns = useMemo(
    () =>
      runs.filter(
        (r) =>
          (!vehicleModelId || r.vehicle_model_id === vehicleModelId) &&
          (!factoryId || !r.factory_id || r.factory_id === factoryId) &&
          (!colorId || !r.color_id || r.color_id === colorId),
      ),
    [runs, vehicleModelId, factoryId, colorId],
  );

  const unplaced = useMemo(
    () => (scene?.points ?? []).filter((p) => p.pos_x == null),
    [scene],
  );

  const loadRefs = useCallback(async () => {
    const [nextModels, nextGroups, nextRuns] = await Promise.all([
      request<Resource[]>("/api/master-data/vehicle-models"),
      request<MeasurementGroup[]>("/api/master-data/measurement-groups"),
      request<ProductionRun[]>("/api/process/production-runs"),
    ]);
    setModels(nextModels);
    setGroups(nextGroups);
    setRuns(nextRuns);
    setVehicleModelId((cur) => cur || modelId || nextModels[0]?.id || "");
  }, [modelId]);

  const loadScene = useCallback(async () => {
    if (!vehicleModelId) {
      setScene(null);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ vehicle_model_id: vehicleModelId });
      if (groupId) params.set("measurement_group_id", groupId);
      if (runId) params.set("production_run_id", runId);
      const payload = await request<Scene3D>(`/api/quality/body-map/3d-scene?${params}`);
      setScene(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载 3D 场景失败");
      setScene(null);
    } finally {
      setLoading(false);
    }
  }, [vehicleModelId, groupId, runId]);

  const loadDetail = useCallback(
    async (pointId: string) => {
      setSelectedPointId(pointId);
      setDetailLoading(true);
      try {
        const params = new URLSearchParams();
        if (runId) params.set("production_run_id", runId);
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
    void loadScene();
  }, [loadScene]);

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
    setPendingPick(null);
  }, [vehicleModelId]);

  async function handleSurfacePick(pos: [number, number, number], normal: [number, number, number] | null) {
    if (!editMode) return;
    setPendingPick({ pos, normal });
    setMessage(`拾取坐标 (${pos[0].toFixed(2)}, ${pos[1].toFixed(2)}, ${pos[2].toFixed(2)}) — 选择左侧未落图点位绑定`);
  }

  async function savePoint3D(pointId: string, pos: [number, number, number], normal: [number, number, number] | null) {
    setError("");
    try {
      await request(`/api/quality/body-map/3d-layouts/${pointId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pos_x: pos[0],
          pos_y: pos[1],
          pos_z: pos[2],
          normal_x: normal?.[0] ?? null,
          normal_y: normal?.[1] ?? null,
          normal_z: normal?.[2] ?? null,
          project_to_2d: true,
        }),
      });
      setMessage("点位已保存并同步四视图");
      setPendingPick(null);
      await loadScene();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存 3D 点位失败");
    }
  }

  return (
    <section className="panel body-map-3d-panel">
      <div className="program-subheading">
        <div>
          <span className="eyebrow">3D 车身</span>
          <h3>三维数模与测量点位</h3>
          <small>加载 GLB 数模，在车身表面拾取落点；保存后自动投影更新四视图 2D 布局。</small>
        </div>
        <div className="row-actions">
          <button className="button button-secondary" type="button" onClick={() => void loadScene()} disabled={loading}>
            {loading ? <LoaderCircle className="spin" /> : <RefreshCw />}
            刷新
          </button>
          <button
            className="button button-secondary"
            type="button"
            disabled={!vehicleModelId}
            onClick={() => setModelEditorOpen(true)}
          >
            <Upload />
            数模管理
          </button>
          <button
            className={`button ${editMode ? "button-primary" : "button-secondary"}`}
            type="button"
            onClick={() => {
              setEditMode((v) => !v);
              setPendingPick(null);
            }}
          >
            <Pencil />
            {editMode ? "退出编辑" : "编辑落点"}
          </button>
        </div>
      </div>

      <div className="body-map-3d-shell">
        <div className="governance-scope-bar body-map-3d-scope-bar">
          <div className="governance-scope-fields body-map-3d-scope-fields">
            <label className="form-field">
              <span>车型</span>
              <select value={vehicleModelId} onChange={(e) => setVehicleModelId(e.target.value)}>
                <option value="">请选择车型</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>{m.code} / {m.name}</option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>测量编组</span>
              <select value={groupId} onChange={(e) => setGroupId(e.target.value)}>
                <option value="">全部点位</option>
                {filteredGroups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.code} / {g.name}
                    {g.quality_type ? ` · ${QUALITY_LABELS[g.quality_type] ?? g.quality_type}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>生产事件</span>
              <select value={runId} onChange={(e) => setRunId(e.target.value)}>
                <option value="">最新生产事件（自动）</option>
                {filteredRuns.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.run_no}{r.body_no ? ` · ${r.body_no}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>着色</span>
              <select value={overlayMode} onChange={(e) => setOverlayMode(e.target.value as OverlayMode)}>
                <option value="RISK">综合风险</option>
                <option value="THICKNESS">膜厚</option>
                <option value="COLOR_DIFFERENCE">色差</option>
                <option value="ORANGE_PEEL">橘皮</option>
              </select>
            </label>
          </div>
        </div>

        {scene ? (
          <section className="quality-analytics-stat-grid body-map-stat-grid">
            <article>
              <span>已落点</span>
              <strong>{scene.placed_count}</strong>
              <small>3D 世界坐标</small>
            </article>
            <article>
              <span>编组内</span>
              <strong>{scene.group_point_count}</strong>
              <small>{groupId ? "所选编组" : "全部点位"}</small>
            </article>
            <article className={scene.fail_count > 0 ? "stat-alert" : ""}>
              <span>超差</span>
              <strong>{scene.fail_count}</strong>
              <small>仅统计 VERIFIED 判定</small>
            </article>
            <article>
              <span>未落点</span>
              <strong>{unplaced.length}</strong>
              <small>需在 3D 编辑模式落点</small>
            </article>
          </section>
        ) : null}

        {error ? <div className="form-error">{error}</div> : null}
        {message ? <div className="form-success">{message}</div> : null}

        {!vehicleModelId ? (
          <div className="program-empty large-empty body-map-3d-empty">
            <Box />
            请先选择车型以加载 3D 数模。
          </div>
        ) : (
          <div className="body-map-3d-layout">
            <div className="body-map-3d-canvas-wrap">
              {scene ? (
                <Scene3DInner
                  scene={scene}
                  editMode={editMode}
                  overlayMode={overlayMode}
                  selectedPointId={selectedPointId}
                  onPointClick={(pid) => void loadDetail(pid)}
                  onSurfacePick={handleSurfacePick}
                />
              ) : loading ? (
                <div className="body-map-3d-loading"><LoaderCircle className="spin" /> 加载中…</div>
              ) : (
                <div className="body-map-3d-loading">无数据</div>
              )}
            </div>

            <aside className="body-map-3d-sidebar">
              {pendingPick ? (
                <div className="body-map-3d-pick-panel">
                  <div className="body-map-3d-pick-head">
                    <MapPinned />
                    <strong>拾取坐标待绑定</strong>
                  </div>
                  <p className="mono">
                    ({pendingPick.pos[0].toFixed(2)}, {pendingPick.pos[1].toFixed(2)}, {pendingPick.pos[2].toFixed(2)})
                  </p>
                  <div className="body-map-3d-pick-list">
                    {unplaced.map((p) => (
                      <button
                        key={p.measurement_point_id}
                        className="program-list-item"
                        type="button"
                        onClick={() => void savePoint3D(p.measurement_point_id, pendingPick.pos, pendingPick.normal)}
                      >
                        <div>
                          <strong>{p.code}</strong>
                          <span>{p.name}</span>
                        </div>
                        <MapPinned />
                      </button>
                    ))}
                    {!unplaced.length ? <small className="muted">没有未落图点位</small> : null}
                  </div>
                  <button className="button button-secondary" type="button" onClick={() => setPendingPick(null)}>
                    取消
                  </button>
                </div>
              ) : null}

              {detailLoading ? (
                <div className="body-map-3d-detail-loading"><LoaderCircle className="spin" /> 加载点位详情…</div>
              ) : detail ? (
                <div className="body-map-3d-detail">
                  <div className="body-map-detail-head">
                    <div>
                      <strong>{detail.code}</strong>
                      <span>{detail.name}</span>
                      <small>{[detail.part_code, detail.part_name, detail.region].filter(Boolean).join(" · ") || "—"}</small>
                    </div>
                  </div>
                  <div className="body-map-quality-grid">
                    {detail.quality_summaries.map((s) => (
                      <div key={s.quality_type} className="body-map-quality-card">
                        <span>{QUALITY_LABELS[s.quality_type] ?? s.quality_type}</span>
                        <strong className={`judgement judgement-${(s.judgement ?? "").toLowerCase()}`}>
                          {formatValue(s.value, s.unit)}
                        </strong>
                        <small>{s.judgement ?? "—"}</small>
                      </div>
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
                      <div className="program-empty">暂无点位贡献</div>
                    ) : (
                      detail.brush_contributions.map((brush) => (
                        <div className="body-map-brush-card" key={brush.brush_id}>
                          <div className="body-map-brush-head">
                            <div className="body-map-brush-title">
                              <strong>
                                {COATING_LABELS[brush.coating_system] ?? brush.coating_system} · {brush.brush_no}
                              </strong>
                              <span className={`status-badge ${brush.contribution_source === "GOVERNED" ? "" : "status-muted"}`}>
                                {brush.contribution_source === "GOVERNED" ? "治理贡献" : "遗留贡献"}
                              </span>
                            </div>
                            <small>
                              {brush.process_stage} · 表 {brush.brush_table_no} · 重叠{" "}
                              {(brush.overlap_ratio * 100).toFixed(0)}% · 权重{" "}
                              {(brush.contribution_weight * 100).toFixed(0)}%
                              {brush.target_family ? ` · ${QUALITY_LABELS[brush.target_family] ?? brush.target_family}` : ""}
                              {brush.is_approved ? " · 已审批" : " · 待审批"}
                            </small>
                          </div>
                          {brush.parameters.length ? (
                            <div className="body-map-param-table">
                              {brush.parameters.map((param) => (
                                <div className="body-map-param-row" key={param.parameter_code}>
                                  <span>
                                    <strong>{param.parameter_name}</strong>
                                    <small className="mono">{param.parameter_code}</small>
                                  </span>
                                  <span className="mono"><em>设定</em> {formatValue(param.configured_value, param.unit)}</span>
                                  <span className="mono"><em>实绩</em> {formatValue(param.actual_value, param.unit)}</span>
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
                </div>
              ) : (
                <div className="program-empty body-map-detail-empty">
                  点击 3D 车身上的点位标记查看质量与刷子参数。
                </div>
              )}
            </aside>
          </div>
        )}
      </div>

      <BodyMapModelEditor
        open={modelEditorOpen}
        modelCode={scene?.vehicle_model_code ?? ""}
        modelName={scene?.vehicle_model_name}
        onClose={() => setModelEditorOpen(false)}
        onChanged={() => void loadScene()}
      />
    </section>
  );
}
