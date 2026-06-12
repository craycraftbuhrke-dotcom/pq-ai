from app.api.routes.ai import approve_recommendation, diagnose, predict
from app.api.routes.dashboard import get_dashboard
from app.api.routes.health import health
from app.schemas.common import DiagnosisRequest, PredictionRequest, RecommendationApproval


def test_health_endpoint() -> None:
    assert health()["status"] == "ok"


def test_dashboard_contract() -> None:
    payload = get_dashboard()
    assert len(payload["stages"]) == 5
    assert payload["stages"][0]["station"] == "P1F1A1"
    assert payload["recommendation"]["constraints_checked"] is True


def test_prediction_diagnosis_and_approval_flow() -> None:
    prediction = predict(
        PredictionRequest(
            production_run_no="RUN-001",
            measurement_point_code="P-ROOF-03",
            target_metrics=["doi"],
        )
    )
    assert prediction["predictions"]["doi"]["value"] > 0

    diagnosis = diagnose(
        DiagnosisRequest(
            production_run_no="RUN-001",
            measurement_point_code="P-ROOF-03",
            observed_metric="doi",
            observed_value=78.2,
        )
    )
    assert diagnosis["confidence"] > 0.8

    approval = approve_recommendation(
        "rec-20260609-003",
        RecommendationApproval(approved=True, approved_by="陈工", comment="受控试验批准"),
    )
    assert approval["status"] == "APPROVED"
