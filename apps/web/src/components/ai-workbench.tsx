"use client";

import {
  Activity,
  BrainCircuit,
  Check,
  FlaskConical,
  LoaderCircle,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { ValidationChart } from "@/components/validation-chart";
import { WorkspaceEmptyState } from "@/components/workspace-empty-state";
import { useAuth } from "@/lib/auth-context";
import { qualityTypeLabel } from "@/lib/display-labels";

const DEFAULT_FEATURE_SET_VERSION = "point-features-v4-material-governed";

type ModelVersion = {
  id: string;
  model_code: string;
  version: string;
  model_type: string;
  target_metric: string;
  feature_set_version: string;
  dataset_snapshot_id?: string | null;
  evaluation_metrics: ModelEvaluationMetrics;
  training_sample_count: number;
  trained_at?: string | null;
  status: string;
};
type ValidationAxisSummary = {
  status: string;
  fold_count?: number;
  evaluated_fold_count?: number;
  skipped_fold_count?: number;
  distinct_key_count?: number;
  validation_sample_count?: number;
  rmse?: number | null;
  mae?: number | null;
  r2?: number | null;
};
type MultiAxisValidation = {
  strategy: string;
  axes: Record<string, ValidationAxisSummary>;
  evaluated_axis_count: number;
  insufficient_axis_count: number;
  worst_rmse?: number | null;
  worst_r2?: number | null;
};
type ModelEvaluationMetrics = {
  training_r2?: number;
  training_rmse?: number;
  validation_r2?: number;
  validation_rmse?: number;
  multi_axis_validation?: MultiAxisValidation;
  [key: string]: number | boolean | MultiAxisValidation | undefined | null;
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
  feature_names: string[];
  leakage_check: {
    passed: boolean;
    group_overlap_count: number;
    snapshot_overlap_count: number;
    temporal_order_valid: boolean;
  };
};
type DatasetMember = {
  id: string;
  dataset_snapshot_id: string;
  point_feature_snapshot_id: string;
  production_run_id: string;
  measurement_point_id: string;
  target_measurement_id: string;
  group_value: string;
  split: string;
  target_value: number;
  feature_values: Record<string, number>;
  occurred_at: string;
};
type AcceptanceDecision = {
  id: string;
  model_version_id: string;
  dataset_snapshot_id: string;
  decision: string;
  criteria: Record<string, unknown>;
  checks: Record<string, boolean>;
  decided_by: string;
  decided_at: string;
  comment?: string | null;
};
type AcceptancePolicy = {
  id: string;
  policy_code: string;
  version: string;
  factory_id: string;
  factory_code: string;
  factory_name: string;
  target_metric: string;
  policy_type: string;
  max_validation_rmse: number;
  min_validation_r2: number;
  min_train_groups: number;
  min_validation_groups: number;
  status: string;
  source_uri: string;
  approved_by?: string | null;
  approved_at?: string | null;
  remark?: string | null;
};
type ModelValidationFold = {
  id: string;
  model_version_id: string;
  dataset_snapshot_id: string;
  validation_axis: string;
  fold_key: string;
  train_sample_count: number;
  validation_sample_count: number;
  train_group_count: number;
  validation_group_count: number;
  metrics: Record<string, number | string | null>;
  status: string;
  evaluated_at: string;
};
type ModelArtifact = {
  id: string;
  model_version_id: string;
  artifact_type: string;
  artifact_uri: string;
  storage_backend: string;
  payload_hash: string;
  metadata_payload: Record<string, unknown>;
  status: string;
  created_by: string;
  registered_at: string;
  remark?: string | null;
};
type Snapshot = {
  id: string;
  production_run_id: string;
  production_run_no: string;
  factory_id: string;
  factory_code: string;
  factory_name: string;
  vehicle_model_id: string;
  vehicle_model_code: string;
  vehicle_model_name: string;
  color_id: string;
  color_code: string;
  color_name: string;
  measurement_point_id: string;
  measurement_point_code: string;
  measurement_point_name: string;
  feature_set_version: string;
  target_family: string;
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
  applicability_status: string;
  ood_status: string;
  governance_evidence?: Record<string, unknown> | null;
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
  constraint_source_code?: string | null;
  constraint_source_version?: string | null;
  constraint_source_type?: string | null;
  constraint_source_uri?: string | null;
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
type ControlledTrial = {
  id: string;
  trial_no: string;
  recommendation_id: string;
  production_run_id: string;
  measurement_point_id: string;
  target_metric: string;
  hypothesis: string;
  evidence_type: string;
  expected_outcome: string;
  risk_assessment: string;
  rollback_plan: string;
  sustained_observation_plan: string;
  constraint_evidence: Record<string, unknown>;
  status: string;
  requested_by: string;
  requested_at: string;
  approved_by?: string | null;
  approved_at?: string | null;
  approval_comment?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  completion_summary?: string | null;
};
type RollbackExecution = {
  id: string;
  rollback_no: string;
  recommendation_id: string;
  controlled_trial_id: string;
  rollback_to_program_version_id?: string | null;
  rollback_reason: string;
  execution_note?: string | null;
  executed_by: string;
  executed_at: string;
  status: string;
  action_snapshot: { actions?: RecommendationAction[] };
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
  measurement_point_code: string;
  measurement_point_name: string;
  quality_type: string;
  reliability_status: string;
  is_valid: boolean;
  measured_at: string;
  metrics: { metric_code: string; raw_value: number; corrected_value?: number | null }[];
};
type MetricDefinition = { code: string; name: string; quality_type: string; is_primary: boolean };
type PointFeatureResult = {
  snapshot_id: string;
  production_run_id: string;
  measurement_point_id: string;
  feature_set_version: string;
  target_family: string;
  feature_values: Record<string, number>;
  quality_labels: Record<string, number>;
  completeness_score: number;
  stage_coverage: string[];
  contribution_count: number;
};
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
type ApplicabilityScope = {
  id: string;
  model_version_id: string;
  factory_id: string;
  factory_code: string;
  factory_name: string;
  vehicle_model_id: string;
  vehicle_model_code: string;
  vehicle_model_name: string;
  color_id: string;
  color_code: string;
  color_name: string;
  status: string;
  source: string;
  approved_by?: string | null;
  approved_at?: string | null;
  remark?: string | null;
};
type OodPolicy = {
  id: string;
  model_version_id: string;
  max_abs_standardized_shift: number;
  max_outlier_feature_ratio: number;
  min_feature_completeness: number;
  action: string;
  status: string;
  approved_by?: string | null;
  approved_at?: string | null;
  remark?: string | null;
  updated_at: string;
};
type GovernanceCheck = {
  model_version_id: string;
  production_run_id: string;
  measurement_point_id: string;
  allowed: boolean;
  applicability_status: string;
  ood_status: string;
  evidence: {
    scope_id?: string | null;
    policy_id?: string | null;
    feature_completeness: number;
    missing_features: string[];
    max_abs_standardized_shift?: number | null;
    outlier_feature_ratio: number;
    outlier_features: { feature: string; value: number; standardized_shift: number }[];
  };
};
type Tab = "models" | "governance" | "predictions" | "recommendations" | "comparison";

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
    PLANNED: "已计划",
    RUNNING: "试验中",
    INEFFECTIVE: "未达预期",
    ROLLED_BACK: "已回滚",
    ACCEPTED: "验收通过",
    BUILT: "已构建",
    IN_SCOPE: "适用范围内",
    OUT_OF_SCOPE: "适用范围外",
    IN_DISTRIBUTION: "分布内",
    OUT_OF_DISTRIBUTION: "分布外",
    POLICY_NOT_APPROVED: "策略未批准",
    INACTIVE: "已停用",
    EVALUATED: "已评估",
    INSUFFICIENT_AXIS_DIVERSITY: "多样性不足",
    INSUFFICIENT_TRAINING_SUPPORT: "训练支撑不足",
    NO_EVALUATED_FOLDS: "无有效折",
    FAILED: "失败",
    REGISTERED: "已登记",
    ASSOCIATION: "关联证据",
    RULE: "规则证据",
    SIMULATION: "仿真证据",
    DOE: "DOE 证据",
    CONTROLLED_CHANGE: "受控变更证据",
    FACTORY_PROCESS_STANDARD: "工厂工艺标准",
    DURR_DEVICE_LIMIT: "Dürr 设备极限",
    MATERIAL_TDS: "材料 TDS",
    ENGINEERING_TRIAL: "工程试验",
  }[status] ?? status;
}

function driftStatusClass(status: string): string {
  if (status === "STABLE") return "status-healthy";
  if (status === "WATCH") return "status-warning";
  if (status === "DRIFT") return "status-risk";
  return "status-info";
}

function validationStatusClass(status: string): string {
  if (status === "EVALUATED") return "status-healthy";
  if (status === "FAILED" || status === "NO_EVALUATED_FOLDS") return "status-risk";
  if (status.startsWith("INSUFFICIENT")) return "status-warning";
  return "status-info";
}

