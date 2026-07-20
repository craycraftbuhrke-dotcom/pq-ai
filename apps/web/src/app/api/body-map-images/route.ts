import { randomUUID } from "crypto";
import { mkdir, readFile, rename, rm, writeFile } from "fs/promises";
import path from "path";

import { NextResponse } from "next/server";
import sharp from "sharp";

import {
  BODY_MAP_VIEW_LABELS,
  BODY_MAP_VIEWS,
  EMPTY_BODY_MAP_IMAGE_MANIFEST,
  builtinBodyMapImage,
  normalizeModelImageKey,
  resolveBodyMapImage,
  type BodyMapImageManifest,
  type BodyMapView,
  withCacheBust,
} from "@/lib/body-map-images";
import { requireApiActor, requireApiPermission } from "@/lib/auth-data";
import { legacyModelKey, ownModelEntry } from "@/lib/body-map-models";
import { withRuntimeFileLock } from "@/lib/runtime-file-lock";
import { parseBoundedFormData } from "@/lib/bounded-request-body";

export const runtime = "nodejs";

function resolvePublicDir(): string {
  const configured = process.env.WEB_PUBLIC_DIR;
  return configured
    ? path.resolve(/*turbopackIgnore: true*/ configured)
    : path.join(/*turbopackIgnore: true*/ process.cwd(), "public");
}

const PUBLIC_DIR = resolvePublicDir();
const RUNTIME_ASSET_DIR = process.env.WEB_RUNTIME_ASSET_DIR
  ? path.resolve(/*turbopackIgnore: true*/ process.env.WEB_RUNTIME_ASSET_DIR)
  : PUBLIC_DIR;
const MANIFEST_PATH = path.join(
  /*turbopackIgnore: true*/ RUNTIME_ASSET_DIR,
  "body-maps",
  "view-images.json",
);
const CUSTOM_DIR = path.join(/*turbopackIgnore: true*/ RUNTIME_ASSET_DIR, "body-maps", "custom");

const ALLOWED_MIME: Record<string, string> = {
  "image/jpeg": ".jpg",
  "image/jpg": ".jpg",
  "image/png": ".png",
  "image/webp": ".webp",
};

function isBodyView(value: string): value is BodyMapView {
  return (BODY_MAP_VIEWS as string[]).includes(value);
}

async function readManifest(): Promise<BodyMapImageManifest> {
  try {
    const raw = await readFile(MANIFEST_PATH, "utf-8");
    const parsed = JSON.parse(raw) as BodyMapImageManifest;
    if (!parsed || typeof parsed !== "object") return { ...EMPTY_BODY_MAP_IMAGE_MANIFEST, models: {} };
    return {
      version: typeof parsed.version === "number" ? parsed.version : 1,
      models: parsed.models && typeof parsed.models === "object" ? parsed.models : {},
    };
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return { ...EMPTY_BODY_MAP_IMAGE_MANIFEST, models: {} };
    }
    throw Object.assign(new Error("点位底图清单无法读取，请检查运行时存储"), { status: 500 });
  }
}

