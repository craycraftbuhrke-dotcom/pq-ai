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
    title: "今日工作",
    items: [{ href: "/", label: "今日工作", icon: "dashboard" }],
  },
  {
    key: "ai",
    title: "智能分析",
    items: [
      {
        href: "/ai",
        label: "智能分析",
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
    title: "基础资料",
    items: [
      {
        href: "/master-data",
        label: "基础资料",
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
    description: "维护喷涂程序和刷子参数，查看五道工序的实际执行情况。",
    icon: "program",
    links: [
      { href: "/process?tab=overview", label: "工艺概况" },
      { href: "/process?tab=simulation", label: "五道工序" },
      { href: "/process?tab=recipes", label: "程序与刷子参数" },
      { href: "/process?tab=runs", label: "生产实际参数" },
    ],
  },
  {
    key: "materials",
    href: "/materials",
    title: "油漆材料",
    description: "核对材料批次、粘度、固含量和供应商检测结果。",
    icon: "material",
    links: [
      { href: "/materials?tab=overview", label: "材料趋势" },
      { href: "/materials?tab=batches", label: "材料批次" },
      { href: "/materials?tab=governance", label: "材料规格与检测" },
    ],
  },
  {
    key: "quality",
    href: "/quality",
    title: "质量管理",
    description: "导入橘皮、色差和膜厚数据，完成判定、复核与点位追溯。",
    icon: "quality",
    links: [
      { href: "/quality?tab=upload", label: "导入检测数据" },
      { href: "/quality?tab=measurements", label: "检测结果与判定" },
      { href: "/quality?tab=body-map", label: "车身点位图" },
      { href: "/quality?tab=3d-view", label: "立体车身点位" },
      { href: "/quality?tab=analytics", label: "质量趋势" },
      { href: "/instruments", label: "仪器管理" },
    ],
  },
  {
    key: "master",
    href: "/master-data",
    title: "基础资料",
    description: "维护工厂、车型、颜色、零件、测量点和机器人信息。",
    icon: "master",
    roles: ["ADMIN", "PROCESS_ENGINEER", "QUALITY_ENGINEER", "INTEGRATION_OPERATOR"],
    links: [
      { href: "/master-data?tab=entities", label: "工厂、车型与颜色" },
      { href: "/quality?tab=body-map", label: "测量编组与点位" },
      { href: "/master-data?tab=robots", label: "机器人与喷涂轨迹" },
    ],
  },
  {
    key: "ai",
    href: "/ai",
    title: "智能分析",
    description: "根据车号和点位进行质量预测、原因排查和参数建议。",
    icon: "ai",
    roles: ["DATA_SCIENTIST", "PROCESS_ENGINEER", "QUALITY_ENGINEER", "APPROVER", "ADMIN"],
    links: [
      { href: "/ai?tab=predictions", label: "质量预测与原因排查" },
      { href: "/ai?tab=recommendations", label: "参数建议与现场试验" },
      { href: "/ai?tab=changes", label: "问题处理与工艺变更" },
    ],
  },
  {
    key: "settings",
    href: "/settings",
    title: "系统设置",
    description: "管理外部系统对接、运行情况、操作记录和账号权限。",
    icon: "integration",
    roles: ["ADMIN", "INTEGRATION_OPERATOR", "AUDITOR"],
    links: [
      { href: "/settings?tab=integrations", label: "外部系统对接" },
      { href: "/settings?tab=monitor", label: "数据接收情况" },
      { href: "/settings?tab=audit", label: "操作记录" },
    ],
  },
] as const;
