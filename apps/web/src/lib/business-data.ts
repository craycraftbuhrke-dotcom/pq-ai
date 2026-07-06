import { apiRequestHeaders } from "@/lib/auth-data";

type Stat = { label: string; value: string; note: string };

export type ModuleData = {
  source: "api" | "fallback";
  stats: Stat[];
  rows: string[][];
};

type Resource = {
  id: string;
  code: string;
  name: string;
};

type ColorResource = Resource & {
  color_type: string;
  supplier?: string | null;
};

type PartResource = Resource & {
  material?: string | null;
  region?: string | null;
};

type MeasurementPointResource = Resource & {
  region?: string | null;
  quality_types: string[];
  is_match_point: boolean;
};

type MasterDataSummary = {
  factories: number;
  vehicle_models: number;
  colors: number;
  parts: number;
  measurement_groups: number;
  measurement_points: number;
  approved_point_contributions: number;
};

type QualityMetric = {
  metric_code: string;
  metric_name: string;
  raw_value: number;
  corrected_value?: number | null;
  unit?: string | null;
};

type QualityMeasurement = {
  data_no: string;
  measurement_point_id: string;
  measurement_point_code: string;
  quality_type: string;
  measured_at: string;
  measured_by?: string | null;
  is_valid: boolean;
  judgement: "PASS" | "FAIL" | "NO_STANDARD" | "INVALID";
  violations: string[];
  metrics: QualityMetric[];
};

type QualitySummary = {
  measurements: number;
  valid_measurements: number;
  metric_values: number;
  standards: number;
  pass_measurements: number;
  fail_measurements: number;
  no_standard_measurements: number;
  measurements_by_type: Record<string, number>;
};

type ModelVersion = {
  id: string;
  model_code: string;
  version: string;
  model_type: string;
  target_metric: string;
  feature_set_version: string;
  evaluation_metrics: Record<string, number>;
  training_sample_count: number;
  trained_at?: string | null;
  status: string;
};

type SprayProgram = {
  id: string;
  program_code: string;
  name: string;
  process_stage: string;
  station_code: string;
  station_name: string;
  robot_model?: string | null;
};

type SprayProgramVersion = {
  id: string;
  version: string;
  status: string;
  source_type: string;
  is_master_sample: boolean;
  updated_at: string;
};

type AuditSummary = {
  total_events: number;
  successful_writes: number;
  failed_writes: number;
  active_users: number;
  active_api_keys: number;
  events_by_action: Record<string, number>;
};

type AuditLog = {
  id: string;
  request_id: string;
  actor_username: string;
  action: string;
  http_method: string;
  path: string;
  resource_type?: string | null;
  resource_id?: string | null;
  status_code: number;
  client_ip?: string | null;
  occurred_at: string;
};

const fallbackMasterData: ModuleData = {
  source: "fallback",
  stats: [
    { label: "工厂", value: "0", note: "等待 API 数据" },
    { label: "车型", value: "0", note: "等待 API 数据" },
    { label: "颜色", value: "0", note: "等待 API 数据" },
    { label: "测量点", value: "0", note: "等待 API 数据" },
  ],
  rows: [],
};

const fallbackQualityData: ModuleData = {
  source: "fallback",
  stats: [
    { label: "今日测量记录", value: "0", note: "等待 API 数据" },
    { label: "一次合格率", value: "-", note: "等待 API 数据" },
    { label: "超差记录", value: "0", note: "等待 API 数据" },
    { label: "待确认数据", value: "0", note: "等待 API 数据" },
  ],
  rows: [],
};

const fallbackAiData: ModuleData = {
  source: "fallback",
  stats: [
    { label: "已注册模型", value: "0", note: "等待 API 数据" },
    { label: "当前生效模型", value: "0", note: "等待 API 数据" },
    { label: "训练样本", value: "0", note: "等待 API 数据" },
    { label: "平均训练 R²", value: "-", note: "等待 API 数据" },
  ],
  rows: [],
};

const fallbackProgramData: ModuleData = {
  source: "fallback",
  stats: [
    { label: "喷涂程序", value: "0", note: "等待 API 数据" },
    { label: "当前生效版本", value: "0", note: "等待 API 数据" },
    { label: "封样版本", value: "0", note: "等待 API 数据" },
    { label: "待审批版本", value: "0", note: "等待 API 数据" },
  ],
  rows: [],
};

