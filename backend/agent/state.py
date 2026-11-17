"""Shared state passed between workflow nodes."""

from typing import TypedDict

from schemas.migration import (
    AnalysisResult,
    ConversionResult,
    KnowledgeReference,
    MigrationResult,
    ValidationReport,
)


class MigrationState(TypedDict, total=False):
    source_sql: str
    analysis: AnalysisResult
    references: list[KnowledgeReference]
    conversion: ConversionResult
    validation: ValidationReport
    attempts: int
    result: MigrationResult
