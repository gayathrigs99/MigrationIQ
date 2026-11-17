import pytest

from schemas.migration import Severity
from services.sql_analyzer import SqlAnalyzer
from services.validation_service import ValidationService

VALID_FUNCTION = """
CREATE OR REPLACE FUNCTION get_bonus(p_salary numeric) RETURNS numeric
LANGUAGE plpgsql AS $$
BEGIN
  RETURN COALESCE(p_salary, 0) * 0.1;
END;
$$;
"""


@pytest.fixture
def validator() -> ValidationService:
    return ValidationService(SqlAnalyzer())


def error_messages(report) -> list[str]:
    return [issue.message for issue in report.errors]


def test_valid_query_passes(validator):
    report = validator.validate("SELECT COALESCE(salary, 0) FROM employees")

    assert report.passed
    assert "sql_parsing" in report.checks_performed


def test_leftover_oracle_construct_fails(validator):
    report = validator.validate("SELECT NVL(salary, 0) FROM employees")

    assert not report.passed
    assert any("NVL" in message for message in error_messages(report))


def test_unparseable_sql_fails(validator):
    report = validator.validate("SELECT * FROM (")

    assert not report.passed
    assert report.errors[0].check == "sql_parsing"


def test_empty_output_fails(validator):
    assert not validator.validate("   ").passed


def test_valid_plpgsql_function_passes_with_unparsed_body_warning(validator):
    report = validator.validate(VALID_FUNCTION)

    assert report.passed
    assert "plpgsql_structure" in report.checks_performed
    assert any(issue.severity is Severity.WARNING for issue in report.issues)


def test_oracle_style_function_header_fails_structure_checks(validator):
    oracle_style = "CREATE OR REPLACE FUNCTION f(p numeric) RETURN numeric IS BEGIN RETURN p; END;"
    report = validator.validate(oracle_style)

    messages = " ".join(error_messages(report))
    assert "RETURNS" in messages
    assert "LANGUAGE" in messages
    assert "quoted" in messages


def test_oracle_construct_inside_plpgsql_body_is_caught(validator):
    sql = VALID_FUNCTION.replace("COALESCE", "NVL")
    report = validator.validate(sql)

    assert not report.passed
