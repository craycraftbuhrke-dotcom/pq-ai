/** Shared helpers for body-map 3D model storage and STEP→GLB conversion. */

import { randomUUID } from "crypto";
import { createWriteStream, existsSync, openAsBlob } from "fs";
import { copyFile, mkdir, open, readFile, readdir, rename, rm, stat, writeFile } from "fs/promises";
import path from "path";

import { apiRequestHeaders, upstreamRequestSignal } from "@/lib/auth-data";
import {
  EMPTY_BODY_MODEL_MANIFEST,
  legacyModelKey,
  MODEL_3D_ASSETS,
  normalizeModelKey,
  ownModelEntry,
  type BodyModelBounds,
  type BodyModelEntry,
  type BodyModelManifest,
} from "@/lib/body-map-models";
import { withRuntimeFileLock } from "@/lib/runtime-file-lock";

export const STP_DEFAULT_UNIT_SCALE = 0.001;

/** Chunk size under typical Xiaomi/K8s Ingress defaults (often 1–10MB). */
export const BODY_MAP_CHUNK_SIZE = 512 * 1024;
export const BODY_MODEL_MAX_UPLOAD_BYTES = (() => {
  const configured = Number(process.env.BODY_MODEL_MAX_UPLOAD_BYTES);
  return Number.isSafeInteger(configured) && configured > 0 ? configured : 256 * 1024 * 1024;
})();
export const BODY_MODEL_UPLOAD_SESSION_TTL_MS = (() => {
  const configured = Number(process.env.BODY_MODEL_UPLOAD_SESSION_TTL_MS);
  return Number.isSafeInteger(configured) && configured >= 60_000
    ? configured
    : 24 * 60 * 60 * 1000;
})();
const BODY_MODEL_GLTF_JSON_MAX_BYTES = Math.min(BODY_MODEL_MAX_UPLOAD_BYTES, 32 * 1024 * 1024);
const UPLOAD_GC_INTERVAL_MS = 60 * 60 * 1000;
let lastUploadGcAt = 0;

const UPLOAD_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function resolvePublicDir(): string {
  const configured = process.env.WEB_PUBLIC_DIR;
  return configured
    ? path.resolve(/*turbopackIgnore: true*/ configured)
    : path.join(/*turbopackIgnore: true*/ process.cwd(), "public");
}

export function resolveRuntimeAssetDir(): string {
  const configured = process.env.WEB_RUNTIME_ASSET_DIR;
  return configured ? path.resolve(/*turbopackIgnore: true*/ configured) : resolvePublicDir();
}

export const PUBLIC_DIR = resolvePublicDir();
export const RUNTIME_ASSET_DIR = resolveRuntimeAssetDir();
export const MANIFEST_PATH = path.join(
  /*turbopackIgnore: true*/ RUNTIME_ASSET_DIR,
  "body-models",
  "view-models.json",
);
export const CUSTOM_DIR = path.join(
  /*turbopackIgnore: true*/ RUNTIME_ASSET_DIR,
  "body-models",
  "custom",
);
export const UPLOAD_ROOT = path.join(/*turbopackIgnore: true*/ CUSTOM_DIR, ".uploads");
const PENDING_DIR = path.join(/*turbopackIgnore: true*/ CUSTOM_DIR, ".pending");

export type RuntimeStorageStatus = {
  runtime_dir: string;
  public_dir: string;
  using_shared_runtime_dir: boolean;
  writable: boolean;
  warning: string | null;
};

/**
 * Probe writable runtime storage. Production multi-replica uploads require a
 * shared WEB_RUNTIME_ASSET_DIR (PVC), not the image-local public/ directory.
 */
export async function getRuntimeStorageStatus(): Promise<RuntimeStorageStatus> {
  const usingShared = Boolean(process.env.WEB_RUNTIME_ASSET_DIR?.trim());
  let writable = false;
  try {
    await mkdir(UPLOAD_ROOT, { recursive: true });
    const probe = path.join(/*turbopackIgnore: true*/ UPLOAD_ROOT, `.write-probe-${randomUUID()}`);
    await writeFile(probe, "ok", "utf-8");
    await rm(probe, { force: true });
    writable = true;
  } catch {
    writable = false;
  }

  let warning: string | null = null;
  if (!writable) {
    warning =
      "运行时资源目录不可写，无法上传三维数模。请挂载共享 PVC，并确认目录权限（通常 uid/gid 1000）。";
  } else if (!usingShared && process.env.NODE_ENV === "production") {
    warning =
      "未配置 WEB_RUNTIME_ASSET_DIR：上传会话写在容器本地盘。多副本时分片会找不到 meta.json。请挂载 RWX PVC 并设置 WEB_RUNTIME_ASSET_DIR=/data/runtime-assets。";
  }

  return {
    runtime_dir: RUNTIME_ASSET_DIR,
    public_dir: PUBLIC_DIR,
    using_shared_runtime_dir: usingShared,
    writable,
    warning,
  };
}

