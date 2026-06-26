"""Vertex AI embedding provider stub.

Demonstrates the GCP deployment path. Not active without GCP setup.
"""

from __future__ import annotations

from app.providers.interfaces import EmbeddingProvider


class VertexEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by Vertex AI (GCP). Stub."""

    def __init__(self, model: str = "text-embedding-004") -> None:
        self._model = model
        self._dimensions = 768

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        return self._stub_response(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._stub_response(t) for t in texts]

    def _stub_response(self, text: str) -> list[float]:
        return [0.0] * self._dimensions
