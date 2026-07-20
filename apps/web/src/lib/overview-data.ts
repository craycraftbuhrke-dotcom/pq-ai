"use client";

import { useCallback, useEffect, useState } from "react";

async function fetchJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const resp = await fetch(path, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (!resp.ok) return fallback;
    return (await resp.json()) as T;
  } catch {
    return fallback;
  }
}

export type DashboardOverview = {
  healthScore: number;
  qualityPassRate: number;
  activeRuns: number;
  openRisks: number;
  pendingRecommendations: number;
  materialBatches: { total: number; verified: number; failSpec: number };
  calibrationAlerts: { expiring30d: number; expired: number };
  engineeringOpenTasks: number;
  aiModels: { approved: number; total: number; latestMetric: string | null };
  recentPredictions: { count24h: number; topRiskPoint: string | null };
  riskPoints: Array<{ code: string; name: string; metric: string; risk: number }>;
  recommendation: {
    id: string;
    status: string;
    predictedImprovement: number;
    pointCode: string;
  } | null;
  source: "api" | "fallback";
  error?: string;
};

export type ProcessOverview = {
  activeRuns: number;
  totalRuns: number;
  stages: Array<{ code: string; name: string; healthy: boolean; runCount: number }>;
  programVersionsActive: number;
  programVersionsDraft: number;
  openIssueTasks: number;
  recentRuns: Array<{ runNo: string; bodyNo: string | null; shift: string | null }>;
};

export type AiOverview = {
  modelsApproved: number;
  modelsTotal: number;
  latestModelMetric: string | null;
  predictions24h: number;
  topRiskPoint: string | null;
  recommendationsPending: number;
  recommendationsTotal: number;
  trialsActive: number;
  trialsCompleted: number;
  openChanges: number;
};

const EMPTY_DASHBOARD: DashboardOverview = {
  healthScore: 0,
  qualityPassRate: 0,
  activeRuns: 0,
  openRisks: 0,
  pendingRecommendations: 0,
  materialBatches: { total: 0, verified: 0, failSpec: 0 },
  calibrationAlerts: { expiring30d: 0, expired: 0 },
  engineeringOpenTasks: 0,
  aiModels: { approved: 0, total: 0, latestMetric: null },
  recentPredictions: { count24h: 0, topRiskPoint: null },
  riskPoints: [],
  recommendation: null,
  source: "fallback",
};

const EMPTY_PROCESS: ProcessOverview = {
  activeRuns: 0,
  totalRuns: 0,
  stages: [],
  programVersionsActive: 0,
  programVersionsDraft: 0,
  openIssueTasks: 0,
  recentRuns: [],
};

const EMPTY_AI: AiOverview = {
  modelsApproved: 0,
  modelsTotal: 0,
  latestModelMetric: null,
  predictions24h: 0,
  topRiskPoint: null,
  recommendationsPending: 0,
  recommendationsTotal: 0,
  trialsActive: 0,
  trialsCompleted: 0,
  openChanges: 0,
};

function mapDashboard(data: Record<string, unknown>): DashboardOverview {
  const mb = (data.material_batches ?? {}) as Record<string, unknown>;
  const ca = (data.calibration_alerts ?? {}) as Record<string, unknown>;
  const aim = (data.ai_models ?? {}) as Record<string, unknown>;
  const rp = (data.recent_predictions ?? {}) as Record<string, unknown>;
  const rec = (data.recommendation ?? {}) as Record<string, unknown>;
  const riskPts = (data.risk_points ?? []) as Array<Record<string, unknown>>;
  return {
    healthScore: Number(data.health_score ?? 0),
    qualityPassRate: Number(data.quality_pass_rate ?? 0),
    activeRuns: Number(data.active_runs ?? 0),
    openRisks: Number(data.open_risks ?? 0),
    pendingRecommendations: Number(data.pending_recommendations ?? 0),
    materialBatches: {
      total: Number(mb.total ?? 0),
      verified: Number(mb.verified ?? 0),
      failSpec: Number(mb.fail_spec ?? 0),
    },
    calibrationAlerts: {
      expiring30d: Number(ca.expiring_30d ?? 0),
      expired: Number(ca.expired ?? 0),
    },
    engineeringOpenTasks: Number(data.engineering_open_tasks ?? 0),
    aiModels: {
      approved: Number(aim.approved ?? 0),
      total: Number(aim.total ?? 0),
      latestMetric: (aim.latest_metric as string | null) ?? null,
    },
    recentPredictions: {
      count24h: Number(rp.count_24h ?? 0),
      topRiskPoint: (rp.top_risk_point as string | null) ?? null,
    },
    riskPoints: riskPts.map((p) => ({
      code: String(p.point_code ?? ""),
      name: String(p.point_name ?? ""),
      metric: String(p.metric ?? ""),
      risk: Number(p.risk ?? 0),
    })),
    recommendation: rec.id
      ? {
          id: String(rec.id),
          status: String(rec.status ?? ""),
          predictedImprovement: Number(rec.predicted_improvement ?? 0),
          pointCode: String(rec.point_code ?? ""),
        }
      : null,
    source: "api",
  };
}

