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
import Link from "next/link";
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

export function QualityMonitorPanel({ embedded = false }: { embedded?: boolean }) {
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
      <div className={embedded ? "embedded-stack" : "page-stack"}>
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
    <div className={embedded ? "embedded-stack" : "page-stack"}>
      {!embedded ? (
      <header className="page-header">
        <div>
          <span className="page-kicker">数据可靠性</span>
          <h1>数据可靠性</h1>
          <p>核验率、校准健康度与标准覆盖。真·SPC 请到「SPC 与趋势」。</p>
        </div>
        <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} /> 刷新
        </button>
      </header>
      ) : (
        <div className="embedded-toolbar">
          <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
            <RefreshCw className={loading ? "spin" : ""} /> 刷新
          </button>
        </div>
      )}
      {error ? <button className="message-banner message-error" onClick={() => setError("")}>{error}<X /></button> : null}

      {loading ? (
        <div className="master-empty"><Activity /> 正在加载质量监控数据...</div>
      ) : data ? (
        <>
          <section className="ovp-kpi-strip" aria-label="质量概览头条">
            <div className="ovp-kpi-tile">
              <span className="ovp-kpi-tile-label">一次合格率</span>
              <div className="ovp-kpi-tile-value">
                <strong>
                  {data.overview.total_measurements > 0
                    ? ((data.overview.valid_measurements / data.overview.total_measurements) * 100).toFixed(1)
                    : "0.0"}
                </strong>
                <span>%</span>
              </div>
              <span className="ovp-kpi-tile-hint">有效测量 / 总测量</span>
            </div>
            <div className="ovp-kpi-tile">
              <span className="ovp-kpi-tile-label">超差测量</span>
              <div className="ovp-kpi-tile-value">
                <strong>{data.overview.failed_measurements}</strong>
                <span>条</span>
              </div>
              <span className="ovp-kpi-tile-hint">需判定与处理</span>
            </div>
            <div className="ovp-kpi-tile">
              <span className="ovp-kpi-tile-label">生效标准</span>
              <div className="ovp-kpi-tile-value">
                <strong>{data.standards.active_standards}</strong>
                <span>项</span>
              </div>
              <span className="ovp-kpi-tile-hint">质量判定依据</span>
            </div>
            <Link className="ovp-kpi-tile" href="/instruments">
              <span className="ovp-kpi-tile-label">仪器管理</span>
              <div className="ovp-kpi-tile-value">
                <strong>{data.instruments.total}</strong>
                <span>台</span>
              </div>
              <span className="ovp-kpi-tile-hint">校准健康 {data.instruments.calibration_health}% →</span>
            </Link>
          </section>
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

          <section className="module-stat-strip quality-monitor-stat-links">
            <Link className="monitor-stat-link" href="/quality?tab=measurements">
              <article><CircleGauge /><span>测量总数</span><strong>{data.overview.total_measurements}</strong><small>有效 {data.overview.valid_measurements}</small></article>
            </Link>
            <Link className="monitor-stat-link" href="/quality?tab=analytics">
              <article><CheckCircle2 /><span>已核验</span><strong>{data.overview.verified_measurements}</strong><small>可进入 SPC 与趋势</small></article>
            </Link>
            <Link className="monitor-stat-link" href="/quality?tab=measurements&filter=reliability_failed">
              <article><AlertTriangle /><span>核验失败</span><strong>{data.overview.failed_measurements}</strong><small>打开判定筛选</small></article>
            </Link>
            <Link className="monitor-stat-link" href="/instruments">
              <article><Clock /><span>校准过期</span><strong>{data.instruments.expired_calibrations}</strong><small>共 {data.instruments.total_calibrations} 条 · 去仪器管理</small></article>
            </Link>
          </section>
          <div className="quality-monitor-cta-row">
            <Link className="button button-secondary" href="/quality?tab=measurements&filter=unverified">查看未核验测量</Link>
            <Link className="button button-secondary" href="/quality?tab=analytics">打开 SPC 与趋势</Link>
            <Link className="button button-secondary" href="/instruments">维护仪器可靠性</Link>
            <Link className="button button-secondary" href="/ai?tab=predictions">去 AI 预测诊断</Link>
          </div>

          <div className="monitor-grid">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">可靠性</span>
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
                  <span className="eyebrow">校准状态</span>
                  <h2>仪器校准状态</h2>
                </div>
                <Link href="/instruments" className="text-link" style={{ fontSize: "0.82rem" }}>
                  去仪器管理 →
                </Link>
              </div>
              {data.instruments.needs_calibration.length > 0 ? (
                <div className="calibration-alerts">
                  {data.instruments.needs_calibration.map((inst) => (
                    <Link className="calibration-alert-row" key={inst.id} href="/instruments">
                      <AlertTriangle className="alert-icon" />
                      <div>
                        <strong>{inst.name}</strong>
                        <span>{INSTRUMENT_LABELS[inst.instrument_type] ?? inst.instrument_type} · {inst.code}</span>
                      </div>
                      <span className="record-status status-off">待校准</span>
                    </Link>
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
                <span className="eyebrow">数据质量指标</span>
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
              <Link className="monitor-indicator is-link" href="/instruments">
                <div className="indicator-bar">
                  <div className="indicator-fill" style={{ width: `${data.instruments.calibration_health}%`, background: gaugeColor(data.instruments.calibration_health) }} />
                </div>
                <div className="indicator-info">
                  <span>校准健康度</span>
                  <strong>{data.instruments.calibration_health}%</strong>
                  <small>{data.instruments.valid_calibrations} / {data.instruments.total_calibrations} · 去仪器</small>
                </div>
              </Link>
              <Link className="monitor-indicator is-link" href="/quality?tab=standards">
                <div className="indicator-bar">
                  <div className="indicator-fill" style={{ width: `${data.standards.active_standards ? 100 : 0}%`, background: gaugeColor(data.standards.active_standards ? 100 : 0) }} />
                </div>
                <div className="indicator-info">
                  <span>生效质量标准</span>
                  <strong>{data.standards.active_standards}</strong>
                  <small>条 · 去维护</small>
                </div>
              </Link>
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
