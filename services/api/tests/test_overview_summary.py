"""Tests for GET /process/overview-summary and GET /ai/overview-summary."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.ai import ai_overview_summary
from app.api.routes.process import process_overview_summary
from app.models.domain import (
    Color,
    ControlledTrial,
    Factory,
    MeasurementPoint,
    ModelVersion,
    Part,
    PredictionResult,
    ProductionRun,
    QualityIssueTask,
    Recommendation,
    SprayProgram,
    SprayProgramVersion,
    VehicleModel,
    VersionStatus,
)
from tests.schema_guard import create_transient_test_schema


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


def _seed_context(session: Session) -> tuple[str, str, str, str]:
    factory = Factory(code="F1", name="Factory 1")
    session.add(factory)
    vm = VehicleModel(code="V1", name="Vehicle 1")
    session.add(vm)
    color = Color(code="C1", name="Color 1", color_type="SOLID")
    session.add(color)
    part = Part(code="DOOR", name="Door")
    session.add(part)
    session.flush()
    return factory.id, vm.id, color.id, part.id


def test_process_overview_summary_empty_database() -> None:
    db = _build_session()
    try:
        summary = process_overview_summary(db)
        assert summary.active_runs == 0
        assert summary.total_runs == 0
        assert len(summary.stages) == 5
        assert all(s.run_count == 0 and not s.healthy for s in summary.stages)
        assert summary.program_versions_active == 0
        assert summary.program_versions_draft == 0
        assert summary.open_issue_tasks == 0
        assert summary.recent_runs == []
    finally:
        db.close()


def test_process_overview_summary_with_data() -> None:
    db = _build_session()
    try:
        factory_id, vm_id, color_id, _part_id = _seed_context(db)
        run = ProductionRun(
            run_no="RUN-001",
            factory_id=factory_id,
            vehicle_model_id=vm_id,
            color_id=color_id,
            started_at=datetime.now(UTC),
        )
        db.add(run)
        program = SprayProgram(
            program_code="PROG-1",
            name="Program 1",
            factory_id=factory_id,
            process_stage="MIDCOAT_EXT",
            station_code="STN-1",
            station_name="Station 1",
        )
        db.add(program)
        db.flush()
        version_active = SprayProgramVersion(
            spray_program_id=program.id,
            version="v1",
            status=VersionStatus.ACTIVE,
        )
        version_draft = SprayProgramVersion(
            spray_program_id=program.id,
            version="v2",
            status=VersionStatus.DRAFT,
        )
        db.add_all([version_active, version_draft])
        issue = QualityIssueTask(
            task_no="ISSUE-1",
            title="Open issue",
            status="OPEN",
            created_by="tester",
            problem_statement="test problem",
        )
        db.add(issue)
        db.commit()

        summary = process_overview_summary(db)
        assert summary.total_runs == 1
        assert summary.active_runs == 1
        assert summary.program_versions_active == 1
        assert summary.program_versions_draft == 1
        assert summary.open_issue_tasks == 1
        assert len(summary.recent_runs) == 1
        assert summary.recent_runs[0]["run_no"] == "RUN-001"
    finally:
        db.close()


def test_ai_overview_summary_empty_database() -> None:
    db = _build_session()
    try:
        summary = ai_overview_summary(db)
        assert summary.models_approved == 0
        assert summary.models_total == 0
        assert summary.latest_model_metric is None
        assert summary.predictions_24h == 0
        assert summary.top_risk_point is None
        assert summary.recommendations_pending == 0
        assert summary.recommendations_total == 0
        assert summary.trials_active == 0
        assert summary.trials_completed == 0
        assert summary.open_changes == 0
    finally:
        db.close()


def test_ai_overview_summary_with_data() -> None:
    db = _build_session()
    try:
        factory_id, vm_id, color_id, part_id = _seed_context(db)
        model = ModelVersion(
            model_code="M1",
            version="v1",
            model_type="THICKNESS",
            target_metric="THICKNESS",
            feature_set_version="fs-1",
            artifact_uri="file:///m1",
            model_payload={},
            evaluation_metrics={},
            status=VersionStatus.APPROVED,
            trained_at=datetime.now(UTC),
        )
        db.add(model)
        point = MeasurementPoint(
            vehicle_model_id=vm_id,
            code="P001",
            name="Point 1",
            part_id=part_id,
        )
        db.add(point)
        run = ProductionRun(
            run_no="RUN-1",
            factory_id=factory_id,
            vehicle_model_id=vm_id,
            color_id=color_id,
            started_at=datetime.now(UTC),
        )
        db.add(run)
        db.flush()
        prediction = PredictionResult(
            model_version_id=model.id,
            production_run_id=run.id,
            measurement_point_id=point.id,
            metric_code="THICKNESS",
            predicted_value=20.0,
            confidence=0.9,
            predicted_at=datetime.now(UTC),
        )
        db.add(prediction)
        recommendation = Recommendation(
            recommendation_no="REC-1",
            production_run_id=run.id,
            measurement_point_id=point.id,
            target_quality_type="THICKNESS",
            target_metric="THICKNESS",
            diagnosis_summary="test",
            predicted_improvement=1.0,
            confidence=0.8,
            status="PENDING",
            model_version="v1",
        )
        db.add(recommendation)
        db.flush()
        trial = ControlledTrial(
            recommendation_id=recommendation.id,
            trial_no="T-1",
            production_run_id=run.id,
            measurement_point_id=point.id,
            target_metric="THICKNESS",
            evidence_type="A_B",
            requested_by="tester",
            requested_at=datetime.now(UTC),
            status="PLANNED",
        )
        db.add(trial)
        issue = QualityIssueTask(
            task_no="ISSUE-1",
            title="Open",
            status="OPEN",
            created_by="tester",
            problem_statement="test problem",
        )
        db.add(issue)
        db.commit()

        summary = ai_overview_summary(db)
        assert summary.models_approved == 1
        assert summary.models_total == 1
        assert summary.predictions_24h == 1
        assert summary.top_risk_point == "P001"
        assert summary.recommendations_pending == 1
        assert summary.recommendations_total == 1
        assert summary.trials_active == 1
        assert summary.open_changes == 1
    finally:
        db.close()
