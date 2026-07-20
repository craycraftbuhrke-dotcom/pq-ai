import { NextResponse } from "next/server";

import { apiRequestHeaders, isUpstreamTimeout, upstreamRequestSignal } from "@/lib/auth-data";
import { readBoundedRequestBody } from "@/lib/bounded-request-body";

const SECURITY_REQUEST_MAX_BYTES = 64 * 1024;

type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: Request, context: Context) {
  const { path } = await context.params;
  if (!path.length || !new Set(["users", "roles", "api-keys"]).has(path[0])) {
    return NextResponse.json({ error: "不支持的用户与权限接口" }, { status: 404 });
  }
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return NextResponse.json({ error: "后端 API 地址未配置" }, { status: 503 });
  const headers = new Headers(await apiRequestHeaders(request));
  try {
    const body = request.method === "GET"
      ? undefined
      : (await readBoundedRequestBody(request, SECURITY_REQUEST_MAX_BYTES)).toString("utf-8");
    if (body) headers.set("Content-Type", request.headers.get("content-type") ?? "application/json");
    const response = await fetch(
      `${apiUrl}/security/${path.map(encodeURIComponent).join("/")}${new URL(request.url).search}`,
      {
        method: request.method,
        headers,
        body,
        cache: "no-store",
        signal: upstreamRequestSignal(request),
      },
    );
    if (response.status === 204) return new NextResponse(null, { status: 204 });
    const result = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    return NextResponse.json(response.ok ? result : { error: result.detail ?? "用户与权限操作失败" }, {
      status: response.status,
    });
  } catch (error) {
    const clientStatus = (error as { status?: number }).status;
    if (clientStatus === 400 || clientStatus === 413) {
      return NextResponse.json(
        { error: error instanceof Error ? error.message : "用户与权限请求无效" },
        { status: clientStatus },
      );
    }
    return NextResponse.json(
      { error: isUpstreamTimeout(error) ? "用户与权限服务响应超时" : "无法连接用户与权限服务" },
      { status: isUpstreamTimeout(error) ? 504 : 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
