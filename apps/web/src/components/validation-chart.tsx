"use client";

type ValidationAxis = {
  axis: string;
  rmse: number | null;
  r2: number | null;
  status: string; // "EVALUATED", "INSUFFICIENT_AXIS_DIVERSITY", etc.
  sampleCount: number;
};

type ValidationChartProps = {
  axes: ValidationAxis[];
  width?: number;
  height?: number;
};

const TEAL = "var(--teal-500)";
const RED = "var(--red-500)";
const AMBER = "var(--amber-500, #b97918)";
const TEXT = "var(--color-text)";
const MUTED = "var(--color-muted)";
const LINE = "var(--color-border)";
const VALIDATION_MARGIN = { top: 8, right: 108, bottom: 8, left: 20 } as const;

function barColor(status: string): string {
  if (status === "EVALUATED") return TEAL;
  if (
    status.includes("INSUFFICIENT") ||
    status === "INSUFFICIENT_AXIS_DIVERSITY"
  )
    return AMBER;
  return RED;
}

function axisShortName(axis: string): string {
  const parts = axis.split("_");
  if (parts.length === 1) return axis;
  if (parts[0] === "TEMPORAL") return `Temporal ${parts.slice(1).join(" ")}`;
  return parts.join(" ");
}

export function ValidationChart({
  axes,
  width = 680,
  height,
}: ValidationChartProps) {
  const barH = 32;
  const barGap = 12;
  const labelW = 138;
  const chartLeft = VALIDATION_MARGIN.left + labelW + 12;

  const insufficientH = 20;

  const evaluatedAxes = axes.filter(
    (a) => !a.status.includes("INSUFFICIENT") && a.status !== "INSUFFICIENT_AXIS_DIVERSITY"
  );
  const insufficientAxes = axes.filter(
    (a) => a.status.includes("INSUFFICIENT") || a.status === "INSUFFICIENT_AXIS_DIVERSITY"
  );

  // Reorder: evaluated first, then insufficient
  const ordered = [...evaluatedAxes, ...insufficientAxes];

  const evalRows = evaluatedAxes.length;
  const insufRows = insufficientAxes.length;
  const actualH =
    VALIDATION_MARGIN.top +
    evalRows * (barH + barGap) +
    (insufRows > 0 ? insufRows * (insufficientH + 8) + 4 : 0) +
    VALIDATION_MARGIN.bottom;

  const svgH = height ?? Math.max(actualH + 8, 120);

  // Compute max RMSE for scaling
  const allRmse = evaluatedAxes
    .map((a) => a.rmse)
    .filter((v): v is number => v != null);
  const maxRmse = allRmse.length > 0 ? Math.max(...allRmse) : 1;

  const barAreaW = width - chartLeft - VALIDATION_MARGIN.right;

  let y = VALIDATION_MARGIN.top;

  const evalBarRects: {
    axis: ValidationAxis;
    x: number;
    y: number;
    w: number;
  }[] = [];

  for (const a of ordered) {
    if (a.status.includes("INSUFFICIENT") || a.status === "INSUFFICIENT_AXIS_DIVERSITY") {
      // Will handle in the next loop; skip now to compute eval squares first
      continue;
    }
    const rmse = a.rmse ?? 0;
    const barW = maxRmse > 0 ? (rmse / maxRmse) * barAreaW : 0;
    evalBarRects.push({ axis: a, x: chartLeft, y, w: Math.max(barW, 4) });
    y += barH + barGap;
  }

  const insufficientItems = ordered.filter(
    (a) => a.status.includes("INSUFFICIENT") || a.status === "INSUFFICIENT_AXIS_DIVERSITY"
  );

  if (axes.length === 0) {
    return (
      <figure style={{ width, height: svgH }} className="chart-figure">
        <figcaption
          className="chart-figure-title"
          style={{ paddingLeft: VALIDATION_MARGIN.left + labelW + 12 }}
        >
          Multi-Axis Validation
        </figcaption>
        <div
          className="chart-empty"
          style={{
            height: svgH - 28,
          }}
        >
          No axes
        </div>
      </figure>
    );
  }

  return (
    <figure style={{ width, height: svgH }} className="chart-figure">
      <figcaption
        className="chart-figure-title"
        style={{ paddingLeft: chartLeft }}
      >
        Multi-Axis Validation
      </figcaption>
      <svg
        viewBox={`0 0 ${width} ${svgH}`}
        role="img"
        aria-label="Multi-Axis Validation"
        className="chart-svg"
      >
        {/* Background grid line at 0 */}
        <line
          x1={chartLeft}
          y1={svgH - VALIDATION_MARGIN.bottom}
          x2={chartLeft}
          y2={VALIDATION_MARGIN.top}
          stroke={LINE}
          strokeWidth={1}
        />

        {/* Evaluated bars */}
        {evalBarRects.map(({ axis, x, y, w }) => {
          const color = barColor(axis.status);
          const rmse = axis.rmse ?? 0;
          return (
            <g key={axis.axis}>
              {/* Axis label */}
              <text
                x={chartLeft - 8}
                y={y + barH / 2 + 4}
                textAnchor="end"
                fill={TEXT}
                fontSize={11}
              >
                {axisShortName(axis.axis)}
              </text>

              {/* Bar */}
              <rect
                x={x}
                y={y}
                width={w}
                height={barH}
                rx={4}
                fill={color}
                opacity={0.85}
              />

              {/* RMSE value on bar */}
              <text
                x={x + Math.max(w, 4) + 6}
                y={y + barH / 2 + 4}
                fill={TEXT}
                fontSize={11}
              >
                RMSE {rmse.toFixed(3)}
              </text>

              {/* R² label */}
              {axis.r2 != null ? (
                <text
                  x={x + Math.max(w, 4) + 6}
                  y={y + barH / 2 + 4}
                  fill={TEXT}
                  fontSize={11}
                  dy={16}
                >
                  R² {axis.r2.toFixed(3)}
                </text>
              ) : null}

              {/* Sample count */}
              <text
                x={width - VALIDATION_MARGIN.right + 6}
                y={y + barH / 2 + 4}
                fill={MUTED}
                fontSize={11}
                textAnchor="start"
              >
                n={axis.sampleCount}
              </text>
            </g>
          );
        })}

        {/* Insufficient rows */}
        {(() => {
          let iy = evalRows > 0
            ? VALIDATION_MARGIN.top + evalRows * (barH + barGap) + 4
            : VALIDATION_MARGIN.top;
          return insufficientItems.map((axis) => {
            const rowY = iy;
            iy += insufficientH + 8;
            return (
              <g key={axis.axis}>
                <text
                  x={chartLeft - 8}
                  y={rowY + insufficientH / 2 + 4}
                  textAnchor="end"
                  fill={TEXT}
                  fontSize={11}
                >
                  {axisShortName(axis.axis)}
                </text>
                <text
                  x={chartLeft}
                  y={rowY + insufficientH / 2 + 4}
                  fill={AMBER}
                  fontSize={11}
                >
                  (insufficient data)
                </text>
                <text
                  x={width - VALIDATION_MARGIN.right + 6}
                  y={rowY + insufficientH / 2 + 4}
                  fill={MUTED}
                  fontSize={11}
                  textAnchor="start"
                >
                  n={axis.sampleCount}
                </text>
              </g>
            );
          });
        })()}
      </svg>
    </figure>
  );
}
