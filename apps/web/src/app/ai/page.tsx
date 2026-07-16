"use client";

import { Suspense, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AiOverviewPanel } from "@/components/ai-overview-panel";
import { AiWorkbench } from "@/components/ai-workbench";
import ControlledTrialsPage from "@/app/controlled-trials/page";
import { DomainHub } from "@/components/domain-hub";
import { EngineeringWorkspace } from "@/components/engineering-workspace";
import { useAuth } from "@/lib/auth-context";
import { AI_HUB_TABS, aiHomeTab, aiShortcuts, type AiHubTab } from "@/lib/ai-hub";

function AiHubInner() {
  const { actor } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const defaultTab = useMemo(() => aiHomeTab(actor.roles), [actor.roles]);
  const shortcuts = useMemo(() => aiShortcuts(actor.roles), [actor.roles]);
  const activeTab = (searchParams.get("tab") as AiHubTab | null) ?? defaultTab;

  function goTab(tab: AiHubTab) {
    const params = new URLSearchParams(searchParams.toString());
    if (tab === defaultTab) params.delete("tab");
    else params.set("tab", tab);
    const query = params.toString();
    router.replace(query ? `/ai?${query}` : "/ai", { scroll: false });
  }

  return (
    <DomainHub
      title="AI 分析中心"
      tabs={AI_HUB_TABS}
      defaultTab={defaultTab}
      toolbar={
        <div className="quality-role-shortcuts" role="navigation" aria-label="角色快捷入口">
          <span className="quality-role-shortcuts-label">常用</span>
          {shortcuts.map((item) => (
            <button
              key={item.tab}
              type="button"
              className={`quality-role-chip ${activeTab === item.tab ? "is-active" : ""}`}
              onClick={() => goTab(item.tab)}
            >
              {item.label}
            </button>
          ))}
        </div>
      }
    >
      {(tab) => {
        if (tab === "overview") return <AiOverviewPanel />;
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
