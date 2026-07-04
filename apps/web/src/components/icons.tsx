import {
  Activity,
  Bot,
  Boxes,
  ChartNoAxesCombined,
  CircleGauge,
  ClipboardList,
  ClipboardCheck,
  Database,
  Factory,
  FlaskConical,
  GitCompareArrows,
  LayoutDashboard,
  PlugZap,
  ScrollText,
  type LucideIcon,
} from "lucide-react";

export const navigationIcons: Record<string, LucideIcon> = {
  dashboard: LayoutDashboard,
  program: GitCompareArrows,
  quality: FlaskConical,
  ai: Bot,
  master: Database,
  audit: ScrollText,
  integration: PlugZap,
  production: Activity,
  engineering: ClipboardList,
};

export const metricIcons = {
  health: CircleGauge,
  passRate: ClipboardCheck,
  runs: Activity,
  risk: ChartNoAxesCombined,
  factory: Factory,
  assets: Boxes,
};
