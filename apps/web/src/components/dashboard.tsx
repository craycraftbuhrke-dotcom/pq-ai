"use client";

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
  // 展示的“数据更新时间”来自后端 snapshot.context.refreshedAt——每次 router.refresh() 触发
  // Server Component 重跑后，props 会带回新的时间戳，无需在客户端手动 setState 维护。
  const refreshedAt = new Date(snapshot.context.refreshedAt).toLocaleTimeString("zh-CN", { hour12: false });

  function handleRefresh() {
    // Server Component 数据源真正重新拉：router.refresh() 让当前路由的 RSC payload 全量重取，
    // 页面 SSR 会重新执行 getDashboardSnapshot()，拿到最新指标/风险点/诊断。
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
          <h1>工艺质量驾驶舱</h1>
          <p>基于生产事件与测量点，监控三个涂层体系、五个喷涂执行阶段和 AI 闭环任务。</p>
        </div>
        <div className="page-actions">
          {/* 展示当前生产上下文；实际切换通过左侧 <ContextSelector> 完成，此处仅只读展示，避免误导用户以为可以点击。 */}
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
        {snapshot.source === "api" ? " API 实时数据" : " 空状态"}
      </div>
      {snapshot.error ? (
        <div className="message-banner message-error" role="alert">
          <span>后端数据库/服务异常：{snapshot.error}</span>
        </div>
      ) : null}
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
