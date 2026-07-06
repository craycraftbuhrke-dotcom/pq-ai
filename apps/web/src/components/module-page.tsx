"use client";

import { ArrowUpRight, FileCheck2, Plus, Search, SlidersHorizontal, X } from "lucide-react";
import { useMemo, useState } from "react";

type ModulePageProps = {
  kicker: string;
  title: string;
  description: string;
  stats: Array<{ label: string; value: string; note: string }>;
  columns: string[];
  rows: string[][];
  primaryAction: string;
  source?: "api" | "fallback";
};

export function ModulePage({
  kicker,
  title,
  description,
  stats,
  columns,
  rows,
  primaryAction,
  source,
}: ModulePageProps) {
  const [showFilter, setShowFilter] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedRow, setSelectedRow] = useState<string[] | null>(null);
  const [notice, setNotice] = useState("");

  const filteredRows = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return rows;
    return rows.filter((row) => row.some((cell) => cell.toLowerCase().includes(normalized)));
  }, [query, rows]);

  function exportCsv() {
    const content = `\uFEFF${[columns, ...filteredRows]
      .map((row) => row.map((cell) => `"${cell.replaceAll('"', '""')}"`).join(","))
      .join("\n")}`;
    const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${title}-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
    setNotice(`已导出 ${filteredRows.length} 条记录`);
  }

  function handlePrimaryAction() {
    if (primaryAction.includes("导出")) {
      exportCsv();
      return;
    }
    setNotice(`${primaryAction}写操作正在按开发计划接入，当前页面使用真实 API 只读数据。`);
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">{kicker}</span>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        <button className="button button-primary" onClick={handlePrimaryAction}>
          <Plus aria-hidden="true" />
          {primaryAction}
        </button>
      </header>
      {source ? (
        <div className="freshness">
          <span className="live-dot" />
          {source === "api" ? " API 实时数据" : " 空状态"}
        </div>
      ) : null}
      {notice ? (
        <button className="message-banner message-success" onClick={() => setNotice("")}>
          {notice}
          <X aria-hidden="true" />
        </button>
      ) : null}
      <section className="module-stat-strip">
        {stats.map((stat) => (
          <article key={stat.label}>
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
            <small>{stat.note}</small>
          </article>
        ))}
      </section>
      <section className="panel module-table-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">LIVE DATA</span>
            <h2>{title}清单</h2>
          </div>
          <div className="inline-actions">
            <button className="button button-secondary" onClick={() => setShowFilter((value) => !value)}>
              <SlidersHorizontal aria-hidden="true" />
              筛选
            </button>
            <button className="button button-secondary" onClick={exportCsv} disabled={!filteredRows.length}>
              <FileCheck2 aria-hidden="true" />
              导出
            </button>
          </div>
        </div>
        {showFilter ? (
          <div className="module-filter">
            <Search aria-hidden="true" />
            <input
              autoFocus
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={`搜索${title}当前清单`}
            />
            <span>{filteredRows.length} / {rows.length}</span>
          </div>
        ) : null}
        <div className="data-table">
          <div className="data-row data-head">
            {columns.map((column) => (
              <span key={column}>{column}</span>
            ))}
            <span />
          </div>
          {filteredRows.map((row) => (
            <div className="data-row" key={row[0]}>
              {row.map((cell, index) => (
                <span className={index === 0 ? "mono" : ""} key={`${row[0]}-${columns[index]}`}>
                  {cell}
                </span>
              ))}
              <button className="icon-button" aria-label={`查看 ${row[0]}`} onClick={() => setSelectedRow(row)}>
                <ArrowUpRight />
              </button>
            </div>
          ))}
          {filteredRows.length === 0 ? <div className="empty-table">暂无匹配数据。</div> : null}
        </div>
      </section>
      {selectedRow ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setSelectedRow(null)}>
          <section
            className="modal-card module-detail-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="module-detail-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="modal-heading">
              <div>
                <span className="eyebrow">RECORD DETAIL</span>
                <h2 id="module-detail-title">{selectedRow[0]}</h2>
              </div>
              <button className="icon-button" onClick={() => setSelectedRow(null)} aria-label="关闭">
                <X aria-hidden="true" />
              </button>
            </div>
            <dl className="module-detail-list">
              {columns.map((column, index) => (
                <div key={column}>
                  <dt>{column}</dt>
                  <dd className={index === 0 ? "mono" : ""}>{selectedRow[index]}</dd>
                </div>
              ))}
            </dl>
          </section>
        </div>
      ) : null}
    </div>
  );
}
