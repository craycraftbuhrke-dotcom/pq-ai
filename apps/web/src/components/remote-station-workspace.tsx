"use client";

import { Check, CircleAlert, LoaderCircle, Network, Plus, RefreshCw, Send, ShieldCheck } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { ModalShell } from "@/components/modal-shell";
import { stageLabel } from "@/lib/display-labels";

type Factory = { id: string; code: string; name: string };
type Program = { id: string; program_code: string; name: string; factory_id: string; process_stage: string; station_code: string; station_name: string };
type ProgramVersion = { id: string; spray_program_id: string; version: string; status: string; program: Program };
type Connection = {
  id: string; connection_code: string; name: string; factory_id: string; station_code: string; station_name: string; process_stage: string;
  host: string; port: number; adapter_mode: string; agent_id: string; status: string; operating_mode: string; last_seen_at?: string | null;
};
type Release = {
  id: string; release_no: string; connection_id: string; base_program_version_id: string; candidate_program_version_id: string; status: string;
  risk_summary: string; requested_by: string; approved_by?: string | null; requested_at: string; last_error?: string | null;
};
type Reconciliation = {
  id: string; status: string; generated_at: string;
  diff_payload: { summary: { parameterCount: number; sameCount: number; differentCount: number; missingCount: number }; rows: Array<{ parameter: string; cloud?: number | string | null; virtualLine?: number | string | null; upperComputer?: number | string | null; status: string }> };
};

const STAGES = ["MIDCOAT_EXT", "BASECOAT_1", "BASECOAT_2", "CLEARCOAT_1", "CLEARCOAT_2"];

function statusLabel(value: string) {
  return ({ DRAFT: "草稿", ACTIVE: "已启用", REJECTED: "已驳回", SUBMITTED: "待审批", APPROVED: "审批通过", STAGED: "已传到上位机暂存区", LOCAL_CONFIRMED: "现场已确认", WAITING_READBACK: "已交付，等待回读", APPLIED: "已提交", VERIFIED: "回读一致", FAILED: "执行失败", READ_ONLY: "只读", APPROVED_RELEASES_ONLY: "仅允许已审批发布", CONSISTENT: "三方一致", DIFFERENT: "存在差异" } as Record<string, string>)[value] ?? value;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  const payload = (await response.json().catch(() => ({}))) as T & { error?: unknown; detail?: unknown };
  if (!response.ok) {
    const detail = payload.error ?? payload.detail;
    const message = typeof detail === "string"
      ? detail
      : detail && typeof detail === "object" && "message" in detail && typeof detail.message === "string"
        ? detail.message
        : `操作失败（${response.status}）`;
    throw new Error(message);
  }
  return payload;
}

