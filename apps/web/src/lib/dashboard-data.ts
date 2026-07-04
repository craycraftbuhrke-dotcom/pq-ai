import {
  recommendationActions,
  riskPoints,
  stages,
  type ProcessStage,
  type RecommendationAction,
  type RiskPoint,
} from "@/lib/demo-data";
import { apiRequestHeaders } from "@/lib/auth-data";

export type DiagnosisFactor = {
  name: string;
  impact: number;
  direction: "negative" | "positive";
};

export type DashboardSnapshot = {
  source: "api" | "fallback";
  context: {
    factory: string;
    vehicleModel: string;
    color: string;
    shift: string;
    refreshedAt: string;
  };
  healthScore: number;
  qualityPassRate: number;
  activeRuns: number;
  openRisks: number;
  pendingRecommendations: number;
  stages: ProcessStage[];
  riskPoints: RiskPoint[];
  diagnosis: {
    pointCode: string;
    summary: string;
    confidence: number;
    factors: DiagnosisFactor[];
  };
  recommendation: {
    id: string;
    status: string;
    currentPrediction: number;
    expectedPrediction: number;
    predictedImprovement: number;
    actions: RecommendationAction[];
  };
};

type ApiDashboard = {
  context: {
    factory: string;
    vehicle_model: string;
    color: string;
    shift: string;
    refreshed_at: string;
  };
  health_score: number;
  quality_pass_rate: number;
  active_runs: number;
  open_risks: number;
  pending_recommendations: number;
  stages: ProcessStage[];
  risk_points: Array<{
    point_code: string;
    point_name: string;
    part: string;
    metric: string;
    prediction: number;
    prediction_unit?: string;
    standard: string;
    risk: number;
  }>;
  diagnosis: {
    point_code: string;
    summary: string;
    confidence: number;
    factors: DiagnosisFactor[];
  };
  recommendation: {
    id: string;
    status: string;
    current_prediction: number;
    expected_prediction: number;
    predicted_improvement: number;
    actions: Array<{
      stage: string;
      brush_no: string;
      parameter: string;
      current: number;
      recommended: number;
      unit: string;
    }>;
  };
};

export const fallbackDashboard: DashboardSnapshot = {
  source: "fallback",
  context: {
    factory: "M9 总装涂装工厂",
    vehicleModel: "MX11",
    color: "珍珠白",
    shift: "白班",
    refreshedAt: "2026-06-10T08:42:16-07:00",
  },
  healthScore: 92.4,
  qualityPassRate: 98.7,
  activeRuns: 126,
  openRisks: 7,
  pendingRecommendations: 3,
  stages,
  riskPoints,
  diagnosis: {
    pointCode: "P-ROOF-03",
    summary: "清漆二站成型空气偏高，且材料粘度接近上限，是 DOI 下降的主要相关因素。",
    confidence: 0.87,
    factors: [
      { name: "清漆二站外成型空气", impact: 0.34, direction: "negative" },
      { name: "清漆粘度", impact: 0.26, direction: "negative" },
      { name: "清漆二站喷涂流量", impact: 0.18, direction: "positive" },
    ],
  },
  recommendation: {
    id: "rec-20260609-003",
    status: "PENDING",
    currentPrediction: 78.2,
    expectedPrediction: 83.6,
    predictedImprovement: 5.4,
    actions: recommendationActions,
  },
};

function mapApiDashboard(data: ApiDashboard): DashboardSnapshot {
  return {
    source: "api",
    context: {
      factory: data.context.factory,
      vehicleModel: data.context.vehicle_model,
      color: data.context.color,
      shift: data.context.shift,
      refreshedAt: data.context.refreshed_at,
    },
    healthScore: data.health_score,
    qualityPassRate: data.quality_pass_rate,
    activeRuns: data.active_runs,
    openRisks: data.open_risks,
    pendingRecommendations: data.pending_recommendations,
    stages: data.stages,
    riskPoints: data.risk_points.map((point) => ({
      code: point.point_code,
      name: point.point_name,
      part: point.part,
      metric: point.metric,
      predicted: `${point.prediction}${point.prediction_unit ? ` ${point.prediction_unit}` : ""}`,
      standard: point.standard,
      risk: point.risk,
    })),
    diagnosis: {
      pointCode: data.diagnosis.point_code,
      summary: data.diagnosis.summary,
      confidence: data.diagnosis.confidence,
      factors: data.diagnosis.factors,
    },
    recommendation: {
      id: data.recommendation.id,
      status: data.recommendation.status,
      currentPrediction: data.recommendation.current_prediction,
      expectedPrediction: data.recommendation.expected_prediction,
      predictedImprovement: data.recommendation.predicted_improvement,
      actions: data.recommendation.actions.map((action) => ({
        stage: action.stage,
        brush: action.brush_no,
        parameter: action.parameter,
        current: String(action.current),
        recommended: String(action.recommended),
        unit: action.unit,
      })),
    },
  };
}

export async function getDashboardSnapshot(): Promise<DashboardSnapshot> {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    return fallbackDashboard;
  }

  try {
    const response = await fetch(`${apiUrl}/dashboard`, {
      cache: "no-store",
      headers: await apiRequestHeaders(),
      signal: AbortSignal.timeout(2500),
    });
    if (!response.ok) {
      return fallbackDashboard;
    }
    return mapApiDashboard((await response.json()) as ApiDashboard);
  } catch {
    return fallbackDashboard;
  }
}
