"use client";

import { Check, LockKeyhole, Sparkles } from "lucide-react";
import { useState } from "react";

import type { DashboardSnapshot } from "@/lib/dashboard-data";
import { useAuth } from "@/lib/auth-context";

type RecommendationPanelProps = {
  recommendation: DashboardSnapshot["recommendation"];
};

function formatPrediction(value: number): string {
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 1 }).format(value);
}

export function RecommendationPanel({ recommendation }: RecommendationPanelProps) {
  const { actor } = useAuth();
  const initialStatus = recommendation.status.toLowerCase();
  const [status, setStatus] = useState<
    "pending" | "submitting" | "approved" | "executed" | "verified"
  >(
    initialStatus === "approved" || initialStatus === "executed" || initialStatus === "verified"
      ? initialStatus
      : "pending",
  );
  const [error, setError] = useState<string | null>(null);

  async function approveRecommendation() {
    setStatus("submitting");
    setError(null);

    try {
      const response = await fetch(`/api/recommendations/${recommendation.id}/approval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approvedBy: actor.isAuthenticated ? actor.displayName : "",
          comment: "通过工艺质量驾驶舱审批",
        }),
      });
      const result = (await response.json()) as { status?: string; error?: string };
      if (!response.ok || result.status !== "APPROVED") {
        throw new Error(result.error ?? "审批提交失败");
      }
      setStatus("approved");
    } catch (approvalError) {
      setStatus("pending");
      setError(approvalError instanceof Error ? approvalError.message : "审批提交失败");
    }
  }

  return (
    <section className="panel recommendation-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">CLOSED LOOP TASK</span>
          <h2>参数推荐</h2>
        </div>
        <span className={`approval-state approval-${status}`}>
          {status === "verified"
            ? "已验证"
            : status === "executed"
              ? "已执行"
              : status === "approved"
                ? "已批准"
                : status === "submitting"
                  ? "提交中"
                  : "待审批"}
        </span>
      </div>
      <div className="recommendation-outcome">
        <div>
          <span>当前 DOI 预测</span>
          <strong>{formatPrediction(recommendation.currentPrediction)}</strong>
        </div>
        <span className="outcome-arrow">→</span>
        <div>
          <span>调整后预测</span>
          <strong>{formatPrediction(recommendation.expectedPrediction)}</strong>
        </div>
        <div className="improvement">
          <Sparkles aria-hidden="true" />
          预计改善 +{formatPrediction(recommendation.predictedImprovement)}
        </div>
      </div>
      <div className="action-list">
        {recommendation.actions.map((action) => (
          <article className="action-row" key={action.parameter}>
            <div>
              <strong>{action.parameter}</strong>
              <span>
                {action.stage} · <span className="mono">{action.brush}</span>
              </span>
            </div>
            <div className="value-change">
              <span>{action.current}</span>
              <strong>→</strong>
              <span>{action.recommended}</span>
              <small>{action.unit}</small>
            </div>
          </article>
        ))}
      </div>
      <div className="constraint-note">
        <LockKeyhole aria-hidden="true" />
        已通过设备硬边界、材料 TDS 和单次调整步长校验
      </div>
      <div className="recommendation-actions">
        {status === "pending" || status === "submitting" ? (
          <>
            <button className="button button-secondary">查看模拟详情</button>
            <button
              className="button button-primary"
              disabled={status === "submitting"}
              onClick={approveRecommendation}
            >
              <Check aria-hidden="true" />
              {status === "submitting" ? "正在提交审批..." : "批准并创建新版本"}
            </button>
            {error ? <div className="approval-error">{error}</div> : null}
          </>
        ) : (
          <div className="approved-message">
            <Check aria-hidden="true" />
            {status === "verified"
              ? "复测评价已完成，闭环效果已记录"
              : status === "executed"
                ? "参数已执行，等待关联复测记录"
                : "推荐已批准，等待工艺执行与复测"}
          </div>
        )}
      </div>
    </section>
  );
}
