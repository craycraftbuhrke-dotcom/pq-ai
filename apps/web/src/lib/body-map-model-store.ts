/** Shared helpers for body-map 3D model storage and STEP→GLB conversion. */

import { execFile } from "child_process";
import { createWriteStream, existsSync } from "fs";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "fs/promises";
import os from "os";
import path from "path";
import { promisify } from "util";

import { apiRequestHeaders } from "@/lib/auth-data";
import {
  EMPTY_BODY_MODEL_MANIFEST,
  MODEL_3D_ASSETS,
  normalizeModelKey,
  type BodyModelBounds,
  type BodyModelEntry,
  type BodyModelManifest,
} from "@/lib/body-map-models";

const execFileAsync = promisify(execFile);

export const STP_DEFAULT_UNIT_SCALE = 0.001;

/** Chunk size under typical Xiaomi/K8s Ingress defaults (often 1–10MB). */
export const BODY_MAP_CHUNK_SIZE = 512 * 1024;

export const GLB_MIME: Record<string, string> = {
  "model/gltf-binary": ".glb",
  "model/gltf+json": ".gltf",
  "application/octet-stream": ".glb",
};

export function resolvePublicDir(): string {
  const candidates = [path.join(process.cwd(), "public"), path.join(process.cwd(), "apps", "web", "public")];
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  return candidates[0];
}

export function resolveRepoRoot(): string {
  const candidates = [process.cwd(), path.join(process.cwd(), "..", "..")];
  for (const candidate of candidates) {
    if (existsSync(path.join(candidate, "scripts", "stp_to_glb.py"))) return candidate;
  }
  return process.cwd();
}

export const PUBLIC_DIR = resolvePublicDir();
export const MANIFEST_PATH = path.join(PUBLIC_DIR, "body-models", "view-models.json");
export const CUSTOM_DIR = path.join(PUBLIC_DIR, "body-models", "custom");
export const UPLOAD_ROOT = path.join(CUSTOM_DIR, ".uploads");

export function fileExtension(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx).toLowerCase() : "";
}

export function isStpName(name: string): boolean {
  const ext = fileExtension(name);
  return ext === ".stp" || ext === ".step";
}

export function isGlbName(name: string, mime = ""): boolean {
  const ext = fileExtension(name);
  if (ext === ".glb" || ext === ".gltf") return true;
  return Boolean(GLB_MIME[mime.toLowerCase()]);
}

export function publicUrlForFile(absPath: string): string {
  const relative = path.relative(PUBLIC_DIR, absPath).split(path.sep).join("/");
  return `/${relative}`;
}

export function parseBounds(raw: string): BodyModelBounds | null {
  if (!raw.trim()) return null;
  try {
    return JSON.parse(raw) as BodyModelBounds;
  } catch {
    return null;
  }
}

export async function readManifest(): Promise<BodyModelManifest> {
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

export async function writeManifest(manifest: BodyModelManifest): Promise<void> {
  await mkdir(path.dirname(MANIFEST_PATH), { recursive: true });
  await writeFile(MANIFEST_PATH, `${JSON.stringify(manifest, null, 2)}\n`, "utf-8");
}

function detailFromApiError(payload: unknown): string {
  if (!payload || typeof payload !== "object") return "STEP 转换失败";
  const detail =
    (payload as { detail?: unknown; error?: unknown }).detail ??
    (payload as { error?: unknown }).error;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) || (detail && typeof detail === "object")) return JSON.stringify(detail);
  return "STEP 转换失败";
}

