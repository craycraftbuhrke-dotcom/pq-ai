"use client";

import { Suspense, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { QualityMonitorPanel } from "@/components/quality-monitor-panel";
import { BodyPointMap } from "@/components/body-point-map";
import { BodyPointMap3D } from "@/components/body-point-map-3d";
import { DomainHub } from "@/components/domain-hub";
import { QualityWorkspace } from "@/components/quality-workspace";
import { useAuth } from "@/lib/auth-context";
import {
  QUALITY_HUB_TABS,
  qualityHomeTab,
  qualityShortcuts,
  type QualityHubTab,
} from "@/lib/quality-hub";

function QualityHubInner() {
  const { actor } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const defaultTab = useMemo(() => qualityHomeTab(actor.roles), [actor.roles]);
  const shortcuts = useMemo(() => qualityShortcuts(actor.roles), [actor.roles]);
  const activeTab = (searchParams.get("tab") as QualityHubTab | null) ?? defaultTab;

  function goTab(tab: QualityHubTab) {
    const params = new URLSearchParams(searchParams.toString());
    if (tab === defaultTab) params.delete("tab");
    else params.set("tab", tab);
    if (tab !== "measurements") params.delete("filter");
    const query = params.toString();
    router.replace(query ? `/quality?${query}` : "/quality", { scroll: false });
  }

  return (
    <DomainHub
      kicker="质量管理"
      title="质量管理中心"
      description="按角色走最短路径：质量上数与判定、工艺看点位与刷子、管理层看 SPC 与数据可靠性。真·SPC 在「SPC 与趋势」。"
      tabs={QUALITY_HUB_TABS}
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
        if (tab === "overview") return <QualityMonitorPanel embedded />;
        if (tab === "upload") return <QualityWorkspace mode="embed" lockedTab="upload" />;
        if (tab === "measurements") return <QualityWorkspace mode="embed" lockedTab="measurements" />;
        if (tab === "body-map") return <BodyPointMap />;
        if (tab === "3d-view") return <BodyPointMap3D />;
        if (tab === "standards") return <QualityWorkspace mode="embed" lockedTab="standards" />;
        if (tab === "analytics") return <QualityWorkspace mode="embed" lockedTab="analytics" />;
        return <QualityMonitorPanel embedded />;
      }}
    </DomainHub>
  );
}

export default function QualityPage() {
  return (
    <Suspense
      fallback={
        <div className="page-stack">
          <div className="master-empty">正在加载质量管理中心…</div>
        </div>
      }
    >
      <QualityHubInner />
    </Suspense>
  );
}
