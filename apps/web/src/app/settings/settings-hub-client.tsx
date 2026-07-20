"use client";

import { Suspense } from "react";

import IntegrationMonitorPage from "@/app/integration-monitor/page";
import SecurityAdminPage from "@/app/security-admin/page";
import { DomainHub } from "@/components/domain-hub";
import { EngineeringWorkspace } from "@/components/engineering-workspace";
import { IntegrationWorkspace } from "@/components/integration-workspace";
import { RemoteStationWorkspace } from "@/components/remote-station-workspace";

const TABS = [
  { key: "integrations", label: "外部数据" },
  { key: "remote-stations", label: "机器人远程工作站" },
  { key: "file-imports", label: "设备与材料文件" },
  { key: "import-profiles", label: "文件填写规则" },
  { key: "monitor", label: "数据接收情况" },
  { key: "audit", label: "操作记录" },
  { key: "security", label: "用户与权限" },
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
        操作记录来源：{source === "api" ? "实时系统数据" : "暂未连接数据源"}
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
      title="系统设置"
      tabs={TABS}
      defaultTab="integrations"
    >
      {(tab) => {
        if (tab === "monitor") return <IntegrationMonitorPage embedded />;
        if (tab === "remote-stations") return <RemoteStationWorkspace />;
        if (tab === "file-imports") return <EngineeringWorkspace mode="embed" lockedTab="imports" />;
        if (tab === "import-profiles") return <EngineeringWorkspace mode="embed" lockedTab="profiles" />;
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
        if (tab === "security") return <SecurityAdminPage />;
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
