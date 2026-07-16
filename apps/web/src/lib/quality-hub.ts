/** Quality hub IA helpers: role home tabs and shortcut chips. */

export type QualityHubTab =
  | "overview"
  | "upload"
  | "measurements"
  | "body-map"
  | "3d-view"
  | "standards"
  | "analytics"
  | "governance";

export const QUALITY_HUB_TABS: Array<{ key: QualityHubTab; label: string }> = [
  { key: "overview", label: "数据可靠性" },
  { key: "upload", label: "批量上传" },
  { key: "measurements", label: "查看与判定" },
  { key: "body-map", label: "车身点位图" },
  { key: "3d-view", label: "3D 车身" },
  { key: "standards", label: "质量标准" },
  { key: "analytics", label: "SPC 与趋势" },
  { key: "governance", label: "仪器可靠性" },
];

export type QualityShortcut = { tab: QualityHubTab; label: string };

/**
 * Role-shaped first screen when visiting /quality without ?tab=.
 * Prefer the job the person does first each day.
 */
export function qualityHomeTab(roles: readonly string[]): QualityHubTab {
  const set = new Set(roles);
  const isAdmin = set.has("ADMIN") || set.has("SYSTEM");
  const isQe = set.has("QUALITY_ENGINEER");
  const isPe = set.has("PROCESS_ENGINEER");
  const isBoss = set.has("APPROVER") || set.has("AUDITOR");

  if (isQe && !isPe) return "upload";
  if (isPe && !isQe) return "body-map";
  if (isBoss && !isQe && !isPe) return "analytics";
  if (isAdmin && !isQe && !isPe) return "governance";
  if (isQe) return "upload";
  if (isPe) return "body-map";
  return "overview";
}

/** Sticky shortcut chips under the hub header — same tabs, shorter path. */
export function qualityShortcuts(roles: readonly string[]): QualityShortcut[] {
  const set = new Set(roles);
  const isAdmin = set.has("ADMIN") || set.has("SYSTEM");
  const isQe = set.has("QUALITY_ENGINEER");
  const isPe = set.has("PROCESS_ENGINEER");
  const isBoss = set.has("APPROVER") || set.has("AUDITOR");

  if (isQe && !isPe) {
    return [
      { tab: "upload", label: "上传" },
      { tab: "measurements", label: "判定" },
      { tab: "standards", label: "标准" },
      { tab: "governance", label: "仪器" },
    ];
  }
  if (isPe && !isQe) {
    return [
      { tab: "body-map", label: "点位图" },
      { tab: "analytics", label: "SPC" },
      { tab: "measurements", label: "判定" },
      { tab: "overview", label: "可靠性" },
    ];
  }
  if (isBoss && !isQe && !isPe) {
    return [
      { tab: "analytics", label: "SPC" },
      { tab: "overview", label: "可靠性" },
      { tab: "body-map", label: "点位图" },
    ];
  }
  if (isAdmin && !isQe && !isPe) {
    return [
      { tab: "governance", label: "仪器" },
      { tab: "standards", label: "标准" },
      { tab: "body-map", label: "点位治理" },
      { tab: "overview", label: "可靠性" },
    ];
  }
  // Mixed / default plant users
  return [
    { tab: "upload", label: "上传" },
    { tab: "measurements", label: "判定" },
    { tab: "body-map", label: "点位图" },
    { tab: "analytics", label: "SPC" },
  ];
}

export type MeasurementStatusFilter =
  | ""
  | "fail"
  | "pass"
  | "no_standard"
  | "unverified"
  | "reliability_failed";

export const MEASUREMENT_STATUS_FILTERS: Array<{
  key: MeasurementStatusFilter;
  label: string;
}> = [
  { key: "", label: "全部" },
  { key: "fail", label: "超差" },
  { key: "pass", label: "合格" },
  { key: "no_standard", label: "无标准" },
  { key: "unverified", label: "未核验" },
  { key: "reliability_failed", label: "核验失败" },
];

export const QUALITY_ANALYTICS_TYPE_KEY = "pq-ai-quality-analytics-type";