export function RemoteStationWorkspace() {
  const [factories, setFactories] = useState<Factory[]>([]);
  const [versions, setVersions] = useState<ProgramVersion[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [releases, setReleases] = useState<Release[]>([]);
  const [reconciliations, setReconciliations] = useState<Reconciliation[]>([]);
  const [connectionId, setConnectionId] = useState("");
  const [versionId, setVersionId] = useState("");
  const [baseVersionId, setBaseVersionId] = useState("");
  const [candidateVersionId, setCandidateVersionId] = useState("");
  const [riskSummary, setRiskSummary] = useState("");
  const [showConnectionForm, setShowConnectionForm] = useState(false);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    const [nextFactories, nextPrograms, nextConnections, nextReleases] = await Promise.all([
      request<Factory[]>("/api/master-data/factories"),
      request<Program[]>("/api/process/spray-programs"),
      request<Connection[]>("/api/remote-stations/connections"),
      request<Release[]>("/api/remote-stations/releases"),
    ]);
    const nextVersions = (await Promise.all(nextPrograms.map(async (program) => (await request<Omit<ProgramVersion, "program">[]>(`/api/process/spray-programs/${program.id}/versions`)).map((version) => ({ ...version, program }))))).flat();
    setFactories(nextFactories); setVersions(nextVersions); setConnections(nextConnections); setReleases(nextReleases);
    setConnectionId((current) => current || nextConnections[0]?.id || "");
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload().catch((loadError) => setError(loadError instanceof Error ? loadError.message : "远程工作站加载失败"));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  const selected = connections.find((item) => item.id === connectionId);
  const availableVersions = useMemo(() => versions.filter((item) => selected && item.program.factory_id === selected.factory_id && item.program.process_stage === selected.process_stage && item.program.station_code === selected.station_code), [selected, versions]);
  const selectedReleases = releases.filter((item) => item.connection_id === connectionId);
  const latestReconciliation = reconciliations[0];

  useEffect(() => {
    if (!connectionId) return;
    void request<Reconciliation[]>(`/api/remote-stations/connections/${connectionId}/reconciliations`).then(setReconciliations).catch(() => setReconciliations([]));
  }, [connectionId]);

  const effectiveVersionId = availableVersions.some((item) => item.id === versionId) ? versionId : availableVersions[0]?.id || "";
  const effectiveBaseVersionId = availableVersions.some((item) => item.id === baseVersionId) ? baseVersionId : availableVersions.find((item) => item.status === "ACTIVE")?.id || availableVersions[0]?.id || "";
  const effectiveCandidateVersionId = availableVersions.some((item) => item.id === candidateVersionId) ? candidateVersionId : availableVersions.find((item) => item.status === "DRAFT")?.id || "";

  function selectConnection(nextConnectionId: string) {
    setConnectionId(nextConnectionId);
    setReconciliations([]);
  }

  async function runAction(key: string, operation: () => Promise<unknown>, message: string) {
    setBusy(key); setError(""); setNotice("");
    try { await operation(); setNotice(message); await reload(); return true; }
    catch (operationError) { setError(operationError instanceof Error ? operationError.message : "操作失败"); return false; }
    finally { setBusy(""); }
  }

  async function createConnection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    const succeeded = await runAction("connection-create", () => request("/api/remote-stations/connections", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
      connection_code: String(data.get("connection_code")), name: String(data.get("name")), factory_id: String(data.get("factory_id")),
      process_stage: String(data.get("process_stage")), station_code: String(data.get("station_code")), station_name: String(data.get("station_name")),
      host: String(data.get("host")), port: Number(data.get("port")), adapter_mode: String(data.get("adapter_mode")), agent_id: String(data.get("agent_id")), server_name: String(data.get("server_name")) || null,
      client_certificate_ref: String(data.get("client_certificate_ref")) || null, client_private_key_ref: String(data.get("client_private_key_ref")) || null, trusted_ca_ref: String(data.get("trusted_ca_ref")) || null,
    }) }), "连接草稿已保存，当前仍为只读且未启用");
    if (succeeded) setShowConnectionForm(false);
  }

  async function capture(source: "CLOUD" | "VIRTUAL_LINE") {
    if (!selected || !effectiveVersionId) return;
    await runAction(`capture-${source}`, () => request(`/api/remote-stations/connections/${selected.id}/snapshots/capture`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source_type: source, program_version_id: effectiveVersionId }) }), source === "CLOUD" ? "已记录云端当前完整刷子表" : "已记录虚拟生产线当前完整刷子表");
  }

  async function createRelease(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selected) return;
    const succeeded = await runAction("release-create", () => request("/api/remote-stations/releases", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ connection_id: selected.id, base_program_version_id: effectiveBaseVersionId, candidate_program_version_id: effectiveCandidateVersionId, risk_summary: riskSummary }) }), "发布草稿已生成，尚未发送到上位机");
    if (succeeded) setRiskSummary("");
  }

  async function releaseAction(release: Release, action: string) {
    const labels: Record<string, string> = { submit: "已提交审批，远程端未发生变化", approve: "审批通过，仍未发送到远程端", reject: "已驳回", stage: "完整刷子表已传到上位机暂存区，未应用", refresh: "已刷新现场确认状态", commit: "已执行正式交付，请以当前状态确认是否仍待回读", "verify-readback": "已重新读取并核对上位机参数" };
    await runAction(`${release.id}-${action}`, () => request(`/api/remote-stations/releases/${release.id}/${action}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: action === "stage" || action === "refresh" || action === "commit" || action === "verify-readback" ? "{}" : JSON.stringify({ comment: "已在远程工作站页面确认" }) }), labels[action]);
  }

  return (
    <div className="remote-station-workspace">
      <div className="remote-safety-banner"><ShieldCheck /><div><strong>系统数据与生产上位机严格隔离</strong><span>页面修改只生成云端草稿。只有“提交审批 → 审批通过 → 传到暂存区 → 现场确认 → 正式提交 → 回读一致”全部完成，生产端才会改变。</span></div></div>
      <section className="remote-station-layout">
        <aside className="remote-connection-list">
          <div className="program-subheading"><div><span className="eyebrow">目标设备</span><h3>上位机连接</h3></div><button className="button button-primary" onClick={() => setShowConnectionForm(true)}><Plus /> 新建</button></div>
          {connections.map((connection) => <button key={connection.id} className={`remote-connection-card ${connection.id === connectionId ? "selected" : ""}`} onClick={() => selectConnection(connection.id)}><span><strong>{connection.name}</strong><small>{stageLabel(connection.process_stage)} · {connection.station_name}</small></span><em>{statusLabel(connection.status)}</em></button>)}
          {!connections.length ? <div className="program-empty">尚未配置目标上位机</div> : null}
        </aside>
        <main className="remote-station-main">
          {selected ? <>
            <section className="remote-summary-card"><div><span className="eyebrow">当前连接</span><h3>{selected.name}</h3><p>{selected.host}:{selected.port} · 通讯程序 {selected.agent_id} · {statusLabel(selected.operating_mode)}</p></div><div className="remote-actions"><button className="button button-secondary" disabled={Boolean(busy)} onClick={() => void runAction("test", () => request(`/api/remote-stations/connections/${selected.id}/test`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }), "连接与通讯程序身份校验通过，全程未修改参数")}><Network /> 测试只读连接</button>{selected.status === "DRAFT" ? <button className="button button-primary" disabled={Boolean(busy)} onClick={() => void runAction("approve-connection", () => request(`/api/remote-stations/connections/${selected.id}/approval`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision: "APPROVE", comment: "连接配置已复核" }) }), "连接已审批启用")}><Check /> 审批启用</button> : null}</div></section>

            <section className="remote-panel"><div className="program-subheading"><div><span className="eyebrow">三方数据</span><h3>云端、虚拟线、上位机对账</h3></div><RefreshCw /></div><label className="form-field"><span>选择要登记的完整程序版本</span><select value={effectiveVersionId} onChange={(event) => setVersionId(event.target.value)}>{availableVersions.map((item) => <option key={item.id} value={item.id}>{item.program.program_code} · {item.version} · {statusLabel(item.status)}</option>)}</select></label><div className="remote-actions"><button className="button button-secondary" disabled={!effectiveVersionId || Boolean(busy)} onClick={() => void capture("CLOUD")}>登记为云端版本</button><button className="button button-secondary" disabled={!effectiveVersionId || Boolean(busy)} onClick={() => void capture("VIRTUAL_LINE")}>登记为虚拟线版本</button><button className="button button-secondary" disabled={selected.status !== "ACTIVE" || Boolean(busy)} onClick={() => void runAction("pull-upper", () => request(`/api/remote-stations/connections/${selected.id}/snapshots/pull-upper`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }), "已从上位机只读回传最新完整刷子表")}>只读拉取上位机</button><button className="button button-primary" disabled={Boolean(busy)} onClick={() => void runAction("reconcile", async () => { const result = await request<Reconciliation>(`/api/remote-stations/connections/${selected.id}/reconciliations`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }); setReconciliations((current) => [result, ...current]); }, "三方差异已重新计算")}>查看三方差异</button></div>
              {latestReconciliation ? <div className="remote-diff-summary"><strong>{statusLabel(latestReconciliation.status)}</strong><span>一致 {latestReconciliation.diff_payload.summary.sameCount}</span><span>不同 {latestReconciliation.diff_payload.summary.differentCount}</span><span>缺少 {latestReconciliation.diff_payload.summary.missingCount}</span></div> : null}
              {latestReconciliation?.diff_payload.rows.filter((row) => row.status !== "SAME").slice(0, 20).map((row) => <div className="remote-diff-row" key={row.parameter}><strong>{row.parameter}</strong><span>云端 {row.cloud ?? "无"}</span><span>虚拟线 {row.virtualLine ?? "无"}</span><span>上位机 {row.upperComputer ?? "无"}</span></div>)}
            </section>

            <section className="remote-panel"><div className="program-subheading"><div><span className="eyebrow">受控发布</span><h3>把完整新版本提交到上位机</h3></div><Send /></div><form className="remote-release-form" onSubmit={(event) => void createRelease(event)}><label className="form-field"><span>上位机当前原版本</span><select required value={effectiveBaseVersionId} onChange={(event) => setBaseVersionId(event.target.value)}>{availableVersions.map((item) => <option key={item.id} value={item.id}>{item.program.program_code} · {item.version}</option>)}</select></label><label className="form-field"><span>准备发布的新版本</span><select required value={effectiveCandidateVersionId} onChange={(event) => setCandidateVersionId(event.target.value)}><option value="">请选择完整草稿版本</option>{availableVersions.filter((item) => item.status === "DRAFT").map((item) => <option key={item.id} value={item.id}>{item.program.program_code} · {item.version}</option>)}</select></label><label className="form-field form-field-wide"><span>调整原因与风险说明</span><textarea required value={riskSummary} onChange={(event) => setRiskSummary(event.target.value)} placeholder="说明要改善的点位、质量问题、调整依据和回退条件" /></label><button className="button button-primary" disabled={!effectiveBaseVersionId || !effectiveCandidateVersionId || !riskSummary || Boolean(busy)}>生成发布草稿</button></form>
              <div className="remote-release-list">{selectedReleases.map((release) => <article key={release.id}><div><span className="record-status">{statusLabel(release.status)}</span><strong>{release.release_no}</strong><small>{release.risk_summary}</small><small>申请人 {release.requested_by}{release.approved_by ? ` · 审批人 ${release.approved_by}` : ""}</small>{release.last_error ? <small className="form-error">{release.last_error}</small> : null}</div><div className="remote-actions">{release.status === "DRAFT" ? <button className="button button-secondary" onClick={() => void releaseAction(release, "submit")}>提交审批</button> : null}{release.status === "SUBMITTED" ? <><button className="button button-primary" onClick={() => void releaseAction(release, "approve")}>审批通过</button><button className="button button-secondary" onClick={() => void releaseAction(release, "reject")}>驳回</button></> : null}{release.status === "APPROVED" ? <button className="button button-primary" onClick={() => void releaseAction(release, "stage")}>传到上位机暂存区</button> : null}{release.status === "STAGED" ? <button className="button button-secondary" onClick={() => void releaseAction(release, "refresh")}>检查现场确认</button> : null}{release.status === "LOCAL_CONFIRMED" ? <button className="button button-primary" onClick={() => void releaseAction(release, "commit")}>正式提交并回读</button> : null}{release.status === "WAITING_READBACK" || release.status === "APPLIED" ? <button className="button button-secondary" onClick={() => void releaseAction(release, "verify-readback")}>重新读取并核对</button> : null}</div></article>)}</div>
            </section>
          </> : <div className="program-empty">请选择一个目标上位机连接</div>}
          {error ? <div className="form-error"><CircleAlert /> {error}</div> : null}{notice ? <div className="form-success">{notice}</div> : null}{busy ? <div className="freshness"><LoaderCircle className="spin" /> 正在处理，请勿重复操作</div> : null}
        </main>
      </section>
      {showConnectionForm ? <ModalShell eyebrow="目标工作站" title="新建上位机连接草稿" description="这里只登记连接和证书配置名，不保存密码、证书或私钥内容。新建后默认只读，必须另行审批才能发布。" onClose={() => setShowConnectionForm(false)} busy={busy === "connection-create"}><form onSubmit={(event) => void createConnection(event)}><div className="form-grid"><label className="form-field"><span>连接编号</span><input name="connection_code" required /></label><label className="form-field"><span>连接名称</span><input name="name" required placeholder="例如：清漆二站生产上位机" /></label><label className="form-field"><span>工厂</span><select name="factory_id" required>{factories.map((factory) => <option key={factory.id} value={factory.id}>{factory.code} / {factory.name}</option>)}</select></label><label className="form-field"><span>喷涂工段</span><select name="process_stage" required>{STAGES.map((stage) => <option key={stage} value={stage}>{stageLabel(stage)}</option>)}</select></label><label className="form-field"><span>工作站编号</span><input name="station_code" required /></label><label className="form-field"><span>工作站名称</span><input name="station_name" required /></label><label className="form-field"><span>上位机地址</span><input name="host" required placeholder="由工厂网络管理员提供" /></label><label className="form-field"><span>通信端口</span><input name="port" type="number" min="1" max="65535" required defaultValue="9443" /></label><label className="form-field"><span>上位机通讯程序编号</span><input name="agent_id" required /></label><label className="form-field"><span>参数交付方式</span><select name="adapter_mode"><option value="SIMULATOR">联调模拟，不写生产</option><option value="FILE_DROP">交给厂家认可的文件导入目录</option><option value="DURR_APPROVED_ADAPTER">Dürr/工厂认可适配器</option></select></label><details className="form-field form-field-wide ai-advanced-details"><summary>安全证书配置（由运维人员填写）</summary><div className="form-grid"><label className="form-field"><span>服务端证书名称</span><input name="server_name" /></label><label className="form-field"><span>客户端证书配置名</span><input name="client_certificate_ref" pattern="[A-Z][A-Z0-9_]*" /></label><label className="form-field"><span>客户端私钥配置名</span><input name="client_private_key_ref" pattern="[A-Z][A-Z0-9_]*" /></label><label className="form-field"><span>受信任根证书配置名</span><input name="trusted_ca_ref" pattern="[A-Z][A-Z0-9_]*" /></label></div></details></div><div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setShowConnectionForm(false)}>取消</button><button className="button button-primary" disabled={busy === "connection-create"}>{busy === "connection-create" ? <LoaderCircle className="spin" /> : <Check />} 保存只读草稿</button></div></form></ModalShell> : null}
    </div>
  );
}
