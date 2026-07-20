import { NextResponse } from "next/server";

import { isUpstreamTimeout, sessionCookieName, upstreamRequestSignal } from "@/lib/auth-data";
import { parseBoundedJson } from "@/lib/bounded-request-body";

type RegisterPayload = {
  username?: string;
  password?: string;
  display_name?: string;
};

export async function POST(request: Request) {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    return NextResponse.json({ error: "后端 API 地址未配置" }, { status: 503 });
  }
  try {
    const payload = await parseBoundedJson<RegisterPayload>(request, 16 * 1024);
    const response = await fetch(`${apiUrl}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: upstreamRequestSignal(request),
    });
    const result = (await response.json().catch(() => ({}))) as {
      access_token?: string;
      expires_at?: string;
      actor?: unknown;
      detail?: string;
    };
    if (!response.ok) {
      return NextResponse.json({ error: result.detail ?? "注册失败" }, { status: response.status });
    }
    const expiresAt = typeof result.expires_at === "string" ? new Date(result.expires_at) : null;
    if (
      typeof result.access_token !== "string" ||
      !result.access_token ||
      !expiresAt ||
      Number.isNaN(expiresAt.getTime()) ||
      expiresAt.getTime() <= Date.now()
    ) {
      return NextResponse.json({ error: "注册服务返回无效响应" }, { status: 502 });
    }
    const nextResponse = NextResponse.json({ actor: result.actor, expires_at: result.expires_at });
    nextResponse.cookies.set(sessionCookieName, result.access_token, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      expires: expiresAt,
    });
    return nextResponse;
  } catch (error) {
    const clientStatus = (error as { status?: number }).status;
    if (typeof clientStatus === "number" && clientStatus >= 400 && clientStatus < 500) {
      return NextResponse.json(
        { error: error instanceof Error ? error.message : "注册请求无效" },
        { status: clientStatus },
      );
    }
    return NextResponse.json(
      { error: isUpstreamTimeout(error) ? "注册服务响应超时" : "无法连接认证服务" },
      { status: isUpstreamTimeout(error) ? 504 : 502 },
    );
  }
}
