"""Splits knowledge base markdown into one retrievable chunk per `##` section.

Authoring rule: keep each section focused on one construct and put the key
statement first. The embedding model only reads roughly the first 256 tokens.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from schemas.migration import KnowledgeCategory

_SECTION_HEADING = re.compile(r"^## +(.+)$", re.MULTILINE)
_DOCUMENT_TITLE = re.compile(r"^# +(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    text: str
    source: str
    section: str
    category: KnowledgeCategory


def load_knowledge_chunks(directory: Path) -> list[KnowledgeChunk]:
    """Chunk every markdown file in `directory`. File stems must be KnowledgeCategory values."""
    chunks: list[KnowledgeChunk] = []
    for path in sorted(directory.glob("*.md")):
        category = KnowledgeCategory(path.stem)
        chunks += chunk_document(path.read_text(encoding="utf-8"), path.name, category)
    return chunks


def chunk_document(text: str, source: str, category: KnowledgeCategory) -> list[KnowledgeChunk]:
    title = _extract_title(text, fallback=source)
    return [
        KnowledgeChunk(
            chunk_id=f"{source}::{index}",
            text=f"{title} / {section}\n\n{body}",
            source=source,
            section=section,
            category=category,
        )
        for index, (section, body) in enumerate(_split_sections(text))
    ]


def _extract_title(text: str, fallback: str) -> str:
    match = _DOCUMENT_TITLE.search(text)
    return match.group(1).strip() if match else fallback


def _split_sections(text: str) -> list[tuple[str, str]]:
    preamble, *rest = _SECTION_HEADING.split(text)
    sections = list(zip(rest[0::2], rest[1::2]))
    intro = _DOCUMENT_TITLE.sub("", preamble).strip()
    if intro:
        sections.insert(0, ("Overview", intro))
    return [(name.strip(), body.strip()) for name, body in sections if body.strip()]
