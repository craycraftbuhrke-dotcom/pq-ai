"use client";

import { Cable, LoaderCircle, Pencil, Plus, RefreshCw, ShieldAlert, Trash2, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { BulkDataActions } from "@/components/bulk-data-actions";
import { physicalDeleteDisabledMessage } from "@/lib/delete-policy";

type Kind =
  | "robots"
  | "controllers"
  | "atomizers"
  | "device-configurations"
  | "trajectory-programs"
  | "path-segments"
  | "contribution-versions"
  | "contribution-entries"
  | "device-executions";
type FormState = Record<string, string>;
type Resource = {
  id: string;
  factory_id?: string;
  program_version_id?: string;
  trajectory_program_id?: string;
  contribution_version_id?: string;
  production_stage_run_id?: string;
  device_configuration_id?: string;
  robot_id?: string;
  atomizer_id?: string;
  controller_id?: string | null;
  measurement_point_id?: string;
  brush_id?: string | null;
  part_id?: string | null;
  path_segment_id?: string | null;
  code?: string;
  name?: string;
  model?: string;
  serial_no?: string;
  status?: string;
  version?: string;
  configuration_version?: string;
  trajectory_code?: string;
  checksum?: string;
  executed_checksum?: string;
  segment_no?: number;
  target_family?: string;
  method?: string;
  source_key?: string;
  bell_cup_type?: string | null;
  bell_cup_code?: string | null;
  software_version?: string | null;
  controller_software_version?: string | null;
  tcp_name?: string | null;
  coordinate_system?: string | null;
  configured_speed?: number | null;
  speed_unit?: string | null;
  trigger_state?: string;
  overlap_ratio?: number;
  contribution_weight?: number;
  validation_score?: number | null;
  approved_by?: string | null;
  source_uri?: string | null;
  evidence_uri?: string | null;
  remark?: string | null;
};
type Named = { id: string; code?: string; name?: string; program_code?: string; version?: string; brush_no?: string };
type Program = Named & { program_code: string };
type RelationshipMaps = {
  factories: Map<string, Named>;
  versions: Map<string, Named>;
  brushes: Map<string, Named>;
  points: Map<string, Named>;
  parts: Map<string, Named>;
  robots: Map<string, Named>;
  controllers: Map<string, Named>;
  atomizers: Map<string, Named>;
  trajectories: Map<string, Named>;
  configurations: Map<string, Named>;
  contributionVersions: Map<string, Named>;
  segments: Map<string, Named>;
};
type Summary = {
  robots: number;
  controllers: number;
  atomizers: number;
  active_device_configurations: number;
  trajectory_programs: number;
  path_segments: number;
  active_contribution_versions: number;
  contribution_entries: number;
  device_executions: number;
  checksum_mismatches: number;
};

const kinds: Array<[Kind, string]> = [
  ["robots", "机器人"],
  ["controllers", "应用控制器"],
  ["atomizers", "静电旋杯"],
  ["device-configurations", "程序设备配置"],
  ["trajectory-programs", "轨迹程序"],
  ["path-segments", "路径段"],
  ["contribution-versions", "贡献版本"],
  ["contribution-entries", "贡献条目"],
  ["device-executions", "生产执行"],
];
const statusOptions: Array<[string, string]> = [["ACTIVE", "生效"], ["APPROVED", "已批准"], ["DRAFT", "草稿"], ["RETIRED", "已退役"]];
const deviceStatusOptions: Array<[string, string]> = [["ACTIVE", "在用"], ["MAINTENANCE", "维护"], ["RETIRED", "退役"]];
const qualityOptions: Array<[string, string]> = [["ORANGE_PEEL", "橘皮"], ["COLOR_DIFFERENCE", "色差/效应"], ["THICKNESS", "膜厚"]];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new Error(payload.error ?? `请求失败（${response.status}）`);
  return payload;
}

