"use client";

import { Plus, X } from "lucide-react";

type ObjectRow = { key: string; value: string };
type ListRow = { value: string };
type TableColumn = {
  key: string;
  label: string;
  type?: "text" | "number" | "datetime-local";
};
type TableRow = Record<string, string>;

function safeParse(value: string): unknown {
  if (!value.trim()) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function stringifyScalar(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function inferScalar(value: string): unknown {
  const normalized = value.trim();
  if (!normalized) return "";
  if (normalized === "true") return true;
  if (normalized === "false") return false;
  if (normalized === "null") return null;
  const numeric = Number(normalized);
  if (!Number.isNaN(numeric) && normalized === String(numeric)) return numeric;
  return value;
}

function parseObjectRows(value: string): ObjectRow[] {
  const parsed = safeParse(value);
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") return [{ key: "", value: "" }];
  const rows = Object.entries(parsed as Record<string, unknown>).map(([key, itemValue]) => ({
    key,
    value: stringifyScalar(itemValue),
  }));
  return rows.length ? rows : [{ key: "", value: "" }];
}

function serializeObjectRows(rows: ObjectRow[]): string {
  const payload = rows.reduce<Record<string, unknown>>((result, row) => {
    if (!row.key.trim()) return result;
    result[row.key.trim()] = inferScalar(row.value);
    return result;
  }, {});
  return JSON.stringify(payload, null, 2);
}

function parseListRows(value: string): ListRow[] {
  const parsed = safeParse(value);
  if (!Array.isArray(parsed)) return [{ value: "" }];
  const rows = parsed.map((item) => ({ value: stringifyScalar(item) }));
  return rows.length ? rows : [{ value: "" }];
}

function serializeListRows(rows: ListRow[]): string {
  const payload = rows
    .map((row) => row.value.trim())
    .filter(Boolean)
    .map((row) => inferScalar(row));
  return JSON.stringify(payload, null, 2);
}

function parseTableRows(value: string, columns: readonly TableColumn[]): TableRow[] {
  const parsed = safeParse(value);
  if (!Array.isArray(parsed)) {
    return [Object.fromEntries(columns.map((column) => [column.key, ""]))];
  }
  const rows = parsed
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && !Array.isArray(item))
    .map((item) =>
      Object.fromEntries(columns.map((column) => [column.key, stringifyScalar(item[column.key])])) as TableRow,
    );
  return rows.length ? rows : [Object.fromEntries(columns.map((column) => [column.key, ""]))];
}

function serializeTableRows(rows: TableRow[], columns: readonly TableColumn[]): string {
  const payload = rows
    .map((row) =>
      Object.fromEntries(
        columns
          .map((column) => [column.key, row[column.key] ?? ""] as const)
          .filter(([, value]) => value.trim() !== "")
          .map(([key, value]) => [key, inferScalar(value)]),
      ),
    )
    .filter((row) => Object.keys(row).length > 0);
  return JSON.stringify(payload, null, 2);
}

function updateObjectRows(value: string, onChange: (value: string) => void, updater: (rows: ObjectRow[]) => ObjectRow[]) {
  onChange(serializeObjectRows(updater(parseObjectRows(value))));
}

function updateListRows(value: string, onChange: (value: string) => void, updater: (rows: ListRow[]) => ListRow[]) {
  onChange(serializeListRows(updater(parseListRows(value))));
}

function updateTableRows(
  value: string,
  columns: readonly TableColumn[],
  onChange: (value: string) => void,
  updater: (rows: TableRow[]) => TableRow[],
) {
  onChange(serializeTableRows(updater(parseTableRows(value, columns)), columns));
}

export function JsonObjectEditor({
  value,
  onChange,
  keyLabel = "项目",
  valueLabel = "值",
  addLabel = "新增一行",
}: {
  value: string;
  onChange: (value: string) => void;
  keyLabel?: string;
  valueLabel?: string;
  addLabel?: string;
}) {
  const rows = parseObjectRows(value);

  return (
    <div className="structured-editor">
      <div className="structured-editor-toolbar">
        <span>{`${keyLabel} / ${valueLabel}`}</span>
        <button
          type="button"
          className="button button-secondary"
          onClick={() =>
            updateObjectRows(value, onChange, (current) => [...current, { key: "", value: "" }])
          }
        >
          <Plus />
          {addLabel}
        </button>
      </div>
      <div className="structured-grid structured-grid-object">
        <div className="structured-grid-head">{keyLabel}</div>
        <div className="structured-grid-head">{valueLabel}</div>
        <div className="structured-grid-head">操作</div>
        {rows.map((row, index) => (
          <StructuredRow key={`${row.key}-${index}`}>
            <input
              value={row.key}
              placeholder={keyLabel}
              onChange={(event) =>
                updateObjectRows(value, onChange, (current) =>
                  current.map((item, rowIndex) => (rowIndex === index ? { ...item, key: event.target.value } : item)),
                )
              }
            />
            <input
              value={row.value}
              placeholder={valueLabel}
              onChange={(event) =>
                updateObjectRows(value, onChange, (current) =>
                  current.map((item, rowIndex) => (rowIndex === index ? { ...item, value: event.target.value } : item)),
                )
              }
            />
            <button
              type="button"
              className="icon-button"
              aria-label={`移除此行 ${index + 1}`}
              onClick={() =>
                updateObjectRows(value, onChange, (current) =>
                  current.length === 1 ? [{ key: "", value: "" }] : current.filter((_, rowIndex) => rowIndex !== index),
                )
              }
            >
              <X aria-hidden="true" />
            </button>
          </StructuredRow>
        ))}
      </div>
    </div>
  );
}

export function JsonStringListEditor({
  value,
  onChange,
  itemLabel = "内容",
  addLabel = "新增一项",
}: {
  value: string;
  onChange: (value: string) => void;
  itemLabel?: string;
  addLabel?: string;
}) {
  const rows = parseListRows(value);

  return (
    <div className="structured-editor">
      <div className="structured-editor-toolbar">
        <span>{itemLabel}</span>
        <button
          type="button"
          className="button button-secondary"
          onClick={() => updateListRows(value, onChange, (current) => [...current, { value: "" }])}
        >
          <Plus />
          {addLabel}
        </button>
      </div>
      <div className="structured-grid structured-grid-list">
        <div className="structured-grid-head">{itemLabel}</div>
        <div className="structured-grid-head">操作</div>
        {rows.map((row, index) => (
          <StructuredRow key={`${row.value}-${index}`}>
            <input
              value={row.value}
              placeholder={itemLabel}
              onChange={(event) =>
                updateListRows(value, onChange, (current) =>
                  current.map((item, rowIndex) => (rowIndex === index ? { value: event.target.value } : item)),
                )
              }
            />
            <button
              type="button"
              className="icon-button"
              aria-label={`移除此行 ${index + 1}`}
              onClick={() =>
                updateListRows(value, onChange, (current) =>
                  current.length === 1 ? [{ value: "" }] : current.filter((_, rowIndex) => rowIndex !== index),
                )
              }
            >
              <X aria-hidden="true" />
            </button>
          </StructuredRow>
        ))}
      </div>
    </div>
  );
}

export function JsonTableEditor({
  value,
  onChange,
  columns,
  addLabel = "新增一行",
}: {
  value: string;
  onChange: (value: string) => void;
  columns: readonly TableColumn[];
  addLabel?: string;
}) {
  const rows = parseTableRows(value, columns);

  return (
    <div className="structured-editor">
      <div className="structured-editor-toolbar">
        <span>表格录入</span>
        <button
          type="button"
          className="button button-secondary"
          onClick={() =>
            updateTableRows(
              value,
              columns,
              onChange,
              (current) => [...current, Object.fromEntries(columns.map((column) => [column.key, ""])) as TableRow],
            )
          }
        >
          <Plus />
          {addLabel}
        </button>
      </div>
      <div className="structured-grid structured-grid-table" style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr)) 44px` }}>
        {columns.map((column) => (
          <div className="structured-grid-head" key={column.key}>
            {column.label}
          </div>
        ))}
        <div className="structured-grid-head">操作</div>
        {rows.map((row, index) => (
          <StructuredRow key={index}>
            {columns.map((column) => (
              <input
                key={column.key}
                type={column.type ?? "text"}
                step={column.type === "number" ? "any" : undefined}
                value={row[column.key] ?? ""}
                placeholder={column.label}
                onChange={(event) =>
                  updateTableRows(value, columns, onChange, (current) =>
                    current.map((item, rowIndex) =>
                      rowIndex === index ? { ...item, [column.key]: event.target.value } : item,
                    ),
                  )
                }
              />
            ))}
            <button
              type="button"
              className="icon-button"
              aria-label={`移除此行 ${index + 1}`}
              onClick={() =>
                updateTableRows(value, columns, onChange, (current) =>
                  current.length === 1
                    ? [Object.fromEntries(columns.map((column) => [column.key, ""])) as TableRow]
                    : current.filter((_, rowIndex) => rowIndex !== index),
                )
              }
            >
              <X aria-hidden="true" />
            </button>
          </StructuredRow>
        ))}
      </div>
    </div>
  );
}

function StructuredRow({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
