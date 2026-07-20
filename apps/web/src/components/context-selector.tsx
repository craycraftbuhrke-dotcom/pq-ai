"use client";

import { Cog, Factory, Layers, PaintBucket } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/lib/auth-context";
import { PROCESS_STAGE_LABELS } from "@/lib/display-labels";
import { useWorkspaceContext } from "@/lib/workspace-context";

type Resource = { id: string; code: string; name: string };
type FactoryModelRelation = { factory_id: string; vehicle_model_id: string };
type ModelColorRelation = { vehicle_model_id: string; color_id: string };

const COATING_SYSTEMS = [
  { id: "midcoat", label: "中涂", stages: ["MIDCOAT_EXT"] },
  { id: "basecoat", label: "色漆", stages: ["BASECOAT_1", "BASECOAT_2"] },
  { id: "clearcoat", label: "清漆", stages: ["CLEARCOAT_1", "CLEARCOAT_2"] },
] as const;

async function fetchList<T>(path: string): Promise<T[]> {
  try {
    const resp = await fetch(path, { cache: "no-store" });
    return resp.ok ? ((await resp.json()) as T[]) : [];
  } catch {
    return [];
  }
}

export function ContextSelector() {
  const { actor } = useAuth();
  const {
    factoryId,
    modelId,
    colorId,
    coating,
    stage,
    setFactoryId,
    setModelId,
    setColorId,
    setCoating,
    setStage,
  } = useWorkspaceContext();
  const [factories, setFactories] = useState<Resource[]>([]);
  const [vehicleModels, setVehicleModels] = useState<Resource[]>([]);
  const [colors, setColors] = useState<Resource[]>([]);
  const [factoryModelRelations, setFactoryModelRelations] = useState<FactoryModelRelation[]>([]);
  const [modelColorRelations, setModelColorRelations] = useState<ModelColorRelation[]>([]);

  useEffect(() => {
    void (async () => {
      const [f, m, c, fm, mc] = await Promise.all([
        fetchList<Resource>("/api/master-data/factories"),
        fetchList<Resource>("/api/master-data/vehicle-models"),
        fetchList<Resource>("/api/master-data/colors"),
        fetchList<FactoryModelRelation>("/api/master-data/factory-vehicle-models"),
        fetchList<ModelColorRelation>("/api/master-data/vehicle-model-colors"),
      ]);
      setFactories(f);
      setVehicleModels(m);
      setColors(c);
      setFactoryModelRelations(fm);
      setModelColorRelations(mc);
    })();
  }, []);

  const availableModels = useMemo(() => {
    const allowed = new Set(
      factoryModelRelations
        .filter((relation) => relation.factory_id === factoryId)
        .map((relation) => relation.vehicle_model_id),
    );
    return allowed.size ? vehicleModels.filter((item) => allowed.has(item.id)) : vehicleModels;
  }, [factoryId, factoryModelRelations, vehicleModels]);

  const availableColors = useMemo(() => {
    const allowed = new Set(
      modelColorRelations
        .filter((relation) => relation.vehicle_model_id === modelId)
        .map((relation) => relation.color_id),
    );
    return allowed.size ? colors.filter((item) => allowed.has(item.id)) : colors;
  }, [colors, modelColorRelations, modelId]);

  useEffect(() => {
    if (!factoryId && factories[0]?.id) setFactoryId(factories[0].id);
  }, [factories, factoryId, setFactoryId]);

  useEffect(() => {
    if (availableModels.length && !availableModels.some((item) => item.id === modelId)) {
      setModelId(availableModels[0].id);
    }
  }, [availableModels, modelId, setModelId]);

  useEffect(() => {
    if (availableColors.length && !availableColors.some((item) => item.id === colorId)) {
      setColorId(availableColors[0].id);
    }
  }, [availableColors, colorId, setColorId]);

  if (!actor.isAuthenticated) return null;

  const currentCoating = COATING_SYSTEMS.find((item) => item.id === coating) ?? COATING_SYSTEMS[1];
  const stageOptions = currentCoating.stages.map((code) => ({
    code,
    label: PROCESS_STAGE_LABELS[code] ?? code,
  }));

  return (
    <div className="context-selector" aria-label="当前作业范围">
      <strong className="context-title">当前范围</strong>
      <div className="context-coating-stages">
        {COATING_SYSTEMS.map((cs) => (
          <button
            key={cs.id}
            type="button"
            className={`context-chip ${coating === cs.id ? "active" : ""}`}
            onClick={() => {
              setCoating(cs.id);
              if (!(cs.stages as readonly string[]).includes(stage)) {
                setStage(cs.stages[0]);
              }
            }}
            title={cs.label}
          >
            <span className="context-chip-label">{cs.label}</span>
          </button>
        ))}
      </div>
      <span className="context-separator" />
      <div className="context-stage-selector">
        <Cog className="context-icon" aria-hidden="true" />
        <span className="context-field-label">喷涂工序</span>
        <select
          value={stageOptions.some((item) => item.code === stage) ? stage : stageOptions[0]?.code}
          onChange={(event) => setStage(event.target.value)}
          className="context-select"
          aria-label="喷涂工位"
        >
          {stageOptions.map((item) => (
            <option key={item.code} value={item.code}>
              {item.label}
            </option>
          ))}
        </select>
      </div>
      <span className="context-separator" />
      <div className="context-factory">
        <Factory className="context-icon" aria-hidden="true" />
        <span className="context-field-label">工厂</span>
        <select
          value={factoryId}
          onChange={(event) => setFactoryId(event.target.value)}
          className="context-select"
          aria-label="工厂"
        >
          {!factories.length ? <option value="">请先维护工厂资料</option> : null}
          {factories.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name || item.code}
            </option>
          ))}
        </select>
      </div>
      <span className="context-separator" />
      <div className="context-model-color">
        <Layers className="context-icon" aria-hidden="true" />
        <span className="context-field-label">车型</span>
        <select
          value={modelId}
          onChange={(event) => setModelId(event.target.value)}
          className="context-select"
          aria-label="车型"
        >
          {!availableModels.length ? <option value="">请先维护车型资料</option> : null}
          {availableModels.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name || item.code}
            </option>
          ))}
        </select>
        <PaintBucket className="context-icon" aria-hidden="true" />
        <span className="context-field-label">颜色</span>
        <select
          value={colorId}
          onChange={(event) => setColorId(event.target.value)}
          className="context-select"
          aria-label="颜色"
        >
          {!availableColors.length ? <option value="">请先维护颜色资料</option> : null}
          {availableColors.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name || item.code}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