function label(item?: Named): string {
  if (!item) return "未关联";
  return `${item.code ?? item.program_code ?? item.brush_no ?? item.version ?? item.id} / ${item.name ?? item.version ?? item.id.slice(0, 8)}`;
}

export function DurrTrajectoryPanel() {
  const [kind, setKind] = useState<Kind>("robots");
  const [resources, setResources] = useState<Record<Kind, Resource[]>>(() => ({
    robots: [],
    controllers: [],
    atomizers: [],
    "device-configurations": [],
    "trajectory-programs": [],
    "path-segments": [],
    "contribution-versions": [],
    "contribution-entries": [],
    "device-executions": [],
  }));
  const [summary, setSummary] = useState<Summary | null>(null);
  const [factories, setFactories] = useState<Named[]>([]);
  const [versions, setVersions] = useState<Named[]>([]);
  const [brushes, setBrushes] = useState<Named[]>([]);
  const [points, setPoints] = useState<Named[]>([]);
  const [parts, setParts] = useState<Named[]>([]);
  const [modal, setModal] = useState<Resource | "new" | null>(null);
  const [form, setForm] = useState<FormState>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "error" | "success"; text: string } | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [nextSummary, robots, controllers, atomizers, configurations, trajectories, segments, contributionVersions, contributionEntries, executions, nextFactories, nextPrograms, nextPoints, nextParts] = await Promise.all([
        request<Summary>("/api/process/robot-governance/summary"),
        request<Resource[]>("/api/process/robot-governance/robots"),
        request<Resource[]>("/api/process/robot-governance/controllers"),
        request<Resource[]>("/api/process/robot-governance/atomizers"),
        request<Resource[]>("/api/process/robot-governance/device-configurations"),
        request<Resource[]>("/api/process/robot-governance/trajectory-programs"),
        request<Resource[]>("/api/process/robot-governance/path-segments"),
        request<Resource[]>("/api/process/robot-governance/contribution-versions"),
        request<Resource[]>("/api/process/robot-governance/contribution-entries"),
        request<Resource[]>("/api/process/robot-governance/device-executions"),
        request<Named[]>("/api/master-data/factories"),
        request<Program[]>("/api/process/spray-programs"),
        request<Named[]>("/api/master-data/measurement-points"),
        request<Named[]>("/api/master-data/parts"),
      ]);
      const versionGroups = await Promise.all(nextPrograms.map((program) => request<Named[]>(`/api/process/spray-programs/${program.id}/versions`)));
      const nextVersions = versionGroups.flat();
      const brushGroups = await Promise.all(nextVersions.map((version) => request<Named[]>(`/api/process/program-versions/${version.id}/brushes`)));
      setSummary(nextSummary);
      setResources({
        robots,
        controllers,
        atomizers,
        "device-configurations": configurations,
        "trajectory-programs": trajectories,
        "path-segments": segments,
        "contribution-versions": contributionVersions,
        "contribution-entries": contributionEntries,
        "device-executions": executions,
      });
      setFactories(nextFactories);
      setVersions(nextVersions);
      setBrushes(brushGroups.flat());
      setPoints(nextPoints);
      setParts(nextParts);
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "Dürr 治理数据加载失败" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  const maps = useMemo(() => {
    const map = (items: Named[]) => new Map(items.map((item) => [item.id, item]));
    return {
      factories: map(factories),
      versions: map(versions),
      brushes: map(brushes),
      points: map(points),
      parts: map(parts),
      robots: map(resources.robots),
      controllers: map(resources.controllers),
      atomizers: map(resources.atomizers),
      trajectories: map(resources["trajectory-programs"]),
      configurations: map(resources["device-configurations"]),
      contributionVersions: map(resources["contribution-versions"]),
      segments: map(resources["path-segments"]),
    };
  }, [brushes, factories, parts, points, resources, versions]);

  function open(record?: Resource) {
    setModal(record ?? "new");
    const nextForm = initialForm(kind, record);
    if (!record) {
      if (["robots", "controllers", "atomizers"].includes(kind)) {
        nextForm.factory_id = factories[0]?.id ?? "";
      } else if (kind === "device-configurations") {
        nextForm.program_version_id = versions[0]?.id ?? "";
        nextForm.robot_id = resources.robots[0]?.id ?? "";
        nextForm.atomizer_id = resources.atomizers[0]?.id ?? "";
        nextForm.controller_id = resources.controllers[0]?.id ?? "";
      } else if (kind === "trajectory-programs" || kind === "contribution-versions") {
        nextForm.program_version_id = versions[0]?.id ?? "";
      } else if (kind === "path-segments") {
        nextForm.trajectory_program_id = resources["trajectory-programs"][0]?.id ?? "";
      } else if (kind === "contribution-entries") {
        nextForm.contribution_version_id = resources["contribution-versions"][0]?.id ?? "";
        nextForm.measurement_point_id = points[0]?.id ?? "";
      }
    }
    setForm(nextForm);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!modal || kind === "device-executions") return;
    setSubmitting(true);
    setMessage(null);
    try {
      const editing = modal !== "new";
      await request(`/api/process/robot-governance/${kind}${editing ? `/${modal.id}` : ""}`, {
        method: editing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildBody(kind, form)),
      });
      setMessage({ type: "success", text: `${kindName(kind)}已${editing ? "更新" : "创建"}并写入 MySQL` });
      setModal(null);
      await reload();
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "保存失败" });
    } finally {
      setSubmitting(false);
    }
  }

  function remove(_record: Resource) {
    void _record;
    setMessage({ type: "error", text: `${kindName(kind)}不能物理删除。${physicalDeleteDisabledMessage}` });
  }

  function bulkResult(message: string, type: "success" | "error") {
    setMessage({ type, text: message });
  }

  const rows = resources[kind];
  return (
    <div className="measurement-governance durr-governance">
      {message ? <button className={`message-banner message-${message.type}`} onClick={() => setMessage(null)}>{message.text}<X /></button> : null}
      <section className="quality-analytics-stat-grid">
        <article><span>机器人 / 控制器 / 旋杯</span><strong>{summary?.robots ?? 0} / {summary?.controllers ?? 0} / {summary?.atomizers ?? 0}</strong><small>设备身份、型号、序列号和软件版本受控</small></article>
        <article><span>生效设备配置 / 轨迹</span><strong>{summary?.active_device_configurations ?? 0} / {summary?.trajectory_programs ?? 0}</strong><small>程序版本绑定设备组合与轨迹校验和</small></article>
        <article><span>路径段 / 生效贡献版本</span><strong>{summary?.path_segments ?? 0} / {summary?.active_contribution_versions ?? 0}</strong><small>按目标族维护点位贡献血缘</small></article>
        <article className={(summary?.checksum_mismatches ?? 0) > 0 ? "stat-alert" : ""}><span>生产执行 / 校验和异常</span><strong>{summary?.device_executions ?? 0} / {summary?.checksum_mismatches ?? 0}</strong><small>异常执行阻断受控点位特征构建</small></article>
      </section>
      <div className="governance-toolbar">
        <div className="master-tabs">
          {kinds.map(([key, text]) => <button key={key} className={kind === key ? "master-tab master-tab-active" : "master-tab"} onClick={() => setKind(key)}>{text}<span>{resources[key].length}</span></button>)}
        </div>
        <div className="page-actions">
          <button className="button button-secondary" onClick={() => void reload()} disabled={loading}><RefreshCw className={loading ? "spin" : ""} />刷新</button>
          <BulkDataActions
            resourceKey={`robot-governance.${kind}`}
            resourceLabel={kindName(kind)}
            disabled={loading || submitting}
            onImported={reload}
            onResult={bulkResult}
          />
          {kind !== "device-executions" ? <button className="button button-primary" onClick={() => open()}><Plus />新建{kindName(kind)}</button> : null}
        </div>
      </div>
      <div className="master-table-wrap">
        <table className="master-table governance-table durr-table">
          <thead><tr><th>编号 / 名称</th><th>受控关系</th><th>版本 / 状态</th><th>工程与追溯详情</th><th>操作</th></tr></thead>
          <tbody>{rows.map((row) => <tr key={row.id}>
            <td><strong>{primary(row)}</strong><small>{row.name ?? row.source_key ?? row.id.slice(0, 12)}</small></td>
            <td>{relationship(kind, row, maps)}</td>
            <td><span className={row.status === "CHECKSUM_MISMATCH" ? "status-badge status-danger" : "status-badge"}>{row.status ?? row.version ?? row.configuration_version ?? "受控"}</span></td>
            <td>{detail(kind, row)}</td>
            <td>{kind === "device-executions" ? <span className="readonly-note">系统实绩</span> : <div className="row-actions"><button className="icon-button" onClick={() => open(row)} aria-label={`编辑${kindName(kind)}`}><Pencil /></button><button className="icon-button icon-button-danger" onClick={() => void remove(row)} aria-label={`删除${kindName(kind)}`}><Trash2 /></button></div>}</td>
          </tr>)}</tbody>
        </table>
        {!rows.length ? <div className="large-empty"><Cable />暂无{kindName(kind)}，请按设备、配置、轨迹、贡献版本顺序建立受控链路。</div> : null}
      </div>
      {modal ? <div className="modal-backdrop" role="presentation" onMouseDown={() => !submitting && setModal(null)}><section className="modal-card quality-modal" role="dialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}><div className="modal-heading"><div><span className="eyebrow">DÜRR ROBOT & TRAJECTORY GOVERNANCE</span><h2>{modal === "new" ? "新建" : "编辑"}{kindName(kind)}</h2></div><button className="icon-button" onClick={() => setModal(null)} aria-label="关闭"><X /></button></div><form onSubmit={submit}><div className="form-grid">{renderFields(kind, form, setForm, { factories, versions, brushes, points, parts, resources })}</div><div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setModal(null)}>取消</button><button className="button button-primary" disabled={submitting}>{submitting ? <LoaderCircle className="spin" /> : null}保存到 MySQL</button></div></form></section></div> : null}
      {(summary?.checksum_mismatches ?? 0) > 0 ? <div className="governance-warning"><ShieldAlert />存在轨迹校验和异常的生产执行。相关工序不能进入 AI 训练、预测、诊断或推荐。</div> : null}
    </div>
  );
}

