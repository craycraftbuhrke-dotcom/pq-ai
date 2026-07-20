import { NextResponse } from "next/server";

import {
  assembleUpload,
  cleanupUpload,
  findCompletedUpload,
  parseBounds,
  persistUploadedModel,
  readUploadMeta,
  uploadDir,
} from "@/lib/body-map-model-store";
import { requireApiPermission } from "@/lib/auth-data";
import { parseBoundedJson } from "@/lib/bounded-request-body";
import { withRuntimeFileLock } from "@/lib/runtime-file-lock";

export const runtime = "nodejs";
export const maxDuration = 600;

type Context = { params: Promise<{ uploadId: string }> };

/** Assemble chunks on disk, convert STP→GLB via pod-local backend, update manifest. */
export async function POST(request: Request, context: Context) {
  const { uploadId } = await context.params;
  try {
    await requireApiPermission(request, "quality.write");
    const body = await parseBoundedJson<{
      upAxis?: string;
      unitScale?: string | number;
      bounds?: string;
    }>(request, 32 * 1024);
    return await withRuntimeFileLock(`${uploadDir(uploadId)}.lock`, async () => {
      const completed = await findCompletedUpload(uploadId);
      if (completed) {
        await cleanupUpload(uploadId).catch(() => undefined);
        return NextResponse.json({
          ok: true,
          action: "upload",
          model_code: completed.model_code,
          entry: completed.entry,
          source: "custom",
          source_format: completed.source_format,
          convert_engine: completed.convert_engine,
          upload: "chunked",
          replayed: true,
        });
      }
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
        uploadId,
      });

      await cleanupUpload(uploadId).catch(() => undefined);

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
    });
  } catch (error) {
    const status = (error as { status?: number }).status;
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "完成上传失败" },
      { status: typeof status === "number" && status >= 400 && status < 600 ? status : 500 },
    );
  }
}
