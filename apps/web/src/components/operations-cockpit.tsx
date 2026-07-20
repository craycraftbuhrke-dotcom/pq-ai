"use client";

import Link from "next/link";
import { ArrowRight, ChevronRight, RefreshCcw } from "lucide-react";
import { useMemo } from "react";

import { useAuth } from "@/lib/auth-context";
import {
  useOverviewData,
  type AiOverview,
  type DashboardOverview,
  type ProcessOverview,
} from "@/lib/overview-data";

function hasRole(roles: Set<string>, allowed: readonly string[], isAdmin: boolean): boolean {
  if (isAdmin || allowed.length === 0) return true;
  return allowed.some((r) => roles.has(r));
}

function metricTone(metric: string): "thickness" | "color" | "orange" | "other" {
  const m = metric.toUpperCase();
  if (m.includes("THICK") || m.includes("膜厚") || m === "DFT") return "thickness";
  if (m.includes("COLOR") || m.includes("L_STAR") || m.includes("A_STAR") || m.includes("B_STAR")) {
    return "color";
  }
  if (m.includes("ORANGE") || m.includes("LW") || m.includes("DOI") || m.includes("橘皮")) {
    return "orange";
  }
  return "other";
}

function ExceptionTriage({ d }: { d: DashboardOverview }) {
  const rows = [...d.riskPoints].sort((a, b) => b.risk - a.risk).slice(0, 6);
  const more = Math.max(0, d.riskPoints.length - rows.length);
  const hasRisk = d.riskPoints.length > 0;

  return (
    <section className={`cockpit-panel cockpit-triage${hasRisk ? " is-alert" : ""}`} aria-label="待办事项">
      <header className="cockpit-panel-head">
        <div>
          <span className="cockpit-panel-kicker">待办事项</span>
          <div className="cockpit-triage-count">
            <strong className="mono">{d.riskPoints.length}</strong>
            <span>项需要处理</span>
          </div>
        </div>
        <Link className="cockpit-panel-link" href="/quality?tab=measurements&filter=fail">
          处理异常
          <ArrowRight aria-hidden="true" />
        </Link>
      </header>

      {rows.length === 0 ? (
        <div className="cockpit-empty">当前无高风险点位</div>
      ) : (
        <ul className="cockpit-exception-list">
          {rows.map((p) => (
            <li key={`${p.code}-${p.metric}`} className={`cockpit-exception-row tone-${metricTone(p.metric)}`}>
              <div className="cockpit-exception-main">
                <span className="cockpit-exception-code mono">{p.code}</span>
                <span className="cockpit-exception-name">{p.name}</span>
              </div>
              <div className="cockpit-exception-meta">
                <span className="cockpit-exception-metric">{p.metric}</span>
                <span className="cockpit-exception-risk">风险 {p.risk.toFixed(1)}</span>
              </div>
              <Link className="cockpit-exception-action" href="/quality?tab=measurements&filter=fail">
                开始排查
              </Link>
            </li>
          ))}
        </ul>
      )}

      {more > 0 ? <div className="cockpit-more">还有 {more} 个未展示</div> : null}

      <footer className="cockpit-status-strip" aria-label="状态摘要">
        <div className="cockpit-status-chip">
          <span>一次合格率</span>
          <strong className="mono">{d.qualityPassRate.toFixed(1)}%</strong>
        </div>
        <div className="cockpit-status-chip">
          <span>健康分</span>
          <strong className="mono">{d.healthScore.toFixed(0)}</strong>
        </div>
        <div className="cockpit-status-chip">
          <span>待推荐</span>
          <strong className="mono">{d.pendingRecommendations}</strong>
        </div>
        <div className="cockpit-status-chip">
          <span>校准到期</span>
          <strong className="mono">{d.calibrationAlerts.expiring30d}</strong>
        </div>
      </footer>
    </section>
  );
}

