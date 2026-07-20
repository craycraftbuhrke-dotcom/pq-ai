/** Built-in and override 3D model assets for body-map 3D view. */

export type BodyModelBounds = {
  min_x: number;
  max_x: number;
  min_y: number;
  max_y: number;
  min_z: number;
  max_z: number;
};

export type BodyModelEntry = {
  url: string | null;
  up_axis: string;
  unit_scale: number;
  bounds?: BodyModelBounds | null;
  model_asset_key?: string | null;
  upload_id?: string | null;
  source_format?: "glb" | "stp";
  convert_engine?: string | null;
  model_code?: string | null;
};

export type BodyModelManifest = {
  version: number;
  models: Record<string, BodyModelEntry>;
};

export const EMPTY_BODY_MODEL_MANIFEST: BodyModelManifest = {
  version: 1,
  models: {},
};

const RESERVED_MODEL_KEYS = new Set(["__proto__", "constructor", "prototype"]);

export function ownModelEntry<T>(models: Record<string, T>, key: string): T | undefined {
  return Object.prototype.hasOwnProperty.call(models, key) ? models[key] : undefined;
}

/** Per-model built-in GLB paths under apps/web/public/body-models (shipped in image). */
export const MODEL_3D_ASSETS: Record<string, BodyModelEntry> = {
  ms11: {
    url: "/body-models/custom/ms11.glb",
    up_axis: "Y",
    unit_scale: 0.001,
    bounds: null,
    model_asset_key: "/body-models/custom/ms11.glb",
  },
};

export function legacyModelKey(code: string): string {
  return code.trim().toLowerCase();
}

function stableKeySuffix(value: string): string {
  let first = 0x811c9dc5;
  let second = 0x9e3779b9;
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    first = Math.imul(first ^ code, 0x01000193);
    second = Math.imul(second ^ code, 0x85ebca6b);
  }
  return `${(first >>> 0).toString(16).padStart(8, "0")}${(second >>> 0).toString(16).padStart(8, "0")}`;
}

export function normalizeModelKey(code: string): string {
  const legacy = legacyModelKey(code);
  const safe = legacy
    .normalize("NFKC")
    .replace(/[^\p{L}\p{N}_-]+/gu, "_")
    .replace(/^_+|_+$/g, "");
  if (safe && safe === legacy && safe.length <= 80 && !RESERVED_MODEL_KEYS.has(safe)) return safe;
  const prefix = (safe || "model").slice(0, 63);
  return `${prefix}_${stableKeySuffix(legacy)}`;
}

export function resolveBodyModel(
  modelCode: string,
  manifest: BodyModelManifest | null | undefined,
): BodyModelEntry {
  const custom = resolveCustomBodyModel(modelCode, manifest);
  if (custom) return custom;
  const lowered = normalizeModelKey(modelCode);
  for (const [key, entry] of Object.entries(MODEL_3D_ASSETS)) {
    if (lowered === key || (key && lowered.includes(key))) {
      return entry;
    }
  }
  return { url: null, up_axis: "Y", unit_scale: 1.0, bounds: null };
}

export function resolveCustomBodyModel(
  modelCode: string,
  manifest: BodyModelManifest | null | undefined,
): BodyModelEntry | undefined {
  const normalized = normalizeModelKey(modelCode);
  const legacy = legacyModelKey(modelCode);
  const models = manifest?.models ?? {};
  const direct = ownModelEntry(models, normalized);
  if (direct) return direct;
  const legacyEntry = legacy !== normalized ? ownModelEntry(models, legacy) : undefined;
  if (legacyEntry) return legacyEntry;
  for (const [key, entry] of Object.entries(models)) {
    if (normalized === normalizeModelKey(key)) return entry;
  }
  return undefined;
}
