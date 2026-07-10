"use client";

import { Suspense } from "react";

import QualityMonitorPage from "@/app/quality-monitor/page";
import { BodyPointMap } from "@/components/body-point-map";
import { DomainHub } from "@/components/domain-hub";
import { QualityWorkspace } from "@/components/quality-workspace";

const TABS = [
  { key: "overview", label: "概览与 SPC" },
  { key: "upload", label: "批量上传" },
  { key: "measurements", label: "查看与判定" },
  { key: "body-map", label: "车身点位图" },
  { key: "standards", label: "质量标准" },
  { key: "analytics", label: "SPC 与趋势" },
  { key: "governance", label: "仪器可靠性" },
];

function QualityHubInner() {
  return (
    <DomainHub
      kicker="质量管理"
      title="质量管理中心"
      description="统一完成质量概览、批量上传、判定、车身点位图、标准、SPC 与仪器可靠性。日常上数从「批量上传」开始。"
      tabs={TABS}
      defaultTab="overview"
    >
      {(tab) => {
        if (tab === "overview") return <QualityMonitorPage embedded />;
        if (tab === "upload") return <QualityWorkspace mode="embed" lockedTab="upload" />;
        if (tab === "measurements") return <QualityWorkspace mode="embed" lockedTab="measurements" />;
        if (tab === "body-map") return <BodyPointMap />;
        if (tab === "standards") return <QualityWorkspace mode="embed" lockedTab="standards" />;
        if (tab === "analytics") return <QualityWorkspace mode="embed" lockedTab="analytics" />;
        if (tab === "governance") return <QualityWorkspace mode="embed" lockedTab="governance" />;
        return <QualityMonitorPage embedded />;
      }}
    </DomainHub>
  );
}

export default function QualityPage() {
  return (
    <Suspense fallback={<div className="page-stack"><div className="master-empty">正在加载质量管理中心…</div></div>}>
      <QualityHubInner />
    </Suspense>
  );
}
