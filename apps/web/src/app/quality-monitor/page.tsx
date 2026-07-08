"use client";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  CircleGauge,
  Clock,
  RefreshCw,
  ShieldCheck,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/lib/auth-context";
import { WorkspaceEmptyState } from "@/components/workspace-empty-state";

type QualityHealth = {
  overview: {
    total_measurements: number;
    valid_measurements: number;
    verified_measurements: number;
    unverified_measurements: number;
    failed_measurements: number;
    metric_completeness: number;
    verification_rate: number;
  };
  instruments: {
    total: number;
    active: number;
    total_calibrations: number;
    valid_calibrations: number;
    expired_calibrations: number;
    calibration_health: number;
    needs_calibration: Array<{
      id: string;
      code: string;
      name: string;
      instrument_type: string;
      status: string;
    }>;
  };
  standards: {
    active_standards: number;
  };
  reliability_by_type: Array<{
    quality_type: string;
    total: number;
    verified: number;
    failed: number;
  }>;
  health_score: number;
};

const TYPE_LABELS: Record<string, string> = {
  ORANGE_PEEL: "橘皮",
  COLOR_DIFFERENCE: "色差",
  THICKNESS: "膜厚",
};

const INSTRUMENT_LABELS: Record<string, string> = {
  BYK_ORANGE_PEEL: "BYK 橘皮仪",
  BYK_COLOR: "BYK 色差仪",
  FISCHER_THICKNESS: "Fischer 膜厚仪",
};

