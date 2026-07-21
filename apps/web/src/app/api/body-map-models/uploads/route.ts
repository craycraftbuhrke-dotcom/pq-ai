import { randomUUID } from "crypto";

import { NextResponse } from "next/server";

import {
  BODY_MAP_CHUNK_SIZE,
  BODY_MODEL_MAX_UPLOAD_BYTES,
  assertRuntimeStorageReadyForUpload,
  garbageCollectExpiredUploads,
  isGlbName,
  isStpName,
  writeUploadMeta,
  type UploadSessionMeta,
} from "@/lib/body-map-model-store";
import { requireApiPermission } from "@/lib/auth-data";
import { parseBoundedJson } from "@/lib/bounded-request-body";

export const runtime = "nodejs";
export const maxDuration = 600;

/** Start a chunked upload session (avoids platform Ingress 413 on large STP/GLB). */
export async function POST(request: Request) {
  try {
    await requireApiPermission(request, "quality.write");
    await assertRuntimeStorageReadyForUpload();
    await garbageCollectExpiredUploads();
    const body = await parseBoundedJson<{
      modelCode?: string;
      fileName?: string;
      totalSize?: number;
      chunkSize?: number;
    }>(request, 32 * 1024);
    const modelCode = String(body.modelCode ?? "").trim();
    const fileName = String(body.fileName ?? "").trim();
    const totalSize = Number(body.totalSize ?? 0);
    const chunkSize = Math.min(
      Math.max(Number(body.chunkSize ?? BODY_MAP_CHUNK_SIZE) || BODY_MAP_CHUNK_SIZE, 64 * 1024),
      BODY_MAP_CHUNK_SIZE,
    );

    if (!modelCode) return NextResponse.json({ error: "缺少 modelCode" }, { status: 400 });
    if (!fileName) return NextResponse.json({ error: "缺少 fileName" }, { status: 400 });
    if (modelCode.length > 100 || fileName.length > 255) {
      return NextResponse.json({ error: "车型代码或文件名过长" }, { status: 400 });
    }
    if (!Number.isSafeInteger(totalSize) || totalSize <= 0) {
      return NextResponse.json({ error: "无效的 totalSize" }, { status: 400 });
    }
    if (totalSize > BODY_MODEL_MAX_UPLOAD_BYTES) {
      return NextResponse.json(
        { error: `文件超过允许大小（最大 ${Math.floor(BODY_MODEL_MAX_UPLOAD_BYTES / 1024 / 1024)} MB）` },
        { status: 413 },
      );
    }
    if (!isStpName(fileName) && !isGlbName(fileName)) {
      return NextResponse.json({ error: "仅支持 GLB / GLTF / STP / STEP" }, { status: 400 });
    }

    const totalChunks = Math.ceil(totalSize / chunkSize);
    const uploadId = randomUUID();
    const meta: UploadSessionMeta = {
      uploadId,
      modelCode,
      fileName,
      totalSize,
      chunkSize,
      totalChunks,
      received: [],
      createdAt: Date.now(),
    };
    await writeUploadMeta(meta);

    return NextResponse.json({
      ok: true,
      uploadId,
      chunkSize,
      totalChunks,
    });
  } catch (error) {
    const status = (error as { status?: number }).status;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "创建上传会话失败" },
      { status: typeof status === "number" ? status : 500 },
    );
  }
}
