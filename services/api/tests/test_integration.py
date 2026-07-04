from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.api.routes.integration import (
    create_endpoint,
    create_event,
    delete_endpoint,
    integration_summary,
    replay_event,
    update_endpoint,
)
from tests.schema_guard import create_transient_test_schema
from app.models.domain import (
    ActualParameter,
    Brush,
    Color,
    Factory,
    IntegrationEvent,
    MaterialBatch,
    MaterialBatchTestResult,
    MaterialCharacteristicDefinition,
    MaterialSpecification,
    MaterialTestMethod,
    MeasurementPoint,
    Part,
    ProductionRun,
    ProductionStageRun,
    QualityMeasurement,
    QualityMetricValue,
    SprayProgram,
    SprayProgramVersion,
    VehicleModel,
)
from app.schemas.integration import (
    IntegrationEndpointCreate,
    IntegrationEndpointUpdate,
    IntegrationEventCreate,
)


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    create_transient_test_schema(engine)
    return Session(engine)


def integration_event(endpoint_id: str, source_event_id: str, event_type: str, payload: dict):
    return IntegrationEventCreate(
        endpoint_id=endpoint_id,
        source_event_id=source_event_id,
        event_type=event_type,
        payload=payload,
    )


def test_integration_inbox_processes_business_events_and_enforces_idempotency() -> None:
    db = build_session()
    factory = Factory(code="F01", name="一号工厂")
    vehicle = VehicleModel(code="M01", name="车型一")
    color = Color(code="C01", name="珍珠白", color_type="BASECOAT")
    db.add_all([factory, vehicle, color])
    db.commit()
    endpoint = create_endpoint(
        IntegrationEndpointCreate(
            code="MES-01",
            name="MES 生产事件",
            system_type="MES",
        ),
        db,
    )
    payload = {
        "run_no": "RUN-INT-001",
        "body_no": "BODY-001",
        "factory_code": factory.code,
        "vehicle_model_code": vehicle.code,
        "color_code": color.code,
        "shift": "DAY",
        "started_at": datetime.now(UTC).isoformat(),
    }
    processed = create_event(integration_event(endpoint.id, "MES-EVT-001", "MES_PRODUCTION_RUN_UPSERT", payload), db)
    duplicate = create_event(integration_event(endpoint.id, "MES-EVT-001", "MES_PRODUCTION_RUN_UPSERT", payload), db)
    assert processed.status == "SUCCEEDED"
    assert duplicate.id == processed.id
    assert db.scalar(select(func.count()).select_from(ProductionRun)) == 1
    assert integration_summary(db)["events"] == 1

    material_endpoint = create_endpoint(
        IntegrationEndpointCreate(code="MAT-01", name="材料系统", system_type="MATERIAL"),
        db,
    )
    definition = MaterialCharacteristicDefinition(
        code="viscosity",
        name="粘度",
        category="VISCOSITY_RHEOLOGY",
        canonical_unit="s",
        target_families=["ORANGE_PEEL"],
    )
    db.add(definition)
    db.flush()
    method = MaterialTestMethod(
        characteristic_definition_id=definition.id,
        code="VISC-CUP",
        name="粘度杯方法",
        version="1.0",
        method_type="FLOW_CUP",
        result_unit="s",
        procedure_uri="approved://material/method/viscosity",
    )
    db.add(method)
    db.flush()
    tested_at = datetime.now(UTC)
    db.add(
        MaterialSpecification(
            material_code="CC-001",
            characteristic_definition_id=definition.id,
            method_id=method.id,
            version="1.0",
            lower_limit=20,
            upper_limit=25,
            status="ACTIVE",
            source_uri="approved://material/spec/CC-001/viscosity",
            effective_from=tested_at - timedelta(days=1),
            approved_by="材料工程师",
            approved_at=tested_at - timedelta(days=1),
        )
    )
    db.commit()
    material = create_event(
        integration_event(
            material_endpoint.id,
            "MAT-EVT-001",
            "MATERIAL_BATCH_UPSERT",
            {
                "batch_no": "LOT-001",
                "material_code": "CC-001",
                "material_name": "清漆",
                "material_type": "CLEARCOAT",
                "viscosity": 24.2,
                "solid_ratio": 0.52,
                "characteristic_results": [
                    {
                        "result_no": "MAT-INT-001",
                        "characteristic_code": definition.code,
                        "method_code": method.code,
                        "method_version": method.version,
                        "result_value": 24.2,
                        "unit": "s",
                        "tested_at": tested_at.isoformat(),
                        "source_uri": "qms://material/MAT-INT-001",
                    }
                ],
            },
        ),
        db,
    )
    assert material.status == "SUCCEEDED"
    assert db.scalar(select(MaterialBatch).where(MaterialBatch.batch_no == "LOT-001")).viscosity == 24.2
    governed_result = db.scalar(
        select(MaterialBatchTestResult).where(
            MaterialBatchTestResult.result_no == "MAT-INT-001"
        )
    )
    assert governed_result.reliability_status == "VERIFIED"
    assert material.mapped_payload["material_result_ids"] == [governed_result.id]

    with pytest.raises(HTTPException) as conflict:
        delete_endpoint(endpoint.id, db)
    assert conflict.value.status_code == 405
    assert update_endpoint(endpoint.id, IntegrationEndpointUpdate(is_active=False), db).is_active is False
    db.close()


