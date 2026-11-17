"""Pydantic schemas shared across the migration pipeline."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class KnowledgeCategory(StrEnum):
    """Knowledge base documents. Each value is the file stem of a document."""

    FUNCTIONS = "oracle_functions"
    DATA_TYPES = "data_type_mapping"
    EXCEPTIONS = "exception_handling"
    CURSORS = "cursor_migration"
    PROCEDURES = "procedure_migration"
    BEST_PRACTICES = "migration_best_practices"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class MigrationStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_ISSUES = "completed_with_issues"


# --- API request -----------------------------------------------------------


class MigrationRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=200_000)
    source_dialect: Literal["oracle"] = "oracle"
    target_dialect: Literal["postgres"] = "postgres"


# --- Analysis --------------------------------------------------------------


class DetectedConstruct(BaseModel):
    name: str
    category: KnowledgeCategory
    description: str
    occurrences: int
    postgres_incompatible: bool
    needs_manual_review: bool


class AnalysisResult(BaseModel):
    is_procedural: bool
    constructs: list[DetectedConstruct]
    parser_error: str | None = None


# --- Retrieval -------------------------------------------------------------


class KnowledgeReference(BaseModel):
    source: str
    section: str
    content: str
    score: float


# --- Conversion (LLM output contract: no defaults, so every field is requested) ---


class Transformation(BaseModel):
    original: str
    replacement: str
    explanation: str


class ConversionResult(BaseModel):
    converted_sql: str
    transformations: list[Transformation]
    uncertain_conversions: list[str]
    suggested_tests: list[str]


# --- Validation ------------------------------------------------------------


class ValidationIssue(BaseModel):
    severity: Severity
    check: str
    message: str


class ValidationReport(BaseModel):
    checks_performed: list[str] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return not self.errors


# --- Final report ----------------------------------------------------------


class MigrationResult(BaseModel):
    status: MigrationStatus
    original_sql: str
    converted_sql: str
    detected_constructs: list[DetectedConstruct]
    transformations: list[Transformation]
    knowledge_references: list[KnowledgeReference]
    validation: ValidationReport
    manual_review_required: bool
    warnings: list[str]
    suggested_tests: list[str]
    attempts: int
