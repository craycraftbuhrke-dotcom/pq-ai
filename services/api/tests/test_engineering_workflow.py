import base64
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.engineering import (
    create_contribution_validation,
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
    preview_file_import_job,
    replay_file_import_job,
    create_supplier_issue,
    create_supplier_submission,
    create_trajectory_geometry,
    engineering_summary,
    update_issue_task,
)
from app.api.routes.factories import create_factory
from app.api.routes.master_data import (
    create_color,
    create_measurement_point,
    create_part,
    create_vehicle_model,
)
from app.api.routes.measurement_governance import create_instrument, create_method
from app.api.routes.process import (
    create_brush,
    create_material_batch,
    create_program_version,
    create_spray_program,
)
from app.api.routes.robot_governance import (
    create_contribution_version,
    create_path_segment,
    create_trajectory_program,
)
from app.models.domain import ModelVersion
from app.schemas.common import FactoryCreate
from app.schemas.engineering import (
    ContributionValidationStudyCreate,
    EngineeringKnowledgeEntryCreate,
    FileImportProfileCreate,
    FileImportPreviewRequest,
    FileImportReplayRequest,
    MeasurementMsaStudyCreate,
    MeasurementProbeCreate,
    ModelExplanationCreate,
    ProcessRouteApplicabilityCreate,
    ProcessRouteCreate,
    ProcessRouteStepCreate,
    QualityIssueCommentCreate,
    QualityIssueEvidenceCreate,
    QualityIssueTaskCreate,
    QualityIssueTaskUpdate,
    SupplierMaterialIssueCreate,
    SupplierMaterialSubmissionCreate,
    TrajectorySegmentGeometryCreate,
)
from app.schemas.master_data import (
    ColorCreate,
    MeasurementPointCreate,
    PartCreate,
    VehicleModelCreate,
)
from app.schemas.process import (
    BrushCreate,
    MaterialBatchCreate,
    PointContributionVersionCreate,
    SprayProgramCreate,
    SprayProgramVersionCreate,
    TrajectoryPathSegmentCreate,
    TrajectoryProgramCreate,
)
from app.schemas.quality import MeasurementInstrumentCreate, MeasurementMethodCreate
from tests.schema_guard import create_transient_test_schema


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


def seed_context(db: Session):
    now = datetime.now(UTC)
    factory = create_factory(FactoryCreate(code="F-ENG", name="工程闭环工厂"), db)
    vehicle = create_vehicle_model(VehicleModelCreate(code="M-ENG", name="工程车型"), db)
    color = create_color(ColorCreate(code="C-ENG", name="工程色漆", color_type="BASECOAT"), db)
    part = create_part(PartCreate(code="P-ENG", name="发动机罩"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code="PT-ENG",
            name="发动机罩中部",
            vehicle_model_id=vehicle.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL", "THICKNESS"],
        ),
        db,
    )
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-ENG",
            name="清漆二站",
            factory_id=factory.id,
            process_stage="CLEARCOAT_2",
            station_code="P1C1A2",
            station_name="清漆二站",
        ),
        db,
    )
    version = create_program_version(
        program.id,
        SprayProgramVersionCreate(version="V1", vehicle_model_ids=[vehicle.id], color_ids=[color.id]),
        db,
    )
    brush = create_brush(version.id, BrushCreate(brush_no="B-ENG", brush_table_no="BT-ENG"), db)
    trajectory = create_trajectory_program(
        TrajectoryProgramCreate(
            program_version_id=version.id,
            trajectory_code="TRJ-ENG",
            name="工程轨迹",
            version="1.0",
            checksum="checksum-eng",
            tcp_name="BELL",
        ),
        db,
    )
    segment = create_path_segment(
        TrajectoryPathSegmentCreate(
            trajectory_program_id=trajectory.id,
            segment_no=1,
            name="发动机罩路径段",
            brush_id=brush.id,
            part_id=part.id,
            configured_speed=800,
            speed_unit="mm/s",
            trigger_state="ON",
        ),
        db,
    )
    contribution = create_contribution_version(
        PointContributionVersionCreate(
            program_version_id=version.id,
            target_family="ORANGE_PEEL",
            version="1.0",
            method="GEOMETRY",
            approved_by="工艺工程师",
        ),
        db,
    )
    material_batch = create_material_batch(
        MaterialBatchCreate(
            batch_no="MAT-ENG",
            material_code="CC-001",
            material_name="清漆材料",
            material_type="CLEARCOAT",
            supplier="供应商A",
        ),
        db,
    )
    return factory, vehicle, color, part, point, version, segment, contribution, material_batch, now


