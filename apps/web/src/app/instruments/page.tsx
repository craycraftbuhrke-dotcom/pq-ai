"use client";

import { Suspense } from "react";

import { DomainHub } from "@/components/domain-hub";
import { MeasurementGovernancePanel } from "@/components/measurement-governance-panel";

const TABS = [{ key: "ledger", label: "仪器台账" }];

function InstrumentsHubInner() {
  return (
    <DomainHub title="仪器管理中心" tabs={TABS} defaultTab="ledger">
      {() => <MeasurementGovernancePanel />}
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
