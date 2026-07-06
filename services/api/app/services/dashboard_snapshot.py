from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.domain import (
    DiagnosisResult,
    MeasurementPoint,
    PredictionResult,
    ProductionRun,
    QualityMeasurement,
    Recommendation,
    RecommendationAction,
)


PROCESS_STAGE_SHELL = [
    ("MIDCOAT_EXT", "中涂外喷"),
    ("BASECOAT_1", "色漆一站"),
    ("BASECOAT_2", "色漆二站"),
    ("CLEARCOAT_1", "清漆一站"),
    ("CLEARCOAT_2", "清漆二站"),
]


def dashboard_snapshot(db: Session | None = None) -> dict:
    snapshot = {
        "context": {
            "factory": "",
            "vehicle_model": "",
            "color": "",
            "shift": "",
            "refreshed_at": datetime.now(UTC).isoformat(),
        },
        "health_score": 0.0,
        "quality_pass_rate": 0.0,
        "active_runs": 0,
        "open_risks": 0,
        "pending_recommendations": 0,
        "stages": [
            {
                "code": code,
                "name": name,
                "station": "",
                "health": 0,
                "status": "healthy",
                "flow": 0,
                "rpm": 0,
            }
            for code, name in PROCESS_STAGE_SHELL
        ],
        "risk_points": [],
        "diagnosis": {
            "point_code": "",
            "summary": "暂无诊断结果",
            "confidence": 0.0,
            "factors": [],
        },
        "recommendation": {
            "id": "",
            "recommendation_no": "",
            "status": "NONE",
            "point_code": "",
            "target_metric": "",
            "current_prediction": 0.0,
            "expected_prediction": 0.0,
            "predicted_improvement": 0.0,
            "confidence": 0.0,
            "constraints_checked": False,
            "actions": [],
        },
    }
    if not db:
        return snapshot

    try:
        total_quality = int(db.scalar(select(func.count()).select_from(QualityMeasurement)) or 0)
        valid_quality = int(
            db.scalar(
                select(func.count())
                .select_from(QualityMeasurement)
                .where(QualityMeasurement.is_valid.is_(True))
            )
            or 0
        )
        snapshot["quality_pass_rate"] = (
            round(valid_quality / total_quality * 100, 2) if total_quality else 0.0
        )
        snapshot["active_runs"] = int(
            db.scalar(select(func.count()).select_from(ProductionRun)) or 0
        )
        snapshot["pending_recommendations"] = int(
            db.scalar(
                select(func.count())
                .select_from(Recommendation)
                .where(Recommendation.status == "PENDING")
            )
            or 0
        )
        diagnosis = db.scalar(
            select(DiagnosisResult).order_by(DiagnosisResult.created_at.desc())
        )
        if diagnosis:
            point = db.get(MeasurementPoint, diagnosis.measurement_point_id)
            raw_factors = diagnosis.factor_contributions
            total_impact = sum(abs(float(factor.get("impact", 0.0))) for factor in raw_factors)
            snapshot["diagnosis"] = {
                "point_code": point.code if point else diagnosis.measurement_point_id,
                "summary": diagnosis.summary,
                "confidence": diagnosis.confidence,
                "factors": [
                    {
                        "name": factor.get("feature", "unknown_feature"),
                        "impact": (
                            abs(float(factor.get("impact", 0.0))) / total_impact
                            if total_impact
                            else 0.0
                        ),
                        "direction": factor.get("direction", "positive"),
                    }
                    for factor in raw_factors[:3]
                ],
            }
        recommendation = db.scalar(
            select(Recommendation).order_by(Recommendation.created_at.desc())
        )
        if recommendation:
            point = db.get(MeasurementPoint, recommendation.measurement_point_id)
            prediction = db.scalar(
                select(PredictionResult)
                .where(
                    PredictionResult.production_run_id == recommendation.production_run_id,
                    PredictionResult.measurement_point_id == recommendation.measurement_point_id,
                    PredictionResult.metric_code == recommendation.target_metric,
                )
                .order_by(PredictionResult.predicted_at.desc())
            )
            actions = list(
                db.scalars(
                    select(RecommendationAction).where(
                        RecommendationAction.recommendation_id == recommendation.id
                    )
                )
            )
            current_prediction = prediction.predicted_value if prediction else 0.0
            snapshot["recommendation"] = {
                "id": recommendation.id,
                "recommendation_no": recommendation.recommendation_no,
                "status": recommendation.status,
                "point_code": point.code if point else recommendation.measurement_point_id,
                "target_metric": recommendation.target_metric,
                "current_prediction": current_prediction,
                "expected_prediction": current_prediction + recommendation.predicted_improvement,
                "predicted_improvement": recommendation.predicted_improvement,
                "confidence": recommendation.confidence,
                "constraints_checked": recommendation.constraints_checked,
                "actions": [
                    {
                        "stage": action.process_stage,
                        "brush_no": action.brush_no or "POINT-AGG",
                        "parameter": action.parameter_name,
                        "current": action.current_value,
                        "recommended": action.recommended_value,
                        "unit": action.unit,
                        "constraint_source": action.constraint_source_code,
                    }
                    for action in actions
                ],
            }
    except SQLAlchemyError:
        db.rollback()
    return snapshot
