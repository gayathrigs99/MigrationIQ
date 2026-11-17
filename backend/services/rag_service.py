"""Retrieval over the migration knowledge base, backed by ChromaDB."""

from collections.abc import Sequence
from pathlib import Path

from chromadb.api.models.Collection import Collection

from schemas.migration import DetectedConstruct, KnowledgeCategory, KnowledgeReference
from services.chunking import KnowledgeChunk, load_knowledge_chunks
from services.embedding_service import EmbeddingService

COLLECTION_NAME = "migration_knowledge"
_GENERAL_QUERY = "Oracle to PostgreSQL migration best practices and common pitfalls"


class RagService:
    def __init__(
        self,
        embedder: EmbeddingService,
        collection: Collection,
        *,
        results_per_construct: int = 2,
        max_references: int = 8,
    ) -> None:
        self._embedder = embedder
        self._collection = collection
        self._results_per_construct = results_per_construct
        self._max_references = max_references

    # --- ingestion ---------------------------------------------------------

    def ingest_directory(self, directory: Path) -> int:
        chunks = load_knowledge_chunks(directory)
        self.ingest(chunks)
        return len(chunks)

    def ingest(self, chunks: Sequence[KnowledgeChunk]) -> None:
        """Idempotent: replaces everything previously stored for the given sources."""
        if not chunks:
            return
        for source in {chunk.source for chunk in chunks}:
            self._collection.delete(where={"source": source})
        self._collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=self._embedder.embed([chunk.text for chunk in chunks]),
            metadatas=[
                {"source": chunk.source, "section": chunk.section, "category": chunk.category.value}
                for chunk in chunks
            ],
        )

    # --- retrieval ---------------------------------------------------------

    def retrieve_for_constructs(
        self, constructs: Sequence[DetectedConstruct]
    ) -> list[KnowledgeReference]:
        """One metadata-filtered query per construct, merged and de-duplicated."""
        if not constructs:
            return self._search(_GENERAL_QUERY, [], self._max_references)

        candidates = [
            reference
            for construct in constructs
            for reference in self._search(
                _construct_query(construct), [construct.category], self._results_per_construct
            )
        ]
        return _best_unique(candidates)[: self._max_references]

    def _search(
        self, query: str, categories: Sequence[KnowledgeCategory], limit: int
    ) -> list[KnowledgeReference]:
        where = {"category": {"$in": [c.value for c in categories]}} if categories else None
        result = self._collection.query(
            query_embeddings=self._embedder.embed([query]), n_results=limit, where=where
        )
        return [
            KnowledgeReference(
                source=metadata["source"],
                section=metadata["section"],
                content=document,
                score=1.0 - distance,
            )
            for document, metadata, distance in zip(
                result["documents"][0], result["metadatas"][0], result["distances"][0]
            )
        ]


def _construct_query(construct: DetectedConstruct) -> str:
    return f"Oracle {construct.name}: {construct.description}. PostgreSQL equivalent."


def _best_unique(references: Sequence[KnowledgeReference]) -> list[KnowledgeReference]:
    best: dict[tuple[str, str], KnowledgeReference] = {}
    for reference in references:
        key = (reference.source, reference.section)
        if key not in best or reference.score > best[key].score:
            best[key] = reference
    return sorted(best.values(), key=lambda reference: reference.score, reverse=True)
