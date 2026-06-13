"use client";

import {
  Download,
  LoaderCircle,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type ResourceKey =
  | "factories"
  | "vehicle-models"
  | "colors"
  | "parts"
  | "measurement-groups"
  | "measurement-points";

type MasterRecord = {
  id: string;
  code: string;
  name: string;
  created_at: string;
  updated_at?: string;
  site_owner?: string | null;
  remark?: string | null;
  is_active?: boolean;
  color_type?: string;
  supplier?: string | null;
  material?: string | null;
  region?: string | null;
  vehicle_model_id?: string;
  part_id?: string;
  quality_type?: string;
  expected_point_count?: number | null;
  point_type?: string;
  quality_types?: string[];
  is_match_point?: boolean;
  feature_values?: Record<string, unknown> | null;
  digital_standard?: Record<string, unknown> | null;
  tds_uri?: string | null;
  msds_uri?: string | null;
  coa_uri?: string | null;
  doe_uri?: string | null;
};

type FieldConfig = {
  key: keyof MasterRecord;
  label: string;
  required?: boolean;
  type?: "text" | "textarea" | "json" | "select" | "checkbox" | "number";
  options?: Array<{ label: string; value: string }>;
  relation?: ResourceKey;
};

type ResourceConfig = {
  label: string;
  singular: string;
  description: string;
  fields: FieldConfig[];
  columns: Array<{ key: keyof MasterRecord; label: string }>;
};

type FormValue = string | boolean;
type FormState = Record<string, FormValue>;
type RelationKey = "factory-vehicle-models" | "vehicle-model-colors" | "measurement-group-points";
type RelationRecord = {
  id: string;
  factory_id?: string;
  vehicle_model_id?: string;
  color_id?: string;
  measurement_group_id?: string;
  measurement_point_id?: string;
  sequence_no?: number;
  is_active?: boolean;
};

const relationConfigs: Record<
  RelationKey,
  { label: string; left: ResourceKey; right: ResourceKey; leftKey: string; rightKey: string }
> = {
  "factory-vehicle-models": {
    label: "工厂 - 车型",
    left: "factories",
    right: "vehicle-models",
    leftKey: "factory_id",
    rightKey: "vehicle_model_id",
  },
  "vehicle-model-colors": {
    label: "车型 - 颜色",
    left: "vehicle-models",
    right: "colors",
    leftKey: "vehicle_model_id",
    rightKey: "color_id",
  },
  "measurement-group-points": {
    label: "测量编组 - 点位",
    left: "measurement-groups",
    right: "measurement-points",
    leftKey: "measurement_group_id",
    rightKey: "measurement_point_id",
  },
};

const emptyRelations: Record<RelationKey, RelationRecord[]> = {
  "factory-vehicle-models": [],
  "vehicle-model-colors": [],
  "measurement-group-points": [],
};

const resourceOrder: ResourceKey[] = [
  "factories",
  "vehicle-models",
  "colors",
  "parts",
  "measurement-groups",
  "measurement-points",
];

const statOrder: ResourceKey[] = [
  "factories",
  "vehicle-models",
  "measurement-groups",
  "measurement-points",
];

const qualityTypeOptions = [
  { label: "橘皮", value: "ORANGE_PEEL" },
  { label: "色差", value: "COLOR_DIFFERENCE" },
  { label: "膜厚", value: "THICKNESS" },
];

const resourceConfigs: Record<ResourceKey, ResourceConfig> = {
  factories: {
    label: "工厂",
    singular: "工厂",
    description: "维护工厂代码、名称、现场调试负责人和启用状态。",
    fields: [
      { key: "code", label: "工厂代码", required: true },
      { key: "name", label: "工厂名称", required: true },
      { key: "site_owner", label: "现场调试负责人" },
      { key: "is_active", label: "启用", type: "checkbox" },
      { key: "remark", label: "备注", type: "textarea" },
    ],
    columns: [
      { key: "code", label: "工厂代码" },
      { key: "name", label: "工厂名称" },
      { key: "site_owner", label: "现场负责人" },
      { key: "is_active", label: "状态" },
      { key: "updated_at", label: "更新时间" },
    ],
  },
  "vehicle-models": {
    label: "车型",
    singular: "车型",
    description: "维护车型统一编码，供工厂、颜色、程序和测量点关联。",
    fields: [
      { key: "code", label: "车型代码", required: true },
      { key: "name", label: "车型名称", required: true },
      { key: "remark", label: "备注", type: "textarea" },
    ],
    columns: [
      { key: "code", label: "车型代码" },
      { key: "name", label: "车型名称" },
      { key: "remark", label: "备注" },
      { key: "updated_at", label: "更新时间" },
    ],
  },
  colors: {
    label: "颜色",
    singular: "颜色",
    description: "维护中涂和色漆颜色编码、供应商及材料文档信息。",
    fields: [
      { key: "code", label: "颜色代码", required: true },
      { key: "name", label: "颜色名称", required: true },
      {
        key: "color_type",
        label: "颜色类型",
        required: true,
        type: "select",
        options: [
          { label: "色漆", value: "BASECOAT" },
          { label: "中涂", value: "MIDCOAT" },
        ],
      },
      { key: "supplier", label: "供应商" },
      { key: "feature_values", label: "颜色特征值 JSON", type: "json" },
      { key: "digital_standard", label: "色差数字标准 JSON", type: "json" },
      { key: "tds_uri", label: "TDS 文档地址" },
      { key: "msds_uri", label: "MSDS 文档地址" },
      { key: "coa_uri", label: "COA 文档地址" },
      { key: "doe_uri", label: "DOE 文档地址" },
      { key: "remark", label: "备注", type: "textarea" },
    ],
    columns: [
      { key: "code", label: "颜色代码" },
      { key: "name", label: "颜色名称" },
      { key: "color_type", label: "类型" },
      { key: "supplier", label: "供应商" },
      { key: "updated_at", label: "更新时间" },
    ],
  },
  parts: {
    label: "零件",
    singular: "零件",
    description: "维护零件编号、材质和车身区域，作为测量点承载对象。",
    fields: [
      { key: "code", label: "零件编号", required: true },
      { key: "name", label: "零件名称", required: true },
      { key: "material", label: "材质" },
      { key: "region", label: "区域" },
      { key: "remark", label: "备注", type: "textarea" },
    ],
    columns: [
      { key: "code", label: "零件编号" },
      { key: "name", label: "零件名称" },
      { key: "material", label: "材质" },
      { key: "region", label: "区域" },
      { key: "updated_at", label: "更新时间" },
    ],
  },
  "measurement-groups": {
    label: "测量编组",
    singular: "测量编组",
    description: "维护车型下的质量测量编组、指标类型和预期点位数量。",
    fields: [
      { key: "code", label: "编组编号", required: true },
      { key: "name", label: "编组名称", required: true },
      { key: "vehicle_model_id", label: "车型", required: true, type: "select", relation: "vehicle-models" },
      { key: "quality_type", label: "质量指标类型", required: true, type: "select", options: qualityTypeOptions },
      { key: "expected_point_count", label: "预期点位数", type: "number" },
      { key: "remark", label: "备注", type: "textarea" },
    ],
    columns: [
      { key: "code", label: "编组编号" },
      { key: "name", label: "编组名称" },
      { key: "vehicle_model_id", label: "车型" },
      { key: "quality_type", label: "质量指标" },
      { key: "expected_point_count", label: "预期点位数" },
    ],
  },
  "measurement-points": {
    label: "测量点",
    singular: "测量点",
    description: "维护测量点、所属车型与零件，以及适用质量指标。",
    fields: [
      { key: "code", label: "点位编号", required: true },
      { key: "name", label: "点位名称", required: true },
      { key: "vehicle_model_id", label: "车型", required: true, type: "select", relation: "vehicle-models" },
      { key: "part_id", label: "零件", required: true, type: "select", relation: "parts" },
      { key: "point_type", label: "点位类型", required: true },
      { key: "region", label: "点位区域" },
      { key: "quality_types", label: "质量指标代码（逗号分隔）", required: true },
      { key: "is_match_point", label: "匹配点", type: "checkbox" },
    ],
    columns: [
      { key: "code", label: "点位编号" },
      { key: "name", label: "点位名称" },
      { key: "vehicle_model_id", label: "车型" },
      { key: "part_id", label: "零件" },
      { key: "quality_types", label: "质量指标" },
    ],
  },
};

const emptyData: Record<ResourceKey, MasterRecord[]> = {
  factories: [],
  "vehicle-models": [],
  colors: [],
  parts: [],
  "measurement-groups": [],
  "measurement-points": [],
};

function formatValue(record: MasterRecord, key: keyof MasterRecord): string {
  const value = record[key];
  if (key === "is_active") return value ? "启用" : "停用";
  if (key === "is_match_point") return value ? "是" : "否";
  if (key === "color_type") return value === "MIDCOAT" ? "中涂" : "色漆";
  if (key === "quality_type") {
    return qualityTypeOptions.find((option) => option.value === value)?.label ?? String(value);
  }
  if (key === "quality_types" && Array.isArray(value)) {
    return value
      .map((item) => qualityTypeOptions.find((option) => option.value === item)?.label ?? item)
      .join(" / ");
  }
  if ((key === "created_at" || key === "updated_at") && typeof value === "string") {
    return new Intl.DateTimeFormat("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  }
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

function recordToForm(
  record: MasterRecord | null,
  resource: ResourceKey,
  data: Record<ResourceKey, MasterRecord[]>,
): FormState {
  const state: FormState = {};
  for (const field of resourceConfigs[resource].fields) {
    const value = record?.[field.key];
    if (field.type === "checkbox") {
      state[field.key] = value === undefined ? field.key === "is_active" : Boolean(value);
    } else if (field.relation) {
      state[field.key] = typeof value === "string" ? value : (data[field.relation][0]?.id ?? "");
    } else if (field.type === "select") {
      state[field.key] = typeof value === "string" ? value : (field.options?.[0]?.value ?? "");
    } else if (field.type === "json") {
      state[field.key] = value ? JSON.stringify(value, null, 2) : "";
    } else if (field.key === "point_type") {
      state[field.key] = typeof value === "string" ? value : "QUALITY";
    } else {
      state[field.key] = value === null || value === undefined ? "" : String(value);
    }
  }
  return state;
}

async function readApiError(response: Response): Promise<string> {
  const payload = (await response.json().catch(() => ({}))) as { error?: string };
  return payload.error ?? `请求失败（${response.status}）`;
}

export function MasterDataWorkspace() {
  const [activeResource, setActiveResource] = useState<ResourceKey>("factories");
  const [data, setData] = useState(emptyData);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [modalMode, setModalMode] = useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = useState<MasterRecord | null>(null);
  const [form, setForm] = useState<FormState>({});
  const [relations, setRelations] = useState(emptyRelations);
  const [activeRelation, setActiveRelation] = useState<RelationKey>("factory-vehicle-models");
  const [relationLeftId, setRelationLeftId] = useState("");
  const [relationRightId, setRelationRightId] = useState("");
  const [relationSequence, setRelationSequence] = useState("0");

  const config = resourceConfigs[activeResource];
  const activeRelationConfig = relationConfigs[activeRelation];
  const selectedRelationLeftId = relationLeftId || data[activeRelationConfig.left][0]?.id || "";
  const selectedRelationRightId = relationRightId || data[activeRelationConfig.right][0]?.id || "";

  function displayValue(record: MasterRecord, key: keyof MasterRecord): string {
    if (key === "vehicle_model_id") {
      const relation = data["vehicle-models"].find((item) => item.id === record.vehicle_model_id);
      return relation ? `${relation.code} / ${relation.name}` : "车型待维护";
    }
    if (key === "part_id") {
      const relation = data.parts.find((item) => item.id === record.part_id);
      return relation ? `${relation.code} / ${relation.name}` : "零件待维护";
    }
    return formatValue(record, key);
  }

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const relationOrder = Object.keys(relationConfigs) as RelationKey[];
      const responses = await Promise.all([
        ...resourceOrder.map((resource) => fetch(`/api/master-data/${resource}`, { cache: "no-store" })),
        ...relationOrder.map((resource) => fetch(`/api/master-data/${resource}`, { cache: "no-store" })),
      ]);
      const failed = responses.find((response) => !response.ok);
      if (failed) throw new Error(await readApiError(failed));
      const payloads = await Promise.all(responses.map((response) => response.json()));
      setData(
        resourceOrder.reduce(
          (result, resource, index) => ({ ...result, [resource]: payloads[index] as MasterRecord[] }),
          emptyData,
        ),
      );
      setRelations(
        relationOrder.reduce(
          (result, resource, index) => ({
            ...result,
            [resource]: payloads[resourceOrder.length + index] as RelationRecord[],
          }),
          emptyRelations,
        ),
      );
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "主数据加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadData(), 0);
    return () => window.clearTimeout(timer);
  }, [loadData]);

  const filteredRecords = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return data[activeResource];
    return data[activeResource].filter((record) =>
      Object.values(record).some((value) => String(value ?? "").toLowerCase().includes(normalized)),
    );
  }, [activeResource, data, query]);

  function openModal(mode: "create" | "edit", record: MasterRecord | null = null) {
    setEditing(record);
    setForm(recordToForm(record, activeResource, data));
    setModalMode(mode);
    setError("");
  }

  function closeModal() {
    if (submitting) return;
    setModalMode(null);
    setEditing(null);
  }

  async function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const isEdit = modalMode === "edit" && editing;
    try {
      const body = Object.fromEntries(
        config.fields
          .filter((field) => !(field.key === "is_active" && !isEdit))
          .map((field) => {
            const value = form[field.key];
            if (field.key === "quality_types" && typeof value === "string") {
              return [
                field.key,
                value
                  .split(",")
                  .map((item) => item.trim().toUpperCase())
                  .filter(Boolean),
              ];
            }
            if (field.type === "number" && typeof value === "string") {
              return [field.key, value.trim() ? Number(value) : null];
            }
            if (field.type === "json" && typeof value === "string") {
              return [field.key, value.trim() ? JSON.parse(value) : null];
            }
            return [field.key, typeof value === "string" && !value.trim() ? null : value];
          }),
      );
      const response = await fetch(
        `/api/master-data/${activeResource}${isEdit ? `/${editing.id}` : ""}`,
        {
          method: isEdit ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      if (!response.ok) throw new Error(await readApiError(response));
      setNotice(`${config.singular}${isEdit ? "已更新" : "已创建"}`);
      setModalMode(null);
      setEditing(null);
      await loadData();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function deleteRecord(record: MasterRecord) {
    if (!window.confirm(`确认删除 ${record.code} / ${record.name}？此操作不可撤销。`)) return;
    setSubmitting(true);
    setError("");
    try {
      const response = await fetch(`/api/master-data/${activeResource}/${record.id}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error(await readApiError(response));
      setNotice(`${config.singular}已删除`);
      await loadData();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "删除失败");
    } finally {
      setSubmitting(false);
    }
  }

  function relationName(resource: ResourceKey, id?: string): string {
    const record = data[resource].find((item) => item.id === id);
    return record ? `${record.code} / ${record.name}` : "未找到关联主数据";
  }

  function changeRelation(relation: RelationKey) {
    const config = relationConfigs[relation];
    setActiveRelation(relation);
    setRelationLeftId(data[config.left][0]?.id ?? "");
    setRelationRightId(data[config.right][0]?.id ?? "");
    setRelationSequence("0");
  }

  async function bindRelation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const relation = relationConfigs[activeRelation];
    setSubmitting(true);
    setError("");
    try {
      const body: Record<string, string | number | boolean> = {
        [relation.leftKey]: selectedRelationLeftId,
        [relation.rightKey]: selectedRelationRightId,
      };
      if (activeRelation === "measurement-group-points") body.sequence_no = Number(relationSequence);
      else body.is_active = true;
      const response = await fetch(`/api/master-data/${activeRelation}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      setNotice(`${relation.label}关系已建立`);
      await loadData();
    } catch (bindError) {
      setError(bindError instanceof Error ? bindError.message : "关系建立失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function deleteRelation(record: RelationRecord) {
    const relation = relationConfigs[activeRelation];
    if (!window.confirm(`确认解除${relation.label}关系？`)) return;
    setSubmitting(true);
    try {
      const response = await fetch(`/api/master-data/${activeRelation}/${record.id}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error(await readApiError(response));
      setNotice(`${relation.label}关系已解除`);
      await loadData();
    } catch (relationError) {
      setError(relationError instanceof Error ? relationError.message : "关系解除失败");
    } finally {
      setSubmitting(false);
    }
  }

  function exportCsv() {
    const headers = config.columns.map((column) => column.label);
    const rows = filteredRecords.map((record) =>
      config.columns.map((column) => `"${displayValue(record, column.key).replaceAll('"', '""')}"`),
    );
    const content = `\uFEFF${[headers, ...rows].map((row) => row.join(",")).join("\n")}`;
    const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${config.label}-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
    setNotice(`已导出 ${filteredRecords.length} 条${config.label}数据`);
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">MYSQL MASTER DATA</span>
          <h1>主数据中心</h1>
          <p>维护贯穿工艺、质量、AI 建模和闭环执行的统一业务编码。</p>
        </div>
        <button className="button button-primary" onClick={() => openModal("create")}>
          <Plus aria-hidden="true" />
          新建{config.singular}
        </button>
      </header>

      <div className="freshness">
        <span className="live-dot" />
        MySQL 实时数据 · 所有操作直接写入后端
      </div>

      <section className="module-stat-strip">
        {statOrder.map((resource) => (
          <article key={resource}>
            <span>{resourceConfigs[resource].label}</span>
            <strong>{loading ? "…" : data[resource].length}</strong>
            <small>{resource === activeResource ? "当前正在维护" : "已连接真实数据库"}</small>
          </article>
        ))}
      </section>

      <section className="panel relation-workspace">
        <div className="master-tabs">
          {(Object.keys(relationConfigs) as RelationKey[]).map((relation) => (
            <button
              className={activeRelation === relation ? "master-tab master-tab-active" : "master-tab"}
              key={relation}
              onClick={() => changeRelation(relation)}
            >
              {relationConfigs[relation].label}
              <span>{relations[relation].length}</span>
            </button>
          ))}
        </div>
        <div className="relation-grid">
          <form className="relation-form" onSubmit={bindRelation}>
            <div>
              <span className="eyebrow">RELATION MAINTENANCE</span>
              <h2>建立{relationConfigs[activeRelation].label}关系</h2>
              <p>关系写入 MySQL，并用于程序适用范围、生产事件和测量编组校验。</p>
            </div>
            <label className="form-field">
              <span>{resourceConfigs[relationConfigs[activeRelation].left].singular}</span>
              <select required value={selectedRelationLeftId} onChange={(event) => setRelationLeftId(event.target.value)}>
                <option value="">请选择</option>
                {data[relationConfigs[activeRelation].left].map((record) => <option value={record.id} key={record.id}>{record.code} / {record.name}</option>)}
              </select>
            </label>
            <label className="form-field">
              <span>{resourceConfigs[relationConfigs[activeRelation].right].singular}</span>
              <select required value={selectedRelationRightId} onChange={(event) => setRelationRightId(event.target.value)}>
                <option value="">请选择</option>
                {data[relationConfigs[activeRelation].right].map((record) => <option value={record.id} key={record.id}>{record.code} / {record.name}</option>)}
              </select>
            </label>
            {activeRelation === "measurement-group-points" ? <label className="form-field"><span>点位顺序</span><input type="number" min="0" value={relationSequence} onChange={(event) => setRelationSequence(event.target.value)} /></label> : null}
            <button className="button button-primary" disabled={!selectedRelationLeftId || !selectedRelationRightId || submitting}><Plus /> 建立关系</button>
          </form>
          <div className="relation-list">
            <div className="relation-row relation-head"><span>主对象</span><span>关联对象</span><span>属性</span><span>操作</span></div>
            {relations[activeRelation].map((record) => {
              const relation = relationConfigs[activeRelation];
              const leftId = record[relation.leftKey as keyof RelationRecord] as string | undefined;
              const rightId = record[relation.rightKey as keyof RelationRecord] as string | undefined;
              return <div className="relation-row" key={record.id}><span>{relationName(relation.left, leftId)}</span><span>{relationName(relation.right, rightId)}</span><span>{activeRelation === "measurement-group-points" ? `顺序 ${record.sequence_no ?? 0}` : record.is_active ? "启用" : "停用"}</span><span><button className="icon-button icon-button-danger" onClick={() => void deleteRelation(record)}><Trash2 /></button></span></div>;
            })}
            {!relations[activeRelation].length ? <div className="master-empty">暂无关系，请从左侧建立。</div> : null}
          </div>
        </div>
      </section>

      {error ? <div className="message-banner message-error">{error}</div> : null}
      {notice ? (
        <button className="message-banner message-success" onClick={() => setNotice("")}>
          {notice}
          <X aria-hidden="true" />
        </button>
      ) : null}

      <section className="panel master-data-panel">
        <div className="master-tabs" role="tablist" aria-label="主数据类型">
          {resourceOrder.map((resource) => (
            <button
              className={resource === activeResource ? "master-tab master-tab-active" : "master-tab"}
              key={resource}
              onClick={() => {
                setActiveResource(resource);
                setQuery("");
                setError("");
              }}
              role="tab"
              aria-selected={resource === activeResource}
            >
              {resourceConfigs[resource].label}
              <span>{data[resource].length}</span>
            </button>
          ))}
        </div>

        <div className="master-toolbar">
          <div>
            <span className="eyebrow">CRUD WORKSPACE</span>
            <h2>{config.label}清单</h2>
            <p>{config.description}</p>
          </div>
          <div className="master-toolbar-actions">
            <label className="master-search">
              <Search aria-hidden="true" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={`搜索${config.label}编码、名称或属性`}
              />
            </label>
            <button className="button button-secondary" onClick={() => void loadData()} disabled={loading}>
              <RefreshCw className={loading ? "spin" : ""} aria-hidden="true" />
              刷新
            </button>
            <button className="button button-secondary" onClick={exportCsv} disabled={!filteredRecords.length}>
              <Download aria-hidden="true" />
              导出
            </button>
          </div>
        </div>

        <div className="master-table-wrap">
          <table className="master-table">
            <thead>
              <tr>
                {config.columns.map((column) => (
                  <th key={column.key}>{column.label}</th>
                ))}
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecords.map((record) => (
                <tr key={record.id}>
                  {config.columns.map((column) => (
                    <td className={column.key === "code" ? "mono" : ""} key={column.key}>
                      {column.key === "is_active" ? (
                        <span className={record.is_active ? "record-status status-on" : "record-status status-off"}>
                          {formatValue(record, column.key)}
                        </span>
                      ) : (
                        displayValue(record, column.key)
                      )}
                    </td>
                  ))}
                  <td>
                    <div className="row-actions">
                      <button className="icon-button" onClick={() => openModal("edit", record)} aria-label={`编辑 ${record.code}`}>
                        <Pencil aria-hidden="true" />
                      </button>
                      <button
                        className="icon-button icon-button-danger"
                        onClick={() => void deleteRecord(record)}
                        disabled={submitting}
                        aria-label={`删除 ${record.code}`}
                      >
                        <Trash2 aria-hidden="true" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {loading ? (
            <div className="master-empty">
              <LoaderCircle className="spin" aria-hidden="true" />
              正在从 MySQL 加载主数据
            </div>
          ) : null}
          {!loading && filteredRecords.length === 0 ? (
            <div className="master-empty">暂无匹配数据，请新建记录或调整搜索条件。</div>
          ) : null}
        </div>
      </section>

      {modalMode ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={closeModal}>
          <section
            className="modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="master-modal-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="modal-heading">
              <div>
                <span className="eyebrow">{modalMode === "create" ? "CREATE" : "EDIT"}</span>
                <h2 id="master-modal-title">{modalMode === "create" ? "新建" : "编辑"}{config.singular}</h2>
              </div>
              <button className="icon-button" onClick={closeModal} aria-label="关闭">
                <X aria-hidden="true" />
              </button>
            </div>
            <form onSubmit={(event) => void submitForm(event)}>
              <div className="form-grid">
                {config.fields.map((field) => (
                  <label className={field.type === "textarea" ? "form-field form-field-wide" : "form-field"} key={field.key}>
                    <span>
                      {field.label}
                      {field.required ? <b>*</b> : null}
                    </span>
                    {field.type === "textarea" || field.type === "json" ? (
                      <textarea
                        value={String(form[field.key] ?? "")}
                        onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.target.value }))}
                        rows={field.type === "json" ? 7 : 4}
                      />
                    ) : field.type === "select" ? (
                      <select
                        value={String(form[field.key] ?? "")}
                        onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.target.value }))}
                        required={field.required}
                      >
                        {(field.relation
                          ? data[field.relation].map((record) => ({
                              label: `${record.code} / ${record.name}`,
                              value: record.id,
                            }))
                          : field.options
                        )?.map((option) => (
                          <option value={option.value} key={option.value}>{option.label}</option>
                        ))}
                      </select>
                    ) : field.type === "checkbox" ? (
                      <span className="checkbox-field">
                        <input
                          type="checkbox"
                          checked={Boolean(form[field.key])}
                          onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.target.checked }))}
                        />
                        {field.key === "is_active" ? "当前工厂可用于业务数据关联" : "该点位用于匹配质量数据"}
                      </span>
                    ) : (
                      <input
                        type={field.type === "number" ? "number" : "text"}
                        value={String(form[field.key] ?? "")}
                        onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.target.value }))}
                        required={field.required}
                        maxLength={field.key === "name" ? 120 : 80}
                      />
                    )}
                  </label>
                ))}
              </div>
              <div className="modal-actions">
                <button className="button button-secondary" type="button" onClick={closeModal} disabled={submitting}>
                  取消
                </button>
                <button className="button button-primary" type="submit" disabled={submitting}>
                  {submitting ? <LoaderCircle className="spin" aria-hidden="true" /> : null}
                  {submitting ? "正在保存" : "保存到 MySQL"}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </div>
  );
}
