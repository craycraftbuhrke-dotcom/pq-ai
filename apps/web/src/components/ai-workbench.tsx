"use client";

import {
  Activity,
  BrainCircuit,
  Check,
  FlaskConical,
  LoaderCircle,
  Play,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type ModelVersion = {
  id: string;
  model_code: string;
  version: string;
  model_type: string;
  target_metric: string;
  feature_set_version: string;
  dataset_snapshot_id?: string | null;
  evaluation_metrics: Record<string, number>;
  training_sample_count: number;
  trained_at?: string | null;
  status: string;
};
type DatasetSnapshot = {
  id: string;
  dataset_code: string;
  version: string;
  target_metric: string;
  feature_set_version: string;
  split_strategy: string;
  group_key: string;
  status: string;
  sample_count: number;
  group_count: number;
  train_sample_count: number;
  validation_sample_count: number;
  train_group_count: number;
  validation_group_count: number;
  cutoff_at?: string | null;
  leakage_check: {
    passed: boolean;
    group_overlap_count: number;
    snapshot_overlap_count: number;
    temporal_order_valid: boolean;
  };
};
type AcceptanceDecision = {
  id: string;
  model_version_id: string;
  dataset_snapshot_id: string;
  decision: string;
  criteria: Record<string, number | null>;
  checks: Record<string, boolean>;
  decided_by: string;
  decided_at: string;
  comment?: string | null;
};
type Snapshot = {
  id: string;
  production_run_id: string;
  production_run_no: string;
  measurement_point_id: string;
  measurement_point_code: string;
  measurement_point_name: string;
  feature_set_version: string;
  feature_count: number;
  completeness_score: number;
};
type Prediction = {
  id: string;
  model_version_id: string;
  model_name: string;
  production_run_id: string;
  measurement_point_id: string;
  metric_code: string;
  predicted_value: number;
  lower_bound?: number | null;
  upper_bound?: number | null;
  confidence: number;
  predicted_at: string;
};
type PredictionResponse = Omit<Prediction, "id" | "model_name" | "predicted_at"> & {
  prediction_result_id?: string | null;
  feature_completeness: number;
};
type Factor = {
  feature: string;
  value: number;
  impact: number;
  direction: string;
  global_importance: number;
  basis: string;
};
type Diagnosis = {
  id: string;
  prediction_result_id?: string | null;
  metric_code: string;
  summary: string;
  factor_contributions: Factor[];
  confidence: number;
  causality_status: string;
  created_at: string;
};
type RecommendationAction = {
  id: string;
  process_stage: string;
  parameter_code: string;
  parameter_name: string;
  current_value: number;
  recommended_value: number;
  executed_value?: number | null;
  unit: string;
  hard_min?: number | null;
  hard_max?: number | null;
};
type Evaluation = {
  id: string;
  baseline_value: number;
  verified_value: number;
  actual_improvement: number;
  is_effective: boolean;
  verified_at: string;
  verified_by: string;
  conclusion?: string | null;
};
type Recommendation = {
  id: string;
  recommendation_no: string;
  production_run_id: string;
  measurement_point_id: string;
  target_metric: string;
  diagnosis_summary: string;
  predicted_improvement: number;
  confidence: number;
  status: string;
  model_version: string;
  constraints_checked: boolean;
  approved_by?: string | null;
  executed_by?: string | null;
  executed_at?: string | null;
  created_at: string;
  actions: RecommendationAction[];
  evaluation?: Evaluation | null;
};
type Measurement = {
  id: string;
  data_no: string;
  production_run_id: string;
  measurement_point_id: string;
  measured_at: string;
  metrics: { metric_code: string; raw_value: number; corrected_value?: number | null }[];
};
type MetricDefinition = { code: string; name: string; quality_type: string; is_primary: boolean };
type FeatureDrift = {
  feature: string;
  training_mean: number;
  recent_mean?: number | null;
  standardized_mean_shift?: number | null;
  missing_rate: number;
  sample_count: number;
  status: string;
};
type DriftReport = {
  model_version_id: string;
  model_code: string;
  version: string;
  target_metric: string;
  model_status: string;
  drift_status: string;
  recommendation: string;
  monitored_snapshot_count: number;
  prediction_count: number;
  labeled_prediction_count: number;
  average_feature_completeness?: number | null;
  average_confidence?: number | null;
  training_rmse?: number | null;
  validation_rmse?: number | null;
  baseline_rmse?: number | null;
  baseline_source: string;
  live_mae?: number | null;
  live_rmse?: number | null;
  rmse_ratio?: number | null;
  max_feature_shift?: number | null;
  window_started_at?: string | null;
  window_ended_at?: string | null;
  feature_drift: FeatureDrift[];
};
type Tab = "models" | "governance" | "predictions" | "recommendations";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  const payload = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new Error(payload.error ?? `请求失败（${response.status}）`);
  return payload;
}

function formatNumber(value?: number | null, digits = 3): string {
  return value === null || value === undefined ? "—" : value.toFixed(digits);
}

