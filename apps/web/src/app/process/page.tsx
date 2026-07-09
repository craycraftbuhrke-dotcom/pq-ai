"use client";

import { Suspense } from "react";

import { DomainHub } from "@/components/domain-hub";
import { ProductionWorkspace } from "@/components/production-workspace";
import { ProgramWorkspace } from "@/components/program-workspace";

const TABS = [
  { key: "overview", label: "概览" },
  { key: "recipes", label: "配方与刷子" },
  { key: "runs", label: "生产实绩" },
];

function ProcessOverview() {
  return (
    <div className="domain-overview">
      <div className="domain-overview-grid">
        <article>
          <h3>配方与刷子</h3>
          <p>维护喷涂程序、受控版本、刷子身份、本工序参数与测量点贡献权重。</p>
          <a className="button button-secondary" href="/process?tab=recipes">进入配方</a>
        </article>
        <article>
          <h3>生产实绩</h3>
          <p>查看生产事件，补录五段工序实绩与实际参数。质量上传可自动创建生产事件。</p>
          <a className="button button-secondary" href="/process?tab=runs">进入实绩</a>
        </article>
        <article>
          <h3>工艺变更与试验</h3>
          <p>工程师参数变更、推荐执行与受控试验已统一到 AI 分析中心的「推荐与试验 / 工艺变更」。</p>
          <a className="button button-secondary" href="/ai?tab=recommendations">去 AI 闭环</a>
        </article>
      </div>
    </div>
  );
}

function ProcessHubInner() {
  return (
    <DomainHub
      kicker="工艺管理"
      title="工艺管理中心"
      description="统一管理喷涂配方、刷子参数、贡献权重与生产实绩。工艺变更与受控试验在 AI 分析中心闭环。"
      tabs={TABS}
      defaultTab="overview"
    >
      {(tab) => {
        if (tab === "recipes") return <ProgramWorkspace mode="recipes" />;
        if (tab === "runs") return <ProductionWorkspace mode="runs" />;
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