/** Fail fast before creating an upload session that cannot survive across pods. */
export async function assertRuntimeStorageReadyForUpload(): Promise<RuntimeStorageStatus> {
  const status = await getRuntimeStorageStatus();
  if (!status.writable) {
    throw Object.assign(new Error(status.warning ?? "运行时资源目录不可写"), { status: 503 });
  }
  if (!status.using_shared_runtime_dir && process.env.NODE_ENV === "production") {
    throw Object.assign(new Error(status.warning ?? "未配置共享运行时目录"), { status: 503 });
  }
  return status;
}

export function fileExtension(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx).toLowerCase() : "";
}

export function isStpName(name: string): boolean {
  const ext = fileExtension(name);
  return ext === ".stp" || ext === ".step";
}

export function isGlbName(name: string): boolean {
  const ext = fileExtension(name);
  return ext === ".glb" || ext === ".gltf";
}

export function publicUrlForFile(absPath: string): string {
  const relative = path.relative(RUNTIME_ASSET_DIR, absPath).split(path.sep).join("/");
  return RUNTIME_ASSET_DIR === PUBLIC_DIR ? `/${relative}` : `/runtime-assets/${relative}`;
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
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return { ...EMPTY_BODY_MODEL_MANIFEST, models: {} };
    }
    throw Object.assign(new Error("三维数模清单无法读取，请检查运行时存储"), { status: 500 });
  }
}

export async function writeManifest(manifest: BodyModelManifest): Promise<void> {
  await mkdir(path.dirname(MANIFEST_PATH), { recursive: true });
  const temporaryPath = `${MANIFEST_PATH}.${randomUUID()}.tmp`;
  try {
    await writeFile(temporaryPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf-8");
    await rename(temporaryPath, MANIFEST_PATH);
  } finally {
    await rm(temporaryPath, { force: true }).catch(() => undefined);
  }
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

export async function convertViaBackend(
  request: Request,
  file: Blob,
  fileName: string,
  outputPath: string,
): Promise<void> {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    throw new Error("后端 API 地址未配置，无法转换 STEP");
  }

  const form = new FormData();
  form.set("file", file, fileName);

  const response = await fetch(`${apiUrl.replace(/\/$/, "")}/quality/body-map/convert-stp`, {
    method: "POST",
    headers: await apiRequestHeaders(request),
    body: form,
    cache: "no-store",
    signal: upstreamRequestSignal(request, 10 * 60 * 1000),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const message = detailFromApiError(payload);
    const err = new Error(message) as Error & { status?: number };
    err.status = response.status;
    throw err;
  }

  const declaredLength = response.headers.get("content-length");
  if (declaredLength !== null) {
    const parsedLength = Number(declaredLength);
    if (!Number.isSafeInteger(parsedLength) || parsedLength < 0) {
      throw new Error("STEP 转换服务返回了无效的 Content-Length");
    }
    if (parsedLength > BODY_MODEL_MAX_UPLOAD_BYTES) {
      throw Object.assign(new Error("STEP 转换结果超过系统允许大小"), { status: 413 });
    }
  }

  if (!response.body) throw new Error("后端转换结果为空");
  await mkdir(path.dirname(outputPath), { recursive: true });
  const reader = response.body.getReader();
  let output;
  try {
    output = await open(outputPath, "wx");
  } catch (error) {
    await reader.cancel("converted model output could not be opened").catch(() => undefined);
    reader.releaseLock();
    throw error;
  }
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > BODY_MODEL_MAX_UPLOAD_BYTES) {
        await reader.cancel("converted model too large").catch(() => undefined);
        throw Object.assign(new Error("STEP 转换结果超过系统允许大小"), { status: 413 });
      }
      await output.write(value);
    }
    if (!total) throw new Error("后端转换结果为空");
  } catch (error) {
    await reader.cancel("converted model persistence failed").catch(() => undefined);
    await output.close().catch(() => undefined);
    await rm(outputPath, { force: true }).catch(() => undefined);
    throw error;
  } finally {
    await output.close().catch(() => undefined);
    reader.releaseLock();
  }
}

