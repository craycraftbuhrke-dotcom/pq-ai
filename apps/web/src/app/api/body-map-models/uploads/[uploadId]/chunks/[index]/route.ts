import { mkdir, writeFile } from "fs/promises";
import path from "path";

import { NextResponse } from "next/server";

import {
  readUploadMeta,
  uploadDir,
  writeUploadMeta,
} from "@/lib/body-map-model-store";

export const runtime = "nodejs";
export const maxDuration = 600;

type Context = { params: Promise<{ uploadId: string; index: string }> };

/** Receive one binary chunk. Body must stay under Ingress limits (≤512KB recommended). */
export async function PUT(request: Request, context: Context) {
  try {
    const { uploadId, index: indexRaw } = await context.params;
    const index = Number(indexRaw);
    if (!uploadId || !Number.isInteger(index) || index < 0) {
      return NextResponse.json({ error: "无效的分片参数" }, { status: 400 });
    }

    const meta = await readUploadMeta(uploadId);
    if (index >= meta.totalChunks) {
      return NextResponse.json({ error: "分片索引超出范围" }, { status: 400 });
    }

    const bytes = Buffer.from(await request.arrayBuffer());
    if (!bytes.length) {
      return NextResponse.json({ error: "空分片" }, { status: 400 });
    }
    if (bytes.length > meta.chunkSize + 1024) {
      return NextResponse.json({ error: "分片过大" }, { status: 413 });
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
  } catch (error) {
    const message = error instanceof Error ? error.message : "分片上传失败";
    const status = message.includes("ENOENT") ? 404 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}
