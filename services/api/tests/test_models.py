from pathlib import Path
import re

from app.db.base import Base
from app.models import domain  # noqa: F401


SCHEMA_SQL = Path(__file__).resolve().parents[3] / "docs" / "sql" / "pq_ai_mysql_schema.sql"
SEVEN_TABLE_SQL = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sql"
    / "pq_ai_training_remote_7_tables.sql"
)


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
        "process_route",
        "process_route_step",
        "process_route_applicability",
        "parameter_constraint_source",
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
        "contribution_validation",
        "trajectory_segment_geometry",
        "production_device_execution",
        "path_segment_execution",
        "material_batch",
        "file_import_profile",
        "file_import_job",
        "supplier_mat_submission",
        "supplier_mat_issue",
        "mat_char_definition",
        "material_test_method",
        "material_specification",
        "mat_char_applicability",
        "material_batch_test_result",
        "production_run",
        "production_stage_run",
        "actual_parameter",
        "measurement_probe",
        "measurement_msa_study",
        "quality_measurement",
        "quality_metric_definition",
        "quality_metric_value",
        "quality_standard",
        "point_feature_snapshot",
        "dataset_snapshot",
        "dataset_split_member",
        "model_version",
        "model_validation_fold",
        "model_artifact",
        "model_acceptance_decision",
        "model_acceptance_policy",
        "model_applicability_scope",
        "model_ood_policy",
        "prediction_result",
        "diagnosis_result",
        "recommendation",
        "recommendation_action",
        "controlled_trial",
        "program_rollback_execution",
        "closed_loop_evaluation",
        "quality_issue_task",
        "quality_issue_evidence",
        "quality_issue_comment",
        "eng_knowledge_entry",
        "model_explanation",
        "training_data_upload",
        "training_wide_sample",
        "remote_station_connection",
        "remote_parameter_snapshot",
        "remote_program_release",
        "remote_release_event",
        "remote_station_reconciliation",
        "app_user",
        "role_code",
        "permission",
        "user_role",
        "role_permission",
        "api_key",
        "user_session",
        "audit_log",
    }
    assert required_tables <= set(Base.metadata.tables)


def test_program_versions_support_multiple_models_and_colors() -> None:
    assert "program_vehicle_model" in Base.metadata.tables
    assert "program_color" in Base.metadata.tables
    assert "vehicle_model_id" not in Base.metadata.tables["spray_program"].columns
    assert "color_id" not in Base.metadata.tables["spray_program"].columns


def test_total_ddl_matches_orm_tables_and_columns_without_physical_foreign_keys() -> None:
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    table_blocks = re.findall(
        r"CREATE TABLE `([^`]+)` \((.*?)\n\) ENGINE=",
        sql,
        flags=re.DOTALL,
    )
    ddl_columns = {
        table_name: set(re.findall(r"^\s{2}`([^`]+)`\s", block, flags=re.MULTILINE))
        for table_name, block in table_blocks
    }
    orm_columns = {
        table.name: {column.name for column in table.columns}
        for table in Base.metadata.sorted_tables
    }

    assert ddl_columns.keys() == orm_columns.keys()
    for table_name, expected_columns in orm_columns.items():
        assert ddl_columns[table_name] == expected_columns, table_name
    assert "FOREIGN KEY" not in sql.upper()


def test_training_remote_approval_sql_contains_exactly_seven_governed_tables() -> None:
    expected_tables = {
        "training_data_upload",
        "training_wide_sample",
        "remote_station_connection",
        "remote_parameter_snapshot",
        "remote_program_release",
        "remote_release_event",
        "remote_station_reconciliation",
    }
    sql = SEVEN_TABLE_SQL.read_text(encoding="utf-8")
    table_blocks = re.findall(
        r"CREATE TABLE `([^`]+)` \((.*?)\n\) ENGINE=",
        sql,
        flags=re.DOTALL,
    )

    assert {table_name for table_name, _ in table_blocks} == expected_tables
    assert len(table_blocks) == 7
    for table_name, block in table_blocks:
        ddl_columns = set(re.findall(r"^\s{2}`([^`]+)`\s", block, flags=re.MULTILINE))
        orm_columns = {column.name for column in Base.metadata.tables[table_name].columns}
        assert ddl_columns == orm_columns, table_name
    upper_sql = sql.upper()
    assert "FOREIGN KEY" not in upper_sql
    assert "CREATE DATABASE" not in upper_sql
    assert "DROP " not in upper_sql
    assert "DELETE " not in upper_sql
    assert "SET " not in upper_sql
    assert "ALTER TABLE" not in upper_sql
