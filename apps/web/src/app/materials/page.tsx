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
      kicker="油漆材料"
      title="材料管理中心"
      description="维护材料批次、特性治理与批次检测趋势。材料结果经治理后才可进入 AI 特征。"
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
