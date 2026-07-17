"""Smoke tests for STEP→GLB conversion service and API wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import stp_convert


client = TestClient(app)


def test_cascadio_available_is_bool() -> None:
    assert isinstance(stp_convert.cascadio_available(), bool)


def test_step_to_glb_missing_input(tmp_path: Path) -> None:
    missing = tmp_path / "missing.stp"
    out = tmp_path / "out.glb"
    with pytest.raises(stp_convert.StpConvertError, match="不存在"):
        stp_convert.step_to_glb(missing, out)


def test_convert_stp_status_endpoint() -> None:
    response = client.get("/api/v1/quality/body-map/convert-stp/status")
    assert response.status_code == 200
    payload = response.json()
    assert "available" in payload
    assert payload["max_upload_mb"] == 250


def test_convert_stp_rejects_non_step() -> None:
    if not stp_convert.cascadio_available():
        # Endpoint short-circuits with 503 before format check when CAD stack missing.
        response = client.post(
            "/api/v1/quality/body-map/convert-stp",
            files={"file": ("model.glb", b"not-a-step", "model/gltf-binary")},
        )
        assert response.status_code == 503
        return

    response = client.post(
        "/api/v1/quality/body-map/convert-stp",
        files={"file": ("model.glb", b"not-a-step", "model/gltf-binary")},
    )
    assert response.status_code == 400
    assert "stp" in response.json()["detail"].lower()


def test_convert_stp_rejects_empty_when_ready() -> None:
    if not stp_convert.cascadio_available():
        pytest.skip("cascadio not installed")
    response = client.post(
        "/api/v1/quality/body-map/convert-stp",
        files={"file": ("empty.stp", b"", "application/step")},
    )
    assert response.status_code == 400
