from app.services.dashboard_snapshot import dashboard_snapshot


def test_dashboard_empty_without_database_has_no_example_business_data() -> None:
    snapshot = dashboard_snapshot()
    assert snapshot["context"]["factory"] == ""
    assert snapshot["risk_points"] == []
    assert snapshot["recommendation"]["id"] == ""
    assert len(snapshot["stages"]) == 5


def test_dashboard_empty_snapshot_includes_cross_domain_kpi_blocks() -> None:
    snapshot = dashboard_snapshot()
    assert snapshot["material_batches"] == {"total": 0, "verified": 0, "fail_spec": 0}
    assert snapshot["calibration_alerts"] == {"expiring_30d": 0, "expired": 0}
    assert snapshot["engineering_open_tasks"] == 0
    assert snapshot["ai_models"] == {"approved": 0, "total": 0, "latest_metric": None}
    assert snapshot["recent_predictions"] == {"count_24h": 0, "top_risk_point": None}
