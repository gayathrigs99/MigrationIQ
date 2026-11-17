"""Workflow nodes. Each node reads the state and returns a partial state update."""

from __future__ import annotations

from typing import Literal

from agent.state import MigrationState
from agent.tools import MigrationToolkit
from schemas.migration import (
    AnalysisResult,
    ConversionResult,
    MigrationResult,
    MigrationStatus,
    ValidationReport,
)
from services.sql_converter import ConversionRequest, CorrectionContext

ANALYZE = "analyze"
RETRIEVE = "retrieve"
CONVERT = "convert"
VALIDATE = "validate"
REPORT = "build_report"


class MigrationNodes:
    def __init__(self, toolkit: MigrationToolkit, max_correction_attempts: int) -> None:
        self._toolkit = toolkit
        self._max_corrections = max_correction_attempts

    def analyze(self, state: MigrationState) -> MigrationState:
        return {"analysis": self._toolkit.analyzer.analyze(state["source_sql"])}

    def retrieve(self, state: MigrationState) -> MigrationState:
        references = self._toolkit.rag.retrieve_for_constructs(state["analysis"].constructs)
        return {"references": references}

    def convert(self, state: MigrationState) -> MigrationState:
        request = ConversionRequest(
            source_sql=state["source_sql"],
            constructs=state["analysis"].constructs,
            references=state["references"],
            correction=_build_correction(state),
        )
        return {
            "conversion": self._toolkit.converter.convert(request),
            "attempts": state.get("attempts", 0) + 1,
        }

    def validate(self, state: MigrationState) -> MigrationState:
        return {"validation": self._toolkit.validator.validate(state["conversion"].converted_sql)}

    def route_after_validation(self, state: MigrationState) -> Literal["convert", "build_report"]:
        corrections_used = state["attempts"] - 1
        if state["validation"].passed or corrections_used >= self._max_corrections:
            return REPORT
        return CONVERT

    def build_report(self, state: MigrationState) -> MigrationState:
        analysis, conversion, validation = state["analysis"], state["conversion"], state["validation"]
        result = MigrationResult(
            status=(
                MigrationStatus.COMPLETED
                if validation.passed
                else MigrationStatus.COMPLETED_WITH_ISSUES
            ),
            original_sql=state["source_sql"],
            converted_sql=conversion.converted_sql,
            detected_constructs=analysis.constructs,
            transformations=conversion.transformations,
            knowledge_references=state["references"],
            validation=validation,
            manual_review_required=_requires_manual_review(analysis, conversion, validation),
            warnings=_collect_warnings(analysis, conversion),
            suggested_tests=conversion.suggested_tests,
            attempts=state["attempts"],
        )
        return {"result": result}


def _build_correction(state: MigrationState) -> CorrectionContext | None:
    validation, conversion = state.get("validation"), state.get("conversion")
    if validation is None or conversion is None:
        return None
    return CorrectionContext(previous_sql=conversion.converted_sql, issues=validation.errors)


def _requires_manual_review(
    analysis: AnalysisResult, conversion: ConversionResult, validation: ValidationReport
) -> bool:
    return (
        not validation.passed
        or bool(conversion.uncertain_conversions)
        or any(construct.needs_manual_review for construct in analysis.constructs)
    )


def _collect_warnings(analysis: AnalysisResult, conversion: ConversionResult) -> list[str]:
    warnings = list(conversion.uncertain_conversions)
    if analysis.parser_error:
        warnings.append(f"Source SQL could not be parsed by SQLGlot: {analysis.parser_error}")
    return warnings
