from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO, StringIO
from types import UnionType
from typing import Any, Callable, Literal, Union, get_args, get_origin

from fastapi import HTTPException
from fastapi.responses import Response
from openpyxl import Workbook, load_workbook
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.factories import create_factory, update_factory
from app.api.routes.engineering import (
    create_contribution_validation,
    create_file_import_job,
    create_file_import_profile,
    create_issue_task,
    create_issue_task_comment,
    create_issue_task_evidence,
    create_knowledge_entry,
    create_measurement_msa_study,
    create_measurement_probe,
    create_model_explanation,
    create_process_route,
    create_process_route_applicability,
    create_process_route_step,
    create_supplier_issue,
    create_supplier_submission,
    create_trajectory_geometry,
    update_contribution_validation,
    update_file_import_job,
    update_file_import_profile,
    update_issue_task,
    update_knowledge_entry,
    update_measurement_msa_study,
    update_measurement_probe,
    update_process_route,
    update_process_route_applicability,
    update_process_route_step,
    update_supplier_issue,
    update_supplier_submission,
    update_trajectory_geometry,
)
from app.api.routes.integration import create_endpoint, create_event, update_endpoint
from app.api.routes.master_data import (
    bind_factory_vehicle_model,
    bind_measurement_group_point,
    bind_vehicle_model_color,
    create_color,
    create_measurement_group,
    create_measurement_point,
    create_part,
    create_vehicle_model,
    update_color,
    update_measurement_group,
    update_measurement_point,
    update_part,
    update_vehicle_model,
)
from app.api.routes.material_governance import (
    create_applicability as create_material_applicability,
    create_definition as create_material_definition,
    create_method as create_material_method,
    create_result as create_material_result,
    create_specification as create_material_specification,
    update_applicability as update_material_applicability,
    update_definition as update_material_definition,
    update_method as update_material_method,
    update_result as update_material_result,
    update_specification as update_material_specification,
)
from app.api.routes.measurement_governance import (
    create_calibration,
    create_import_profile,
    create_instrument,
    create_method as create_measurement_method,
    create_reference,
    update_calibration,
    update_import_profile,
    update_instrument,
    update_method as update_measurement_method,
    update_reference,
)
from app.api.routes.process import (
    create_actual_parameter,
    create_brush,
    create_brush_parameter,
    create_material_batch,
    create_parameter_constraint_source,
    create_parameter_definition,
    create_production_run,
    create_production_stage_run,
    create_program_version,
    create_spray_program,
    update_actual_parameter,
    update_brush,
    update_brush_parameter,
    update_material_batch,
    update_parameter_constraint_source,
    update_production_run,
    update_production_stage_run,
    update_program_version,
    update_spray_program,
    upsert_brush_point_contribution,
)
from app.api.routes.quality import (
    create_quality_measurement,
    create_quality_standard,
    update_quality_measurement,
    update_quality_standard,
)
from app.api.routes.robot_governance import (
    create_atomizer,
    create_contribution_entry,
    create_contribution_version,
    create_controller,
    create_device_configuration,
    create_device_execution,
    create_path_segment,
    create_robot,
    create_trajectory_program,
    update_atomizer,
    update_contribution_entry,
    update_contribution_version,
    update_controller,
    update_device_configuration,
    update_device_execution,
    update_path_segment,
    update_robot,
    update_trajectory_program,
)
from app.models.domain import (
    ActualParameter,
    Brush,
    BrushParameter,
    BrushPointContribution,
    Color,
    ContributionValidationStudy,
    DurrApplicationController,
    DurrRobot,
    DurrRotaryAtomizer,
    EngineeringKnowledgeEntry,
    Factory,
    FactoryVehicleModel,
    FileImportJob,
    FileImportProfile,
    IntegrationEndpoint,
    IntegrationEvent,
    MaterialBatch,
    MaterialBatchTestResult,
    MaterialCharacteristicApplicability,
    MaterialCharacteristicDefinition,
    MaterialSpecification,
    MaterialTestMethod,
    MeasurementCalibrationRecord,
    MeasurementGroup,
    MeasurementGroupPoint,
    MeasurementImportProfile,
    MeasurementInstrument,
    MeasurementMethod,
    MeasurementMsaStudy,
    MeasurementPoint,
    MeasurementProbe,
    MeasurementReferenceStandard,
    ModelExplanation,
    MeasurementRepeatReading,
    ParameterConstraintSource,
    ParameterDefinition,
    Part,
    PointContributionEntry,
    PointContributionVersion,
    ProcessRoute,
    ProcessRouteApplicability,
    ProcessRouteStep,
    ProductionDeviceExecution,
    ProductionRun,
    ProductionStageRun,
    ProgramColor,
    ProgramDeviceConfiguration,
    ProgramVehicleModel,
    QualityMeasurement,
    QualityIssueComment,
    QualityIssueEvidence,
    QualityIssueTask,
    QualityMetricValue,
    QualityStandard,
    SprayProgram,
    SprayProgramVersion,
    SupplierMaterialIssue,
    SupplierMaterialSubmission,
    TrajectoryPathSegment,
    TrajectorySegmentGeometry,
    TrajectoryProgram,
    VehicleModel,
    VehicleModelColor,
)
from app.schemas.common import FactoryCreate, FactoryUpdate
from app.schemas.engineering import (
    ContributionValidationStudyCreate,
    ContributionValidationStudyUpdate,
    EngineeringKnowledgeEntryCreate,
    EngineeringKnowledgeEntryUpdate,
    FileImportJobCreate,
    FileImportJobUpdate,
    FileImportProfileCreate,
    FileImportProfileUpdate,
    MeasurementMsaStudyCreate,
    MeasurementMsaStudyUpdate,
    MeasurementProbeCreate,
    MeasurementProbeUpdate,
    ModelExplanationCreate,
    ProcessRouteApplicabilityCreate,
    ProcessRouteApplicabilityUpdate,
    ProcessRouteCreate,
    ProcessRouteStepCreate,
    ProcessRouteStepUpdate,
    ProcessRouteUpdate,
    QualityIssueTaskCreate,
    QualityIssueTaskUpdate,
    QualityIssueCommentCreate,
    QualityIssueEvidenceCreate,
    SupplierMaterialIssueCreate,
    SupplierMaterialIssueUpdate,
    SupplierMaterialSubmissionCreate,
    SupplierMaterialSubmissionUpdate,
    TrajectorySegmentGeometryCreate,
    TrajectorySegmentGeometryUpdate,
)
from app.schemas.integration import (
    IntegrationEndpointCreate,
    IntegrationEndpointUpdate,
    IntegrationEventCreate,
)
from app.schemas.master_data import (
    ColorCreate,
    ColorUpdate,
    FactoryVehicleModelCreate,
    MeasurementGroupCreate,
    MeasurementGroupPointBind,
    MeasurementGroupUpdate,
    MeasurementPointCreate,
    MeasurementPointUpdate,
    PartCreate,
    PartUpdate,
    VehicleModelColorCreate,
    VehicleModelCreate,
    VehicleModelUpdate,
)
from app.schemas.material import (
    MaterialBatchTestResultCreate,
    MaterialBatchTestResultUpdate,
    MaterialCharacteristicApplicabilityCreate,
    MaterialCharacteristicApplicabilityUpdate,
    MaterialCharacteristicDefinitionCreate,
    MaterialCharacteristicDefinitionUpdate,
    MaterialSpecificationCreate,
    MaterialSpecificationUpdate,
    MaterialTestMethodCreate,
    MaterialTestMethodUpdate,
)
from app.schemas.process import (
    ActualParameterCreate,
    ActualParameterUpdate,
    BrushCreate,
    BrushParameterCreate,
    BrushParameterUpdate,
    BrushPointContributionUpsert,
    BrushUpdate,
    DurrAtomizerCreate,
    DurrAtomizerUpdate,
    DurrControllerCreate,
    DurrControllerUpdate,
    DurrRobotCreate,
    DurrRobotUpdate,
    MaterialBatchCreate,
    MaterialBatchUpdate,
    ParameterConstraintSourceCreate,
    ParameterConstraintSourceUpdate,
    ParameterDefinitionCreate,
    PointContributionEntryCreate,
    PointContributionEntryUpdate,
    PointContributionVersionCreate,
    PointContributionVersionUpdate,
    ProductionDeviceExecutionCreate,
    ProductionDeviceExecutionUpdate,
    ProductionRunCreate,
    ProductionRunUpdate,
    ProductionStageRunCreate,
    ProductionStageRunUpdate,
    ProgramDeviceConfigurationCreate,
    ProgramDeviceConfigurationUpdate,
    SprayProgramCreate,
    SprayProgramUpdate,
    SprayProgramVersionCreate,
    SprayProgramVersionUpdate,
    TrajectoryPathSegmentCreate,
    TrajectoryPathSegmentUpdate,
    TrajectoryProgramCreate,
    TrajectoryProgramUpdate,
)
from app.schemas.quality import (
    MeasurementCalibrationCreate,
    MeasurementCalibrationUpdate,
    MeasurementImportProfileCreate,
    MeasurementImportProfileUpdate,
    MeasurementInstrumentCreate,
    MeasurementInstrumentUpdate,
    MeasurementMethodCreate,
    MeasurementMethodUpdate,
    MeasurementReferenceStandardCreate,
    MeasurementReferenceStandardUpdate,
    QualityMeasurementCreate,
    QualityMeasurementUpdate,
    QualityStandardCreate,
    QualityStandardUpdate,
)

