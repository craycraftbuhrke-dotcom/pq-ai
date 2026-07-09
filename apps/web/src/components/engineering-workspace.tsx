"use client";

import {
  ClipboardList,
  FileCheck2,
  GitBranch,
  LoaderCircle,
  MessageSquarePlus,
  Plus,
  RefreshCw,
  RotateCcw,
  Route,
  ShieldCheck,
  Sparkles,
  Truck,
  Upload,
  Wrench,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { BulkDataActions } from "@/components/bulk-data-actions";
import { ModalShell } from "@/components/modal-shell";
import { SectionHeader } from "@/components/section-header";
import { JsonObjectEditor, JsonStringListEditor } from "@/components/structured-json-editor";
import { WorkspaceEmptyState } from "@/components/workspace-empty-state";
import { ROLE_LABELS, statusLabel } from "@/lib/display-labels";
import { useWorkspaceContext } from "@/lib/workspace-context";

type TabKey =
  | "issues"
  | "routes"
  | "imports"
  | "measurement"
  | "supplier"
  | "contribution"
  | "knowledge"
  | "modeling";

type FieldType = "text" | "textarea" | "select" | "number" | "datetime-local" | "json" | "checkbox";
type FormState = Record<string, string | boolean>;
type Resource = Record<string, unknown> & { id: string; created_at?: string; updated_at?: string };
type Summary = Record<string, number>;

type FieldDef = {
  name: string;
  label: string;
  type?: FieldType;
  required?: boolean;
  options?: Array<[string, string]>;
  placeholder?: string;
};

type TabConfig = {
  label: string;
  endpoint: string;
  bulkKey: string;
  bulkLabel: string;
  icon: typeof ClipboardList;
  fields: FieldDef[];
  table: Array<[string, string]>;
};

const processStages: Array<[string, string]> = [
  ["MIDCOAT_EXT", "中涂外喷"],
  ["BASECOAT_1", "色漆一站"],
  ["BASECOAT_2", "色漆二站"],
  ["CLEARCOAT_1", "清漆一站"],
  ["CLEARCOAT_2", "清漆二站"],
];

const qualityTypes: Array<[string, string]> = [
  ["ORANGE_PEEL", "橘皮"],
  ["COLOR_DIFFERENCE", "色差/效应"],
  ["THICKNESS", "膜厚"],
];

const statusOptions: Record<string, Array<[string, string]>> = {
  route: [["DRAFT", "草稿"], ["APPROVED", "已批准"], ["ACTIVE", "生效"], ["RETIRED", "退役"]],
  task: [["OPEN", "打开"], ["TRIAGE", "分诊"], ["IN_TRIAL", "试验中"], ["WAITING_SUPPLIER", "等待供应商"], ["VERIFIED", "已验证"], ["CLOSED", "关闭"]],
  severity: [["LOW", "低"], ["MEDIUM", "中"], ["HIGH", "高"], ["CRITICAL", "严重"]],
  importJob: [["PREVIEWED", "已预览"], ["VALIDATED", "已校验"], ["IMPORTED", "已导入"], ["FAILED", "失败"], ["REPLAYED", "已重放"]],
  supplier: [["SUBMITTED", "已提交"], ["VALIDATED", "已校验"], ["ACCEPTED", "接受"], ["REJECTED", "拒绝"], ["SUPERSEDED", "已替代"]],
  issue: [["OPEN", "打开"], ["WAITING_SUPPLIER", "等待供应商"], ["CONTAINED", "已遏制"], ["CLOSED", "关闭"]],
  approval: [["DRAFT", "草稿"], ["APPROVED", "已批准"], ["ACTIVE", "生效"], ["RETIRED", "退役"]],
};

const roleOptions: Array<[string, string]> = Object.entries(ROLE_LABELS);

const FK_SELECT_FIELDS = new Set([
  "factory_id",
  "production_run_id",
  "measurement_point_id",
  "quality_measurement_id",
  "material_batch_id",
  "instrument_id",
  "probe_id",
  "method_id",
  "profile_id",
  "contribution_version_id",
  "model_version_id",
  "prediction_result_id",
  "owner_role",
]);

const tabs: Record<TabKey, TabConfig> = {
  issues: {
    label: "问题处理中心",
    endpoint: "issue-tasks",
    bulkKey: "engineering.issue-tasks",
    bulkLabel: "质量问题/调试工单",
    icon: ClipboardList,
    fields: [
      { name: "task_no", label: "工单编号", required: true, placeholder: "QI-2026-0001" },
      { name: "title", label: "标题", required: true },
      { name: "task_type", label: "任务类型", type: "select", options: [["QUALITY_ISSUE", "质量问题"], ["PROCESS_DEBUG", "工艺调试"], ["SUPPLIER_FEEDBACK", "供应商反馈"], ["CONTROLLED_TRIAL", "受控试验"]] },
      { name: "status", label: "状态", type: "select", options: statusOptions.task },
      { name: "severity", label: "严重度", type: "select", options: statusOptions.severity },
      { name: "factory_id", label: "工厂", type: "select" },
      { name: "production_run_id", label: "生产车身", type: "select" },
      { name: "measurement_point_id", label: "测量点", type: "select" },
      { name: "quality_measurement_id", label: "质量记录", type: "select" },
      { name: "material_batch_id", label: "材料批次", type: "select" },
      { name: "process_stage", label: "工序", type: "select", options: [["", "不指定"], ...processStages] },
      { name: "target_quality_type", label: "质量族", type: "select", options: [["", "不指定"], ...qualityTypes] },
      { name: "target_metric", label: "目标指标" },
      { name: "owner_role", label: "责任角色", type: "select", options: [["", "不指定"], ...roleOptions] },
      { name: "created_by", label: "创建人", required: true, placeholder: "例如：张工" },
      { name: "due_at", label: "期望完成时间", type: "datetime-local" },
      { name: "problem_statement", label: "问题描述", type: "textarea", required: true },
      { name: "hypothesis", label: "工程假设", type: "textarea" },
    ],
    table: [["task_no", "编号"], ["title", "标题"], ["severity", "严重度"], ["status", "状态"], ["target_metric", "指标"]],
  },
  routes: {
    label: "工艺路线",
    endpoint: "process-routes",
    bulkKey: "engineering.process-routes",
    bulkLabel: "3C3B 工艺路线",
    icon: Route,
    fields: [
      { name: "factory_id", label: "工厂", required: true, type: "select" },
      { name: "route_code", label: "路线代码", required: true, placeholder: "3C3B-F01" },
      { name: "name", label: "路线名称", required: true },
      { name: "version", label: "版本", required: true, placeholder: "V1.0" },
      { name: "status", label: "状态", type: "select", options: statusOptions.route },
      { name: "bake_strategy", label: "闪干/烘烤策略" },
      { name: "source_uri", label: "来源文件地址" },
      { name: "effective_from", label: "生效时间", type: "datetime-local" },
      { name: "effective_to", label: "失效时间", type: "datetime-local" },
      { name: "approved_by", label: "审批人" },
      { name: "remark", label: "备注", type: "textarea" },
    ],
    table: [["route_code", "路线"], ["name", "名称"], ["version", "版本"], ["status", "状态"], ["bake_strategy", "策略"]],
  },
  imports: {
    label: "文件导入",
    endpoint: "file-import-jobs",
    bulkKey: "engineering.file-import-jobs",
    bulkLabel: "设备/材料文件导入任务",
    icon: FileCheck2,
    fields: [
      { name: "import_no", label: "导入任务号", required: true, placeholder: "IMP-DXQ-001" },
      { name: "profile_id", label: "导入配置", required: true, type: "select" },
      { name: "domain_type", label: "文件域", type: "select", options: [["DURR_DXQ", "Dürr DXQ"], ["DURR_PLC", "Dürr PLC"], ["BYK_COLOR", "BYK 色差"], ["BYK_ORANGE_PEEL", "BYK 橘皮"], ["FISCHER_THICKNESS", "Fischer 膜厚"], ["MATERIAL_COA", "材料 COA"], ["MATERIAL_TDS", "材料 TDS"]] },
      { name: "source_filename", label: "文件名", required: true },
      { name: "source_uri", label: "来源文件地址" },
      { name: "source_checksum", label: "文件校验码" },
      { name: "status", label: "状态", type: "select", options: statusOptions.importJob },
      { name: "row_count", label: "总行数", type: "number" },
      { name: "valid_row_count", label: "有效行数", type: "number" },
      { name: "failed_row_count", label: "失败行数", type: "number" },
      { name: "preview_payload", label: "预览结果", type: "json" },
      { name: "error_report", label: "错误清单", type: "json" },
      { name: "submitted_by", label: "提交人", required: true },
    ],
    table: [["import_no", "任务号"], ["domain_type", "文件域"], ["source_filename", "文件"], ["status", "状态"], ["row_count", "行数"]],
  },
  measurement: {
    label: "测量/MSA",
    endpoint: "measurement-msa-studies",
    bulkKey: "engineering.measurement-msa-studies",
    bulkLabel: "测量重复性再现性",
    icon: ShieldCheck,
    fields: [
      { name: "study_no", label: "研究编号", required: true, placeholder: "MSA-2026-001" },
      { name: "instrument_id", label: "仪器", required: true, type: "select" },
      { name: "probe_id", label: "探头", type: "select" },
      { name: "method_id", label: "方法", type: "select" },
      { name: "quality_type", label: "质量族", type: "select", options: qualityTypes },
      { name: "metric_code", label: "指标代码", required: true, placeholder: "例如：DOI / 膜厚" },
      { name: "study_type", label: "研究类型", placeholder: "例如：重复性再现性" },
      { name: "sample_count", label: "样件数", type: "number", required: true },
      { name: "operator_count", label: "人员数", type: "number", required: true },
      { name: "repeat_count", label: "重复次数", type: "number", required: true },
      { name: "grr_percent", label: "GRR %", type: "number" },
      { name: "ndc", label: "NDC", type: "number" },
      { name: "result", label: "结论", type: "select", options: [["PENDING", "待定"], ["PASS", "通过"], ["FAIL", "失败"]] },
      { name: "study_at", label: "研究时间", type: "datetime-local", required: true },
      { name: "approved_by", label: "审批人" },
      { name: "raw_results", label: "原始结果明细", type: "json" },
    ],
    table: [["study_no", "编号"], ["quality_type", "质量族"], ["metric_code", "指标"], ["result", "结论"], ["grr_percent", "GRR %"]],
  },
  supplier: {
    label: "供应商材料",
    endpoint: "supplier-submissions",
    bulkKey: "engineering.supplier-submissions",
    bulkLabel: "供应商材料提交",
    icon: Truck,
    fields: [
      { name: "submission_no", label: "提交编号", required: true },
      { name: "supplier", label: "供应商", required: true },
      { name: "material_batch_id", label: "材料批次", type: "select" },
      { name: "material_code", label: "材料代码", required: true },
      { name: "material_name", label: "材料名称" },
      { name: "document_type", label: "文件类型", type: "select", options: [["COA", "COA"], ["TDS", "TDS"], ["MSDS", "MSDS"], ["DOE", "DOE"]] },
      { name: "source_uri", label: "来源文件地址" },
      { name: "profile_id", label: "导入配置", type: "select" },
      { name: "status", label: "状态", type: "select", options: statusOptions.supplier },
      { name: "submitted_by", label: "提交人", required: true },
      { name: "reviewed_by", label: "审核人" },
      { name: "field_values", label: "字段值明细", type: "json" },
      { name: "validation_result", label: "校验结果", type: "json" },
      { name: "remark", label: "备注", type: "textarea" },
    ],
    table: [["submission_no", "编号"], ["supplier", "供应商"], ["material_code", "材料"], ["document_type", "类型"], ["status", "状态"]],
  },
  contribution: {
    label: "贡献验证",
    endpoint: "contribution-validations",
    bulkKey: "engineering.contribution-validations",
    bulkLabel: "点位贡献验证",
    icon: GitBranch,
    fields: [
      { name: "contribution_version_id", label: "贡献版本", required: true, type: "select" },
      { name: "study_no", label: "研究编号", required: true },
      { name: "target_family", label: "目标族", type: "select", options: qualityTypes },
      { name: "method", label: "来源方法", type: "select", options: [["EXPERT", "专家映射"], ["DXQ_SIMULATION", "DXQ 仿真"], ["DOE", "DOE"], ["DEPOSITION_MODEL", "沉积模型"]] },
      { name: "status", label: "状态", type: "select", options: statusOptions.approval },
      { name: "sample_count", label: "样本数", type: "number" },
      { name: "validation_score", label: "验证分数", type: "number" },
      { name: "evidence_uri", label: "证据 URI" },
      { name: "evidence_payload", label: "证据明细", type: "json" },
      { name: "approved_by", label: "审批人" },
      { name: "remark", label: "备注", type: "textarea" },
    ],
    table: [["study_no", "编号"], ["target_family", "目标族"], ["method", "方法"], ["status", "状态"], ["validation_score", "得分"]],
  },
  knowledge: {
    label: "诊断知识库",
    endpoint: "knowledge-entries",
    bulkKey: "engineering.knowledge-entries",
    bulkLabel: "诊断知识库",
    icon: Wrench,
    fields: [
      { name: "entry_code", label: "知识编号", required: true },
      { name: "version", label: "版本", required: true },
      { name: "title", label: "标题", required: true },
      { name: "category", label: "类别", required: true },
      { name: "target_quality_type", label: "质量族", type: "select", options: [["", "不指定"], ...qualityTypes] },
      { name: "metric_code", label: "指标代码" },
      { name: "symptom_pattern", label: "症状模式", type: "textarea", required: true },
      { name: "diagnosis_rule", label: "诊断规则", type: "textarea", required: true },
      { name: "recommended_checks", label: "推荐检查项", type: "json" },
      { name: "related_parameters", label: "相关参数清单", type: "json" },
      { name: "evidence_level", label: "证据等级", type: "select", options: [["RULE", "规则"], ["SIMULATION", "仿真"], ["DOE", "DOE"], ["CONTROLLED_CHANGE", "受控变更"], ["VERIFIED_CAUSE", "验证原因"]] },
      { name: "status", label: "状态", type: "select", options: statusOptions.approval },
      { name: "created_by", label: "创建人", required: true },
      { name: "approved_by", label: "审批人" },
    ],
    table: [["entry_code", "编号"], ["title", "标题"], ["category", "类别"], ["target_quality_type", "目标族"], ["status", "状态"]],
  },
  modeling: {
    label: "模型解释",
    endpoint: "model-explanations",
    bulkKey: "engineering.model-explanations",
    bulkLabel: "模型解释结果",
    icon: Sparkles,
    fields: [
      { name: "model_version_id", label: "模型版本", required: true, type: "select" },
      { name: "prediction_result_id", label: "关联预测结果", type: "select" },
      { name: "explanation_type", label: "解释类型", type: "select", options: [["SHAP", "特征贡献解释"], ["SENSITIVITY", "敏感性"], ["UNCERTAINTY", "不确定度"], ["FEATURE_IMPORTANCE", "特征重要性"]] },
      { name: "target_metric", label: "目标指标", required: true },
      { name: "feature_impacts", label: "特征影响结果", type: "json" },
      { name: "sensitivity_grid", label: "敏感性结果", type: "json" },
      { name: "uncertainty", label: "不确定度结果", type: "json" },
      { name: "generated_by", label: "生成人", required: true },
    ],
    table: [["explanation_type", "类型"], ["target_metric", "指标"], ["generated_by", "生成人"], ["generated_at", "生成时间"], ["model_version_id", "模型版本"]],
  },
};

type RefLists = {
  factories: Resource[];
  productionRuns: Resource[];
  measurementPoints: Resource[];
  qualityMeasurements: Resource[];
  materialBatches: Resource[];
  instruments: Resource[];
  probes: Resource[];
  methods: Resource[];
  importProfiles: Resource[];
  contributionVersions: Resource[];
  modelVersions: Resource[];
  predictions: Resource[];
};

function emptyRefs(): RefLists {
  return {
    factories: [],
    productionRuns: [],
    measurementPoints: [],
    qualityMeasurements: [],
    materialBatches: [],
    instruments: [],
    probes: [],
    methods: [],
    importProfiles: [],
    contributionVersions: [],
    modelVersions: [],
    predictions: [],
  };
}

const orderedTabs = Object.keys(tabs) as TabKey[];

function emptyTabData(): Record<TabKey, Resource[]> {
  return {
    issues: [],
    routes: [],
    imports: [],
    measurement: [],
    supplier: [],
    contribution: [],
    knowledge: [],
    modeling: [],
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  const payload = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new Error(payload.error ?? `请求失败（${response.status}）`);
  return payload;
}

async function softRequest<T>(path: string): Promise<T[]> {
  try {
    const payload = await request<T[] | T>(path);
    return Array.isArray(payload) ? payload : [];
  } catch {
    return [];
  }
}

function codeNameLabel(item: Resource): string {
  const code = String(item.code ?? item.batch_no ?? item.run_no ?? item.data_no ?? item.model_code ?? item.id);
  const name = item.name != null && item.name !== "" ? String(item.name) : "";
  return name ? `${code} / ${name}` : code;
}

function productionRunLabel(item: Resource): string {
  const runNo = String(item.run_no ?? item.id);
  const bodyNo = item.body_no != null && item.body_no !== "" ? String(item.body_no) : "";
  return bodyNo ? `${runNo} · ${bodyNo}` : runNo;
}

function materialBatchLabel(item: Resource): string {
  const batch = String(item.batch_no ?? item.code ?? item.id);
  const material = item.material_code != null && item.material_code !== "" ? String(item.material_code) : "";
  return material ? `${batch} · ${material}` : batch;
}

function contributionVersionLabel(item: Resource): string {
  const family = item.target_family != null ? statusLabel(String(item.target_family)) : "";
  const version = String(item.version ?? item.id.slice(0, 8));
  return family ? `${family} · ${version}` : version;
}

function modelVersionLabel(item: Resource): string {
  return `${String(item.model_code ?? item.id)}:${String(item.version ?? "")}`;
}

function importProfileLabel(item: Resource): string {
  return `${String(item.code ?? item.id)} / ${String(item.version ?? "")} · ${statusLabel(String(item.domain_type ?? ""))}`;
}

function withEmpty(options: Array<[string, string]>, required?: boolean): Array<[string, string]> {
  return required ? options : [["", "不指定"], ...options];
}

function fieldOptions(field: FieldDef, refs: RefLists): Array<[string, string]> | undefined {
  if (field.options) return field.options;
  switch (field.name) {
    case "factory_id":
      return withEmpty(refs.factories.map((item) => [item.id, codeNameLabel(item)]), field.required);
    case "production_run_id":
      return withEmpty(refs.productionRuns.map((item) => [item.id, productionRunLabel(item)]), field.required);
    case "measurement_point_id":
      return withEmpty(refs.measurementPoints.map((item) => [item.id, codeNameLabel(item)]), field.required);
    case "quality_measurement_id":
      return withEmpty(refs.qualityMeasurements.map((item) => [item.id, String(item.data_no ?? item.id)]), field.required);
    case "material_batch_id":
      return withEmpty(refs.materialBatches.map((item) => [item.id, materialBatchLabel(item)]), field.required);
    case "instrument_id":
      return withEmpty(refs.instruments.map((item) => [item.id, codeNameLabel(item)]), field.required);
    case "probe_id":
      return withEmpty(refs.probes.map((item) => [item.id, codeNameLabel(item)]), field.required);
    case "method_id":
      return withEmpty(
        refs.methods.map((item) => [item.id, `${String(item.code ?? item.id)}${item.version ? `:${item.version}` : ""}`]),
        field.required,
      );
    case "profile_id":
      return withEmpty(refs.importProfiles.map((item) => [item.id, importProfileLabel(item)]), field.required);
    case "contribution_version_id":
      return withEmpty(refs.contributionVersions.map((item) => [item.id, contributionVersionLabel(item)]), field.required);
    case "model_version_id":
      return withEmpty(refs.modelVersions.map((item) => [item.id, modelVersionLabel(item)]), field.required);
    case "prediction_result_id":
      return withEmpty(
        refs.predictions.map((item) => [
          item.id,
          `${String(item.metric_code ?? "指标")} = ${item.predicted_value ?? "—"} · ${String(item.model_name ?? item.model_version_id ?? "").toString().slice(0, 24)}`,
        ]),
        field.required,
      );
    default:
      return field.options;
  }
}

function resolveField(field: FieldDef, refs: RefLists): FieldDef {
  if (!FK_SELECT_FIELDS.has(field.name) && field.type !== "select") return field;
  const options = fieldOptions(field, refs);
  if (!options) return field;
  return { ...field, type: "select", options };
}

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("文件读取失败"));
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.readAsDataURL(file);
  });
}

