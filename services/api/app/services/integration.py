from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.scope_policy import (
    is_out_of_scope_name,
    require_approved_mapping,
    require_approved_metrics,
)
from app.models.domain import (
    ActualParameter,
    Brush,
    Color,
    Factory,
    IntegrationEndpoint,
    IntegrationEvent,
    MaterialBatch,
    MeasurementPoint,
    ParameterDefinition,
    ProductionRun,
    ProductionStageRun,
    QualityMeasurement,
    QualityMetricValue,
    VehicleModel,
)


def _required_by_code(db: Session, model: type, code: str, label: str):
    resource = db.scalar(select(model).where(model.code == code))
    if not resource:
        raise ValueError(f"{label}代码不存在：{code}")
    return resource


def _datetime(value: str | datetime, label: str) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}不是有效 ISO 时间") from exc


def _process_mes_run(db: Session, payload: dict) -> dict:
    require_approved_mapping(payload.get("context_values"), "MES 生产事件上下文")
    factory = _required_by_code(db, Factory, payload["factory_code"], "工厂")
    vehicle = _required_by_code(db, VehicleModel, payload["vehicle_model_code"], "车型")
    color = _required_by_code(db, Color, payload["color_code"], "颜色")
    run = db.scalar(select(ProductionRun).where(ProductionRun.run_no == payload["run_no"]))
    values = {
        "body_no": payload.get("body_no"),
        "factory_id": factory.id,
        "vehicle_model_id": vehicle.id,
        "color_id": color.id,
        "shift": payload.get("shift"),
        "started_at": _datetime(payload["started_at"], "started_at"),
        "completed_at": (
            _datetime(payload["completed_at"], "completed_at")
            if payload.get("completed_at")
            else None
        ),
        "context_values": payload.get("context_values"),
    }
    if run:
        for field, value in values.items():
            setattr(run, field, value)
        operation = "UPDATED"
    else:
        run = ProductionRun(run_no=payload["run_no"], **values)
        db.add(run)
        operation = "CREATED"
    db.flush()
    return {"operation": operation, "resource_type": "production_run", "resource_id": run.id}


def _process_material_batch(db: Session, payload: dict) -> dict:
    require_approved_mapping(payload.get("coa_values"), "材料 COA")
    batch = db.scalar(select(MaterialBatch).where(MaterialBatch.batch_no == payload["batch_no"]))
    values = {
        "material_code": payload["material_code"],
        "material_name": payload["material_name"],
        "material_type": payload["material_type"],
        "supplier": payload.get("supplier"),
        "viscosity": payload.get("viscosity"),
        "solid_ratio": payload.get("solid_ratio"),
        "coa_values": payload.get("coa_values"),
    }
    if batch:
        for field, value in values.items():
            setattr(batch, field, value)
        operation = "UPDATED"
    else:
        batch = MaterialBatch(batch_no=payload["batch_no"], **values)
        db.add(batch)
        operation = "CREATED"
    db.flush()
    return {"operation": operation, "resource_type": "material_batch", "resource_id": batch.id}


def _process_qms_measurement(db: Session, payload: dict) -> dict:
    run = db.scalar(select(ProductionRun).where(ProductionRun.run_no == payload["production_run_no"]))
    if not run:
        raise ValueError(f"生产事件不存在：{payload['production_run_no']}")
    point = db.scalar(
        select(MeasurementPoint).where(
            MeasurementPoint.vehicle_model_id == run.vehicle_model_id,
            MeasurementPoint.code == payload["measurement_point_code"],
        )
    )
    if not point:
        raise ValueError(f"车型下测量点不存在：{payload['measurement_point_code']}")
    metrics = payload.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise ValueError("QMS 质量事件至少需要一个 metrics 指标")
    require_approved_metrics(
        payload["quality_type"],
        [str(metric["metric_code"]) for metric in metrics],
    )
    measurement = db.scalar(
        select(QualityMeasurement).where(QualityMeasurement.data_no == payload["data_no"])
    )
    values = {
        "production_run_id": run.id,
        "measurement_group_id": payload.get("measurement_group_id"),
        "measurement_point_id": point.id,
        "quality_type": payload["quality_type"],
        "data_type": payload.get("data_type", "TEST"),
        "measured_at": _datetime(payload["measured_at"], "measured_at"),
        "measured_by": payload.get("measured_by"),
        "device_code": payload.get("device_code"),
        "status_score": payload.get("status_score"),
        "is_valid": payload.get("is_valid", True),
    }
    if measurement:
        for field, value in values.items():
            setattr(measurement, field, value)
        db.execute(
            delete(QualityMetricValue).where(QualityMetricValue.measurement_id == measurement.id)
        )
        operation = "UPDATED"
    else:
        measurement = QualityMeasurement(data_no=payload["data_no"], **values)
        db.add(measurement)
        db.flush()
        operation = "CREATED"
    db.add_all(
        [
            QualityMetricValue(
                measurement_id=measurement.id,
                metric_code=metric["metric_code"],
                metric_name=metric.get("metric_name", metric["metric_code"]),
                raw_value=float(metric["raw_value"]),
                corrected_value=metric.get("corrected_value"),
                unit=metric.get("unit"),
            )
            for metric in metrics
        ]
    )
    db.flush()
    return {"operation": operation, "resource_type": "quality_measurement", "resource_id": measurement.id}


