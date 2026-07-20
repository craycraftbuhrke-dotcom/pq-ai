import { NextResponse } from "next/server";

import { apiRequestHeaders, isUpstreamTimeout, upstreamRequestSignal } from "@/lib/auth-data";
import { parseBoundedJson } from "@/lib/bounded-request-body";

type ApprovalRequest = {
  approvedBy?: string;
  comment?: string;
};

export async function POST(
  request: Request,
  context: { params: Promise<{ recommendationId: string }> },
) {
  const { recommendationId } = await context.params;
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;

  if (!apiUrl) {
    return NextResponse.json({ error: "后端 API 地址未配置" }, { status: 503 });
  }

  try {
    const payload = await parseBoundedJson<ApprovalRequest>(request, 32 * 1024);
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
        signal: upstreamRequestSignal(request),
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
  } catch (error) {
    const clientStatus = (error as { status?: number }).status;
    if (typeof clientStatus === "number" && clientStatus >= 400 && clientStatus < 500) {
      return NextResponse.json(
        { error: error instanceof Error ? error.message : "审批请求无效" },
        { status: clientStatus },
      );
    }
    return NextResponse.json(
      { error: isUpstreamTimeout(error) ? "审批服务响应超时" : "无法连接审批服务，请稍后重试" },
      { status: isUpstreamTimeout(error) ? 504 : 502 },
    );
  }
}
