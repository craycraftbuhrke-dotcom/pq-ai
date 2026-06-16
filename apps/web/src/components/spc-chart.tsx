"use client";

import { useMemo } from "react";

type SpcPoint = {
  label: string;
  value: number;
  judgement: string; // "PASS" | "FAIL" | "NO_STANDARD"
  measuredAt: string;
};

type SpcChartProps = {
  title: string;
  unit?: string;
  series: SpcPoint[];
  mean?: number | null;
  ucl?: number | null;
  lcl?: number | null;
  standardMin?: number | null;
  standardMax?: number | null;
  width?: number;
  height?: number;
};

const TEAL = "var(--teal-500)";
const RED = "var(--red-500)";
const GRAY = "var(--color-muted)";
const TEXT = "var(--color-text)";
const MUTED = "var(--color-muted)";
const LINE = "var(--color-border)";

function pointColor(judgement: string): string {
  if (judgement === "PASS") return TEAL;
  if (judgement === "FAIL") return RED;
  return GRAY;
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    const hh = String(d.getHours()).padStart(2, "0");
    const min = String(d.getMinutes()).padStart(2, "0");
    return `${mm}/${dd} ${hh}:${min}`;
  } catch {
    return iso;
  }
}

export function SpcChart({
  title,
  unit = "",
  series,
  mean,
  ucl,
  lcl,
  standardMin,
  standardMax,
  width = 800,
  height = 340,
}: SpcChartProps) {
  const margin = { top: 20, right: 24, bottom: 48, left: 64 };

  const { plotW, plotH, yMin, yMax, points, xTicks } = useMemo(() => {
    const pw = Math.max(width - margin.left - margin.right, 100);
    const ph = Math.max(height - margin.top - margin.bottom, 60);
    const n = series.length;

    // compute Y range
    const rawVals = series.map((p) => p.value);
    const allVals = [
      ...rawVals,
      mean,
      ucl,
      lcl,
      standardMin,
      standardMax,
    ].filter((v): v is number => v != null && !Number.isNaN(v));

    let dataMin = Math.min(...rawVals);
    let dataMax = Math.max(...rawVals);
    const range = dataMax - dataMin || 1;
    const pad = range * 0.1;
    let tyMin = dataMin - pad;
    let tyMax = dataMax + pad;

    if (allVals.length > 0) {
      const absMin = Math.min(...allVals);
      const absMax = Math.max(...allVals);
      if (absMin < tyMin) tyMin = absMin - pad * 0.5;
      if (absMax > tyMax) tyMax = absMax + pad * 0.5;
    }

    // make range slightly nicer
    const niceRange = tyMax - tyMin;
    tyMin = tyMin - niceRange * 0.05;
    tyMax = tyMax + niceRange * 0.05;

    // compute point positions
    const pts = series.map((p, i) => ({
      x: margin.left + (n > 1 ? (i / (n - 1)) * pw : pw / 2),
      y:
        margin.top +
        ph -
        ((p.value - tyMin) / (tyMax - tyMin || 1)) * ph,
      ...p,
    }));

    // x-axis ticks: show every Nth label
    const maxTickLabels = Math.min(12, n);
    const step = Math.max(1, Math.ceil(n / maxTickLabels));
    const ticks = series
      .map((p, i) => ({ i, label: p.measuredAt }))
      .filter((_, i) => i % step === 0);

    return {
      plotW: pw,
      plotH: ph,
      yMin: tyMin,
      yMax: tyMax,
      points: pts,
      xTicks: ticks,
    };
  }, [series, mean, ucl, lcl, standardMin, standardMax, width, height]);

  // Y-axis ticks
  const yTicks = useMemo(() => {
    const steps = 5;
    const tickVals: number[] = [];
    for (let i = 0; i <= steps; i++) {
      tickVals.push(yMin + ((yMax - yMin) * i) / steps);
    }
    return tickVals;
  }, [yMin, yMax]);

  const linePathD = useMemo(() => {
    if (points.length === 0) return "";
    return points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
      .join(" ");
  }, [points]);

  const toY = (v: number) =>
    margin.top + plotH - ((v - yMin) / (yMax - yMin || 1)) * plotH;

  const refLines: { label: string; value: number; stroke: string; dash: string }[] =
    [];
  if (ucl != null) refLines.push({ label: `UCL ${ucl}`, value: ucl, stroke: TEAL, dash: "6,3" });
  if (lcl != null) refLines.push({ label: `LCL ${lcl}`, value: lcl, stroke: TEAL, dash: "6,3" });
  if (mean != null) refLines.push({ label: `Mean ${mean}`, value: mean, stroke: MUTED, dash: "4,2" });
  if (standardMax != null)
    refLines.push({ label: `Std Max ${standardMax}`, value: standardMax, stroke: GRAY, dash: "2,2" });
  if (standardMin != null)
    refLines.push({ label: `Std Min ${standardMin}`, value: standardMin, stroke: GRAY, dash: "2,2" });

  if (series.length === 0) {
    return (
      <figure style={{ width, height }} className="spc-chart">
        <figcaption style={{ color: TEXT, fontWeight: 600, marginBottom: 8 }}>{title}</figcaption>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: height - 28,
            color: MUTED,
          }}
        >
          No data
        </div>
      </figure>
    );
  }

  return (
    <figure style={{ width, height, margin: 0 }}>
      <figcaption
        style={{
          color: TEXT,
          fontWeight: 600,
          fontSize: 13,
          marginBottom: 4,
        }}
      >
        {title}
      </figcaption>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={title}
        style={{ width: "100%", height: "auto", display: "block" }}
      >
        {/* Y-axis grid lines + labels */}
        {yTicks.map((v, i) => {
          const y = toY(v);
          return (
            <g key={`y-${i}`}>
              <line
                x1={margin.left}
                y1={y}
                x2={width - margin.right}
                y2={y}
                stroke={LINE}
                strokeWidth={0.5}
              />
              <text
                x={margin.left - 6}
                y={y + 4}
                textAnchor="end"
                fill={MUTED}
                fontSize={11}
              >
                {Number.isInteger(v) ? v : v.toFixed(2)}
              </text>
            </g>
          );
        })}

        {/* Reference lines */}
        {refLines.map((rl) => {
          const y = toY(rl.value);
          return (
            <g key={rl.label}>
              <line
                x1={margin.left}
                y1={y}
                x2={width - margin.right}
                y2={y}
                stroke={rl.stroke}
                strokeWidth={1}
                strokeDasharray={rl.dash}
              />
              <text
                x={width - margin.right - 4}
                y={y - 4}
                textAnchor="end"
                fill={rl.stroke}
                fontSize={10}
              >
                {rl.label}
              </text>
            </g>
          );
        })}

        {/* X-axis */}
        <line
          x1={margin.left}
          y1={margin.top + plotH}
          x2={width - margin.right}
          y2={margin.top + plotH}
          stroke={LINE}
          strokeWidth={1}
        />

        {/* X-axis tick labels */}
        {xTicks.map((t) => {
          const x =
            margin.left +
            (t.i / (series.length - 1 || 1)) * plotW;
          return (
            <text
              key={`xt-${t.i}`}
              x={x}
              y={margin.top + plotH + 16}
              textAnchor="middle"
              fill={MUTED}
              fontSize={10}
            >
              {formatTime(t.label)}
            </text>
          );
        })}

        {/* Line */}
        <path
          d={linePathD}
          fill="none"
          stroke={TEAL}
          strokeWidth={2}
          strokeLinejoin="round"
        />

        {/* Points */}
        {points.map((p) => (
          <g key={`pt-${p.measuredAt}-${p.value}`}>
            <circle
              cx={p.x}
              cy={p.y}
              r={4}
              fill={pointColor(p.judgement)}
              stroke="#fff"
              strokeWidth={1.5}
            />
            <title>
              {`${p.value}${unit ? ` ${unit}` : ""} — ${formatTime(p.measuredAt)} — ${p.judgement}`}
            </title>
          </g>
        ))}

        {/* Y-axis title */}
        {unit ? (
          <text
            x={12}
            y={margin.top + plotH / 2}
            textAnchor="middle"
            fill={MUTED}
            fontSize={11}
            transform={`rotate(-90, 12, ${margin.top + plotH / 2})`}
          >
            {unit}
          </text>
        ) : null}
      </svg>
    </figure>
  );
}
