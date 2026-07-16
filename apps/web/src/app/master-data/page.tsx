"use client";

import { Suspense } from "react";

import { DomainHub } from "@/components/domain-hub";
import { MasterDataWorkspace } from "@/components/master-data-workspace";
import { ProgramWorkspace } from "@/components/program-workspace";

const TABS = [
  { key: "entities", label: "组织与产品" },
  { key: "robots", label: "机器人与轨迹" },
];

function MasterDataHubInner() {
  return (
    <DomainHub
      title="主数据中心"
      tabs={TABS}
      defaultTab="entities"
    >
      {(tab) => {
        if (tab === "robots") return <ProgramWorkspace mode="durr" />;
        return <MasterDataWorkspace mode="entities" />;
      }}
    </DomainHub>
  );
}

export default function MasterDataPage() {
  return (
    <Suspense fallback={<div className="page-stack"><div className="master-empty">正在加载主数据中心…</div></div>}>
      <MasterDataHubInner />
    </Suspense>
  );
}
