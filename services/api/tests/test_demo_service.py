from app.services.demo import dashboard_snapshot, prediction_result


def test_dashboard_has_five_process_stages() -> None:
    snapshot = dashboard_snapshot()
    assert len(snapshot["stages"]) == 5
    assert snapshot["stages"][0]["code"] == "MIDCOAT_EXT"
    assert snapshot["stages"][-1]["code"] == "CLEARCOAT_2"


def test_prediction_returns_requested_metrics() -> None:
    result = prediction_result(
        {
            "production_run_no": "RUN-001",
            "measurement_point_code": "P-ROOF-03",
            "target_metrics": ["doi"],
        }
    )
    assert set(result["predictions"]) == {"doi"}
    assert result["confidence"] > 0.8