function mapProcess(data: Record<string, unknown>): ProcessOverview {
  const stages = (data.stages ?? []) as Array<Record<string, unknown>>;
  const recent = (data.recent_runs ?? []) as Array<Record<string, unknown>>;
  return {
    activeRuns: Number(data.active_runs ?? 0),
    totalRuns: Number(data.total_runs ?? 0),
    stages: stages.map((s) => ({
      code: String(s.code ?? ""),
      name: String(s.name ?? ""),
      healthy: Boolean(s.healthy),
      runCount: Number(s.run_count ?? 0),
    })),
    programVersionsActive: Number(data.program_versions_active ?? 0),
    programVersionsDraft: Number(data.program_versions_draft ?? 0),
    openIssueTasks: Number(data.open_issue_tasks ?? 0),
    recentRuns: recent.map((r) => ({
      runNo: String(r.run_no ?? ""),
      bodyNo: (r.body_no as string | null) ?? null,
      shift: (r.shift as string | null) ?? null,
    })),
  };
}

function mapAi(data: Record<string, unknown>): AiOverview {
  return {
    modelsApproved: Number(data.models_approved ?? 0),
    modelsTotal: Number(data.models_total ?? 0),
    latestModelMetric: (data.latest_model_metric as string | null) ?? null,
    predictions24h: Number(data.predictions_24h ?? 0),
    topRiskPoint: (data.top_risk_point as string | null) ?? null,
    recommendationsPending: Number(data.recommendations_pending ?? 0),
    recommendationsTotal: Number(data.recommendations_total ?? 0),
    trialsActive: Number(data.trials_active ?? 0),
    trialsCompleted: Number(data.trials_completed ?? 0),
    openChanges: Number(data.open_changes ?? 0),
  };
}

export type OverviewData = {
  dashboard: DashboardOverview;
  process: ProcessOverview;
  ai: AiOverview;
  loading: boolean;
  refresh: () => void;
};

export function useOverviewData(): OverviewData {
  const [dashboard, setDashboard] = useState<DashboardOverview>(EMPTY_DASHBOARD);
  const [process, setProcess] = useState<ProcessOverview>(EMPTY_PROCESS);
  const [ai, setAi] = useState<AiOverview>(EMPTY_AI);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  const refresh = useCallback(() => setTick((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      const [d, p, a] = await Promise.all([
        fetchJson("/api/dashboard", EMPTY_DASHBOARD as unknown as Record<string, unknown>).then((d) =>
          mapDashboard(d as Record<string, unknown>),
        ),
        fetchJson("/api/process/overview-summary", {} as Record<string, unknown>).then((d) =>
          mapProcess(d as Record<string, unknown>),
        ),
        fetchJson("/api/ai/overview-summary", {} as Record<string, unknown>).then((d) =>
          mapAi(d as Record<string, unknown>),
        ),
      ]);
      if (cancelled) return;
      setDashboard(d);
      setProcess(p);
      setAi(a);
      setLoading(false);
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [tick]);

  return { dashboard, process, ai, loading, refresh };
}
