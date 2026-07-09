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

/** 按现场任务组织，而不是按系统模块堆叠 */
export const navSections: readonly NavSection[] = [
  {
    key: "today",
    title: "今日工作",
    items: [{ href: "/", label: "今日总览", icon: "dashboard" }],
  },
  {
    key: "field",
    title: "现场作业",
    items: [
      { href: "/quality", label: "录入与查看质量", icon: "quality" },
      { href: "/import-wizard", label: "批量导入测量", icon: "import" },
      { href: "/production", label: "生产车身记录", icon: "production" },
      { href: "/programs", label: "喷涂配方", icon: "program" },
    ],
  },
  {
    key: "improve",
    title: "问题处理",
    items: [
      { href: "/quality-monitor", label: "数据是否可信", icon: "monitor" },
      { href: "/engineering", label: "问题与调试", icon: "engineering" },
      {
        href: "/ai-workbench",
        label: "智能分析与推荐",
        icon: "ai",
        roles: ["DATA_SCIENTIST", "PROCESS_ENGINEER", "QUALITY_ENGINEER", "APPROVER", "ADMIN"],
      },
      { href: "/controlled-trials", label: "受控试验", icon: "trial" },
    ],
  },
  {
    key: "analysis",
    title: "材料与趋势",
    items: [{ href: "/material-trends", label: "材料批次趋势", icon: "material" }],
  },
  {
    key: "settings",
    title: "基础设置",
    collapsible: true,
    items: [
      {
        href: "/master-data",
        label: "工厂与测量点",
        icon: "master",
        roles: ["ADMIN", "PROCESS_ENGINEER", "QUALITY_ENGINEER", "INTEGRATION_OPERATOR"],
      },
      {
        href: "/integrations",
        label: "系统对接",
        icon: "integration",
        roles: ["ADMIN", "INTEGRATION_OPERATOR"],
      },
      {
        href: "/integration-monitor",
        label: "对接运行状态",
        icon: "monitor",
        roles: ["ADMIN", "INTEGRATION_OPERATOR", "AUDITOR"],
      },
      {
        href: "/audit",
        label: "操作审计",
        icon: "audit",
        roles: ["ADMIN", "AUDITOR"],
      },
    ],
  },
] as const;
