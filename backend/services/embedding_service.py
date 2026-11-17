"""Sentence-transformer embeddings with lazy model loading."""

from collections.abc import Sequence

from sentence_transformers import SentenceTransformer


class EmbeddingService:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._get_model().encode(list(texts), normalize_embeddings=True)
        return vectors.tolist()

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model
