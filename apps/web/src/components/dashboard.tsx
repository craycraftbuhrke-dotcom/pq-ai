"use client";

import { ChevronDown, RefreshCcw } from "lucide-react";
import { useState } from "react";

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
  const [selectedPoint, setSelectedPoint] = useState(snapshot.diagnosis.pointCode);
  const [refreshed, setRefreshed] = useState(
    new Date(snapshot.context.refreshedAt).toLocaleTimeString("zh-CN", { hour12: false }),
  );

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">
            {snapshot.context.factory} · {snapshot.context.vehicleModel} · {snapshot.context.color}
          </span>
          <h1>工艺质量驾驶舱</h1>
          <p>基于生产事件与测量点，监控五段喷涂工艺、质量风险和 AI 闭环任务。</p>
        </div>
        <div className="page-actions">
          <button className="context-button">
            当前车型与颜色
            <strong>
              {snapshot.context.vehicleModel} · {snapshot.context.color}
            </strong>
            <ChevronDown aria-hidden="true" />
          </button>
          <button
            className="icon-button icon-button-bordered"
            aria-label="刷新数据"
            onClick={() => setRefreshed(new Date().toLocaleTimeString("zh-CN", { hour12: false }))}
          >
            <RefreshCcw />
          </button>
        </div>
      </header>
      <div className="freshness">
        <span className="live-dot" /> 数据更新时间 {refreshed} ·
        {snapshot.source === "api" ? " API 实时数据" : " 演示快照"}
      </div>
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