FileFormat = Literal["csv", "xlsx"]
ImportMode = Literal["create", "upsert"]


@dataclass(frozen=True)
class BulkField:
    name: str
    label: str
    kind: str
    required: bool = False
    example: str = ""
    description: str = ""


@dataclass(frozen=True)
class BulkResource:
    key: str
    label: str
    group: str
    model: type
    create_schema: type[BaseModel]
    update_schema: type[BaseModel] | None
    create_func: Callable[..., Any]
    update_func: Callable[..., Any] | None = None
    create_arg_fields: tuple[str, ...] = ()
    update_arg_fields: tuple[str, ...] = ()
    update_uses_resource_id: bool = True
    unique_fields: tuple[str, ...] = ()
    order_by: tuple[str, ...] = ("created_at",)
    extra_fields: tuple[BulkField, ...] = ()
    export_row: Callable[[Session, Any], dict[str, Any]] | None = None
    match_existing: Callable[[Session, dict[str, Any]], str | None] | None = None
    importable: bool = True
    fields: tuple[BulkField, ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "fields",
            _build_fields(self.create_schema, self.update_schema, self.extra_fields),
        )


def list_bulk_resources() -> list[dict[str, str | bool]]:
    return [
        {
            "key": resource.key,
            "label": resource.label,
            "group": resource.group,
            "importable": resource.importable,
        }
        for resource in RESOURCES.values()
    ]


def get_resource(resource_key: str) -> BulkResource:
    resource = RESOURCES.get(resource_key)
    if not resource:
        raise HTTPException(status_code=404, detail=f"不支持的批量资源：{resource_key}")
    return resource


def render_template(resource_key: str, file_format: FileFormat) -> Response:
    resource = get_resource(resource_key)
    rows: list[dict[str, Any]] = []
    return _file_response(
        resource,
        file_format,
        rows,
        purpose="template",
        include_metadata=True,
    )


def export_resource(resource_key: str, file_format: FileFormat, db: Session) -> Response:
    resource = get_resource(resource_key)
    rows = [_resource_row(resource, db, item) for item in _query_resources(resource, db)]
    return _file_response(
        resource,
        file_format,
        rows,
        purpose="export",
        include_metadata=file_format == "xlsx",
    )


