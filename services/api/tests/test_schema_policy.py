from sqlalchemy.exc import OperationalError, ProgrammingError

from app.db.schema_policy import missing_column_name, missing_table_name


def test_missing_table_name_extracts_mysql_table() -> None:
    exc = ProgrammingError(
        "select * from model_ood_policy",
        {},
        Exception(1146, "Table 'pq_ai.model_ood_policy' doesn't exist"),
    )

    assert missing_table_name(exc) == "model_ood_policy"


def test_missing_table_name_ignores_other_programming_errors() -> None:
    exc = ProgrammingError("select broken", {}, Exception(1054, "Unknown column"))

    assert missing_table_name(exc) is None


def test_missing_column_name_extracts_mysql_column() -> None:
    exc = OperationalError(
        "select prediction_result.applicability_status",
        {},
        Exception(
            1054,
            "Unknown column 'prediction_result.applicability_status' in 'field list'",
        ),
    )

    assert missing_column_name(exc) == "prediction_result.applicability_status"


def test_missing_column_name_ignores_other_operational_errors() -> None:
    exc = OperationalError("select 1", {}, Exception(2006, "MySQL server has gone away"))

    assert missing_column_name(exc) is None