function localDateTime(value?: unknown): string {
  const date = value ? new Date(String(value)) : new Date();
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.map((item) => displayValue(item)).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  if (String(value).includes("T") && !Number.isNaN(new Date(String(value)).getTime())) {
    return new Date(String(value)).toLocaleString("zh-CN");
  }
  return statusLabel(String(value));
}

function isSystemGeneratedJsonField(fieldName: string): boolean {
  return [
    "preview_payload",
    "error_report",
    "validation_result",
    "feature_impacts",
    "sensitivity_grid",
    "uncertainty",
  ].includes(fieldName);
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function asRecordArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && !Array.isArray(item))
    : [];
}

function defaultForm(fields: FieldDef[]): FormState {
  return Object.fromEntries(
    fields.map((field) => {
      if (field.type === "checkbox") return [field.name, false];
      if (field.type === "json") return [field.name, field.name === "related_parameters" ? "[]" : "{}"];
      if (field.type === "datetime-local") return [field.name, field.required ? localDateTime() : ""];
      return [field.name, field.options?.[0]?.[0] ?? ""];
    }),
  );
}

function payloadFromForm(fields: FieldDef[], form: FormState): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const field of fields) {
    const value = form[field.name];
    if ((value === "" || value === undefined) && !field.required) continue;
    if (field.type === "number") {
      if (value === "" || value === undefined) continue;
      payload[field.name] = Number(value);
    } else if (field.type === "checkbox") {
      payload[field.name] = Boolean(value);
    } else if (field.type === "json") {
      if (value === "" || value === undefined) continue;
      payload[field.name] = JSON.parse(String(value));
    } else if (field.type === "datetime-local") {
      if (value === "" || value === undefined) continue;
      payload[field.name] = new Date(String(value)).toISOString();
    } else {
      payload[field.name] = value;
    }
  }
  return payload;
}