def import_resource(
    resource_key: str,
    content: bytes,
    *,
    filename: str,
    mode: ImportMode,
    default_values: dict[str, Any] | None = None,
    db: Session,
) -> dict[str, Any]:
    resource = get_resource(resource_key)
    if not resource.importable:
        raise HTTPException(status_code=405, detail=f"{resource.label}不支持批量导入")
    rows = _parse_rows(content, filename)
    field_names = {field.name for field in resource.fields}
    required = {field.name for field in resource.fields if field.required}
    default_values = default_values or {}
    unknown = sorted({key for row in rows for key in row if key and key not in field_names})
    if unknown:
        raise HTTPException(status_code=422, detail=f"模板字段不匹配，未知字段：{', '.join(unknown)}")
    unknown_defaults = sorted(key for key in default_values if key not in field_names)
    if unknown_defaults:
        raise HTTPException(
            status_code=422,
            detail=f"默认导入字段不匹配：{', '.join(unknown_defaults)}",
        )

    created = 0
    updated = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    for row_index, raw_row in enumerate(rows, start=2):
        merged_row = _apply_default_values(raw_row, default_values)
        if not any(str(value or "").strip() for value in merged_row.values()):
            skipped += 1
            continue
        try:
            normalized = _normalize_row(resource, merged_row)
            missing = sorted(
                name
                for name in required
                if name != "id" and _is_blank(normalized.get(name))
            )
            if missing:
                raise ValueError(f"缺少必填字段：{', '.join(missing)}")
            existing_id = _resolve_existing_id(resource, db, normalized) if mode == "upsert" else None
            if existing_id:
                if not resource.update_func or not resource.update_schema:
                    skipped += 1
                    continue
                _call_update(resource, db, existing_id, normalized)
                updated += 1
            else:
                _call_create(resource, db, normalized)
                created += 1
        except Exception as exc:  # noqa: BLE001 - row-level import must collect all failures.
            db.rollback()
            errors.append({"row": row_index, "message": _error_message(exc)})

    return {
        "resource_key": resource.key,
        "resource_label": resource.label,
        "mode": mode,
        "total_rows": len(rows),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "failed": len(errors),
        "errors": errors[:100],
        "truncated_errors": len(errors) > 100,
    }


def _build_fields(
    create_schema: type[BaseModel],
    update_schema: type[BaseModel] | None,
    extra_fields: tuple[BulkField, ...],
) -> tuple[BulkField, ...]:
    fields = [BulkField("id", "ID（可选，用于更新）", "string", False, "", "导出后回写更新使用")]
    fields.extend(extra_fields)
    seen = {field.name for field in fields}
    for schema in [create_schema, update_schema]:
        if not schema:
            continue
        for name, model_field in schema.model_fields.items():
            if name in seen:
                continue
            fields.append(
                BulkField(
                    name=name,
                    label=name,
                    kind=_kind_from_annotation(model_field.annotation),
                    required=schema is create_schema and model_field.is_required(),
                    example=_example_for(name, model_field.annotation),
                    description=_description_for(name),
                )
            )
            seen.add(name)
    return tuple(fields)


def _kind_from_annotation(annotation: Any) -> str:
    annotation = _strip_optional(annotation)
    origin = get_origin(annotation)
    if origin is list:
        return "list"
    if origin is dict:
        return "json"
    if annotation in {int}:
        return "integer"
    if annotation in {float}:
        return "number"
    if annotation is bool:
        return "boolean"
    if annotation is datetime:
        return "datetime"
    return "string"


