import { NextResponse } from "next/server";

import { apiRequestHeaders } from "@/lib/auth-data";

type ApprovalRequest = {
  approvedBy?: string;
  comment?: string;
};

export async function POST(
  request: Request,
  context: { params: Promise<{ recommendationId: string }> },
) {
  const { recommendationId } = await context.params;
  const payload = (await request.json().catch(() => ({}))) as ApprovalRequest;
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;

  if (!apiUrl) {
    return NextResponse.json({ error: "后端 API 地址未配置" }, { status: 503 });
  }

  try {
    const authHeaders = await apiRequestHeaders(request);
    const response = await fetch(
      `${apiUrl}/ai/recommendations/${encodeURIComponent(recommendationId)}/approval`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({
          approved: true,
          approved_by: payload.approvedBy ?? "工艺审批人",
          comment: payload.comment,
        }),
        cache: "no-store",
      },
    );
    const result = (await response.json()) as Record<string, unknown>;
    if (!response.ok) {
      return NextResponse.json(
        { error: result.detail ?? "后端审批接口返回错误" },
        { status: response.status },
      );
    }
    return NextResponse.json(result);
  } catch {
    return NextResponse.json({ error: "无法连接审批服务，请稍后重试" }, { status: 502 });
  }
}
