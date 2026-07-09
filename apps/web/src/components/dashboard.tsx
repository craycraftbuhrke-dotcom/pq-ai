"use client";

import Link from "next/link";
import { RefreshCcw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { DiagnosisPanel } from "@/components/diagnosis-panel";
import { MetricStrip } from "@/components/metric-strip";
import { ProcessFlow } from "@/components/process-flow";
import { RecommendationPanel } from "@/components/recommendation-panel";
import { RiskTable } from "@/components/risk-table";
import type { DashboardSnapshot } from "@/lib/dashboard-data";

type DashboardProps = {
  snapshot: DashboardSnapshot;
};

export function Dashboard({ snapshot }: DashboardProps) {
  const router = useRouter();
  const [selectedPoint, setSelectedPoint] = useState(snapshot.diagnosis.pointCode || "");
  const [isRefreshing, startTransition] = useTransition();
  const refreshedAt = new Date(snapshot.context.refreshedAt).toLocaleTimeString("zh-CN", { hour12: false });

  function handleRefresh() {
    startTransition(() => router.refresh());
  }

  const contextLabel =
    [snapshot.context.vehicleModel, snapshot.context.color].filter(Boolean).join(" · ") || "待选择";

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">
            {[snapshot.context.factory, snapshot.context.vehicleModel, snapshot.context.color]
              .filter(Boolean)
              .join(" · ") || "未选择生产上下文"}
          </span>
          <h1>今日总览</h1>
          <p>先看五站喷涂状态与风险点位，再进入质量录入、问题处理或智能推荐。</p>
        </div>
        <div className="page-actions">
          <div className="context-button" role="status" aria-label={`当前车型与颜色：${contextLabel}`}>
            当前车型与颜色
            <strong>{contextLabel}</strong>
          </div>
          <button
            className="icon-button icon-button-bordered"
            aria-label={isRefreshing ? "正在刷新数据" : "刷新数据"}
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCcw className={isRefreshing ? "spin" : ""} aria-hidden="true" />
          </button>
        </div>
      </header>
      <div className="freshness">
        <span className="live-dot" /> 数据更新时间 {refreshedAt} ·
        {snapshot.source === "api" ? " 实时业务数据" : " 暂无数据"}
      </div>
      {snapshot.error ? (
        <div className="message-banner message-error" role="alert">
          <span>服务暂时异常：{snapshot.error}</span>
        </div>
      ) : null}
      <section className="dashboard-quick-links" aria-label="常用入口">
        <Link className="dashboard-quick-link" href="/quality">
          <strong>录入质量</strong>
          <span>登记膜厚、色差、橘皮测量</span>
        </Link>
        <Link className="dashboard-quick-link" href="/production">
          <strong>查看生产车身</strong>
          <span>核对五站喷涂实绩参数</span>
        </Link>
        <Link className="dashboard-quick-link" href="/ai-workbench">
          <strong>智能分析与推荐</strong>
          <span>预测质量并获取参数建议</span>
        </Link>
        <Link className="dashboard-quick-link" href="/engineering">
          <strong>问题与调试</strong>
          <span>记录异常并跟进闭环</span>
        </Link>
      </section>
      <MetricStrip snapshot={snapshot} />
      <ProcessFlow stages={snapshot.stages} />
      <div className="dashboard-grid">
        <RiskTable riskPoints={snapshot.riskPoints} onSelect={setSelectedPoint} />
        <div className="insight-stack">
          <DiagnosisPanel
            pointCode={selectedPoint}
            summary={snapshot.diagnosis.summary}
            confidence={snapshot.diagnosis.confidence}
            factors={snapshot.diagnosis.factors}
          />
          <RecommendationPanel recommendation={snapshot.recommendation} />
        </div>
      </div>
    </div>
  );
}
