"use client";

import {
  ArrowRight,
  Check,
  FlaskConical,
  LoaderCircle,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { InfoGrid } from "@/components/info-grid";
import { useAuth } from "@/lib/auth-context";
import { WorkspaceEmptyState } from "@/components/workspace-empty-state";

type ControlledTrial = {
  id: string;
  trial_no: string;
  recommendation_id: string;
  recommendation_no: string;
  production_run_id?: string | null;
  measurement_point_code?: string;
  measurement_point_name?: string;
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
  rollback?: { status: string; rollback_no: string; executed_at: string } | null;
  evaluation?: { is_effective: boolean; actual_improvement: number; conclusion: string | null } | null;
};

type Summary = {
  total: number;
  planned: number;
  approved: number;
  running: number;
  verified: number;
  ineffective: number;
  rolled_back: number;
};

const STATUS_LABELS: Record<string, string> = {
  PLANNED: "已计划",
  APPROVED: "已批准",
  RUNNING: "试验中",
  VERIFIED: "有效",
  INEFFECTIVE: "未达预期",
  ROLLED_BACK: "已回滚",
};

const STATUS_TONES: Record<string, string> = {
  PLANNED: "status-info",
  APPROVED: "status-info",
  RUNNING: "status-warning",
  VERIFIED: "status-healthy",
  INEFFECTIVE: "status-warning",
  ROLLED_BACK: "status-risk",
};

const EVIDENCE_LABELS: Record<string, string> = {
  ASSOCIATION: "关联证据",
  RULE: "规则证据",
  SIMULATION: "仿真证据",
  DOE: "DOE 证据",
  CONTROLLED_CHANGE: "受控变更证据",
};

function getApiKeyFromCookie(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)pq_api_key=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    cache: "no-store",
    headers: { ...init?.headers, "x-api-key": getApiKeyFromCookie() },
    ...init,
  });
  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => ({}))) as T & { detail?: string };
  if (!response.ok) throw new Error(payload.detail ?? `请求失败（${response.status}）`);
  return payload;
}

