from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.modeling import (
    add_acceptance_policy,
    build_dataset,
    change_acceptance_policy_status,
    change_model_status,
    decide_model_acceptance,
    diagnose_from_prediction,
    check_model_governance,
    get_model_drift,
    list_applicability_scopes,
    list_feature_snapshots,
    list_model_artifacts,
    list_ood_policies,
    list_validation_folds,
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
    DatasetBuildRequest,
    ModelAcceptanceRequest,
    ModelAcceptancePolicyCreate,
    ModelAcceptancePolicyStatusUpdate,
    ModelGovernanceCheckRequest,
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
                reliability_status="VERIFIED",
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

        dataset = build_dataset(
            DatasetBuildRequest(
                dataset_code="DOI-DATASET",
                version="1.0",
                target_metric="doi",
                holdout_ratio=0.25,
            ),
            db,
        )
        assert dataset.train_group_count == 6
        assert dataset.validation_group_count == 2
        assert dataset.leakage_check["passed"] is True
        assert dataset.leakage_check["group_overlap_count"] == 0
        trained = train_baseline_model(
            ModelTrainingRequest(
                model_code="DOI-BASELINE",
                version="1.0",
                target_metric="doi",
                dataset_snapshot_id=dataset.id,
                min_samples=5,
                ridge_lambda=0.01,
            ),
            db,
        )
        assert trained.model_type == "RIDGE_REGRESSION_BASELINE"
        assert trained.status == "DRAFT"
        assert trained.training_sample_count == 6
        assert trained.evaluation_metrics["training_r2"] > 0.99
        assert "validation_rmse" in trained.evaluation_metrics
        multi_axis = trained.evaluation_metrics["multi_axis_validation"]
        assert multi_axis["strategy"] == "TEMPORAL_HOLDOUT_PLUS_LEAVE_AXIS_OUT"
        assert multi_axis["axes"]["TIME_HOLDOUT"]["status"] == "EVALUATED"
        assert multi_axis["axes"]["PRODUCTION_GROUP_LOO"]["status"] == "EVALUATED"
        assert multi_axis["axes"]["FACTORY"]["status"] == "INSUFFICIENT_AXIS_DIVERSITY"
        assert trained.model_payload["minimums"]
        assert trained.model_payload["maximums"]
        validation_folds = list_validation_folds(trained.id, db)
        assert {fold.validation_axis for fold in validation_folds} >= {
            "TIME_HOLDOUT",
            "FACTORY",
            "VEHICLE_MODEL",
            "COLOR",
            "PRODUCTION_GROUP_LOO",
        }
        assert any(
            fold.validation_axis == "PRODUCTION_GROUP_LOO" and fold.status == "EVALUATED"
            for fold in validation_folds
        )
        artifacts = list_model_artifacts(trained.id, db)
        assert artifacts[0].status == "REGISTERED"
        assert artifacts[0].artifact_uri == trained.artifact_uri
        assert len(artifacts[0].payload_hash) == 64
        scopes = list_applicability_scopes(db)
        policies = list_ood_policies(db)
        assert len(scopes) == 1
        assert scopes[0]["status"] == "PENDING"
        assert policies[0].status == "PENDING"
        with pytest.raises(HTTPException, match="必须先通过独立验证和人工验收"):
            change_model_status(trained.id, ModelStatusUpdate(status="ACTIVE"), db)
        with pytest.raises(HTTPException, match="模型未满足验收检查"):
            decide_model_acceptance(
                trained.id,
                ModelAcceptanceRequest(
                    decision="ACCEPTED",
                    decided_by="模型验收人",
                ),
                db,
            )
        factory_policy = add_acceptance_policy(
            ModelAcceptancePolicyCreate(
                policy_code="F1-DOI-ACCEPTANCE",
                version="1.0",
                factory_id=factory.id,
                target_metric="doi",
                max_validation_rmse=0.5,
                min_validation_r2=0.9,
                min_train_groups=5,
                min_validation_groups=2,
                source_uri="factory://F1/model-acceptance/doi/1.0",
            ),
            db,
        )
        assert factory_policy.status == "DRAFT"
        factory_policy = change_acceptance_policy_status(
            factory_policy.id,
            ModelAcceptancePolicyStatusUpdate(
                status="ACTIVE",
                approved_by="工厂模型治理委员会",
            ),
            db,
        )
        assert factory_policy.status == "ACTIVE"
        acceptance = decide_model_acceptance(
            trained.id,
            ModelAcceptanceRequest(
                decision="ACCEPTED",
                decided_by="模型验收人",
                comment="独立验证指标符合本次受控试验目标",
            ),
            db,
        )
        assert acceptance.decision == "ACCEPTED"
        assert acceptance.checks["has_configured_applicability_scope"] is True
        assert acceptance.checks["has_configured_ood_policy"] is True
        assert acceptance.checks["has_multi_axis_validation_report"] is True
        assert acceptance.checks["has_evaluated_validation_axis"] is True
        assert acceptance.checks["has_registered_model_artifact"] is True
        assert acceptance.checks["model_artifact_hash_matches"] is True
        assert acceptance.checks["factory_acceptance_policies_present"] is True
        assert acceptance.checks["factory_acceptance_thresholds_passed"] is True
        assert acceptance.criteria["model_artifact"]["hash_matches"] is True
        assert acceptance.criteria["multi_axis_validation"]["evaluated_axis_count"] >= 2
        assert acceptance.criteria["factory_acceptance_policies"][0]["policy_code"] == (
            "F1-DOI-ACCEPTANCE:1.0"
        )
        assert list_applicability_scopes(db)[0]["status"] == "ACTIVE"
        assert list_ood_policies(db)[0].status == "ACTIVE"
        trained = change_model_status(trained.id, ModelStatusUpdate(status="ACTIVE"), db)
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
        assert prediction["applicability_status"] == "IN_SCOPE"
        assert prediction["ood_status"] == "IN_DISTRIBUTION"
        assert prediction["governance_evidence"]["scope_id"] == scopes[0]["id"]
        governance = check_model_governance(
            trained.id,
            ModelGovernanceCheckRequest(
                production_run_id=runs[-1][0].id,
                measurement_point_id=point.id,
            ),
            db,
        )
        assert governance["allowed"] is True

        out_of_scope_factory = Factory(code="F2", name="范围外工厂")
        db.add(out_of_scope_factory)
        db.flush()
        out_of_scope_run = ProductionRun(
            run_no="RUN-OUT-OF-SCOPE",
            factory_id=out_of_scope_factory.id,
            vehicle_model_id=model.id,
            color_id=color.id,
            started_at=now + timedelta(hours=2),
        )
        extreme_run = ProductionRun(
            run_no="RUN-OOD",
            factory_id=factory.id,
            vehicle_model_id=model.id,
            color_id=color.id,
            started_at=now + timedelta(hours=3),
        )
        incomplete_run = ProductionRun(
            run_no="RUN-INCOMPLETE",
            factory_id=factory.id,
            vehicle_model_id=model.id,
            color_id=color.id,
            started_at=now + timedelta(hours=4),
        )
        db.add_all([out_of_scope_run, extreme_run, incomplete_run])
        db.flush()
        db.add_all(
            [
                PointFeatureSnapshot(
                    production_run_id=out_of_scope_run.id,
                    measurement_point_id=point.id,
                    feature_set_version=CURRENT_FEATURE_SET_VERSION,
                    feature_values={
                        "clearcoat_2.spray_flow": 7.0,
                        "clearcoat_2.outer_air": 4.0,
                    },
                    completeness_score=1.0,
                    generated_at=now,
                ),
                PointFeatureSnapshot(
                    production_run_id=extreme_run.id,
                    measurement_point_id=point.id,
                    feature_set_version=CURRENT_FEATURE_SET_VERSION,
                    feature_values={
                        "clearcoat_2.spray_flow": 100.0,
                        "clearcoat_2.outer_air": 100.0,
                    },
                    completeness_score=1.0,
                    generated_at=now,
                ),
                PointFeatureSnapshot(
                    production_run_id=incomplete_run.id,
                    measurement_point_id=point.id,
                    feature_set_version=CURRENT_FEATURE_SET_VERSION,
                    feature_values={"clearcoat_2.spray_flow": 5.0},
                    completeness_score=0.5,
                    generated_at=now,
                ),
            ]
        )
        db.commit()
        out_of_scope_check = check_model_governance(
            trained.id,
            ModelGovernanceCheckRequest(
                production_run_id=out_of_scope_run.id,
                measurement_point_id=point.id,
            ),
            db,
        )
        assert out_of_scope_check["applicability_status"] == "OUT_OF_SCOPE"
        assert out_of_scope_check["allowed"] is False
        with pytest.raises(HTTPException, match="不在模型已批准适用范围"):
            predict_from_snapshot(
                trained.id,
                ModelPredictionRequest(
                    production_run_id=out_of_scope_run.id,
                    measurement_point_id=point.id,
                ),
                db,
            )
        ood_check = check_model_governance(
            trained.id,
            ModelGovernanceCheckRequest(
                production_run_id=extreme_run.id,
                measurement_point_id=point.id,
            ),
            db,
        )
        assert ood_check["ood_status"] == "OUT_OF_DISTRIBUTION"
        assert ood_check["evidence"]["outlier_features"]
        with pytest.raises(HTTPException, match="输入分布外"):
            recommend_from_snapshot(
                trained.id,
                ModelRecommendationRequest(
                    production_run_id=extreme_run.id,
                    measurement_point_id=point.id,
                    target_min=100.0,
                ),
                db,
            )
        incomplete_check = check_model_governance(
            trained.id,
            ModelGovernanceCheckRequest(
                production_run_id=incomplete_run.id,
                measurement_point_id=point.id,
            ),
            db,
        )
        assert incomplete_check["ood_status"] == "OUT_OF_DISTRIBUTION"
        assert incomplete_check["evidence"]["missing_features"] == ["clearcoat_2.outer_air"]
        with pytest.raises(HTTPException, match="完整率 50.0%"):
            predict_from_snapshot(
                trained.id,
                ModelPredictionRequest(
                    production_run_id=incomplete_run.id,
                    measurement_point_id=point.id,
                ),
                db,
            )
        drift = get_model_drift(trained.id, db)
        assert drift["monitored_snapshot_count"] == 11
        assert drift["prediction_count"] == 1
        assert drift["labeled_prediction_count"] == 1
        assert drift["baseline_source"] == "VALIDATION"
        assert drift["baseline_rmse"] == trained.evaluation_metrics["validation_rmse"]
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
            reliability_status="VERIFIED",
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
            reliability_status="VERIFIED",
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
                dataset_snapshot_id=dataset.id,
                min_samples=5,
                ridge_lambda=0.01,
            ),
            db,
        )
        assert trained.status == "ACTIVE"
        assert next_model.status == "DRAFT"
        decide_model_acceptance(
            next_model.id,
            ModelAcceptanceRequest(
                decision="ACCEPTED",
                decided_by="模型验收人",
            ),
            db,
        )
        next_model = change_model_status(
            next_model.id,
            ModelStatusUpdate(status="ACTIVE"),
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
        rejected = decide_model_acceptance(
            trained.id,
            ModelAcceptanceRequest(
                decision="REJECTED",
                decided_by="模型验收人",
                comment="上线后复核发现不再适用",
            ),
            db,
        )
        assert rejected.decision == "REJECTED"
        assert trained.status == "RETIRED"
        with pytest.raises(HTTPException, match="只有生效模型可以执行在线预测"):
            predict_from_snapshot(
                next_model.id,
                ModelPredictionRequest(
                    production_run_id=runs[-1][0].id,
                    measurement_point_id=point.id,
                ),
                db,
            )
