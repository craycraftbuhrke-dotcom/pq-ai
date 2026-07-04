import { NextResponse } from "next/server";

import { apiRequestHeaders } from "@/lib/auth-data";

type Context = { params: Promise<{ path: string[] }> };

async function proxyBulk(request: Request, context: Context) {
  const { path } = await context.params;
  if (!path.length) {
    return NextResponse.json({ error: "不支持的批量接口" }, { status: 404 });
  }
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    return NextResponse.json({ error: "后端 API 地址未配置" }, { status: 503 });
  }
  const headers = new Headers(await apiRequestHeaders(request));
  let body: ArrayBuffer | undefined;
  if (request.method !== "GET") {
    body = await request.arrayBuffer();
    headers.set("Content-Type", request.headers.get("content-type") ?? "application/octet-stream");
  }

  try {
    const response = await fetch(
      `${apiUrl}/bulk/${path.map(encodeURIComponent).join("/")}${new URL(request.url).search}`,
      { method: request.method, headers, body, cache: "no-store" },
    );
    const contentType = response.headers.get("content-type") ?? "";
    if (!response.ok) {
      const payload = contentType.includes("application/json")
        ? ((await response.json().catch(() => ({}))) as Record<string, unknown>)
        : {};
      return NextResponse.json(
        { error: payload.detail ?? "后端批量服务返回错误" },
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
  } catch {
    return NextResponse.json({ error: "无法连接后端批量服务" }, { status: 502 });
  }
}

export const GET = proxyBulk;
export const POST = proxyBulk;
