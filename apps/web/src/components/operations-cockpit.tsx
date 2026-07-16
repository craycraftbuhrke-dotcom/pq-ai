"use client";

import { RefreshCcw } from "lucide-react";
import { useMemo } from "react";

import { OvpCard, OvpCardList, OvpCardStatusStrip, type OvpAccent } from "@/components/ovp-card";
import { useAuth } from "@/lib/auth-context";
import { useOverviewData, type AiOverview, type DashboardOverview, type ProcessOverview } from "@/lib/overview-data";

type RoleKey = string;

function roleMatches(cardRoles: readonly RoleKey[] | undefined, actorRoles: Set<string>, isAdmin: boolean): boolean {
  if (!cardRoles || cardRoles.length === 0) return true;
  if (isAdmin) return true;
  return cardRoles.some((r) => actorRoles.has(r));
}

function QualityExceptionCard({ d }: { d: DashboardOverview }) {
  const failCount = d.riskPoints.length;
  const items = d.riskPoints.slice(0, 5).map((p) => ({
    label: `${p.code} · ${p.name}`,
    value: p.metric,
  }));
  return (
    <OvpCard
      title="质量异常"
      kpiLabel="高风险点位"
      kpiValue={failCount}
      kpiUnit="个"
      accent={failCount > 0 ? "negative" : "positive"}
      viewAllHref="/quality?tab=measurements&filter=fail"
    >
      <OvpCardList items={items} />
    </OvpCard>
  );
}

function DataReliabilityCard({ d }: { d: DashboardOverview }) {
  const score = d.healthScore;
  const passTone = d.qualityPassRate >= 95 ? "positive" : "warning";
  const recTone = d.pendingRecommendations > 0 ? "warning" : "neutral";
  const calTone = d.calibrationAlerts.expiring30d > 0 ? "warning" : "positive";
  const segments = [
    { label: `合格率 ${d.qualityPassRate.toFixed(1)}%`, tone: passTone as OvpAccent },
    { label: `待审批 ${d.pendingRecommendations}`, tone: recTone as OvpAccent },
    { label: `校准预警 ${d.calibrationAlerts.expiring30d}`, tone: calTone as OvpAccent },
  ];
  return (
    <OvpCard
      title="数据可靠性"
      kpiLabel="综合健康分"
      kpiValue={score.toFixed(1)}
      kpiUnit="/ 100"
      accent={score >= 80 ? "positive" : score >= 60 ? "warning" : "negative"}
      viewAllHref="/quality?tab=overview"
    >
      <OvpCardStatusStrip segments={segments} />
    </OvpCard>
  );
}

function ProcessStageHealthCard({ p }: { p: ProcessOverview }) {
  const healthyCount = p.stages.filter((s) => s.healthy).length;
  const total = p.stages.length || 5;
  const segments = p.stages.map((s) => ({
    label: `${s.name} ${s.runCount}`,
    tone: (s.healthy ? "positive" : "neutral") as OvpAccent,
  }));
  return (
    <OvpCard
      title="工艺五段健康"
      kpiLabel="健康段数"
      kpiValue={`${healthyCount}/${total}`}
      accent={healthyCount === total ? "positive" : "warning"}
      viewAllHref="/process?tab=simulation"
    >
      <OvpCardStatusStrip segments={segments} />
    </OvpCard>
  );
}

function ActiveRunsCard({ p }: { p: ProcessOverview }) {
  const items = p.recentRuns.map((r) => ({
    label: `${r.runNo}${r.shift ? ` · ${r.shift}` : ""}`,
    value: r.bodyNo ?? "—",
  }));
  return (
    <OvpCard
      title="在制生产"
      kpiLabel="活动批次"
      kpiValue={p.activeRuns}
      kpiUnit="台"
      accent="info"
      viewAllHref="/process?tab=runs"
    >
      <OvpCardList items={items} />
    </OvpCard>
  );
}

