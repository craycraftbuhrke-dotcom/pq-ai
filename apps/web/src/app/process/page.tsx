"use client";

import { Suspense } from "react";

import ControlledTrialsPage from "@/app/controlled-trials/page";
import { AiWorkbench } from "@/components/ai-workbench";
import { DomainHub } from "@/components/domain-hub";
import { EngineeringWorkspace } from "@/components/engineering-workspace";
import { OvpCard, OvpCardList, OvpCardStatusStrip, type OvpAccent } from "@/components/ovp-card";
import { PaintLineSimulation } from "@/components/paint-line-simulation";
import { ProductionWorkspace } from "@/components/production-workspace";
import { ProgramWorkspace } from "@/components/program-workspace";
import { useOverviewData, type ProcessOverview as ProcessOverviewData } from "@/lib/overview-data";

const TABS = [
  { key: "overview", label: "概览" },
  { key: "simulation", label: "虚拟产线" },
  { key: "recipes", label: "配方与刷子" },
  { key: "runs", label: "生产实绩" },
  { key: "predictions", label: "预测与诊断" },
  { key: "recommendations", label: "推荐与试验" },
  { key: "changes", label: "工艺变更" },
];

function ProcessOverviewPanel({ data }: { data: ProcessOverviewData }) {
  const stageSegments = data.stages.map((s) => ({
    label: `${s.name} ${s.runCount}`,
    tone: (s.healthy ? "positive" : "neutral") as OvpAccent,
  }));
  const healthyCount = data.stages.filter((s) => s.healthy).length;
  const total = data.stages.length || 5;
  const recentRunItems = data.recentRuns.map((r) => ({
    label: `${r.runNo}${r.shift ? ` · ${r.shift}` : ""}`,
    value: r.bodyNo ?? "—",
  }));

  return (
    <div className="domain-overview">
      <div className="domain-overview-intro">
        <strong>从这里进入工艺工作台</strong>
        <span>配方、生产实绩、质量预测、推荐试验与工艺变更均在本中心完成。</span>
      </div>
      <div className="ovp-card-grid">
        <OvpCard
          title="在制生产"
          kpiLabel="活动批次"
          kpiValue={data.activeRuns}
          kpiUnit="台"
          accent="info"
          viewAllHref="/process?tab=runs"
          viewAllLabel="进入实绩"
        >
          <OvpCardList items={recentRunItems} />
        </OvpCard>
        <OvpCard
          title="五段健康"
          kpiLabel="健康段数"
          kpiValue={`${healthyCount}/${total}`}
          accent={healthyCount === total ? "positive" : "warning"}
          viewAllHref="/process?tab=simulation"
          viewAllLabel="进入仿真"
        >
          <OvpCardStatusStrip segments={stageSegments} />
        </OvpCard>
        <OvpCard
          title="配方版本"
          kpiLabel="生效版本"
          kpiValue={data.programVersionsActive}
          kpiUnit="个"
          accent={data.programVersionsDraft > 0 ? "warning" : "positive"}
          viewAllHref="/process?tab=recipes"
          viewAllLabel="进入配方"
        >
          <OvpCardList
            items={[
              { label: "生效版本", value: String(data.programVersionsActive) },
              { label: "草稿版本", value: String(data.programVersionsDraft) },
            ]}
          />
        </OvpCard>
        <OvpCard
          title="工艺问题"
          kpiLabel="未关闭问题"
          kpiValue={data.openIssueTasks}
          kpiUnit="项"
          accent={data.openIssueTasks > 0 ? "warning" : "positive"}
          viewAllHref="/process?tab=changes"
          viewAllLabel="去工艺变更"
        >
          <OvpCardList items={[{ label: "待处理问题", value: String(data.openIssueTasks) }]} />
        </OvpCard>
      </div>
    </div>
  );
}

function ProcessOverview() {
  const { process } = useOverviewData();
  return <ProcessOverviewPanel data={process} />;
}

function ProcessHubInner() {
  return (
    <DomainHub
      title="工艺管理中心"
      tabs={TABS}
      defaultTab="overview"
    >
      {(tab) => {
        if (tab === "simulation") return <PaintLineSimulation />;
        if (tab === "recipes") return <ProgramWorkspace mode="recipes" />;
        if (tab === "runs") return <ProductionWorkspace mode="runs" />;
        if (tab === "predictions") {
          return <AiWorkbench mode="embed" lockedTab="predictions" />;
        }
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
        return <ProcessOverview />;
      }}
    </DomainHub>
  );
}

export default function ProcessPage() {
  return (
    <Suspense fallback={<div className="page-stack"><div className="master-empty">正在加载工艺管理中心…</div></div>}>
      <ProcessHubInner />
    </Suspense>
  );
}
