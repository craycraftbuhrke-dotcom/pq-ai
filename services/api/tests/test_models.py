from app.db.base import Base
from app.models import domain  # noqa: F401


def test_core_closed_loop_tables_are_registered() -> None:
    required_tables = {
        "factory",
        "factory_vehicle_model",
        "vehicle_model",
        "vehicle_model_color",
        "color",
        "part",
        "measurement_group",
        "measurement_point",
        "spray_program",
        "spray_program_version",
        "program_vehicle_model",
        "program_color",
        "brush",
        "brush_parameter",
        "brush_point_contribution",
        "durr_robot",
        "durr_application_controller",
        "durr_rotary_atomizer",
        "program_device_configuration",
        "trajectory_program",
        "trajectory_path_segment",
        "point_contribution_version",
        "point_contribution_entry",
        "production_device_execution",
        "path_segment_execution",
        "material_batch",
        "material_characteristic_definition",
        "material_test_method",
        "material_specification",
        "material_characteristic_applicability",
        "material_batch_test_result",
        "production_run",
        "production_stage_run",
        "actual_parameter",
        "quality_measurement",
        "quality_metric_definition",
        "quality_metric_value",
        "quality_standard",
        "point_feature_snapshot",
        "model_version",
        "prediction_result",
        "diagnosis_result",
        "recommendation",
        "recommendation_action",
        "closed_loop_evaluation",
        "app_user",
        "role",
        "permission",
        "user_role",
        "role_permission",
        "api_key",
        "audit_log",
    }
    assert required_tables <= set(Base.metadata.tables)


def test_program_versions_support_multiple_models_and_colors() -> None:
    assert "program_vehicle_model" in Base.metadata.tables
    assert "program_color" in Base.metadata.tables
    assert "vehicle_model_id" not in Base.metadata.tables["spray_program"].columns
    assert "color_id" not in Base.metadata.tables["spray_program"].columns
