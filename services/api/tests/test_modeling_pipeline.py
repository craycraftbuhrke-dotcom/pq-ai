from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.modeling import (
    change_model_status,
    diagnose_from_prediction,
    get_model_drift,
    list_feature_snapshots,
    predict_from_snapshot,
    recommend_from_snapshot,
    train_baseline_model,
)
from app.api.routes.ai import (
    approve_recommendation,
    execute_recommendation,
    get_recommendation,
    list_diagnoses,
    list_evaluations,
    list_predictions,
    list_recommendations,
    verify_recommendation,
)
from app.db.base import Base
from app.domain.scope_policy import CURRENT_FEATURE_SET_VERSION
from app.models import domain  # noqa: F401
from app.models.domain import (
    Color,
    Factory,
    MeasurementPoint,
    ParameterDefinition,
    Part,
    PointFeatureSnapshot,
    ProductionRun,
    QualityMeasurement,
    QualityMetricValue,
    Recommendation,
    VehicleModel,
)
from app.schemas.common import (
    RecommendationApproval,
    RecommendationExecution,
    RecommendationExecutionAction,
    RecommendationVerification,
)
from app.schemas.modeling import (
    ModelPredictionRequest,
    ModelRecommendationRequest,
    ModelStatusUpdate,
    ModelTrainingRequest,
)
from app.services.demo import dashboard_snapshot