function MaterialReadinessCard({ d }: { d: DashboardOverview }) {
  const items = [
    { label: "已核验批次", value: String(d.materialBatches.verified) },
    { label: "失效规格", value: String(d.materialBatches.failSpec) },
    { label: "总批次", value: String(d.materialBatches.total) },
  ];
  return (
    <OvpCard
      title="材料就绪"
      kpiLabel="已核验批次"
      kpiValue={d.materialBatches.verified}
      kpiUnit="批"
      accent={d.materialBatches.failSpec > 0 ? "warning" : "positive"}
      viewAllHref="/materials?tab=overview"
    >
      <OvpCardList items={items} />
    </OvpCard>
  );
}

function AiRecommendationCard({ a, d }: { a: AiOverview; d: DashboardOverview }) {
  const rec = d.recommendation;
  const items = [
    { label: "待处理推荐", value: String(a.recommendationsPending) },
    { label: "推荐总数", value: String(a.recommendationsTotal) },
    rec
      ? { label: `Top 推荐 ${rec.pointCode}`, value: `+${rec.predictedImprovement.toFixed(2)}` }
      : { label: "Top 推荐", value: "—" },
  ];
  return (
    <OvpCard
      title="AI 推荐"
      kpiLabel="待处理"
      kpiValue={a.recommendationsPending}
      kpiUnit="条"
      accent={a.recommendationsPending > 0 ? "warning" : "positive"}
      viewAllHref="/ai?tab=recommendations"
    >
      <OvpCardList items={items} />
    </OvpCard>
  );
}