function kindName(kind: Kind): string {
  return kinds.find(([key]) => key === kind)?.[1] ?? kind;
}

function primary(row: Resource): string {
  if (row.trajectory_code) return `${row.trajectory_code}:${row.version}`;
  if (row.configuration_version) return `设备配置 ${row.configuration_version}`;
  if (row.segment_no) return `SEG-${row.segment_no}`;
  if (row.target_family) return `${row.target_family}:${row.version}`;
  if (row.executed_checksum) return row.executed_checksum.slice(0, 16);
  return row.code ?? row.source_key ?? row.id.slice(0, 12);
}

function relationship(kind: Kind, row: Resource, maps: RelationshipMaps): string {
  if (["robots", "controllers", "atomizers"].includes(kind)) return label(maps.factories.get(row.factory_id ?? ""));
  if (kind === "device-configurations" || kind === "trajectory-programs" || kind === "contribution-versions") return label(maps.versions.get(row.program_version_id ?? ""));
  if (kind === "path-segments") return `${label(maps.trajectories.get(row.trajectory_program_id ?? ""))} · ${label(maps.brushes.get(row.brush_id ?? ""))}`;
  if (kind === "contribution-entries") return `${label(maps.contributionVersions.get(row.contribution_version_id ?? ""))} · ${label(maps.points.get(row.measurement_point_id ?? ""))}`;
  return `${label(maps.configurations.get(row.device_configuration_id ?? ""))} · ${label(maps.trajectories.get(row.trajectory_program_id ?? ""))}`;
}