function StageHealthPanel({ p }: { p: ProcessOverview }) {
  const stages =
    p.stages.length > 0
      ? p.stages
      : [
          { code: "MIDCOAT_EXT", name: "中涂外喷", healthy: false, runCount: 0 },
          { code: "BASECOAT_1", name: "色漆一站", healthy: false, runCount: 0 },
          { code: "BASECOAT_2", name: "色漆二站", healthy: false, runCount: 0 },
          { code: "CLEARCOAT_1", name: "清漆一站", healthy: false, runCount: 0 },
          { code: "CLEARCOAT_2", name: "清漆二站", healthy: false, runCount: 0 },
        ];
  const healthyCount = stages.filter((s) => s.healthy).length;
  const recent = p.recentRuns.slice(0, 3);

  return (
    <section className="cockpit-panel cockpit-stages" aria-label="五道喷涂工序">
      <header className="cockpit-panel-head">
        <div>
          <span className="cockpit-panel-kicker">五道喷涂工序</span>
          <div className="cockpit-stages-summary">
            <strong className="mono">
              {healthyCount}/{stages.length}
            </strong>
            <span>道正常 · 在制 {p.activeRuns} 台</span>
          </div>
        </div>
        <Link className="cockpit-panel-link" href="/process?tab=simulation">
          查看工序详情
          <ArrowRight aria-hidden="true" />
        </Link>
      </header>

      <div className="cockpit-stage-board">
        {stages.map((s) => (
          <div key={s.code} className={`cockpit-stage-cell${s.healthy ? " is-healthy" : " is-idle"}`}>
            <span className="cockpit-stage-name">{s.name}</span>
            <strong className="mono">{s.runCount}</strong>
            <span className="cockpit-stage-hint">{s.healthy ? "运行中" : "无活动"}</span>
          </div>
        ))}
      </div>

      <div className="cockpit-runs">
        <div className="cockpit-runs-head">
          <span>最近实绩</span>
          <Link href="/process?tab=runs">
            全部
            <ChevronRight aria-hidden="true" />
          </Link>
        </div>
        {recent.length === 0 ? (
          <div className="cockpit-empty compact">暂无生产实绩</div>
        ) : (
          <ul className="cockpit-run-list">
            {recent.map((r) => (
              <li key={r.runNo}>
                <span className="mono">{r.runNo}</span>
                <span>{r.bodyNo ?? "—"}</span>
                <span className="cockpit-run-shift">{r.shift ?? "—"}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function ClosedLoopRail({
  a,
  d,
  show,
}: {
  a: AiOverview;
  d: DashboardOverview;
  show: boolean;
}) {
  if (!show) return null;

  const topRec = d.recommendation;
  const steps = [
    {
      key: "predict",
      label: "预测风险",
      value: a.topRiskPoint ?? (a.predictions24h > 0 ? `${a.predictions24h} 次/24h` : "—"),
      href: "/ai?tab=predictions",
      emphasize: Boolean(a.topRiskPoint),
    },
    {
      key: "rec",
      label: "待处理推荐",
      value: topRec
        ? `${a.recommendationsPending} · +${topRec.predictedImprovement.toFixed(2)}`
        : String(a.recommendationsPending),
      href: "/ai?tab=recommendations",
      emphasize: a.recommendationsPending > 0,
    },
    {
      key: "trial",
      label: "活动试验",
      value: String(a.trialsActive),
      href: "/ai?tab=recommendations",
      emphasize: a.trialsActive > 0,
    },
    {
      key: "change",
      label: "未关闭变更",
      value: String(a.openChanges),
      href: "/ai?tab=changes",
      emphasize: a.openChanges > 0,
    },
  ];

  return (
    <section className="cockpit-loop" aria-label="闭环待办">
      <div className="cockpit-loop-label">闭环待办</div>
      <ol className="cockpit-loop-steps">
        {steps.map((step, index) => (
          <li key={step.key} className={step.emphasize ? "is-hot" : undefined}>
            {index > 0 ? <span className="cockpit-loop-connector" aria-hidden="true" /> : null}
            <Link href={step.href} className="cockpit-loop-step">
              <span className="cockpit-loop-step-label">{step.label}</span>
              <strong className="mono">{step.value}</strong>
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}

function SupportTile({
  title,
  value,
  unit,
  hint,
  href,
  tone = "neutral",
  rows,
}: {
  title: string;
  value: string | number;
  unit?: string;
  hint: string;
  href: string;
  tone?: "neutral" | "ok" | "warn" | "bad";
  rows: Array<{ label: string; value: string }>;
}) {
  return (
    <article className={`cockpit-support cockpit-support-${tone}`}>
      <header>
        <span>{title}</span>
        <div className="cockpit-support-kpi">
          <strong className="mono">{value}</strong>
          {unit ? <span>{unit}</span> : null}
        </div>
        <p>{hint}</p>
      </header>
      <ul>
        {rows.map((row) => (
          <li key={row.label}>
            <span>{row.label}</span>
            <strong className="mono">{row.value}</strong>
          </li>
        ))}
      </ul>
      <Link href={href}>
        进入
        <ArrowRight aria-hidden="true" />
      </Link>
    </article>
  );
}

export function OperationsCockpit() {
  const { actor } = useAuth();
  const { dashboard, process, ai, loading, refresh } = useOverviewData();

  const isAdmin = actor.roles.includes("ADMIN") || actor.permissions.includes("*");
  const roles = useMemo(() => new Set(actor.roles), [actor.roles]);

  const showProcess = hasRole(roles, ["PROCESS_ENGINEER", "ADMIN"], isAdmin);
  const showAi = hasRole(roles, ["PROCESS_ENGINEER", "APPROVER", "DATA_SCIENTIST", "QUALITY_ENGINEER", "ADMIN"], isAdmin);
  const showMaterial = hasRole(roles, ["QUALITY_ENGINEER", "PROCESS_ENGINEER", "ADMIN"], isAdmin);
  const showCalibration = hasRole(roles, ["QUALITY_ENGINEER", "ADMIN"], isAdmin);

  const refreshedAt = new Date().toLocaleTimeString("zh-CN", { hour12: false });

  return (
    <div className="page-stack cockpit-page">
      <header className="cockpit-heading">
        <div>
          <h1>今日工作</h1>
          <p>先处理异常，再确认数据，最后推进试验闭环。</p>
        </div>
      </header>
      <div className="cockpit-toolbar">
        <div className="cockpit-freshness">
          <span className="live-dot" />
          <span>
            {dashboard.source === "api" ? "实时业务数据" : "暂无数据"} · {refreshedAt}
          </span>
        </div>
        <button
          className="icon-button icon-button-bordered"
          aria-label={loading ? "正在刷新" : "刷新"}
          onClick={refresh}
          disabled={loading}
        >
          <RefreshCcw className={loading ? "spin" : ""} aria-hidden="true" />
        </button>
      </div>

      <div className={`cockpit-deck${showProcess ? "" : " is-single"}`}>
        <ExceptionTriage d={dashboard} />
        {showProcess ? <StageHealthPanel p={process} /> : null}

        <ClosedLoopRail a={ai} d={dashboard} show={showAi} />

        <div className="cockpit-support-row">
          {showMaterial ? (
            <SupportTile
              title="材料就绪"
              value={dashboard.materialBatches.verified}
              unit="批已核验"
              hint={`共 ${dashboard.materialBatches.total} 批`}
              href="/materials?tab=overview"
              tone={dashboard.materialBatches.failSpec > 0 ? "warn" : "ok"}
              rows={[
                { label: "已核验", value: String(dashboard.materialBatches.verified) },
                { label: "失效规格", value: String(dashboard.materialBatches.failSpec) },
              ]}
            />
          ) : null}
          <SupportTile
            title="质量合格率"
            value={dashboard.qualityPassRate.toFixed(1)}
            unit="%"
            hint={`健康分 ${dashboard.healthScore.toFixed(0)}/100`}
            href="/quality?tab=measurements"
            tone={
              dashboard.healthScore >= 80 ? "ok" : dashboard.healthScore >= 60 ? "warn" : "bad"
            }
            rows={[
              { label: "一次合格率", value: `${dashboard.qualityPassRate.toFixed(1)}%` },
              { label: "待审批推荐", value: String(dashboard.pendingRecommendations) },
            ]}
          />
          {showCalibration ? (
            <SupportTile
              title="校准预警"
              value={dashboard.calibrationAlerts.expiring30d}
              unit="件/30天"
              hint={
                dashboard.calibrationAlerts.expired > 0
                  ? `已过期 ${dashboard.calibrationAlerts.expired}`
                  : "无过期"
              }
              href="/instruments"
              tone={
                dashboard.calibrationAlerts.expired > 0
                  ? "bad"
                  : dashboard.calibrationAlerts.expiring30d > 0
                    ? "warn"
                    : "ok"
              }
              rows={[
                { label: "30 天内到期", value: String(dashboard.calibrationAlerts.expiring30d) },
                { label: "已过期", value: String(dashboard.calibrationAlerts.expired) },
              ]}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
