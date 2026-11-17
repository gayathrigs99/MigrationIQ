"""Load the knowledge base into ChromaDB. Run from backend/: python ingest.py"""

from core.config import get_settings
from core.container import create_rag_service


def main() -> None:
    settings = get_settings()
    count = create_rag_service(settings).ingest_directory(settings.knowledge_base_directory)
    print(f"Ingested {count} chunks from {settings.knowledge_base_directory}")


if __name__ == "__main__":
    main()
