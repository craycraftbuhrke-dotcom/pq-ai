import { execFile } from "child_process";
import { existsSync } from "fs";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "fs/promises";
import os from "os";
import path from "path";
import { promisify } from "util";

import { NextResponse } from "next/server";

import { apiRequestHeaders } from "@/lib/auth-data";
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
export const maxDuration = 600;

const execFileAsync = promisify(execFile);

function resolvePublicDir(): string {
  const candidates = [path.join(process.cwd(), "public"), path.join(process.cwd(), "apps", "web", "public")];
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  return candidates[0];
}

function resolveRepoRoot(): string {
  const candidates = [process.cwd(), path.join(process.cwd(), "..", "..")];
  for (const candidate of candidates) {
    if (existsSync(path.join(candidate, "scripts", "stp_to_glb.py"))) return candidate;
  }
  return process.cwd();
}

const PUBLIC_DIR = resolvePublicDir();
const MANIFEST_PATH = path.join(PUBLIC_DIR, "body-models", "view-models.json");
const CUSTOM_DIR = path.join(PUBLIC_DIR, "body-models", "custom");

const STP_DEFAULT_UNIT_SCALE = 0.001;

const GLB_MIME: Record<string, string> = {
  "model/gltf-binary": ".glb",
  "model/gltf+json": ".gltf",
  "application/octet-stream": ".glb",
};

function fileExtension(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx).toLowerCase() : "";
}

function isStpFile(file: File): boolean {
  const ext = fileExtension(file.name);
  return ext === ".stp" || ext === ".step";
}

function isGlbFile(file: File): boolean {
  const ext = fileExtension(file.name);
  if (ext === ".glb" || ext === ".gltf") return true;
  return Boolean(GLB_MIME[(file.type || "").toLowerCase()]);
}

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

function detailFromApiError(payload: unknown): string {
  if (!payload || typeof payload !== "object") return "STEP 转换失败";
  const detail = (payload as { detail?: unknown; error?: unknown }).detail
    ?? (payload as { error?: unknown }).error;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return JSON.stringify(detail);
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return "STEP 转换失败";
}

async function convertViaBackend(request: Request, file: File): Promise<Buffer> {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    throw new Error("后端 API 地址未配置，无法转换 STEP");
  }

  const form = new FormData();
  form.set("file", file, file.name);

  const response = await fetch(`${apiUrl.replace(/\/$/, "")}/quality/body-map/convert-stp`, {
    method: "POST",
    headers: await apiRequestHeaders(request),
    body: form,
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const message = detailFromApiError(payload);
    const err = new Error(message) as Error & { status?: number };
    err.status = response.status;
    throw err;
  }

  const bytes = Buffer.from(await response.arrayBuffer());
  if (!bytes.length) throw new Error("后端转换结果为空");
  return bytes;
}

async function convertViaLocalScript(file: File): Promise<Buffer> {
  const script = path.join(resolveRepoRoot(), "scripts", "stp_to_glb.py");
  if (!existsSync(script)) {
    throw new Error("本地未找到 scripts/stp_to_glb.py，无法离线转换 STEP");
  }

  const tmpDir = await mkdtemp(path.join(os.tmpdir(), "pqai-stp-"));
  const ext = fileExtension(file.name) || ".stp";
  const stpPath = path.join(tmpDir, `input${ext}`);
  const glbPath = path.join(tmpDir, "output.glb");

  try {
    await writeFile(stpPath, Buffer.from(await file.arrayBuffer()));
    await execFileAsync(
      process.env.PYTHON_BIN || "python",
      [script, "--input", stpPath, "--output", glbPath, "--no-manifest"],
      { timeout: 10 * 60 * 1000, maxBuffer: 16 * 1024 * 1024 },
    );
    if (!existsSync(glbPath)) {
      throw new Error("本地 STEP 转换未生成 GLB（请确认已安装 cascadio）");
    }
    return await readFile(glbPath);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`本地 STEP 转换失败：${message}`);
  } finally {
    await rm(tmpDir, { recursive: true, force: true }).catch(() => undefined);
  }
}

async function convertStpToGlb(request: Request, file: File): Promise<{ bytes: Buffer; engine: string }> {
  try {
    const bytes = await convertViaBackend(request, file);
    return { bytes, engine: "api-cascadio" };
  } catch (error) {
    const status = (error as { status?: number }).status;
    // Fall back when API is missing, unreachable, or CAD stack not installed.
    if (status !== undefined && status !== 503 && status !== 502 && status < 500) {
      throw error;
    }
    const bytes = await convertViaLocalScript(file);
    return { bytes, engine: "local-cascadio" };
  }
}

function parseBounds(raw: string): BodyModelBounds | null {
  if (!raw.trim()) return null;
  try {
    return JSON.parse(raw) as BodyModelBounds;
  } catch {
    return null;
  }
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
      return NextResponse.json({ error: "请上传 GLB/GLTF 或 STP/STEP 文件" }, { status: 400 });
    }

    const bounds = parseBounds(String(form.get("bounds") ?? ""));
    const upAxis = String(form.get("upAxis") ?? "Y").trim() || "Y";
    const unitScaleRaw = parseFloat(String(form.get("unitScale") ?? ""));
    let storedUrl: string;
    let unitScale: number;
    let convertEngine: string | null = null;
    let sourceFormat: "glb" | "stp";

    if (isStpFile(file)) {
      // No app-level size cap — conversion may take many minutes for multi‑GB STEP.
      const stpBytes = Buffer.from(await file.arrayBuffer());
      const stpBlob = new File([stpBytes], file.name, {
        type: file.type || "application/step",
      });
      const { bytes, engine } = await convertStpToGlb(request, stpBlob);

      await mkdir(CUSTOM_DIR, { recursive: true });
      const outAbs = path.join(CUSTOM_DIR, `${modelKey}.glb`);
      await writeFile(outAbs, bytes);
      // Keep original STEP next to GLB for re-convert / audit (best-effort).
      const stpAbs = path.join(CUSTOM_DIR, `${modelKey}${fileExtension(file.name) || ".stp"}`);
      await writeFile(stpAbs, stpBytes).catch(() => undefined);

      storedUrl = publicUrlForFile(outAbs);
      unitScale = Number.isFinite(unitScaleRaw) ? unitScaleRaw : STP_DEFAULT_UNIT_SCALE;
      convertEngine = engine;
      sourceFormat = "stp";
    } else if (isGlbFile(file)) {
      const mime = (file.type || "").toLowerCase();
      const ext = fileExtension(file.name) || GLB_MIME[mime] || ".glb";
      if (ext !== ".glb" && ext !== ".gltf") {
        return NextResponse.json({ error: "仅支持 GLB / GLTF / STP / STEP" }, { status: 400 });
      }

      await mkdir(CUSTOM_DIR, { recursive: true });
      const outAbs = path.join(CUSTOM_DIR, `${modelKey}${ext}`);
      await writeFile(outAbs, Buffer.from(await file.arrayBuffer()));
      storedUrl = publicUrlForFile(outAbs);
      unitScale = Number.isFinite(unitScaleRaw) ? unitScaleRaw : 1.0;
      sourceFormat = "glb";
    } else {
      return NextResponse.json({ error: "仅支持 GLB / GLTF / STP / STEP" }, { status: 400 });
    }

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
      source_format: sourceFormat,
      convert_engine: convertEngine,
    });
  } catch (error) {
    const status = (error as { status?: number }).status;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "模型保存失败" },
      { status: typeof status === "number" && status >= 400 && status < 600 ? status : 500 },
    );
  }
}
