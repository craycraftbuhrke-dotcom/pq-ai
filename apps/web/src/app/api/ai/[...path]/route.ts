import { NextResponse } from "next/server";

import { apiRequestHeaders, isUpstreamTimeout, upstreamRequestSignal } from "@/lib/auth-data";
import { BULK_IMPORT_MAX_BYTES, readBoundedRequestBody } from "@/lib/bounded-request-body";

const allowedRoots = new Set([
  "overview-summary",
  "models",
  "predictions",
  "diagnoses",
  "recommendations",
  "controlled-trials",
  "rollback-executions",
  "evaluations",
]);

type Context = { params: Promise<{ path: string[] }> };

function formatUpstreamDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return null;
      })
      .filter((item): item is string => Boolean(item));
    if (parts.length) return parts.join("；");
  }
  if (detail && typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    if (typeof record.message === "string") {
      const errors = Array.isArray(record.errors)
        ? record.errors.filter((item): item is string => typeof item === "string")
        : [];
      return errors.length
        ? `${record.message}：${errors.slice(0, 20).join("；")}`
        : record.message;
    }
  }
  return fallback;
}

async function proxy(request: Request, context: Context) {
  const { path } = await context.params;
  if (!path.length || !allowedRoots.has(path[0])) {
    return NextResponse.json({ error: "不支持的智能分析操作" }, { status: 404 });
  }
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return NextResponse.json({ error: "后端 API 地址未配置" }, { status: 503 });
  const headers = new Headers(await apiRequestHeaders(request));
  try {
    let body: ArrayBuffer | undefined;
    if (request.method !== "GET") {
      const bytes = await readBoundedRequestBody(request, BULK_IMPORT_MAX_BYTES);
      const copy = new Uint8Array(bytes.length);
      copy.set(bytes);
      body = copy.buffer;
      headers.set("Content-Type", request.headers.get("content-type") ?? "application/json");
    }
    const response = await fetch(
      `${apiUrl}/ai/${path.map(encodeURIComponent).join("/")}${new URL(request.url).search}`,
      { method: request.method, headers, body, cache: "no-store", signal: upstreamRequestSignal(request) },
    );
    if (response.status === 204) return new NextResponse(null, { status: 204 });
    const contentType = response.headers.get("content-type") ?? "";
    if (!response.ok) {
      const result = contentType.includes("application/json")
        ? ((await response.json().catch(() => ({}))) as Record<string, unknown>)
        : {};
      return NextResponse.json(
        { error: formatUpstreamDetail(result.detail, "后端 AI 服务返回错误") },
        { status: response.status },
      );
    }
    if (contentType.includes("application/json")) {
      return NextResponse.json(await response.json(), { status: response.status });
    }
    const resultHeaders = new Headers();
    resultHeaders.set("Content-Type", contentType || "application/octet-stream");
    const disposition = response.headers.get("content-disposition");
    if (disposition) resultHeaders.set("Content-Disposition", disposition);
    return new NextResponse(await response.arrayBuffer(), {
      status: response.status,
      headers: resultHeaders,
    });
  } catch (error) {
    const status = (error as { status?: number }).status;
    if (typeof status === "number") {
      return NextResponse.json(
        { error: error instanceof Error ? error.message : "上传文件无效" },
        { status },
      );
    }
    return NextResponse.json(
      { error: isUpstreamTimeout(error) ? "AI 服务响应超时" : "无法连接后端 AI 服务" },
      { status: isUpstreamTimeout(error) ? 504 : 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
