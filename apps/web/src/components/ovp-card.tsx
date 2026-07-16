"use client";

import Link from "next/link";
import { ArrowRight, ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import type { ReactNode } from "react";

export type OvpTrend = "up" | "down" | "flat";
export type OvpAccent = "positive" | "warning" | "negative" | "neutral" | "info";

export type OvpCardProps = {
  title: string;
  kpiValue: string | number;
  kpiUnit?: string;
  kpiLabel?: string;
  trend?: OvpTrend;
  trendLabel?: string;
  accent?: OvpAccent;
  viewAllHref: string;
  viewAllLabel?: string;
  roles?: readonly string[];
  children?: ReactNode;
};

const trendIcon: Record<OvpTrend, typeof ArrowUpRight> = {
  up: ArrowUpRight,
  down: ArrowDownRight,
  flat: Minus,
};

export function OvpCard({
  title,
  kpiValue,
  kpiUnit,
  kpiLabel,
  trend,
  trendLabel,
  accent = "neutral",
  viewAllHref,
  viewAllLabel = "查看全部",
  children,
}: OvpCardProps) {
  const TrendIcon = trend ? trendIcon[trend] : null;
  return (
    <article className={`ovp-card ovp-card-accent-${accent}`}>
      <header className="ovp-card-head">
        <div className="ovp-card-title-wrap">
          <h3 className="ovp-card-title">{title}</h3>
          {kpiLabel ? <span className="ovp-card-kpi-label">{kpiLabel}</span> : null}
        </div>
        <div className="ovp-card-kpi">
          <strong className="ovp-card-kpi-value">{kpiValue}</strong>
          {kpiUnit ? <span className="ovp-card-kpi-unit">{kpiUnit}</span> : null}
          {TrendIcon ? (
            <span className={`ovp-card-trend ovp-card-trend-${trend}`}>
              <TrendIcon aria-hidden="true" />
              {trendLabel ? <span className="ovp-card-trend-label">{trendLabel}</span> : null}
            </span>
          ) : null}
        </div>
      </header>
      {children ? <div className="ovp-card-body">{children}</div> : null}
      <Link className="ovp-card-viewall" href={viewAllHref}>
        {viewAllLabel}
        <ArrowRight aria-hidden="true" />
      </Link>
    </article>
  );
}

export function OvpCardList({ items }: { items: Array<{ label: string; value?: string }> }) {
  if (!items.length) {
    return <div className="ovp-card-empty">暂无数据</div>;
  }
  return (
    <ul className="ovp-card-list">
      {items.map((item, idx) => (
        <li key={`${item.label}-${idx}`} className="ovp-card-list-row">
          <span className="ovp-card-list-label">{item.label}</span>
          {item.value ? <span className="ovp-card-list-value">{item.value}</span> : null}
        </li>
      ))}
    </ul>
  );
}

export function OvpCardStatusStrip({
  segments,
}: {
  segments: Array<{ label: string; tone: OvpAccent }>;
}) {
  if (!segments.length) {
    return <div className="ovp-card-empty">暂无数据</div>;
  }
  return (
    <div className="ovp-card-strip">
      {segments.map((seg) => (
        <span key={seg.label} className={`ovp-card-strip-seg ovp-card-strip-${seg.tone}`}>
          {seg.label}
        </span>
      ))}
    </div>
  );
}