const fallbackAuditData: ModuleData = {
  source: "fallback",
  stats: [
    { label: "审计事件", value: "0", note: "等待 API 审计链路" },
    { label: "成功写操作", value: "0", note: "暂无实时记录" },
    { label: "失败写操作", value: "0", note: "暂无实时记录" },
    { label: "活跃密钥", value: "0", note: "身份服务未连接" },
  ],
  rows: [],
};

async function fetchJson<T>(path: string): Promise<T> {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    throw new Error("API URL is not configured");
  }
  const response = await fetch(`${apiUrl}${path}`, {
    cache: "no-store",
    headers: await apiRequestHeaders(),
    signal: AbortSignal.timeout(2500),
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function getMasterDataPageData(): Promise<ModuleData> {
  try {
    const [summary, factories, vehicleModels, colors, parts, points] = await Promise.all([
      fetchJson<MasterDataSummary>("/master-data/summary"),
      fetchJson<Resource[]>("/factories"),
      fetchJson<Resource[]>("/vehicle-models"),
      fetchJson<ColorResource[]>("/colors"),
      fetchJson<PartResource[]>("/parts"),
      fetchJson<MeasurementPointResource[]>("/measurement-points"),
    ]);
    const rows: string[][] = [
      ...factories.map((item) => [item.code, item.name, "工厂", "生产业务上下文", "正常", "已配置"]),
      ...vehicleModels.map((item) => [item.code, item.name, "车型", "工厂与颜色关系", "正常", "已配置"]),
      ...colors.map((item) => [
        item.code,
        item.name,
        item.color_type === "MIDCOAT" ? "中涂颜色" : "色漆颜色",
        item.supplier ?? "供应商待维护",
        "正常",
        "已配置",
      ]),
      ...parts.map((item) => [
        item.code,
        item.name,
        "零件",
        [item.material, item.region].filter(Boolean).join(" / ") || "属性待维护",
        "正常",
        "已配置",
      ]),
      ...points.map((item) => [
        item.code,
        item.name,
        "测量点",
        [item.region, item.quality_types.join(", ")].filter(Boolean).join(" / ") || "指标待维护",
        item.is_match_point ? "匹配点" : "正常",
        "贡献待确认",
      ]),
    ].slice(0, 12);

    return {
      source: "api",
      stats: [
        { label: "工厂", value: String(summary.factories), note: "已建立业务上下文" },
        { label: "车型", value: String(summary.vehicle_models), note: `${summary.colors} 个颜色配置` },
        { label: "零件", value: String(summary.parts), note: `${summary.measurement_groups} 个测量编组` },
        {
          label: "测量点",
          value: String(summary.measurement_points),
          note: `${summary.approved_point_contributions} 条已审批刷子贡献`,
        },
      ],
      rows,
    };
  } catch {
    return fallbackMasterData;
  }
}

function formatMetric(metric: QualityMetric | undefined): string {
  if (!metric) return "无指标值";
  const value = metric.corrected_value ?? metric.raw_value;
  return `${value}${metric.unit ? ` ${metric.unit}` : ""}`;
}

export async function getQualityPageData(): Promise<ModuleData> {
  try {
    const [summary, measurements] = await Promise.all([
      fetchJson<QualitySummary>("/quality/summary"),
      fetchJson<QualityMeasurement[]>("/quality/measurements?limit=20"),
    ]);
    const validRate = summary.measurements
      ? `${((summary.valid_measurements / summary.measurements) * 100).toFixed(1)}%`
      : "0.0%";
    return {
      source: "api",
      stats: [
        { label: "质量测量记录", value: String(summary.measurements), note: `有效率 ${validRate}` },
        { label: "合格测量", value: String(summary.pass_measurements), note: `${summary.fail_measurements} 条超差` },
        { label: "指标值", value: String(summary.metric_values), note: "橘皮、色差/效应与膜厚" },
        { label: "质量标准", value: String(summary.standards), note: "用于自动符合性判定" },
      ],
      rows: measurements.map((measurement) => {
        const metric = measurement.metrics[0];
        return [
          measurement.data_no,
          measurement.measurement_point_code,
          `${measurement.quality_type} / ${metric?.metric_name ?? "无指标"}`,
          formatMetric(metric),
          measurement.judgement === "PASS"
            ? "合格"
            : measurement.judgement === "FAIL"
              ? "超差"
              : measurement.judgement === "INVALID"
                ? "无效"
                : "无标准",
          new Date(measurement.measured_at).toLocaleString("zh-CN", { hour12: false }),
        ];
      }),
    };
  } catch {
    return fallbackQualityData;
  }
}

export async function getAiWorkbenchData(): Promise<ModuleData> {
  try {
    const models = await fetchJson<ModelVersion[]>("/ai/models");
    const active = models.filter((model) => model.status === "ACTIVE");
    const sampleCount = models.reduce((total, model) => total + model.training_sample_count, 0);
    const r2Values = models
      .map((model) => model.evaluation_metrics.training_r2)
      .filter((value): value is number => typeof value === "number");
    const averageR2 = r2Values.length
      ? (r2Values.reduce((total, value) => total + value, 0) / r2Values.length).toFixed(3)
      : "—";
    return {
      source: "api",
      stats: [
        { label: "已注册模型", value: String(models.length), note: "模型版本可审计追溯" },
        { label: "当前生效模型", value: String(active.length), note: "仅生效模型可在线调用" },
        { label: "训练样本", value: String(sampleCount), note: "基于点位特征快照" },
        { label: "平均训练 R²", value: averageR2, note: "基础模型训练集指标" },
      ],
      rows: models.map((model) => [
        `${model.model_code} · ${model.version}`,
        model.target_metric,
        model.model_type,
        String(model.training_sample_count),
        typeof model.evaluation_metrics.training_r2 === "number"
          ? model.evaluation_metrics.training_r2.toFixed(3)
          : "—",
        model.status,
      ]),
    };
  } catch {
    return fallbackAiData;
  }
}

export async function getProgramsPageData(): Promise<ModuleData> {
  try {
    const programs = await fetchJson<SprayProgram[]>("/spray-programs");
    const versionsByProgram = await Promise.all(
      programs.map((program) =>
        fetchJson<SprayProgramVersion[]>(`/spray-programs/${program.id}/versions`),
      ),
    );
    const versions = versionsByProgram.flat();
    const activeCount = versions.filter((version) => version.status === "ACTIVE").length;
    const masterCount = versions.filter((version) => version.is_master_sample).length;
    const pendingCount = versions.filter((version) => version.status === "PENDING").length;
    return {
      source: "api",
      stats: [
        { label: "喷涂程序", value: String(programs.length), note: "覆盖五个工艺阶段" },
        { label: "当前生效版本", value: String(activeCount), note: "受控版本可追溯" },
        { label: "封样版本", value: String(masterCount), note: "作为参数基准" },
        { label: "待审批版本", value: String(pendingCount), note: "等待工艺审批" },
      ],
      rows: programs.map((program, index) => {
        const version = versionsByProgram[index][0];
        return [
          program.program_code,
          program.name,
          `${program.station_code} · ${program.process_stage}`,
          version?.version ?? "未建版本",
          version?.status ?? "DRAFT",
          program.robot_model ?? "机器人型号待维护",
        ];
      }),
    };
  } catch {
    return fallbackProgramData;
  }
}

export async function getAuditPageData(): Promise<ModuleData> {
  try {
    const [summary, logs] = await Promise.all([
      fetchJson<AuditSummary>("/audit/summary"),
      fetchJson<AuditLog[]>("/audit/logs?limit=100"),
    ]);
    const mostActiveAction = Object.entries(summary.events_by_action).sort(
      ([, left], [, right]) => right - left,
    )[0];
    return {
      source: "api",
      stats: [
        {
          label: "审计事件",
          value: String(summary.total_events),
          note: mostActiveAction ? `最频繁：${mostActiveAction[0]}` : "尚无写操作",
        },
        {
          label: "成功写操作",
          value: String(summary.successful_writes),
          note: "HTTP 状态码小于 400",
        },
        {
          label: "失败写操作",
          value: String(summary.failed_writes),
          note: "包含未认证与无权限请求",
        },
        {
          label: "活跃密钥",
          value: String(summary.active_api_keys),
          note: `${summary.active_users} 个活跃用户`,
        },
      ],
      rows: logs.map((log) => [
        log.request_id.slice(0, 8),
        log.actor_username,
        log.action,
        `${log.http_method} ${log.path}`,
        String(log.status_code),
        new Date(log.occurred_at).toLocaleString("zh-CN", { hour12: false }),
      ]),
    };
  } catch {
    return fallbackAuditData;
  }
}
