"use client";

import { AlertTriangle, CheckCircle2, LoaderCircle, RefreshCw, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { OvpCard, OvpCardList } from "@/components/ovp-card";
import { useAuth } from "@/lib/auth-context";
import { WorkspaceEmptyState } from "@/components/workspace-empty-state";

type InstrumentHealth = {
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
  summary: {
    instruments: number;
    active_instruments: number;
    methods: number;
    references: number;
    calibrations: number;
    valid_calibrations: number;
    import_profiles: number;
  };
};

const INSTRUMENT_LABELS: Record<string, string> = {
  BYK_ORANGE_PEEL: "BYK 橘皮仪",
  BYK_COLOR: "BYK 色差仪",
  FISCHER_THICKNESS: "Fischer 膜厚仪",
};

function gaugeColor(value: number): string {
  if (value >= 90) return "var(--teal-500)";
  if (value >= 70) return "var(--amber-500)";
  return "var(--red-500)";
}

export function InstrumentsOverviewPanel({ embedded = false }: { embedded?: boolean }) {
  const { actor } = useAuth();
  const [data, setData] = useState<InstrumentHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [monitorResp, summaryResp] = await Promise.all([
        fetch("/api/quality/monitoring/quality-summary", {
          cache: "no-store",
        }),
        fetch("/api/quality/governance/summary", {
          cache: "no-store",
        }),
      ]);
      if (!monitorResp.ok || !summaryResp.ok) throw new Error("加载失败");
      const monitor = (await monitorResp.json()) as { instruments: InstrumentHealth["instruments"] };
      const summary = (await summaryResp.json()) as InstrumentHealth["summary"];
      setData({ instruments: monitor.instruments, summary });
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  if (!actor.isAuthenticated) {
    return (
      <div className={embedded ? "embedded-stack" : "page-stack"}>
        <WorkspaceEmptyState
          icon={ShieldCheck}
          title="请先登录后查看仪器管理"
          description="仪器管理页面展示仪器台账、校准状态与可靠性指标，需要登录后再继续。"
          compact
        />
      </div>
    );
  }

  return (
    <div className={embedded ? "embedded-stack" : "page-stack"}>
      <div className="embedded-toolbar">
        <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} /> 刷新
        </button>
      </div>
      {error ? (
        <button className="message-banner message-error" onClick={() => setError("")}>
          {error}
          <X />
        </button>
      ) : null}

      {loading ? (
        <div className="master-empty">
          <LoaderCircle className="spin" /> 正在加载仪器管理数据...
        </div>
      ) : data ? (
        <>
          <section className="ovp-kpi-strip" aria-label="仪器概览头条">
            <div className="ovp-kpi-tile">
              <span className="ovp-kpi-tile-label">在用仪器</span>
              <div className="ovp-kpi-tile-value">
                <strong>{data.summary.active_instruments}</strong>
                <span>/ {data.summary.instruments}</span>
              </div>
              <span className="ovp-kpi-tile-hint">活动 / 总数</span>
            </div>
            <div className="ovp-kpi-tile">
              <span className="ovp-kpi-tile-label">校准健康度</span>
              <div className="ovp-kpi-tile-value">
                <strong style={{ color: gaugeColor(data.instruments.calibration_health) }}>
                  {data.instruments.calibration_health}
                </strong>
                <span>%</span>
              </div>
              <span className="ovp-kpi-tile-hint">
                {data.instruments.valid_calibrations} / {data.instruments.total_calibrations} 有效
              </span>
            </div>
            <div className="ovp-kpi-tile">
              <span className="ovp-kpi-tile-label">校准过期</span>
              <div className="ovp-kpi-tile-value">
                <strong style={{ color: data.instruments.expired_calibrations > 0 ? "var(--red)" : "var(--teal-700)" }}>
                  {data.instruments.expired_calibrations}
                </strong>
                <span>条</span>
              </div>
              <span className="ovp-kpi-tile-hint">需补做校准</span>
            </div>
            <div className="ovp-kpi-tile">
              <span className="ovp-kpi-tile-label">测量方法</span>
              <div className="ovp-kpi-tile-value">
                <strong>{data.summary.methods}</strong>
                <span>个</span>
              </div>
              <span className="ovp-kpi-tile-hint">参考件 {data.summary.references}</span>
            </div>
          </section>

          <div className="ovp-card-grid">
            <OvpCard
              title="待校准仪器"
              kpiLabel="待校准"
              kpiValue={data.instruments.needs_calibration.length}
              kpiUnit="台"
              accent={data.instruments.needs_calibration.length > 0 ? "warning" : "positive"}
              viewAllHref="/instruments?tab=governance"
              viewAllLabel="去维护校准"
            >
              {data.instruments.needs_calibration.length > 0 ? (
                <OvpCardList
                  items={data.instruments.needs_calibration.slice(0, 5).map((inst) => ({
                    label: `${inst.name} · ${INSTRUMENT_LABELS[inst.instrument_type] ?? inst.instrument_type}`,
                    value: inst.code,
                  }))}
                />
              ) : (
                <div className="ovp-card-empty">
                  <CheckCircle2 aria-hidden="true" /> 所有仪器校准有效
                </div>
              )}
            </OvpCard>

            <OvpCard
              title="仪器台账"
              kpiLabel="总数"
              kpiValue={data.summary.instruments}
              kpiUnit="台"
              accent="info"
              viewAllHref="/instruments?tab=governance"
              viewAllLabel="管理仪器"
            >
              <OvpCardList
                items={[
                  { label: "在用仪器", value: String(data.summary.active_instruments) },
                  { label: "导入模板", value: String(data.summary.import_profiles) },
                ]}
              />
            </OvpCard>

            <OvpCard
              title="校准记录"
              kpiLabel="总记录"
              kpiValue={data.summary.calibrations}
              kpiUnit="条"
              accent={data.instruments.expired_calibrations > 0 ? "negative" : "positive"}
              viewAllHref="/instruments?tab=governance"
              viewAllLabel="查看校准"
            >
              <OvpCardList
                items={[
                  { label: "有效校准", value: String(data.instruments.valid_calibrations) },
                  { label: "过期校准", value: String(data.instruments.expired_calibrations) },
                ]}
              />
            </OvpCard>
          </div>

          {data.instruments.needs_calibration.length > 0 ? (
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">校准预警</span>
                  <h2>待校准仪器清单</h2>
                </div>
                <span className="record-status status-off">
                  {data.instruments.needs_calibration.length} 个待校准
                </span>
              </div>
              <div className="calibration-alerts">
                {data.instruments.needs_calibration.map((inst) => (
                  <Link
                    className="calibration-alert-row"
                    key={inst.id}
                    href="/instruments?tab=governance"
                  >
                    <AlertTriangle className="alert-icon" />
                    <div>
                      <strong>{inst.name}</strong>
                      <span>
                        {INSTRUMENT_LABELS[inst.instrument_type] ?? inst.instrument_type} · {inst.code}
                      </span>
                    </div>
                    <span className="record-status status-off">待校准</span>
                  </Link>
                ))}
              </div>
            </section>
          ) : null}
        </>
      ) : (
        <WorkspaceEmptyState
          icon={ShieldCheck}
          title="暂无仪器管理数据"
          description="系统还没有仪器台账或校准记录，补齐基础数据后这里会自动展示。"
        />
      )}
    </div>
  );
}
