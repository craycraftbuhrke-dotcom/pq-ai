/** 面向现场用户的中文展示标签。技术码仅作次要信息或内部值。 */

export const PROCESS_STAGE_LABELS: Record<string, string> = {
  MIDCOAT_EXT: "中涂外喷",
  BASECOAT_1: "色漆一站",
  BASECOAT_2: "色漆二站",
  CLEARCOAT_1: "清漆一站",
  CLEARCOAT_2: "清漆二站",
};

export const QUALITY_TYPE_LABELS: Record<string, string> = {
  ORANGE_PEEL: "橘皮",
  COLOR_DIFFERENCE: "色差",
  THICKNESS: "膜厚",
};

export const ROLE_LABELS: Record<string, string> = {
  ADMIN: "系统管理员",
  PROCESS_ENGINEER: "工艺工程师",
  QUALITY_ENGINEER: "质量工程师",
  DATA_SCIENTIST: "数据分析师",
  APPROVER: "审批人",
  ROBOT_OPERATOR: "机器人操作员",
  INTEGRATION_OPERATOR: "集成运维",
  AUDITOR: "审计员",
  SYSTEM: "系统",
};

export const RELIABILITY_LABELS: Record<string, string> = {
  VERIFIED: "已验证",
  UNVERIFIED: "待验证",
  FAILED: "未通过",
};

const GENERIC_STATUS_LABELS: Record<string, string> = {
  ACTIVE: "已生效",
  INACTIVE: "已停用",
  DRAFT: "草稿",
  PENDING: "待处理",
  APPROVED: "已批准",
  REJECTED: "已驳回",
  EXECUTED: "已执行",
  VERIFIED: "已验证",
  COMPLETED: "已完成",
  RUNNING: "进行中",
  PLANNED: "已计划",
  CANCELLED: "已取消",
  RETIRED: "已退役",
  SUCCEEDED: "成功",
  FAILED: "失败",
  DEAD_LETTER: "需人工处理",
  ROLLED_BACK: "已回滚",
  INEFFECTIVE: "无效",
  ACCEPTED: "已验收",
  IN_SCOPE: "适用范围内",
  OUT_OF_SCOPE: "超出适用范围",
  IN_DISTRIBUTION: "数据正常",
  OUT_OF_DISTRIBUTION: "数据异常偏高",
  OOD: "数据异常",
  TRAIN: "训练",
  VALIDATION: "验证",
  TEST: "测试",
  MASTER_SAMPLE: "封样",
  STANDARD: "标准件",
  MANUAL: "手工",
  AI: "智能推荐",
  IMPORT: "导入",
  HEALTHY: "正常",
  WARNING: "关注",
  RISK: "风险",
  DRIFT: "漂移",
  STABLE: "稳定",
  INSUFFICIENT: "数据不足",
  PASSED: "通过",
  BLOCKED: "已阻断",
  QUALITY_ISSUE: "质量问题",
  CONTROLLED_TRIAL: "受控试验",
  DURR_DXQ: "Dürr DXQ 文件",
  DURR_PLC: "Dürr PLC 文件",
  MATERIAL_COA: "材料 COA",
  MATERIAL_TDS: "材料 TDS",
  INBOUND: "接入",
  OUTBOUND: "外发",
  BIDIRECTIONAL: "双向",
  API_KEY: "系统访问密钥",
  OAUTH2: "统一登录授权",
  BASIC: "账号密码验证",
  NONE: "不验证",
  MES: "生产系统",
  QMS: "质量系统",
  ROBOT: "机器人",
  MATERIAL: "材料系统",
  MEASUREMENT: "测量系统",
  MES_PRODUCTION_RUN_UPSERT: "同步生产车身",
  MATERIAL_BATCH_UPSERT: "同步材料批次",
  QMS_QUALITY_MEASUREMENT_UPSERT: "同步质量测量",
  ROBOT_ACTUAL_PARAMETERS_UPSERT: "同步喷涂实绩",
  ROBOT_TRAJECTORY_EXECUTION_UPSERT: "同步轨迹执行",
  SHAP: "特征贡献解释",
  GRR: "重复性再现性",
  NDC: "分辨力",
  DXQ_SIMULATION: "DXQ 仿真",
  CORRELATION_ONLY: "仅关联分析",
  BYK_ORANGE_PEEL: "BYK 橘皮仪",
  BYK_COLOR: "BYK 色差仪",
  FISCHER_THICKNESS: "Fischer 膜厚仪",
  MATCH: "匹配点",
  PROCESS: "工艺点",
  QUALITY: "质量点",
  THICKNESS: "膜厚",
  COLOR: "色差",
  ORANGE_PEEL: "橘皮",
  approval: "审批",
  execution: "执行",
  verification: "复测",
  rollback: "回滚",
};

export function displayLabel(
  value: string | null | undefined,
  maps: Array<Record<string, string>> = [],
): string {
  if (!value) return "—";
  for (const map of maps) {
    if (map[value]) return map[value];
  }
  if (GENERIC_STATUS_LABELS[value]) return GENERIC_STATUS_LABELS[value];
  if (PROCESS_STAGE_LABELS[value]) return PROCESS_STAGE_LABELS[value];
  if (QUALITY_TYPE_LABELS[value]) return QUALITY_TYPE_LABELS[value];
  if (ROLE_LABELS[value]) return ROLE_LABELS[value];
  if (RELIABILITY_LABELS[value]) return RELIABILITY_LABELS[value];
  return value;
}

export function stageLabel(code: string | null | undefined): string {
  return displayLabel(code, [PROCESS_STAGE_LABELS]);
}

export function qualityTypeLabel(code: string | null | undefined): string {
  return displayLabel(code, [QUALITY_TYPE_LABELS]);
}

export function roleLabel(code: string | null | undefined): string {
  return displayLabel(code, [ROLE_LABELS]);
}

export function reliabilityLabel(code: string | null | undefined): string {
  return displayLabel(code, [RELIABILITY_LABELS]);
}

export function statusLabel(code: string | null | undefined): string {
  return displayLabel(code);
}

export function primaryRoleLabel(roles: string[]): string {
  if (!roles.length) return "已认证用户";
  return roleLabel(roles[0]);
}

/** 选项：中文主文案，技术码作 value */
export function labeledOptions(map: Record<string, string>): Array<[string, string]> {
  return Object.entries(map).map(([code, label]) => [code, label]);
}

export const SAVE_BUTTON_LABEL = "保存";
export const SAVING_BUTTON_LABEL = "正在保存";
export const DATA_LIVE_HINT = "当前为实时业务数据";
export const NO_PHYSICAL_DELETE_HINT =
  "系统不支持直接删除记录，请使用停用、归档或版本替换。";
