from datetime import UTC, datetime, timedelta

from sqlalchemy import select
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
    MaterialBatchTestResult,
    MaterialCharacteristicDefinition,
    MaterialTestMethod,
    MeasurementCalibrationRecord,
    MeasurementImportProfile,
    MeasurementInstrument,
    MeasurementMethod,
    MeasurementPoint,
    MeasurementReferenceStandard,
    MeasurementRepeatReading,
    ParameterDefinition,
    PathSegmentExecution,
    ProductionDeviceExecution,
    ProductionRun,
    ProductionStageRun,
    ProgramDeviceConfiguration,
    QualityMeasurement,
    QualityMetricValue,
    TrajectoryPathSegment,
    TrajectoryProgram,
    VehicleModel,
)
from app.services.measurement_reliability import refresh_measurement_reliability
from app.services.material_governance import refresh_material_result_reliability


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
    result_ids = []
    for item in payload.get("characteristic_results", []):
        definition = db.scalar(
            select(MaterialCharacteristicDefinition).where(
                MaterialCharacteristicDefinition.code == item["characteristic_code"]
            )
        )
        if not definition:
            raise ValueError(f"材料特性代码不存在：{item['characteristic_code']}")
        method = db.scalar(
            select(MaterialTestMethod).where(
                MaterialTestMethod.code == item["method_code"],
                MaterialTestMethod.version == item.get("method_version", "1.0"),
            )
        )
        if not method:
            raise ValueError("材料检测方法代码与版本不存在")
        result = db.scalar(
            select(MaterialBatchTestResult).where(
                MaterialBatchTestResult.result_no == item["result_no"]
            )
        )
        result_values = {
            "material_batch_id": batch.id,
            "characteristic_definition_id": definition.id,
            "method_id": method.id,
            "result_value": float(item["result_value"]),
            "unit": item["unit"],
            "tested_at": _datetime(item["tested_at"], "tested_at"),
            "tested_by": item.get("tested_by"),
            "source_uri": item.get("source_uri"),
            "raw_values": item.get("raw_values"),
            "remark": item.get("remark"),
        }
        if result:
            for field, value in result_values.items():
                setattr(result, field, value)
        else:
            result = MaterialBatchTestResult(result_no=item["result_no"], **result_values)
            db.add(result)
            db.flush()
        refresh_material_result_reliability(db, result)
        result_ids.append(result.id)
    return {
        "operation": operation,
        "resource_type": "material_batch",
        "resource_id": batch.id,
        "material_result_ids": result_ids,
    }


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
    repeat_readings = payload.get("repeat_readings", [])
    require_approved_metrics(
        payload["quality_type"],
        [str(reading["metric_code"]) for reading in repeat_readings],
    )
    instrument = (
        _required_by_code(db, MeasurementInstrument, payload["instrument_code"], "测量仪器")
        if payload.get("instrument_code")
        else None
    )
    method = (
        db.scalar(
            select(MeasurementMethod).where(
                MeasurementMethod.code == payload["measurement_method_code"],
                MeasurementMethod.version == payload.get("measurement_method_version", "1.0"),
            )
        )
        if payload.get("measurement_method_code")
        else None
    )
    if payload.get("measurement_method_code") and not method:
        raise ValueError("测量方法代码与版本不存在")
    calibration = (
        db.scalar(
            select(MeasurementCalibrationRecord).where(
                MeasurementCalibrationRecord.calibration_no == payload["calibration_no"]
            )
        )
        if payload.get("calibration_no")
        else None
    )
    if payload.get("calibration_no") and not calibration:
        raise ValueError("校准/检查记录编号不存在")
    reference = (
        _required_by_code(
            db,
            MeasurementReferenceStandard,
            payload["reference_standard_code"],
            "参考件",
        )
        if payload.get("reference_standard_code")
        else None
    )
    import_profile = (
        db.scalar(
            select(MeasurementImportProfile).where(
                MeasurementImportProfile.code == payload["import_profile_code"],
                MeasurementImportProfile.version == payload.get("import_profile_version", "1.0"),
            )
        )
        if payload.get("import_profile_code")
        else None
    )
    if payload.get("import_profile_code") and not import_profile:
        raise ValueError("导入模板代码与版本不存在")
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
        "device_code": instrument.code if instrument else payload.get("device_code"),
        "instrument_id": instrument.id if instrument else None,
        "measurement_method_id": method.id if method else None,
        "calibration_record_id": calibration.id if calibration else None,
        "reference_standard_id": reference.id if reference else None,
        "import_profile_id": import_profile.id if import_profile else None,
        "measurement_direction": payload.get("measurement_direction"),
        "raw_file_uri": payload.get("raw_file_uri"),
        "status_score": payload.get("status_score"),
        "is_valid": payload.get("is_valid", True),
    }
    if measurement:
        for field, value in values.items():
            setattr(measurement, field, value)
        operation = "UPDATED"
    else:
        measurement = QualityMeasurement(data_no=payload["data_no"], **values)
        db.add(measurement)
        db.flush()
        operation = "CREATED"
    existing_metrics = {
        metric.metric_code: metric
        for metric in db.scalars(
            select(QualityMetricValue).where(QualityMetricValue.measurement_id == measurement.id)
        )
    }
    for metric in metrics:
        metric_values = {
            "metric_name": metric.get("metric_name", metric["metric_code"]),
            "raw_value": float(metric["raw_value"]),
            "corrected_value": metric.get("corrected_value"),
            "unit": metric.get("unit"),
        }
        existing = existing_metrics.get(metric["metric_code"])
        if existing:
            for field, value in metric_values.items():
                setattr(existing, field, value)
        else:
            db.add(
                QualityMetricValue(
                    measurement_id=measurement.id,
                    metric_code=metric["metric_code"],
                    **metric_values,
                )
            )
    existing_readings = {
        (reading.repeat_no, reading.metric_code): reading
        for reading in db.scalars(
            select(MeasurementRepeatReading).where(
                MeasurementRepeatReading.measurement_id == measurement.id
            )
        )
    }
    for reading in repeat_readings:
        key = (int(reading["repeat_no"]), reading["metric_code"])
        reading_values = {
            "raw_value": float(reading["raw_value"]),
            "corrected_value": reading.get("corrected_value"),
            "unit": reading.get("unit"),
            "is_valid": reading.get("is_valid", True),
            "invalid_reason": reading.get("invalid_reason"),
        }
        existing = existing_readings.get(key)
        if existing:
            for field, value in reading_values.items():
                setattr(existing, field, value)
        else:
            db.add(
                MeasurementRepeatReading(
                    measurement_id=measurement.id,
                    repeat_no=key[0],
                    metric_code=key[1],
                    **reading_values,
                )
            )
    db.flush()
    refresh_measurement_reliability(db, measurement)
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


