"""Text helpers shared by SQL analysis and validation."""

import re

_COMMENT_OR_STRING = re.compile(r"--[^\n]*|/\*.*?\*/|'(?:[^']|'')*'", re.DOTALL)
_PROCEDURAL_MARKER = re.compile(
    r"\b(?:CREATE\s+(?:OR\s+REPLACE\s+)?(?:FUNCTION|PROCEDURE|PACKAGE|TRIGGER)|DECLARE|BEGIN)\b",
    re.IGNORECASE,
)


def strip_comments(sql: str) -> str:
    """Remove comments but keep string literals untouched."""
    return _COMMENT_OR_STRING.sub(_blank_unless_literal, sql)


def mask_comments_and_literals(sql: str) -> str:
    """Blank out comments and string literals so keyword scans cannot match inside them."""
    return _COMMENT_OR_STRING.sub(" ", sql)


def is_procedural(sql: str) -> bool:
    """True for PL/SQL or PL/pgSQL code (routines, packages, triggers, anonymous blocks)."""
    return _PROCEDURAL_MARKER.search(mask_comments_and_literals(sql)) is not None


def _blank_unless_literal(match: re.Match[str]) -> str:
    text = match.group()
    return text if text.startswith("'") else " "
