from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.factories import create_factory
from app.api.routes.features import build_point_snapshot
from app.api.routes.master_data import (
    bind_factory_vehicle_model,
    bind_vehicle_model_color,
    create_color,
    create_measurement_point,
    create_part,
    create_vehicle_model,
)
from app.api.routes.material_governance import (
    create_applicability,
    create_definition,
    create_method,
    create_result,
    create_specification,
    material_governance_summary,
    update_result,
    update_specification,
)
from app.api.routes.process import (
    create_brush,
    create_brush_parameter,
    create_material_batch,
    create_production_run,
    create_production_stage_run,
    create_program_version,
    create_spray_program,
    upsert_brush_point_contribution,
)
from tests.schema_guard import create_transient_test_schema
from app.schemas.common import FactoryCreate
from app.schemas.features import PointFeatureBuildRequest
from app.schemas.master_data import (
    ColorCreate,
    FactoryVehicleModelCreate,
    MeasurementPointCreate,
    PartCreate,
    VehicleModelColorCreate,
    VehicleModelCreate,
)
from app.schemas.material import (
    MaterialBatchTestResultCreate,
    MaterialBatchTestResultUpdate,
    MaterialCharacteristicApplicabilityCreate,
    MaterialCharacteristicDefinitionCreate,
    MaterialSpecificationCreate,
    MaterialSpecificationUpdate,
    MaterialTestMethodCreate,
)
from app.schemas.process import (
    BrushCreate,
    BrushParameterCreate,
    BrushPointContributionUpsert,
    MaterialBatchCreate,
    ProductionRunCreate,
    ProductionStageRunCreate,
    SprayProgramCreate,
    SprayProgramVersionCreate,
)


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


def test_active_material_governance_requires_approval_evidence() -> None:
    db = build_session()
    now = datetime.now(UTC)
    definition = create_definition(
        MaterialCharacteristicDefinitionCreate(
            code="approval_gate",
            name="审批门禁特性",
            category="VISCOSITY_RHEOLOGY",
            canonical_unit="s",
            target_families=["ORANGE_PEEL"],
        ),
        db,
    )
    with pytest.raises(HTTPException, match="批准规程来源"):
        create_method(
            MaterialTestMethodCreate(
                characteristic_definition_id=definition.id,
                code="METHOD-NO-SOURCE",
                name="缺少来源方法",
                version="1.0",
                method_type="FLOW_CUP",
                result_unit="s",
            ),
            db,
        )
    method = create_method(
        MaterialTestMethodCreate(
            characteristic_definition_id=definition.id,
            code="METHOD-APPROVED",
            name="批准方法",
            version="1.0",
            method_type="FLOW_CUP",
            result_unit="s",
            procedure_uri="approved://material/method/approval-gate",
        ),
        db,
    )
    with pytest.raises(HTTPException, match="来源、生效时间和审批人"):
        create_specification(
            MaterialSpecificationCreate(
                material_code="CC-GATE",
                characteristic_definition_id=definition.id,
                method_id=method.id,
                version="1.0",
                status="ACTIVE",
            ),
            db,
        )
    with pytest.raises(HTTPException, match="适用关系必须维护审批人"):
        create_applicability(
            MaterialCharacteristicApplicabilityCreate(
                characteristic_definition_id=definition.id,
                material_type="CLEARCOAT",
                process_stage="CLEARCOAT_2",
                target_family="ORANGE_PEEL",
                status="ACTIVE",
            ),
            db,
        )
    db.close()


def test_specification_reassignment_recomputes_old_result_reliability() -> None:
    db = build_session()
    now = datetime.now(UTC)
    batch = create_material_batch(
        MaterialBatchCreate(
            batch_no="LOT-REASSIGN",
            material_code="CC-REASSIGN",
            material_name="规格重分配清漆",
            material_type="CLEARCOAT",
        ),
        db,
    )
    definitions = [
        create_definition(
            MaterialCharacteristicDefinitionCreate(
                code=code,
                name=name,
                category="VISCOSITY_RHEOLOGY",
                canonical_unit="s",
                target_families=["ORANGE_PEEL"],
            ),
            db,
        )
        for code, name in (("reassign_a", "重分配 A"), ("reassign_b", "重分配 B"))
    ]
    methods = [
        create_method(
            MaterialTestMethodCreate(
                characteristic_definition_id=definition.id,
                code=f"METHOD-{index}",
                name=f"重分配方法 {index}",
                version="1.0",
                method_type="FLOW_CUP",
                result_unit="s",
                procedure_uri=f"approved://material/method/reassign-{index}",
            ),
            db,
        )
        for index, definition in enumerate(definitions, start=1)
    ]
    specification = create_specification(
        MaterialSpecificationCreate(
            material_code=batch.material_code,
            characteristic_definition_id=definitions[0].id,
            method_id=methods[0].id,
            version="1.0",
            status="ACTIVE",
            source_uri="approved://material/spec/reassign",
            effective_from=now - timedelta(days=1),
            approved_by="材料工程师",
        ),
        db,
    )
    result = create_result(
        MaterialBatchTestResultCreate(
            result_no="MAT-REASSIGN-001",
            material_batch_id=batch.id,
            characteristic_definition_id=definitions[0].id,
            method_id=methods[0].id,
            result_value=22,
            unit="s",
            tested_at=now,
            source_uri="approved://material/result/reassign",
        ),
        db,
    )
    assert result.reliability_status == "VERIFIED"

    update_specification(
        specification.id,
        MaterialSpecificationUpdate(
            characteristic_definition_id=definitions[1].id,
            method_id=methods[1].id,
        ),
        db,
    )
    db.refresh(result)
    assert result.reliability_status == "VERIFIED"
    assert result.specification_id is None
    assert any("缺少检测时间有效的批准材料规格" in issue for issue in (result.reliability_issues or []))
    db.close()


