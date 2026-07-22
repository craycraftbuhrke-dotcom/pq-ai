/** AI hub IA helpers: role home tabs and shortcut chips. */

export type AiHubTab = "overview" | "models" | "comparison";

export const AI_HUB_TABS: Array<{ key: AiHubTab; label: string }> = [
  { key: "overview", label: "概览" },
  { key: "models", label: "训练与验收" },
  { key: "comparison", label: "模型对比" },
];

export type AiShortcut = { tab: AiHubTab; label: string };

/**
 * Role-shaped first screen when visiting /ai without ?tab=.
 * Field prediction / recommendation / change work moved to /process.
 */
export function aiHomeTab(roles: readonly string[]): AiHubTab {
  const set = new Set(roles);
  const isDs = set.has("DATA_SCIENTIST");
  if (isDs) return "models";
  return "overview";
}

/** Sticky shortcut chips under the hub header. */
export function aiShortcuts(roles: readonly string[]): AiShortcut[] {
  const set = new Set(roles);
  const isDs = set.has("DATA_SCIENTIST");
  if (isDs) {
    return [
      { tab: "models", label: "模型" },
      { tab: "comparison", label: "对比" },
      { tab: "overview", label: "概览" },
    ];
  }
  return [
    { tab: "overview", label: "概览" },
    { tab: "models", label: "模型" },
    { tab: "comparison", label: "对比" },
  ];
}
