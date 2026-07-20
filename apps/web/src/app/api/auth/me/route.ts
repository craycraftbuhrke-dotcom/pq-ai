import { NextResponse } from "next/server";

import { apiRequestHeaders, isUpstreamTimeout, upstreamRequestSignal } from "@/lib/auth-data";
import { readBoundedRequestBody } from "@/lib/bounded-request-body";

async function proxy(request: Request) {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    return NextResponse.json({ error: "后端 API 地址未配置" }, { status: 503 });
  }
  try {
    const headers = new Headers(await apiRequestHeaders(request));
    const body = request.method === "GET"
      ? undefined
      : (await readBoundedRequestBody(request, 64 * 1024)).toString("utf-8");
    if (body) headers.set("Content-Type", "application/json");
    const response = await fetch(`${apiUrl}/auth/me`, {
      method: request.method,
      body,
      headers,
      cache: "no-store",
      signal: upstreamRequestSignal(request),
    });
    const result = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    return NextResponse.json(response.ok ? { actor: result } : { error: result.detail ?? "登录已失效" }, {
      status: response.status,
    });
  } catch (error) {
    const clientStatus = (error as { status?: number }).status;
    if (typeof clientStatus === "number" && clientStatus >= 400 && clientStatus < 500) {
      return NextResponse.json(
        { error: error instanceof Error ? error.message : "个人资料请求无效" },
        { status: clientStatus },
      );
    }
    return NextResponse.json(
      { error: isUpstreamTimeout(error) ? "认证服务响应超时" : "无法连接认证服务" },
      { status: isUpstreamTimeout(error) ? 504 : 502 },
    );
  }
}

export const GET = proxy;
export const PUT = proxy;