def _process_robot_trajectory_execution(db: Session, payload: dict) -> dict:
    run = db.scalar(
        select(ProductionRun).where(ProductionRun.run_no == payload["production_run_no"])
    )
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
    configuration_query = select(ProgramDeviceConfiguration).where(
        ProgramDeviceConfiguration.program_version_id == stage.program_version_id
    )
    if payload.get("device_configuration_version"):
        configuration_query = configuration_query.where(
            ProgramDeviceConfiguration.configuration_version
            == payload["device_configuration_version"]
        )
    else:
        configuration_query = configuration_query.where(
            ProgramDeviceConfiguration.status == "ACTIVE"
        )
    configuration = db.scalar(configuration_query)
    if not configuration:
        raise ValueError("生产工序缺少匹配的受治理设备配置")
    trajectory_query = select(TrajectoryProgram).where(
        TrajectoryProgram.program_version_id == stage.program_version_id,
        TrajectoryProgram.trajectory_code == payload["trajectory_code"],
    )
    if payload.get("trajectory_version"):
        trajectory_query = trajectory_query.where(
            TrajectoryProgram.version == payload["trajectory_version"]
        )
    else:
        trajectory_query = trajectory_query.where(TrajectoryProgram.status == "ACTIVE")
    trajectory = db.scalar(trajectory_query)
    if not trajectory:
        raise ValueError("生产工序缺少匹配的受治理轨迹程序")
    execution = db.scalar(
        select(ProductionDeviceExecution).where(
            ProductionDeviceExecution.production_stage_run_id == stage.id
        )
    )
    values = {
        "device_configuration_id": configuration.id,
        "trajectory_program_id": trajectory.id,
        "executed_checksum": payload["executed_checksum"],
        "started_at": _datetime(payload["started_at"], "started_at")
        if payload.get("started_at")
        else None,
        "completed_at": _datetime(payload["completed_at"], "completed_at")
        if payload.get("completed_at")
        else None,
        "status": (
            "CHECKSUM_MISMATCH"
            if payload["executed_checksum"] != trajectory.checksum
            else payload.get("status", "COMPLETED")
        ),
        "source_system": payload.get("source_system", "ROBOT"),
        "deviation_details": payload.get("deviation_details"),
    }
    operation = "UPDATED" if execution else "CREATED"
    if execution:
        for field, value in values.items():
            setattr(execution, field, value)
    else:
        execution = ProductionDeviceExecution(
            production_stage_run_id=stage.id,
            **values,
        )
        db.add(execution)
        db.flush()
    existing_segments = {
        row.path_segment_id: row
        for row in db.scalars(
            select(PathSegmentExecution).where(
                PathSegmentExecution.device_execution_id == execution.id
            )
        )
    }
    for item in payload.get("segments", []):
        segment = db.scalar(
            select(TrajectoryPathSegment).where(
                TrajectoryPathSegment.trajectory_program_id == trajectory.id,
                TrajectoryPathSegment.segment_no == int(item["segment_no"]),
            )
        )
        if not segment:
            raise ValueError(f"轨迹路径段不存在：{item['segment_no']}")
        segment_values = {
            "actual_speed": item.get("actual_speed"),
            "speed_unit": item.get("speed_unit"),
            "trigger_state": item.get("trigger_state"),
            "actual_values": item.get("actual_values"),
        }
        existing = existing_segments.get(segment.id)
        if existing:
            for field, value in segment_values.items():
                setattr(existing, field, value)
        else:
            db.add(
                PathSegmentExecution(
                    device_execution_id=execution.id,
                    path_segment_id=segment.id,
                    **segment_values,
                )
            )
    db.flush()
    return {
        "operation": operation,
        "resource_type": "production_device_execution",
        "resource_id": execution.id,
        "status": execution.status,
    }


PROCESSORS = {
    "MES_PRODUCTION_RUN_UPSERT": _process_mes_run,
    "MATERIAL_BATCH_UPSERT": _process_material_batch,
    "QMS_QUALITY_MEASUREMENT_UPSERT": _process_qms_measurement,
    "ROBOT_ACTUAL_PARAMETERS_UPSERT": _process_robot_parameters,
    "ROBOT_TRAJECTORY_EXECUTION_UPSERT": _process_robot_trajectory_execution,
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
