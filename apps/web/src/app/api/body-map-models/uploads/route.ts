import { randomUUID } from "crypto";

import { NextResponse } from "next/server";

import {
  BODY_MAP_CHUNK_SIZE,
  isGlbName,
  isStpName,
  writeUploadMeta,
  type UploadSessionMeta,
} from "@/lib/body-map-model-store";

export const runtime = "nodejs";
export const maxDuration = 600;

/** Start a chunked upload session (avoids platform Ingress 413 on large STP/GLB). */
export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      modelCode?: string;
      fileName?: string;
      totalSize?: number;
      chunkSize?: number;
    };
    const modelCode = String(body.modelCode ?? "").trim();
    const fileName = String(body.fileName ?? "").trim();
    const totalSize = Number(body.totalSize ?? 0);
    const chunkSize = Math.min(
      Math.max(Number(body.chunkSize ?? BODY_MAP_CHUNK_SIZE) || BODY_MAP_CHUNK_SIZE, 64 * 1024),
      BODY_MAP_CHUNK_SIZE,
    );

    if (!modelCode) return NextResponse.json({ error: "缺少 modelCode" }, { status: 400 });
    if (!fileName) return NextResponse.json({ error: "缺少 fileName" }, { status: 400 });
    if (!Number.isFinite(totalSize) || totalSize <= 0) {
      return NextResponse.json({ error: "无效的 totalSize" }, { status: 400 });
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
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "创建上传会话失败" },
      { status: 500 },
    );
  }
}