function statusLabel(status: string): string {
  return {
    ACTIVE: "生效",
    DRAFT: "草稿",
    RETIRED: "已退役",
    STABLE: "稳定",
    WATCH: "观察",
    DRIFT: "漂移",
    NO_DATA: "无数据",
    PENDING: "待审批",
    APPROVED: "已批准",
    REJECTED: "已驳回",
    EXECUTED: "已执行",
    VERIFIED: "已复测",
    ACCEPTED: "验收通过",
    BUILT: "已构建",
  }[status] ?? status;
}

function driftStatusClass(status: string): string {
  if (status === "STABLE") return "status-healthy";
  if (status === "WATCH") return "status-warning";
  if (status === "DRIFT") return "status-risk";
  return "status-info";
}

export function AiWorkbench() {
  const [tab, setTab] = useState<Tab>("models");
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [datasets, setDatasets] = useState<DatasetSnapshot[]>([]);
  const [acceptanceDecisions, setAcceptanceDecisions] = useState<AcceptanceDecision[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [diagnoses, setDiagnoses] = useState<Diagnosis[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [metrics, setMetrics] = useState<MetricDefinition[]>([]);
  const [driftReport, setDriftReport] = useState<DriftReport | null>(null);
  const [selectedModelId, setSelectedModelId] = useState("");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [selectedSnapshotId, setSelectedSnapshotId] = useState("");
  const [selectedPredictionId, setSelectedPredictionId] = useState("");
  const [selectedRecommendationId, setSelectedRecommendationId] = useState("");
  const [query, setQuery] = useState("");
  const [targetMin, setTargetMin] = useState("");
  const [targetMax, setTargetMax] = useState("");
  const [executedValues, setExecutedValues] = useState<Record<string, string>>({});
  const [verificationMeasurementId, setVerificationMeasurementId] = useState("");
  const [defaultModelCode] = useState(() => `PQ-MODEL-${Date.now().toString().slice(-6)}`);
  const [defaultDatasetCode] = useState(() => `PQ-DATASET-${Date.now().toString().slice(-6)}`);
  const [loading, setLoading] = useState(true);
  const [driftLoading, setDriftLoading] = useState(false);
  const [submitting, setSubmitting] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextModels, nextDatasets, nextAcceptanceDecisions, nextSnapshots, nextPredictions, nextDiagnoses, nextRecommendations, nextMeasurements, nextMetrics] =
        await Promise.all([
          request<ModelVersion[]>("/api/ai/models"),
          request<DatasetSnapshot[]>("/api/ai/models/datasets"),
          request<AcceptanceDecision[]>("/api/ai/models/acceptance-decisions"),
          request<Snapshot[]>("/api/ai/models/feature-snapshots"),
          request<Prediction[]>("/api/ai/predictions"),
          request<Diagnosis[]>("/api/ai/diagnoses"),
          request<Recommendation[]>("/api/ai/recommendations"),
          request<Measurement[]>("/api/quality/measurements?limit=500"),
          request<MetricDefinition[]>("/api/quality/metric-definitions"),
        ]);
      setModels(nextModels);
      setDatasets(nextDatasets);
      setAcceptanceDecisions(nextAcceptanceDecisions);
      setSnapshots(nextSnapshots);
      setPredictions(nextPredictions);
      setDiagnoses(nextDiagnoses);
      setRecommendations(nextRecommendations);
      setMeasurements(nextMeasurements);
      setMetrics(nextMetrics);
      setSelectedModelId((current) => current || nextModels[0]?.id || "");
      setSelectedDatasetId((current) => current || nextDatasets[0]?.id || "");
      setSelectedSnapshotId((current) => current || nextSnapshots[0]?.id || "");
      setSelectedPredictionId((current) => current || nextPredictions[0]?.id || "");
      setSelectedRecommendationId((current) => current || nextRecommendations[0]?.id || "");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "AI 工作台加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDrift = useCallback(async (modelId: string) => {
    setDriftLoading(true);
    try {
      setDriftReport(await request<DriftReport>(`/api/ai/models/${modelId}/drift`));
    } catch (loadError) {
      setDriftReport(null);
      setError(loadError instanceof Error ? loadError.message : "模型漂移报告加载失败");
    } finally {
      setDriftLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  useEffect(() => {
    if (!selectedModelId) return;
    const timer = window.setTimeout(() => void loadDrift(selectedModelId), 0);
    return () => window.clearTimeout(timer);
  }, [loadDrift, selectedModelId]);

  const selectedModel = models.find((item) => item.id === selectedModelId);
  const selectedDataset = datasets.find((item) => item.id === selectedDatasetId);
  const modelDataset = datasets.find((item) => item.id === selectedModel?.dataset_snapshot_id);
  const selectedAcceptance = acceptanceDecisions.find((item) => item.model_version_id === selectedModelId);
  const compatibleSnapshots = useMemo(
    () => snapshots.filter((item) => !selectedModel || item.feature_set_version === selectedModel.feature_set_version),
    [selectedModel, snapshots],
  );
  const selectedSnapshot = compatibleSnapshots.find((item) => item.id === selectedSnapshotId) ?? compatibleSnapshots[0];
  const selectedPrediction = predictions.find((item) => item.id === selectedPredictionId);
  const selectedDiagnosis = diagnoses.find((item) => item.prediction_result_id === selectedPredictionId);
  const selectedRecommendation = recommendations.find((item) => item.id === selectedRecommendationId);
  const verificationOptions = useMemo(() => {
    if (!selectedRecommendation) return [];
    return measurements.filter(
      (measurement) =>
        measurement.production_run_id === selectedRecommendation.production_run_id &&
        measurement.measurement_point_id === selectedRecommendation.measurement_point_id &&
        (!selectedRecommendation.executed_at ||
          new Date(measurement.measured_at) > new Date(selectedRecommendation.executed_at)) &&
        measurement.metrics.some((metric) => metric.metric_code === selectedRecommendation.target_metric),
    );
  }, [measurements, selectedRecommendation]);

  const filteredModels = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return models.filter((model) =>
      !normalized ||
      [model.model_code, model.version, model.target_metric, model.model_type, model.status].some((value) =>
        value.toLowerCase().includes(normalized),
      ),
    );
  }, [models, query]);
  const filteredPredictions = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return predictions.filter((prediction) =>
      !normalized ||
      [prediction.model_name, prediction.metric_code].some((value) => value.toLowerCase().includes(normalized)),
    );
  }, [predictions, query]);
  const filteredRecommendations = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return recommendations.filter((recommendation) =>
      !normalized ||
      [recommendation.recommendation_no, recommendation.target_metric, recommendation.status, recommendation.model_version]
        .some((value) => value.toLowerCase().includes(normalized)),
    );
  }, [query, recommendations]);

  function showSuccess(message: string) {
    setNotice(message);
    setError("");
  }

  function showError(operationError: unknown) {
    setError(operationError instanceof Error ? operationError.message : "操作失败");
    setNotice("");
  }

  function selectRecommendation(recommendationId: string) {
    setSelectedRecommendationId(recommendationId);
    setVerificationMeasurementId("");
  }

  async function trainModel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setSubmitting("train");
    try {
      await request<ModelVersion>("/api/ai/models/train", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_code: String(data.get("model_code")),
          version: String(data.get("version")),
          target_metric: String(data.get("target_metric")),
          feature_set_version: String(data.get("feature_set_version")),
          dataset_snapshot_id: String(data.get("dataset_snapshot_id")),
          min_samples: Number(data.get("min_samples")),
          ridge_lambda: Number(data.get("ridge_lambda")),
        }),
      });
      showSuccess("基础模型训练完成，已保存为待验收草稿版本");
      event.currentTarget.reset();
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function buildDataset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setSubmitting("dataset");
    try {
      const dataset = await request<DatasetSnapshot>("/api/ai/models/datasets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_code: String(data.get("dataset_code")),
          version: String(data.get("version")),
          target_metric: String(data.get("target_metric")),
          feature_set_version: String(data.get("feature_set_version")),
          holdout_ratio: Number(data.get("holdout_ratio")),
          min_train_groups: Number(data.get("min_train_groups")),
          min_validation_groups: Number(data.get("min_validation_groups")),
        }),
      });
      setSelectedDatasetId(dataset.id);
      showSuccess("数据集快照已固化，并通过分组与时间泄漏检查");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function decideModelAcceptance(decision: "ACCEPTED" | "REJECTED") {
    if (!selectedModel) return;
    setSubmitting(`acceptance-${decision}`);
    try {
      await request<AcceptanceDecision>(`/api/ai/models/${selectedModel.id}/acceptance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision,
          decided_by: "模型验收人",
          comment: decision === "ACCEPTED" ? "已复核独立验证指标与适用范围" : "独立验证或适用范围未满足上线要求",
        }),
      });
      showSuccess(decision === "ACCEPTED" ? "模型已通过验收，可以激活" : "模型已记录为验收驳回");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function runPrediction() {
    if (!selectedModel || !selectedSnapshot) return;
    setSubmitting("predict");
    try {
      const result = await request<PredictionResponse>(`/api/ai/models/${selectedModel.id}/predictions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          production_run_id: selectedSnapshot.production_run_id,
          measurement_point_id: selectedSnapshot.measurement_point_id,
          persist_result: true,
        }),
      });
      setTargetMin(String(Number((result.predicted_value + Math.max(0.5, Math.abs(result.predicted_value) * 0.02)).toFixed(3))));
      setTargetMax("");
      setSelectedPredictionId(result.prediction_result_id ?? "");
      showSuccess(`预测完成：${result.metric_code} = ${formatNumber(result.predicted_value)}`);
      await reload();
      setTab("predictions");
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function changeModelStatus(status: "ACTIVE" | "RETIRED" | "DRAFT") {
    if (!selectedModel) return;
    setSubmitting(`model-status-${status}`);
    try {
      await request<ModelVersion>(`/api/ai/models/${selectedModel.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      showSuccess(`模型已切换为“${statusLabel(status)}”状态`);
      await reload();
      await loadDrift(selectedModel.id);
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function runDiagnosis(predictionId: string) {
    setSubmitting(`diagnose-${predictionId}`);
    try {
      await request(`/api/ai/models/predictions/${predictionId}/diagnoses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      setSelectedPredictionId(predictionId);
      showSuccess("诊断完成，已生成局部特征贡献证据");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function generateRecommendation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedModel || !selectedSnapshot) return;
    setSubmitting("recommend");
    try {
      const result = await request<{ recommendation_id: string }>(`/api/ai/models/${selectedModel.id}/recommendations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          production_run_id: selectedSnapshot.production_run_id,
          measurement_point_id: selectedSnapshot.measurement_point_id,
          target_min: targetMin === "" ? null : Number(targetMin),
          target_max: targetMax === "" ? null : Number(targetMax),
          max_actions: 3,
          max_step_ratio: 0.1,
        }),
      });
      setSelectedRecommendationId(result.recommendation_id);
      showSuccess("已生成受硬边界约束的工艺参数推荐");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function approveRecommendation(recommendation: Recommendation, approved: boolean) {
    setSubmitting(`approval-${recommendation.id}`);
    try {
      await request(`/api/ai/recommendations/${recommendation.id}/approval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved, approved_by: "陈工", comment: approved ? "受控试验批准" : "人工评审驳回" }),
      });
      showSuccess(approved ? "推荐已批准，可填写实际执行值" : "推荐已驳回");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function executeRecommendation(recommendation: Recommendation) {
    setSubmitting(`execute-${recommendation.id}`);
    try {
      await request(`/api/ai/recommendations/${recommendation.id}/execution`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          executed_by: "机器人程序员",
          actions: recommendation.actions.map((action) => ({
            action_id: action.id,
            executed_value: Number(executedValues[action.id] ?? action.recommended_value),
          })),
        }),
      });
      showSuccess("实际执行值已记录，推荐进入待复测状态");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function verifyRecommendation(recommendation: Recommendation) {
    const measurementId = verificationMeasurementId || verificationOptions[0]?.id;
    if (!measurementId) {
      showError(new Error("当前生产事件和点位没有可用于复测的质量记录"));
      return;
    }
    setSubmitting(`verify-${recommendation.id}`);
    try {
      await request(`/api/ai/recommendations/${recommendation.id}/verification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          verified_measurement_id: measurementId,
          verified_by: "质量工程师",
          conclusion: "通过质量复测记录完成闭环效果评价",
        }),
      });
      showSuccess("复测评价完成，闭环结果已归档");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">Prediction · Diagnosis · Recommendation · Verification</span>
          <h1>AI 闭环工作台</h1>
          <p>基于真实点位特征快照训练模型，并完成预测、诊断、约束推荐、审批、执行与复测评价。</p>
        </div>
        <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} /> 刷新实时数据
        </button>
      </header>

      {error ? <button className="message-banner message-error" onClick={() => setError("")}>{error}<X /></button> : null}
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}

      <section className="module-stat-strip">
        <article><span>模型版本</span><strong>{models.length}</strong><small>{models.filter((model) => model.status === "ACTIVE").length} 个生效</small></article>
        <article><span>数据集 / 点位快照</span><strong>{datasets.length} / {snapshots.length}</strong><small>{datasets.filter((item) => item.leakage_check.passed).length} 个数据集通过泄漏检查</small></article>
        <article><span>预测 / 诊断</span><strong>{predictions.length} / {diagnoses.length}</strong><small>全部结果保存至 MySQL</small></article>
        <article><span>闭环推荐</span><strong>{recommendations.length}</strong><small>{recommendations.filter((item) => item.status === "VERIFIED").length} 条已完成复测</small></article>
      </section>

      <section className="panel ai-workspace">
        <div className="master-tabs">
          {([["models", "模型训练"], ["governance", "模型治理"], ["predictions", "预测与诊断"], ["recommendations", "推荐与闭环"]] as [Tab, string][]).map(([key, label]) => (
            <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>{label}</button>
          ))}
          <label className="master-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索当前工作区" /></label>
        </div>

        {tab === "models" ? (
          <div className="ai-split">
            <div className="ai-control-panel ai-governed-training">
              <form onSubmit={buildDataset}>
                <div className="program-subheading"><div><span className="eyebrow">Dataset Governance</span><h3>构建无泄漏数据集</h3></div><ShieldCheck /></div>
                <div className="ai-form-stack">
                  <label className="form-field"><span>数据集代码 <b>*</b></span><input name="dataset_code" required defaultValue={defaultDatasetCode} /></label>
                  <div className="ai-two-fields"><label className="form-field"><span>版本</span><input name="version" required defaultValue="1.0" /></label><label className="form-field"><span>时间留出比例</span><input name="holdout_ratio" type="number" min="0.1" max="0.5" step="0.05" defaultValue="0.25" /></label></div>
                  <label className="form-field"><span>目标质量指标</span><select name="target_metric" required>{metrics.filter((item) => item.is_primary).map((item) => <option key={`${item.quality_type}-${item.code}`} value={item.code}>{item.name} / {item.code}</option>)}</select></label>
                  <label className="form-field"><span>特征集版本</span><select name="feature_set_version">{Array.from(new Set(snapshots.map((item) => item.feature_set_version))).map((value) => <option key={value}>{value}</option>)}</select></label>
                  <div className="ai-two-fields"><label className="form-field"><span>最少训练分组</span><input name="min_train_groups" type="number" min="2" defaultValue="3" /></label><label className="form-field"><span>最少验证分组</span><input name="min_validation_groups" type="number" min="1" defaultValue="2" /></label></div>
                  <button className="button button-secondary" disabled={submitting === "dataset"}>{submitting === "dataset" ? <LoaderCircle className="spin" /> : <ShieldCheck />} 固化数据集快照</button>
                </div>
              </form>
              <form onSubmit={trainModel}>
                <div className="program-subheading"><div><span className="eyebrow">Training</span><h3>训练候选模型</h3></div><FlaskConical /></div>
                <div className="ai-form-stack">
                  <label className="form-field"><span>受治理数据集</span><select name="dataset_snapshot_id" required value={selectedDatasetId} onChange={(event) => setSelectedDatasetId(event.target.value)}>{datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.dataset_code}:{dataset.version} · {dataset.train_group_count}/{dataset.validation_group_count} 组</option>)}</select></label>
                  <input type="hidden" name="target_metric" value={selectedDataset?.target_metric ?? ""} />
                  <input type="hidden" name="feature_set_version" value={selectedDataset?.feature_set_version ?? ""} />
                  <label className="form-field"><span>模型代码 <b>*</b></span><input name="model_code" required defaultValue={defaultModelCode} /></label>
                  <label className="form-field"><span>版本 <b>*</b></span><input name="version" required defaultValue="1.0" /></label>
                  <div className="ai-context-box"><span>训练 / 验证样本</span><strong>{selectedDataset ? `${selectedDataset.train_sample_count} / ${selectedDataset.validation_sample_count}` : "—"}</strong><span>独立分组</span><strong>{selectedDataset ? `${selectedDataset.train_group_count} / ${selectedDataset.validation_group_count}` : "—"}</strong><span>泄漏检查</span><strong>{selectedDataset?.leakage_check.passed ? "通过" : "—"}</strong></div>
                  <div className="ai-two-fields"><label className="form-field"><span>最小训练样本</span><input name="min_samples" type="number" min="3" defaultValue="5" /></label><label className="form-field"><span>岭惩罚系数</span><input name="ridge_lambda" type="number" min="0" step="0.01" defaultValue="0.1" /></label></div>
                  <button className="button button-primary" disabled={!selectedDataset || submitting === "train"}>{submitting === "train" ? <LoaderCircle className="spin" /> : <BrainCircuit />} 训练候选版本</button>
                </div>
              </form>
            </div>
            <div className="ai-record-list">
              {filteredModels.map((model) => (
                <article className={`ai-model-card ${model.id === selectedModelId ? "selected" : ""}`} key={model.id} onClick={() => setSelectedModelId(model.id)}>
                  <div><span className={`record-status ${model.status === "ACTIVE" ? "status-on" : "status-off"}`}>{statusLabel(model.status)}</span><strong>{model.model_code}:{model.version}</strong><small>{model.model_type}</small></div>
                  <div className="ai-model-metrics"><span>目标 <b>{model.target_metric}</b></span><span>训练样本 <b>{model.training_sample_count}</b></span><span>验证 R² <b>{formatNumber(model.evaluation_metrics.validation_r2)}</b></span><span>验证 RMSE <b>{formatNumber(model.evaluation_metrics.validation_rmse)}</b></span></div>
                </article>
              ))}
              {!filteredModels.length ? <div className="master-empty"><BrainCircuit /> 暂无模型版本</div> : null}
            </div>
          </div>
        ) : null}

        {tab === "governance" ? (
          <div className="ai-split">
            <div className="ai-control-panel">
              <div className="program-subheading"><div><span className="eyebrow">Model Registry</span><h3>版本状态治理</h3></div><ShieldCheck /></div>
              <div className="ai-form-stack">
                <label className="form-field"><span>模型版本</span><select value={selectedModelId} onChange={(event) => setSelectedModelId(event.target.value)}>{models.map((model) => <option key={model.id} value={model.id}>{model.model_code}:{model.version} / {statusLabel(model.status)}</option>)}</select></label>
                <div className="ai-context-box"><span>目标指标</span><strong>{selectedModel?.target_metric ?? "—"}</strong><span>当前状态</span><strong>{statusLabel(selectedModel?.status ?? "—")}</strong><span>数据集</span><strong>{modelDataset ? `${modelDataset.dataset_code}:${modelDataset.version}` : "旧模型未绑定"}</strong><span>分组切分</span><strong>{modelDataset ? `${modelDataset.train_group_count} 训练 / ${modelDataset.validation_group_count} 验证` : "—"}</strong><span>验证 R² / RMSE</span><strong>{selectedModel ? `${formatNumber(selectedModel.evaluation_metrics.validation_r2)} / ${formatNumber(selectedModel.evaluation_metrics.validation_rmse)}` : "—"}</strong><span>验收结论</span><strong>{selectedAcceptance ? statusLabel(selectedAcceptance.decision) : "待验收"}</strong></div>
                <p className="ai-hint">模型必须先通过无泄漏独立验证和人工验收，才允许激活；激活后同模型代码与目标指标的其他版本会自动退役。</p>
                <div className="ai-two-fields">
                  <button className="button button-secondary danger-button" disabled={!selectedModel || submitting === "acceptance-REJECTED"} onClick={() => void decideModelAcceptance("REJECTED")}><X /> 验收驳回</button>
                  <button className="button button-secondary" disabled={!selectedModel || !modelDataset?.leakage_check.passed || submitting === "acceptance-ACCEPTED"} onClick={() => void decideModelAcceptance("ACCEPTED")}><ShieldCheck /> 验收通过</button>
                </div>
                <button className="button button-primary" disabled={!selectedModel || selectedModel.status === "ACTIVE" || selectedAcceptance?.decision !== "ACCEPTED" || submitting === "model-status-ACTIVE"} onClick={() => void changeModelStatus("ACTIVE")}>{submitting === "model-status-ACTIVE" ? <LoaderCircle className="spin" /> : <Check />} 激活版本</button>
                <div className="ai-two-fields">
                  <button className="button button-secondary" disabled={!selectedModel || selectedModel.status === "DRAFT" || submitting === "model-status-DRAFT"} onClick={() => void changeModelStatus("DRAFT")}>转为草稿</button>
                  <button className="button button-secondary danger-button" disabled={!selectedModel || selectedModel.status === "RETIRED" || submitting === "model-status-RETIRED"} onClick={() => void changeModelStatus("RETIRED")}>退役版本</button>
                </div>
              </div>
            </div>
            <div className="ai-record-list">
              {driftLoading ? <div className="master-empty"><LoaderCircle className="spin" /> 正在计算实时漂移报告</div> : null}
              {!driftLoading && driftReport ? <>
                <div className="ai-governance-summary">
                  <div>
                    <span className={`status-badge ${driftStatusClass(driftReport.drift_status)}`}>{statusLabel(driftReport.drift_status)}</span>
                    <strong>{driftReport.model_code}:{driftReport.version}</strong>
                    <small>{driftReport.target_metric} · 最近 {driftReport.monitored_snapshot_count} 个点位快照</small>
                  </div>
                  <button className="button button-secondary" onClick={() => void loadDrift(driftReport.model_version_id)}><RefreshCw /> 重新计算</button>
                </div>
                <div className="ai-drift-stat-grid">
                  <article><span>最大特征偏移</span><strong>{formatNumber(driftReport.max_feature_shift)}</strong><small>标准差倍数</small></article>
                  <article><span>在线 RMSE</span><strong>{formatNumber(driftReport.live_rmse)}</strong><small>验收基线 {formatNumber(driftReport.baseline_rmse)}</small></article>
                  <article><span>RMSE 比率</span><strong>{formatNumber(driftReport.rmse_ratio, 2)}</strong><small>在线 / 训练期</small></article>
                  <article><span>有标签预测</span><strong>{driftReport.labeled_prediction_count}</strong><small>共 {driftReport.prediction_count} 条预测</small></article>
                  <article><span>平均完整率</span><strong>{formatNumber((driftReport.average_feature_completeness ?? 0) * 100, 1)}%</strong><small>监控窗口输入</small></article>
                  <article><span>平均置信度</span><strong>{formatNumber((driftReport.average_confidence ?? 0) * 100, 1)}%</strong><small>在线预测结果</small></article>
                </div>
                <p className={`ai-drift-recommendation ${driftStatusClass(driftReport.drift_status)}`}>{driftReport.recommendation}</p>
                <div className="ai-drift-table">
                  <div className="ai-drift-row ai-drift-head"><span>特征</span><span>训练均值</span><span>近期均值</span><span>偏移</span><span>缺失率</span><span>状态</span></div>
                  {driftReport.feature_drift.map((feature) => <div className="ai-drift-row" key={feature.feature}><span><strong>{feature.feature}</strong><small>{feature.sample_count} 个有效样本</small></span><span>{formatNumber(feature.training_mean)}</span><span>{formatNumber(feature.recent_mean)}</span><span>{formatNumber(feature.standardized_mean_shift)}</span><span>{formatNumber(feature.missing_rate * 100, 1)}%</span><span><b className={`status-badge ${driftStatusClass(feature.status)}`}>{statusLabel(feature.status)}</b></span></div>)}
                </div>
              </> : null}
              {!driftLoading && !driftReport ? <div className="master-empty"><Activity /> 请选择模型版本查看治理报告</div> : null}
            </div>
          </div>
        ) : null}

        {tab === "predictions" ? (
          <div className="ai-split">
            <div className="ai-control-panel">
              <div className="program-subheading"><div><span className="eyebrow">Inference</span><h3>执行点位预测</h3></div><Target /></div>
              <div className="ai-form-stack">
                <label className="form-field"><span>生效模型</span><select value={selectedModelId} onChange={(event) => { setSelectedModelId(event.target.value); setSelectedSnapshotId(""); }}>{models.map((model) => <option key={model.id} value={model.id}>{model.model_code}:{model.version} / {model.target_metric}</option>)}</select></label>
                <label className="form-field"><span>生产事件与测量点快照</span><select value={selectedSnapshot?.id ?? ""} onChange={(event) => setSelectedSnapshotId(event.target.value)}>{compatibleSnapshots.map((snapshot) => <option key={snapshot.id} value={snapshot.id}>{snapshot.production_run_no} · {snapshot.measurement_point_code} · {formatNumber(snapshot.completeness_score * 100, 0)}%</option>)}</select></label>
                <div className="ai-context-box"><span>特征版本</span><strong>{selectedSnapshot?.feature_set_version ?? "—"}</strong><span>特征数量</span><strong>{selectedSnapshot?.feature_count ?? "—"}</strong></div>
                <button className="button button-primary" onClick={() => void runPrediction()} disabled={!selectedModel || selectedModel.status !== "ACTIVE" || !selectedSnapshot || submitting === "predict"}>{submitting === "predict" ? <LoaderCircle className="spin" /> : <Play />} 执行并保存预测</button>
              </div>
            </div>
            <div className="ai-record-list">
              {filteredPredictions.map((prediction) => {
                const diagnosis = diagnoses.find((item) => item.prediction_result_id === prediction.id);
                return <button className={`ai-result-card ${prediction.id === selectedPredictionId ? "selected" : ""}`} key={prediction.id} onClick={() => setSelectedPredictionId(prediction.id)}>
                  <div><strong>{prediction.metric_code} = {formatNumber(prediction.predicted_value)}</strong><span>{prediction.model_name}</span><small>{new Date(prediction.predicted_at).toLocaleString("zh-CN")}</small></div>
                  <div className="ai-result-numbers"><span>{formatNumber(prediction.lower_bound)} - {formatNumber(prediction.upper_bound)}</span><b>{formatNumber(prediction.confidence * 100, 1)}%</b></div>
                  <span className={`record-status ${diagnosis ? "status-on" : "status-off"}`}>{diagnosis ? "已诊断" : "待诊断"}</span>
                </button>;
              })}
              {!filteredPredictions.length ? <div className="master-empty"><Activity /> 暂无预测记录</div> : null}
              {selectedPrediction ? <div className="ai-evidence-panel">
                <div className="program-subheading"><div><span className="eyebrow">Explainability</span><h3>诊断证据</h3></div>{!selectedDiagnosis ? <button className="button button-primary" onClick={() => void runDiagnosis(selectedPrediction.id)} disabled={submitting === `diagnose-${selectedPrediction.id}`}>{submitting ? <LoaderCircle className="spin" /> : <Sparkles />} 生成诊断</button> : <span className="record-status status-on">{selectedDiagnosis.causality_status}</span>}</div>
                {selectedDiagnosis ? <><p className="ai-summary">{selectedDiagnosis.summary}</p><div className="ai-factor-list">{selectedDiagnosis.factor_contributions.map((factor) => <div key={factor.feature}><span><strong>{factor.feature}</strong><small>当前值 {formatNumber(factor.value)} · {factor.basis}</small></span><b className={factor.impact >= 0 ? "positive" : "negative"}>{factor.impact >= 0 ? "+" : ""}{formatNumber(factor.impact)}</b></div>)}</div></> : <div className="program-empty">选择“生成诊断”后保存局部特征贡献和相关性说明。</div>}
              </div> : null}
            </div>
          </div>
        ) : null}

        {tab === "recommendations" ? (
          <div className="ai-split">
            <form className="ai-control-panel" onSubmit={generateRecommendation}>
              <div className="program-subheading"><div><span className="eyebrow">Constrained Optimization</span><h3>生成参数推荐</h3></div><ShieldCheck /></div>
              <div className="ai-form-stack">
                <label className="form-field"><span>模型</span><select value={selectedModelId} onChange={(event) => { setSelectedModelId(event.target.value); setSelectedSnapshotId(""); }}>{models.map((model) => <option key={model.id} value={model.id}>{model.model_code}:{model.version} / {model.target_metric}</option>)}</select></label>
                <label className="form-field"><span>点位特征快照</span><select value={selectedSnapshot?.id ?? ""} onChange={(event) => setSelectedSnapshotId(event.target.value)}>{compatibleSnapshots.map((snapshot) => <option key={snapshot.id} value={snapshot.id}>{snapshot.production_run_no} · {snapshot.measurement_point_code}</option>)}</select></label>
                <div className="ai-two-fields"><label className="form-field"><span>目标下限</span><input type="number" step="any" value={targetMin} onChange={(event) => setTargetMin(event.target.value)} /></label><label className="form-field"><span>目标上限</span><input type="number" step="any" value={targetMax} onChange={(event) => setTargetMax(event.target.value)} /></label></div>
                <p className="ai-hint">至少填写一个目标边界。推荐只使用已启用参数，并强制校验工艺硬边界。</p>
                <button className="button button-primary" disabled={!selectedModel || selectedModel.status !== "ACTIVE" || !selectedSnapshot || (!targetMin && !targetMax) || submitting === "recommend"}>{submitting === "recommend" ? <LoaderCircle className="spin" /> : <Sparkles />} 生成约束推荐</button>
              </div>
            </form>
            <div className="ai-record-list">
              <div className="ai-recommendation-grid">
                {filteredRecommendations.map((recommendation) => <button className={`ai-recommendation-card ${recommendation.id === selectedRecommendationId ? "selected" : ""}`} key={recommendation.id} onClick={() => selectRecommendation(recommendation.id)}><span className={`record-status ${["REJECTED"].includes(recommendation.status) ? "status-off" : "status-on"}`}>{statusLabel(recommendation.status)}</span><strong>{recommendation.recommendation_no}</strong><small>{recommendation.model_version} · {recommendation.target_metric}</small><b>{recommendation.predicted_improvement >= 0 ? "+" : ""}{formatNumber(recommendation.predicted_improvement)}</b></button>)}
              </div>
              {selectedRecommendation ? <div className="ai-evidence-panel">
                <div className="program-subheading"><div><span className="eyebrow">Closed Loop</span><h3>{selectedRecommendation.recommendation_no}</h3></div><span className="record-status status-on">{statusLabel(selectedRecommendation.status)}</span></div>
                <p className="ai-summary">{selectedRecommendation.diagnosis_summary}</p>
                <div className="ai-action-table">
                  <div className="ai-action-row ai-action-head"><span>参数</span><span>当前值</span><span>推荐值</span><span>实际执行值</span><span>硬边界</span></div>
                  {selectedRecommendation.actions.map((action) => <div className="ai-action-row" key={action.id}><span><strong>{action.parameter_name}</strong><small>{action.process_stage} · {action.parameter_code}</small></span><span>{formatNumber(action.current_value)} {action.unit}</span><span>{formatNumber(action.recommended_value)} {action.unit}</span><span>{selectedRecommendation.status === "APPROVED" ? <input type="number" step="any" value={executedValues[action.id] ?? ""} onChange={(event) => setExecutedValues((current) => ({ ...current, [action.id]: event.target.value }))} /> : `${formatNumber(action.executed_value)} ${action.unit}`}</span><span>{formatNumber(action.hard_min)} - {formatNumber(action.hard_max)}</span></div>)}
                </div>
                {selectedRecommendation.status === "PENDING" ? <div className="ai-workflow-actions"><button className="button button-secondary danger-button" onClick={() => void approveRecommendation(selectedRecommendation, false)}><X /> 驳回</button><button className="button button-primary" onClick={() => void approveRecommendation(selectedRecommendation, true)}><Check /> 批准受控试验</button></div> : null}
                {selectedRecommendation.status === "APPROVED" ? <div className="ai-workflow-actions"><button className="button button-primary" onClick={() => void executeRecommendation(selectedRecommendation)}><Play /> 记录实际执行</button></div> : null}
                {selectedRecommendation.status === "EXECUTED" ? <div className="ai-verification"><label className="form-field"><span>选择执行后的同生产事件、同点位复测记录</span><select value={verificationMeasurementId} onChange={(event) => setVerificationMeasurementId(event.target.value)}><option value="">请选择复测数据</option>{verificationOptions.map((measurement) => <option key={measurement.id} value={measurement.id}>{measurement.data_no} · {new Date(measurement.measured_at).toLocaleString("zh-CN")}</option>)}</select></label>{!verificationOptions.length ? <p className="ai-hint">请先在质量数据中心录入执行后的复测数据，或通过 QMS 集成事件写入。</p> : null}<button className="button button-primary" disabled={!verificationOptions.length} onClick={() => void verifyRecommendation(selectedRecommendation)}><ShieldCheck /> 完成复测评价</button></div> : null}
                {selectedRecommendation.evaluation ? <div className={`ai-evaluation ${selectedRecommendation.evaluation.is_effective ? "effective" : "ineffective"}`}><strong>{selectedRecommendation.evaluation.is_effective ? "闭环改善有效" : "闭环改善未达预期"}</strong><span>基准 {formatNumber(selectedRecommendation.evaluation.baseline_value)} → 复测 {formatNumber(selectedRecommendation.evaluation.verified_value)}，实际改善 {formatNumber(selectedRecommendation.evaluation.actual_improvement)}</span><small>{selectedRecommendation.evaluation.verified_by} · {selectedRecommendation.evaluation.conclusion}</small></div> : null}
              </div> : <div className="master-empty"><Sparkles /> 暂无推荐记录</div>}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
