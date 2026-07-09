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

export const navSections: readonly NavSection[] = [
  {
    key: "overview",
    title: "总览",
    items: [{ href: "/", label: "工艺质量总览", icon: "dashboard" }],
  },
  {
    key: "execution",
    title: "现场执行",
    items: [
      { href: "/programs", label: "工艺配方管理", icon: "program" },
      { href: "/production", label: "生产执行记录", icon: "production" },
      { href: "/material-trends", label: "材料批次分析", icon: "material" },
    ],
  },
  {
    key: "improvement",
    title: "质量改进",
    items: [
      { href: "/quality", label: "质量测量与标准", icon: "quality" },
      { href: "/quality-monitor", label: "质量数据监控", icon: "monitor" },
      { href: "/engineering", label: "工程问题闭环", icon: "engineering" },
      { href: "/ai-workbench", label: "AI 优化工作台", icon: "ai", roles: ["DATA_SCIENTIST", "PROCESS_ENGINEER", "QUALITY_ENGINEER", "APPROVER"] },
      { href: "/controlled-trials", label: "受控试验管理", icon: "trial" },
    ],
  },
  {
    key: "governance",
    title: "治理工具",
    collapsible: true,
    items: [
      { href: "/import-wizard", label: "批量数据导入", icon: "import" },
      { href: "/master-data", label: "主数据治理", icon: "master", roles: ["ADMIN", "PROCESS_ENGINEER", "QUALITY_ENGINEER", "INTEGRATION_OPERATOR"] },
      { href: "/integrations", label: "系统集成任务", icon: "integration", roles: ["ADMIN", "INTEGRATION_OPERATOR"] },
      { href: "/integration-monitor", label: "集成运行监控", icon: "monitor", roles: ["ADMIN", "INTEGRATION_OPERATOR", "AUDITOR"] },
      { href: "/audit", label: "审计追溯", icon: "audit", roles: ["ADMIN", "AUDITOR"] },
    ],
  },
] as const;

export const roleQuickAccess: Record<string, readonly string[]> = {
  ADMIN: ["/", "/master-data", "/integrations", "/integration-monitor", "/security-admin"],
  PROCESS_ENGINEER: ["/programs", "/production", "/engineering", "/controlled-trials", "/material-trends"],
  QUALITY_ENGINEER: ["/quality", "/quality-monitor", "/engineering", "/controlled-trials", "/audit"],
  DATA_SCIENTIST: ["/ai-workbench", "/quality", "/quality-monitor", "/controlled-trials", "/engineering"],
  APPROVER: ["/controlled-trials", "/engineering", "/quality", "/quality-monitor", "/"],
  INTEGRATION_OPERATOR: ["/integrations", "/integration-monitor", "/import-wizard", "/master-data", "/"],
  AUDITOR: ["/audit", "/quality-monitor", "/integration-monitor", "/quality", "/"],
  ROBOT_OPERATOR: ["/production", "/programs", "/quality", "/material-trends", "/"],
  SYSTEM: ["/", "/programs", "/quality", "/master-data", "/integrations"],
};
