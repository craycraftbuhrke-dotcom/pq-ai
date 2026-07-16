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
};

export type BodyModelManifest = {
  version: number;
  models: Record<string, BodyModelEntry>;
};

export const EMPTY_BODY_MODEL_MANIFEST: BodyModelManifest = {
  version: 1,
  models: {},
};

/** Per-model built-in GLB paths under apps/web/public/body-models. */
export const MODEL_3D_ASSETS: Record<string, BodyModelEntry> = {
  // Add built-in GLB paths here as files become available, e.g.:
  // ms11: { url: "/body-models/ms11.glb", up_axis: "Y", unit_scale: 1.0 },
};

export function normalizeModelKey(code: string): string {
  return code.trim().toLowerCase();
}

export function resolveBodyModel(
  modelCode: string,
  manifest: BodyModelManifest | null | undefined,
): BodyModelEntry {
  const lowered = normalizeModelKey(modelCode);
  const models = manifest?.models ?? {};
  for (const [key, entry] of Object.entries(models)) {
    if (lowered === key || (key && lowered.includes(key))) {
      return entry;
    }
  }
  for (const [key, entry] of Object.entries(MODEL_3D_ASSETS)) {
    if (lowered === key || (key && lowered.includes(key))) {
      return entry;
    }
  }
  return { url: null, up_axis: "Y", unit_scale: 1.0, bounds: null };
}
