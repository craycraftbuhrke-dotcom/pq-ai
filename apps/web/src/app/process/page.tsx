"use client";

import Link from "next/link";
import { Suspense } from "react";
import { ArrowRight, Bot, GitCompareArrows, Activity } from "lucide-react";

import { DomainHub } from "@/components/domain-hub";
import { ProductionWorkspace } from "@/components/production-workspace";
import { ProgramWorkspace } from "@/components/program-workspace";

const TABS = [
  { key: "overview", label: "概览" },
  { key: "recipes", label: "配方与刷子" },
  { key: "runs", label: "生产实绩" },
];

const OVERVIEW_CARDS = [
  {
    key: "recipes",
    href: "/process?tab=recipes",
    icon: GitCompareArrows,
    title: "配方与刷子",
    description: "维护喷涂程序、受控版本、刷子身份、本工序参数与测量点贡献权重。",
    action: "进入配方",
  },
  {
    key: "runs",
    href: "/process?tab=runs",
    icon: Activity,
    title: "生产实绩",
    description: "查看生产事件，补录五段工序实绩与实际参数。质量上传可自动创建生产事件。",
    action: "进入实绩",
  },
  {
    key: "ai",
    href: "/ai?tab=recommendations",
    icon: Bot,
    title: "工艺变更与试验",
    description: "工程师参数变更、推荐执行与受控试验已统一到 AI 分析中心闭环。",
    action: "去 AI 闭环",
  },
] as const;

function ProcessOverview() {
  return (
    <div className="domain-overview">
      <div className="domain-overview-intro">
        <strong>从这里进入工艺工作台</strong>
        <span>配方配置与生产实绩在本中心完成；推荐试验与工艺变更请到 AI 分析中心。</span>
      </div>
      <div className="domain-overview-grid">
        {OVERVIEW_CARDS.map((card) => {
          const Icon = card.icon;
          return (
            <article className="domain-overview-card" key={card.key}>
              <div className="domain-overview-card-head">
                <span className="domain-overview-icon" aria-hidden="true">
                  <Icon />
                </span>
                <div>
                  <h3>{card.title}</h3>
                  <p>{card.description}</p>
                </div>
              </div>
              <Link className="button button-secondary domain-overview-action" href={card.href}>
                {card.action}
                <ArrowRight aria-hidden="true" />
              </Link>
            </article>
          );
        })}
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
