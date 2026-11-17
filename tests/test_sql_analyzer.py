import pytest

from schemas.migration import KnowledgeCategory
from services.sql_analyzer import SqlAnalyzer


@pytest.fixture
def analyzer() -> SqlAnalyzer:
    return SqlAnalyzer()


def names(result) -> list[str]:
    return [construct.name for construct in result.constructs]


def test_detects_oracle_functions_and_counts_occurrences(analyzer):
    result = analyzer.analyze("SELECT NVL(a, 0), NVL(b, 0), SYSDATE FROM DUAL")

    assert names(result) == ["NVL", "SYSDATE", "DUAL"]
    assert result.constructs[0].occurrences == 2


def test_ignores_constructs_inside_comments_and_string_literals(analyzer):
    result = analyzer.analyze("SELECT 'NVL(x)' AS label -- SYSDATE\nFROM employees /* DECODE( */")

    assert names(result) == []


def test_clean_sql_has_no_parser_error(analyzer):
    result = analyzer.analyze("SELECT NVL(salary, 0) FROM employees")

    assert result.parser_error is None
    assert not result.is_procedural


def test_reports_parser_error_for_broken_sql(analyzer):
    result = analyzer.analyze("SELECT * FROM (")

    assert result.parser_error is not None


def test_procedural_code_is_flagged_and_not_parsed(analyzer):
    sql = """
    CREATE OR REPLACE PROCEDURE audit_it IS
      PRAGMA AUTONOMOUS_TRANSACTION;
    BEGIN
      DBMS_OUTPUT.PUT_LINE('hi');
    END;
    """
    result = analyzer.analyze(sql)

    assert result.is_procedural
    assert result.parser_error is None
    assert {"ROUTINE_DEFINITION", "PRAGMA_AUTONOMOUS_TRANSACTION", "DBMS_OUTPUT"} <= set(names(result))


def test_constructs_carry_category_and_review_flags(analyzer):
    result = analyzer.analyze("SELECT id FROM t CONNECT BY PRIOR id = parent_id")
    connect_by = result.constructs[0]

    assert connect_by.name == "CONNECT_BY"
    assert connect_by.category is KnowledgeCategory.FUNCTIONS
    assert connect_by.needs_manual_review


def test_constructs_valid_in_postgres_are_not_marked_incompatible(analyzer):
    result = analyzer.analyze("BEGIN\nEXCEPTION WHEN OTHERS THEN NULL;\nEND;")
    exception_block = next(c for c in result.constructs if c.name == "EXCEPTION_BLOCK")

    assert not exception_block.postgres_incompatible
