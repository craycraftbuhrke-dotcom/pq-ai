import { NextResponse } from "next/server";

import { apiRequestHeaders, isUpstreamTimeout, upstreamRequestSignal } from "@/lib/auth-data";

const privateNoStore = { "Cache-Control": "private, no-store" };

export async function GET(request: Request) {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    return NextResponse.json(
      { error: "后端 API 地址未配置" },
      { status: 503, headers: privateNoStore },
    );
  }
  try {
    const response = await fetch(`${apiUrl}/dashboard`, {
      headers: await apiRequestHeaders(request),
      cache: "no-store",
      signal: upstreamRequestSignal(request),
    });
    const result = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    return NextResponse.json(response.ok ? result : { error: result.detail ?? "总览数据加载失败" }, {
      status: response.status,
      headers: privateNoStore,
    });
  } catch (error) {
    return NextResponse.json(
      { error: isUpstreamTimeout(error) ? "总览服务响应超时" : "无法连接总览服务" },
      { status: isUpstreamTimeout(error) ? 504 : 502, headers: privateNoStore },
    );
  }
}
