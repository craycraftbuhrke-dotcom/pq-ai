from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.domain import (
    DiagnosisResult,
    MeasurementPoint,
    PredictionResult,
    Recommendation,
    RecommendationAction,
)


def dashboard_snapshot(db: Session | None = None) -> dict:
    snapshot = {
        "context": {
            "factory": "M9 总装涂装工厂",
            "vehicle_model": "MX11",
            "color": "珍珠白",
            "shift": "白班",
            "refreshed_at": datetime.now(UTC).isoformat(),
        },
        "health_score": 92.4,
        "quality_pass_rate": 98.7,
        "active_runs": 126,
        "open_risks": 7,
        "pending_recommendations": 3,
        "stages": [
            {
                "code": "MIDCOAT_EXT",
                "name": "中涂外喷",
                "station": "P1F1A1",
                "health": 96,
                "status": "healthy",
                "flow": 342,
                "rpm": 45000,
            },
            {
                "code": "BASECOAT_1",
                "name": "色漆一站",
                "station": "P1B1A1",
                "health": 93,
                "status": "healthy",
                "flow": 286,
                "rpm": 48000,
            },
            {
                "code": "BASECOAT_2",
                "name": "色漆二站",
                "station": "P1B1A2",
                "health": 86,
                "status": "warning",
                "flow": 212,
                "rpm": 50000,
            },
            {
                "code": "CLEARCOAT_1",
                "name": "清漆一站",
                "station": "P1C1A1",
                "health": 91,
                "status": "healthy",
                "flow": 302,
                "rpm": 47000,
            },
            {
                "code": "CLEARCOAT_2",
                "name": "清漆二站",
                "station": "P1C1A2",
                "health": 78,
                "status": "risk",
                "flow": 315,
                "rpm": 46000,
            },
        ],
        "risk_points": [
            {
                "point_code": "P-ROOF-03",
                "point_name": "车顶中部 03",
                "part": "车顶",
                "risk": 86,
                "metric": "DOI",
                "prediction": 78.2,
                "standard": "≥ 82",
            },
            {
                "point_code": "P-HOOD-06",
                "point_name": "发动机罩 06",
                "part": "发动机罩",
                "risk": 72,
                "metric": "总膜厚",
                "prediction": 116.8,
                "standard": "120–145 μm",
            },
            {
                "point_code": "P-LD-02",
                "point_name": "左前门 02",
                "part": "左前门",
                "risk": 39,
                "metric": "dE45",
                "prediction": 0.71,
                "standard": "≤ 0.80",
            },
        ],
        "diagnosis": {
            "point_code": "P-ROOF-03",
            "summary": "清漆二站成型空气偏高，且材料粘度接近上限，是 DOI 下降的主要相关因素。",
            "confidence": 0.87,
            "factors": [
                {"name": "清漆二站外成型空气", "impact": 0.34, "direction": "negative"},
                {"name": "清漆粘度", "impact": 0.26, "direction": "negative"},
                {"name": "清漆二站喷涂流量", "impact": 0.18, "direction": "positive"},
            ],
        },
        "recommendation": demo_recommendation(),
    }
    if db:
        try:
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
                    "expected_prediction": current_prediction
                    + recommendation.predicted_improvement,
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
                snapshot["pending_recommendations"] = int(
                    db.scalar(
                        select(func.count())
                        .select_from(Recommendation)
                        .where(Recommendation.status == "PENDING")
                    )
                    or 0
                )
        except SQLAlchemyError:
            db.rollback()
    return snapshot


def demo_recommendation() -> dict:
    return {
        "id": "rec-20260609-003",
        "recommendation_no": "REC-20260609-003",
        "status": "PENDING",
        "point_code": "P-ROOF-03",
        "target_metric": "DOI",
        "current_prediction": 78.2,
        "expected_prediction": 83.6,
        "predicted_improvement": 5.4,
        "confidence": 0.87,
        "constraints_checked": True,
        "actions": [
            {
                "stage": "清漆二站",
                "brush_no": "B-042",
                "parameter": "外成型空气流量",
                "current": 410,
                "recommended": 385,
                "unit": "Nl/min",
                "constraint_source": "DEMO-CLEARCOAT-OUTER-AIR",
            },
            {
                "stage": "清漆二站",
                "brush_no": "B-042",
                "parameter": "喷涂流量",
                "current": 315,
                "recommended": 326,
                "unit": "ml/min",
                "constraint_source": "DEMO-CLEARCOAT-SPRAY-FLOW",
            },
        ],
    }


def prediction_result(payload: dict) -> dict:
    predictions = {
        "thickness_total": {"value": 128.6, "lower": 124.2, "upper": 133.0, "unit": "μm"},
        "doi": {"value": 81.8, "lower": 78.9, "upper": 84.7, "unit": ""},
    }
    return {
        "model_version": "pq-quality-tabular-0.1.0",
        "production_run_no": payload["production_run_no"],
        "measurement_point_code": payload["measurement_point_code"],
        "predictions": {
            metric: predictions.get(metric, {"value": 0, "lower": 0, "upper": 0, "unit": ""})
            for metric in payload["target_metrics"]
        },
        "confidence": 0.84,
        "is_demo_model": True,
    }
