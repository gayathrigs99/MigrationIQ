import pytest

from agent.graph import build_migration_graph, run_migration
from agent.nodes import MigrationNodes
from agent.tools import MigrationToolkit
from schemas.migration import ConversionResult, MigrationStatus
from services.sql_analyzer import SqlAnalyzer
from services.validation_service import ValidationService

ORACLE_SQL = "SELECT NVL(salary, 0) FROM employees"
STILL_ORACLE = "SELECT NVL(salary, 0) FROM employees"
FIXED = "SELECT COALESCE(salary, 0) FROM employees"


class FakeRag:
    def retrieve_for_constructs(self, constructs):
        return []


class ScriptedConverter:
    """Returns the scripted SQL outputs in order and records every request."""

    def __init__(self, outputs: list[str]) -> None:
        self._outputs = iter(outputs)
        self.requests = []

    def convert(self, request) -> ConversionResult:
        self.requests.append(request)
        return ConversionResult(
            converted_sql=next(self._outputs),
            transformations=[],
            uncertain_conversions=[],
            suggested_tests=["NULL salary returns 0"],
        )


def run(outputs: list[str], max_corrections: int = 2):
    analyzer = SqlAnalyzer()
    converter = ScriptedConverter(outputs)
    toolkit = MigrationToolkit(
        analyzer=analyzer,
        rag=FakeRag(),
        converter=converter,
        validator=ValidationService(analyzer),
    )
    graph = build_migration_graph(MigrationNodes(toolkit, max_corrections))
    return run_migration(graph, ORACLE_SQL), converter


def test_passes_on_first_attempt_without_retry():
    result, converter = run([FIXED])

    assert result.status is MigrationStatus.COMPLETED
    assert result.attempts == 1
    assert converter.requests[0].correction is None
    assert not result.manual_review_required


def test_retries_with_validation_feedback_then_succeeds():
    result, converter = run([STILL_ORACLE, FIXED])

    assert result.status is MigrationStatus.COMPLETED
    assert result.attempts == 2
    correction = converter.requests[1].correction
    assert correction.previous_sql == STILL_ORACLE
    assert any("NVL" in issue.message for issue in correction.issues)


def test_stops_after_retry_limit_and_requires_manual_review():
    result, _ = run([STILL_ORACLE] * 5, max_corrections=2)

    assert result.status is MigrationStatus.COMPLETED_WITH_ISSUES
    assert result.attempts == 3  # one initial conversion + two corrections
    assert result.manual_review_required
    assert not result.validation.passed


def test_zero_corrections_means_single_attempt():
    result, _ = run([STILL_ORACLE] * 3, max_corrections=0)

    assert result.attempts == 1
    assert result.status is MigrationStatus.COMPLETED_WITH_ISSUES


def test_report_carries_detected_constructs_and_original_sql():
    result, _ = run([FIXED])

    assert result.original_sql == ORACLE_SQL
    assert [c.name for c in result.detected_constructs] == ["NVL"]
