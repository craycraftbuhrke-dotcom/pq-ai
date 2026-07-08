"use client";

import { Activity, CheckCircle2, CircleAlert, LoaderCircle, PlugZap, RefreshCw, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { SectionHeader } from "@/components/section-header";
import { WorkspaceEmptyState } from "@/components/workspace-empty-state";
import { useAuth } from "@/lib/auth-context";

type EndpointHealth = {
  id: string; code: string; name: string; system_type: string; is_active: boolean;
  last_success_at: string | null; last_failure_at: string | null;
  event_count: number; success_count: number; failed_count: number; pending_count: number;
};
type IntegrationHealth = {
  total_endpoints: number; active_endpoints: number; total_events: number;
  success_rate: number; dead_letter_count: number;
  recent_failures: Array<{ event_no: string; endpoint_code: string; event_type: string; last_error: string; created_at: string }>;
  endpoints: EndpointHealth[];
};

const SYSTEM_ICONS: Record<string, string> = { MES: "🏭", QMS: "✅", ROBOT: "🤖", MATERIAL: "🧪", MEASUREMENT: "📐" };

function getApiKey(): string { const m = document.cookie.match(/(?:^|;\s*)pq_api_key=([^;]*)/); return m ? decodeURIComponent(m[1]) : ""; }
function timeSince(d: string | null): string {
  if (!d) return "—"; const diff = Date.now() - new Date(d).getTime(); const mins = Math.floor(diff / 60000);
  if (mins < 1) return "刚刚"; if (mins < 60) return `${mins} 分钟前`;
  const hours = Math.floor(mins / 60); if (hours < 24) return `${hours} 小时前`; return `${Math.floor(hours / 24)} 天前`;
}

export default function IntegrationMonitorPage() {
  const { actor } = useAuth();
  const [health, setHealth] = useState<IntegrationHealth | null>(null);
  const [loading, setLoading] = useState(true); const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const key = getApiKey();
      const [epR, evR, smR] = await Promise.all([
        fetch("/api/integrations/endpoints", { headers: { "x-api-key": key }, cache: "no-store" }),
        fetch("/api/integrations/events?limit=500", { headers: { "x-api-key": key }, cache: "no-store" }),
        fetch("/api/integrations/summary", { headers: { "x-api-key": key }, cache: "no-store" }),
      ]);
      const eps = (await epR.json()) as Array<{ id: string; code: string; name: string; system_type: string; is_active: boolean; last_success_at: string | null; last_failure_at: string | null }>;
      const evts = (await evR.json()) as Array<{ event_no: string; endpoint_id: string; event_type: string; status: string; last_error: string | null; created_at: string }>;
      const sm = (await smR.json()) as { endpoints: number; active_endpoints: number; events: number; events_by_status: Record<string, number>; failed_events: number };

      const epHealth: EndpointHealth[] = (eps || []).map((ep) => {
        const ee = (evts || []).filter((e) => e.endpoint_id === ep.id);
        return { id: ep.id, code: ep.code, name: ep.name, system_type: ep.system_type, is_active: ep.is_active, last_success_at: ep.last_success_at, last_failure_at: ep.last_failure_at, event_count: ee.length, success_count: ee.filter((e) => e.status === "SUCCEEDED").length, failed_count: ee.filter((e) => e.status === "FAILED" || e.status === "DEAD_LETTER").length, pending_count: ee.filter((e) => e.status === "PENDING").length };
      });
      const recent = (evts || []).filter((e) => e.status === "FAILED" || e.status === "DEAD_LETTER").slice(0, 5).map((e) => {
        const ep = eps?.find((x) => x.id === e.endpoint_id);
        return { event_no: e.event_no, endpoint_code: ep?.code ?? "unknown", event_type: e.event_type, last_error: e.last_error ?? "未知错误", created_at: e.created_at };
      });
      const ok = (sm?.events ?? 0) - (sm?.failed_events ?? 0);
      setHealth({ total_endpoints: sm?.endpoints ?? 0, active_endpoints: sm?.active_endpoints ?? 0, total_events: sm?.events ?? 0, success_rate: sm?.events ? Math.round(ok / sm.events * 100) : 0, dead_letter_count: sm?.events_by_status?.DEAD_LETTER ?? 0, recent_failures: recent, endpoints: epHealth });
    } catch (err) { setError(err instanceof Error ? err.message : "加载失败"); } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [reload]);
  if (!actor.isAuthenticated) {
    return (
      <div className="page-stack">
        <WorkspaceEmptyState
          icon={PlugZap}
          title="请先登录后查看集成监控"
          description="集成监控会展示端点健康度、失败事件和待处理死信，需要登录后再继续。"
          compact
        />
      </div>
    );
  }

  return (
    <div className="page-stack">
      <header className="page-header"><div><span className="page-kicker">PHASE 7 · INTEGRATION MONITOR</span><h1>集成监控</h1><p>实时监控 MES、QMS、机器人、材料系统集成端点的连接状态与事件处理情况。</p></div><button className="button button-secondary" onClick={() => void reload()} disabled={loading}><RefreshCw className={loading ? "spin" : ""} /> 刷新</button></header>
      {error ? <button className="message-banner message-error" onClick={() => setError("")}>{error}<X /></button> : null}
      {loading ? <div className="master-empty"><LoaderCircle className="spin" /> 正在加载集成监控数据...</div> : health ? <>
        <section className="module-stat-strip">
          <article><PlugZap /><span>活跃端点</span><strong>{health.active_endpoints}/{health.total_endpoints}</strong><small>集成连接</small></article>
          <article><CheckCircle2 /><span>处理成功率</span><strong>{health.success_rate}%</strong><small>{health.total_events} 个事件</small></article>
          <article><CircleAlert /><span>死信</span><strong>{health.dead_letter_count}</strong><small>需人工重放</small></article>
          <article><Activity /><span>最近失败</span><strong>{health.recent_failures.length}</strong><small>条待处理</small></article>
        </section>
        <div className="integration-monitor-grid">
          <section className="panel">
            <SectionHeader eyebrow="ENDPOINTS" title="端点状态" className="panel-heading" compact />
            <div className="master-table-wrap"><table className="master-table"><thead><tr><th>端点</th><th>类型</th><th>事件数</th><th>成功</th><th>失败</th><th>待处理</th><th>最近成功</th><th>状态</th></tr></thead><tbody>{health.endpoints.map((ep) => <tr key={ep.id}><td><strong>{ep.code}</strong><small>{ep.name}</small></td><td>{SYSTEM_ICONS[ep.system_type] ?? "🔌"} {ep.system_type}</td><td>{ep.event_count}</td><td className="cell-good">{ep.success_count}</td><td className={ep.failed_count > 0 ? "cell-warn" : ""}>{ep.failed_count}</td><td className={ep.pending_count > 0 ? "cell-warn" : ""}>{ep.pending_count}</td><td><small>{timeSince(ep.last_success_at)}</small></td><td><span className={`record-status ${ep.is_active ? "status-on" : "status-off"}`}>{ep.is_active ? "在线" : "离线"}</span></td></tr>)}</tbody></table>{!health.endpoints.length ? <WorkspaceEmptyState icon={PlugZap} title="暂无集成端点" description="先在集成与任务中心维护端点后，这里才会展示健康度与事件统计。" compact /> : null}</div>
          </section>
          <section className="panel">
            <SectionHeader
              eyebrow="RECENT FAILURES"
              title="近期失败事件"
              className="panel-heading"
              compact
              badge={<span className={`record-status ${health.recent_failures.length > 0 ? "status-off" : "status-on"}`}>{health.recent_failures.length > 0 ? `${health.recent_failures.length} 条` : "无失败"}</span>}
            />
            {health.recent_failures.length > 0 ? (
              <div className="failure-list">
                {health.recent_failures.map((f, i) => <div className="failure-card" key={i}><CircleAlert className="alert-icon" /><div className="failure-body"><div className="failure-header"><strong className="mono">{f.endpoint_code}</strong><span>{f.event_type}</span><small>{timeSince(f.created_at)}</small></div><p className="failure-error">{f.last_error}</p></div></div>)}
              </div>
            ) : (
              <WorkspaceEmptyState icon={CheckCircle2} title="最近未发现失败事件" description="最近的集成事件处理状态稳定，当前没有需要人工复盘的失败记录。" compact />
            )}
          </section>
        </div>
      </> : <WorkspaceEmptyState icon={PlugZap} title="暂无集成监控数据" description="当前还没有可用于统计的端点和事件数据，补齐集成端点后这里会自动形成监控视图。" />}
    </div>
  );
}
