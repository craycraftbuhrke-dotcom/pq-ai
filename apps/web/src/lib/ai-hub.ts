/** AI hub IA helpers: role home tabs and shortcut chips. */

export type AiHubTab =
  | "overview"
  | "predictions"
  | "recommendations"
  | "changes"
  | "models"
  | "comparison";

export const AI_HUB_TABS: Array<{ key: AiHubTab; label: string }> = [
  { key: "overview", label: "概览" },
  { key: "predictions", label: "预测与诊断" },
  { key: "recommendations", label: "推荐与试验" },
  { key: "changes", label: "工艺变更" },
  { key: "models", label: "训练与验收" },
  { key: "comparison", label: "模型对比" },
];

export type AiShortcut = { tab: AiHubTab; label: string };

/**
 * Role-shaped first screen when visiting /ai without ?tab=.
 * Data scientists care about models; process engineers and approvers care
 * about the recommendation queue; admins land on the overview.
 */
export function aiHomeTab(roles: readonly string[]): AiHubTab {
  const set = new Set(roles);
  const isAdmin = set.has("ADMIN") || set.has("SYSTEM");
  const isDs = set.has("DATA_SCIENTIST");
  const isPe = set.has("PROCESS_ENGINEER");
  const isApprover = set.has("APPROVER");

  if (isDs && !isPe && !isApprover) return "models";
  if (isPe && !isDs) return "recommendations";
  if (isApprover && !isDs && !isPe) return "recommendations";
  if (isAdmin && !isDs && !isPe && !isApprover) return "overview";
  if (isDs) return "models";
  if (isPe || isApprover) return "recommendations";
  return "overview";
}

/** Sticky shortcut chips under the hub header — same tabs, shorter path. */
export function aiShortcuts(roles: readonly string[]): AiShortcut[] {
  const set = new Set(roles);
  const isAdmin = set.has("ADMIN") || set.has("SYSTEM");
  const isDs = set.has("DATA_SCIENTIST");
  const isPe = set.has("PROCESS_ENGINEER");
  const isApprover = set.has("APPROVER");

  if (isDs && !isPe && !isApprover) {
    return [
      { tab: "models", label: "模型" },
      { tab: "comparison", label: "对比" },
      { tab: "predictions", label: "预测" },
      { tab: "overview", label: "概览" },
    ];
  }
  if ((isPe || isApprover) && !isDs) {
    return [
      { tab: "recommendations", label: "推荐" },
      { tab: "changes", label: "变更" },
      { tab: "predictions", label: "预测" },
      { tab: "overview", label: "概览" },
    ];
  }
  if (isAdmin && !isDs && !isPe && !isApprover) {
    return [
      { tab: "overview", label: "概览" },
      { tab: "models", label: "模型" },
      { tab: "recommendations", label: "推荐" },
      { tab: "changes", label: "变更" },
    ];
  }
  // Mixed / default users
  return [
    { tab: "overview", label: "概览" },
    { tab: "predictions", label: "预测" },
    { tab: "recommendations", label: "推荐" },
    { tab: "models", label: "模型" },
  ];
}
