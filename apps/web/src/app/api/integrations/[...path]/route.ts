import { NextResponse } from "next/server";

import { apiRequestHeaders, isUpstreamTimeout, upstreamRequestSignal } from "@/lib/auth-data";

const allowedRoots = new Set(["summary", "endpoints", "events"]);

type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: Request, context: Context) {
  const { path } = await context.params;
  if (!path.length || !allowedRoots.has(path[0])) {
    return NextResponse.json({ error: "不支持的集成接口" }, { status: 404 });
  }
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return NextResponse.json({ error: "后端 API 地址未配置" }, { status: 503 });
  const headers = new Headers(await apiRequestHeaders(request));
  let body: string | undefined;
  if (request.method !== "GET") {
    headers.set("Content-Type", "application/json");
    body = await request.text();
  }
  try {
    const response = await fetch(
      `${apiUrl}/integrations/${path.map(encodeURIComponent).join("/")}${new URL(request.url).search}`,
      { method: request.method, headers, body, cache: "no-store", signal: upstreamRequestSignal(request, 60_000) },
    );
    if (response.status === 204) return new NextResponse(null, { status: 204 });
    const result = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    if (!response.ok) {
      return NextResponse.json({ error: result.detail ?? "后端集成服务返回错误" }, { status: response.status });
    }
    return NextResponse.json(result, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { error: isUpstreamTimeout(error) ? "集成服务响应超时" : "无法连接后端集成服务" },
      { status: isUpstreamTimeout(error) ? 504 : 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