def _process_robot_parameters(db: Session, payload: dict) -> dict:
    run = db.scalar(select(ProductionRun).where(ProductionRun.run_no == payload["production_run_no"]))
    if not run:
        raise ValueError(f"生产事件不存在：{payload['production_run_no']}")
    stage = db.scalar(
        select(ProductionStageRun).where(
            ProductionStageRun.production_run_id == run.id,
            ProductionStageRun.process_stage == payload["process_stage"],
        )
    )
    if not stage:
        raise ValueError(f"生产事件缺少工序实绩：{payload['process_stage']}")
    parameters = payload.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        raise ValueError("机器人实绩事件至少需要一个 parameters 参数")
    sampled_at = _datetime(payload["sampled_at"], "sampled_at")
    resources = []
    for parameter in parameters:
        if is_out_of_scope_name(parameter["parameter_code"]):
            raise ValueError(
                f"机器人实绩参数超出当前项目范围：{parameter['parameter_code']}"
            )
        definition = db.scalar(
            select(ParameterDefinition).where(ParameterDefinition.code == parameter["parameter_code"])
        )
        brush = None
        if parameter.get("brush_no"):
            brush = db.scalar(
                select(Brush).where(
                    Brush.program_version_id == stage.program_version_id,
                    Brush.brush_no == parameter["brush_no"],
                )
            )
        resource = ActualParameter(
            production_stage_run_id=stage.id,
            brush_id=brush.id if brush else None,
            parameter_definition_id=definition.id if definition else None,
            parameter_code=parameter["parameter_code"],
            actual_value=float(parameter["actual_value"]),
            unit=parameter["unit"],
            sampled_at=sampled_at,
            source_system=payload.get("source_system", "ROBOT"),
        )
        db.add(resource)
        resources.append(resource)
    stage.actual_parameters = {
        parameter["parameter_code"]: parameter["actual_value"] for parameter in parameters
    }
    db.flush()
    return {
        "operation": "CREATED",
        "resource_type": "actual_parameter",
        "resource_ids": [resource.id for resource in resources],
    }


PROCESSORS = {
    "MES_PRODUCTION_RUN_UPSERT": _process_mes_run,
    "MATERIAL_BATCH_UPSERT": _process_material_batch,
    "QMS_QUALITY_MEASUREMENT_UPSERT": _process_qms_measurement,
    "ROBOT_ACTUAL_PARAMETERS_UPSERT": _process_robot_parameters,
}


def process_integration_event(db: Session, event: IntegrationEvent) -> IntegrationEvent:
    endpoint = db.get(IntegrationEndpoint, event.endpoint_id)
    if event.status == "SUCCEEDED":
        return event
    event.status = "PROCESSING"
    event.attempt_count += 1
    event.last_error = None
    db.commit()

    try:
        if not endpoint or not endpoint.is_active:
            raise ValueError("集成端点不存在或已停用")
        processor = PROCESSORS.get(event.event_type)
        if not processor:
            raise ValueError(f"尚未配置事件处理器：{event.event_type}")
        event.mapped_payload = processor(db, event.payload)
        event.status = "SUCCEEDED"
        event.processed_at = datetime.now(UTC)
        event.next_retry_at = None
        endpoint.last_success_at = event.processed_at
        db.commit()
        db.refresh(event)
        return event
    except Exception as exc:
        db.rollback()
        event = db.get(IntegrationEvent, event.id)
        endpoint = db.get(IntegrationEndpoint, event.endpoint_id)
        event.status = "DEAD_LETTER" if event.attempt_count >= event.max_attempts else "FAILED"
        event.last_error = str(exc)
        event.next_retry_at = (
            None
            if event.status == "DEAD_LETTER"
            else datetime.now(UTC) + timedelta(minutes=min(60, 2**event.attempt_count))
        )
        endpoint.last_failure_at = datetime.now(UTC)
        db.commit()
        db.refresh(event)
        return event
