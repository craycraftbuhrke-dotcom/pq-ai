import { NextResponse } from "next/server";

import {
  assembleUpload,
  cleanupUpload,
  parseBounds,
  persistUploadedModel,
  readUploadMeta,
} from "@/lib/body-map-model-store";

export const runtime = "nodejs";
export const maxDuration = 600;

type Context = { params: Promise<{ uploadId: string }> };

/** Assemble chunks on disk, convert STP→GLB via pod-local backend, update manifest. */
export async function POST(request: Request, context: Context) {
  const { uploadId } = await context.params;
  try {
    const body = (await request.json().catch(() => ({}))) as {
      upAxis?: string;
      unitScale?: string | number;
      bounds?: string;
    };
    const meta = await readUploadMeta(uploadId);
    if (meta.received.length !== meta.totalChunks) {
      return NextResponse.json(
        {
          error: `分片未齐：已收 ${meta.received.length}/${meta.totalChunks}`,
        },
        { status: 400 },
      );
    }

    const sourcePath = await assembleUpload(uploadId);
    const unitScaleRaw = parseFloat(String(body.unitScale ?? ""));
    const result = await persistUploadedModel({
      modelCode: meta.modelCode,
      fileName: meta.fileName,
      upAxis: String(body.upAxis ?? "Y").trim() || "Y",
      unitScaleRaw,
      bounds: parseBounds(String(body.bounds ?? "")),
      sourcePath,
      request,
    });

    await cleanupUpload(uploadId);

    return NextResponse.json({
      ok: true,
      action: "upload",
      model_code: result.model_code,
      entry: result.entry,
      source: "custom",
      source_format: result.source_format,
      convert_engine: result.convert_engine,
      upload: "chunked",
    });
  } catch (error) {
    const status = (error as { status?: number }).status;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "完成上传失败" },
      { status: typeof status === "number" && status >= 400 && status < 600 ? status : 500 },
    );
  }
}
