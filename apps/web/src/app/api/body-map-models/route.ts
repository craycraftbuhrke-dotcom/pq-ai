import { mkdir, unlink, writeFile } from "fs/promises";
import path from "path";

import { NextResponse } from "next/server";

import {
  CUSTOM_DIR,
  MANIFEST_PATH,
  MODEL_3D_ASSETS,
  fileExtension,
  isGlbName,
  isStpName,
  normalizeModelKey,
  parseBounds,
  persistUploadedModel,
  readManifest,
  removeStoredModelArtifacts,
  writeManifest,
} from "@/lib/body-map-model-store";
import {
  legacyModelKey,
  ownModelEntry,
  resolveBodyModel,
  resolveCustomBodyModel,
  type BodyModelEntry,
} from "@/lib/body-map-models";
import { requireApiActor, requireApiPermission } from "@/lib/auth-data";
import { parseBoundedFormData } from "@/lib/bounded-request-body";
import { withRuntimeFileLock } from "@/lib/runtime-file-lock";

export const runtime = "nodejs";
export const maxDuration = 600;

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
  const key = normalizeModelKey(modelCode);
  const customEntry = resolveCustomBodyModel(modelCode, manifest);
  const entry = customEntry ?? resolveBodyModel(modelCode, manifest);
  return NextResponse.json({
    model_code: modelCode,
    model_key: key,
    entry,
    source: customEntry ? "custom" : entry.url ? "builtin" : "none",
    manifest_path: "/body-models/view-models.json",
  });
}

/** Reset + tiny single-shot upload. Large files use /api/body-map-models/uploads. */
export async function POST(request: Request) {
  try {
    await requireApiPermission(request, "quality.write");
  } catch (error) {
    return requestError(error, "认证失败");
  }
  let form: FormData;
  try {
    form = await parseBoundedFormData(request, 512 * 1024);
  } catch (error) {
    return requestError(error, "上传内容无法解析");
  }
  const modelCode = String(form.get("modelCode") ?? "").trim();
  const action = String(form.get("action") ?? "upload").trim().toLowerCase();
  const file = form.get("file");

  if (!modelCode) {
    return NextResponse.json({ error: "缺少 modelCode" }, { status: 400 });
  }
  if (modelCode.length > 100) {
    return NextResponse.json({ error: "车型代码不能超过 100 个字符" }, { status: 400 });
  }
  const modelKey = normalizeModelKey(modelCode);

  try {
    if (action === "reset") {
      await withRuntimeFileLock(`${MANIFEST_PATH}.lock`, async () => {
        const manifest = await readManifest();
        const superseded = [
          ownModelEntry(manifest.models, modelKey),
          ownModelEntry(manifest.models, legacyModelKey(modelCode)),
        ].filter((entry): entry is BodyModelEntry => entry !== undefined);
        if (ownModelEntry(manifest.models, modelKey)) delete manifest.models[modelKey];
        const legacyKey = legacyModelKey(modelCode);
        if (ownModelEntry(manifest.models, legacyKey)) delete manifest.models[legacyKey];
        await writeManifest(manifest);
        await Promise.all(superseded.map((entry) => removeStoredModelArtifacts(entry)));
      });
      return NextResponse.json({
        ok: true,
        action: "reset",
        model_code: modelCode,
        entry: ownModelEntry(MODEL_3D_ASSETS, modelKey) ?? { url: null, up_axis: "Y", unit_scale: 1.0 },
        source: ownModelEntry(MODEL_3D_ASSETS, modelKey) ? "builtin" : "none",
      });
    }

    if (!(file instanceof File)) {
      return NextResponse.json({ error: "请上传 GLB/GLTF 或 STP/STEP 文件" }, { status: 400 });
    }
    if (file.name.length > 255) {
      return NextResponse.json({ error: "文件名不能超过 255 个字符" }, { status: 400 });
    }

    if (file.size > 400 * 1024) {
      return NextResponse.json(
        {
          error: "文件较大，请使用分片上传",
          code: "USE_CHUNKED_UPLOAD",
        },
        { status: 413 },
      );
    }

    if (!isStpName(file.name) && !isGlbName(file.name)) {
      return NextResponse.json({ error: "仅支持 GLB / GLTF / STP / STEP" }, { status: 400 });
    }

    const tmpDir = path.join(CUSTOM_DIR, ".tmp");
    await mkdir(tmpDir, { recursive: true });
    const sourcePath = path.join(
      tmpDir,
      `${modelKey}-${Date.now()}${fileExtension(file.name) || ".bin"}`,
    );
    await writeFile(sourcePath, Buffer.from(await file.arrayBuffer()));

    try {
      const result = await persistUploadedModel({
        modelCode,
        fileName: file.name,
        upAxis: String(form.get("upAxis") ?? "Y").trim() || "Y",
        unitScaleRaw: parseFloat(String(form.get("unitScale") ?? "")),
        bounds: parseBounds(String(form.get("bounds") ?? "")),
        sourcePath,
        request,
      });
      return NextResponse.json({
        ok: true,
        action: "upload",
        model_code: result.model_code,
        entry: result.entry,
        source: "custom",
        source_format: result.source_format,
        convert_engine: result.convert_engine,
      });
    } finally {
      await unlink(sourcePath).catch(() => undefined);
    }
  } catch (error) {
    const status = (error as { status?: number }).status;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "模型保存失败" },
      { status: typeof status === "number" && status >= 400 && status < 600 ? status : 500 },
    );
  }
}
