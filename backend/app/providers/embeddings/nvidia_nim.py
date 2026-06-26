"""Nvidia NIM embedding provider stub.

Demonstrates the on-prem deployment path. Not active without a NIM endpoint.
"""

from __future__ import annotations

from app.providers.interfaces import EmbeddingProvider


class NvidiaNimEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by Nvidia NIM (on-prem). Stub."""

    def __init__(self, base_url: str = "http://localhost:8000/nim") -> None:
        self._base_url = base_url
        self._dimensions = 768

    @property
    def model_name(self) -> str:
        return "nvidia/nv-embed-qa"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        return [0.0] * self._dimensions

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self._dimensions for _ in texts]
