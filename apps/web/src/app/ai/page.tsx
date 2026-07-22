"use client";

import { Suspense, useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AiOverviewPanel } from "@/components/ai-overview-panel";
import { AiWorkbench } from "@/components/ai-workbench";
import { DomainHub } from "@/components/domain-hub";
import { useAuth } from "@/lib/auth-context";
import { AI_HUB_TABS, aiHomeTab, aiShortcuts, type AiHubTab } from "@/lib/ai-hub";

const LEGACY_AI_TABS: Record<string, string> = {
  predictions: "/process?tab=predictions",
  recommendations: "/process?tab=recommendations",
  changes: "/process?tab=changes",
  issues: "/process?tab=changes",
};

function AiHubInner() {
  const { actor } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const defaultTab = useMemo(() => aiHomeTab(actor.roles), [actor.roles]);
  const shortcuts = useMemo(() => aiShortcuts(actor.roles), [actor.roles]);
  const requestedTab = searchParams.get("tab");
  const activeTab = (requestedTab as AiHubTab | null) ?? defaultTab;

  useEffect(() => {
    if (!requestedTab) return;
    const target = LEGACY_AI_TABS[requestedTab];
    if (target) router.replace(target);
  }, [requestedTab, router]);

  function goTab(tab: AiHubTab) {
    const params = new URLSearchParams(searchParams.toString());
    if (tab === defaultTab) params.delete("tab");
    else params.set("tab", tab);
    const query = params.toString();
    router.replace(query ? `/ai?${query}` : "/ai", { scroll: false });
  }

  if (requestedTab && LEGACY_AI_TABS[requestedTab]) {
    return (
      <div className="page-stack">
        <div className="master-empty">正在跳转到工艺管理…</div>
      </div>
    );
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
        if (tab === "comparison") {
          return <AiWorkbench mode="embed" lockedTab="comparison" />;
        }
        return <AiWorkbench mode="embed" allowedTabs={["models", "governance"]} />;
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