def _strip_optional(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin in {Union, UnionType}:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def _example_for(name: str, annotation: Any) -> str:
    kind = _kind_from_annotation(annotation)
    if name.endswith("_id"):
        return "填对应资源 id"
    if kind == "boolean":
        return "true"
    if kind == "number":
        return "12.34"
    if kind == "integer":
        return "1"
    if kind == "datetime":
        return "2026-06-10T08:00:00+08:00"
    if kind == "json":
        return "{}"
    if kind == "list":
        return "A,B 或 JSON 数组"
    if "quality_type" in name or name == "target_family":
        return "ORANGE_PEEL"
    if "process_stage" in name:
        return "MIDCOAT_EXT"
    return ""


def _description_for(name: str) -> str:
    descriptions = {
        "id": "存在 id 时可用于 upsert 更新。",
        "metrics": "质量指标数组 JSON，例如 [{\"metric_code\":\"doi\",\"metric_name\":\"DOI\",\"raw_value\":82.5}]。",
        "repeat_readings": "逐次读数数组 JSON，可留空 []。",
        "vehicle_model_ids": "程序版本适用车型 id 列表，逗号分隔或 JSON 数组。",
        "color_ids": "程序版本适用颜色 id 列表，逗号分隔或 JSON 数组。",
        "supported_quality_types": "仪器支持质量类型，逗号分隔或 JSON 数组。",
        "target_families": "材料特性批准目标族，逗号分隔或 JSON 数组。",
    }
    return descriptions.get(name, "")


def _query_resources(resource: BulkResource, db: Session) -> list[Any]:
    query = select(resource.model)
    order_columns = [
        getattr(resource.model, name)
        for name in resource.order_by
        if hasattr(resource.model, name)
    ]
    if order_columns:
        query = query.order_by(*order_columns)
    return list(db.scalars(query))


def _resource_row(resource: BulkResource, db: Session, item: Any) -> dict[str, Any]:
    if resource.export_row:
        row = resource.export_row(db, item)
    else:
        row = {field.name: getattr(item, field.name, None) for field in resource.fields}
    row.setdefault("id", getattr(item, "id", ""))
    return {field.name: row.get(field.name) for field in resource.fields}


def _file_response(
    resource: BulkResource,
    file_format: FileFormat,
    rows: list[dict[str, Any]],
    *,
    purpose: Literal["template", "export"],
    include_metadata: bool,
) -> Response:
    if file_format == "xlsx":
        content = _xlsx_bytes(resource, rows, include_metadata=include_metadata)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = _csv_bytes(resource, rows)
        media_type = "text/csv; charset=utf-8"
    suffix = "xlsx" if file_format == "xlsx" else "csv"
    filename = f"{resource.key}-{purpose}.{suffix}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _csv_bytes(resource: BulkResource, rows: list[dict[str, Any]]) -> bytes:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=[field.name for field in resource.fields])
    writer.writeheader()
    for row in rows:
        writer.writerow({field.name: _cell_to_string(row.get(field.name)) for field in resource.fields})
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def _xlsx_bytes(resource: BulkResource, rows: list[dict[str, Any]], *, include_metadata: bool) -> bytes:
    workbook = Workbook()
    data_sheet = workbook.active
    data_sheet.title = "data"
    headers = [field.name for field in resource.fields]
    data_sheet.append(headers)
    for row in rows:
        data_sheet.append([_cell_to_string(row.get(field.name)) for field in resource.fields])
    data_sheet.freeze_panes = "A2"
    for column in data_sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        data_sheet.column_dimensions[column[0].column_letter].width = min(max(max_length + 2, 12), 60)

    if include_metadata:
        meta = workbook.create_sheet("fields")
        meta.append(["field", "label", "type", "required", "example", "description"])
        for field_spec in resource.fields:
            meta.append(
                [
                    field_spec.name,
                    field_spec.label,
                    field_spec.kind,
                    "yes" if field_spec.required else "no",
                    field_spec.example,
                    field_spec.description,
                ]
            )
        meta.freeze_panes = "A2"
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _parse_rows(content: bytes, filename: str) -> list[dict[str, Any]]:
    if not content:
        raise HTTPException(status_code=422, detail="导入文件为空")
    lowered = filename.lower()
    if lowered.endswith(".xlsx"):
        return _parse_xlsx(content)
    return _parse_csv(content)


def _parse_csv(content: bytes) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV 缺少表头")
    return [dict(row) for row in reader]


def _parse_xlsx(content: bytes) -> list[dict[str, Any]]:
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    sheet = workbook["data"] if "data" in workbook.sheetnames else workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(status_code=422, detail="Excel 缺少 data 工作表表头")
    headers = [str(value).strip() if value is not None else "" for value in rows[0]]
    if not any(headers):
        raise HTTPException(status_code=422, detail="Excel 表头为空")
    parsed = []
    for values in rows[1:]:
        parsed.append({headers[index]: values[index] if index < len(values) else None for index in range(len(headers)) if headers[index]})
    return parsed


def _normalize_row(resource: BulkResource, raw_row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    fields = {field.name: field for field in resource.fields}
    for name, field_spec in fields.items():
        if name not in raw_row:
            continue
        normalized[name] = _coerce_value(raw_row[name], field_spec)
    return normalized


def _apply_default_values(
    raw_row: dict[str, Any],
    default_values: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(raw_row)
    for key, value in default_values.items():
      if key not in merged or _is_blank(merged.get(key)):
          merged[key] = value
    return merged


def _coerce_value(value: Any, field_spec: BulkField) -> Any:
    if _is_blank(value):
        return None
    if isinstance(value, str):
        value = value.strip()
    if field_spec.kind == "boolean":
        return _coerce_bool(value)
    if field_spec.kind == "integer":
        return int(value)
    if field_spec.kind == "number":
        return float(value)
    if field_spec.kind == "datetime":
        return _coerce_datetime(value)
    if field_spec.kind == "json":
        return _coerce_json(value, object_required=True)
    if field_spec.kind == "list":
        return _coerce_list(value)
    return str(value) if not isinstance(value, str) else value


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y", "是", "启用", "生效"}:
        return True
    if normalized in {"false", "0", "no", "n", "否", "停用", "失效"}:
        return False
    raise ValueError(f"布尔字段无法识别：{value}")


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _coerce_json(value: Any, *, object_required: bool) -> Any:
    if isinstance(value, (dict, list)):
        parsed = value
    else:
        parsed = json.loads(str(value))
    if object_required and not isinstance(parsed, dict):
        raise ValueError("JSON 字段必须是对象")
    return parsed


def _coerce_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    text = str(value).strip()
    if text.startswith("["):
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError("列表字段必须是 JSON 数组或逗号分隔值")
        return parsed
    return [item.strip() for item in text.split(",") if item.strip()]


def _cell_to_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _resolve_existing_id(resource: BulkResource, db: Session, row: dict[str, Any]) -> str | None:
    row_id = row.get("id")
    if row_id and db.get(resource.model, row_id):
        return str(row_id)
    if resource.match_existing:
        return resource.match_existing(db, row)
    if not resource.unique_fields or any(_is_blank(row.get(field_name)) for field_name in resource.unique_fields):
        return None
    conditions = [getattr(resource.model, field_name) == row[field_name] for field_name in resource.unique_fields]
    existing = db.scalar(select(resource.model).where(*conditions))
    return existing.id if existing else None


def _call_create(resource: BulkResource, db: Session, row: dict[str, Any]) -> Any:
    payload = resource.create_schema(**_schema_values(resource.create_schema, row))
    args = [_required_arg(row, field_name) for field_name in resource.create_arg_fields]
    if args:
        return resource.create_func(*args, payload, db)
    return resource.create_func(payload, db)


def _call_update(resource: BulkResource, db: Session, resource_id: str, row: dict[str, Any]) -> Any:
    if not resource.update_func or not resource.update_schema:
        raise ValueError(f"{resource.label}不支持批量更新")
    payload = resource.update_schema(**_schema_values(resource.update_schema, row, exclude_none=False))
    if resource.update_uses_resource_id:
        return resource.update_func(resource_id, payload, db)
    args = [_required_arg(row, field_name) for field_name in resource.update_arg_fields]
    return resource.update_func(*args, payload, db)


def _schema_values(
    schema: type[BaseModel],
    row: dict[str, Any],
    *,
    exclude_none: bool = True,
) -> dict[str, Any]:
    values = {}
    for name in schema.model_fields:
        if name not in row:
            continue
        if exclude_none and row[name] is None:
            continue
        values[name] = row[name]
    return values


def _required_arg(row: dict[str, Any], field_name: str) -> Any:
    value = row.get(field_name)
    if _is_blank(value):
        raise ValueError(f"缺少上下文字段：{field_name}")
    return value


def _error_message(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        return str(exc.detail)
    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
    return str(exc)


def _program_version_row(db: Session, version: SprayProgramVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "spray_program_id": version.spray_program_id,
        "version": version.version,
        "status": version.status,
        "source_type": version.source_type,
        "is_master_sample": version.is_master_sample,
        "approved_by": version.approved_by,
        "vehicle_model_ids": list(
            db.scalars(
                select(ProgramVehicleModel.vehicle_model_id).where(
                    ProgramVehicleModel.program_version_id == version.id
                )
            )
        ),
        "color_ids": list(
            db.scalars(
                select(ProgramColor.color_id).where(ProgramColor.program_version_id == version.id)
            )
        ),
    }


def _quality_measurement_row(db: Session, measurement: QualityMeasurement) -> dict[str, Any]:
    return {
        "id": measurement.id,
        "data_no": measurement.data_no,
        "production_run_id": measurement.production_run_id,
        "measurement_group_id": measurement.measurement_group_id,
        "measurement_point_id": measurement.measurement_point_id,
        "quality_type": measurement.quality_type,
        "data_type": measurement.data_type,
        "measured_at": measurement.measured_at,
        "measured_by": measurement.measured_by,
        "device_code": measurement.device_code,
        "instrument_id": measurement.instrument_id,
        "measurement_probe_id": measurement.measurement_probe_id,
        "measurement_method_id": measurement.measurement_method_id,
        "calibration_record_id": measurement.calibration_record_id,
        "reference_standard_id": measurement.reference_standard_id,
        "import_profile_id": measurement.import_profile_id,
        "measurement_direction": measurement.measurement_direction,
        "raw_file_uri": measurement.raw_file_uri,
        "status_score": measurement.status_score,
        "is_valid": measurement.is_valid,
        "metrics": [
            {
                "metric_code": metric.metric_code,
                "metric_name": metric.metric_name,
                "raw_value": metric.raw_value,
                "corrected_value": metric.corrected_value,
                "unit": metric.unit,
            }
            for metric in db.scalars(
                select(QualityMetricValue)
                .where(QualityMetricValue.measurement_id == measurement.id)
                .order_by(QualityMetricValue.metric_code)
            )
        ],
        "repeat_readings": [
            {
                "repeat_no": reading.repeat_no,
                "metric_code": reading.metric_code,
                "raw_value": reading.raw_value,
                "corrected_value": reading.corrected_value,
                "unit": reading.unit,
                "is_valid": reading.is_valid,
                "invalid_reason": reading.invalid_reason,
            }
            for reading in db.scalars(
                select(MeasurementRepeatReading)
                .where(MeasurementRepeatReading.measurement_id == measurement.id)
                .order_by(MeasurementRepeatReading.repeat_no, MeasurementRepeatReading.metric_code)
            )
        ],
    }


def _brush_contribution_match(db: Session, row: dict[str, Any]) -> str | None:
    if _is_blank(row.get("brush_id")) or _is_blank(row.get("measurement_point_id")):
        return None
    existing = db.scalar(
        select(BrushPointContribution).where(
            BrushPointContribution.brush_id == row["brush_id"],
            BrushPointContribution.measurement_point_id == row["measurement_point_id"],
        )
    )
    return existing.id if existing else None


def _contribution_entry_match(db: Session, row: dict[str, Any]) -> str | None:
    if _is_blank(row.get("contribution_version_id")) or _is_blank(row.get("measurement_point_id")):
        return None
    source_key = None
    if row.get("brush_id"):
        source_key = f"BRUSH:{row['brush_id']}"
    if row.get("path_segment_id"):
        source_key = f"PATH:{row['path_segment_id']}"
    if not source_key:
        return None
    existing = db.scalar(
        select(PointContributionEntry).where(
            PointContributionEntry.contribution_version_id == row["contribution_version_id"],
            PointContributionEntry.measurement_point_id == row["measurement_point_id"],
            PointContributionEntry.source_key == source_key,
        )
    )
    return existing.id if existing else None


def _resource(
    key: str,
    label: str,
    group: str,
    model: type,
    create_schema: type[BaseModel],
    update_schema: type[BaseModel] | None,
    create_func_ref: Callable[..., Any],
    update_func_ref: Callable[..., Any] | None = None,
    *,
    unique_fields: tuple[str, ...] = (),
    create_arg_fields: tuple[str, ...] = (),
    update_arg_fields: tuple[str, ...] = (),
    update_uses_resource_id: bool = True,
    order_by: tuple[str, ...] = ("created_at",),
    extra_fields: tuple[BulkField, ...] = (),
    export_row: Callable[[Session, Any], dict[str, Any]] | None = None,
    match_existing: Callable[[Session, dict[str, Any]], str | None] | None = None,
    importable: bool = True,
) -> BulkResource:
    return BulkResource(
        key=key,
        label=label,
        group=group,
        model=model,
        create_schema=create_schema,
        update_schema=update_schema,
        create_func=create_func_ref,
        update_func=update_func_ref,
        unique_fields=unique_fields,
        create_arg_fields=create_arg_fields,
        update_arg_fields=update_arg_fields,
        update_uses_resource_id=update_uses_resource_id,
        order_by=order_by,
        extra_fields=extra_fields,
        export_row=export_row,
        match_existing=match_existing,
        importable=importable,
    )


RESOURCES: dict[str, BulkResource] = {
    resource.key: resource
    for resource in [
        _resource("master.factories", "工厂", "主数据", Factory, FactoryCreate, FactoryUpdate, create_factory, update_factory, unique_fields=("code",), order_by=("code",)),
        _resource("master.vehicle-models", "车型", "主数据", VehicleModel, VehicleModelCreate, VehicleModelUpdate, create_vehicle_model, update_vehicle_model, unique_fields=("code",), order_by=("code",)),
        _resource("master.colors", "颜色", "主数据", Color, ColorCreate, ColorUpdate, create_color, update_color, unique_fields=("code",), order_by=("code",)),
        _resource("master.parts", "零件", "主数据", Part, PartCreate, PartUpdate, create_part, update_part, unique_fields=("code",), order_by=("code",)),
        _resource("master.measurement-groups", "测量编组", "主数据", MeasurementGroup, MeasurementGroupCreate, MeasurementGroupUpdate, create_measurement_group, update_measurement_group, unique_fields=("vehicle_model_id", "code"), order_by=("code",)),
        _resource("master.measurement-points", "测量点", "主数据", MeasurementPoint, MeasurementPointCreate, MeasurementPointUpdate, create_measurement_point, update_measurement_point, unique_fields=("vehicle_model_id", "code"), order_by=("code",)),
        _resource("master.factory-vehicle-models", "工厂-车型关系", "主数据关系", FactoryVehicleModel, FactoryVehicleModelCreate, None, bind_factory_vehicle_model, unique_fields=("factory_id", "vehicle_model_id"), order_by=("created_at",)),
        _resource("master.vehicle-model-colors", "车型-颜色关系", "主数据关系", VehicleModelColor, VehicleModelColorCreate, None, bind_vehicle_model_color, unique_fields=("vehicle_model_id", "color_id"), order_by=("created_at",)),
        _resource("master.measurement-group-points", "测量编组-点位关系", "主数据关系", MeasurementGroupPoint, MeasurementGroupPointBind, None, bind_measurement_group_point, unique_fields=("measurement_group_id", "measurement_point_id"), order_by=("sequence_no",)),
        _resource("process.parameter-definitions", "参数定义", "工艺", ParameterDefinition, ParameterDefinitionCreate, None, create_parameter_definition, unique_fields=("code",), order_by=("code",)),
        _resource("process.parameter-constraint-sources", "参数约束来源", "工艺", ParameterConstraintSource, ParameterConstraintSourceCreate, ParameterConstraintSourceUpdate, create_parameter_constraint_source, update_parameter_constraint_source, unique_fields=("constraint_code",), order_by=("constraint_code",)),
        _resource("process.spray-programs", "喷涂程序", "工艺", SprayProgram, SprayProgramCreate, SprayProgramUpdate, create_spray_program, update_spray_program, unique_fields=("factory_id", "program_code"), order_by=("program_code",)),
        _resource("process.program-versions", "喷涂程序版本", "工艺", SprayProgramVersion, SprayProgramVersionCreate, SprayProgramVersionUpdate, create_program_version, update_program_version, unique_fields=("spray_program_id", "version"), create_arg_fields=("spray_program_id",), extra_fields=(BulkField("spray_program_id", "喷涂程序 ID", "string", True, "填 spray_program.id", "创建版本所需父级程序 ID"),), export_row=_program_version_row, order_by=("created_at",)),
        _resource("process.brushes", "刷子表/刷子号", "工艺", Brush, BrushCreate, BrushUpdate, create_brush, update_brush, unique_fields=("program_version_id", "brush_no"), create_arg_fields=("program_version_id",), extra_fields=(BulkField("program_version_id", "程序版本 ID", "string", True),), order_by=("brush_no",)),
        _resource("process.brush-parameters", "刷子参数", "工艺", BrushParameter, BrushParameterCreate, BrushParameterUpdate, create_brush_parameter, update_brush_parameter, unique_fields=("brush_id", "parameter_code"), create_arg_fields=("brush_id",), extra_fields=(BulkField("brush_id", "刷子 ID", "string", True),), order_by=("parameter_code",)),
        _resource("process.brush-contributions", "刷子点位贡献", "工艺", BrushPointContribution, BrushPointContributionUpsert, BrushPointContributionUpsert, upsert_brush_point_contribution, upsert_brush_point_contribution, create_arg_fields=("brush_id", "measurement_point_id"), update_arg_fields=("brush_id", "measurement_point_id"), update_uses_resource_id=False, extra_fields=(BulkField("brush_id", "刷子 ID", "string", True), BulkField("measurement_point_id", "测量点 ID", "string", True)), match_existing=_brush_contribution_match, order_by=("created_at",)),
        _resource("process.material-batches", "材料批次", "生产", MaterialBatch, MaterialBatchCreate, MaterialBatchUpdate, create_material_batch, update_material_batch, unique_fields=("batch_no",), order_by=("batch_no",)),
        _resource("process.production-runs", "生产事件", "生产", ProductionRun, ProductionRunCreate, ProductionRunUpdate, create_production_run, update_production_run, unique_fields=("run_no",), order_by=("started_at",)),
        _resource("process.production-stage-runs", "生产工序实绩", "生产", ProductionStageRun, ProductionStageRunCreate, ProductionStageRunUpdate, create_production_stage_run, update_production_stage_run, unique_fields=("production_run_id", "process_stage"), create_arg_fields=("production_run_id",), extra_fields=(BulkField("production_run_id", "生产事件 ID", "string", True),), order_by=("created_at",)),
        _resource("process.actual-parameters", "实际参数", "生产", ActualParameter, ActualParameterCreate, ActualParameterUpdate, create_actual_parameter, update_actual_parameter, create_arg_fields=("production_stage_run_id",), extra_fields=(BulkField("production_stage_run_id", "生产工序实绩 ID", "string", True),), order_by=("sampled_at",)),
        _resource("quality.measurements", "质量测量", "质量", QualityMeasurement, QualityMeasurementCreate, QualityMeasurementUpdate, create_quality_measurement, update_quality_measurement, unique_fields=("data_no",), order_by=("measured_at",), export_row=_quality_measurement_row),
        _resource("quality.standards", "质量标准", "质量", QualityStandard, QualityStandardCreate, QualityStandardUpdate, create_quality_standard, update_quality_standard, unique_fields=("standard_no", "version", "quality_type", "metric_code"), order_by=("standard_no",)),
        _resource("measurement-governance.instruments", "测量仪器", "仪器治理", MeasurementInstrument, MeasurementInstrumentCreate, MeasurementInstrumentUpdate, create_instrument, update_instrument, unique_fields=("code",), order_by=("code",)),
        _resource("measurement-governance.methods", "测量方法", "仪器治理", MeasurementMethod, MeasurementMethodCreate, MeasurementMethodUpdate, create_measurement_method, update_measurement_method, unique_fields=("code", "version"), order_by=("code", "version")),
        _resource("measurement-governance.references", "参考件", "仪器治理", MeasurementReferenceStandard, MeasurementReferenceStandardCreate, MeasurementReferenceStandardUpdate, create_reference, update_reference, unique_fields=("code",), order_by=("code",)),
        _resource("measurement-governance.import-profiles", "仪器导入模板", "仪器治理", MeasurementImportProfile, MeasurementImportProfileCreate, MeasurementImportProfileUpdate, create_import_profile, update_import_profile, unique_fields=("code", "version"), order_by=("code", "version")),
        _resource("measurement-governance.calibrations", "校准/检查记录", "仪器治理", MeasurementCalibrationRecord, MeasurementCalibrationCreate, MeasurementCalibrationUpdate, create_calibration, update_calibration, unique_fields=("calibration_no",), order_by=("calibrated_at",)),
        _resource("engineering.process-routes", "3C3B 工艺路线", "工程闭环", ProcessRoute, ProcessRouteCreate, ProcessRouteUpdate, create_process_route, update_process_route, unique_fields=("factory_id", "route_code", "version"), order_by=("route_code", "version")),
        _resource("engineering.process-route-steps", "3C3B 路线步骤", "工程闭环", ProcessRouteStep, ProcessRouteStepCreate, ProcessRouteStepUpdate, create_process_route_step, update_process_route_step, unique_fields=("process_route_id", "step_code"), order_by=("process_route_id", "sequence_no")),
        _resource("engineering.process-route-applicabilities", "路线适用车型颜色", "工程闭环", ProcessRouteApplicability, ProcessRouteApplicabilityCreate, ProcessRouteApplicabilityUpdate, create_process_route_applicability, update_process_route_applicability, unique_fields=("process_route_id", "vehicle_model_id", "color_id"), order_by=("created_at",)),
        _resource("engineering.file-import-profiles", "设备/材料文件导入 Profile", "工程闭环", FileImportProfile, FileImportProfileCreate, FileImportProfileUpdate, create_file_import_profile, update_file_import_profile, unique_fields=("code", "version"), order_by=("domain_type", "code", "version")),
        _resource("engineering.file-import-jobs", "设备/材料文件导入任务", "工程闭环", FileImportJob, FileImportJobCreate, FileImportJobUpdate, create_file_import_job, update_file_import_job, unique_fields=("import_no",), order_by=("submitted_at",)),
        _resource("engineering.measurement-probes", "测量探头", "工程闭环", MeasurementProbe, MeasurementProbeCreate, MeasurementProbeUpdate, create_measurement_probe, update_measurement_probe, unique_fields=("instrument_id", "code"), order_by=("instrument_id", "code")),
        _resource("engineering.measurement-msa-studies", "测量 MSA/GRR", "工程闭环", MeasurementMsaStudy, MeasurementMsaStudyCreate, MeasurementMsaStudyUpdate, create_measurement_msa_study, update_measurement_msa_study, unique_fields=("study_no",), order_by=("study_at",)),
        _resource("engineering.issue-tasks", "质量问题/调试工单", "工程闭环", QualityIssueTask, QualityIssueTaskCreate, QualityIssueTaskUpdate, create_issue_task, update_issue_task, unique_fields=("task_no",), order_by=("created_at",)),
        _resource("engineering.issue-evidence", "问题工单证据", "工程闭环", QualityIssueEvidence, QualityIssueEvidenceCreate, None, create_issue_task_evidence, unique_fields=("task_id", "source_type", "source_id", "evidence_type"), create_arg_fields=("task_id",), extra_fields=(BulkField("task_id", "问题工单 ID", "string", True),), order_by=("created_at",)),
        _resource("engineering.issue-comments", "问题工单协作记录", "工程闭环", QualityIssueComment, QualityIssueCommentCreate, None, create_issue_task_comment, create_arg_fields=("task_id",), extra_fields=(BulkField("task_id", "问题工单 ID", "string", True),), order_by=("created_at",)),
        _resource("engineering.knowledge-entries", "诊断知识库", "工程闭环", EngineeringKnowledgeEntry, EngineeringKnowledgeEntryCreate, EngineeringKnowledgeEntryUpdate, create_knowledge_entry, update_knowledge_entry, unique_fields=("entry_code", "version"), order_by=("category", "entry_code", "version")),
        _resource("engineering.supplier-submissions", "供应商材料提交", "工程闭环", SupplierMaterialSubmission, SupplierMaterialSubmissionCreate, SupplierMaterialSubmissionUpdate, create_supplier_submission, update_supplier_submission, unique_fields=("submission_no",), order_by=("submitted_at",)),
        _resource("engineering.supplier-issues", "供应商材料问题", "工程闭环", SupplierMaterialIssue, SupplierMaterialIssueCreate, SupplierMaterialIssueUpdate, create_supplier_issue, update_supplier_issue, unique_fields=("issue_no",), order_by=("created_at",)),
        _resource("engineering.contribution-validations", "点位贡献验证", "工程闭环", ContributionValidationStudy, ContributionValidationStudyCreate, ContributionValidationStudyUpdate, create_contribution_validation, update_contribution_validation, unique_fields=("contribution_version_id", "study_no"), order_by=("created_at",)),
        _resource("engineering.trajectory-geometries", "轨迹段几何治理", "工程闭环", TrajectorySegmentGeometry, TrajectorySegmentGeometryCreate, TrajectorySegmentGeometryUpdate, create_trajectory_geometry, update_trajectory_geometry, unique_fields=("path_segment_id", "geometry_version"), order_by=("created_at",)),
        _resource("engineering.model-explanations", "模型解释/SHAP", "工程闭环", ModelExplanation, ModelExplanationCreate, None, create_model_explanation, unique_fields=("model_version_id", "prediction_result_id", "explanation_type", "target_metric"), order_by=("generated_at",)),
        _resource("material-governance.definitions", "材料特性定义", "材料治理", MaterialCharacteristicDefinition, MaterialCharacteristicDefinitionCreate, MaterialCharacteristicDefinitionUpdate, create_material_definition, update_material_definition, unique_fields=("code",), order_by=("code",)),
        _resource("material-governance.methods", "材料检测方法", "材料治理", MaterialTestMethod, MaterialTestMethodCreate, MaterialTestMethodUpdate, create_material_method, update_material_method, unique_fields=("code", "version"), order_by=("code", "version")),
        _resource("material-governance.specifications", "材料规格", "材料治理", MaterialSpecification, MaterialSpecificationCreate, MaterialSpecificationUpdate, create_material_specification, update_material_specification, unique_fields=("material_code", "characteristic_definition_id", "method_id", "version"), order_by=("material_code", "created_at")),
        _resource("material-governance.applicabilities", "材料适用关系", "材料治理", MaterialCharacteristicApplicability, MaterialCharacteristicApplicabilityCreate, MaterialCharacteristicApplicabilityUpdate, create_material_applicability, update_material_applicability, unique_fields=("characteristic_definition_id", "material_type", "process_stage", "target_family"), order_by=("process_stage",)),
        _resource("material-governance.results", "材料批次检测结果", "材料治理", MaterialBatchTestResult, MaterialBatchTestResultCreate, MaterialBatchTestResultUpdate, create_material_result, update_material_result, unique_fields=("result_no",), order_by=("tested_at",)),
        _resource("robot-governance.robots", "Dürr 机器人", "Dürr 治理", DurrRobot, DurrRobotCreate, DurrRobotUpdate, create_robot, update_robot, unique_fields=("factory_id", "code"), order_by=("code",)),
        _resource("robot-governance.controllers", "Dürr 应用控制器", "Dürr 治理", DurrApplicationController, DurrControllerCreate, DurrControllerUpdate, create_controller, update_controller, unique_fields=("factory_id", "code"), order_by=("code",)),
        _resource("robot-governance.atomizers", "Dürr 静电旋杯", "Dürr 治理", DurrRotaryAtomizer, DurrAtomizerCreate, DurrAtomizerUpdate, create_atomizer, update_atomizer, unique_fields=("factory_id", "code"), order_by=("code",)),
        _resource("robot-governance.device-configurations", "程序设备配置", "Dürr 治理", ProgramDeviceConfiguration, ProgramDeviceConfigurationCreate, ProgramDeviceConfigurationUpdate, create_device_configuration, update_device_configuration, unique_fields=("program_version_id", "configuration_version"), order_by=("created_at",)),
        _resource("robot-governance.trajectory-programs", "轨迹程序", "Dürr 治理", TrajectoryProgram, TrajectoryProgramCreate, TrajectoryProgramUpdate, create_trajectory_program, update_trajectory_program, unique_fields=("program_version_id", "trajectory_code", "version"), order_by=("created_at",)),
        _resource("robot-governance.path-segments", "轨迹路径段", "Dürr 治理", TrajectoryPathSegment, TrajectoryPathSegmentCreate, TrajectoryPathSegmentUpdate, create_path_segment, update_path_segment, unique_fields=("trajectory_program_id", "segment_no"), order_by=("trajectory_program_id", "segment_no")),
        _resource("robot-governance.contribution-versions", "点位贡献版本", "Dürr 治理", PointContributionVersion, PointContributionVersionCreate, PointContributionVersionUpdate, create_contribution_version, update_contribution_version, unique_fields=("program_version_id", "target_family", "version"), order_by=("created_at",)),
        _resource("robot-governance.contribution-entries", "点位贡献条目", "Dürr 治理", PointContributionEntry, PointContributionEntryCreate, PointContributionEntryUpdate, create_contribution_entry, update_contribution_entry, match_existing=_contribution_entry_match, order_by=("contribution_version_id", "measurement_point_id")),
        _resource("robot-governance.device-executions", "设备轨迹执行", "Dürr 治理", ProductionDeviceExecution, ProductionDeviceExecutionCreate, ProductionDeviceExecutionUpdate, create_device_execution, update_device_execution, unique_fields=("production_stage_run_id",), order_by=("created_at",)),
        _resource("integrations.endpoints", "集成端点", "集成", IntegrationEndpoint, IntegrationEndpointCreate, IntegrationEndpointUpdate, create_endpoint, update_endpoint, unique_fields=("code",), order_by=("code",)),
        _resource("integrations.events", "集成事件", "集成", IntegrationEvent, IntegrationEventCreate, None, create_event, unique_fields=("endpoint_id", "source_event_id"), order_by=("created_at",)),
    ]
}
