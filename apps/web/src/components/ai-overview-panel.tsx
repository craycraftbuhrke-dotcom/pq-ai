"use client";

import { OvpCard, OvpCardList, OvpCardStatusStrip, type OvpAccent } from "@/components/ovp-card";
import { useOverviewData, type AiOverview } from "@/lib/overview-data";

function ModelStatusCard({ a }: { a: AiOverview }) {
  const items = [
    { label: "已验收模型", value: String(a.modelsApproved) },
    { label: "模型总数", value: String(a.modelsTotal) },
    { label: "最新目标指标", value: a.latestModelMetric ?? "—" },
  ];
  return (
    <OvpCard
      title="模型状态"
      kpiLabel="已验收"
      kpiValue={a.modelsApproved}
      kpiUnit="个"
      accent={a.modelsApproved > 0 ? "positive" : "warning"}
      viewAllHref="/ai?tab=models"
    >
      <OvpCardList items={items} />
    </OvpCard>
  );
}

function PredictionQueueCard({ a }: { a: AiOverview }) {
  const items = [
    { label: "24h 预测数", value: String(a.predictions24h) },
    { label: "最高风险点", value: a.topRiskPoint ?? "—" },
  ];
  return (
    <OvpCard
      title="预测队列"
      kpiLabel="24h 预测"
      kpiValue={a.predictions24h}
      kpiUnit="次"
      accent="info"
      viewAllHref="/ai?tab=predictions"
    >
      <OvpCardList items={items} />
    </OvpCard>
  );
}

function RecommendationQueueCard({ a }: { a: AiOverview }) {
  const pendingTone = a.recommendationsPending > 0 ? "warning" : "positive";
  const segments = [
    { label: `待处理 ${a.recommendationsPending}`, tone: pendingTone as OvpAccent },
    { label: `总数 ${a.recommendationsTotal}`, tone: "neutral" as OvpAccent },
  ];
  return (
    <OvpCard
      title="推荐队列"
      kpiLabel="待处理"
      kpiValue={a.recommendationsPending}
      kpiUnit="条"
      accent={a.recommendationsPending > 0 ? "warning" : "positive"}
      viewAllHref="/ai?tab=recommendations"
    >
      <OvpCardStatusStrip segments={segments} />
    </OvpCard>
  );
}

function TrialStatusCard({ a }: { a: AiOverview }) {
  const items = [
    { label: "活动试验", value: String(a.trialsActive) },
    { label: "已完成试验", value: String(a.trialsCompleted) },
  ];
  return (
    <OvpCard
      title="受控试验"
      kpiLabel="活动试验"
      kpiValue={a.trialsActive}
      kpiUnit="项"
      accent={a.trialsActive > 0 ? "info" : "neutral"}
      viewAllHref="/ai?tab=recommendations"
    >
      <OvpCardList items={items} />
    </OvpCard>
  );
}

function EngineeringChangeCard({ a }: { a: AiOverview }) {
  const items = [
    { label: "未关闭问题", value: String(a.openChanges) },
  ];
  return (
    <OvpCard
      title="工艺变更"
      kpiLabel="未关闭"
      kpiValue={a.openChanges}
      kpiUnit="项"
      accent={a.openChanges > 0 ? "warning" : "positive"}
      viewAllHref="/ai?tab=changes"
    >
      <OvpCardList items={items} />
    </OvpCard>
  );
}

export function AiOverviewPanel() {
  const { ai } = useOverviewData();
  return (
    <div className="domain-overview">
      <div className="domain-overview-intro">
        <strong>AI 闭环总览</strong>
        <span>模型验收、预测诊断、推荐试验与工艺变更的关键指标；点击卡片进入对应工作台。</span>
      </div>
      <div className="ovp-card-grid">
        <ModelStatusCard a={ai} />
        <PredictionQueueCard a={ai} />
        <RecommendationQueueCard a={ai} />
        <TrialStatusCard a={ai} />
        <EngineeringChangeCard a={ai} />
      </div>
    </div>
  );
}
