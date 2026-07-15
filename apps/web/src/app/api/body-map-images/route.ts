import { spawnSync } from "child_process";
import { existsSync } from "fs";
import { mkdir, readFile, writeFile } from "fs/promises";
import path from "path";

import { NextResponse } from "next/server";

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

export const runtime = "nodejs";

function resolvePublicDir(): string {
  const candidates = [path.join(process.cwd(), "public"), path.join(process.cwd(), "apps", "web", "public")];
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  return candidates[0];
}

const PUBLIC_DIR = resolvePublicDir();
const MANIFEST_PATH = path.join(PUBLIC_DIR, "body-maps", "view-images.json");
const CUSTOM_DIR = path.join(PUBLIC_DIR, "body-maps", "custom");

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
  } catch {
    return { ...EMPTY_BODY_MAP_IMAGE_MANIFEST, models: {} };
  }
}

async function writeManifest(manifest: BodyMapImageManifest): Promise<void> {
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
  const key = normalizeModelImageKey(modelCode);
  const overrides = manifest.models[key] ?? {};
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
  const form = await request.formData();
  const modelCode = String(form.get("modelCode") ?? "").trim();
  const bodyViewRaw = String(form.get("bodyView") ?? "").trim().toUpperCase();
  const action = String(form.get("action") ?? "upload").trim().toLowerCase();
  const file = form.get("file");

  if (!modelCode) {
    return NextResponse.json({ error: "缺少 modelCode" }, { status: 400 });
  }
  if (!isBodyView(bodyViewRaw)) {
    return NextResponse.json({ error: "bodyView 仅支持 RIGHT / LEFT / TOP / REAR" }, { status: 400 });
  }
  const bodyView = bodyViewRaw;
  const modelKey = normalizeModelImageKey(modelCode);
  const manifest = await readManifest();
  if (!manifest.models[modelKey]) manifest.models[modelKey] = {};

  try {
    if (action === "reset") {
      delete manifest.models[modelKey][bodyView];
      if (!Object.keys(manifest.models[modelKey]).length) delete manifest.models[modelKey];
      await writeManifest(manifest);
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
      const rightAbs = path.join(PUBLIC_DIR, rightUrl.replace(/^\//, "").replace(/\//g, path.sep));
      await mkdir(CUSTOM_DIR, { recursive: true });
      const outAbs = path.join(CUSTOM_DIR, `${modelKey}_LEFT_mirror.jpg`);
      const script = [
        "from PIL import Image",
        "from pathlib import Path",
        `src = Path(r'''${rightAbs}''')`,
        `dst = Path(r'''${outAbs}''')`,
        "Image.open(src).transpose(Image.FLIP_LEFT_RIGHT).convert('RGB').save(dst, quality=92, optimize=True)",
      ].join("\n");
      const result = spawnSync("python", ["-c", script], { encoding: "utf-8" });
      if (result.status !== 0) {
        return NextResponse.json(
          { error: result.stderr || result.stdout || "镜像生成失败，请确认已安装 Pillow" },
          { status: 500 },
        );
      }
      const storedUrl = publicUrlForFile(outAbs);
      manifest.models[modelKey][bodyView] = storedUrl;
      await writeManifest(manifest);
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
    const ext = ALLOWED_MIME[mime];
    if (!ext) {
      return NextResponse.json({ error: "仅支持 JPG / PNG / WebP" }, { status: 400 });
    }
    if (file.size > 8 * 1024 * 1024) {
      return NextResponse.json({ error: "图片不能超过 8MB" }, { status: 400 });
    }

    await mkdir(CUSTOM_DIR, { recursive: true });
    const outAbs = path.join(CUSTOM_DIR, `${modelKey}_${bodyView}${ext}`);
    await writeFile(outAbs, Buffer.from(await file.arrayBuffer()));
    const storedUrl = publicUrlForFile(outAbs);
    manifest.models[modelKey][bodyView] = storedUrl;
    await writeManifest(manifest);

    return NextResponse.json({
      ok: true,
      action: "upload",
      model_code: modelCode,
      body_view: bodyView,
      url: withCacheBust(storedUrl, Date.now()),
      source: "custom",
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "底图保存失败" },
      { status: 500 },
    );
  }
}
