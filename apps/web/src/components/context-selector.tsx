"use client";

import { Cog, Factory, Layers, PaintBucket } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/lib/auth-context";
import { PROCESS_STAGE_LABELS } from "@/lib/display-labels";
import { useWorkspaceContext } from "@/lib/workspace-context";

type Resource = { id: string; code: string; name: string };

const COATING_SYSTEMS = [
  { id: "midcoat", label: "中涂", stages: ["MIDCOAT_EXT"] },
  { id: "basecoat", label: "色漆", stages: ["BASECOAT_1", "BASECOAT_2"] },
  { id: "clearcoat", label: "清漆", stages: ["CLEARCOAT_1", "CLEARCOAT_2"] },
] as const;

function getApiKey(): string {
  const match = document.cookie.match(/(?:^|;\s*)pq_api_key=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function fetchList<T>(path: string): Promise<T[]> {
  try {
    const resp = await fetch(path, { headers: { "x-api-key": getApiKey() }, cache: "no-store" });
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
  const defaultsApplied = useRef(false);

  useEffect(() => {
    void (async () => {
      const [f, m, c] = await Promise.all([
        fetchList<Resource>("/api/master-data/factories"),
        fetchList<Resource>("/api/master-data/vehicle-models"),
        fetchList<Resource>("/api/master-data/colors"),
      ]);
      setFactories(f);
      setVehicleModels(m);
      setColors(c);
    })();
  }, []);

  useEffect(() => {
    if (defaultsApplied.current) return;
    if (!factories.length && !vehicleModels.length && !colors.length) return;
    defaultsApplied.current = true;
    if (!factoryId && factories[0]?.id) setFactoryId(factories[0].id);
    if (!modelId && vehicleModels[0]?.id) setModelId(vehicleModels[0].id);
    if (!colorId && colors[0]?.id) setColorId(colors[0].id);
  }, [colorId, colors, factories, factoryId, modelId, setColorId, setFactoryId, setModelId, vehicleModels]);

  if (!actor.isAuthenticated) return null;

  const currentCoating = COATING_SYSTEMS.find((item) => item.id === coating) ?? COATING_SYSTEMS[1];
  const stageOptions = currentCoating.stages.map((code) => ({
    code,
    label: PROCESS_STAGE_LABELS[code] ?? code,
  }));

  return (
    <div className="context-selector" aria-label="当前作业范围">
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
        <select
          value={factoryId}
          onChange={(event) => setFactoryId(event.target.value)}
          className="context-select"
          aria-label="工厂"
        >
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
        <select
          value={modelId}
          onChange={(event) => setModelId(event.target.value)}
          className="context-select"
          aria-label="车型"
        >
          {vehicleModels.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name || item.code}
            </option>
          ))}
        </select>
        <span className="context-dot">·</span>
        <PaintBucket className="context-icon" aria-hidden="true" />
        <select
          value={colorId}
          onChange={(event) => setColorId(event.target.value)}
          className="context-select"
          aria-label="颜色"
        >
          {colors.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name || item.code}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
