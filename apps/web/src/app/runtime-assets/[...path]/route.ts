import { createReadStream } from "fs";
import { realpath, stat } from "fs/promises";
import { Readable } from "stream";
import path from "path";

import { NextResponse } from "next/server";

import { requireApiActor } from "@/lib/auth-data";
import { resolveRuntimeAssetDir } from "@/lib/body-map-model-store";

export const runtime = "nodejs";

type Context = { params: Promise<{ path: string[] }> };

const CONTENT_TYPES: Record<string, string> = {
  ".glb": "model/gltf-binary",
  ".gltf": "model/gltf+json",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
};

function resolveRuntimeFile(root: string, parts: string[]): string {
  if (
    parts.length < 3 ||
    !["body-models", "body-maps"].includes(parts[0]) ||
    parts[1] !== "custom" ||
    parts.some((part) => !part || part === "." || part === ".." || part.startsWith("."))
  ) {
    throw Object.assign(new Error("资源路径无效"), { status: 400 });
  }
  const resolved = path.resolve(/*turbopackIgnore: true*/ root, ...parts);
  if (!resolved.startsWith(`${root}${path.sep}`)) {
    throw Object.assign(new Error("资源路径越界"), { status: 400 });
  }
  return resolved;
}

function parseRange(value: string | null, size: number): { start: number; end: number } | null {
  if (!value) return null;
  const match = /^bytes=(\d+)-(\d*)$/.exec(value.trim());
  if (!match) throw Object.assign(new Error("Range 请求格式无效"), { status: 416 });
  const start = Number(match[1]);
  const end = match[2] ? Number(match[2]) : size - 1;
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 0 || start > end || end >= size) {
    throw Object.assign(new Error("Range 请求超出文件范围"), { status: 416 });
  }
  return { start, end };
}

export async function GET(request: Request, context: Context) {
  try {
    await requireApiActor(request);
    const parts = (await context.params).path;
    const runtimeRoot = await realpath(resolveRuntimeAssetDir());
    const filePath = resolveRuntimeFile(runtimeRoot, parts);
    const actualPath = await realpath(filePath);
    if (!actualPath.startsWith(`${runtimeRoot}${path.sep}`)) {
      return NextResponse.json({ error: "资源路径越界" }, { status: 400 });
    }
    const fileStat = await stat(actualPath);
    if (!fileStat.isFile()) return NextResponse.json({ error: "资源不存在" }, { status: 404 });

    const range = parseRange(request.headers.get("range"), fileStat.size);
    const start = range?.start ?? 0;
    const end = range?.end ?? fileStat.size - 1;
    const stream = Readable.toWeb(createReadStream(actualPath, { start, end }));
    const headers = new Headers({
      "Accept-Ranges": "bytes",
      "Cache-Control": "private, no-cache",
      "Content-Length": String(end - start + 1),
      "Content-Type": CONTENT_TYPES[path.extname(actualPath).toLowerCase()] ?? "application/octet-stream",
      "X-Content-Type-Options": "nosniff",
    });
    if (range) headers.set("Content-Range", `bytes ${start}-${end}/${fileStat.size}`);
    return new Response(stream as ReadableStream, { status: range ? 206 : 200, headers });
  } catch (error) {
    const status = (error as { status?: number }).status;
    const code = (error as NodeJS.ErrnoException).code;
    if (typeof status !== "number") {
      return NextResponse.json(
        { error: code === "ENOENT" || code === "ENOTDIR" ? "资源不存在" : "资源读取失败" },
        { status: code === "ENOENT" || code === "ENOTDIR" ? 404 : 500 },
      );
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "资源读取失败" },
      { status },
    );
  }
}
