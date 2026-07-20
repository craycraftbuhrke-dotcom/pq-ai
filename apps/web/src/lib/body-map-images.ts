/** Built-in body-map backgrounds under apps/web/public, plus override manifest helpers. */

import { legacyModelKey, normalizeModelKey, ownModelEntry } from "@/lib/body-map-models";

export type BodyMapView = "RIGHT" | "LEFT" | "TOP" | "REAR";

export const BODY_MAP_VIEWS: BodyMapView[] = ["RIGHT", "LEFT", "TOP", "REAR"];

export const BODY_MAP_VIEW_LABELS: Record<BodyMapView, string> = {
  RIGHT: "右侧视图",
  LEFT: "左侧视图",
  TOP: "俯视图",
  REAR: "后视图",
};

export const DEFAULT_BODY_MAP_IMAGES: Record<BodyMapView, string> = {
  RIGHT: "/body-maps/side.jpg",
  LEFT: "/body-maps/side-left.jpg",
  TOP: "/body-maps/top.jpg",
  REAR: "/ms11_back.jpg",
};

/** Per-model defaults (matched by vehicle_model.code, case-insensitive / substring). */
export const MODEL_BODY_MAP_IMAGES: Record<string, Partial<Record<BodyMapView, string>>> = {
  kunlun: {
    RIGHT: "/kunlun_rightside.jpg",
    LEFT: "/kunlun_leftside.jpg",
    TOP: "/kunlun_top.jpg",
    REAR: "/kunlun_trunk.jpg",
  },
  昆仑: {
    RIGHT: "/kunlun_rightside.jpg",
    LEFT: "/kunlun_leftside.jpg",
    TOP: "/kunlun_top.jpg",
    REAR: "/kunlun_trunk.jpg",
  },
  ms11: {
    RIGHT: "/ms11_rightside.jpg",
    LEFT: "/ms11_leftside.jpg",
    TOP: "/body-maps/top.jpg",
    REAR: "/ms11_back.jpg",
  },
};

export type BodyMapImageManifest = {
  version: number;
  models: Record<string, Partial<Record<BodyMapView, string>>>;
};

export const EMPTY_BODY_MAP_IMAGE_MANIFEST: BodyMapImageManifest = {
  version: 1,
  models: {},
};

export function normalizeModelImageKey(code: string): string {
  return normalizeModelKey(code);
}

export function builtinBodyMapImage(modelCode: string, view: BodyMapView): string {
  const lowered = normalizeModelImageKey(modelCode);
  for (const [key, images] of Object.entries(MODEL_BODY_MAP_IMAGES)) {
    const needle = key.toLowerCase();
    if (lowered === needle || (needle && lowered.includes(needle))) {
      return images[view] ?? DEFAULT_BODY_MAP_IMAGES[view];
    }
  }
  return DEFAULT_BODY_MAP_IMAGES[view];
}

export function resolveBodyMapImage(
  modelCode: string,
  view: BodyMapView,
  manifest: BodyMapImageManifest | null | undefined,
): string {
  const lowered = normalizeModelImageKey(modelCode);
  const legacy = legacyModelKey(modelCode);
  const models = manifest?.models ?? {};
  const direct =
    ownModelEntry(models, lowered) ??
    (legacy !== lowered ? ownModelEntry(models, legacy) : undefined);
  if (direct?.[view]) return direct[view]!;
  for (const [key, images] of Object.entries(models)) {
    if (lowered === key || (key && lowered.includes(key))) {
      const override = images?.[view];
      if (override) return override;
    }
  }
  return builtinBodyMapImage(modelCode, view);
}

export function withCacheBust(url: string, version?: string | number | null): string {
  if (!version) return url;
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}v=${encodeURIComponent(String(version))}`;
}
