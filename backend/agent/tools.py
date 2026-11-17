"""The tools available to the migration workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.rag_service import RagService
    from services.sql_analyzer import SqlAnalyzer
    from services.sql_converter import SqlConverter
    from services.validation_service import ValidationService


@dataclass(frozen=True)
class MigrationToolkit:
    analyzer: SqlAnalyzer
    rag: RagService
    converter: SqlConverter
    validator: ValidationService
