import { NextResponse } from "next/server";

import { apiRequestHeaders } from "@/lib/auth-data";

const resourcePaths: Record<string, string> = {
  factories: "/factories",
  "vehicle-models": "/vehicle-models",
  colors: "/colors",
  parts: "/parts",
  "measurement-groups": "/measurement-groups",
  "measurement-points": "/measurement-points",
  "factory-vehicle-models": "/factory-vehicle-models",
  "vehicle-model-colors": "/vehicle-model-colors",
  "measurement-group-points": "/measurement-group-points",
};

export async function proxyMasterDataRequest(
  request: Request,
  resource: string,
  id?: string,
) {
  const basePath = resourcePaths[resource];
  if (!basePath) {
    return NextResponse.json({ error: "不支持的主数据类型" }, { status: 404 });
  }

  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    return NextResponse.json({ error: "后端 API 地址未配置" }, { status: 503 });
  }

  const target = `${apiUrl}${basePath}${id ? `/${encodeURIComponent(id)}` : ""}`;
  const method = request.method;
  const headers = new Headers(await apiRequestHeaders(request));
  let body: string | undefined;

  if (method !== "GET") {
    headers.set("Content-Type", "application/json");
    body = await request.text();
  }

  try {
    const response = await fetch(target, { method, headers, body, cache: "no-store" });
    if (response.status === 204) {
      return new NextResponse(null, { status: 204 });
    }
    const result = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    if (!response.ok) {
      return NextResponse.json(
        { error: result.detail ?? "后端服务返回错误" },
        { status: response.status },
      );
    }
    return NextResponse.json(result, { status: response.status });
  } catch {
    return NextResponse.json({ error: "无法连接后端服务，请确认 API 已启动" }, { status: 502 });
  }
}
