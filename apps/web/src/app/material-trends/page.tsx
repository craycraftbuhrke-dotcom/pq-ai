"use client";

import {
  BarChart3,
  FileText,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/lib/auth-context";

type BatchResult = {
  id: string;
  result_no: string;
  batch_no: string;
  material_code: string;
  material_name: string;
  characteristic_name: string;
  result_value: number;
  unit: string;
  tested_at: string;
  reliability_status: string;
  is_within_spec: boolean | null;
};

type MaterialTrendSummary = {
  total_batches: number;
  total_results: number;
  verified_results: number;
  failed_results: number;
  pass_spec_rate: number;
  recent_trend: "stable" | "improving" | "declining" | "insufficient_data";
  batch_list: Array<{
    batch_no: string;
    material_code: string;
    material_name: string;
    result_count: number;
    verified_count: number;
    failed_count: number;
    latest_tested_at: string;
  }>;
};

const RELIABILITY_COLORS: Record<string, string> = {
  VERIFIED: "var(--teal)",
  PASSED: "var(--teal)",
  FAILED: "var(--red)",
  UNVERIFIED: "var(--text-muted)",
  PENDING: "var(--text-muted)",
};

const TREND_LABELS: Record<string, string> = {
  stable: "稳定",
  improving: "改善中",
  declining: "下降中",
  insufficient_data: "数据不足",
};

const TREND_ICONS: Record<string, React.ReactNode> = {
  stable: <TrendingUp style={{ color: "var(--teal)" }} />,
  improving: <TrendingUp style={{ color: "var(--teal)" }} />,
  declining: <TrendingDown style={{ color: "var(--red)" }} />,
  insufficient_data: <BarChart3 style={{ color: "var(--text-muted)" }} />,
};

function getApiKeyFromCookie(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)pq_api_key=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function formatDate(raw: string): string {
  try {
    return new Date(raw).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return raw;
  }
}

function formatShortDate(raw: string): string {
  try {
    return new Date(raw).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
    });
  } catch {
    return raw;
  }
}

function reliabilityDot(status: string) {
  const color = RELIABILITY_COLORS[status] ?? "var(--text-muted)";
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: color,
        flexShrink: 0,
      }}
    />
  );
}

function reliabilityLabel(status: string) {
  const map: Record<string, string> = {
    VERIFIED: "已验证",
    FAILED: "失败",
    UNVERIFIED: "未验证",
    PENDING: "待验证",
    PASSED: "通过",
  };
  return map[status] ?? status;
}

