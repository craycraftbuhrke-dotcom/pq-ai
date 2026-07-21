import { mkdir, writeFile } from "fs/promises";
import path from "path";

import { NextResponse } from "next/server";

import {
  readUploadMeta,
  uploadDir,
  writeUploadMeta,
} from "@/lib/body-map-model-store";
import { requireApiPermission } from "@/lib/auth-data";
import { readBoundedRequestBody } from "@/lib/bounded-request-body";
import { withRuntimeFileLock } from "@/lib/runtime-file-lock";

export const runtime = "nodejs";
export const maxDuration = 600;

type Context = { params: Promise<{ uploadId: string; index: string }> };

/**
 * Receive one binary chunk via POST (not PUT).
 * Many Xiaomi/K8s Ingress setups only allow GET/POST and return 404 for PUT.
 */
async function receiveChunk(request: Request, context: Context) {
  try {
    await requireApiPermission(request, "quality.write");
    const { uploadId, index: indexRaw } = await context.params;
    const index = Number(indexRaw);
    if (!uploadId || !Number.isInteger(index) || index < 0) {
      return NextResponse.json({ error: "无效的分片参数" }, { status: 400 });
    }

    let initialMeta;
    try {
      initialMeta = await readUploadMeta(uploadId);
    } catch (error) {
      const status = (error as { status?: number }).status;
      const message =
        error instanceof Error
          ? error.message
          : "上传会话不存在或已过期，请重新选择文件上传";
      return NextResponse.json(
        { error: message },
        { status: typeof status === "number" ? status : 404 },
      );
    }
    if (index >= initialMeta.totalChunks) {
      return NextResponse.json({ error: "分片索引超出范围" }, { status: 400 });
    }

    const contentType = (request.headers.get("content-type") ?? "").toLowerCase();
    const boundedBody = await readBoundedRequestBody(request, initialMeta.chunkSize + 64 * 1024);
    let bytes: Buffer;
    if (contentType.includes("multipart/form-data")) {
      const form = await new Response(new Uint8Array(boundedBody), {
        headers: { "content-type": request.headers.get("content-type") ?? "" },
      }).formData();
      const part = form.get("chunk") ?? form.get("file");
      if (typeof part === "string" || !part) {
        return NextResponse.json({ error: "缺少 chunk 字段" }, { status: 400 });
      }
      bytes = Buffer.from(await part.arrayBuffer());
    } else {
      bytes = boundedBody;
    }

    if (!bytes.length) {
      return NextResponse.json({ error: "空分片" }, { status: 400 });
    }
    if (bytes.length > initialMeta.chunkSize + 1024) {
      return NextResponse.json({ error: "分片过大" }, { status: 413 });
    }

    return await withRuntimeFileLock(`${uploadDir(uploadId)}.lock`, async () => {
      const meta = await readUploadMeta(uploadId);
      if (index >= meta.totalChunks || meta.chunkSize !== initialMeta.chunkSize) {
        return NextResponse.json({ error: "上传会话已变化，请重新上传" }, { status: 409 });
      }

      const dir = uploadDir(uploadId);
      await mkdir(dir, { recursive: true });
      await writeFile(path.join(dir, `chunk-${index}.part`), bytes);

      if (!meta.received.includes(index)) {
        meta.received.push(index);
        meta.received.sort((a, b) => a - b);
        await writeUploadMeta(meta);
      }

      return NextResponse.json({
        ok: true,
        uploadId,
        index,
        received: meta.received.length,
        totalChunks: meta.totalChunks,
      });
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "分片上传失败";
    const status = (error as { status?: number }).status;
    return NextResponse.json({ error: message }, { status: typeof status === "number" ? status : 500 });
  }
}

export const POST = receiveChunk;
/** Kept for local/dev clients; production Ingress often blocks PUT. */
export const PUT = receiveChunk;
