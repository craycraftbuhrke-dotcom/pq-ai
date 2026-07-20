"use client";

import { Activity, BrainCircuit, LoaderCircle, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

type Model = {
  id: string;
  model_code: string;
  version: string;
  target_metric: string;
  status: string;
};

type Prediction = {
  prediction_result_id: string | null;
  metric_code: string;
  predicted_value: number;
  lower_bound: number;
  upper_bound: number;
  confidence: number;
};

type Diagnosis = {
  summary: string;
  confidence: number;
  causality_status: string;
  factor_contributions: Array<{ feature?: string; contribution?: number }>;
};

type Recommendation = {
  recommendation_no: string;
  current_prediction: number;
  expected_prediction: number;
  predicted_improvement: number;
  actions: Array<{
    parameter_name?: string;
    feature_name?: string;
    current_value?: number;
    recommended_value?: number;
    unit?: string;
  }>;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  const payload = (await response.json().catch(() => ({}))) as T & { error?: unknown };
  if (!response.ok) {
    const error = payload.error;
    throw new Error(
      typeof error === "string"
        ? error
        : error && typeof error === "object" && "message" in error
          ? String(error.message)
          : `操作失败（${response.status}）`,
    );
  }
  return payload;
}

export function PointAiActions({
  productionRunId,
  measurementPointId,
}: {
  productionRunId?: string | null;
  measurementPointId: string;
}) {
  const [models, setModels] = useState<Model[]>([]);
  const [modelId, setModelId] = useState("");
  const [targetMin, setTargetMin] = useState("");
  const [targetMax, setTargetMax] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);

  useEffect(() => {
    let cancelled = false;
    void request<Model[]>("/api/ai/models")
      .then((items) => {
        if (cancelled) return;
        const active = items.filter((item) => item.status === "ACTIVE");
        setModels(active);
        setModelId((current) => current || active[0]?.id || "");
      })
      .catch((loadError) => {
        if (!cancelled) setError(loadError instanceof Error ? loadError.message : "模型加载失败");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedModel = useMemo(() => models.find((item) => item.id === modelId), [modelId, models]);
  const ready = Boolean(productionRunId && measurementPointId && modelId);

  async function predict(): Promise<Prediction> {
    if (!ready || !productionRunId) throw new Error("请先选择有生产记录的点位和生效模型");
    const result = await request<Prediction>(`/api/ai/models/${modelId}/predictions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        production_run_id: productionRunId,
        measurement_point_id: measurementPointId,
        persist_result: true,
      }),
    });
    setPrediction(result);
    return result;
  }

  async function runPrediction() {
    setBusy("prediction");
    setError("");
    try {
      await predict();
    } catch (operationError) {
      setError(operationError instanceof Error ? operationError.message : "质量预测失败");
    } finally {
      setBusy("");
    }
  }

  async function runDiagnosis() {
    setBusy("diagnosis");
    setError("");
    try {
      const predicted = prediction?.prediction_result_id ? prediction : await predict();
      if (!predicted.prediction_result_id) throw new Error("预测结果未保存，不能继续诊断");
      setDiagnosis(
        await request<Diagnosis>(
          `/api/ai/models/predictions/${predicted.prediction_result_id}/diagnoses`,
          { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" },
        ),
      );
    } catch (operationError) {
      setError(operationError instanceof Error ? operationError.message : "智能诊断失败");
    } finally {
      setBusy("");
    }
  }

  async function runRecommendation() {
    setBusy("recommendation");
    setError("");
    try {
      if (!ready || !productionRunId) throw new Error("请先选择有生产记录的点位和生效模型");
      setRecommendation(
        await request<Recommendation>(`/api/ai/models/${modelId}/recommendations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            production_run_id: productionRunId,
            measurement_point_id: measurementPointId,
            target_min: targetMin === "" ? null : Number(targetMin),
            target_max: targetMax === "" ? null : Number(targetMax),
            max_actions: 3,
            max_step_ratio: 0.1,
          }),
        }),
      );
    } catch (operationError) {
      setError(operationError instanceof Error ? operationError.message : "参数建议生成失败");
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="point-ai-card">
      <div className="program-subheading compact">
        <div><span className="eyebrow">智能辅助</span><h4>分析这个点位</h4></div>
        <BrainCircuit />
      </div>
      {!productionRunId ? <p className="ai-hint">请先在页面上方选择一条生产记录。</p> : null}
      <label className="form-field">
        <span>选择已验收生效的模型</span>
        <select value={modelId} onChange={(event) => { setModelId(event.target.value); setPrediction(null); setDiagnosis(null); setRecommendation(null); }} disabled={!models.length}>
          {models.map((model) => <option key={model.id} value={model.id}>{model.model_code} · {model.target_metric}</option>)}
        </select>
      </label>
      {!models.length ? <p className="ai-hint">暂无可用于现场分析的生效模型。</p> : null}
      <div className="point-ai-targets">
        <label className="form-field"><span>期望下限（建议时可填）</span><input type="number" step="any" value={targetMin} onChange={(event) => setTargetMin(event.target.value)} /></label>
        <label className="form-field"><span>期望上限（建议时可填）</span><input type="number" step="any" value={targetMax} onChange={(event) => setTargetMax(event.target.value)} /></label>
      </div>
      <div className="point-ai-buttons">
        <button type="button" className="button button-secondary" disabled={!ready || Boolean(busy)} onClick={() => void runPrediction()}>{busy === "prediction" ? <LoaderCircle className="spin" /> : <Activity />} 质量预测</button>
        <button type="button" className="button button-secondary" disabled={!ready || Boolean(busy)} onClick={() => void runDiagnosis()}>{busy === "diagnosis" ? <LoaderCircle className="spin" /> : <BrainCircuit />} 原因诊断</button>
        <button type="button" className="button button-primary" disabled={!ready || Boolean(busy)} onClick={() => void runRecommendation()}>{busy === "recommendation" ? <LoaderCircle className="spin" /> : <Sparkles />} 参数建议</button>
      </div>
      {error ? <div className="form-error">{error}</div> : null}
      {prediction ? <div className="point-ai-result"><strong>预测结果</strong><span>{selectedModel?.target_metric}：{prediction.predicted_value.toFixed(3)}</span><small>参考区间 {prediction.lower_bound.toFixed(3)} 至 {prediction.upper_bound.toFixed(3)} · 可信度 {(prediction.confidence * 100).toFixed(0)}%</small></div> : null}
      {diagnosis ? <div className="point-ai-result"><strong>诊断结论</strong><span>{diagnosis.summary}</span><small>当前结论是关联分析，需通过受控试验确认原因。</small></div> : null}
      {recommendation ? <div className="point-ai-result"><strong>参数建议</strong><span>预计从 {recommendation.current_prediction.toFixed(3)} 改善到 {recommendation.expected_prediction.toFixed(3)}</span>{recommendation.actions.map((action, index) => <small key={`${action.feature_name}-${index}`}>{action.parameter_name ?? action.feature_name ?? "工艺参数"}：{action.current_value ?? "—"} → {action.recommended_value ?? "—"} {action.unit ?? ""}</small>)}</div> : null}
    </section>
  );
}
