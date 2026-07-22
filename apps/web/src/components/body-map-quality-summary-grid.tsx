"use client";

import { useMemo, useState } from "react";

export type BodyMapMetricReading = {
  metric_code: string;
  metric_name?: string | null;
  value?: number | null;
  unit?: string | null;
  judgement?: string | null;
  is_primary?: boolean;
};

export type BodyMapQualitySummary = {
  quality_type: string;
  metric_code?: string | null;
  metric_name?: string | null;
  value?: number | null;
  unit?: string | null;
  measured_at?: string | null;
  data_no?: string | null;
  judgement?: string | null;
  reliability_status?: string | null;
  metrics?: BodyMapMetricReading[];
};

const QUALITY_TYPE_LABELS: Record<string, string> = {
  ORANGE_PEEL: "橘皮",
  COLOR_DIFFERENCE: "色差",
  THICKNESS: "膜厚",
};

const JUDGEMENT_LABELS: Record<string, string> = {
  PASS: "合格",
  FAIL: "超差",
  NO_STANDARD: "无标准",
  INVALID: "无效",
};

const RELIABILITY_LABELS: Record<string, string> = {
  VERIFIED: "已核验",
  UNVERIFIED: "未核验",
  FAILED: "可靠性失败",
};

function formatValue(value: number | null | undefined, unit?: string | null): string {
  if (value == null) return "—";
  const text = Number.isInteger(value) ? String(value) : value.toFixed(2);
  return unit ? `${text} ${unit}` : text;
}

function defaultMetricCode(summary: BodyMapQualitySummary): string {
  const metrics = summary.metrics ?? [];
  if (summary.metric_code && metrics.some((item) => item.metric_code === summary.metric_code)) {
    return summary.metric_code;
  }
  const withValue = metrics.find((item) => item.value != null);
  if (withValue) return withValue.metric_code;
  const primary = metrics.find((item) => item.is_primary);
  if (primary) return primary.metric_code;
  return metrics[0]?.metric_code ?? summary.metric_code ?? "";
}

function QualityTypeCard({ summary }: { summary: BodyMapQualitySummary }) {
  const metrics = summary.metrics ?? [];
  const [selectedCode, setSelectedCode] = useState(() => defaultMetricCode(summary));
  const [showAll, setShowAll] = useState(false);

  const selected = useMemo(() => {
    return (
      metrics.find((item) => item.metric_code === selectedCode) ??
      metrics.find((item) => item.metric_code === summary.metric_code) ??
      metrics[0] ??
      null
    );
  }, [metrics, selectedCode, summary.metric_code]);

  const displayValue = selected?.value ?? summary.value;
  const displayUnit = selected?.unit ?? summary.unit;
  const displayJudgement = selected?.judgement ?? summary.judgement;
  const filledCount = metrics.filter((item) => item.value != null).length;

  return (
    <article data-judgement={displayJudgement ?? (displayValue == null ? "EMPTY" : "PASS")}>
      <div className="body-map-quality-card-head">
        <span>{QUALITY_TYPE_LABELS[summary.quality_type] ?? summary.quality_type}</span>
        {metrics.length > 1 ? (
          <label className="body-map-metric-switch">
            <span className="sr-only">切换指标</span>
            <select
              value={selected?.metric_code ?? ""}
              onChange={(event) => setSelectedCode(event.target.value)}
            >
              {metrics.map((item) => (
                <option key={item.metric_code} value={item.metric_code}>
                  {item.metric_name ?? item.metric_code}
                  {item.value == null ? "（无数据）" : ""}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <small>{selected?.metric_name ?? summary.metric_name ?? summary.metric_code ?? "—"}</small>
        )}
      </div>
      <strong className="mono">{formatValue(displayValue, displayUnit)}</strong>
      <small>
        {selected?.metric_name ?? selected?.metric_code ?? summary.metric_name ?? "—"}
        {displayJudgement
          ? ` · ${JUDGEMENT_LABELS[displayJudgement] ?? displayJudgement}`
          : " · 无已核验数据"}
      </small>
      {summary.reliability_status ? (
        <span className={`body-map-reliability reliability-${summary.reliability_status.toLowerCase()}`}>
          {RELIABILITY_LABELS[summary.reliability_status] ?? summary.reliability_status}
        </span>
      ) : null}
      {summary.measured_at ? (
        <small className="mono">
          {new Date(summary.measured_at).toLocaleString("zh-CN", { hour12: false })}
        </small>
      ) : null}
      {metrics.length ? (
        <div className="body-map-metric-actions">
          <button
            type="button"
            className="button button-secondary body-map-metric-toggle"
            onClick={() => setShowAll((current) => !current)}
          >
            {showAll ? "收起全字段" : `全字段阅览（${filledCount}/${metrics.length}）`}
          </button>
        </div>
      ) : null}
      {showAll ? (
        <div className="body-map-metric-table">
          {metrics.map((item) => (
            <button
              key={item.metric_code}
              type="button"
              className={`body-map-metric-row ${item.metric_code === selected?.metric_code ? "selected" : ""}`}
              onClick={() => setSelectedCode(item.metric_code)}
            >
              <span>
                <strong>{item.metric_name ?? item.metric_code}</strong>
                <small className="mono">{item.metric_code}</small>
              </span>
              <span className="mono">{formatValue(item.value, item.unit)}</span>
              <span>
                {item.judgement
                  ? JUDGEMENT_LABELS[item.judgement] ?? item.judgement
                  : item.value == null
                    ? "—"
                    : ""}
              </span>
            </button>
          ))}
        </div>
      ) : null}
    </article>
  );
}

export function BodyMapQualitySummaryGrid({
  summaries,
  emptyText = "暂无质量数据",
}: {
  summaries: BodyMapQualitySummary[];
  emptyText?: string;
}) {
  if (!summaries.length) {
    return <div className="master-empty">{emptyText}</div>;
  }
  return (
    <div className="body-map-quality-grid">
      {summaries.map((summary) => (
        <QualityTypeCard
          key={`${summary.quality_type}:${summary.data_no ?? ""}:${summary.measured_at ?? ""}`}
          summary={summary}
        />
      ))}
    </div>
  );
}
