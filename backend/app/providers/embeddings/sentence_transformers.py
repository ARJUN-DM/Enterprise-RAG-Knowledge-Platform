"""Local sentence-transformers embedding provider.

No API key required. Downloads the model on first use (~90 MB for MiniLM).
Embeddings are 384-dimensional; zero-padded to 768 to match the schema dimension.
"""

from __future__ import annotations

import numpy as np

from app.providers.interfaces import EmbeddingProvider


class SentenceTransformersEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using sentence-transformers (runs locally)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None
        self._actual_dimensions = 384
        self._target_dimensions = 768  # padded to match schema

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._target_dimensions

    def _get_model(self):
        """Lazy-load the model on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def _pad(self, vector: list[float]) -> list[float]:
        """Zero-pad a 384-d vector to 768-d."""
        if len(vector) >= self._target_dimensions:
            return vector[: self._target_dimensions]
        return vector + [0.0] * (self._target_dimensions - len(vector))

    async def embed(self, text: str) -> list[float]:
        model = self._get_model()
        emb = model.encode(text, normalize_embeddings=True)
        return self._pad(emb.tolist())

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        embs = model.encode(texts, normalize_embeddings=True)
        return [self._pad(row.tolist()) for row in embs]