/** Simplify the SVG scatter-plot into a few function helpers */
function ScatterChart({
  results,
  selectedChar,
  onSelectChar,
  characteristics,
}: {
  results: BatchResult[];
  selectedChar: string;
  onSelectChar: (c: string) => void;
  characteristics: string[];
}) {
  const filtered = results
    .filter((r) => r.characteristic_name === selectedChar)
    .sort((a, b) => new Date(a.tested_at).getTime() - new Date(b.tested_at).getTime());

  if (filtered.length === 0) {
    return (
      <div className="master-empty" style={{ minHeight: 200 }}>
        <BarChart3 /> 暂无该特性的检测数据
      </div>
    );
  }

  const values = filtered.map((r) => r.result_value);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;
  const pad = range * 0.15;

  const yMin = minVal - pad;
  const yMax = maxVal + pad;

  const timestamps = filtered.map((r) => new Date(r.tested_at).getTime());
  const tMin = Math.min(...timestamps);
  const tMax = Math.max(...timestamps);
  const tRange = tMax - tMin || 1;

  const W = 660;
  const H = 260;
  const PAD = { top: 20, right: 20, bottom: 36, left: 56 };
  const PW = W - PAD.left - PAD.right;
  const PH = H - PAD.top - PAD.bottom;

  const toX = (t: number) => PAD.left + ((t - tMin) / tRange) * PW;
  const toY = (v: number) => PAD.top + PH - ((v - yMin) / (yMax - yMin)) * PH;

  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const sd = Math.sqrt(values.reduce((s, v) => s + (v - mean) ** 2, 0) / (values.length - 1 || 1));

  const yTicks = 5;
  const yTickVals = Array.from({ length: yTicks }, (_, i) => yMin + ((yMax - yMin) / (yTicks - 1)) * i);
  const tTickCount = Math.min(6, filtered.length);
  const tTickVals =
    tTickCount > 1
      ? Array.from({ length: tTickCount }, (_, i) => {
          const idx = Math.round((i / (tTickCount - 1)) * (filtered.length - 1));
          return filtered[idx].tested_at;
        })
      : [filtered[0].tested_at];

  return (
    <div>
      <div style={{ padding: "8px 16px", display: "flex", alignItems: "center", gap: 8 }}>
        <span className="eyebrow">特性选择</span>
        <select
          style={{
            background: "var(--surface)",
            border: "1px solid var(--line)",
            borderRadius: 5,
            padding: "4px 8px",
            fontSize: 11,
            color: "var(--text)",
          }}
          value={selectedChar}
          onChange={(e) => onSelectChar(e.target.value)}
        >
          {characteristics.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <span style={{ marginLeft: "auto", color: "var(--text-muted)", fontSize: 10 }}>
          {filtered.length} 条记录 · 均值 {mean.toFixed(3)} · σ {sd.toFixed(3)}
        </span>
      </div>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        style={{ display: "block", width: "100%", maxWidth: W, height: "auto" }}
      >
        {/* grid lines */}
        {yTickVals.map((v) => {
          const y = toY(v);
          return (
            <g key={`y-${v}`}>
              <line x1={PAD.left} x2={W - PAD.right} y1={y} y2={y} stroke="var(--line)" strokeWidth={0.5} />
              <text x={PAD.left - 6} y={y + 3} textAnchor="end" fill="var(--text-muted)" fontSize={8}>
                {v.toFixed(2)}
              </text>
            </g>
          );
        })}

        {/* mean line */}
        <line
          x1={PAD.left}
          x2={W - PAD.right}
          y1={toY(mean)}
          y2={toY(mean)}
          stroke="var(--cyan)"
          strokeWidth={1}
          strokeDasharray="5 3"
        />
        <text x={W - PAD.right + 2} y={toY(mean) + 3} fill="var(--cyan)" fontSize={7}>
          μ
        </text>

        {/* +2σ line */}
        <line
          x1={PAD.left}
          x2={W - PAD.right}
          y1={toY(mean + 2 * sd)}
          y2={toY(mean + 2 * sd)}
          stroke="var(--amber)"
          strokeWidth={0.8}
          strokeDasharray="3 4"
        />
        {/* -2σ line */}
        <line
          x1={PAD.left}
          x2={W - PAD.right}
          y1={toY(mean - 2 * sd)}
          y2={toY(mean - 2 * sd)}
          stroke="var(--amber)"
          strokeWidth={0.8}
          strokeDasharray="3 4"
        />

        {/* x axis ticks */}
        {tTickVals.map((t, i) => {
          const x = toX(new Date(t).getTime());
          return (
            <text key={`t-${i}`} x={x} y={H - 4} textAnchor="middle" fill="var(--text-muted)" fontSize={8}>
              {formatShortDate(t)}
            </text>
          );
        })}

        {/* data points */}
        {filtered.map((r) => {
          const t = new Date(r.tested_at).getTime();
          const cx = toX(t);
          const cy = toY(r.result_value);
          const color = RELIABILITY_COLORS[r.reliability_status] ?? "var(--text-muted)";
          return (
            <g key={r.id}>
              <circle cx={cx} cy={cy} r={4} fill={color} opacity={0.85} />
              <title>
                {r.result_no} · {r.batch_no} · {r.result_value} {r.unit} · {reliabilityLabel(r.reliability_status)}
              </title>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function MaterialTrendsPage() {
  const { actor } = useAuth();
  const [results, setResults] = useState<BatchResult[]>([]);
  const [summary, setSummary] = useState<MaterialTrendSummary | null>(null);
  const [selectedBatch, setSelectedBatch] = useState<string | null>(null);
  const [selectedChar, setSelectedChar] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const apiKey = getApiKeyFromCookie();
      const [resResp, sumResp] = await Promise.all([
        fetch("/api/process/material-governance/results?limit=500", {
          cache: "no-store",
          headers: { "x-api-key": apiKey },
        }),
        fetch("/api/process/material-governance/summary", {
          cache: "no-store",
          headers: { "x-api-key": apiKey },
        }),
      ]);

      if (!resResp.ok || !sumResp.ok) {
        const detail = await (resResp.ok ? sumResp : resResp)
          .json()
          .catch(() => ({}));
        throw new Error((detail as { detail?: string }).detail ?? "加载失败");
      }

      const resData = (await resResp.json()) as BatchResult[];
      const sumData = (await sumResp.json()) as MaterialTrendSummary;

      setResults(resData || []);
      setSummary(sumData);
      setSelectedBatch(null);

      if (resData?.length) {
        const chars = [...new Set(resData.map((r) => r.characteristic_name))];
        setSelectedChar((prev) => (prev && chars.includes(prev) ? prev : chars[0] ?? ""));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void reload(); }, [reload]);

  const characteristics = useMemo(
    () => [...new Set(results.map((r) => r.characteristic_name))],
    [results],
  );

  const batchSummaries = useMemo(() => {
    const map = new Map<
      string,
      {
        batch_no: string;
        material_code: string;
        material_name: string;
        result_count: number;
        verified_count: number;
        failed_count: number;
        latest_tested_at: string;
      }
    >();
    for (const r of results) {
      const existing = map.get(r.batch_no);
      if (!existing) {
        map.set(r.batch_no, {
          batch_no: r.batch_no,
          material_code: r.material_code,
          material_name: r.material_name,
          result_count: 1,
          verified_count: r.reliability_status === "VERIFIED" ? 1 : 0,
          failed_count: r.reliability_status === "FAILED" ? 1 : 0,
          latest_tested_at: r.tested_at,
        });
      } else {
        existing.result_count++;
        if (r.reliability_status === "VERIFIED") existing.verified_count++;
        if (r.reliability_status === "FAILED") existing.failed_count++;
        if (r.tested_at > existing.latest_tested_at) existing.latest_tested_at = r.tested_at;
      }
    }
    return [...map.values()].sort(
      (a, b) => new Date(b.latest_tested_at).getTime() - new Date(a.latest_tested_at).getTime(),
    );
  }, [results]);

  const batchResults = useMemo(
    () => results.filter((r) => r.batch_no === selectedBatch),
    [results, selectedBatch],
  );

  const calculatedSummary = useMemo(() => {
    if (summary) return summary;
    const verified = results.filter((r) => r.reliability_status === "VERIFIED").length;
    const failed = results.filter((r) => r.reliability_status === "FAILED").length;
    const passed = results.filter((r) => r.is_within_spec === true).length;
    const total = results.length;
    return {
      total_batches: batchSummaries.length,
      total_results: total,
      verified_results: verified,
      failed_results: failed,
      pass_spec_rate: total ? Math.round((passed / total) * 10000) / 100 : 0,
      recent_trend: "insufficient_data" as const,
      batch_list: batchSummaries,
    };
  }, [summary, results, batchSummaries]);

  if (!actor.isAuthenticated) {
    return (
      <div className="page-stack">
        <div className="master-empty">
          <ShieldCheck /> 请先登录。
        </div>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">MATERIAL GOVERNANCE</span>
          <h1>材料批次质量趋势</h1>
          <p>追踪材料批次检测结果的可靠性与趋势变化。</p>
        </div>
        <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} /> 刷新
        </button>
      </header>

      {error ? (
        <button className="message-banner message-error" onClick={() => setError("")}>
          {error}
          <X />
        </button>
      ) : null}

      {loading ? (
        <div className="master-empty">
          <LoaderCircle className="spin" /> 正在加载材料批次数据...
        </div>
      ) : results.length === 0 && !error ? (
        <div className="master-empty">
          <FileText /> 暂无材料批次检测数据。
        </div>
      ) : (
        <>
          <section className="module-stat-strip">
            <article>
              <span>批次总数</span>
              <strong>{calculatedSummary.total_batches}</strong>
              <small>
                {TREND_ICONS[calculatedSummary.recent_trend]}
                {TREND_LABELS[calculatedSummary.recent_trend] ?? calculatedSummary.recent_trend}
              </small>
            </article>
            <article>
              <span>检测总数</span>
              <strong>{calculatedSummary.total_results}</strong>
              <small>全部检测结果</small>
            </article>
            <article>
              <span>已验证</span>
              <strong>{calculatedSummary.verified_results}</strong>
              <small>
                {calculatedSummary.total_results
                  ? ((calculatedSummary.verified_results / calculatedSummary.total_results) * 100).toFixed(1) + "%"
                  : "—"}
              </small>
            </article>
            <article>
              <span>失败 / 合格率</span>
              <strong>
                {calculatedSummary.failed_results} / {calculatedSummary.pass_spec_rate}%
              </strong>
              <small>可靠性问题</small>
            </article>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">BATCH LIST</span>
                <h2>批次检测汇总</h2>
              </div>
              <span className="mono" style={{ color: "var(--text-muted)", fontSize: 10 }}>
                {batchSummaries.length} 个批次
              </span>
            </div>
            <div className="master-table-wrap">
              <table className="master-table">
                <thead>
                  <tr>
                    <th>状态</th>
                    <th>批次号</th>
                    <th>物料代码</th>
                    <th>物料名称</th>
                    <th>检测数</th>
                    <th>已验证</th>
                    <th>失败</th>
                    <th>最近检测</th>
                  </tr>
                </thead>
                <tbody>
                  {batchSummaries.map((batch) => {
                    const relStatus =
                      batch.failed_count > 0
                        ? "FAILED"
                        : batch.verified_count >= batch.result_count
                          ? "VERIFIED"
                          : "UNVERIFIED";
                    return (
                      <tr
                        key={batch.batch_no}
                        onClick={() =>
                          setSelectedBatch((prev) => (prev === batch.batch_no ? null : batch.batch_no))
                        }
                        style={{
                          cursor: "pointer",
                          background:
                            selectedBatch === batch.batch_no ? "var(--surface)" : undefined,
                        }}
                      >
                        <td>{reliabilityDot(relStatus)}</td>
                        <td className="mono">{batch.batch_no}</td>
                        <td className="mono" style={{ color: "var(--text-muted)" }}>
                          {batch.material_code}
                        </td>
                        <td>{batch.material_name}</td>
                        <td>{batch.result_count}</td>
                        <td>
                          <span className="record-status status-on">{batch.verified_count}</span>
                        </td>
                        <td>
                          {batch.failed_count > 0 ? (
                            <span className="record-status status-off" style={{ color: "var(--red)" }}>
                              {batch.failed_count}
                            </span>
                          ) : (
                            <span className="record-status status-off">0</span>
                          )}
                        </td>
                        <td className="mono" style={{ fontSize: 9, color: "var(--text-muted)" }}>
                          {formatDate(batch.latest_tested_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">TREND CHART</span>
                <h2>检测值趋势</h2>
              </div>
            </div>
            <ScatterChart
              results={results}
              selectedChar={selectedChar}
              onSelectChar={setSelectedChar}
              characteristics={characteristics}
            />
          </section>

          {selectedBatch && batchResults.length > 0 ? (
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">BATCH DETAIL</span>
                  <h2>
                    批次 {selectedBatch} · {batchResults[0]?.material_name ?? "—"}
                  </h2>
                </div>
                <button
                  className="button button-secondary"
                  onClick={() => setSelectedBatch(null)}
                  style={{ fontSize: 9, padding: "4px 8px", minHeight: 26 }}
                >
                  <X /> 关闭
                </button>
              </div>
              <div className="master-table-wrap">
                <table className="master-table">
                  <thead>
                    <tr>
                      <th>结果编号</th>
                      <th>特性名称</th>
                      <th>检测值</th>
                      <th>单位</th>
                      <th>规格符合</th>
                      <th>可靠性</th>
                      <th>检测时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {batchResults.map((r) => (
                      <tr key={r.id}>
                        <td className="mono">{r.result_no}</td>
                        <td>{r.characteristic_name}</td>
                        <td className="mono">{r.result_value}</td>
                        <td style={{ color: "var(--text-muted)" }}>{r.unit}</td>
                        <td>
                          {r.is_within_spec === true ? (
                            <span className="record-status status-on">合格</span>
                          ) : r.is_within_spec === false ? (
                            <span className="record-status status-off" style={{ color: "var(--red)" }}>
                              不合格
                            </span>
                          ) : (
                            <span className="record-status status-off">—</span>
                          )}
                        </td>
                        <td>
                          <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                            {reliabilityDot(r.reliability_status)}
                            <span
                              className={`record-status ${
                                r.reliability_status === "VERIFIED"
                                  ? "status-on"
                                  : r.reliability_status === "FAILED"
                                    ? "status-off"
                                    : "status-off"
                              }`}
                              style={
                                r.reliability_status === "FAILED"
                                  ? { color: "var(--red)" }
                                  : undefined
                              }
                            >
                              {reliabilityLabel(r.reliability_status)}
                            </span>
                          </span>
                        </td>
                        <td className="mono" style={{ fontSize: 9, color: "var(--text-muted)" }}>
                          {formatDate(r.tested_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : selectedBatch ? (
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">BATCH DETAIL</span>
                  <h2>批次 {selectedBatch}</h2>
                </div>
                <button
                  className="button button-secondary"
                  onClick={() => setSelectedBatch(null)}
                  style={{ fontSize: 9, padding: "4px 8px", minHeight: 26 }}
                >
                  <X /> 关闭
                </button>
              </div>
              <div className="master-empty"><FileText /> 该批次暂无检测结果。</div>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
