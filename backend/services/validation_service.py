"""Validation of generated PostgreSQL.

Checks here are deterministic and cheap. Passing them does NOT prove semantic
equivalence: a PL/pgSQL body is only checked structurally, and executing the
code against a real PostgreSQL instance is a separate, later stage.
"""

import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from schemas.migration import Severity, ValidationIssue, ValidationReport
from services.sql_analyzer import SqlAnalyzer
from services.sql_text import is_procedural, strip_comments

_CREATE_ROUTINE = re.compile(r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(FUNCTION|PROCEDURE)\b", re.IGNORECASE)
_RETURNS_CLAUSE = re.compile(r"\bRETURNS\b", re.IGNORECASE)
_LANGUAGE_CLAUSE = re.compile(r"\bLANGUAGE\s+\w+", re.IGNORECASE)
_QUOTED_BODY = re.compile(r"\bAS\s+(?:\$\w*\$|')", re.IGNORECASE)

_LEFTOVER_CHECK = "leftover_oracle_constructs"
_PARSING_CHECK = "sql_parsing"
_STRUCTURE_CHECK = "plpgsql_structure"


class ValidationService:
    def __init__(self, analyzer: SqlAnalyzer) -> None:
        self._analyzer = analyzer

    def validate(self, postgres_sql: str) -> ValidationReport:
        if not postgres_sql.strip():
            return ValidationReport(
                checks_performed=["non_empty_output"],
                issues=[_error("non_empty_output", "The converted SQL is empty.")],
            )

        checks = [_LEFTOVER_CHECK]
        issues = self._find_leftover_oracle_constructs(postgres_sql)

        if is_procedural(postgres_sql):
            checks.append(_STRUCTURE_CHECK)
            issues += _find_plpgsql_structure_issues(postgres_sql)
            issues.append(_warning(
                _STRUCTURE_CHECK,
                "The PL/pgSQL body is not parsed. Run it against a PostgreSQL instance "
                "and verify behaviour with tests.",
            ))
        else:
            checks.append(_PARSING_CHECK)
            issues += _find_postgres_parse_issues(postgres_sql)

        return ValidationReport(checks_performed=checks, issues=issues)

    def _find_leftover_oracle_constructs(self, sql: str) -> list[ValidationIssue]:
        analysis = self._analyzer.analyze(sql)
        return [
            _error(
                _LEFTOVER_CHECK,
                f"Oracle-specific construct {c.name} remains in the converted SQL "
                f"({c.occurrences}x): {c.description}.",
            )
            for c in analysis.constructs
            if c.postgres_incompatible
        ]


def _find_postgres_parse_issues(sql: str) -> list[ValidationIssue]:
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except SqlglotError as error:
        return [_error(_PARSING_CHECK, f"PostgreSQL parse error: {str(error).splitlines()[0]}")]

    issues = []
    for statement in statements:
        if statement is None:
            continue
        if isinstance(statement, exp.Command):
            issues.append(_warning(
                _PARSING_CHECK, "A statement type is not fully understood by the parser."
            ))
    return issues


def _find_plpgsql_structure_issues(sql: str) -> list[ValidationIssue]:
    code = strip_comments(sql)
    routine = _CREATE_ROUTINE.search(code)
    if routine is None:
        return []

    issues = []
    if routine.group(1).upper() == "FUNCTION" and not _RETURNS_CLAUSE.search(code):
        issues.append(_error(
            _STRUCTURE_CHECK, "Function has no RETURNS clause (Oracle's RETURN is not valid here)."
        ))
    if not _LANGUAGE_CLAUSE.search(code):
        issues.append(_error(_STRUCTURE_CHECK, "Routine has no LANGUAGE clause."))
    if not _QUOTED_BODY.search(code):
        issues.append(_error(
            _STRUCTURE_CHECK, "Routine body must follow AS and be quoted, e.g. AS $$ ... $$."
        ))
    return issues


def _error(check: str, message: str) -> ValidationIssue:
    return ValidationIssue(severity=Severity.ERROR, check=check, message=message)


def _warning(check: str, message: str) -> ValidationIssue:
    return ValidationIssue(severity=Severity.WARNING, check=check, message=message)