function getApiKey(): string {
  const match = document.cookie.match(/(?:^|;\s*)pq_api_key=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function gaugeColor(value: number): string {
  if (value >= 90) return "var(--teal-500)";
  if (value >= 70) return "var(--amber-500)";
  return "var(--red-500)";
}

function GaugeArc({ value, label, size = 80 }: { value: number; label: string; size?: number }) {
  const radius = (size - 10) / 2;
  const circumference = radius * Math.PI;
  const strokeDashoffset = circumference * (1 - value / 100);
  const color = gaugeColor(value);

  return (
    <div className="gauge">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2 + 5}
          r={radius}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={0}
          transform={`rotate(180 ${size / 2} ${size / 2 + 5})`}
        />
        <circle
          cx={size / 2}
          cy={size / 2 + 5}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          transform={`rotate(180 ${size / 2} ${size / 2 + 5})`}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="gauge-value">
        <strong style={{ color }}>{value.toFixed(1)}%</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

export default function QualityMonitorPage() {
  const { actor } = useAuth();
  const [data, setData] = useState<QualityHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await fetch("/api/quality/monitoring/quality-summary", {
        cache: "no-store",
        headers: { "x-api-key": getApiKey() },
      });
      if (!resp.ok) throw new Error("加载失败");
      setData((await resp.json()) as QualityHealth);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  if (!actor.isAuthenticated) {
    return (
      <div className="page-stack">
        <WorkspaceEmptyState
          icon={ShieldCheck}
          title="请先登录后查看质量监控"
          description="质量监控页面会展示测量完整率、验证率和仪器校准健康度，需要登录后再继续。"
          compact
        />
      </div>
    );
  }

  const healthColor = gaugeColor(data?.health_score ?? 0);
  const healthLabel = (data?.health_score ?? 0) >= 90 ? "健康" : (data?.health_score ?? 0) >= 70 ? "需要注意" : "需关注";

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">PHASE 4 · QUALITY MONITORING</span>
          <h1>数据质量监控</h1>
          <p>实时监控测量数据可靠性、仪器校准状态与质量标准覆盖度。</p>
        </div>
        <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} /> 刷新
        </button>
      </header>
      {error ? <button className="message-banner message-error" onClick={() => setError("")}>{error}<X /></button> : null}

      {loading ? (
        <div className="master-empty"><Activity /> 正在加载质量监控数据...</div>
      ) : data ? (
        <>
          <section className="monitor-hero">
            <div className="monitor-health-card" style={{ borderColor: healthColor }}>
              <div className="monitor-health-main">
                <GaugeArc value={data.health_score} label="综合健康度" size={120} />
                <div className="monitor-health-details">
                  <h2>数据链路 {healthLabel}</h2>
                  <p>基于测量完整率、验证率和校准健康度综合评估</p>
                  <div className="monitor-health-metrics">
                    <span>完整率 <strong>{data.overview.metric_completeness}%</strong></span>
                    <span>验证率 <strong>{data.overview.verification_rate}%</strong></span>
                    <span>校准 <strong>{data.instruments.calibration_health}%</strong></span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="module-stat-strip">
            <article><CircleGauge /><span>测量总数</span><strong>{data.overview.total_measurements}</strong><small>有效 {data.overview.valid_measurements}</small></article>
            <article><CheckCircle2 /><span>已验证</span><strong>{data.overview.verified_measurements}</strong><small>可进入 SPC 和 AI</small></article>
            <article><AlertTriangle /><span>失败</span><strong>{data.overview.failed_measurements}</strong><small>可靠性问题</small></article>
            <article><Clock /><span>校准过期</span><strong>{data.instruments.expired_calibrations}</strong><small>共 {data.instruments.total_calibrations} 条记录</small></article>
          </section>

          <div className="monitor-grid">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">RELIABILITY</span>
                  <h2>按质量类型统计</h2>
                </div>
              </div>
              <div className="reliability-bars">
                {data.reliability_by_type.length ? data.reliability_by_type.map((item) => {
                  const verifiedPct = item.total ? (item.verified / item.total * 100).toFixed(1) : "0";
                  const failedPct = item.total ? (item.failed / item.total * 100).toFixed(1) : "0";
                  return (
                    <div className="reliability-bar-row" key={item.quality_type}>
                      <div className="reliability-bar-label">
                        <strong>{TYPE_LABELS[item.quality_type] ?? item.quality_type}</strong>
                        <span>{item.total} 条</span>
                      </div>
                      <div className="reliability-bar-track">
                        <div className="reliability-bar-verified" style={{ width: `${verifiedPct}%` }} title={`已验证 ${verifiedPct}%`} />
                        <div className="reliability-bar-failed" style={{ width: `${failedPct}%`, marginLeft: `${verifiedPct}%` }} title={`失败 ${failedPct}%`} />
                      </div>
                      <div className="reliability-bar-stats">
                        <span className="stat-verified">{verifiedPct}%</span>
                        {Number(failedPct) > 0 ? <span className="stat-failed">{failedPct}%</span> : null}
                      </div>
                    </div>
                  );
                }) : (
                  <WorkspaceEmptyState
                    icon={Activity}
                    title="暂无质量类型统计数据"
                    description="当前还没有可用于聚合的质量类型测量记录，录入测量数据后这里会自动形成统计。"
                    compact
                  />
                )}
              </div>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">CALIBRATION</span>
                  <h2>仪器校准状态</h2>
                </div>
                <span className={`record-status ${data.instruments.needs_calibration.length === 0 ? "status-on" : "status-off"}`}>
                  {data.instruments.needs_calibration.length === 0 ? "全部正常" : `${data.instruments.needs_calibration.length} 个待校准`}
                </span>
              </div>
              {data.instruments.needs_calibration.length > 0 ? (
                <div className="calibration-alerts">
                  {data.instruments.needs_calibration.map((inst) => (
                    <div className="calibration-alert-row" key={inst.id}>
                      <AlertTriangle className="alert-icon" />
                      <div>
                        <strong>{inst.name}</strong>
                        <span>{INSTRUMENT_LABELS[inst.instrument_type] ?? inst.instrument_type} · {inst.code}</span>
                      </div>
                      <span className="record-status status-off">待校准</span>
                    </div>
                  ))}
                </div>
              ) : (
                <WorkspaceEmptyState
                  icon={CheckCircle2}
                  title="当前无需补做仪器校准"
                  description="所有需要校准的仪器均处于有效校准期内，后续有到期记录时会自动出现在这里。"
                  compact
                />
              )}
            </section>
          </div>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">DATA QUALITY INDICATORS</span>
                <h2>数据质量指标</h2>
              </div>
            </div>
            <div className="monitor-indicators">
              <div className="monitor-indicator">
                <div className="indicator-bar">
                  <div className="indicator-fill" style={{ width: `${data.overview.metric_completeness}%`, background: gaugeColor(data.overview.metric_completeness) }} />
                </div>
                <div className="indicator-info">
                  <span>数据完整率</span>
                  <strong>{data.overview.metric_completeness}%</strong>
                  <small>有效 / 全部</small>
                </div>
              </div>
              <div className="monitor-indicator">
                <div className="indicator-bar">
                  <div className="indicator-fill" style={{ width: `${data.overview.verification_rate}%`, background: gaugeColor(data.overview.verification_rate) }} />
                </div>
                <div className="indicator-info">
                  <span>可靠性验证率</span>
                  <strong>{data.overview.verification_rate}%</strong>
                  <small>已验证 / 有效</small>
                </div>
              </div>
              <div className="monitor-indicator">
                <div className="indicator-bar">
                  <div className="indicator-fill" style={{ width: `${data.instruments.calibration_health}%`, background: gaugeColor(data.instruments.calibration_health) }} />
                </div>
                <div className="indicator-info">
                  <span>校准健康度</span>
                  <strong>{data.instruments.calibration_health}%</strong>
                  <small>{data.instruments.valid_calibrations} / {data.instruments.total_calibrations}</small>
                </div>
              </div>
              <div className="monitor-indicator">
                <div className="indicator-bar">
                  <div className="indicator-fill" style={{ width: `${data.standards.active_standards ? 100 : 0}%`, background: gaugeColor(data.standards.active_standards ? 100 : 0) }} />
                </div>
                <div className="indicator-info">
                  <span>生效质量标准</span>
                  <strong>{data.standards.active_standards}</strong>
                  <small>条</small>
                </div>
              </div>
            </div>
          </section>
        </>
      ) : (
        <WorkspaceEmptyState
          icon={ShieldCheck}
          title="暂无质量监控数据"
          description="系统还没有形成可用于监控的测量、校准或质量标准数据，补齐基础数据后这里会自动展示。"
        />
      )}
    </div>
  );
}
