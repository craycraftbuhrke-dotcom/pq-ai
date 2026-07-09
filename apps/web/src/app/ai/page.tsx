"use client";

import { Suspense } from "react";

import ControlledTrialsPage from "@/app/controlled-trials/page";
import { AiWorkbench } from "@/components/ai-workbench";
import { DomainHub } from "@/components/domain-hub";
import { EngineeringWorkspace } from "@/components/engineering-workspace";

const TABS = [
  { key: "predictions", label: "预测与诊断" },
  { key: "recommendations", label: "推荐与试验" },
  { key: "changes", label: "工艺变更" },
  { key: "models", label: "训练与验收" },
  { key: "comparison", label: "模型对比" },
];

function AiHubInner() {
  return (
    <DomainHub
      kicker="AI 智能分析"
      title="AI 分析中心"
      description="预测诊断、推荐与受控试验、工艺变更闭环，以及模型训练验收。推荐与试验、工艺变更放在同一工作台。"
      tabs={TABS}
      defaultTab="predictions"
    >
      {(tab) => {
        if (tab === "recommendations") {
          return (
            <div className="ai-split-embed">
              <AiWorkbench mode="embed" lockedTab="recommendations" />
              <ControlledTrialsPage embedded />
            </div>
          );
        }
        if (tab === "changes") {
          return <EngineeringWorkspace mode="embed" lockedTab="issues" />;
        }
        if (tab === "models") {
          return <AiWorkbench mode="embed" allowedTabs={["models", "governance"]} />;
        }
        if (tab === "comparison") {
          return <AiWorkbench mode="embed" lockedTab="comparison" />;
        }
        return <AiWorkbench mode="embed" lockedTab="predictions" />;
      }}
    </DomainHub>
  );
}

export default function AiPage() {
  return (
    <Suspense fallback={<div className="page-stack"><div className="master-empty">正在加载 AI 分析中心…</div></div>}>
      <AiHubInner />
    </Suspense>
  );
}
