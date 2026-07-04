"use client";

import { Cog, Factory, Layers, PaintBucket } from "lucide-react";
import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth-context";

type Resource = { id: string; code: string; name: string };
type CoatingSystem = { id: string; label: string; shortcut: string };
type StageInfo = { code: string; label: string };

const COATING_SYSTEMS: CoatingSystem[] = [
  { id: "midcoat", label: "中涂系统", shortcut: "MC" },
  { id: "basecoat", label: "色漆系统", shortcut: "BC" },
  { id: "clearcoat", label: "清漆系统", shortcut: "CC" },
];

const STAGES: StageInfo[] = [
  { code: "MIDCOAT_EXT", label: "中涂外喷" },
  { code: "BASECOAT_1", label: "色漆一站" },
  { code: "BASECOAT_2", label: "色漆二站" },
  { code: "CLEARCOAT_1", label: "清漆一站" },
  { code: "CLEARCOAT_2", label: "清漆二站" },
];

function getApiKey(): string {
  const match = document.cookie.match(/(?:^|;\s*)pq_api_key=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function fetchList<T>(path: string): Promise<T[]> {
  try {
    const resp = await fetch(path, { headers: { "x-api-key": getApiKey() }, cache: "no-store" });
    return resp.ok ? (resp.json() as Promise<T[]>) : [];
  } catch { return []; }
}

export function ContextSelector() {
  const { actor } = useAuth();
  const [factories, setFactories] = useState<Resource[]>([]);
  const [vehicleModels, setVehicleModels] = useState<Resource[]>([]);
  const [colors, setColors] = useState<Resource[]>([]);
  const [coating, setCoating] = useState("basecoat");
  const [stage, setStage] = useState("BASECOAT_1");
  const [factoryId, setFactoryId] = useState("");
  const [modelId, setModelId] = useState("");
  const [colorId, setColorId] = useState("");

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
      setFactoryId((prev) => prev || f[0]?.id || "");
      setModelId((prev) => prev || m[0]?.id || "");
      setColorId((prev) => prev || c[0]?.id || "");
    })();
  }, []);

  const currentCoating = COATING_SYSTEMS.find((c) => c.id === coating);
  const currentStage = STAGES.find((s) => s.code === stage);
  const currentFactory = factories.find((f) => f.id === factoryId);
  const currentModel = vehicleModels.find((m) => m.id === modelId);
  const currentColor = colors.find((c) => c.id === colorId);

  if (!actor.isAuthenticated) return null;

  return (
    <div className="context-selector">
      <div className="context-coating-stages">
        {COATING_SYSTEMS.map((cs) => (
          <button
            key={cs.id}
            className={`context-chip ${coating === cs.id ? "active" : ""}`}
            onClick={() => setCoating(cs.id)}
            title={cs.label}
          >
            <span className="context-chip-shortcut">{cs.shortcut}</span>
            <span className="context-chip-label">{cs.label}</span>
          </button>
        ))}
      </div>
      <span className="context-separator" />
      <div className="context-stage-selector">
        <Cog className="context-icon" />
        <select value={stage} onChange={(e) => setStage(e.target.value)} className="context-select">
          {STAGES.map((s) => <option key={s.code} value={s.code}>{s.label}</option>)}
        </select>
      </div>
      <span className="context-separator" />
      <div className="context-factory">
        <Factory className="context-icon" />
        <select value={factoryId} onChange={(e) => setFactoryId(e.target.value)} className="context-select">
          {factories.map((f) => <option key={f.id} value={f.id}>{f.code}</option>)}
        </select>
      </div>
      <span className="context-separator" />
      <div className="context-model-color">
        <Layers className="context-icon" />
        <select value={modelId} onChange={(e) => setModelId(e.target.value)} className="context-select">
          {vehicleModels.map((m) => <option key={m.id} value={m.id}>{m.code}</option>)}
        </select>
        <span className="context-dot">·</span>
        <PaintBucket className="context-icon" />
        <select value={colorId} onChange={(e) => setColorId(e.target.value)} className="context-select">
          {colors.map((c) => <option key={c.id} value={c.id}>{c.code}</option>)}
        </select>
      </div>
      <span className="context-separator" />
      <div className="context-summary">
        <span className="context-summary-text">
          {currentCoating?.label} · {currentStage?.label} · {currentFactory?.code ?? "—"} · {currentModel?.code ?? "—"} · {currentColor?.code ?? "—"}
        </span>
      </div>
    </div>
  );
}