async function writeManifest(manifest: BodyMapImageManifest): Promise<void> {
  await mkdir(path.dirname(MANIFEST_PATH), { recursive: true });
  const temporaryPath = `${MANIFEST_PATH}.${randomUUID()}.tmp`;
  try {
    await writeFile(temporaryPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf-8");
    await rename(temporaryPath, MANIFEST_PATH);
  } finally {
    await rm(temporaryPath, { force: true }).catch(() => undefined);
  }
}

function publicUrlForFile(absPath: string): string {
  const relative = path.relative(RUNTIME_ASSET_DIR, absPath).split(path.sep).join("/");
  return RUNTIME_ASSET_DIR === PUBLIC_DIR ? `/${relative}` : `/runtime-assets/${relative}`;
}

function publicAssetPath(url: string): string {
  const relative = url.split("?", 1)[0].replace(/^\/+/, "");
  const isRuntime = relative.startsWith("runtime-assets/");
  const rootDir = isRuntime ? RUNTIME_ASSET_DIR : PUBLIC_DIR;
  const assetRelative = isRuntime ? relative.slice("runtime-assets/".length) : relative;
  const resolved = path.resolve(/*turbopackIgnore: true*/ rootDir, assetRelative);
  const root = `${path.resolve(/*turbopackIgnore: true*/ rootDir)}${path.sep}`;
  if (!resolved.startsWith(root)) {
    throw Object.assign(new Error("底图资源路径无效"), { status: 400 });
  }
  return resolved;
}

function mutableCustomAssetPath(url: string | undefined): string | null {
  if (!url) return null;
  let candidate: string;
  try {
    candidate = publicAssetPath(url);
  } catch {
    return null;
  }
  const relative = path.relative(
    path.resolve(/*turbopackIgnore: true*/ CUSTOM_DIR),
    path.resolve(/*turbopackIgnore: true*/ candidate),
  );
  if (!relative || relative.startsWith("..") || path.isAbsolute(relative)) return null;
  return candidate;
}

async function removeSupersededImage(url: string | undefined, currentPath?: string): Promise<void> {
  const previousPath = mutableCustomAssetPath(url);
  if (
    !previousPath ||
    (currentPath &&
      path.resolve(/*turbopackIgnore: true*/ previousPath) ===
        path.resolve(/*turbopackIgnore: true*/ currentPath))
  ) return;
  await rm(previousPath, { force: true }).catch(() => undefined);
}

async function commitImageRevision(
  manifest: BodyMapImageManifest,
  modelKey: string,
  bodyView: BodyMapView,
  newPath: string,
  previousUrl: string | undefined,
): Promise<string> {
  const storedUrl = publicUrlForFile(newPath);
  manifest.models[modelKey][bodyView] = storedUrl;
  try {
    await writeManifest(manifest);
  } catch (error) {
    await rm(newPath, { force: true }).catch(() => undefined);
    throw error;
  }
  await removeSupersededImage(previousUrl, newPath);
  return storedUrl;
}

function requestError(error: unknown, fallback: string) {
  const status = (error as { status?: number }).status;
  return NextResponse.json(
    { error: error instanceof Error ? error.message : fallback },
    { status: typeof status === "number" && status >= 400 && status < 600 ? status : 500 },
  );
}

export async function GET(request: Request) {
  try {
    await requireApiActor(request);
  } catch (error) {
    return requestError(error, "认证失败");
  }
  const { searchParams } = new URL(request.url);
  const modelCode = (searchParams.get("modelCode") ?? "").trim();
  if (!modelCode) {
    return NextResponse.json({ error: "缺少 modelCode" }, { status: 400 });
  }
  if (modelCode.length > 100) {
    return NextResponse.json({ error: "车型代码不能超过 100 个字符" }, { status: 400 });
  }
  const manifest = await readManifest();
  const key = normalizeModelImageKey(modelCode);
  const legacyKey = legacyModelKey(modelCode);
  const overrides = ownModelEntry(manifest.models, key) ?? ownModelEntry(manifest.models, legacyKey) ?? {};
  const views = BODY_MAP_VIEWS.map((view) => {
    const builtin = builtinBodyMapImage(modelCode, view);
    const resolved = resolveBodyMapImage(modelCode, view, manifest);
    const isCustom = Boolean(overrides[view]);
    return {
      body_view: view,
      label: BODY_MAP_VIEW_LABELS[view],
      url: resolved,
      builtin_url: builtin,
      source: isCustom ? "custom" : "builtin",
    };
  });
  return NextResponse.json({
    model_code: modelCode,
    model_key: key,
    views,
    manifest_path: "/body-maps/view-images.json",
  });
}

export async function POST(request: Request) {
  try {
    await requireApiPermission(request, "quality.write");
  } catch (error) {
    return requestError(error, "认证失败");
  }
  let form: FormData;
  try {
    form = await parseBoundedFormData(request, 9 * 1024 * 1024);
  } catch (error) {
    return requestError(error, "上传内容无法解析");
  }
  const modelCode = String(form.get("modelCode") ?? "").trim();
  const bodyViewRaw = String(form.get("bodyView") ?? "").trim().toUpperCase();
  const action = String(form.get("action") ?? "upload").trim().toLowerCase();
  const file = form.get("file");

  if (!modelCode) {
    return NextResponse.json({ error: "缺少 modelCode" }, { status: 400 });
  }
  if (modelCode.length > 100) {
    return NextResponse.json({ error: "车型代码不能超过 100 个字符" }, { status: 400 });
  }
  if (!isBodyView(bodyViewRaw)) {
    return NextResponse.json({ error: "bodyView 仅支持 RIGHT / LEFT / TOP / REAR" }, { status: 400 });
  }
  const bodyView = bodyViewRaw;
  const modelKey = normalizeModelImageKey(modelCode);
  const legacyKey = legacyModelKey(modelCode);

  try {
    return await withRuntimeFileLock(`${MANIFEST_PATH}.lock`, async () => {
      const manifest = await readManifest();
      const current = ownModelEntry(manifest.models, modelKey);
      const legacyEntry = legacyKey !== modelKey ? ownModelEntry(manifest.models, legacyKey) : undefined;
      if (legacyEntry || current) {
        manifest.models[modelKey] = { ...(legacyEntry ?? {}), ...(current ?? {}) };
      }
      if (legacyKey !== modelKey) {
        delete manifest.models[legacyKey];
      }
      if (!ownModelEntry(manifest.models, modelKey)) manifest.models[modelKey] = {};
      const previousUrl = manifest.models[modelKey][bodyView];

      if (action === "reset") {
        delete manifest.models[modelKey][bodyView];
        if (!Object.keys(manifest.models[modelKey]).length) delete manifest.models[modelKey];
        await writeManifest(manifest);
        await removeSupersededImage(previousUrl);
        return NextResponse.json({
          ok: true,
          action: "reset",
          model_code: modelCode,
          body_view: bodyView,
          url: builtinBodyMapImage(modelCode, bodyView),
          source: "builtin",
        });
      }

      if (action === "mirror-from-right") {
        if (bodyView !== "LEFT") {
          return NextResponse.json({ error: "仅左侧视图支持从右侧镜像生成" }, { status: 400 });
        }
        const rightUrl = resolveBodyMapImage(modelCode, "RIGHT", manifest).split("?")[0];
        const rightAbs = publicAssetPath(rightUrl);
        await mkdir(CUSTOM_DIR, { recursive: true });
        const outAbs = path.join(
          /*turbopackIgnore: true*/ CUSTOM_DIR,
          `${modelKey}_LEFT-${randomUUID()}.jpg`,
        );
        let storedUrl: string;
        try {
          await sharp(rightAbs).rotate().flop().jpeg({ quality: 92 }).toFile(outAbs);
          storedUrl = await commitImageRevision(
            manifest,
            modelKey,
            bodyView,
            outAbs,
            previousUrl,
          );
        } catch (error) {
          await rm(outAbs, { force: true }).catch(() => undefined);
          throw error;
        }
        return NextResponse.json({
          ok: true,
          action: "mirror-from-right",
          model_code: modelCode,
          body_view: bodyView,
          url: withCacheBust(storedUrl, Date.now()),
          source: "custom",
        });
      }

      if (!(file instanceof File)) {
        return NextResponse.json({ error: "请上传图片文件" }, { status: 400 });
      }
      const mime = (file.type || "").toLowerCase();
      if (!ALLOWED_MIME[mime]) {
        return NextResponse.json({ error: "仅支持 JPG / PNG / WebP" }, { status: 400 });
      }
      if (file.size > 8 * 1024 * 1024) {
        return NextResponse.json({ error: "图片不能超过 8MB" }, { status: 400 });
      }

      const bytes = Buffer.from(await file.arrayBuffer());
      const metadata = await sharp(bytes).metadata().catch(() => null);
      const detectedExt =
        metadata?.format === "jpeg"
          ? ".jpg"
          : metadata?.format === "png"
            ? ".png"
            : metadata?.format === "webp"
              ? ".webp"
              : null;
      if (!detectedExt) {
        return NextResponse.json({ error: "图片内容无效，仅支持 JPG / PNG / WebP" }, { status: 400 });
      }

      await mkdir(CUSTOM_DIR, { recursive: true });
      const outAbs = path.join(
        /*turbopackIgnore: true*/ CUSTOM_DIR,
        `${modelKey}_${bodyView}-${randomUUID()}${detectedExt}`,
      );
      let storedUrl: string;
      try {
        await writeFile(outAbs, bytes, { flag: "wx" });
        storedUrl = await commitImageRevision(
          manifest,
          modelKey,
          bodyView,
          outAbs,
          previousUrl,
        );
      } catch (error) {
        await rm(outAbs, { force: true }).catch(() => undefined);
        throw error;
      }

      return NextResponse.json({
        ok: true,
        action: "upload",
        model_code: modelCode,
        body_view: bodyView,
        url: withCacheBust(storedUrl, Date.now()),
        source: "custom",
      });
    });
  } catch (error) {
    return requestError(error, "底图保存失败");
  }
}
