import { NextResponse } from "next/server";

import { apiRequestHeaders, isUpstreamTimeout, upstreamRequestSignal } from "@/lib/auth-data";
import { readBoundedRequestBody } from "@/lib/bounded-request-body";

export async function PUT(request: Request) {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return NextResponse.json({ error: "后端 API 地址未配置" }, { status: 503 });
  try {
    const headers = new Headers(await apiRequestHeaders(request));
    headers.set("Content-Type", "application/json");
    const body = await readBoundedRequestBody(request, 16 * 1024);
    const response = await fetch(`${apiUrl}/auth/me/password`, {
      method: "PUT",
      headers,
      body: body.toString("utf-8"),
      cache: "no-store",
      signal: upstreamRequestSignal(request),
    });
    const result = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    return NextResponse.json(response.ok ? result : { error: result.detail ?? "密码修改失败" }, {
      status: response.status,
    });
  } catch (error) {
    const clientStatus = (error as { status?: number }).status;
    if (typeof clientStatus === "number" && clientStatus >= 400 && clientStatus < 500) {
      return NextResponse.json(
        { error: error instanceof Error ? error.message : "密码修改请求无效" },
        { status: clientStatus },
      );
    }
    return NextResponse.json(
      { error: isUpstreamTimeout(error) ? "认证服务响应超时" : "无法连接认证服务" },
      { status: isUpstreamTimeout(error) ? 504 : 502 },
    );
  }
}