def test_governed_material_result_enters_features_and_failed_result_blocks_required_feature() -> None:
    db = build_session()
    now = datetime.now(UTC)
    factory = create_factory(FactoryCreate(code="F-MAT", name="材料治理工厂"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code="M-MAT", name="材料治理车型"), db)
    color = create_color(ColorCreate(code="C-MAT", name="材料治理颜色", color_type="BASECOAT"), db)
    bind_factory_vehicle_model(
        FactoryVehicleModelCreate(factory_id=factory.id, vehicle_model_id=vehicle.id),
        db,
    )
    bind_vehicle_model_color(
        VehicleModelColorCreate(vehicle_model_id=vehicle.id, color_id=color.id),
        db,
    )
    part = create_part(PartCreate(code="P-MAT", name="车顶"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code="PT-MAT",
            name="材料治理点位",
            vehicle_model_id=vehicle.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-MAT",
            name="清漆二站",
            factory_id=factory.id,
            process_stage="CLEARCOAT_2",
            station_code="P1C1A2",
            station_name="清漆二站",
        ),
        db,
    )
    version = create_program_version(
        program.id, SprayProgramVersionCreate(version="V1", status="ACTIVE"), db
    )
    brush = create_brush(
        version.id, BrushCreate(brush_no="B-MAT", brush_table_no="BT-MAT"), db
    )
    create_brush_parameter(
        brush.id,
        BrushParameterCreate(
            parameter_code="clearcoat_2_spray_flow",
            parameter_name="清漆二站喷涂流量",
            configured_value=300,
            unit="ml/min",
        ),
        db,
    )
    upsert_brush_point_contribution(
        brush.id,
        point.id,
        BrushPointContributionUpsert(
            overlap_ratio=1,
            contribution_weight=1,
            is_approved=True,
        ),
        db,
    )
    material = create_material_batch(
        MaterialBatchCreate(
            batch_no="LOT-MAT",
            material_code="CC-MAT",
            material_name="治理清漆",
            material_type="CLEARCOAT",
            viscosity=999,
            coa_values={"legacy_density": 999},
        ),
        db,
    )
    definition = create_definition(
        MaterialCharacteristicDefinitionCreate(
            code="viscosity",
            name="粘度",
            category="VISCOSITY_RHEOLOGY",
            canonical_unit="s",
            target_families=["ORANGE_PEEL", "THICKNESS"],
        ),
        db,
    )
    method = create_method(
        MaterialTestMethodCreate(
            characteristic_definition_id=definition.id,
            code="VISC-CUP",
            name="受控粘度方法",
            version="1.0",
            method_type="FLOW_CUP",
            result_unit="s",
            procedure_uri="approved://material/method/viscosity",
        ),
        db,
    )
    specification = create_specification(
        MaterialSpecificationCreate(
            material_code=material.material_code,
            characteristic_definition_id=definition.id,
            method_id=method.id,
            version="1.0",
            lower_limit=20,
            upper_limit=25,
            status="ACTIVE",
            source_uri="approved://material/spec/CC-MAT/viscosity",
            effective_from=now - timedelta(days=1),
            approved_by="材料工程师",
        ),
        db,
    )
    create_applicability(
        MaterialCharacteristicApplicabilityCreate(
            characteristic_definition_id=definition.id,
            material_type="CLEARCOAT",
            process_stage="CLEARCOAT_2",
            target_family="ORANGE_PEEL",
            is_required=True,
            status="ACTIVE",
            approved_by="工艺工程师",
        ),
        db,
    )
    result = create_result(
        MaterialBatchTestResultCreate(
            result_no="MAT-RESULT-001",
            material_batch_id=material.id,
            characteristic_definition_id=definition.id,
            method_id=method.id,
            result_value=22.5,
            unit="s",
            tested_at=now - timedelta(hours=1),
            tested_by="材料工程师",
            source_uri="approved://material/results/MAT-RESULT-001",
        ),
        db,
    )
    assert result.reliability_status == "VERIFIED"
    assert result.specification_id == specification.id
    assert result.is_within_spec is True

    run = create_production_run(
        ProductionRunCreate(
            run_no="RUN-MAT",
            factory_id=factory.id,
            vehicle_model_id=vehicle.id,
            color_id=color.id,
            started_at=now,
        ),
        db,
    )
    create_production_stage_run(
        run.id,
        ProductionStageRunCreate(
            process_stage="CLEARCOAT_2",
            program_version_id=version.id,
            material_batch_id=material.id,
        ),
        db,
    )
    snapshot = build_point_snapshot(
        PointFeatureBuildRequest(
            production_run_id=run.id,
            measurement_point_id=point.id,
            target_family="ORANGE_PEEL",
        ),
        db,
    )
    assert snapshot["feature_values"]["clearcoat_2.material.viscosity"] == 22.5
    assert "clearcoat_2.material_viscosity" not in snapshot["feature_values"]
    assert snapshot["lineage"]["material_result_ids"] == [result.id]
    assert snapshot["lineage"]["material_specification_ids"] == [specification.id]
    assert material_governance_summary(db)["verified_results"] == 1

    failed = update_result(
        result.id,
        MaterialBatchTestResultUpdate(result_value=27),
        db,
    )
    assert failed.reliability_status == "FAILED"
    assert failed.is_within_spec is False
    # Day-1: required material gaps no longer hard-block snapshot build.
    blocked = build_point_snapshot(
        PointFeatureBuildRequest(
            production_run_id=run.id,
            measurement_point_id=point.id,
            target_family="ORANGE_PEEL",
        ),
        db,
    )
    assert "clearcoat_2.material.viscosity" not in blocked["feature_values"]
    db.close()
