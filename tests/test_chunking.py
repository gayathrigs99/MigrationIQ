from pathlib import Path

from schemas.migration import KnowledgeCategory
from services.chunking import chunk_document, load_knowledge_chunks

KNOWLEDGE_BASE = Path(__file__).resolve().parent.parent / "knowledge_base"
MAX_CHUNK_CHARS = 2500  # keeps the key content inside the embedding model's window


def test_each_section_becomes_one_chunk_with_title_context():
    text = "# Title\n\nIntro text.\n\n## First\n\nBody one.\n\n## Second\n\nBody two.\n"
    chunks = chunk_document(text, "doc.md", KnowledgeCategory.FUNCTIONS)

    assert [c.section for c in chunks] == ["Overview", "First", "Second"]
    assert chunks[1].text.startswith("Title / First")
    assert [c.chunk_id for c in chunks] == ["doc.md::0", "doc.md::1", "doc.md::2"]


def test_knowledge_base_files_all_chunk_into_valid_categories():
    chunks = load_knowledge_chunks(KNOWLEDGE_BASE)

    assert {c.category for c in chunks} == set(KnowledgeCategory)


def test_knowledge_base_sections_stay_small_and_ids_are_unique():
    chunks = load_knowledge_chunks(KNOWLEDGE_BASE)

    assert len({c.chunk_id for c in chunks}) == len(chunks)
    too_long = [c.chunk_id for c in chunks if len(c.text) > MAX_CHUNK_CHARS]
    assert not too_long, f"Split these sections: {too_long}"