def test_train_predict_and_diagnose_real_point_snapshots() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    with Session(engine, expire_on_commit=False) as db:
        factory = Factory(code="F1", name="工厂")
        model = VehicleModel(code="M1", name="车型")
        color = Color(code="C1", name="颜色", color_type="BASECOAT")
        part = Part(code="ROOF", name="车顶")
        db.add_all([factory, model, color, part])
        db.flush()
        point = MeasurementPoint(
            code="P1",
            name="点位",
            vehicle_model_id=model.id,
            part_id=part.id,
            quality_types=["ORANGE_PEEL"],
        )
        db.add(point)
        db.flush()
        db.add_all(
            [
                ParameterDefinition(
                    code="spray_flow",
                    name="喷涂流量",
                    category="清漆二站",
                    unit="ml/min",
                    hard_min=0,
                    hard_max=20,
                    is_recommendable=True,
                ),
                ParameterDefinition(
                    code="outer_air",
                    name="外成型空气流量",
                    category="清漆二站",
                    unit="Nl/min",
                    hard_min=0,
                    hard_max=10,
                    is_recommendable=True,
                ),
            ]
        )

        runs = []
        for index in range(8):
            run = ProductionRun(
                run_no=f"RUN-{index}",
                factory_id=factory.id,
                vehicle_model_id=model.id,
                color_id=color.id,
                started_at=now + timedelta(minutes=index),
            )
            db.add(run)
            db.flush()
            x1 = float(index)
            x2 = float((index * 2) % 5)
            target = 10.0 + 2.0 * x1 - 0.5 * x2
            db.add(
                PointFeatureSnapshot(
                    production_run_id=run.id,
                    measurement_point_id=point.id,
                    feature_set_version=CURRENT_FEATURE_SET_VERSION,
                    feature_values={"clearcoat_2.spray_flow": x1, "clearcoat_2.outer_air": x2},
                    completeness_score=1.0,
                    generated_at=now,
                )
            )
            measurement = QualityMeasurement(
                data_no=f"QM-{index}",
                production_run_id=run.id,
                measurement_point_id=point.id,
                quality_type="ORANGE_PEEL",
                measured_at=now + timedelta(minutes=index),
            )
            db.add(measurement)
            db.flush()
            db.add(
                QualityMetricValue(
                    measurement_id=measurement.id,
                    metric_code="doi",
                    metric_name="DOI",
                    raw_value=target,
                )
            )
            runs.append((run, target))
        db.commit()

        trained = train_baseline_model(
            ModelTrainingRequest(
                model_code="DOI-BASELINE",
                version="1.0",
                target_metric="doi",
                min_samples=5,
                ridge_lambda=0.01,
            ),
            db,
        )
        assert trained.model_type == "RIDGE_REGRESSION_BASELINE"
        assert trained.training_sample_count == 8
        assert trained.evaluation_metrics["training_r2"] > 0.99
        snapshots = list_feature_snapshots(db)
        assert len(snapshots) == 8
        assert snapshots[0]["feature_count"] == 2
        assert snapshots[0]["production_run_no"].startswith("RUN-")

        prediction = predict_from_snapshot(
            trained.id,
            ModelPredictionRequest(
                production_run_id=runs[-1][0].id,
                measurement_point_id=point.id,
            ),
            db,
        )
        assert prediction["predicted_value"] == pytest.approx(runs[-1][1], abs=0.2)
        assert prediction["prediction_result_id"]
        drift = get_model_drift(trained.id, db)
        assert drift["monitored_snapshot_count"] == 8
        assert drift["prediction_count"] == 1
        assert drift["labeled_prediction_count"] == 1
        assert drift["feature_drift"]
        assert drift["feature_drift"][0]["standardized_mean_shift"] is not None
        assert drift["drift_status"] in {"STABLE", "WATCH", "DRIFT"}

        diagnosis = diagnose_from_prediction(prediction["prediction_result_id"], db)
        assert diagnosis["causality_status"] == "CORRELATION_ONLY"
        assert diagnosis["factor_contributions"]
        assert diagnosis["factor_contributions"][0]["feature"].startswith("clearcoat_2.")
        assert list_predictions(db)[0]["model_name"] == "DOI-BASELINE:1.0"
        assert list_diagnoses(db)[0]["id"] == diagnosis["diagnosis_result_id"]

        recommendation = recommend_from_snapshot(
            trained.id,
            ModelRecommendationRequest(
                production_run_id=runs[-1][0].id,
                measurement_point_id=point.id,
                target_min=prediction["predicted_value"] + 1.0,
                max_actions=2,
            ),
            db,
        )
        assert recommendation["status"] == "PENDING"
        assert recommendation["constraints_checked"] is True
        assert recommendation["predicted_improvement"] > 0
        assert recommendation["actions"]
        assert all(
            action["hard_min"] <= action["recommended_value"] <= action["hard_max"]
            for action in recommendation["actions"]
        )

        approval = approve_recommendation(
            recommendation["recommendation_id"],
            RecommendationApproval(approved=True, approved_by="陈工", comment="受控试验"),
            db,
        )
        assert approval["status"] == "APPROVED"
        execution = execute_recommendation(
            recommendation["recommendation_id"],
            RecommendationExecution(
                executed_by="机器人程序员",
                actions=[
                    RecommendationExecutionAction(
                        action_id=action["id"], executed_value=action["recommended_value"]
                    )
                    for action in recommendation["actions"]
                ],
            ),
            db,
        )
        assert execution["status"] == "EXECUTED"
        db.expire_all()
        persisted_recommendation = db.get(Recommendation, recommendation["recommendation_id"])
        assert persisted_recommendation.executed_by == "机器人程序员"
        assert persisted_recommendation.executed_at is not None
        pre_execution_measurement = QualityMeasurement(
            data_no="QM-PRE-EXECUTION",
            production_run_id=runs[-1][0].id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=persisted_recommendation.executed_at - timedelta(seconds=1),
        )
        db.add(pre_execution_measurement)
        db.flush()
        db.add(
            QualityMetricValue(
                measurement_id=pre_execution_measurement.id,
                metric_code="doi",
                metric_name="DOI",
                raw_value=runs[-1][1],
            )
        )
        db.commit()
        with pytest.raises(HTTPException, match="复测记录必须晚于推荐任务执行时间"):
            verify_recommendation(
                recommendation["recommendation_id"],
                RecommendationVerification(
                    verified_measurement_id=pre_execution_measurement.id,
                    verified_by="质量工程师",
                ),
                db,
            )

        verified_measurement = QualityMeasurement(
            data_no="QM-VERIFIED",
            production_run_id=runs[-1][0].id,
            measurement_point_id=point.id,
            quality_type="ORANGE_PEEL",
            measured_at=now + timedelta(hours=1),
        )
        db.add(verified_measurement)
        db.flush()
        db.add(
            QualityMetricValue(
                measurement_id=verified_measurement.id,
                metric_code="doi",
                metric_name="DOI",
                raw_value=runs[-1][1] + 1.2,
            )
        )
        db.commit()
        verification = verify_recommendation(
            recommendation["recommendation_id"],
            RecommendationVerification(
                verified_measurement_id=verified_measurement.id,
                verified_by="质量工程师",
                conclusion="复测改善有效",
            ),
            db,
        )
        assert verification["status"] == "VERIFIED"
        assert verification["actual_improvement"] == pytest.approx(1.2)
        assert verification["is_effective"] is True
        recommendation_detail = get_recommendation(recommendation["recommendation_id"], db)
        assert recommendation_detail["status"] == "VERIFIED"
        assert recommendation_detail["actions"][0]["executed_value"] is not None
        assert recommendation_detail["evaluation"]["is_effective"] is True
        assert list_recommendations(db)[0]["id"] == recommendation["recommendation_id"]
        assert list_evaluations(db)[0]["recommendation_id"] == recommendation["recommendation_id"]
        dashboard = dashboard_snapshot(db)
        assert dashboard["recommendation"]["id"] == recommendation["recommendation_id"]
        assert dashboard["recommendation"]["status"] == "VERIFIED"
        assert dashboard["diagnosis"]["point_code"] == "P1"
        assert dashboard["diagnosis"]["factors"]

        next_model = train_baseline_model(
            ModelTrainingRequest(
                model_code="DOI-BASELINE",
                version="2.0",
                target_metric="doi",
                min_samples=5,
                ridge_lambda=0.01,
            ),
            db,
        )
        assert trained.status == "RETIRED"
        assert next_model.status == "ACTIVE"
        reactivated = change_model_status(
            trained.id,
            ModelStatusUpdate(status="ACTIVE"),
            db,
        )
        assert reactivated.status == "ACTIVE"
        assert next_model.status == "RETIRED"
        with pytest.raises(HTTPException, match="只有生效模型可以执行在线预测"):
            predict_from_snapshot(
                next_model.id,
                ModelPredictionRequest(
                    production_run_id=runs[-1][0].id,
                    measurement_point_id=point.id,
                ),
                db,
            )
