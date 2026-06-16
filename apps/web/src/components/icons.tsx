import {
  Activity,
  Bot,
  Boxes,
  ChartNoAxesCombined,
  CircleGauge,
  ClipboardCheck,
  Crosshair,
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
  trial: Crosshair,
  master: Database,
  audit: ScrollText,
  integration: PlugZap,
  production: Activity,
};

export const metricIcons = {
  health: CircleGauge,
  passRate: ClipboardCheck,
  runs: Activity,
  risk: ChartNoAxesCombined,
  factory: Factory,
  assets: Boxes,
};
