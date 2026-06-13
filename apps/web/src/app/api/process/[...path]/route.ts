import { NextResponse } from "next/server";

import { apiRequestHeaders } from "@/lib/auth-data";

const allowedRoots = new Set([
  "spray-programs",
  "program-versions",
  "brushes",
  "brush-parameters",
  "parameter-definitions",
  "production-runs",
  "production-stage-runs",
  "actual-parameters",
  "material-batches",
  "material-governance",
  "robot-governance",
]);

type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: Request, context: Context) {
  const { path } = await context.params;
  if (!path.length || !allowedRoots.has(path[0])) {
    return NextResponse.json({ error: "不支持的工艺数据接口" }, { status: 404 });
  }
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    return NextResponse.json({ error: "后端 API 地址未配置" }, { status: 503 });
  }
  const headers = new Headers(apiRequestHeaders());
  let body: string | undefined;
  if (!["GET", "DELETE"].includes(request.method)) {
    headers.set("Content-Type", "application/json");
    body = await request.text();
  }
  try {
    const response = await fetch(
      `${apiUrl}/${path.map(encodeURIComponent).join("/")}${new URL(request.url).search}`,
      { method: request.method, headers, body, cache: "no-store" },
    );
    if (response.status === 204) return new NextResponse(null, { status: 204 });
    const result = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    if (!response.ok) {
      return NextResponse.json(
        { error: result.detail ?? "后端工艺服务返回错误" },
        { status: response.status },
      );
    }
    return NextResponse.json(result, { status: response.status });
  } catch {
    return NextResponse.json({ error: "无法连接后端工艺服务" }, { status: 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
