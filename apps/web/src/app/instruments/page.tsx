"use client";

import { Suspense } from "react";

import { DomainHub } from "@/components/domain-hub";
import { InstrumentsOverviewPanel } from "@/components/instruments-overview-panel";
import { MeasurementGovernancePanel } from "@/components/measurement-governance-panel";

const TABS = [
  { key: "overview", label: "概览" },
  { key: "governance", label: "仪器治理" },
];

function InstrumentsHubInner() {
  return (
    <DomainHub
      title="仪器管理中心"
      tabs={TABS}
      defaultTab="overview"
    >
      {(tab) => {
        if (tab === "governance") return <MeasurementGovernancePanel />;
        return <InstrumentsOverviewPanel embedded />;
      }}
    </DomainHub>
  );
}

export default function InstrumentsPage() {
  return (
    <Suspense
      fallback={
        <div className="page-stack">
          <div className="master-empty">正在加载仪器管理中心…</div>
        </div>
      }
    >
      <InstrumentsHubInner />
    </Suspense>
  );
}
