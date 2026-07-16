"use client";

import { Suspense } from "react";

import IntegrationMonitorPage from "@/app/integration-monitor/page";
import { DomainHub } from "@/components/domain-hub";
import { IntegrationWorkspace } from "@/components/integration-workspace";

const TABS = [
  { key: "integrations", label: "系统对接" },
  { key: "monitor", label: "对接监控" },
  { key: "audit", label: "操作审计" },
];

function AuditEmbed({
  stats,
  columns,
  rows,
  source,
}: {
  stats: Array<{ label: string; value: string; note: string }>;
  columns: string[];
  rows: string[][];
  source: "api" | "fallback";
}) {
  return (
    <div className="embedded-stack">
      <div className="freshness">
        <span className="live-dot" />
        审计数据来源：{source === "api" ? "实时 API" : "回退占位"}
      </div>
      <section className="module-stat-strip">
        {stats.map((item) => (
          <article key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <small>{item.note}</small>
          </article>
        ))}
      </section>
      <div className="master-table-wrap">
        <table className="master-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.join("|")}>
                {row.map((cell, index) => (
                  <td key={`${columns[index]}-${cell}`}>{cell}</td>
                ))}
              </tr>
            ))}
            {!rows.length ? (
              <tr>
                <td colSpan={columns.length}>暂无审计记录</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SettingsHubInner({
  audit,
}: {
  audit: {
    stats: Array<{ label: string; value: string; note: string }>;
    columns: string[];
    rows: string[][];
    source: "api" | "fallback";
  };
}) {
  return (
    <DomainHub
      title="系统设置中心"
      tabs={TABS}
      defaultTab="integrations"
    >
      {(tab) => {
        if (tab === "monitor") return <IntegrationMonitorPage embedded />;
        if (tab === "audit") {
          return (
            <AuditEmbed
              stats={audit.stats}
              columns={audit.columns}
              rows={audit.rows}
              source={audit.source}
            />
          );
        }
        return <IntegrationWorkspace embedded />;
      }}
    </DomainHub>
  );
}

export function SettingsHubClient({
  audit,
}: {
  audit: {
    stats: Array<{ label: string; value: string; note: string }>;
    columns: string[];
    rows: string[][];
    source: "api" | "fallback";
  };
}) {
  return (
    <Suspense fallback={<div className="page-stack"><div className="master-empty">正在加载系统设置中心…</div></div>}>
      <SettingsHubInner audit={audit} />
    </Suspense>
  );
}
