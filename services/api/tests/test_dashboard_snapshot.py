from app.services.dashboard_snapshot import dashboard_snapshot


def test_dashboard_empty_without_database_has_no_example_business_data() -> None:
    snapshot = dashboard_snapshot()
    assert snapshot["context"]["factory"] == ""
    assert snapshot["risk_points"] == []
    assert snapshot["recommendation"]["id"] == ""
    assert len(snapshot["stages"]) == 5