export function EngineeringWorkspace() {
  const { factoryId } = useWorkspaceContext();
  const [active, setActive] = useState<TabKey>("issues");
  const [summary, setSummary] = useState<Summary>({});
  const [data, setData] = useState<Record<TabKey, Resource[]>>(() => emptyTabData());
  const [refs, setRefs] = useState<RefLists>(() => emptyRefs());
  const [form, setForm] = useState<FormState>(() => defaultForm(tabs.issues.fields));
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedImportJobId, setSelectedImportJobId] = useState<string | null>(null);
  const [importProfileId, setImportProfileId] = useState("");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importSubmittedBy, setImportSubmittedBy] = useState("engineer");
  const [evidence, setEvidence] = useState<Resource[]>([]);
  const [comments, setComments] = useState<Resource[]>([]);
  const [evidenceText, setEvidenceText] = useState("");
  const [commentText, setCommentText] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const closeModal = useCallback(() => {
    if (submitting) return;
    setModalOpen(false);
  }, [submitting]);

  const config = tabs[active];
  const resolvedFields = useMemo(
    () => config.fields.map((field) => resolveField(field, refs)),
    [config.fields, refs],
  );
  const EmptyIcon = config.icon;
  const selectedTask = useMemo(() => data.issues.find((item) => item.id === selectedTaskId) ?? null, [data.issues, selectedTaskId]);
  const selectedImportJob = useMemo(() => data.imports.find((item) => item.id === selectedImportJobId) ?? null, [data.imports, selectedImportJobId]);
  const selectedImportPreview = asRecord(selectedImportJob?.preview_payload);
  const selectedImportErrors = asRecord(selectedImportJob?.error_report);
  const selectedImportPreviewRows = asRecordArray(selectedImportPreview.preview_rows);
  const selectedImportErrorRows = asRecordArray(selectedImportErrors.errors);
  const importProfiles = refs.importProfiles;

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [
        nextSummary,
        nextProfiles,
        factories,
        productionRuns,
        measurementPoints,
        qualityMeasurements,
        materialBatches,
        instruments,
        probes,
        methods,
        contributionVersions,
        modelVersions,
        predictions,
        ...resources
      ] = await Promise.all([
        request<Summary>("/api/engineering/summary"),
        softRequest<Resource>("/api/engineering/file-import-profiles"),
        softRequest<Resource>("/api/master-data/factories"),
        softRequest<Resource>("/api/process/production-runs?limit=500"),
        softRequest<Resource>("/api/master-data/measurement-points"),
        softRequest<Resource>("/api/quality/measurements?limit=500"),
        softRequest<Resource>("/api/process/material-batches"),
        softRequest<Resource>("/api/quality/governance/instruments"),
        softRequest<Resource>("/api/engineering/measurement-probes"),
        softRequest<Resource>("/api/quality/governance/methods"),
        softRequest<Resource>("/api/process/robot-governance/contribution-versions"),
        softRequest<Resource>("/api/ai/models"),
        softRequest<Resource>("/api/ai/predictions"),
        ...orderedTabs.map((key) => request<Resource[]>(`/api/engineering/${tabs[key].endpoint}`)),
      ]);
      setSummary(nextSummary);
      setRefs({
        factories,
        productionRuns,
        measurementPoints,
        qualityMeasurements,
        materialBatches,
        instruments,
        probes,
        methods,
        importProfiles: nextProfiles,
        contributionVersions,
        modelVersions,
        predictions,
      });
      setImportProfileId((current) => current || nextProfiles[0]?.id || "");
      const nextData = emptyTabData();
      orderedTabs.forEach((key, index) => {
        nextData[key] = resources[index] ?? [];
      });
      setData(nextData);
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "工程闭环数据加载失败" });
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTaskDetail = useCallback(async (taskId: string | null) => {
    if (!taskId) {
      setEvidence([]);
      setComments([]);
      return;
    }
    try {
      const [nextEvidence, nextComments] = await Promise.all([
        request<Resource[]>(`/api/engineering/issue-tasks/${taskId}/evidence`),
        request<Resource[]>(`/api/engineering/issue-tasks/${taskId}/comments`),
      ]);
      setEvidence(nextEvidence);
      setComments(nextComments);
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "工单证据加载失败" });
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadTaskDetail(selectedTaskId), 0);
    return () => window.clearTimeout(timer);
  }, [loadTaskDetail, selectedTaskId]);

  function openCreate(nextTab = active) {
    setActive(nextTab);
    const nextFields = tabs[nextTab].fields.map((field) => resolveField(field, refs));
    const nextForm = defaultForm(nextFields);
    if ((nextTab === "issues" || nextTab === "routes") && factoryId) {
      nextForm.factory_id = factoryId;
    }
    setForm(nextForm);
    setModalOpen(true);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);
    try {
      const payload = payloadFromForm(resolvedFields, form);
      await request(`/api/engineering/${config.endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setMessage({ type: "success", text: `${config.bulkLabel}已创建` });
      setModalOpen(false);
      await reload();
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "保存失败" });
    } finally {
      setSubmitting(false);
    }
  }

  async function addEvidence() {
    if (!selectedTaskId || !evidenceText.trim()) return;
    setSubmitting(true);
    try {
      await request(`/api/engineering/issue-tasks/${selectedTaskId}/evidence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          evidence_type: "MANUAL_REVIEW",
          source_type: "ENGINEER_NOTE",
          summary: evidenceText,
          evidence_payload: {},
          confidence: 0.7,
          created_by: "engineer",
        }),
      });
      setEvidenceText("");
      await loadTaskDetail(selectedTaskId);
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "证据保存失败" });
    } finally {
      setSubmitting(false);
    }
  }

  async function addComment() {
    if (!selectedTaskId || !commentText.trim()) return;
    setSubmitting(true);
    try {
      await request(`/api/engineering/issue-tasks/${selectedTaskId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ author: "engineer", role: "PROCESS_ENGINEER", body: commentText }),
      });
      setCommentText("");
      await loadTaskDetail(selectedTaskId);
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "协作记录保存失败" });
    } finally {
      setSubmitting(false);
    }
  }

  async function previewImportFile() {
    if (!importProfileId || !importFile) {
      setMessage({ type: "error", text: "请选择导入配置和 CSV/XLSX 文件" });
      return;
    }
    setSubmitting(true);
    try {
      const contentBase64 = await readAsDataUrl(importFile);
      const job = await request<Resource>("/api/engineering/file-import-jobs/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_id: importProfileId,
          source_filename: importFile.name,
          content_base64: contentBase64,
          submitted_by: importSubmittedBy || "engineer",
        }),
      });
      setSelectedImportJobId(job.id);
      setImportFile(null);
      setMessage({ type: "success", text: "导入文件已完成预览与校验，未写入目标业务表" });
      await reload();
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "文件预览失败" });
    } finally {
      setSubmitting(false);
    }
  }

  async function replayImportJob() {
    if (!selectedImportJobId) return;
    setSubmitting(true);
    try {
      const replay = await request<Resource>(`/api/engineering/file-import-jobs/${selectedImportJobId}/replay`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ submitted_by: importSubmittedBy || "engineer" }),
      });
      setSelectedImportJobId(replay.id);
      setMessage({ type: "success", text: "导入任务已重放并生成新的审计记录" });
      await reload();
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "导入任务重放失败" });
    } finally {
      setSubmitting(false);
    }
  }

  function bulkResult(text: string, type: "success" | "error") {
    setMessage({ type, text });
  }

  return (
    <div className="page-stack engineering-workspace">
      <header className="page-header">
        <div>
          <span className="page-kicker">问题与调试</span>
          <h1>工程问题处理与 3C3B 闭环中心</h1>
          <p>把异常复核、Dürr 执行、材料批次、测量可靠性、AI 推荐、受控试验与经验沉淀连接成可审计任务流。</p>
        </div>
        <div className="page-actions">
          <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
            <RefreshCw className={loading ? "spin" : ""} />
            刷新
          </button>
          <BulkDataActions resourceKey={config.bulkKey} resourceLabel={config.bulkLabel} disabled={loading || submitting} onImported={reload} onResult={bulkResult} />
          <button className="button button-primary" onClick={() => openCreate()}>
            <Plus />
            新建{config.bulkLabel}
          </button>
        </div>
      </header>

      {message ? <button className={`message-banner message-${message.type}`} onClick={() => setMessage(null)}>{message.text}<X /></button> : null}

      <section className="quality-analytics-stat-grid">
        <article><span>工艺路线 / 生效</span><strong>{summary.process_routes ?? 0} / {summary.active_routes ?? 0}</strong><small>工厂级工艺路线版本</small></article>
        <article><span>问题工单 / 打开</span><strong>{summary.issue_tasks ?? 0} / {summary.open_tasks ?? 0}</strong><small>异常、调试、供应商反馈</small></article>
        <article><span>导入任务</span><strong>{summary.file_import_jobs ?? 0}</strong><small>Dürr/BYK/Fischer/材料文件治理</small></article>
        <article><span>MSA / 贡献验证</span><strong>{summary.msa_studies ?? 0} / {summary.contribution_validations ?? 0}</strong><small>测量可靠性与点位贡献可信度</small></article>
      </section>

      <div className="master-tabs engineering-tabs">
        {orderedTabs.map((key) => {
          const Icon = tabs[key].icon;
          return (
            <button key={key} className={active === key ? "master-tab master-tab-active" : "master-tab"} onClick={() => setActive(key)}>
              <Icon />
              {tabs[key].label}
              <span>{data[key].length}</span>
            </button>
          );
        })}
      </div>

      <section className={active === "issues" || active === "imports" ? "engineering-grid" : ""}>
        <div className="master-table-wrap">
          <table className="master-table">
            <thead>
              <tr>
                {config.table.map(([, label]) => <th key={label}>{label}</th>)}
                <th>创建时间</th>
              </tr>
            </thead>
            <tbody>
              {data[active].map((row) => (
                <tr
                  key={row.id}
                  className={
                    row.id === selectedTaskId || row.id === selectedImportJobId
                      ? "selected-row"
                      : ""
                  }
                  onClick={() => {
                    if (active === "issues") setSelectedTaskId(row.id);
                    if (active === "imports") setSelectedImportJobId(row.id);
                  }}
                >
                  {config.table.map(([field]) => <td key={field}>{displayValue(row[field])}</td>)}
                  <td>{displayValue(row.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data[active].length ? <WorkspaceEmptyState icon={EmptyIcon} title={`暂无${config.bulkLabel}`} description="可直接新建，或先下载模板后批量导入数据。" compact /> : null}
        </div>

        {active === "issues" ? (
          <aside className="engineering-detail-card">
            <SectionHeader
              eyebrow="问题证据"
              title={selectedTask ? displayValue(selectedTask.title) : "选择左侧工单"}
              description={selectedTask ? displayValue(selectedTask.problem_statement) : "选择工单后，可追加测量复核、Dürr 执行、材料批次、AI 诊断或人工判断证据。"}
              titleAs="h3"
            />
            <div className="compact-list">
              <strong>证据</strong>
              {evidence.map((item) => <span key={item.id}>{displayValue(item.evidence_type)} · {displayValue(item.summary)}</span>)}
              {!evidence.length ? <small>暂无证据</small> : null}
            </div>
            <textarea value={evidenceText} onChange={(event) => setEvidenceText(event.target.value)} placeholder="追加证据摘要，例如：Fischer 探头校准 PASS，重复测量差异 1.2μm。" />
            <button className="button button-secondary" onClick={() => void addEvidence()} disabled={!selectedTaskId || submitting}>
              <FileCheck2 />
              追加证据
            </button>
            <div className="compact-list">
              <strong>协作记录</strong>
              {comments.map((item) => <span key={item.id}>{displayValue(item.author)} · {displayValue(item.body)}</span>)}
              {!comments.length ? <small>暂无协作记录</small> : null}
            </div>
            <textarea value={commentText} onChange={(event) => setCommentText(event.target.value)} placeholder="记录下一步动作、责任人或试验安排。" />
            <button className="button button-primary" onClick={() => void addComment()} disabled={!selectedTaskId || submitting}>
              <MessageSquarePlus />
              追加协作记录
            </button>
          </aside>
        ) : null}

        {active === "imports" ? (
          <aside className="engineering-detail-card">
            <SectionHeader
              eyebrow="文件预览"
              title="设备/材料文件预览校验"
              description="选择已审批的导入配置后上传 CSV/XLSX。系统只生成预览、字段映射和错误报告，不会自动写入目标表。"
              titleAs="h3"
            />
            <label>
              <span>导入配置</span>
              <select value={importProfileId} onChange={(event) => setImportProfileId(event.target.value)}>
                {importProfiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {displayValue(profile.code)} / {displayValue(profile.version)} · {statusLabel(String(profile.domain_type ?? ""))}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>提交人</span>
              <input value={importSubmittedBy} onChange={(event) => setImportSubmittedBy(event.target.value)} />
            </label>
            <label className="file-upload-card">
              <Upload />
              <span>{importFile ? importFile.name : "选择 CSV/XLSX 文件"}</span>
              <input
                type="file"
                accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={(event) => setImportFile(event.target.files?.[0] ?? null)}
              />
            </label>
            <button className="button button-primary" onClick={() => void previewImportFile()} disabled={submitting || !importProfileId || !importFile}>
              {submitting ? <LoaderCircle className="spin" /> : <FileCheck2 />}
              预览并校验
            </button>
            <div className="compact-list">
              <strong>选中任务</strong>
              {selectedImportJob ? (
                <>
                  <span>{displayValue(selectedImportJob.import_no)} · {displayValue(selectedImportJob.status)}</span>
                  <span>行数：{displayValue(selectedImportJob.row_count)}，有效：{displayValue(selectedImportJob.valid_row_count)}，失败：{displayValue(selectedImportJob.failed_row_count)}</span>
                  <button className="button button-secondary" onClick={() => void replayImportJob()} disabled={submitting}>
                    <RotateCcw />
                    重放任务
                  </button>
                </>
              ) : <small>选择左侧导入任务后查看预览与错误报告</small>}
            </div>
            {selectedImportPreviewRows.length ? (
              <div className="compact-list">
                <strong>预览行</strong>
                {selectedImportPreviewRows.slice(0, 3).map((row, index) => (
                  <span key={index}>{Object.entries(row).slice(0, 4).map(([key, entryValue]) => `${key}: ${displayValue(entryValue)}`).join(" · ")}</span>
                ))}
              </div>
            ) : null}
            {selectedImportErrorRows.length ? (
              <div className="compact-list import-error-list">
                <strong>错误报告</strong>
                {selectedImportErrorRows.slice(0, 5).map((row, index) => (
                  <span key={index}>第 {displayValue(row.row)} 行 · {displayValue(row.field)} · {displayValue(row.message)}</span>
                ))}
              </div>
            ) : null}
          </aside>
        ) : null}
      </section>

      {modalOpen ? (
        <ModalShell
          className="quality-modal"
          eyebrow="工程流程"
          title={`新建${config.bulkLabel}`}
          description={`统一维护${config.bulkLabel}表单结构、关闭交互和保存动作。`}
          onClose={closeModal}
          busy={submitting}
        >
          <form onSubmit={submit}>
            <div className="form-grid">
                {resolvedFields.filter((field) => !isSystemGeneratedJsonField(field.name)).map((field) => (
                  <label
                    key={field.name}
                    className={field.type === "textarea" || field.type === "json" ? "form-field form-field-wide" : "form-field"}
                  >
                    <span>{field.label}{field.required ? " *" : ""}</span>
                    {renderField(field, form, setForm)}
                  </label>
                ))}
                {resolvedFields.some((field) => isSystemGeneratedJsonField(field.name)) ? (
                  <div className="modal-note form-field-wide">
                    系统生成字段不会在录入弹窗中要求人工填写。保存后，预览结果、错误清单、校验结果和模型解释结果由后端自动生成或回写。
                  </div>
                ) : null}
            </div>
            <div className="modal-actions">
              <button type="button" className="button button-secondary" onClick={closeModal} disabled={submitting}>取消</button>
              <button className="button button-primary" disabled={submitting}>
                {submitting ? <LoaderCircle className="spin" aria-hidden="true" /> : null}
                {submitting ? "正在保存" : "保存"}
              </button>
            </div>
          </form>
        </ModalShell>
      ) : null}
    </div>
  );
}

function renderField(field: FieldDef, form: FormState, setForm: (next: FormState) => void) {
  const value = form[field.name];
  if (field.type === "select") {
    return (
      <select value={String(value ?? "")} required={field.required} onChange={(event) => setForm({ ...form, [field.name]: event.target.value })}>
        {(field.options ?? []).map(([optionValue, label]) => <option key={optionValue} value={optionValue}>{label}</option>)}
      </select>
    );
  }
  if (field.type === "json") {
    if (field.name === "recommended_checks" || field.name === "related_parameters") {
      return (
        <JsonStringListEditor
          value={String(value ?? "")}
          onChange={(nextValue) => setForm({ ...form, [field.name]: nextValue })}
          itemLabel={field.name === "recommended_checks" ? "检查项" : "参数代码"}
          addLabel={field.name === "recommended_checks" ? "新增检查项" : "新增参数"}
        />
      );
    }
    return (
      <JsonObjectEditor
        value={String(value ?? "")}
        onChange={(nextValue) => setForm({ ...form, [field.name]: nextValue })}
        keyLabel={
          field.name === "field_values"
            ? "字段名"
            : field.name === "field_mapping"
              ? "源列名"
              : field.name === "evidence_payload"
                ? "证据项"
                : "项目"
        }
        valueLabel={
          field.name === "field_mapping"
            ? "目标字段"
            : field.name === "raw_results"
              ? "结果值"
              : "内容"
        }
        addLabel={
          field.name === "field_mapping"
            ? "新增映射"
            : field.name === "field_values"
              ? "新增字段"
              : "新增一项"
        }
      />
    );
  }
  if (field.type === "textarea") {
    return <textarea value={String(value ?? "")} required={field.required} placeholder={field.placeholder} onChange={(event) => setForm({ ...form, [field.name]: event.target.value })} />;
  }
  if (field.type === "checkbox") {
    return <input type="checkbox" checked={Boolean(value)} onChange={(event) => setForm({ ...form, [field.name]: event.target.checked })} />;
  }
  return (
    <input
      type={field.type ?? "text"}
      value={String(value ?? "")}
      required={field.required}
      placeholder={field.placeholder}
      onChange={(event) => setForm({ ...form, [field.name]: event.target.value })}
    />
  );
}
