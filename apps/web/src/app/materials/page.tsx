"use client";

import { Suspense } from "react";

import { DomainHub } from "@/components/domain-hub";
import { ProductionWorkspace } from "@/components/production-workspace";
import { MaterialTrendsPanel } from "@/components/material-trends-panel";

const TABS = [
  { key: "overview", label: "概览与 SPC" },
  { key: "batches", label: "材料批次" },
  { key: "governance", label: "特性治理" },
];

function MaterialsHubInner() {
  return (
    <DomainHub
      title="材料管理中心"
      tabs={TABS}
      defaultTab="overview"
    >
      {(tab) => {
        if (tab === "batches") return <ProductionWorkspace mode="materials" />;
        if (tab === "governance") return <ProductionWorkspace mode="material-governance" />;
        return <div className="embedded-stack"><MaterialTrendsPanel embedded /></div>;
      }}
    </DomainHub>
  );
}

export default function MaterialsPage() {
  return (
    <Suspense fallback={<div className="page-stack"><div className="master-empty">正在加载材料管理中心…</div></div>}>
      <MaterialsHubInner />
    </Suspense>
  );
}
