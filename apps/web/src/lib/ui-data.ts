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

export const navItems = [
  { href: "/", label: "工艺质量驾驶舱", icon: "dashboard" },
  { href: "/programs", label: "喷涂程序中心", icon: "program" },
  { href: "/production", label: "生产实绩中心", icon: "production" },
  { href: "/material-trends", label: "材料批次趋势", icon: "material" },
  { href: "/quality", label: "质量数据中心", icon: "quality" },
  { href: "/engineering", label: "工程闭环中心", icon: "engineering" },
  { href: "/quality-monitor", label: "数据质量监控", icon: "monitor" },
  { href: "/import-wizard", label: "数据导入向导", icon: "import" },
  { href: "/ai-workbench", label: "AI 闭环工作台", icon: "ai" },
  { href: "/controlled-trials", label: "受控试验中心", icon: "trial" },
  { href: "/master-data", label: "主数据中心", icon: "master" },
  { href: "/integrations", label: "集成与任务中心", icon: "integration" },
  { href: "/integration-monitor", label: "集成监控", icon: "monitor" },
  { href: "/audit", label: "审计中心", icon: "audit" },
] as const;
