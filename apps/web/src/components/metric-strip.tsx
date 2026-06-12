import { metricIcons } from "@/components/icons";
import type { DashboardSnapshot } from "@/lib/dashboard-data";

type MetricStripProps = {
  snapshot: DashboardSnapshot;
};

export function MetricStrip({ snapshot }: MetricStripProps) {
  const metrics = [
    {
      label: "综合健康度",
      value: snapshot.healthScore.toFixed(1),
      suffix: "/ 100",
      trend: "+1.8 较昨日",
      icon: metricIcons.health,
      tone: "teal",
    },
    {
      label: "质量一次合格率",
      value: snapshot.qualityPassRate.toFixed(1),
      suffix: "%",
      trend: "+0.4% 本班次",
      icon: metricIcons.passRate,
      tone: "teal",
    },
    {
      label: "在制生产事件",
      value: String(snapshot.activeRuns),
      suffix: "台",
      trend: `${snapshot.stages.length} 个工艺阶段`,
      icon: metricIcons.runs,
      tone: "cyan",
    },
    {
      label: "高风险点位",
      value: String(snapshot.openRisks),
      suffix: "个",
      trend: `${snapshot.pendingRecommendations} 条待审批建议`,
      icon: metricIcons.risk,
      tone: "amber",
    },
  ] as const;

  return (
    <section className="metric-strip" aria-label="关键指标">
      {metrics.map((metric) => {
        const Icon = metric.icon;
        return (
          <article className="metric-item" key={metric.label}>
            <div className={`metric-icon metric-icon-${metric.tone}`}>
              <Icon aria-hidden="true" />
            </div>
            <div>
              <span className="metric-label">{metric.label}</span>
              <div className="metric-value">
                <strong>{metric.value}</strong>
                <span>{metric.suffix}</span>
              </div>
              <span className="metric-trend">{metric.trend}</span>
            </div>
          </article>
        );
      })}
    </section>
  );
}
