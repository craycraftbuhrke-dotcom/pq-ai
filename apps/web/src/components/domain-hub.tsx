"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ReactNode, useCallback, useMemo } from "react";

export type DomainTab = {
  key: string;
  label: string;
};

type DomainHubProps = {
  title: string;
  tabs: DomainTab[];
  defaultTab: string;
  actions?: ReactNode;
  /** Optional row between page header and tab panel (e.g. role shortcuts). */
  toolbar?: ReactNode;
  children: (tab: string) => ReactNode;
};

export function DomainHub({
  title,
  tabs,
  defaultTab,
  actions,
  toolbar,
  children,
}: DomainHubProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const allowed = useMemo(() => new Set(tabs.map((tab) => tab.key)), [tabs]);
  const raw = searchParams.get("tab");
  const tab = raw && allowed.has(raw) ? raw : defaultTab;

  const setTab = useCallback(
    (next: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (next === defaultTab) params.delete("tab");
      else params.set("tab", next);
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [defaultTab, pathname, router, searchParams],
  );

  return (
    <div className="page-stack">
      {actions ? (
        <header className="page-header">
          <div className="page-actions">{actions}</div>
        </header>
      ) : null}
      {toolbar ? <div className="domain-hub-toolbar">{toolbar}</div> : null}
      <section className="panel domain-hub">
        <div className="master-tabs" role="tablist" aria-label={title}>
          {tabs.map((item) => (
            <button
              key={item.key}
              type="button"
              role="tab"
              aria-selected={tab === item.key}
              className={tab === item.key ? "master-tab master-tab-active" : "master-tab"}
              onClick={() => setTab(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="domain-hub-body">{children(tab)}</div>
      </section>
    </div>
  );
}