function shortHash(value?: string | null): string {
  if (!value) return "—";
  return value.length <= 20 ? value : `${value.slice(0, 12)}...${value.slice(-8)}`;
}

export function AiWorkbench() {
  const { actor } = useAuth();
  const actorName = actor.isAuthenticated ? actor.displayName : "";
  const canManageModels =
    actor.roles.includes("DATA_SCIENTIST") ||
    actor.roles.includes("ADMIN") ||
    actor.permissions.includes("*") ||
    actor.roles.includes("SYSTEM");
  const [tab, setTab] = useState<Tab>("predictions");
  const [showAdvancedTraining, setShowAdvancedTraining] = useState(false);
  const activeTab =
    !canManageModels && (tab === "models" || tab === "governance" || tab === "comparison")
      ? "predictions"
      : tab;
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [datasets, setDatasets] = useState<DatasetSnapshot[]>([]);
  const [acceptanceDecisions, setAcceptanceDecisions] = useState<AcceptanceDecision[]>([]);
  const [acceptancePolicies, setAcceptancePolicies] = useState<AcceptancePolicy[]>([]);
  const [applicabilityScopes, setApplicabilityScopes] = useState<ApplicabilityScope[]>([]);
  const [oodPolicies, setOodPolicies] = useState<OodPolicy[]>([]);
  const [validationFolds, setValidationFolds] = useState<ModelValidationFold[]>([]);
  const [modelArtifacts, setModelArtifacts] = useState<ModelArtifact[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [datasetMembers, setDatasetMembers] = useState<DatasetMember[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [diagnoses, setDiagnoses] = useState<Diagnosis[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [controlledTrials, setControlledTrials] = useState<ControlledTrial[]>([]);
  const [rollbackExecutions, setRollbackExecutions] = useState<RollbackExecution[]>([]);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [metrics, setMetrics] = useState<MetricDefinition[]>([]);
  const [driftReport, setDriftReport] = useState<DriftReport | null>(null);
  const [governanceCheck, setGovernanceCheck] = useState<GovernanceCheck | null>(null);
  const [selectedModelId, setSelectedModelId] = useState("");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [selectedSnapshotId, setSelectedSnapshotId] = useState("");
  const [selectedBuildMeasurementId, setSelectedBuildMeasurementId] = useState("");
  const [selectedPredictionId, setSelectedPredictionId] = useState("");
  const [selectedRecommendationId, setSelectedRecommendationId] = useState("");
  const [query, setQuery] = useState("");
  const [targetMin, setTargetMin] = useState("");
  const [targetMax, setTargetMax] = useState("");
  const [executedValues, setExecutedValues] = useState<Record<string, string>>({});
  const [verificationMeasurementId, setVerificationMeasurementId] = useState("");
  const [defaultModelCode] = useState(() => `PQ-MODEL-${Date.now().toString().slice(-6)}`);
  const [defaultDatasetCode] = useState(() => `PQ-DATASET-${Date.now().toString().slice(-6)}`);
  const [defaultPolicyCode] = useState(() => `FACTORY-POLICY-${Date.now().toString().slice(-6)}`);
  const [loading, setLoading] = useState(true);
  const [membersLoading, setMembersLoading] = useState(false);
  const [driftLoading, setDriftLoading] = useState(false);
  const [governanceLoading, setGovernanceLoading] = useState(false);
  const [submitting, setSubmitting] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextModels, nextDatasets, nextAcceptanceDecisions, nextAcceptancePolicies, nextApplicabilityScopes, nextOodPolicies, nextValidationFolds, nextModelArtifacts, nextSnapshots, nextPredictions, nextDiagnoses, nextRecommendations, nextControlledTrials, nextRollbacks, nextMeasurements, nextMetrics] =
        await Promise.all([
          request<ModelVersion[]>("/api/ai/models"),
          request<DatasetSnapshot[]>("/api/ai/models/datasets"),
          request<AcceptanceDecision[]>("/api/ai/models/acceptance-decisions"),
          request<AcceptancePolicy[]>("/api/ai/models/acceptance-policies"),
          request<ApplicabilityScope[]>("/api/ai/models/applicability-scopes"),
          request<OodPolicy[]>("/api/ai/models/ood-policies"),
          request<ModelValidationFold[]>("/api/ai/models/validation-folds"),
          request<ModelArtifact[]>("/api/ai/models/artifacts"),
          request<Snapshot[]>("/api/ai/models/feature-snapshots"),
          request<Prediction[]>("/api/ai/predictions"),
          request<Diagnosis[]>("/api/ai/diagnoses"),
          request<Recommendation[]>("/api/ai/recommendations"),
          request<ControlledTrial[]>("/api/ai/controlled-trials"),
          request<RollbackExecution[]>("/api/ai/rollback-executions"),
          request<Measurement[]>("/api/quality/measurements?limit=500"),
          request<MetricDefinition[]>("/api/quality/metric-definitions"),
        ]);
      setModels(nextModels);
      setDatasets(nextDatasets);
      setAcceptanceDecisions(nextAcceptanceDecisions);
      setAcceptancePolicies(nextAcceptancePolicies);
      setApplicabilityScopes(nextApplicabilityScopes);
      setOodPolicies(nextOodPolicies);
      setValidationFolds(nextValidationFolds);
      setModelArtifacts(nextModelArtifacts);
      setSnapshots(nextSnapshots);
      setPredictions(nextPredictions);
      setDiagnoses(nextDiagnoses);
      setRecommendations(nextRecommendations);
      setControlledTrials(nextControlledTrials);
      setRollbackExecutions(nextRollbacks);
      setMeasurements(nextMeasurements);
      setMetrics(nextMetrics);
      setSelectedModelId((current) => current || nextModels[0]?.id || "");
      setSelectedDatasetId((current) => current || nextDatasets[0]?.id || "");
      setSelectedSnapshotId((current) => current || nextSnapshots[0]?.id || "");
      setSelectedBuildMeasurementId((current) =>
        nextMeasurements.some((measurement) => measurement.id === current)
          ? current
          : nextMeasurements[0]?.id || "",
      );
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

  const loadDatasetMembers = useCallback(async (datasetId: string) => {
    if (!datasetId) {
      setDatasetMembers([]);
      return;
    }
    setMembersLoading(true);
    try {
      setDatasetMembers(
        await request<DatasetMember[]>(`/api/ai/models/datasets/${datasetId}/members`),
      );
    } catch (loadError) {
      setDatasetMembers([]);
      setError(loadError instanceof Error ? loadError.message : "训练矩阵样本加载失败");
    } finally {
      setMembersLoading(false);
    }
  }, []);

  const loadGovernanceCheck = useCallback(async (modelId: string, snapshot: Snapshot) => {
    setGovernanceLoading(true);
    try {
      setGovernanceCheck(await request<GovernanceCheck>(`/api/ai/models/${modelId}/governance-check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          production_run_id: snapshot.production_run_id,
          measurement_point_id: snapshot.measurement_point_id,
        }),
      }));
    } catch (loadError) {
      setGovernanceCheck(null);
      setError(loadError instanceof Error ? loadError.message : "模型适用范围检查失败");
    } finally {
      setGovernanceLoading(false);
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

  useEffect(() => {
    const timer = window.setTimeout(() => void loadDatasetMembers(selectedDatasetId), 0);
    return () => window.clearTimeout(timer);
  }, [loadDatasetMembers, selectedDatasetId]);

  const selectedModel = models.find((item) => item.id === selectedModelId);
  const selectedDataset = datasets.find((item) => item.id === selectedDatasetId);
  const modelDataset = datasets.find((item) => item.id === selectedModel?.dataset_snapshot_id);
  const featureSetVersions = useMemo(() => {
    const versions = Array.from(new Set(snapshots.map((item) => item.feature_set_version)));
    return versions.length ? versions : [DEFAULT_FEATURE_SET_VERSION];
  }, [snapshots]);
  const featureBuildMeasurements = measurements.filter(
    (measurement) =>
      measurement.is_valid &&
      ["ORANGE_PEEL", "COLOR_DIFFERENCE", "THICKNESS"].includes(measurement.quality_type),
  );
  const selectedBuildMeasurement =
    featureBuildMeasurements.find((item) => item.id === selectedBuildMeasurementId) ??
    featureBuildMeasurements[0];
  const selectedDatasetMembers = datasetMembers.filter(
    (member) => member.dataset_snapshot_id === selectedDatasetId,
  );
  const selectedAcceptance = acceptanceDecisions.find((item) => item.model_version_id === selectedModelId);
  const selectedAcceptancePolicies = acceptancePolicies.filter(
    (item) => !selectedModel || item.target_metric === selectedModel.target_metric,
  );
  const selectedScopes = applicabilityScopes.filter((item) => item.model_version_id === selectedModelId);
  const selectedApplicableScopes = selectedScopes.filter((scope) => scope.status !== "INACTIVE");
  const selectedOodPolicy = oodPolicies.find((item) => item.model_version_id === selectedModelId);
  const selectedValidationFolds = validationFolds.filter((item) => item.model_version_id === selectedModelId);
  const selectedArtifact = modelArtifacts.find(
    (item) => item.model_version_id === selectedModelId && item.status === "REGISTERED",
  );
  const selectedMultiAxis = selectedModel?.evaluation_metrics.multi_axis_validation;
  const selectedAxisEntries = selectedMultiAxis ? Object.entries(selectedMultiAxis.axes) : [];
  const hasValidationEvidence = Boolean(
    selectedMultiAxis?.evaluated_axis_count || selectedValidationFolds.some((item) => item.status === "EVALUATED"),
  );
  const hasArtifactEvidence = Boolean(selectedArtifact);
  const factoryOptions = useMemo(
    () => Array.from(
      new Map(
        snapshots.map((snapshot) => [
          snapshot.factory_id,
          {
            id: snapshot.factory_id,
            code: snapshot.factory_code,
            name: snapshot.factory_name,
          },
        ]),
      ).values(),
    ),
    [snapshots],
  );
  const factoryPolicyCoverage = selectedApplicableScopes.length > 0 && selectedApplicableScopes.every(
    (scope) => selectedAcceptancePolicies.some(
      (policy) =>
        policy.factory_id === scope.factory_id &&
        policy.status === "ACTIVE" &&
        policy.policy_type === "FACTORY_APPROVED",
    ),
  );
  const selectedModelFeatureSetVersion = selectedModel?.feature_set_version;
  const compatibleSnapshots = snapshots.filter(
    (item) => !selectedModelFeatureSetVersion || item.feature_set_version === selectedModelFeatureSetVersion,
  );
  const selectedSnapshot = compatibleSnapshots.find((item) => item.id === selectedSnapshotId) ?? compatibleSnapshots[0];
  const governanceAllowed = Boolean(
    governanceCheck?.allowed &&
    governanceCheck.model_version_id === selectedModelId &&
    governanceCheck.production_run_id === selectedSnapshot?.production_run_id &&
    governanceCheck.measurement_point_id === selectedSnapshot?.measurement_point_id,
  );
  const selectedPrediction = predictions.find((item) => item.id === selectedPredictionId);
  const selectedDiagnosis = diagnoses.find((item) => item.prediction_result_id === selectedPredictionId);
  const selectedRecommendation = recommendations.find((item) => item.id === selectedRecommendationId);
  const selectedTrial = controlledTrials.find((item) => item.recommendation_id === selectedRecommendationId);
  const selectedTrialApproved = selectedTrial?.status === "APPROVED";
  const selectedRollback = rollbackExecutions.find((item) => item.controlled_trial_id === selectedTrial?.id);
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

  useEffect(() => {
    if (!selectedModelId || !selectedSnapshot) return;
    const timer = window.setTimeout(
      () => void loadGovernanceCheck(selectedModelId, selectedSnapshot),
      0,
    );
    return () => window.clearTimeout(timer);
  }, [loadGovernanceCheck, selectedModelId, selectedSnapshot]);

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
          max_abs_standardized_shift: Number(data.get("max_abs_standardized_shift")),
          max_outlier_feature_ratio: Number(data.get("max_outlier_feature_ratio")),
          min_feature_completeness: Number(data.get("min_feature_completeness")),
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

  async function buildPointFeatureSnapshot(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedBuildMeasurement) {
      showError(new Error("请先维护至少一条有效质量测量记录"));
      return;
    }
    const data = new FormData(event.currentTarget);
    setSubmitting("feature-snapshot");
    try {
      const result = await request<PointFeatureResult>("/api/features/point-snapshots/build", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          production_run_id: selectedBuildMeasurement.production_run_id,
          measurement_point_id: selectedBuildMeasurement.measurement_point_id,
          target_family: selectedBuildMeasurement.quality_type,
          feature_set_version: String(data.get("feature_set_version") || DEFAULT_FEATURE_SET_VERSION),
        }),
      });
      setSelectedSnapshotId(result.snapshot_id);
      showSuccess(
        `点位特征快照已生成：${result.stage_coverage.length}/5 工段，${Object.keys(result.feature_values).length} 个特征，${Object.keys(result.quality_labels).length} 个质量标签`,
      );
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

  async function createAcceptancePolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setSubmitting("acceptance-policy-create");
    try {
      await request<AcceptancePolicy>("/api/ai/models/acceptance-policies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          policy_code: String(data.get("policy_code")),
          version: String(data.get("version")),
          factory_id: String(data.get("factory_id")),
          target_metric: String(data.get("target_metric")),
          max_validation_rmse: Number(data.get("max_validation_rmse")),
          min_validation_r2: Number(data.get("min_validation_r2")),
          min_train_groups: Number(data.get("min_train_groups")),
          min_validation_groups: Number(data.get("min_validation_groups")),
          source_uri: String(data.get("source_uri")),
          remark: String(data.get("remark") || ""),
        }),
      });
      showSuccess("工厂模型验收策略草稿已创建，批准激活后才能用于模型验收");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function changeAcceptancePolicyStatus(policy: AcceptancePolicy, status: "ACTIVE" | "RETIRED") {
    setSubmitting(`acceptance-policy-${policy.id}-${status}`);
    try {
      await request<AcceptancePolicy>(`/api/ai/models/acceptance-policies/${policy.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status,
          approved_by: status === "ACTIVE" ? "工厂模型治理人" : null,
        }),
      });
      showSuccess(status === "ACTIVE" ? "工厂验收策略已批准激活" : "工厂验收策略已退役");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function updateOodPolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedModel) return;
    const data = new FormData(event.currentTarget);
    setSubmitting("ood-policy");
    try {
      await request<OodPolicy>(`/api/ai/models/${selectedModel.id}/ood-policy`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          max_abs_standardized_shift: Number(data.get("max_abs_standardized_shift")),
          max_outlier_feature_ratio: Number(data.get("max_outlier_feature_ratio")),
          min_feature_completeness: Number(data.get("min_feature_completeness")),
          action: "BLOCK",
          remark: "由模型治理工作台更新，需重新人工验收后生效。",
        }),
      });
      showSuccess("异常输入拦截规则已更新为待验收，已生效模型会自动退役");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function deactivateScope(scope: ApplicabilityScope) {
    if (!selectedModel) return;
    setSubmitting(`scope-${scope.id}`);
    try {
      await request(`/api/ai/models/${selectedModel.id}/applicability-scopes/${scope.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: "INACTIVE",
          remark: "由模型治理工作台停用。",
        }),
      });
      showSuccess("模型适用范围已停用");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function addScopeFromSelectedSnapshot() {
    if (!selectedModel || !selectedSnapshot) return;
    setSubmitting("scope-add");
    try {
      await request(`/api/ai/models/${selectedModel.id}/applicability-scopes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          factory_id: selectedSnapshot.factory_id,
          vehicle_model_id: selectedSnapshot.vehicle_model_id,
          color_id: selectedSnapshot.color_id,
          remark: "由模型治理工作台基于现有生产快照申请扩展，需重新人工验收。",
        }),
      });
      showSuccess("新适用范围已加入待验收清单，验收前不会授权推理");
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

  async function createControlledTrial(recommendation: Recommendation) {
    setSubmitting(`trial-create-${recommendation.id}`);
    try {
      await request<ControlledTrial>(`/api/ai/recommendations/${recommendation.id}/controlled-trial`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          hypothesis: `${recommendation.diagnosis_summary} 执行受约束推荐后，${recommendation.target_metric} 应沿预测改善方向变化。`,
          evidence_type: "ASSOCIATION",
          expected_outcome: `目标指标改善方向与模型预测一致，预期改善 ${formatNumber(recommendation.predicted_improvement)}。`,
          risk_assessment: "单次调整值保持在参数硬边界内；执行后必须由质量工程师复测确认。",
          rollback_plan: "若复测未改善或出现副作用，恢复推荐前刷子/程序参数版本并记录原因。",
          sustained_observation_plan: "至少跟踪后续 3 台同车型同色同点位质量结果，确认改善稳定。",
          requested_by: actorName,
        }),
      });
      showSuccess("受控试验计划已创建，需工艺负责人批准后才能批准推荐");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function approveControlledTrial(trial: ControlledTrial, approved: boolean) {
    setSubmitting(`trial-approval-${trial.id}`);
    try {
      await request<ControlledTrial>(`/api/ai/controlled-trials/${trial.id}/approval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approved,
          approved_by: actorName,
          comment: approved ? "假设、风险和回滚方案完整，同意进入推荐审批。" : "试验方案不满足现场执行要求。",
        }),
      });
      showSuccess(approved ? "受控试验计划已批准，可以批准推荐" : "受控试验计划已驳回");
      await reload();
    } catch (operationError) {
      showError(operationError);
    } finally {
      setSubmitting("");
    }
  }

  async function recordRollback(trial: ControlledTrial) {
    setSubmitting(`rollback-${trial.id}`);
    try {
      await request<RollbackExecution>(`/api/ai/controlled-trials/${trial.id}/rollback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rollback_reason: trial.completion_summary ?? "复测未达预期，按受控试验回滚方案执行。",
          executed_by: actorName,
          execution_note: trial.rollback_plan,
        }),
      });
      showSuccess("回滚执行已记录，推荐动作快照已归档");
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
        body: JSON.stringify({ approved, approved_by: actorName, comment: approved ? "受控试验批准" : "人工评审驳回" }),
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

  if (!actor.isAuthenticated) {
    return (
      <div className="page-stack">
        <WorkspaceEmptyState
          icon={ShieldCheck}
          title="请先登录后进入 AI 闭环工作台"
          description="模型治理、预测诊断、推荐审批与复测闭环都属于高风险业务能力，需要登录后再继续。"
        />
      </div>
    );
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">智能分析与推荐</span>
          <h1>智能分析与推荐</h1>
          <p>
            {canManageModels
              ? "现场可直接查看预测、诊断与参数推荐；模型训练与验收仅对数据分析人员开放。"
              : "根据当前车身与测量点，查看质量预测、原因提示，并按目标质量获取工艺参数推荐。"}
          </p>
        </div>
        <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} /> 刷新
        </button>
      </header>

      {error ? <button className="message-banner message-error" onClick={() => setError("")}>{error}<X /></button> : null}
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}

      <section className="module-stat-strip">
        <article><span>可用模型</span><strong>{models.filter((model) => model.status === "ACTIVE").length}</strong><small>共 {models.length} 个版本</small></article>
        <article><span>预测 / 诊断</span><strong>{predictions.length} / {diagnoses.length}</strong><small>结果已保存</small></article>
        <article><span>参数推荐</span><strong>{recommendations.length}</strong><small>{recommendations.filter((item) => item.status === "VERIFIED").length} 条已复测</small></article>
        <article><span>受控试验</span><strong>{controlledTrials.length}</strong><small>可在「受控试验」菜单继续跟进</small></article>
      </section>

      <section className="panel ai-workspace">
        <div className="master-tabs">
          {(
            (
              canManageModels
                ? ([
                    ["predictions", "预测与诊断"],
                    ["recommendations", "推荐与试验"],
                    ["models", "准备训练数据"],
                    ["governance", "模型验收"],
                    ["comparison", "模型对比"],
                  ] as [Tab, string][])
                : ([
                    ["predictions", "预测与诊断"],
                    ["recommendations", "推荐与试验"],
                  ] as [Tab, string][])
            )
          ).map(([key, label]) => (
            <button key={key} className={activeTab === key ? "active" : ""} onClick={() => setTab(key)}>{label}</button>
          ))}
          <label className="master-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索当前列表" /></label>
        </div>

        {activeTab === "models" && canManageModels ? (
          <div className="ai-split">
            <div className="ai-control-panel ai-governed-training">
              <form onSubmit={buildPointFeatureSnapshot}>
                <div className="program-subheading"><div><span className="eyebrow">第 1 步</span><h3>从质量记录生成训练样本</h3></div><Activity /></div>
                <div className="ai-form-stack">
                  <label className="form-field">
                    <span>选择一条已验证的质量测量</span>
                    <select
                      value={selectedBuildMeasurement?.id ?? ""}
                      onChange={(event) => setSelectedBuildMeasurementId(event.target.value)}
                      disabled={!featureBuildMeasurements.length}
                    >
                      {featureBuildMeasurements.map((measurement) => (
                        <option key={measurement.id} value={measurement.id}>
                          {measurement.data_no} · {measurement.measurement_point_code} · {qualityTypeLabel(measurement.quality_type)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <input type="hidden" name="feature_set_version" value={featureSetVersions[0] ?? DEFAULT_FEATURE_SET_VERSION} />
                  <div className="ai-context-box"><span>车身/事件</span><strong>{selectedBuildMeasurement?.production_run_id.slice(0, 8) ?? "—"}</strong><span>测量点</span><strong>{selectedBuildMeasurement ? `${selectedBuildMeasurement.measurement_point_code} / ${selectedBuildMeasurement.measurement_point_name}` : "—"}</strong><span>质量类型</span><strong>{selectedBuildMeasurement ? qualityTypeLabel(selectedBuildMeasurement.quality_type) : "—"}</strong><span>数据可信度</span><strong>{selectedBuildMeasurement ? statusLabel(selectedBuildMeasurement.reliability_status) : "—"}</strong></div>
                  <p className="ai-hint">系统会把该车该点的五站喷涂参数、材料结果与质量结果汇总成一条训练样本。</p>
                  <button className="button button-secondary" disabled={!selectedBuildMeasurement || submitting === "feature-snapshot"}>{submitting === "feature-snapshot" ? <LoaderCircle className="spin" /> : <Activity />} 生成训练样本</button>
                </div>
              </form>
              <form onSubmit={buildDataset}>
                <div className="program-subheading"><div><span className="eyebrow">第 2 步</span><h3>汇总历史样本并划分训练/验证</h3></div><ShieldCheck /></div>
                <div className="ai-form-stack">
                  <label className="form-field"><span>数据集名称 <b>*</b></span><input name="dataset_code" required defaultValue={defaultDatasetCode} /></label>
                  <div className="ai-two-fields"><label className="form-field"><span>版本</span><input name="version" required defaultValue="1.0" /></label><label className="form-field"><span>留给验证的比例</span><input name="holdout_ratio" type="number" min="0.1" max="0.5" step="0.05" defaultValue="0.25" title="用最近一部分车身做验证，避免把同一台车既拿来训练又拿来考试" /></label></div>
                  <label className="form-field"><span>要预测的质量指标</span><select name="target_metric" required>{metrics.filter((item) => item.is_primary).map((item) => <option key={`${item.quality_type}-${item.code}`} value={item.code}>{item.name}</option>)}</select></label>
                  <input type="hidden" name="feature_set_version" value={featureSetVersions[0] ?? DEFAULT_FEATURE_SET_VERSION} />
                  <details className="ai-advanced-details">
                    <summary>高级选项（一般不用改）</summary>
                    <div className="ai-two-fields"><label className="form-field"><span>最少训练车身组数</span><input name="min_train_groups" type="number" min="2" defaultValue="3" /></label><label className="form-field"><span>最少验证车身组数</span><input name="min_validation_groups" type="number" min="1" defaultValue="2" /></label></div>
                  </details>
                  <button className="button button-secondary" disabled={submitting === "dataset"}>{submitting === "dataset" ? <LoaderCircle className="spin" /> : <ShieldCheck />} 生成训练集</button>
                </div>
              </form>
              <form onSubmit={trainModel}>
                <div className="program-subheading"><div><span className="eyebrow">第 3 步</span><h3>训练模型</h3></div><FlaskConical /></div>
                <div className="ai-form-stack">
                  <label className="form-field"><span>选择训练集</span><select name="dataset_snapshot_id" required value={selectedDatasetId} onChange={(event) => setSelectedDatasetId(event.target.value)}>{datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.dataset_code}:{dataset.version} · 训练{dataset.train_group_count}/验证{dataset.validation_group_count} 组</option>)}</select></label>
                  <input type="hidden" name="target_metric" value={selectedDataset?.target_metric ?? ""} />
                  <input type="hidden" name="feature_set_version" value={selectedDataset?.feature_set_version ?? ""} />
                  <label className="form-field"><span>模型名称 <b>*</b></span><input name="model_code" required defaultValue={defaultModelCode} /></label>
                  <label className="form-field"><span>版本 <b>*</b></span><input name="version" required defaultValue="1.0" /></label>
                  <div className="ai-context-box"><span>训练 / 验证样本</span><strong>{selectedDataset ? `${selectedDataset.train_sample_count} / ${selectedDataset.validation_sample_count}` : "—"}</strong><span>车身分组</span><strong>{selectedDataset ? `${selectedDataset.train_group_count} / ${selectedDataset.validation_group_count}` : "—"}</strong><span>数据检查</span><strong>{selectedDataset?.leakage_check.passed ? "通过" : "—"}</strong></div>
                  <button type="button" className="button button-secondary" onClick={() => setShowAdvancedTraining((value) => !value)}>{showAdvancedTraining ? "收起高级参数" : "显示高级参数"}</button>
                  {showAdvancedTraining ? (
                    <>
                      <div className="ai-two-fields"><label className="form-field"><span>最少样本数</span><input name="min_samples" type="number" min="3" defaultValue="5" /></label><label className="form-field"><span>模型平滑强度</span><input name="ridge_lambda" type="number" min="0" step="0.01" defaultValue="0.1" title="数值越大，模型越保守" /></label></div>
                      <div className="ai-two-fields"><label className="form-field"><span>允许偏离训练均值的最大倍数</span><input name="max_abs_standardized_shift" type="number" min="0.1" step="0.1" defaultValue="4" /></label><label className="form-field"><span>允许异常参数占比</span><input name="max_outlier_feature_ratio" type="number" min="0" max="1" step="0.05" defaultValue="0.2" /></label></div>
                      <label className="form-field"><span>参数完整率下限</span><input name="min_feature_completeness" type="number" min="0.1" max="1" step="0.05" defaultValue="1" /></label>
                      <p className="ai-hint">这些阈值只控制“输入是否太离谱就拒绝预测”，不能替代设备、材料或工艺安全边界。训练后仍需人工验收。</p>
                    </>
                  ) : (
                    <>
                      <input type="hidden" name="min_samples" value="5" />
                      <input type="hidden" name="ridge_lambda" value="0.1" />
                      <input type="hidden" name="max_abs_standardized_shift" value="4" />
                      <input type="hidden" name="max_outlier_feature_ratio" value="0.2" />
                      <input type="hidden" name="min_feature_completeness" value="1" />
                    </>
                  )}
                  <button className="button button-primary" disabled={!selectedDataset || submitting === "train"}>{submitting === "train" ? <LoaderCircle className="spin" /> : <BrainCircuit />} 开始训练</button>
                </div>
              </form>
            </div>
            <div className="ai-record-list">
              <article className="ai-model-card">
                <div><span className="record-status status-on">训练矩阵</span><strong>{selectedDataset ? `${selectedDataset.dataset_code}:${selectedDataset.version}` : "未选择数据集"}</strong><small>{selectedDataset ? `${selectedDataset.sample_count} 行样本 · ${selectedDataset.feature_names.length} 个共同特征` : "先构建数据集快照"}</small></div>
                {selectedDataset ? (
                  <div className="compact-table">
                    <div className="production-actual-row compact-head"><span>分组</span><span>切分</span><span>目标值</span><span>特征数</span><span>时间</span></div>
                    {selectedDatasetMembers.slice(0, 6).map((member) => (
                      <div className="production-actual-row" key={member.id}>
                        <span><strong>{member.group_value}</strong><small>{member.measurement_point_id.slice(0, 8)} · {member.production_run_id.slice(0, 8)}</small></span>
                        <span>{member.split}</span>
                        <span>{formatNumber(member.target_value)}</span>
                        <span>{Object.keys(member.feature_values ?? {}).length}</span>
                        <span>{new Date(member.occurred_at).toLocaleString("zh-CN", { hour12: false })}</span>
                      </div>
                    ))}
                    {!selectedDatasetMembers.length ? <div className="program-empty">{membersLoading ? "训练矩阵样本加载中..." : "暂无矩阵成员，请重新构建数据集"}</div> : null}
                  </div>
                ) : null}
              </article>
              {filteredModels.map((model) => (
                <article className={`ai-model-card ${model.id === selectedModelId ? "selected" : ""}`} key={model.id} onClick={() => setSelectedModelId(model.id)}>
                  <div><span className={`record-status ${model.status === "ACTIVE" ? "status-on" : "status-off"}`}>{statusLabel(model.status)}</span><strong>{model.model_code}:{model.version}</strong><small>{model.model_type}</small></div>
                  <div className="ai-model-metrics"><span>目标 <b>{model.target_metric}</b></span><span>训练样本 <b>{model.training_sample_count}</b></span><span>验证 R² <b>{formatNumber(model.evaluation_metrics.validation_r2)}</b></span><span>验证 RMSE <b>{formatNumber(model.evaluation_metrics.validation_rmse)}</b></span></div>
                </article>
              ))}
              {!filteredModels.length ? (
                <WorkspaceEmptyState
                  icon={BrainCircuit}
                  title="暂无模型版本"
                  description="先完成点位特征快照和数据集治理，再训练候选模型，这里才会出现可管理的模型版本。"
                  compact
                />
              ) : null}
            </div>
          </div>
        ) : null}

        {activeTab === "governance" && canManageModels ? (
          <div className="ai-split">
            <div className="ai-control-panel">
              <div className="program-subheading"><div><span className="eyebrow">模型状态</span><h3>版本状态治理</h3></div><ShieldCheck /></div>
              <div className="ai-form-stack">
                <label className="form-field"><span>模型版本</span><select value={selectedModelId} onChange={(event) => setSelectedModelId(event.target.value)}>{models.map((model) => <option key={model.id} value={model.id}>{model.model_code}:{model.version} / {statusLabel(model.status)}</option>)}</select></label>
                <div className="ai-context-box"><span>目标指标</span><strong>{selectedModel?.target_metric ?? "—"}</strong><span>当前状态</span><strong>{statusLabel(selectedModel?.status ?? "—")}</strong><span>数据集</span><strong>{modelDataset ? `${modelDataset.dataset_code}:${modelDataset.version}` : "旧模型未绑定"}</strong><span>分组切分</span><strong>{modelDataset ? `${modelDataset.train_group_count} 训练 / ${modelDataset.validation_group_count} 验证` : "—"}</strong><span>验证拟合度 / 误差</span><strong>{selectedModel ? `${formatNumber(selectedModel.evaluation_metrics.validation_r2)} / ${formatNumber(selectedModel.evaluation_metrics.validation_rmse)}` : "—"}</strong><span>多维验证</span><strong>{selectedMultiAxis ? `${selectedMultiAxis.evaluated_axis_count}/${selectedAxisEntries.length} 轴` : "未生成"}</strong><span>模型校验码</span><strong>{shortHash(selectedArtifact?.payload_hash)}</strong><span>验收结论</span><strong>{selectedAcceptance ? statusLabel(selectedAcceptance.decision) : "待验收"}</strong><span>适用范围</span><strong>{selectedScopes.filter((item) => item.status === "ACTIVE").length} 生效 / {selectedScopes.length} 条</strong><span>异常输入拦截</span><strong>{selectedOodPolicy ? statusLabel(selectedOodPolicy.status) : "未配置"}</strong><span>工厂验收策略</span><strong>{factoryPolicyCoverage ? "全部覆盖" : "覆盖不完整"}</strong></div>
                <p className="ai-hint">模型必须通过独立验证，并确认工厂/车型/颜色适用范围与异常输入拦截规则后，才允许激活给现场使用。</p>
                <div className="ai-governance-block">
                  <strong>多维验证与模型工件</strong>
                  {selectedAxisEntries.length ? <div className="ai-validation-grid">
                    {selectedAxisEntries.map(([axis, summary]) => <article key={axis}><span className={`status-badge ${validationStatusClass(summary.status)}`}>{statusLabel(summary.status)}</span><strong>{axis}</strong><small>{summary.evaluated_fold_count ?? 0}/{summary.fold_count ?? 0} 折 · RMSE {formatNumber(summary.rmse)} · R² {formatNumber(summary.r2)}</small></article>)}
                  </div> : <p className="ai-hint">当前模型没有多维验证折报告，不能验收或激活。</p>}
                  {selectedArtifact ? <div className="ai-artifact-row"><span><b>{selectedArtifact.artifact_type}</b><small>{selectedArtifact.storage_backend} · {statusLabel(selectedArtifact.status)} · {shortHash(selectedArtifact.payload_hash)}</small></span><code>{selectedArtifact.artifact_uri}</code></div> : <p className="ai-hint">当前模型没有已登记工件哈希，不能验收或激活。</p>}
                </div>
                <div className="ai-governance-block">
                  <strong>工厂模型验收策略</strong>
                  {selectedAcceptancePolicies.map((policy) => <div className="ai-scope-row" key={policy.id}><span><b>{policy.factory_code} · {policy.policy_code}:{policy.version}</b><small>{policy.policy_type} · {statusLabel(policy.status)} · RMSE ≤ {formatNumber(policy.max_validation_rmse)} · R² ≥ {formatNumber(policy.min_validation_r2)}</small></span><div className="ai-inline-actions">{policy.status !== "ACTIVE" ? <button type="button" className="button button-secondary" disabled={submitting === `acceptance-policy-${policy.id}-ACTIVE`} onClick={() => void changeAcceptancePolicyStatus(policy, "ACTIVE")}>批准激活</button> : null}{policy.status === "ACTIVE" ? <button type="button" className="button button-secondary danger-button" disabled={submitting === `acceptance-policy-${policy.id}-RETIRED`} onClick={() => void changeAcceptancePolicyStatus(policy, "RETIRED")}>退役</button> : null}</div></div>)}
                  {!selectedAcceptancePolicies.length ? <p className="ai-hint">当前目标指标没有工厂验收策略，模型不能验收。</p> : null}
                </div>
                <form className="ai-governance-block" onSubmit={createAcceptancePolicy}>
                  <strong>创建工厂批准策略草稿</strong>
                  <label className="form-field"><span>工厂</span><select name="factory_id" required>{factoryOptions.map((factory) => <option key={factory.id} value={factory.id}>{factory.code} · {factory.name}</option>)}</select></label>
                  <input type="hidden" name="target_metric" value={selectedModel?.target_metric ?? ""} />
                  <div className="ai-two-fields"><label className="form-field"><span>策略代码</span><input name="policy_code" required defaultValue={defaultPolicyCode} /></label><label className="form-field"><span>版本</span><input name="version" required defaultValue="1.0" /></label></div>
                  <div className="ai-two-fields"><label className="form-field"><span>验证 RMSE 上限</span><input name="max_validation_rmse" type="number" min="0" step="any" required /></label><label className="form-field"><span>验证 R² 下限</span><input name="min_validation_r2" type="number" step="any" required /></label></div>
                  <div className="ai-two-fields"><label className="form-field"><span>最少训练分组</span><input name="min_train_groups" type="number" min="2" required /></label><label className="form-field"><span>最少验证分组</span><input name="min_validation_groups" type="number" min="1" required /></label></div>
                  <label className="form-field"><span>批准来源 URI</span><input name="source_uri" required placeholder="例如：dms://factory/model-policy/..." /></label>
                  <label className="form-field"><span>备注</span><textarea name="remark" rows={2} /></label>
                  <p className="ai-hint">阈值必须来自工厂批准文件或评审结论，系统不会自动生成或猜测工厂验收阈值。</p>
                  <button className="button button-secondary" disabled={!selectedModel || !factoryOptions.length || submitting === "acceptance-policy-create"}>{submitting === "acceptance-policy-create" ? <LoaderCircle className="spin" /> : <ShieldCheck />} 创建策略草稿</button>
                </form>
                <div className="ai-two-fields">
                  <button className="button button-secondary danger-button" disabled={!selectedModel || submitting === "acceptance-REJECTED"} onClick={() => void decideModelAcceptance("REJECTED")}><X /> 验收驳回</button>
                  <button className="button button-secondary" disabled={!selectedModel || !modelDataset?.leakage_check.passed || !hasValidationEvidence || !hasArtifactEvidence || !factoryPolicyCoverage || submitting === "acceptance-ACCEPTED"} onClick={() => void decideModelAcceptance("ACCEPTED")}><ShieldCheck /> 验收通过</button>
                </div>
                <button className="button button-primary" disabled={!selectedModel || selectedModel.status === "ACTIVE" || selectedAcceptance?.decision !== "ACCEPTED" || selectedOodPolicy?.status !== "ACTIVE" || !selectedScopes.some((item) => item.status === "ACTIVE") || !hasValidationEvidence || !hasArtifactEvidence || !factoryPolicyCoverage || submitting === "model-status-ACTIVE"} onClick={() => void changeModelStatus("ACTIVE")}>{submitting === "model-status-ACTIVE" ? <LoaderCircle className="spin" /> : <Check />} 激活版本</button>
                <div className="ai-two-fields">
                  <button className="button button-secondary" disabled={!selectedModel || selectedModel.status === "DRAFT" || submitting === "model-status-DRAFT"} onClick={() => void changeModelStatus("DRAFT")}>转为草稿</button>
                  <button className="button button-secondary danger-button" disabled={!selectedModel || selectedModel.status === "RETIRED" || submitting === "model-status-RETIRED"} onClick={() => void changeModelStatus("RETIRED")}>退役版本</button>
                </div>
                <div className="ai-governance-block">
                  <strong>工厂 / 车型 / 颜色适用范围</strong>
                  {selectedScopes.map((scope) => <div className="ai-scope-row" key={scope.id}><span><b>{scope.factory_code}</b> · {scope.vehicle_model_code} · {scope.color_code}<small>{scope.source} · {statusLabel(scope.status)}</small></span>{scope.status !== "INACTIVE" ? <button type="button" className="button button-secondary danger-button" disabled={submitting === `scope-${scope.id}`} onClick={() => void deactivateScope(scope)}>停用</button> : null}</div>)}
                  {!selectedScopes.length ? <p className="ai-hint">当前模型没有适用范围，不能验收或激活。</p> : null}
                  <label className="form-field"><span>从现有生产快照申请扩展范围</span><select value={selectedSnapshot?.id ?? ""} onChange={(event) => setSelectedSnapshotId(event.target.value)}>{compatibleSnapshots.map((snapshot) => <option key={snapshot.id} value={snapshot.id}>{snapshot.factory_code} / {snapshot.vehicle_model_code} / {snapshot.color_code} · {snapshot.production_run_no}</option>)}</select></label>
                  <button type="button" className="button button-secondary" disabled={!selectedModel || !selectedSnapshot || submitting === "scope-add"} onClick={() => void addScopeFromSelectedSnapshot()}>{submitting === "scope-add" ? <LoaderCircle className="spin" /> : <Target />} 加入待验收范围</button>
                </div>
                <form className="ai-governance-block" onSubmit={updateOodPolicy}>
                  <strong>异常输入拦截规则</strong>
                  <div className="ai-two-fields"><label className="form-field"><span>最大标准化偏移</span><input name="max_abs_standardized_shift" type="number" min="0.1" step="0.1" key={`shift-${selectedOodPolicy?.id}-${selectedOodPolicy?.updated_at}`} defaultValue={selectedOodPolicy?.max_abs_standardized_shift ?? 4} /></label><label className="form-field"><span>最大异常特征比例</span><input name="max_outlier_feature_ratio" type="number" min="0" max="1" step="0.05" key={`ratio-${selectedOodPolicy?.id}-${selectedOodPolicy?.updated_at}`} defaultValue={selectedOodPolicy?.max_outlier_feature_ratio ?? 0.2} /></label></div>
                  <label className="form-field"><span>最低特征完整率</span><input name="min_feature_completeness" type="number" min="0.1" max="1" step="0.05" key={`complete-${selectedOodPolicy?.id}-${selectedOodPolicy?.updated_at}`} defaultValue={selectedOodPolicy?.min_feature_completeness ?? 1} /></label>
                  <button className="button button-secondary" disabled={!selectedModel || submitting === "ood-policy"}>{submitting === "ood-policy" ? <LoaderCircle className="spin" /> : <ShieldCheck />} 保存并重新验收</button>
                </form>
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
              {!driftLoading && !driftReport ? (
                <WorkspaceEmptyState
                  icon={Activity}
                  title="请选择模型版本查看治理报告"
                  description="治理报告会展示漂移、验证证据、工件哈希和适用范围，请先从左侧选择具体模型版本。"
                  compact
                />
              ) : null}
              {selectedModel?.evaluation_metrics?.multi_axis_validation ? (() => {
                const raw = selectedModel.evaluation_metrics.multi_axis_validation as unknown as Record<string, unknown>;
                const axes = raw && typeof raw === "object" && "axes" in raw ? (raw.axes as Record<string, Record<string, unknown>>) : null;
                const entries = axes ? Object.entries(axes) : [];
                if (entries.length === 0) return null;
                return (
                  <div className="validation-chart-panel">
                    <div className="program-subheading"><div><span className="eyebrow">Multi-Axis Validation</span><h3>多轴验证证据</h3></div></div>
                    <ValidationChart
                      axes={entries.map(([axis, summary]) => {
                        const s = summary as Record<string, unknown>;
                        return {
                          axis,
                          rmse: (s.rmse as number | null) ?? null,
                          r2: (s.r2 as number | null) ?? null,
                          status: (s.status as string) ?? "UNKNOWN",
                          sampleCount: (s.validation_sample_count as number) ?? 0,
                        };
                      })}
                    />
                  </div>
                );
              })() : null}
            </div>
          </div>
        ) : null}

        {activeTab === "predictions" ? (
          <div className="ai-split">
            <div className="ai-control-panel">
              <div className="program-subheading"><div><span className="eyebrow">Inference</span><h3>执行点位预测</h3></div><Target /></div>
              <div className="ai-form-stack">
                <label className="form-field"><span>生效模型</span><select value={selectedModelId} onChange={(event) => { setSelectedModelId(event.target.value); setSelectedSnapshotId(""); }}>{models.map((model) => <option key={model.id} value={model.id}>{model.model_code}:{model.version} / {model.target_metric}</option>)}</select></label>
                <label className="form-field"><span>选择车身与测量点</span><select value={selectedSnapshot?.id ?? ""} onChange={(event) => setSelectedSnapshotId(event.target.value)}>{compatibleSnapshots.map((snapshot) => <option key={snapshot.id} value={snapshot.id}>{snapshot.production_run_no} · {snapshot.measurement_point_code} · {snapshot.factory_code}/{snapshot.vehicle_model_code}/{snapshot.color_code}</option>)}</select></label>
                <div className="ai-context-box"><span>生产上下文</span><strong>{selectedSnapshot ? `${selectedSnapshot.factory_code} / ${selectedSnapshot.vehicle_model_code} / ${selectedSnapshot.color_code}` : "—"}</strong><span>特征版本 / 数量</span><strong>{selectedSnapshot ? `${selectedSnapshot.feature_set_version} / ${selectedSnapshot.feature_count}` : "—"}</strong><span>适用范围</span><strong>{governanceLoading ? "检查中" : statusLabel(governanceCheck?.applicability_status ?? "—")}</strong><span>输入分布</span><strong>{governanceLoading ? "检查中" : statusLabel(governanceCheck?.ood_status ?? "—")}</strong><span>完整率 / 最大偏移</span><strong>{governanceCheck ? `${formatNumber(governanceCheck.evidence.feature_completeness * 100, 1)}% / ${formatNumber(governanceCheck.evidence.max_abs_standardized_shift)}` : "—"}</strong></div>
                {governanceCheck && !governanceAllowed && !governanceLoading ? <p className="ai-governance-warning">当前车型/颜色不在模型适用范围内，或输入参数偏离训练数据过多，已暂停预测与推荐。</p> : null}
                <button className="button button-primary" onClick={() => void runPrediction()} disabled={!selectedModel || selectedModel.status !== "ACTIVE" || !selectedSnapshot || governanceLoading || !governanceAllowed || submitting === "predict"}>{submitting === "predict" ? <LoaderCircle className="spin" /> : <Play />} 执行并保存预测</button>
              </div>
            </div>
            <div className="ai-record-list">
              {filteredPredictions.map((prediction) => {
                const diagnosis = diagnoses.find((item) => item.prediction_result_id === prediction.id);
                return <button className={`ai-result-card ${prediction.id === selectedPredictionId ? "selected" : ""}`} key={prediction.id} onClick={() => setSelectedPredictionId(prediction.id)}>
                  <div><strong>{prediction.metric_code} = {formatNumber(prediction.predicted_value)}</strong><span>{prediction.model_name}</span><small>{statusLabel(prediction.applicability_status)} · {statusLabel(prediction.ood_status)} · {new Date(prediction.predicted_at).toLocaleString("zh-CN")}</small></div>
                  <div className="ai-result-numbers"><span>{formatNumber(prediction.lower_bound)} - {formatNumber(prediction.upper_bound)}</span><b>{formatNumber(prediction.confidence * 100, 1)}%</b></div>
                  <span className={`record-status ${diagnosis ? "status-on" : "status-off"}`}>{diagnosis ? "已诊断" : "待诊断"}</span>
                </button>;
              })}
              {!filteredPredictions.length ? (
                <WorkspaceEmptyState
                  icon={Activity}
                  title="暂无预测记录"
                  description="当生效模型通过治理门禁后执行预测，这里会沉淀点位预测结果和诊断证据。"
                  compact
                />
              ) : null}
              {selectedPrediction ? <div className="ai-evidence-panel">
                <div className="program-subheading"><div><span className="eyebrow">Explainability</span><h3>诊断证据</h3></div>{!selectedDiagnosis ? <button className="button button-primary" onClick={() => void runDiagnosis(selectedPrediction.id)} disabled={submitting === `diagnose-${selectedPrediction.id}`}>{submitting ? <LoaderCircle className="spin" /> : <Sparkles />} 生成诊断</button> : <span className="record-status status-on">{selectedDiagnosis.causality_status}</span>}</div>
                {selectedDiagnosis ? <><p className="ai-summary">{selectedDiagnosis.summary}</p><div className="ai-factor-list">{selectedDiagnosis.factor_contributions.map((factor) => <div key={factor.feature}><span><strong>{factor.feature}</strong><small>当前值 {formatNumber(factor.value)} · {factor.basis}</small></span><b className={factor.impact >= 0 ? "positive" : "negative"}>{factor.impact >= 0 ? "+" : ""}{formatNumber(factor.impact)}</b></div>)}</div></> : <div className="program-empty">选择“生成诊断”后保存局部特征贡献和相关性说明。</div>}
              </div> : null}
            </div>
          </div>
        ) : null}

        {activeTab === "recommendations" ? (
          <div className="ai-split">
            <form className="ai-control-panel" onSubmit={generateRecommendation}>
              <div className="program-subheading"><div><span className="eyebrow">Constrained Optimization</span><h3>生成参数推荐</h3></div><ShieldCheck /></div>
              <div className="ai-form-stack">
                <label className="form-field"><span>模型</span><select value={selectedModelId} onChange={(event) => { setSelectedModelId(event.target.value); setSelectedSnapshotId(""); }}>{models.map((model) => <option key={model.id} value={model.id}>{model.model_code}:{model.version} / {model.target_metric}</option>)}</select></label>
                <label className="form-field"><span>选择车身与测量点</span><select value={selectedSnapshot?.id ?? ""} onChange={(event) => setSelectedSnapshotId(event.target.value)}>{compatibleSnapshots.map((snapshot) => <option key={snapshot.id} value={snapshot.id}>{snapshot.production_run_no} · {snapshot.measurement_point_code}</option>)}</select></label>
                <div className="ai-context-box"><span>生产上下文</span><strong>{selectedSnapshot ? `${selectedSnapshot.factory_code} / ${selectedSnapshot.vehicle_model_code} / ${selectedSnapshot.color_code}` : "—"}</strong><span>适用范围</span><strong>{governanceLoading ? "检查中" : statusLabel(governanceCheck?.applicability_status ?? "—")}</strong><span>输入分布</span><strong>{governanceLoading ? "检查中" : statusLabel(governanceCheck?.ood_status ?? "—")}</strong><span>异常特征比例</span><strong>{governanceCheck ? `${formatNumber(governanceCheck.evidence.outlier_feature_ratio * 100, 1)}%` : "—"}</strong></div>
                <div className="ai-two-fields"><label className="form-field"><span>目标下限</span><input type="number" step="any" value={targetMin} onChange={(event) => setTargetMin(event.target.value)} /></label><label className="form-field"><span>目标上限</span><input type="number" step="any" value={targetMax} onChange={(event) => setTargetMax(event.target.value)} /></label></div>
                <p className="ai-hint">至少填写一个目标上下限。系统会在安全边界内给出可执行的参数调整建议；确认后请到「受控试验」跟进。</p>
                <button className="button button-primary" disabled={!selectedModel || selectedModel.status !== "ACTIVE" || !selectedSnapshot || governanceLoading || !governanceAllowed || (!targetMin && !targetMax) || submitting === "recommend"}>{submitting === "recommend" ? <LoaderCircle className="spin" /> : <Sparkles />} 生成约束推荐</button>
              </div>
            </form>
            <div className="ai-record-list">
              <div className="ai-recommendation-grid">
                {filteredRecommendations.map((recommendation) => <button className={`ai-recommendation-card ${recommendation.id === selectedRecommendationId ? "selected" : ""}`} key={recommendation.id} onClick={() => selectRecommendation(recommendation.id)}><span className={`record-status ${["REJECTED"].includes(recommendation.status) ? "status-off" : "status-on"}`}>{statusLabel(recommendation.status)}</span><strong>{recommendation.recommendation_no}</strong><small>{recommendation.model_version} · {recommendation.target_metric}</small><b>{recommendation.predicted_improvement >= 0 ? "+" : ""}{formatNumber(recommendation.predicted_improvement)}</b></button>)}
              </div>
              {selectedRecommendation ? <div className="ai-evidence-panel">
                <div className="program-subheading"><div><span className="eyebrow">推荐闭环</span><h3>{selectedRecommendation.recommendation_no}</h3></div><span className="record-status status-on">{statusLabel(selectedRecommendation.status)}</span></div>
                <p className="ai-summary">{selectedRecommendation.diagnosis_summary}</p>
                <div className="ai-trial-panel">
                  <div className="ai-trial-heading">
                    <span><b>受控试验计划</b><small>推荐审批前必须具备假设、风险、回滚和持续观察方案。</small></span>
                    <span className={`status-badge ${selectedTrial?.status === "APPROVED" || selectedTrial?.status === "VERIFIED" || selectedTrial?.status === "ROLLED_BACK" ? "status-healthy" : selectedTrial?.status === "REJECTED" || selectedTrial?.status === "INEFFECTIVE" ? "status-risk" : "status-warning"}`}>{selectedTrial ? statusLabel(selectedTrial.status) : "未创建"}</span>
                  </div>
                  {selectedTrial ? <div className="ai-trial-details"><p><b>假设</b>{selectedTrial.hypothesis}</p><p><b>证据</b>{statusLabel(selectedTrial.evidence_type)}</p><p><b>预期</b>{selectedTrial.expected_outcome}</p><p><b>风险</b>{selectedTrial.risk_assessment}</p><p><b>回滚</b>{selectedTrial.rollback_plan}</p><p><b>持续观察</b>{selectedTrial.sustained_observation_plan}</p>{selectedTrial.completion_summary ? <p><b>结论</b>{selectedTrial.completion_summary}</p> : null}</div> : <p className="ai-hint">当前推荐尚未纳入受控试验，不能直接批准执行。</p>}
                  {selectedRollback ? <div className="ai-rollback-panel"><strong>{selectedRollback.rollback_no}</strong><span>{selectedRollback.executed_by} · {new Date(selectedRollback.executed_at).toLocaleString("zh-CN")}</span><small>{selectedRollback.rollback_reason}</small></div> : null}
                  {selectedRecommendation.status === "PENDING" && !selectedTrial ? <button className="button button-secondary" type="button" disabled={submitting === `trial-create-${selectedRecommendation.id}`} onClick={() => void createControlledTrial(selectedRecommendation)}>{submitting === `trial-create-${selectedRecommendation.id}` ? <LoaderCircle className="spin" /> : <ShieldCheck />} 创建受控试验计划</button> : null}
                  {selectedRecommendation.status === "PENDING" && selectedTrial?.status === "PLANNED" ? <div className="ai-workflow-actions compact-actions"><button className="button button-secondary danger-button" type="button" disabled={submitting === `trial-approval-${selectedTrial.id}`} onClick={() => void approveControlledTrial(selectedTrial, false)}><X /> 驳回试验</button><button className="button button-secondary" type="button" disabled={submitting === `trial-approval-${selectedTrial.id}`} onClick={() => void approveControlledTrial(selectedTrial, true)}>{submitting === `trial-approval-${selectedTrial.id}` ? <LoaderCircle className="spin" /> : <Check />} 批准试验计划</button></div> : null}
                  {selectedTrial?.status === "INEFFECTIVE" && !selectedRollback ? <button className="button button-secondary danger-button" type="button" disabled={submitting === `rollback-${selectedTrial.id}`} onClick={() => void recordRollback(selectedTrial)}>{submitting === `rollback-${selectedTrial.id}` ? <LoaderCircle className="spin" /> : <RotateCcw />} 记录回滚执行</button> : null}
                </div>
                <div className="ai-action-table">
                  <div className="ai-action-row ai-action-head"><span>参数</span><span>当前值</span><span>推荐值</span><span>实际执行值</span><span>硬边界</span></div>
                  {selectedRecommendation.actions.map((action) => <div className="ai-action-row" key={action.id}><span><strong>{action.parameter_name}</strong><small>{action.process_stage} · {action.parameter_code}</small></span><span>{formatNumber(action.current_value)} {action.unit}</span><span>{formatNumber(action.recommended_value)} {action.unit}</span><span>{selectedRecommendation.status === "APPROVED" ? <input type="number" step="any" value={executedValues[action.id] ?? ""} onChange={(event) => setExecutedValues((current) => ({ ...current, [action.id]: event.target.value }))} /> : `${formatNumber(action.executed_value)} ${action.unit}`}</span><span>{formatNumber(action.hard_min)} - {formatNumber(action.hard_max)}<small>{action.constraint_source_code ? `${statusLabel(action.constraint_source_type ?? "")} · ${action.constraint_source_code} / ${action.constraint_source_version ?? "—"}` : "约束来源未固化"}</small></span></div>)}
                </div>
                {selectedRecommendation.status === "PENDING" ? <div className="ai-workflow-actions"><button className="button button-secondary danger-button" onClick={() => void approveRecommendation(selectedRecommendation, false)}><X /> 驳回推荐</button><button className="button button-primary" disabled={!selectedTrialApproved || submitting === `approval-${selectedRecommendation.id}`} onClick={() => void approveRecommendation(selectedRecommendation, true)}><Check /> 批准推荐执行</button></div> : null}
                {selectedRecommendation.status === "APPROVED" ? <div className="ai-workflow-actions"><button className="button button-primary" onClick={() => void executeRecommendation(selectedRecommendation)}><Play /> 记录实际执行</button></div> : null}
                {selectedRecommendation.status === "EXECUTED" ? <div className="ai-verification"><label className="form-field"><span>选择执行后的同生产事件、同点位复测记录</span><select value={verificationMeasurementId} onChange={(event) => setVerificationMeasurementId(event.target.value)}><option value="">请选择复测数据</option>{verificationOptions.map((measurement) => <option key={measurement.id} value={measurement.id}>{measurement.data_no} · {new Date(measurement.measured_at).toLocaleString("zh-CN")}</option>)}</select></label>{!verificationOptions.length ? <p className="ai-hint">请先在质量数据中心录入执行后的复测数据，或通过 QMS 集成事件写入。</p> : null}<button className="button button-primary" disabled={!verificationOptions.length} onClick={() => void verifyRecommendation(selectedRecommendation)}><ShieldCheck /> 完成复测评价</button></div> : null}
                {selectedRecommendation.evaluation ? <div className={`ai-evaluation ${selectedRecommendation.evaluation.is_effective ? "effective" : "ineffective"}`}><strong>{selectedRecommendation.evaluation.is_effective ? "闭环改善有效" : "闭环改善未达预期"}</strong><span>基准 {formatNumber(selectedRecommendation.evaluation.baseline_value)} → 复测 {formatNumber(selectedRecommendation.evaluation.verified_value)}，实际改善 {formatNumber(selectedRecommendation.evaluation.actual_improvement)}</span><small>{selectedRecommendation.evaluation.verified_by} · {selectedRecommendation.evaluation.conclusion}</small></div> : null}
              </div> : (
                <WorkspaceEmptyState
                  icon={Sparkles}
                  title="暂无推荐记录"
                  description="推荐会在模型与安全校验通过后生成；确认后可到「受控试验」继续审批、执行与复测。"
                  compact
                />
              )}
            </div>
          </div>
        ) : null}
        {activeTab === "comparison" && canManageModels ? (
          <div className="model-comparison">
            <div className="program-subheading">
              <div><span className="eyebrow">模型对比</span><h3>模型版本对比</h3></div>
              <span>{models.length} 个模型版本</span>
            </div>
            <div className="comparison-grid">
              {models.length === 0 ? (
                <WorkspaceEmptyState
                  icon={BrainCircuit}
                  title="暂无模型版本可供对比"
                  description="至少训练出一个模型版本后，才会在这里形成验证指标和特征版本对比视图。"
                  compact
                />
              ) : (
                <div className="model-comparison-table-wrap">
                  <table className="master-table comparison-table">
                    <thead>
                      <tr>
                        <th>模型</th>
                        <th>目标</th>
                        <th>训练 R²</th>
                        <th>验证 R²</th>
                        <th>训练 RMSE</th>
                        <th>验证 RMSE</th>
                        <th>样本数</th>
                        <th>特征版本</th>
                        <th>状态</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...models]
                        .sort((a, b) => (b.evaluation_metrics.validation_r2 ?? 0) - (a.evaluation_metrics.validation_r2 ?? 0))
                        .map((model) => {
                          const trainingR2 = model.evaluation_metrics.training_r2;
                          const validationR2 = model.evaluation_metrics.validation_r2;
                          const isActive = model.status === "ACTIVE";
                          return (
                            <tr key={model.id} className={isActive ? "comparison-row-active" : ""}>
                              <td className="mono">{model.model_code}:{model.version}</td>
                              <td>{model.target_metric}</td>
                              <td className={trainingR2 != null && trainingR2 >= 0.7 ? "cell-good" : trainingR2 != null ? "cell-warn" : ""}>{formatNumber(trainingR2)}</td>
                              <td className={validationR2 != null && validationR2 >= 0.6 ? "cell-good" : validationR2 != null ? "cell-warn" : ""}>{formatNumber(validationR2)}</td>
                              <td>{formatNumber(model.evaluation_metrics.training_rmse)}</td>
                              <td>{formatNumber(model.evaluation_metrics.validation_rmse)}</td>
                              <td>{model.training_sample_count}</td>
                              <td className="mono comparison-feature-version">{model.feature_set_version.slice(-20)}</td>
                              <td><span className={`record-status ${isActive ? "status-on" : "status-off"}`}>{statusLabel(model.status)}</span></td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                  {models.some((model) => model.evaluation_metrics.validation_r2 != null) ? (
                    <div className="comparison-summary">
                      <article><span>已评估模型</span><strong>{models.filter((model) => model.evaluation_metrics.validation_r2 != null).length}</strong></article>
                      <article><span>平均验证 R²</span><strong>{formatNumber(models.reduce((sum, model) => sum + (model.evaluation_metrics.validation_r2 ?? 0), 0) / Math.max(1, models.filter((model) => model.evaluation_metrics.validation_r2 != null).length))}</strong></article>
                      <article><span>生效模型</span><strong>{models.filter((model) => model.status === "ACTIVE").length}</strong></article>
                      <article><span>特征集版本</span><strong>{Array.from(new Set(models.map((model) => model.feature_set_version))).length} 个</strong></article>
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
