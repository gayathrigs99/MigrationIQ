"""Deterministic detection of Oracle-specific constructs.

SQLGlot parses plain SQL well but not PL/SQL bodies, so construct detection is
rule based. SQLGlot is used only as a parse check for non-procedural statements.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

import sqlglot
from sqlglot.errors import SqlglotError

from schemas.migration import AnalysisResult, DetectedConstruct, KnowledgeCategory
from services.sql_text import is_procedural, mask_comments_and_literals


@dataclass(frozen=True)
class ConstructRule:
    name: str
    pattern: re.Pattern[str]
    category: KnowledgeCategory
    description: str
    postgres_incompatible: bool = True
    needs_manual_review: bool = False


def _rule(
    name: str,
    pattern: str,
    category: KnowledgeCategory,
    description: str,
    *,
    postgres_incompatible: bool = True,
    needs_manual_review: bool = False,
) -> ConstructRule:
    return ConstructRule(
        name=name,
        pattern=re.compile(pattern, re.IGNORECASE),
        category=category,
        description=description,
        postgres_incompatible=postgres_incompatible,
        needs_manual_review=needs_manual_review,
    )


_F = KnowledgeCategory.FUNCTIONS
_T = KnowledgeCategory.DATA_TYPES
_E = KnowledgeCategory.EXCEPTIONS
_C = KnowledgeCategory.CURSORS
_P = KnowledgeCategory.PROCEDURES

DEFAULT_RULES: tuple[ConstructRule, ...] = (
    # Functions and SQL syntax
    _rule("NVL", r"\bNVL\s*\(", _F, "NULL replacement function"),
    _rule("NVL2", r"\bNVL2\s*\(", _F, "Conditional NULL function"),
    _rule("DECODE", r"\bDECODE\s*\(", _F, "Inline value-matching function"),
    _rule("SYSDATE", r"\bSYSDATE\b", _F, "Current date and time"),
    _rule("SYSTIMESTAMP", r"\bSYSTIMESTAMP\b", _F, "Current timestamp with time zone"),
    _rule("TO_DATE", r"\bTO_DATE\s*\(", _F, "String to date conversion",
          postgres_incompatible=False, needs_manual_review=True),
    _rule("TRUNC", r"\bTRUNC\s*\(", _F, "Date or number truncation",
          postgres_incompatible=False, needs_manual_review=True),
    _rule("ADD_MONTHS", r"\bADD_MONTHS\s*\(", _F, "Date month arithmetic"),
    _rule("MONTHS_BETWEEN", r"\bMONTHS_BETWEEN\s*\(", _F, "Fractional months between dates"),
    _rule("LISTAGG", r"\bLISTAGG\s*\(", _F, "String aggregation"),
    _rule("INSTR", r"\bINSTR\s*\(", _F, "Substring position search"),
    _rule("ROWNUM", r"\bROWNUM\b", _F, "Row-limiting pseudo-column", needs_manual_review=True),
    _rule("DUAL", r"\bFROM\s+DUAL\b", _F, "Dummy single-row table"),
    _rule("SEQUENCE_NEXTVAL", r"\b\w+\.(?:NEXTVAL|CURRVAL)\b", _F, "Sequence access syntax"),
    _rule("MINUS", r"\bMINUS\b", _F, "Set difference operator"),
    _rule("OUTER_JOIN_PLUS", r"\(\+\)", _F, "Legacy outer join operator", needs_manual_review=True),
    _rule("CONNECT_BY", r"\bCONNECT\s+BY\b", _F, "Hierarchical query", needs_manual_review=True),
    _rule("MERGE", r"\bMERGE\s+INTO\b", _F, "Upsert statement",
          postgres_incompatible=False, needs_manual_review=True),
    # Data types
    _rule("VARCHAR2", r"\bN?VARCHAR2\b", _T, "Oracle variable-length string type"),
    _rule("NUMBER", r"\bNUMBER\b", _T, "Oracle numeric type"),
    _rule("LOB_TYPES", r"\b(?:CLOB|NCLOB|BLOB)\b", _T, "Large object types"),
    # Exceptions
    _rule("RAISE_APPLICATION_ERROR", r"\bRAISE_APPLICATION_ERROR\s*\(", _E,
          "Custom error raising"),
    _rule("ORACLE_EXCEPTION_NAME",
          r"\b(?:DUP_VAL_ON_INDEX|ZERO_DIVIDE|VALUE_ERROR|INVALID_NUMBER)\b", _E,
          "Oracle predefined exception name"),
    _rule("SQLCODE", r"\bSQLCODE\b", _E, "Numeric error code of the current exception"),
    _rule("PRAGMA_EXCEPTION_INIT", r"\bPRAGMA\s+EXCEPTION_INIT\b", _E,
          "Binding a user exception to an error number", needs_manual_review=True),
    _rule("EXCEPTION_BLOCK", r"\bEXCEPTION\s+WHEN\b", _E, "Exception handling block",
          postgres_incompatible=False),
    # Cursors and collections
    _rule("EXPLICIT_CURSOR", r"\bCURSOR\s+\w+(?:\s*\([^)]*\))?\s+IS\b", _C,
          "Explicit cursor declaration"),
    _rule("REF_CURSOR", r"\bSYS_REFCURSOR\b|\bREF\s+CURSOR\b", _C, "Cursor variable"),
    _rule("BULK_COLLECT", r"\bBULK\s+COLLECT\b", _C, "Bulk fetch into collections",
          needs_manual_review=True),
    _rule("FORALL", r"\bFORALL\b", _C, "Bulk DML over collections", needs_manual_review=True),
    # Procedures, functions and packages
    _rule("ROUTINE_DEFINITION", r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:PROCEDURE|FUNCTION)\b", _P,
          "Stored routine definition", postgres_incompatible=False),
    _rule("PACKAGE", r"\bCREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\b", _P, "Package definition",
          needs_manual_review=True),
    _rule("PRAGMA_AUTONOMOUS_TRANSACTION", r"\bPRAGMA\s+AUTONOMOUS_TRANSACTION\b", _P,
          "Autonomous transaction", needs_manual_review=True),
    _rule("EXECUTE_IMMEDIATE", r"\bEXECUTE\s+IMMEDIATE\b", _P, "Dynamic SQL",
          needs_manual_review=True),
    _rule("DBMS_OUTPUT", r"\bDBMS_OUTPUT\s*\.\s*\w+", _P, "Console output package"),
    _rule("ROWTYPE_ATTRIBUTE", r"%ROWTYPE\b", _P, "Row type anchoring",
          postgres_incompatible=False),
)


class SqlAnalyzer:
    """Finds Oracle-specific constructs in SQL or PL/SQL text."""

    def __init__(self, rules: Sequence[ConstructRule] = DEFAULT_RULES) -> None:
        self._rules = tuple(rules)

    def analyze(self, sql: str) -> AnalysisResult:
        masked = mask_comments_and_literals(sql)
        procedural = is_procedural(sql)
        constructs = [
            construct
            for rule in self._rules
            if (construct := self._detect(rule, masked)) is not None
        ]
        return AnalysisResult(
            is_procedural=procedural,
            constructs=constructs,
            parser_error=None if procedural else _find_oracle_parser_error(sql),
        )

    @staticmethod
    def _detect(rule: ConstructRule, masked_sql: str) -> DetectedConstruct | None:
        occurrences = len(rule.pattern.findall(masked_sql))
        if occurrences == 0:
            return None
        return DetectedConstruct(
            name=rule.name,
            category=rule.category,
            description=rule.description,
            occurrences=occurrences,
            postgres_incompatible=rule.postgres_incompatible,
            needs_manual_review=rule.needs_manual_review,
        )


def _find_oracle_parser_error(sql: str) -> str | None:
    try:
        sqlglot.parse(sql, read="oracle")
    except SqlglotError as error:
        return str(error).splitlines()[0]
    return None
