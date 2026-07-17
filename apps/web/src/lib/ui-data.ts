export type ProcessStage = {
  code: string;
  name: string;
  station: string;
  health: number;
  status: "healthy" | "warning" | "risk";
  flow: number;
  rpm: number;
};

export type RiskPoint = {
  code: string;
  name: string;
  part: string;
  metric: string;
  predicted: string;
  standard: string;
  risk: number;
};

export type RecommendationAction = {
  stage: string;
  brush: string;
  parameter: string;
  current: string;
  recommended: string;
  unit: string;
};

export type NavItem = {
  href: string;
  label: string;
  icon: string;
  roles?: readonly string[];
};

export type NavSection = {
  key: string;
  title: string;
  collapsible?: boolean;
  items: readonly NavItem[];
};

/** 侧滑栏一级导航：每项直接链接到对应域，无二级标题。 */
export const navSections: readonly NavSection[] = [
  {
    key: "home",
    title: "驾驶舱",
    items: [{ href: "/", label: "驾驶舱", icon: "dashboard" }],
  },
  {
    key: "ai",
    title: "AI 闭环",
    items: [
      {
        href: "/ai",
        label: "AI 闭环",
        icon: "ai",
        roles: ["DATA_SCIENTIST", "PROCESS_ENGINEER", "QUALITY_ENGINEER", "APPROVER", "ADMIN"],
      },
    ],
  },
  {
    key: "process",
    title: "工艺管理",
    items: [{ href: "/process", label: "工艺管理", icon: "program" }],
  },
  {
    key: "quality",
    title: "质量管理",
    items: [{ href: "/quality", label: "质量管理", icon: "quality" }],
  },
  {
    key: "materials",
    title: "油漆材料",
    items: [{ href: "/materials", label: "油漆材料", icon: "material" }],
  },
  {
    key: "instruments",
    title: "仪器管理",
    items: [{ href: "/instruments", label: "仪器管理", icon: "monitor" }],
  },
  {
    key: "master",
    title: "主数据",
    items: [
      {
        href: "/master-data",
        label: "主数据",
        icon: "master",
        roles: ["ADMIN", "PROCESS_ENGINEER", "QUALITY_ENGINEER", "INTEGRATION_OPERATOR"],
      },
    ],
  },
  {
    key: "settings",
    title: "系统设置",
    items: [
      {
        href: "/settings",
        label: "系统设置",
        icon: "integration",
        roles: ["ADMIN", "INTEGRATION_OPERATOR", "AUDITOR"],
      },
    ],
  },
  {
    key: "profile",
    title: "个人中心",
    items: [{ href: "/profile", label: "个人中心", icon: "audit" }],
  },
] as const;

export type DomainPortalCard = {
  key: string;
  href: string;
  title: string;
  description: string;
  icon: string;
  roles?: readonly string[];
  links: Array<{ href: string; label: string }>;
};

export const domainPortalCards: readonly DomainPortalCard[] = [
  {
    key: "process",
    href: "/process",
    title: "工艺管理",
    description: "喷涂程序、虚拟产线、刷子参数、贡献权重与生产实绩。",
    icon: "program",
    links: [
      { href: "/process?tab=overview", label: "概览" },
      { href: "/process?tab=simulation", label: "虚拟产线" },
      { href: "/process?tab=recipes", label: "配方与刷子" },
      { href: "/process?tab=runs", label: "生产实绩" },
    ],
  },
  {
    key: "materials",
    href: "/materials",
    title: "油漆材料",
    description: "材料批次、特性治理与批次趋势 SPC。",
    icon: "material",
    links: [
      { href: "/materials?tab=overview", label: "概览与 SPC" },
      { href: "/materials?tab=batches", label: "材料批次" },
      { href: "/materials?tab=governance", label: "特性治理" },
    ],
  },
  {
    key: "quality",
    href: "/quality",
    title: "质量管理",
    description: "橘皮/色差/膜厚上传、判定、标准与车身点位。",
    icon: "quality",
    links: [
      { href: "/quality?tab=upload", label: "批量上传" },
      { href: "/quality?tab=measurements", label: "查看与判定" },
      { href: "/quality?tab=body-map", label: "车身点位图" },
      { href: "/quality?tab=3d-view", label: "3D 车身" },
      { href: "/quality?tab=analytics", label: "SPC 与趋势" },
      { href: "/instruments", label: "仪器管理" },
    ],
  },
  {
    key: "master",
    href: "/master-data",
    title: "主数据",
    description: "工厂、车型、零件、颜色与机器人轨迹。",
    icon: "master",
    roles: ["ADMIN", "PROCESS_ENGINEER", "QUALITY_ENGINEER", "INTEGRATION_OPERATOR"],
    links: [
      { href: "/master-data?tab=entities", label: "组织与产品" },
      { href: "/quality?tab=body-map", label: "测量编组与点位" },
      { href: "/master-data?tab=robots", label: "机器人与轨迹" },
    ],
  },
  {
    key: "ai",
    href: "/ai",
    title: "AI 智能分析",
    description: "训练验收、预测诊断、推荐试验与工艺变更闭环。",
    icon: "ai",
    roles: ["DATA_SCIENTIST", "PROCESS_ENGINEER", "QUALITY_ENGINEER", "APPROVER", "ADMIN"],
    links: [
      { href: "/ai?tab=predictions", label: "预测与诊断" },
      { href: "/ai?tab=recommendations", label: "推荐与试验" },
      { href: "/ai?tab=changes", label: "工艺变更" },
    ],
  },
  {
    key: "settings",
    href: "/settings",
    title: "系统设置",
    description: "系统对接、运行监控、审计与账号权限。",
    icon: "integration",
    roles: ["ADMIN", "INTEGRATION_OPERATOR", "AUDITOR"],
    links: [
      { href: "/settings?tab=integrations", label: "系统对接" },
      { href: "/settings?tab=monitor", label: "对接监控" },
      { href: "/settings?tab=audit", label: "操作审计" },
    ],
  },
] as const;
