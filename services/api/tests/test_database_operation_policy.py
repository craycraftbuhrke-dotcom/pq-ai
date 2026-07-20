import pytest

from app.db.session import forbidden_mysql_runtime_operation


@pytest.mark.parametrize(
    ("statement", "operation"),
    [
        ("DELETE FROM quality_measurement", "delete"),
        ("DELETE/**/FROM quality_measurement", "delete"),
        ("  CREATE TABLE forbidden (id INT)", "create"),
        ("/* ticket bypass */ DROP TABLE quality_measurement", "drop"),
        ("-- no bypass\nSET sql_mode = ''", "set"),
        ("# no bypass\r\nALTER TABLE factory ADD COLUMN x INT", "alter"),
        ("TRUNCATE TABLE audit_log", "truncate"),
        ("REPLACE INTO factory VALUES (1)", "replace"),
        ("RENAME TABLE factory TO factory_old", "rename"),
        ("/*! DELETE FROM quality_measurement */", "delete"),
        ("/*!50700 DELETE FROM quality_measurement */", "delete"),
        ("/*M! DELETE FROM quality_measurement */", "delete"),
        ("WITH doomed AS (SELECT id FROM quality_measurement) DELETE FROM quality_measurement", "delete"),
        ("SELECT 1; DELETE FROM quality_measurement", "delete"),
        ("SELECT 1--1; DELETE FROM quality_measurement", "delete"),
        ("CALL destructive_procedure()", "call"),
        ("PREPARE stmt FROM 'DELETE FROM quality_measurement'", "delete"),
        ("PREPARE stmt FROM 'SELECT 1; DROP TABLE factory'", "drop"),
        ("PREPARE stmt FROM @dynamic_sql", "prepare"),
        ("PREPARE stmt FROM CONCAT('DELETE ', 'FROM factory')", "prepare"),
        (r"PREPARE stmt FROM 'SELECT \\n 1'", "prepare"),
    ],
)
def test_forbidden_mysql_runtime_operations(statement: str, operation: str) -> None:
    assert forbidden_mysql_runtime_operation(statement) == operation


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT 1",
        "INSERT INTO factory (factory_code) VALUES ('F1')",
        "UPDATE factory SET factory_name = '一厂' WHERE factory_code = 'F1'",
        "/* read */ SELECT factory_code FROM factory",
        "SELECT '/*! DELETE FROM factory */'",
        "WITH rows_to_update AS (SELECT id FROM factory) UPDATE factory SET factory_name = '一厂'",
        "WITH source_rows AS (SELECT id FROM factory) INSERT INTO audit_log (id) SELECT id FROM source_rows",
        "SELECT 1--1",
        "PREPARE stmt FROM 'SELECT factory_code FROM factory WHERE factory_code = ''F1'''",
    ],
)
def test_allowed_mysql_runtime_operations(statement: str) -> None:
    assert forbidden_mysql_runtime_operation(statement) is None