export async function convertStpFileToGlb(
  request: Request,
  filePath: string,
  fileName: string,
  outputPath: string,
): Promise<{ engine: string }> {
  const file = await openAsBlob(filePath, { type: "application/step" });
  await convertViaBackend(request, file, fileName, outputPath);
  return { engine: "api-cascadio" };
}

async function validateModelFileContents(filePath: string, fileName: string): Promise<void> {
  const ext = fileExtension(fileName);
  let valid = false;
  if (ext === ".glb") {
    const fileSize = (await stat(filePath)).size;
    if (fileSize >= 12) {
      const handle = await open(filePath, "r");
      const header = Buffer.alloc(12);
      let bytesRead = 0;
      try {
        ({ bytesRead } = await handle.read(header, 0, header.length, 0));
      } finally {
        await handle.close();
      }
      valid =
        bytesRead === header.length &&
        header.subarray(0, 4).toString("ascii") === "glTF" &&
        header.readUInt32LE(4) === 2 &&
        header.readUInt32LE(8) === fileSize;
    }
  } else if (ext === ".gltf") {
    const fileSize = (await stat(filePath)).size;
    if (fileSize > BODY_MODEL_GLTF_JSON_MAX_BYTES) {
      throw Object.assign(
        new Error("GLTF JSON 不能超过 32 MiB，请改用二进制 GLB 格式"),
        { status: 413 },
      );
    }
    try {
      const document = JSON.parse((await readFile(filePath, "utf-8")).trim()) as {
        asset?: { version?: unknown };
        buffers?: Array<{ uri?: unknown }>;
        images?: Array<{ uri?: unknown; bufferView?: unknown }>;
      };
      const buffersAreEmbedded = (document.buffers ?? []).every(
        (buffer) => typeof buffer.uri === "string" && buffer.uri.startsWith("data:"),
      );
      const imagesAreEmbedded = (document.images ?? []).every((image) =>
        typeof image.uri === "string"
          ? image.uri.startsWith("data:")
          : Number.isInteger(image.bufferView),
      );
      valid =
        Boolean(document) &&
        typeof document === "object" &&
        typeof document.asset?.version === "string" &&
        document.asset.version.startsWith("2.") &&
        buffersAreEmbedded &&
        imagesAreEmbedded;
    } catch {
      valid = false;
    }
  } else if (isStpName(fileName)) {
    const handle = await open(filePath, "r");
    const head = Buffer.alloc(4096);
    let bytesRead = 0;
    try {
      ({ bytesRead } = await handle.read(head, 0, head.length, 0));
    } finally {
      await handle.close();
    }
    valid = head.subarray(0, bytesRead).toString("ascii").trimStart().startsWith("ISO-10303-21;");
  }
  if (!valid) {
    throw Object.assign(new Error("文件内容与扩展名不匹配或文件已损坏"), { status: 400 });
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
  uploadId?: string;
};

export type PersistResult = {
  entry: BodyModelEntry;
  source_format: "glb" | "stp";
  convert_engine: string | null;
  model_code: string;
};

type PreparedModel = {
  pendingModelPath: string;
  modelExtension: ".glb" | ".gltf";
  pendingSourcePath: string | null;
  sourceExtension: ".stp" | ".step" | null;
  unitScale: number;
  convertEngine: string | null;
  sourceFormat: "glb" | "stp";
};

async function prepareUploadedModel(options: PersistOptions): Promise<PreparedModel> {
  await mkdir(PENDING_DIR, { recursive: true });
  const token = randomUUID();
  if (isStpName(options.fileName)) {
    const sourceExtension = fileExtension(options.fileName) === ".step" ? ".step" : ".stp";
    const pendingModelPath = path.join(/*turbopackIgnore: true*/ PENDING_DIR, `${token}.glb`);
    const pendingSourcePath = path.join(
      /*turbopackIgnore: true*/ PENDING_DIR,
      `${token}${sourceExtension}`,
    );
    try {
      const { engine } = await convertStpFileToGlb(
        options.request,
        options.sourcePath,
        options.fileName,
        pendingModelPath,
      );
      await validateModelFileContents(pendingModelPath, `${token}.glb`);
      await copyFile(options.sourcePath, pendingSourcePath);
      return {
        pendingModelPath,
        modelExtension: ".glb",
        pendingSourcePath,
        sourceExtension,
        unitScale: Number.isFinite(options.unitScaleRaw) ? options.unitScaleRaw : STP_DEFAULT_UNIT_SCALE,
        convertEngine: engine,
        sourceFormat: "stp",
      };
    } catch (error) {
      await rm(pendingModelPath, { force: true }).catch(() => undefined);
      await rm(pendingSourcePath, { force: true }).catch(() => undefined);
      throw error;
    }
  }

  if (!isGlbName(options.fileName)) {
    throw Object.assign(new Error("仅支持 GLB / GLTF / STP / STEP"), { status: 400 });
  }
  const extension = fileExtension(options.fileName) === ".gltf" ? ".gltf" : ".glb";
  const pendingModelPath = path.join(
    /*turbopackIgnore: true*/ PENDING_DIR,
    `${token}${extension}`,
  );
  try {
    await copyFile(options.sourcePath, pendingModelPath);
    await validateModelFileContents(pendingModelPath, `${token}${extension}`);
  } catch (error) {
    await rm(pendingModelPath, { force: true }).catch(() => undefined);
    throw error;
  }
  return {
    pendingModelPath,
    modelExtension: extension,
    pendingSourcePath: null,
    sourceExtension: null,
    unitScale: Number.isFinite(options.unitScaleRaw) ? options.unitScaleRaw : 1.0,
    convertEngine: null,
    sourceFormat: "glb",
  };
}

async function finalizeUploadedModel(
  options: PersistOptions,
  prepared: PreparedModel,
): Promise<PersistResult> {
  const modelKey = normalizeModelKey(options.modelCode);
  const manifest = await readManifest();
  const legacyKey = legacyModelKey(options.modelCode);
  const current = ownModelEntry(manifest.models, modelKey);
  const legacyEntry = legacyKey !== modelKey ? ownModelEntry(manifest.models, legacyKey) : undefined;
  const supersededEntries = [current, legacyEntry].filter(
    (candidate): candidate is BodyModelEntry => candidate !== undefined,
  );
  if (legacyKey !== modelKey) {
    delete manifest.models[legacyKey];
  }
  await mkdir(CUSTOM_DIR, { recursive: true });

  const revision = randomUUID();
  const outAbs = path.join(
    /*turbopackIgnore: true*/ CUSTOM_DIR,
    `${modelKey}-${revision}${prepared.modelExtension}`,
  );
  const sourceAbs = prepared.sourceExtension
    ? path.join(
        /*turbopackIgnore: true*/ CUSTOM_DIR,
        `${modelKey}-${revision}${prepared.sourceExtension}`,
      )
    : null;
  const storedUrl = publicUrlForFile(outAbs);

  const entry: BodyModelEntry = {
    url: storedUrl,
    up_axis: options.upAxis || "Y",
    unit_scale: prepared.unitScale,
    bounds: options.bounds,
    model_asset_key: storedUrl,
    upload_id: options.uploadId ?? null,
    source_format: prepared.sourceFormat,
    convert_engine: prepared.convertEngine,
    model_code: options.modelCode,
  };
  manifest.models[modelKey] = entry;
  try {
    await rename(prepared.pendingModelPath, outAbs);
    if (prepared.pendingSourcePath && sourceAbs) {
      await rename(prepared.pendingSourcePath, sourceAbs);
    }
    await writeManifest(manifest);
  } catch (error) {
    await rm(outAbs, { force: true }).catch(() => undefined);
    if (sourceAbs) await rm(sourceAbs, { force: true }).catch(() => undefined);
    throw error;
  }

  await Promise.all(
    supersededEntries.map((previous) => removeSupersededModelArtifacts(previous, outAbs, sourceAbs)),
  );

  return {
    entry,
    source_format: prepared.sourceFormat,
    convert_engine: prepared.convertEngine,
    model_code: options.modelCode,
  };
}

export async function findCompletedUpload(uploadId: string): Promise<PersistResult | null> {
  uploadDir(uploadId);
  const manifest = await readManifest();
  for (const [modelCode, entry] of Object.entries(manifest.models)) {
    if (entry.upload_id !== uploadId || !entry.url || !entry.source_format) continue;
    return {
      entry,
      source_format: entry.source_format,
      convert_engine: entry.convert_engine ?? null,
      model_code: entry.model_code || modelCode,
    };
  }
  return null;
}

const GENERATED_MODEL_REVISION_PATTERN = /-[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function generatedCustomArtifactFromUrl(url: string | null): string | null {
  if (!url) return null;
  let pathname: string;
  try {
    pathname = new URL(url, "http://runtime.local").pathname;
  } catch {
    return null;
  }
  const relativeUrl = pathname.startsWith("/runtime-assets/")
    ? pathname.slice("/runtime-assets/".length)
    : pathname.replace(/^\/+/, "");
  const candidate = path.resolve(/*turbopackIgnore: true*/ RUNTIME_ASSET_DIR, relativeUrl);
  const relativeToCustom = path.relative(
    path.resolve(/*turbopackIgnore: true*/ CUSTOM_DIR),
    candidate,
  );
  if (!relativeToCustom || relativeToCustom.startsWith("..") || path.isAbsolute(relativeToCustom)) {
    return null;
  }
  const extension = path.extname(candidate).toLowerCase();
  const revisionStem = path.basename(candidate, extension);
  if (![".glb", ".gltf"].includes(extension) || !GENERATED_MODEL_REVISION_PATTERN.test(revisionStem)) {
    return null;
  }
  return candidate;
}

async function removeSupersededModelArtifacts(
  previous: BodyModelEntry,
  currentModelPath?: string,
  currentSourcePath?: string | null,
): Promise<void> {
  const previousModelPath = generatedCustomArtifactFromUrl(previous.url);
  if (!previousModelPath) return;
  const previousStem = previousModelPath.slice(0, -path.extname(previousModelPath).length);
  const protectedPaths = new Set(
    [currentModelPath, currentSourcePath]
      .filter((candidate): candidate is string => typeof candidate === "string")
      .map((candidate) => path.resolve(/*turbopackIgnore: true*/ candidate)),
  );
  await Promise.all(
    [previousModelPath, `${previousStem}.stp`, `${previousStem}.step`].map(async (candidate) => {
      if (protectedPaths.has(path.resolve(/*turbopackIgnore: true*/ candidate))) return;
      await rm(candidate, { force: true }).catch(() => undefined);
    }),
  );
}

export async function removeStoredModelArtifacts(previous: BodyModelEntry): Promise<void> {
  await removeSupersededModelArtifacts(previous);
}

export async function persistUploadedModel(options: PersistOptions): Promise<PersistResult> {
  await validateModelFileContents(options.sourcePath, options.fileName);
  const prepared = await prepareUploadedModel(options);
  try {
    return await withRuntimeFileLock(`${MANIFEST_PATH}.lock`, () =>
      finalizeUploadedModel(options, prepared),
    );
  } finally {
    await rm(prepared.pendingModelPath, { force: true }).catch(() => undefined);
    if (prepared.pendingSourcePath) {
      await rm(prepared.pendingSourcePath, { force: true }).catch(() => undefined);
    }
  }
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
  const normalized = uploadId.trim();
  if (!UPLOAD_ID_PATTERN.test(normalized)) {
    throw Object.assign(new Error("无效的上传会话标识"), { status: 400 });
  }
  const root = path.resolve(/*turbopackIgnore: true*/ UPLOAD_ROOT);
  const resolved = path.resolve(/*turbopackIgnore: true*/ root, normalized);
  if (path.dirname(resolved) !== root) {
    throw Object.assign(new Error("上传会话路径越界"), { status: 400 });
  }
  return resolved;
}

export function uploadMetaPath(uploadId: string): string {
  return path.join(/*turbopackIgnore: true*/ uploadDir(uploadId), "meta.json");
}

export async function readUploadMeta(uploadId: string): Promise<UploadSessionMeta> {
  let raw: string;
  try {
    raw = await readFile(uploadMetaPath(uploadId), "utf-8");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      throw Object.assign(
        new Error(
          "上传会话不存在或无法在当前实例读取。请确认所有前端 Pod 已挂载同一 RWX PVC，并设置 WEB_RUNTIME_ASSET_DIR；然后重新选择文件上传。",
        ),
        { status: 404 },
      );
    }
    throw error;
  }
  const meta = JSON.parse(raw) as UploadSessionMeta;
  const receivedIsValid =
    Array.isArray(meta.received) &&
    new Set(meta.received).size === meta.received.length &&
    meta.received.every(
      (index) => Number.isSafeInteger(index) && index >= 0 && index < meta.totalChunks,
    );
  if (
    meta.uploadId !== uploadId ||
    !Number.isSafeInteger(meta.totalSize) ||
    meta.totalSize <= 0 ||
    meta.totalSize > BODY_MODEL_MAX_UPLOAD_BYTES ||
    !Number.isSafeInteger(meta.chunkSize) ||
    meta.chunkSize <= 0 ||
    meta.chunkSize > BODY_MAP_CHUNK_SIZE ||
    !Number.isSafeInteger(meta.totalChunks) ||
    meta.totalChunks !== Math.ceil(meta.totalSize / meta.chunkSize) ||
    !Number.isFinite(meta.createdAt) ||
    meta.createdAt > Date.now() + 5 * 60 * 1000 ||
    !receivedIsValid
  ) {
    throw Object.assign(new Error("上传会话元数据无效"), { status: 400 });
  }
  if (Date.now() - meta.createdAt > BODY_MODEL_UPLOAD_SESSION_TTL_MS) {
    await cleanupUpload(uploadId);
    throw Object.assign(new Error("上传会话已过期，请重新选择文件上传"), { status: 410 });
  }
  return meta;
}

export async function writeUploadMeta(meta: UploadSessionMeta): Promise<void> {
  await mkdir(uploadDir(meta.uploadId), { recursive: true });
  const target = uploadMetaPath(meta.uploadId);
  const temporaryPath = `${target}.${randomUUID()}.tmp`;
  await writeFile(temporaryPath, `${JSON.stringify(meta, null, 2)}\n`, "utf-8");
  await rename(temporaryPath, target);
}

export async function assembleUpload(uploadId: string): Promise<string> {
  const meta = await readUploadMeta(uploadId);
  const dir = uploadDir(uploadId);
  const assembled = path.join(
    /*turbopackIgnore: true*/ dir,
    `assembled${fileExtension(meta.fileName) || ".bin"}`,
  );
  const out = createWriteStream(assembled);
  let assembledSize = 0;
  try {
    for (let i = 0; i < meta.totalChunks; i++) {
      const chunkPath = path.join(/*turbopackIgnore: true*/ dir, `chunk-${i}.part`);
      if (!existsSync(chunkPath)) {
        throw Object.assign(new Error(`缺少分片 ${i + 1}/${meta.totalChunks}`), { status: 400 });
      }
      const buf = await readFile(chunkPath);
      assembledSize += buf.length;
      await new Promise<void>((resolve, reject) => {
        out.write(buf, (err: Error | null | undefined) => (err ? reject(err) : resolve()));
      });
    }
    await new Promise<void>((resolve, reject) => {
      out.end((err: Error | null | undefined) => (err ? reject(err) : resolve()));
    });
    if (assembledSize !== meta.totalSize) {
      throw Object.assign(
        new Error(`上传文件大小不一致：期望 ${meta.totalSize} 字节，实际 ${assembledSize} 字节`),
        { status: 400 },
      );
    }
  } catch (error) {
    out.destroy();
    await rm(assembled, { force: true }).catch(() => undefined);
    throw error;
  }
  return assembled;
}

export async function cleanupUpload(uploadId: string): Promise<void> {
  await rm(uploadDir(uploadId), { recursive: true, force: true }).catch(() => undefined);
}

export async function garbageCollectExpiredUploads(now = Date.now()): Promise<number> {
  if (now - lastUploadGcAt < UPLOAD_GC_INTERVAL_MS) return 0;
  lastUploadGcAt = now;
  const entries = await readdir(UPLOAD_ROOT, { withFileTypes: true }).catch(() => []);
  let removed = 0;
  await Promise.all(
    entries.map(async (entry) => {
      if (!entry.isDirectory() || !UPLOAD_ID_PATTERN.test(entry.name)) return;
      const dir = uploadDir(entry.name);
      try {
        await withRuntimeFileLock(
          `${dir}.lock`,
          async () => {
            const currentDirectoryStat = await stat(dir).catch(() => null);
            if (!currentDirectoryStat?.isDirectory()) return;
            let createdAt: number | null = null;
            try {
              const parsed = JSON.parse(
                await readFile(path.join(/*turbopackIgnore: true*/ dir, "meta.json"), "utf-8"),
              ) as { createdAt?: unknown };
              if (typeof parsed.createdAt === "number" && Number.isFinite(parsed.createdAt)) {
                createdAt = parsed.createdAt;
              }
            } catch {
              createdAt = currentDirectoryStat.mtimeMs;
            }
            if (createdAt !== null && now - createdAt > BODY_MODEL_UPLOAD_SESSION_TTL_MS) {
              await cleanupUpload(entry.name);
              removed += 1;
            }
          },
          { waitMs: 0 },
        );
      } catch {
        // Opportunistic GC must not delay or fail a live upload request.
      }
    }),
  );
  return removed;
}

export { MODEL_3D_ASSETS, normalizeModelKey };
