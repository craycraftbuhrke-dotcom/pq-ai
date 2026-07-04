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

export const stages: ProcessStage[] = [
  {
    code: "MIDCOAT_EXT",
    name: "中涂外喷",
    station: "P1F1A1",
    health: 96,
    status: "healthy",
    flow: 342,
    rpm: 45000,
  },
  {
    code: "BASECOAT_1",
    name: "色漆一站",
    station: "P1B1A1",
    health: 93,
    status: "healthy",
    flow: 286,
    rpm: 48000,
  },
  {
    code: "BASECOAT_2",
    name: "色漆二站",
    station: "P1B1A2",
    health: 86,
    status: "warning",
    flow: 212,
    rpm: 50000,
  },
  {
    code: "CLEARCOAT_1",
    name: "清漆一站",
    station: "P1C1A1",
    health: 91,
    status: "healthy",
    flow: 302,
    rpm: 47000,
  },
  {
    code: "CLEARCOAT_2",
    name: "清漆二站",
    station: "P1C1A2",
    health: 78,
    status: "risk",
    flow: 315,
    rpm: 46000,
  },
];

export const riskPoints: RiskPoint[] = [
  {
    code: "P-ROOF-03",
    name: "车顶中部 03",
    part: "车顶",
    metric: "DOI",
    predicted: "78.2",
    standard: "≥ 82",
    risk: 86,
  },
  {
    code: "P-HOOD-06",
    name: "发动机罩 06",
    part: "发动机罩",
    metric: "总膜厚",
    predicted: "116.8 μm",
    standard: "120–145 μm",
    risk: 72,
  },
  {
    code: "P-LD-02",
    name: "左前门 02",
    part: "左前门",
    metric: "dE45",
    predicted: "0.71",
    standard: "≤ 0.80",
    risk: 39,
  },
];

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

export const recommendationActions: RecommendationAction[] = [
  {
    stage: "清漆二站",
    brush: "B-042",
    parameter: "外成型空气流量",
    current: "410",
    recommended: "385",
    unit: "Nl/min",
  },
  {
    stage: "清漆二站",
    brush: "B-042",
    parameter: "喷涂流量",
    current: "315",
    recommended: "326",
    unit: "ml/min",
  },
];