export async function convertViaBackend(request: Request, file: File): Promise<Buffer> {
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

export async function convertViaLocalScript(filePath: string, fileName: string): Promise<Buffer> {
  const script = path.join(resolveRepoRoot(), "scripts", "stp_to_glb.py");
  if (!existsSync(script)) {
    throw new Error("本地未找到 scripts/stp_to_glb.py，无法离线转换 STEP");
  }

  const tmpDir = await mkdtemp(path.join(os.tmpdir(), "pqai-stp-"));
  const glbPath = path.join(tmpDir, "output.glb");

  try {
    await execFileAsync(
      process.env.PYTHON_BIN || "python",
      [script, "--input", filePath, "--output", glbPath, "--no-manifest"],
      { timeout: 60 * 60 * 1000, maxBuffer: 16 * 1024 * 1024 },
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

export async function convertStpFileToGlb(
  request: Request,
  filePath: string,
  fileName: string,
): Promise<{ bytes: Buffer; engine: string }> {
  const bytes = await readFile(filePath);
  const file = new File([bytes], fileName, { type: "application/step" });
  try {
    const glb = await convertViaBackend(request, file);
    return { bytes: glb, engine: "api-cascadio" };
  } catch (error) {
    const status = (error as { status?: number }).status;
    if (status !== undefined && status !== 503 && status !== 502 && status < 500) {
      throw error;
    }
    const glb = await convertViaLocalScript(filePath, fileName);
    return { bytes: glb, engine: "local-cascadio" };
  }
}

export type PersistOptions = {
  modelCode: string;
  fileName: string;
  upAxis: string;
  unitScaleRaw: number;
  bounds: BodyModelBounds | null;
  /** Absolute path to assembled source file on disk. */
  sourcePath: string;
  request: Request;
};

export async function persistUploadedModel(options: PersistOptions): Promise<{
  entry: BodyModelEntry;
  source_format: "glb" | "stp";
  convert_engine: string | null;
  model_code: string;
}> {
  const modelKey = normalizeModelKey(options.modelCode);
  const manifest = await readManifest();
  await mkdir(CUSTOM_DIR, { recursive: true });

  let storedUrl: string;
  let unitScale: number;
  let convertEngine: string | null = null;
  let sourceFormat: "glb" | "stp";

  if (isStpName(options.fileName)) {
    const { bytes, engine } = await convertStpFileToGlb(
      options.request,
      options.sourcePath,
      options.fileName,
    );
    const outAbs = path.join(CUSTOM_DIR, `${modelKey}.glb`);
    await writeFile(outAbs, bytes);
    const stpAbs = path.join(CUSTOM_DIR, `${modelKey}${fileExtension(options.fileName) || ".stp"}`);
    await writeFile(stpAbs, await readFile(options.sourcePath)).catch(() => undefined);
    storedUrl = publicUrlForFile(outAbs);
    unitScale = Number.isFinite(options.unitScaleRaw) ? options.unitScaleRaw : STP_DEFAULT_UNIT_SCALE;
    convertEngine = engine;
    sourceFormat = "stp";
  } else if (isGlbName(options.fileName)) {
    const ext = fileExtension(options.fileName) || ".glb";
    if (ext !== ".glb" && ext !== ".gltf") {
      throw Object.assign(new Error("仅支持 GLB / GLTF / STP / STEP"), { status: 400 });
    }
    const outAbs = path.join(CUSTOM_DIR, `${modelKey}${ext}`);
    await writeFile(outAbs, await readFile(options.sourcePath));
    storedUrl = publicUrlForFile(outAbs);
    unitScale = Number.isFinite(options.unitScaleRaw) ? options.unitScaleRaw : 1.0;
    sourceFormat = "glb";
  } else {
    throw Object.assign(new Error("仅支持 GLB / GLTF / STP / STEP"), { status: 400 });
  }

  const entry: BodyModelEntry = {
    url: storedUrl,
    up_axis: options.upAxis || "Y",
    unit_scale: unitScale,
    bounds: options.bounds,
    model_asset_key: storedUrl,
  };
  manifest.models[modelKey] = entry;
  await writeManifest(manifest);

  return {
    entry,
    source_format: sourceFormat,
    convert_engine: convertEngine,
    model_code: options.modelCode,
  };
}

export type UploadSessionMeta = {
  uploadId: string;
  modelCode: string;
  fileName: string;
  totalSize: number;
  chunkSize: number;
  totalChunks: number;
  received: number[];
  createdAt: number;
};

export function uploadDir(uploadId: string): string {
  return path.join(UPLOAD_ROOT, uploadId);
}

export function uploadMetaPath(uploadId: string): string {
  return path.join(uploadDir(uploadId), "meta.json");
}

export async function readUploadMeta(uploadId: string): Promise<UploadSessionMeta> {
  const raw = await readFile(uploadMetaPath(uploadId), "utf-8");
  return JSON.parse(raw) as UploadSessionMeta;
}

export async function writeUploadMeta(meta: UploadSessionMeta): Promise<void> {
  await mkdir(uploadDir(meta.uploadId), { recursive: true });
  await writeFile(uploadMetaPath(meta.uploadId), `${JSON.stringify(meta, null, 2)}\n`, "utf-8");
}

export async function assembleUpload(uploadId: string): Promise<string> {
  const meta = await readUploadMeta(uploadId);
  const dir = uploadDir(uploadId);
  const assembled = path.join(dir, `assembled${fileExtension(meta.fileName) || ".bin"}`);
  const out = createWriteStream(assembled);
  try {
    for (let i = 0; i < meta.totalChunks; i++) {
      const chunkPath = path.join(dir, `chunk-${i}.part`);
      if (!existsSync(chunkPath)) {
        throw Object.assign(new Error(`缺少分片 ${i + 1}/${meta.totalChunks}`), { status: 400 });
      }
      const buf = await readFile(chunkPath);
      await new Promise<void>((resolve, reject) => {
        out.write(buf, (err: Error | null | undefined) => (err ? reject(err) : resolve()));
      });
    }
    await new Promise<void>((resolve, reject) => {
      out.end((err: Error | null | undefined) => (err ? reject(err) : resolve()));
    });
  } catch (error) {
    out.destroy();
    throw error;
  }
  return assembled;
}

export async function cleanupUpload(uploadId: string): Promise<void> {
  await rm(uploadDir(uploadId), { recursive: true, force: true }).catch(() => undefined);
}

export { MODEL_3D_ASSETS, normalizeModelKey };