def test_engineering_route_task_supplier_measurement_and_ai_workflow() -> None:
    db = build_session()
    factory, vehicle, color, _part, point, _version, segment, contribution, material_batch, now = seed_context(db)

    with pytest.raises(HTTPException) as approval_error:
        create_process_route(
            ProcessRouteCreate(
                factory_id=factory.id,
                route_code="3C3B-ENG",
                name="工程 3C3B 路线",
                version="1.0",
                status="ACTIVE",
            ),
            db,
        )
    assert approval_error.value.status_code == 422

    route = create_process_route(
        ProcessRouteCreate(
            factory_id=factory.id,
            route_code="3C3B-ENG",
            name="工程 3C3B 路线",
            version="1.0",
            status="ACTIVE",
            approved_by="工艺负责人",
        ),
        db,
    )
    assert route.approved_at is not None
    step = create_process_route_step(
        ProcessRouteStepCreate(
            process_route_id=route.id,
            sequence_no=5,
            step_code="CLEAR2",
            step_name="清漆二站",
            step_type="SPRAY_STAGE",
            coating_system="CLEARCOAT",
            process_stage="CLEARCOAT_2",
            is_ai_feature_source=True,
        ),
        db,
    )
    assert step.process_stage == "CLEARCOAT_2"
    applicability = create_process_route_applicability(
        ProcessRouteApplicabilityCreate(
            process_route_id=route.id,
            vehicle_model_id=vehicle.id,
            color_id=color.id,
        ),
        db,
    )
    assert applicability.status == "ACTIVE"

    durr_profile = create_file_import_profile(
        FileImportProfileCreate(
            code="DXQ-ENG",
            name="DXQ 导入",
            version="1.0",
            domain_type="DURR_DXQ",
            parser_type="DXQ_EXPORT",
            target_resource="trajectory-geometries",
            field_mapping={"segment": "segment_no"},
            required_fields=["segment_no"],
            validation_rules={"numeric_fields": ["segment_no"], "max_rows": 10},
            status="ACTIVE",
            approved_by="机器人负责人",
        ),
        db,
    )
    import_job = preview_file_import_job(
        FileImportPreviewRequest(
            import_no="IMP-DXQ-ENG",
            profile_id=durr_profile.id,
            source_filename="dxq-export.csv",
            content_base64=base64.b64encode(b"segment,speed\n1,800\n").decode("ascii"),
            submitted_by="robot_engineer",
        ),
        db,
    )
    assert import_job.status == "VALIDATED"
    assert import_job.row_count == 1
    assert import_job.preview_payload["preview_rows"][0]["segment_no"] == "1"
    replay = replay_file_import_job(
        import_job.id,
        FileImportReplayRequest(import_no="REPLAY-DXQ-ENG", submitted_by="robot_engineer"),
        db,
    )
    assert replay.status == "REPLAYED"
    assert replay.replay_of_job_id == import_job.id
    geometry = create_trajectory_geometry(
        TrajectorySegmentGeometryCreate(
            path_segment_id=segment.id,
            geometry_version="1.0",
            source_import_job_id=import_job.id,
            gun_distance=280,
            path_spacing=55,
            overlap_ratio=0.62,
            status="VALIDATED",
        ),
        db,
    )
    assert geometry.source_import_job_id == import_job.id

    instrument = create_instrument(
        MeasurementInstrumentCreate(
            code="FISCHER-ENG",
            name="Fischer 膜厚仪",
            manufacturer="Helmut Fischer",
            model="Dualscope",
            instrument_type="FISCHER_THICKNESS",
            serial_no="SN-FISCHER-ENG",
            supported_quality_types=["THICKNESS"],
        ),
        db,
    )
    method = create_method(
        MeasurementMethodCreate(
            code="FISCHER-MSA",
            name="膜厚 MSA",
            version="1.0",
            quality_type="THICKNESS",
            instrument_type="FISCHER_THICKNESS",
            method_type="MAGNETIC_INDUCTION",
        ),
        db,
    )
    probe = create_measurement_probe(
        MeasurementProbeCreate(
            instrument_id=instrument.id,
            code="PROBE-1",
            name="磁感应探头",
            probe_type="MAGNETIC_INDUCTION",
            substrate_type="STEEL",
            layer_scope="TOTAL_FILM",
        ),
        db,
    )
    msa = create_measurement_msa_study(
        MeasurementMsaStudyCreate(
            study_no="MSA-ENG",
            instrument_id=instrument.id,
            probe_id=probe.id,
            method_id=method.id,
            quality_type="THICKNESS",
            metric_code="thickness_total",
            sample_count=10,
            operator_count=3,
            repeat_count=2,
            result="PASS",
            study_at=now,
            approved_by="质量负责人",
        ),
        db,
    )
    assert msa.approved_at is not None

    material_profile = create_file_import_profile(
        FileImportProfileCreate(
            code="COA-ENG",
            name="COA 导入",
            version="1.0",
            domain_type="MATERIAL_COA",
            target_resource="supplier-submissions",
            field_mapping={"viscosity": "viscosity"},
            required_fields=["viscosity"],
            status="ACTIVE",
            approved_by="材料工程师",
        ),
        db,
    )
    submission = create_supplier_submission(
        SupplierMaterialSubmissionCreate(
            submission_no="SUB-ENG",
            supplier="供应商A",
            material_batch_id=material_batch.id,
            material_code=material_batch.material_code,
            material_name=material_batch.material_name,
            document_type="COA",
            profile_id=material_profile.id,
            status="ACCEPTED",
            submitted_by="supplier",
            reviewed_by="material_engineer",
            field_values={"viscosity": 23.5},
        ),
        db,
    )
    assert submission.reviewed_at is not None
    supplier_issue = create_supplier_issue(
        SupplierMaterialIssueCreate(
            issue_no="SUP-ISS-ENG",
            submission_id=submission.id,
            material_batch_id=material_batch.id,
            issue_type="COA_FIELD_MISSING",
            status="CLOSED",
            description="COA 缺少固含字段，已补充。",
            resolution="供应商补交新版 COA",
        ),
        db,
    )
    assert supplier_issue.closed_at is not None

    validation = create_contribution_validation(
        ContributionValidationStudyCreate(
            contribution_version_id=contribution.id,
            study_no="CONTRIB-ENG",
            target_family="ORANGE_PEEL",
            method="DXQ_SIMULATION",
            status="APPROVED",
            validation_score=0.88,
            approved_by="工艺负责人",
        ),
        db,
    )
    assert validation.approved_at is not None

    task = create_issue_task(
        QualityIssueTaskCreate(
            task_no="QI-ENG",
            title="清漆二站 DOI 偏低",
            severity="HIGH",
            factory_id=factory.id,
            vehicle_model_id=vehicle.id,
            color_id=color.id,
            measurement_point_id=point.id,
            material_batch_id=material_batch.id,
            process_stage="CLEARCOAT_2",
            target_quality_type="ORANGE_PEEL",
            target_metric="doi",
            created_by="quality_engineer",
            problem_statement="发动机罩中部 DOI 低于封样标准，需复核测量、材料与 Dürr 执行。",
        ),
        db,
    )
    create_issue_task_evidence(
        task.id,
        QualityIssueEvidenceCreate(
            evidence_type="MEASUREMENT_REVIEW",
            source_type="MSA",
            source_id=msa.id,
            summary="膜厚 MSA 通过，测量系统可用于诊断。",
            confidence=0.9,
            created_by="quality_engineer",
        ),
        db,
    )
    create_issue_task_comment(
        task.id,
        QualityIssueCommentCreate(
            author="process_engineer",
            role="PROCESS_ENGINEER",
            body="优先复核清漆二站外成型空气与枪距。",
        ),
        db,
    )
    closed = update_issue_task(
        task.id,
        QualityIssueTaskUpdate(
            status="CLOSED",
            conclusion="通过受控试验确认清漆二站外成型空气偏高与 DOI 下降相关。",
        ),
        db,
    )
    assert closed.closed_at is not None

    knowledge = create_knowledge_entry(
        EngineeringKnowledgeEntryCreate(
            entry_code="KB-DOI-LOW",
            version="1.0",
            title="DOI 偏低结构谱诊断",
            category="ORANGE_PEEL",
            target_quality_type="ORANGE_PEEL",
            metric_code="doi",
            symptom_pattern="DOI 低，LW/SW 同时恶化",
            diagnosis_rule="先排除测量可靠性，再复核清漆流量、成型空气、枪距、速度和材料固含。",
            recommended_checks={"measurement": ["calibration", "repeatability"]},
            related_parameters=["clearcoat_2_outer_shaping_air", "clearcoat_2_gun_distance"],
            status="ACTIVE",
            created_by="quality_engineer",
            approved_by="process_owner",
        ),
        db,
    )
    assert knowledge.approved_at is not None

    model = ModelVersion(
        model_code="MODEL-ENG",
        version="1.0",
        model_type="XGBOOST",
        target_metric="doi",
        feature_set_version="fs-1",
        artifact_uri="s3://models/model-eng",
        model_payload={"family": "tree"},
        evaluation_metrics={"rmse": 1.2},
        training_sample_count=120,
        status="ACTIVE",
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    explanation = create_model_explanation(
        ModelExplanationCreate(
            model_version_id=model.id,
            explanation_type="SHAP",
            target_metric="doi",
            feature_impacts={"clearcoat_2_outer_shaping_air": -0.42},
            generated_by="data_scientist",
        ),
        db,
    )
    assert explanation.generated_at is not None

    summary = engineering_summary(db)
    assert summary["active_routes"] == 1
    assert summary["open_tasks"] == 0
    assert summary["supplier_submissions"] == 1
    assert summary["model_explanations"] == 1
    db.close()
