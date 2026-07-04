import { NextResponse } from "next/server";

import { sessionCookieName } from "@/lib/auth-data";

type LoginPayload = {
  username?: string;
  password?: string;
};

type LoginResult = {
  access_token?: string;
  expires_at?: string;
  actor?: unknown;
  detail?: string;
};

export async function POST(request: Request) {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    return NextResponse.json({ error: "后端 API 地址未配置" }, { status: 503 });
  }

  const payload = (await request.json().catch(() => ({}))) as LoginPayload;
  try {
    const response = await fetch(`${apiUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: payload.username ?? "",
        password: payload.password ?? "",
      }),
      cache: "no-store",
    });
    const result = (await response.json().catch(() => ({}))) as LoginResult;
    if (!response.ok || !result.access_token || !result.expires_at) {
      return NextResponse.json(
        { error: result.detail ?? "用户名或密码错误" },
        { status: response.status || 401 },
      );
    }

    const nextResponse = NextResponse.json({ actor: result.actor, expires_at: result.expires_at });
    const expires = new Date(result.expires_at);
    nextResponse.cookies.set(sessionCookieName, result.access_token, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      expires,
    });
    return nextResponse;
  } catch {
    return NextResponse.json({ error: "无法连接认证服务" }, { status: 502 });
  }
}