export default function ControlledTrialsPage() {
  const { actor } = useAuth();
  const [trials, setTrials] = useState<ControlledTrial[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [selectedTrial, setSelectedTrial] = useState<ControlledTrial | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await apiRequest<ControlledTrial[]>("/api/ai/controlled-trials?limit=200");
      setTrials(data || []);
      const counts: Record<string, number> = {};
      if (data) {
        for (const trial of data) {
          counts[trial.status] = (counts[trial.status] || 0) + 1;
        }
      }
      setSummary({
        total: data?.length ?? 0,
        planned: counts.PLANNED ?? 0,
        approved: counts.APPROVED ?? 0,
        running: counts.RUNNING ?? 0,
        verified: counts.VERIFIED ?? 0,
        ineffective: counts.INEFFECTIVE ?? 0,
        rolled_back: counts.ROLLED_BACK ?? 0,
      });
      setSelectedTrial((current) => {
        if (!current) return null;
        const updated = data?.find((t) => t.id === current.id);
        return updated ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return trials.filter(
      (t) =>
        (!statusFilter || t.status === statusFilter) &&
        (!q || [t.trial_no, t.recommendation_no, t.target_metric, t.hypothesis].some((v) =>
          String(v ?? "").toLowerCase().includes(q),
        )),
    );
  }, [trials, query, statusFilter]);

  const visibleSelectedTrial = useMemo(
    () => (selectedTrial ? filtered.find((trial) => trial.id === selectedTrial.id) ?? null : null),
    [filtered, selectedTrial],
  );

  async function executeAction(trialId: string, action: string) {
    setSubmitting(action);
    setError("");
    try {
      await apiRequest(`/api/ai/controlled-trials/${trialId}/${action}`, { method: "POST" });
      setNotice(`操作"${action}"已提交`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setSubmitting("");
    }
  }

  if (!actor.isAuthenticated) {
    return (
      <div className="page-stack">
        <WorkspaceEmptyState
          icon={ShieldCheck}
          title="请先登录后查看受控试验"
          description="受控试验中心包含高风险审批、执行和回滚动作，登录后才能查看完整闭环记录。"
          compact
        />
      </div>
    );
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">CLOSED LOOP · PHASE 6</span>
          <h1>受控试验中心</h1>
          <p>管理工艺参数调整的受控试验计划、审批、执行、复测评价与回滚的全流程闭环。</p>
        </div>
        <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} /> 刷新
        </button>
      </header>
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}
      {error ? <button className="message-banner message-error" onClick={() => setError("")}>{error}<X /></button> : null}
      <section className="module-stat-strip">
        <article><span>试验总数</span><strong>{summary?.total ?? "…"}</strong><small>全程可追溯审计</small></article>
        <article><span>试验中</span><strong>{summary?.running ?? "…"}</strong><small>等待复测评价</small></article>
        <article><span>有效 / 未达预期</span><strong>{summary?.verified ?? "…"} / {summary?.ineffective ?? "…"}</strong><small>已归档</small></article>
        <article><span>已回滚</span><strong>{summary?.rolled_back ?? "…"}</strong><small>已恢复原程序版本</small></article>
      </section>
      <section className="panel controlled-trial-workspace">
        <div className="master-tabs">
          <label className="master-search">
            <Search />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索试验编号、假设或指标" />
          </label>
          <select className="integration-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">全部状态</option>
            {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div className="controlled-trial-grid">
          <div className="trial-list">
            {filtered.map((trial) => (
              <button
                key={trial.id}
                className={`trial-card ${selectedTrial?.id === trial.id ? "selected" : ""}`}
                onClick={() => setSelectedTrial(trial)}
              >
                <div className="trial-card-header">
                  <span className={`status-badge ${STATUS_TONES[trial.status] ?? "status-info"}`}>
                    {STATUS_LABELS[trial.status] ?? trial.status}
                  </span>
                  <strong className="mono">{trial.trial_no}</strong>
                </div>
                <div className="trial-card-meta">
                  <span>{trial.target_metric}</span>
                  <span>{EVIDENCE_LABELS[trial.evidence_type] ?? trial.evidence_type}</span>
                </div>
                <p className="trial-card-hypothesis">{trial.hypothesis.slice(0, 80)}{trial.hypothesis.length > 80 ? "…" : ""}</p>
                <small>创建: {trial.requested_at ? new Date(trial.requested_at).toLocaleString("zh-CN") : "—"}</small>
              </button>
            ))}
            {!filtered.length ? (
              <WorkspaceEmptyState
                icon={FlaskConical}
                title="暂无受控试验记录"
                description="当前筛选条件下没有试验计划，可切换状态筛选或从 AI 推荐链路中创建新的受控试验。"
                compact
              />
            ) : null}
          </div>
          {visibleSelectedTrial ? (
            <div className="trial-detail">
              <div className="program-subheading">
                <div>
                  <span className="eyebrow">TRIAL DETAIL</span>
                  <h3>{visibleSelectedTrial.trial_no}</h3>
                </div>
                <span className={`status-badge ${STATUS_TONES[visibleSelectedTrial.status] ?? "status-info"}`}>
                  {STATUS_LABELS[visibleSelectedTrial.status] ?? visibleSelectedTrial.status}
                </span>
              </div>
              <InfoGrid
                className="trial-detail-grid"
                items={[
                  {
                    label: "关联推荐",
                    value: <span className="mono">{visibleSelectedTrial.recommendation_no ?? visibleSelectedTrial.recommendation_id.slice(0, 12)}</span>,
                  },
                  { label: "目标指标", value: visibleSelectedTrial.target_metric },
                  { label: "涉及点位", value: visibleSelectedTrial.measurement_point_code ?? visibleSelectedTrial.measurement_point_name ?? "—" },
                  { label: "证据类型", value: EVIDENCE_LABELS[visibleSelectedTrial.evidence_type] ?? visibleSelectedTrial.evidence_type },
                ]}
              />
              <div className="trial-section">
                <h4>试验假设</h4>
                <p>{visibleSelectedTrial.hypothesis}</p>
              </div>
              <div className="trial-section">
                <h4>预期结果</h4>
                <p>{visibleSelectedTrial.expected_outcome}</p>
              </div>
              <div className="trial-section">
                <h4>风险评估</h4>
                <p>{visibleSelectedTrial.risk_assessment}</p>
              </div>
              <div className="trial-section">
                <h4>回滚方案</h4>
                <p>{visibleSelectedTrial.rollback_plan}</p>
              </div>
              <div className="trial-section">
                <h4>持续观察方案</h4>
                <p>{visibleSelectedTrial.sustained_observation_plan}</p>
              </div>
              <div className="trial-timeline">
                <div><span>创建人</span><strong>{visibleSelectedTrial.requested_by}</strong><small>{new Date(visibleSelectedTrial.requested_at).toLocaleString("zh-CN")}</small></div>
                {visibleSelectedTrial.approved_by ? <ArrowRight className="flow-arrow" /> : null}
                {visibleSelectedTrial.approved_by ? <div><span>审批人</span><strong>{visibleSelectedTrial.approved_by}</strong><small>{visibleSelectedTrial.approved_at ? new Date(visibleSelectedTrial.approved_at).toLocaleString("zh-CN") : "—"}</small></div> : null}
                {visibleSelectedTrial.started_at ? <ArrowRight className="flow-arrow" /> : null}
                {visibleSelectedTrial.started_at ? <div><span>试验开始</span><strong>{new Date(visibleSelectedTrial.started_at).toLocaleString("zh-CN")}</strong></div> : null}
              </div>
              {visibleSelectedTrial.evaluation ? (
                <div className="trial-section">
                  <h4>复测评价 {visibleSelectedTrial.evaluation.is_effective ? <span className="status-badge status-healthy">有效</span> : <span className="status-badge status-warning">未达预期</span>}</h4>
                  <p>实际改善: {visibleSelectedTrial.evaluation.actual_improvement > 0 ? "+" : ""}{visibleSelectedTrial.evaluation.actual_improvement.toFixed(2)}</p>
                  {visibleSelectedTrial.evaluation.conclusion ? <p>{visibleSelectedTrial.evaluation.conclusion}</p> : null}
                </div>
              ) : null}
              {visibleSelectedTrial.rollback ? (
                <div className="trial-section">
                  <h4>回滚记录 <span className="status-badge status-risk">ROLLED_BACK</span></h4>
                  <p>回滚编号: {visibleSelectedTrial.rollback.rollback_no}</p>
                  <p>执行时间: {visibleSelectedTrial.rollback.executed_at ? new Date(visibleSelectedTrial.rollback.executed_at).toLocaleString("zh-CN") : "—"}</p>
                </div>
              ) : null}
              {visibleSelectedTrial.status === "PLANNED" ? (
                <div className="ai-workflow-actions">
                  <button className="button button-primary" onClick={() => executeAction(visibleSelectedTrial.id, "approval")} disabled={submitting === "approval"}>
                    {submitting === "approval" ? <LoaderCircle className="spin" /> : <Check />}
                    批准试验
                  </button>
                </div>
              ) : visibleSelectedTrial.status === "APPROVED" ? (
                <div className="ai-workflow-actions">
                  <button className="button button-primary" onClick={() => executeAction(visibleSelectedTrial.id, "start")} disabled={submitting === "start"}>
                    {submitting === "start" ? <LoaderCircle className="spin" /> : <Play />}
                    开始试验
                  </button>
                </div>
              ) : visibleSelectedTrial.status === "INEFFECTIVE" ? (
                <div className="ai-workflow-actions">
                  <button className="button button-secondary" onClick={() => executeAction(visibleSelectedTrial.id, "rollback")} disabled={submitting === "rollback"}>
                    {submitting === "rollback" ? <LoaderCircle className="spin" /> : <RotateCcw />}
                    执行回滚
                  </button>
                </div>
              ) : null}
              {visibleSelectedTrial.completion_summary ? (
                <div className="trial-section">
                  <h4>试验总结</h4>
                  <p>{visibleSelectedTrial.completion_summary}</p>
                </div>
              ) : null}
              {visibleSelectedTrial.approval_comment ? (
                <div className="trial-section">
                  <h4>审批意见</h4>
                  <p>{visibleSelectedTrial.approval_comment}</p>
                </div>
              ) : null}
            </div>
          ) : (
            <WorkspaceEmptyState
              icon={ArrowRight}
              title="请选择一条受控试验"
              description="左侧列表不会再默认自动选中记录，请由你显式选择需要查看的试验详情，降低误操作风险。"
            />
          )}
        </div>
      </section>
    </div>
  );
}