function AiPredictionCard({ a }: { a: AiOverview }) {
  const items = [
    { label: "24h 预测数", value: String(a.predictions24h) },
    { label: "最高风险点", value: a.topRiskPoint ?? "—" },
    { label: "已验收模型", value: String(a.modelsApproved) },
  ];
  return (
    <OvpCard
      title="AI 预测"
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

function EngineeringChangeCard({ a }: { a: AiOverview }) {
  const items = [
    { label: "未关闭问题", value: String(a.openChanges) },
    { label: "活动试验", value: String(a.trialsActive) },
    { label: "已完成试验", value: String(a.trialsCompleted) },
  ];
  return (
    <OvpCard
      title="工艺变更"
      kpiLabel="未关闭问题"
      kpiValue={a.openChanges}
      kpiUnit="项"
      accent={a.openChanges > 0 ? "warning" : "positive"}
      viewAllHref="/ai?tab=changes"
    >
      <OvpCardList items={items} />
    </OvpCard>
  );
}

function CalibrationAlertCard({ d }: { d: DashboardOverview }) {
  const items = [
    { label: "30 天内到期", value: String(d.calibrationAlerts.expiring30d) },
    { label: "已过期", value: String(d.calibrationAlerts.expired) },
  ];
  return (
    <OvpCard
      title="校准预警"
      kpiLabel="30 天到期"
      kpiValue={d.calibrationAlerts.expiring30d}
      kpiUnit="件"
      accent={d.calibrationAlerts.expired > 0 ? "negative" : d.calibrationAlerts.expiring30d > 0 ? "warning" : "positive"}
      viewAllHref="/quality?tab=governance"
    >
      <OvpCardList items={items} />
    </OvpCard>
  );
}

export function OperationsCockpit() {
  const { actor } = useAuth();
  const { dashboard, process, ai, loading, refresh } = useOverviewData();

  const isAdmin = actor.roles.includes("ADMIN") || actor.permissions.includes("*");
  const actorRoles = useMemo(() => new Set(actor.roles), [actor.roles]);

  const cards = useMemo(() => {
    const all = [
      { key: "quality-exception", roles: [] as string[], node: <QualityExceptionCard d={dashboard} /> },
      { key: "data-reliability", roles: [] as string[], node: <DataReliabilityCard d={dashboard} /> },
      { key: "process-stage", roles: ["PROCESS_ENGINEER", "ADMIN"], node: <ProcessStageHealthCard p={process} /> },
      { key: "active-runs", roles: ["PROCESS_ENGINEER", "ADMIN"], node: <ActiveRunsCard p={process} /> },
      { key: "material-readiness", roles: ["QUALITY_ENGINEER", "PROCESS_ENGINEER", "ADMIN"], node: <MaterialReadinessCard d={dashboard} /> },
      { key: "ai-recommendation", roles: ["PROCESS_ENGINEER", "APPROVER", "DATA_SCIENTIST", "ADMIN"], node: <AiRecommendationCard a={ai} d={dashboard} /> },
      { key: "ai-prediction", roles: ["PROCESS_ENGINEER", "QUALITY_ENGINEER", "DATA_SCIENTIST", "ADMIN"], node: <AiPredictionCard a={ai} /> },
      { key: "engineering-change", roles: ["PROCESS_ENGINEER", "ADMIN"], node: <EngineeringChangeCard a={ai} /> },
      { key: "calibration-alert", roles: ["QUALITY_ENGINEER", "ADMIN"], node: <CalibrationAlertCard d={dashboard} /> },
    ];
    return all.filter((c) => roleMatches(c.roles, actorRoles, isAdmin));
  }, [dashboard, process, ai, actorRoles, isAdmin]);

  const refreshedAt = new Date().toLocaleTimeString("zh-CN", { hour12: false });

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">工作台</span>
          <h1>运营总览</h1>
          <p>按角色聚合的质量、工艺、材料与 AI 闭环 KPI；从异常卡片直接进入对应工作流。</p>
        </div>
        <div className="page-actions">
          <button
            className="icon-button icon-button-bordered"
            aria-label={loading ? "正在刷新" : "刷新"}
            onClick={refresh}
            disabled={loading}
          >
            <RefreshCcw className={loading ? "spin" : ""} aria-hidden="true" />
          </button>
        </div>
      </header>
      <div className="freshness">
        <span className="live-dot" /> 数据更新时间 {refreshedAt} ·
        {dashboard.source === "api" ? " 实时业务数据" : " 暂无数据"}
      </div>

      <section className="ovp-kpi-strip" aria-label="核心指标">
        <div className="ovp-kpi-tile">
          <span className="ovp-kpi-tile-label">综合健康度</span>
          <div className="ovp-kpi-tile-value">
            <strong>{dashboard.healthScore.toFixed(1)}</strong>
            <span>/ 100</span>
          </div>
          <span className="ovp-kpi-tile-hint">质量可靠性综合分</span>
        </div>
        <div className="ovp-kpi-tile">
          <span className="ovp-kpi-tile-label">质量一次合格率</span>
          <div className="ovp-kpi-tile-value">
            <strong>{dashboard.qualityPassRate.toFixed(1)}</strong>
            <span>%</span>
          </div>
          <span className="ovp-kpi-tile-hint">有效测量占比</span>
        </div>
        <div className="ovp-kpi-tile">
          <span className="ovp-kpi-tile-label">在制生产</span>
          <div className="ovp-kpi-tile-value">
            <strong>{dashboard.activeRuns}</strong>
            <span>台</span>
          </div>
          <span className="ovp-kpi-tile-hint">未完成生产事件</span>
        </div>
        <div className="ovp-kpi-tile">
          <span className="ovp-kpi-tile-label">待处理推荐</span>
          <div className="ovp-kpi-tile-value">
            <strong>{dashboard.pendingRecommendations}</strong>
            <span>条</span>
          </div>
          <span className="ovp-kpi-tile-hint">AI 闭环待审批</span>
        </div>
      </section>

      <section className="ovp-card-grid" aria-label="工作流入口">
        {cards.map((c) => (
          <div key={c.key}>{c.node}</div>
        ))}
      </section>
    </div>
  );
}
