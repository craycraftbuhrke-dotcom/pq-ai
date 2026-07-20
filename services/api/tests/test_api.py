from fastapi import HTTPException
import pytest
from sqlalchemy.exc import OperationalError

from app.api.routes.ai import diagnose, predict
from app.api.routes.dashboard import get_dashboard
from app.api.routes.health import liveness, readiness
from app.schemas.common import DiagnosisRequest, PredictionRequest


def test_health_endpoint() -> None:
    assert liveness() == {
        "status": "ok",
        "service": "pq-ai-api",
        "check": "liveness",
    }


def test_readiness_checks_database() -> None:
    class ReadySession:
        def execute(self, statement):
            assert str(statement) == "SELECT 1"

    assert readiness(ReadySession())["check"] == "readiness"


def test_readiness_returns_503_when_database_is_unavailable() -> None:
    class UnavailableSession:
        def execute(self, statement):
            raise OperationalError("SELECT 1", {}, RuntimeError("offline"))

    with pytest.raises(HTTPException) as error:
        readiness(UnavailableSession())
    assert error.value.status_code == 503


def test_dashboard_contract() -> None:
    payload = get_dashboard()
    assert len(payload["stages"]) == 5
    assert payload["stages"][0]["station"] == ""
    assert payload["recommendation"]["constraints_checked"] is False


def test_legacy_prediction_diagnosis_and_approval_routes_are_retired() -> None:
    with pytest.raises(HTTPException) as prediction_error:
        predict(
            PredictionRequest(
                production_run_no="TEST-RUN",
                measurement_point_code="TEST-POINT",
                target_metrics=["doi"],
            )
        )
    assert prediction_error.value.status_code == 410

    with pytest.raises(HTTPException) as diagnosis_error:
        diagnose(
            DiagnosisRequest(
                production_run_no="TEST-RUN",
                measurement_point_code="TEST-POINT",
                observed_metric="doi",
                observed_value=78.2,
            )
        )
    assert diagnosis_error.value.status_code == 410
