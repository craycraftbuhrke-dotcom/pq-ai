import { existsSync } from "fs";
import { mkdir, readFile, writeFile } from "fs/promises";
import path from "path";

import { NextResponse } from "next/server";

import {
  EMPTY_BODY_MODEL_MANIFEST,
  MODEL_3D_ASSETS,
  normalizeModelKey,
  resolveBodyModel,
  type BodyModelBounds,
  type BodyModelEntry,
  type BodyModelManifest,
} from "@/lib/body-map-models";

export const runtime = "nodejs";

function resolvePublicDir(): string {
  const candidates = [path.join(process.cwd(), "public"), path.join(process.cwd(), "apps", "web", "public")];
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  return candidates[0];
}

const PUBLIC_DIR = resolvePublicDir();
const MANIFEST_PATH = path.join(PUBLIC_DIR, "body-models", "view-models.json");
const CUSTOM_DIR = path.join(PUBLIC_DIR, "body-models", "custom");

const ALLOWED_MIME: Record<string, string> = {
  "model/gltf-binary": ".glb",
  "model/gltf+json": ".gltf",
  "application/octet-stream": ".glb",
};

async function readManifest(): Promise<BodyModelManifest> {
  try {
    const raw = await readFile(MANIFEST_PATH, "utf-8");
    const parsed = JSON.parse(raw) as BodyModelManifest;
    if (!parsed || typeof parsed !== "object") return { ...EMPTY_BODY_MODEL_MANIFEST, models: {} };
    return {
      version: typeof parsed.version === "number" ? parsed.version : 1,
      models: parsed.models && typeof parsed.models === "object" ? parsed.models : {},
    };
  } catch {
    return { ...EMPTY_BODY_MODEL_MANIFEST, models: {} };
  }
}

async function writeManifest(manifest: BodyModelManifest): Promise<void> {
  await mkdir(path.dirname(MANIFEST_PATH), { recursive: true });
  await writeFile(MANIFEST_PATH, `${JSON.stringify(manifest, null, 2)}\n`, "utf-8");
}

function publicUrlForFile(absPath: string): string {
  const relative = path.relative(PUBLIC_DIR, absPath).split(path.sep).join("/");
  return `/${relative}`;
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const modelCode = (searchParams.get("modelCode") ?? "").trim();
  if (!modelCode) {
    return NextResponse.json({ error: "缺少 modelCode" }, { status: 400 });
  }
  const manifest = await readManifest();
  const key = normalizeModelKey(modelCode);
  const entry = resolveBodyModel(modelCode, manifest);
  return NextResponse.json({
    model_code: modelCode,
    model_key: key,
    entry,
    source: manifest.models[key] ? "custom" : MODEL_3D_ASSETS[key] ? "builtin" : "none",
    manifest_path: "/body-models/view-models.json",
  });
}

export async function POST(request: Request) {
  const form = await request.formData();
  const modelCode = String(form.get("modelCode") ?? "").trim();
  const action = String(form.get("action") ?? "upload").trim().toLowerCase();
  const file = form.get("file");

  if (!modelCode) {
    return NextResponse.json({ error: "缺少 modelCode" }, { status: 400 });
  }
  const modelKey = normalizeModelKey(modelCode);
  const manifest = await readManifest();

  try {
    if (action === "reset") {
      delete manifest.models[modelKey];
      if (!Object.keys(manifest.models).length) {
        /* keep manifest but empty models is fine */
      }
      await writeManifest(manifest);
      return NextResponse.json({
        ok: true,
        action: "reset",
        model_code: modelCode,
        entry: MODEL_3D_ASSETS[modelKey] ?? { url: null, up_axis: "Y", unit_scale: 1.0 },
        source: MODEL_3D_ASSETS[modelKey] ? "builtin" : "none",
      });
    }

    if (!(file instanceof File)) {
      return NextResponse.json({ error: "请上传 GLB/GLTF 文件" }, { status: 400 });
    }
    const mime = (file.type || "").toLowerCase();
    const ext = ALLOWED_MIME[mime];
    if (!ext) {
      return NextResponse.json({ error: "仅支持 GLB / GLTF" }, { status: 400 });
    }
    if (file.size > 80 * 1024 * 1024) {
      return NextResponse.json({ error: "模型文件不能超过 80MB" }, { status: 400 });
    }

    await mkdir(CUSTOM_DIR, { recursive: true });
    const outAbs = path.join(CUSTOM_DIR, `${modelKey}${ext}`);
    await writeFile(outAbs, Buffer.from(await file.arrayBuffer()));
    const storedUrl = publicUrlForFile(outAbs);

    const boundsRaw = String(form.get("bounds") ?? "").trim();
    let bounds: BodyModelBounds | null = null;
    if (boundsRaw) {
      try {
        bounds = JSON.parse(boundsRaw) as BodyModelBounds;
      } catch {
        bounds = null;
      }
    }
    const upAxis = String(form.get("upAxis") ?? "Y").trim() || "Y";
    const unitScaleRaw = parseFloat(String(form.get("unitScale") ?? "1"));
    const unitScale = Number.isFinite(unitScaleRaw) ? unitScaleRaw : 1.0;

    const entry: BodyModelEntry = {
      url: storedUrl,
      up_axis: upAxis,
      unit_scale: unitScale,
      bounds,
      model_asset_key: storedUrl,
    };
    manifest.models[modelKey] = entry;
    await writeManifest(manifest);

    return NextResponse.json({
      ok: true,
      action: "upload",
      model_code: modelCode,
      entry,
      source: "custom",
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "模型保存失败" },
      { status: 500 },
    );
  }
}