function detail(kind: Kind, row: Resource): string {
  if (kind === "robots") return `${row.model} · SN ${row.serial_no} · 控制软件 ${row.controller_software_version ?? "待维护"}`;
  if (kind === "controllers") return `${row.model} · SN ${row.serial_no} · 软件 ${row.software_version ?? "待维护"}`;
  if (kind === "atomizers") return `${row.model} · SN ${row.serial_no} · 杯型 ${row.bell_cup_type ?? row.bell_cup_code ?? "待维护"}`;
  if (kind === "device-configurations") return `机器人 ${row.robot_id?.slice(0, 8)} · 旋杯 ${row.atomizer_id?.slice(0, 8)} · 控制器 ${row.controller_id?.slice(0, 8)}`;
  if (kind === "trajectory-programs") return `checksum ${row.checksum?.slice(0, 18)} · TCP ${row.tcp_name ?? "待维护"} · ${row.coordinate_system ?? "坐标系待维护"}`;
  if (kind === "path-segments") return `${row.configured_speed ?? "待维护"} ${row.speed_unit ?? ""} · trigger ${row.trigger_state} · ${label(row.part_id ? { id: row.part_id } : undefined)}`;
  if (kind === "contribution-versions") return `${row.method} · 审批人 ${row.approved_by ?? "待维护"} · ${row.evidence_uri ?? "证据待维护"}`;
  if (kind === "contribution-entries") return `重叠率 ${percent(row.overlap_ratio)} · 权重 ${percent(row.contribution_weight)} · 验证 ${percent(row.validation_score)}`;
  return `批准 ${row.checksum?.slice(0, 12) ?? "—"} · 实际 ${row.executed_checksum?.slice(0, 12) ?? "—"}`;
}