def test_qms_robot_events_and_failed_event_replay() -> None:
    db = build_session()
    now = datetime.now(UTC)
    factory = Factory(code="F02", name="二号工厂")
    vehicle = VehicleModel(code="M02", name="车型二")
    color = Color(code="C02", name="黑色", color_type="BASECOAT")
    db.add_all([factory, vehicle, color])
    db.flush()
    part = Part(code="ROOF", name="车顶")
    db.add(part)
    db.flush()
    point = MeasurementPoint(
        code="P01",
        name="车顶点位",
        vehicle_model_id=vehicle.id,
        part_id=part.id,
        quality_types=["ORANGE_PEEL"],
    )
    db.add(point)
    program = SprayProgram(
        program_code="PRG-01",
        name="清漆二站",
        factory_id=factory.id,
        process_stage="CLEARCOAT_2",
        station_code="P1C1A2",
        station_name="清漆二站",
    )
    db.add(program)
    db.flush()
    version = SprayProgramVersion(
        spray_program_id=program.id,
        version="V1",
        status="ACTIVE",
        source_type="MANUAL",
    )
    run = ProductionRun(
        run_no="RUN-INT-002",
        factory_id=factory.id,
        vehicle_model_id=vehicle.id,
        color_id=color.id,
        started_at=now,
    )
    db.add_all([version, run])
    db.flush()
    brush = Brush(program_version_id=version.id, brush_no="B01", brush_table_no="BT01")
    stage = ProductionStageRun(
        production_run_id=run.id,
        process_stage="CLEARCOAT_2",
        program_version_id=version.id,
    )
    db.add_all([brush, stage])
    db.commit()

    qms = create_endpoint(
        IntegrationEndpointCreate(code="QMS-01", name="质量系统", system_type="QMS"),
        db,
    )
    qms_event = create_event(
        integration_event(
            qms.id,
            "QMS-EVT-001",
            "QMS_QUALITY_MEASUREMENT_UPSERT",
            {
                "data_no": "QM-INT-001",
                "production_run_no": run.run_no,
                "measurement_point_code": point.code,
                "quality_type": "ORANGE_PEEL",
                "measured_at": now.isoformat(),
                "metrics": [{"metric_code": "doi", "metric_name": "DOI", "raw_value": 82.5}],
            },
        ),
        db,
    )
    assert qms_event.status == "SUCCEEDED"
    measurement = db.scalar(
        select(QualityMeasurement).where(QualityMeasurement.data_no == "QM-INT-001")
    )
    assert db.scalar(
        select(QualityMetricValue).where(QualityMetricValue.measurement_id == measurement.id)
    ).raw_value == 82.5

    robot = create_endpoint(
        IntegrationEndpointCreate(code="ROBOT-01", name="机器人实绩", system_type="ROBOT"),
        db,
    )
    robot_event = create_event(
        integration_event(
            robot.id,
            "ROBOT-EVT-001",
            "ROBOT_ACTUAL_PARAMETERS_UPSERT",
            {
                "production_run_no": run.run_no,
                "process_stage": "CLEARCOAT_2",
                "sampled_at": now.isoformat(),
                "parameters": [
                    {
                        "brush_no": brush.brush_no,
                        "parameter_code": "clearcoat_2_spray_flow",
                        "actual_value": 318.0,
                        "unit": "ml/min",
                    }
                ],
            },
        ),
        db,
    )
    assert robot_event.status == "SUCCEEDED"
    assert db.scalar(select(func.count()).select_from(ActualParameter)) == 1

    failed = create_event(
        IntegrationEventCreate(
            endpoint_id=qms.id,
            source_event_id="BAD-EVT-001",
            event_type="UNKNOWN_EVENT",
            payload={},
            max_attempts=2,
        ),
        db,
    )
    assert failed.status == "FAILED"
    replayed = replay_event(failed.id, db)
    assert replayed.status == "DEAD_LETTER"
    assert replayed.attempt_count == 2
    assert db.scalar(select(IntegrationEvent).where(IntegrationEvent.id == failed.id)).last_error
    db.close()
