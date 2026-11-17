"""Composition root: the only place that wires concrete services together."""

import chromadb
from langgraph.graph.state import CompiledStateGraph

from agent.graph import build_migration_graph
from agent.nodes import MigrationNodes
from agent.tools import MigrationToolkit
from core.config import Settings, get_settings
from services.embedding_service import EmbeddingService
from services.llm_service import GeminiLlmService
from services.rag_service import COLLECTION_NAME, RagService
from services.sql_analyzer import SqlAnalyzer
from services.sql_converter import SqlConverter
from services.validation_service import ValidationService


def create_rag_service(settings: Settings) -> RagService:
    client = chromadb.PersistentClient(path=str(settings.chroma_persist_directory))
    collection = client.get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    return RagService(
        EmbeddingService(settings.embedding_model_name),
        collection,
        results_per_construct=settings.retrieval_results_per_construct,
        max_references=settings.retrieval_max_references,
    )


def create_migration_graph(settings: Settings | None = None) -> CompiledStateGraph:
    settings = settings or get_settings()
    analyzer = SqlAnalyzer()
    toolkit = MigrationToolkit(
        analyzer=analyzer,
        rag=create_rag_service(settings),
        converter=SqlConverter(GeminiLlmService(settings.gemini_api_key, settings.llm_model)),
        validator=ValidationService(analyzer),
    )
    return build_migration_graph(MigrationNodes(toolkit, settings.max_correction_attempts))