function percent(value?: number | null): string {
  return value == null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function initialForm(kind: Kind, record?: Resource): FormState {
  if (kind === "robots") return { factory_id: record?.factory_id ?? "", code: record?.code ?? "", name: record?.name ?? "", model: record?.model ?? "", serial_no: record?.serial_no ?? "", controller_software_version: record?.controller_software_version ?? "", status: record?.status ?? "ACTIVE", source_uri: record?.source_uri ?? "", remark: record?.remark ?? "" };
  if (kind === "controllers") return { factory_id: record?.factory_id ?? "", code: record?.code ?? "", name: record?.name ?? "", model: record?.model ?? "", serial_no: record?.serial_no ?? "", software_version: record?.software_version ?? "", status: record?.status ?? "ACTIVE", source_uri: record?.source_uri ?? "", remark: record?.remark ?? "" };
  if (kind === "atomizers") return { factory_id: record?.factory_id ?? "", controller_id: record?.controller_id ?? "", code: record?.code ?? "", name: record?.name ?? "", model: record?.model ?? "", serial_no: record?.serial_no ?? "", bell_cup_type: record?.bell_cup_type ?? "", bell_cup_code: record?.bell_cup_code ?? "", status: record?.status ?? "ACTIVE", source_uri: record?.source_uri ?? "", remark: record?.remark ?? "" };
  if (kind === "device-configurations") return { program_version_id: record?.program_version_id ?? "", robot_id: record?.robot_id ?? "", atomizer_id: record?.atomizer_id ?? "", controller_id: record?.controller_id ?? "", configuration_version: record?.configuration_version ?? "1.0", status: record?.status ?? "DRAFT", approved_by: record?.approved_by ?? "", source_uri: record?.source_uri ?? "", remark: record?.remark ?? "" };
  if (kind === "trajectory-programs") return { program_version_id: record?.program_version_id ?? "", trajectory_code: record?.trajectory_code ?? "", name: record?.name ?? "", version: record?.version ?? "1.0", checksum: record?.checksum ?? "", coordinate_system: record?.coordinate_system ?? "", tcp_name: record?.tcp_name ?? "", status: record?.status ?? "DRAFT", approved_by: record?.approved_by ?? "", source_uri: record?.source_uri ?? "", remark: record?.remark ?? "" };
  if (kind === "path-segments") return { trajectory_program_id: record?.trajectory_program_id ?? "", segment_no: String(record?.segment_no ?? 1), name: record?.name ?? "", brush_id: record?.brush_id ?? "", part_id: record?.part_id ?? "", tcp_name: record?.tcp_name ?? "", configured_speed: String(record?.configured_speed ?? ""), speed_unit: record?.speed_unit ?? "mm/s", trigger_state: record?.trigger_state ?? "ON", remark: record?.remark ?? "" };
  if (kind === "contribution-versions") return { program_version_id: record?.program_version_id ?? "", target_family: record?.target_family ?? "ORANGE_PEEL", version: record?.version ?? "1.0", method: record?.method ?? "EXPERT", status: record?.status ?? "DRAFT", approved_by: record?.approved_by ?? "", evidence_uri: record?.evidence_uri ?? "", remark: record?.remark ?? "" };
  return { contribution_version_id: record?.contribution_version_id ?? "", measurement_point_id: record?.measurement_point_id ?? "", brush_id: record?.brush_id ?? "", path_segment_id: record?.path_segment_id ?? "", overlap_ratio: String(record?.overlap_ratio ?? 1), contribution_weight: String(record?.contribution_weight ?? 1), validation_score: String(record?.validation_score ?? "") };
}

function buildBody(kind: Kind, form: FormState): Record<string, unknown> {
  const body: Record<string, unknown> = { ...form };
  for (const key of ["controller_id", "controller_software_version", "software_version", "bell_cup_type", "bell_cup_code", "source_uri", "approved_by", "coordinate_system", "tcp_name", "brush_id", "part_id", "evidence_uri", "path_segment_id", "remark"]) if (body[key] === "") body[key] = null;
  for (const key of ["segment_no", "configured_speed", "overlap_ratio", "contribution_weight", "validation_score"]) if (body[key] !== undefined) body[key] = body[key] === "" ? null : Number(body[key]);
  if (kind === "contribution-entries" && body.brush_id && body.path_segment_id) throw new Error("贡献条目只能选择刷子或路径段之一");
  return body;
}

function input(labelText: string, key: string, form: FormState, setForm: (form: FormState) => void, type = "text", required = false) {
  return <label className="form-field" key={key}><span>{labelText}{required ? <b>*</b> : null}</span><input type={type} step={type === "number" ? "any" : undefined} required={required} value={form[key] ?? ""} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>;
}

function select(labelText: string, key: string, form: FormState, setForm: (form: FormState) => void, choices: Array<[string, string]>, required = true) {
  return <label className="form-field" key={key}><span>{labelText}{required ? <b>*</b> : null}</span><select required={required} value={form[key] ?? ""} onChange={(event) => setForm({ ...form, [key]: event.target.value })}>{!required ? <option value="">未关联</option> : null}{choices.map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>;
}

function renderFields(kind: Kind, form: FormState, setForm: (form: FormState) => void, refs: { factories: Named[]; versions: Named[]; brushes: Named[]; points: Named[]; parts: Named[]; resources: Record<Kind, Resource[]> }) {
  const options = (items: Named[]) => items.map((item) => [item.id, label(item)] as [string, string]);
  const commonDevice = [select("工厂", "factory_id", form, setForm, options(refs.factories)), input("设备代码", "code", form, setForm, "text", true), input("设备名称", "name", form, setForm, "text", true), input("型号", "model", form, setForm, "text", true), input("序列号", "serial_no", form, setForm, "text", true)];
  if (kind === "robots") return [...commonDevice, input("控制软件版本", "controller_software_version", form, setForm), select("状态", "status", form, setForm, deviceStatusOptions), input("受控来源 URI", "source_uri", form, setForm), input("备注", "remark", form, setForm)];
  if (kind === "controllers") return [...commonDevice, input("软件版本", "software_version", form, setForm), select("状态", "status", form, setForm, deviceStatusOptions), input("受控来源 URI", "source_uri", form, setForm), input("备注", "remark", form, setForm)];
  if (kind === "atomizers") return [...commonDevice, select("绑定应用控制器", "controller_id", form, setForm, options(refs.resources.controllers), false), input("旋杯类型", "bell_cup_type", form, setForm), input("杯头代码", "bell_cup_code", form, setForm), select("状态", "status", form, setForm, deviceStatusOptions), input("受控来源 URI", "source_uri", form, setForm), input("备注", "remark", form, setForm)];
  if (kind === "device-configurations") return [select("喷涂程序版本", "program_version_id", form, setForm, options(refs.versions)), select("机器人", "robot_id", form, setForm, options(refs.resources.robots)), select("静电旋杯", "atomizer_id", form, setForm, options(refs.resources.atomizers)), select("应用控制器", "controller_id", form, setForm, options(refs.resources.controllers)), input("配置版本", "configuration_version", form, setForm, "text", true), select("状态", "status", form, setForm, statusOptions), input("审批人", "approved_by", form, setForm), input("受控来源 URI", "source_uri", form, setForm), input("备注", "remark", form, setForm)];
  if (kind === "trajectory-programs") return [select("喷涂程序版本", "program_version_id", form, setForm, options(refs.versions)), input("轨迹代码", "trajectory_code", form, setForm, "text", true), input("轨迹名称", "name", form, setForm, "text", true), input("轨迹版本", "version", form, setForm, "text", true), input("批准文件校验和", "checksum", form, setForm, "text", true), input("坐标系", "coordinate_system", form, setForm), input("TCP 名称", "tcp_name", form, setForm), select("状态", "status", form, setForm, statusOptions), input("审批人", "approved_by", form, setForm), input("受控来源 URI", "source_uri", form, setForm), input("备注", "remark", form, setForm)];
  if (kind === "path-segments") return [select("轨迹程序", "trajectory_program_id", form, setForm, options(refs.resources["trajectory-programs"])), input("路径段序号", "segment_no", form, setForm, "number", true), input("路径段名称", "name", form, setForm, "text", true), select("刷子", "brush_id", form, setForm, options(refs.brushes), false), select("零件", "part_id", form, setForm, options(refs.parts), false), input("TCP 名称", "tcp_name", form, setForm), input("配置移枪速度", "configured_speed", form, setForm, "number"), input("速度单位", "speed_unit", form, setForm), select("触发状态", "trigger_state", form, setForm, [["ON", "ON"], ["OFF", "OFF"], ["PULSE", "PULSE"]]), input("备注", "remark", form, setForm)];
  if (kind === "contribution-versions") return [select("喷涂程序版本", "program_version_id", form, setForm, options(refs.versions)), select("质量目标族", "target_family", form, setForm, qualityOptions), input("贡献版本", "version", form, setForm, "text", true), select("建立方法", "method", form, setForm, [["EXPERT", "专家评审"], ["GEOMETRY", "几何分析"], ["SIMULATION", "仿真"], ["DOE", "DOE"], ["FITTED_DEPOSITION", "拟合沉积"]]), select("状态", "status", form, setForm, statusOptions), input("审批人", "approved_by", form, setForm), input("证据 URI", "evidence_uri", form, setForm), input("备注", "remark", form, setForm)];
  return [select("贡献版本", "contribution_version_id", form, setForm, options(refs.resources["contribution-versions"])), select("测量点", "measurement_point_id", form, setForm, options(refs.points)), select("刷子来源（二选一）", "brush_id", form, setForm, options(refs.brushes), false), select("路径段来源（二选一）", "path_segment_id", form, setForm, options(refs.resources["path-segments"]), false), input("重叠率（0~1）", "overlap_ratio", form, setForm, "number", true), input("贡献权重（0~1）", "contribution_weight", form, setForm, "number", true), input("验证分数（0~1）", "validation_score", form, setForm, "number")];
}
