import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    return NextResponse.json(
      { status: "unavailable", message: "系统服务地址未配置" },
      { status: 503 },
    );
  }

  try {
    const response = await fetch(`${apiUrl.replace(/\/$/, "")}/health/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2500),
    });
    if (!response.ok) {
      const payload = (await response.json().catch(() => ({}))) as { detail?: string };
      return NextResponse.json(
        {
          status: "not_ready",
          message: payload.detail ?? `系统数据连接未就绪（状态 ${response.status}）`,
        },
        { status: 503 },
      );
    }
    return NextResponse.json({ status: "ready", message: "系统和数据连接正常" });
  } catch {
    return NextResponse.json(
      { status: "unavailable", message: "无法连接系统服务" },
      { status: 503 },
    );
  }
}
