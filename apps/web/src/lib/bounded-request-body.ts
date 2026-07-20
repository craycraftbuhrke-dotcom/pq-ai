import "server-only";

export const BULK_IMPORT_MAX_BYTES = (() => {
  const configured = Number(process.env.BULK_IMPORT_MAX_BYTES);
  return Number.isSafeInteger(configured) && configured > 0 ? configured : 50 * 1024 * 1024;
})();

export async function readBoundedRequestBody(request: Request, maxBytes: number): Promise<Buffer> {
  const declared = request.headers.get("content-length");
  if (declared !== null) {
    const parsed = Number(declared);
    if (!Number.isSafeInteger(parsed) || parsed < 0) {
      throw Object.assign(new Error("Content-Length 无效"), { status: 400 });
    }
    if (parsed > maxBytes) {
      throw Object.assign(new Error("请求内容超过允许大小"), { status: 413 });
    }
  }

  if (!request.body) return Buffer.alloc(0);
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) {
        await reader.cancel("request body too large").catch(() => undefined);
        throw Object.assign(new Error("请求内容超过允许大小"), { status: 413 });
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  return Buffer.concat(chunks.map((chunk) => Buffer.from(chunk)), total);
}

export async function parseBoundedFormData(request: Request, maxBytes: number): Promise<FormData> {
  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("multipart/form-data")) {
    throw Object.assign(new Error("请求必须使用 multipart/form-data"), { status: 400 });
  }
  const bytes = await readBoundedRequestBody(request, maxBytes);
  return new Response(new Uint8Array(bytes), { headers: { "content-type": contentType } }).formData();
}

export async function parseBoundedJson<T>(request: Request, maxBytes: number): Promise<T> {
  const bytes = await readBoundedRequestBody(request, maxBytes);
  try {
    return JSON.parse(bytes.toString("utf-8")) as T;
  } catch {
    throw Object.assign(new Error("请求 JSON 无效"), { status: 400 });
  }
}
