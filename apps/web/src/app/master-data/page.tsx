"use client";

import { Suspense } from "react";

import { DomainHub } from "@/components/domain-hub";
import { MasterDataWorkspace } from "@/components/master-data-workspace";
import { ProgramWorkspace } from "@/components/program-workspace";

const TABS = [
  { key: "entities", label: "组织与产品" },
  { key: "measurement", label: "测量体系" },
  { key: "robots", label: "机器人与轨迹" },
];

function MasterDataHubInner() {
  return (
    <DomainHub
      kicker="主数据"
      title="主数据中心"
      description="维护工厂、车型、颜色、零件、测量点，以及机器人设备与轨迹治理。"
      tabs={TABS}
      defaultTab="entities"
    >
      {(tab) => {
        if (tab === "measurement") return <MasterDataWorkspace mode="measurement" />;
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
