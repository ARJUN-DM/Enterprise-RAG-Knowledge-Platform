"""OpenAI embedding provider adapter.

Uses text-embedding-3-small (1536 dimensions) by default.
"""

from __future__ import annotations

from openai import AsyncOpenAI

from app.providers.interfaces import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by OpenAI."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "text-embedding-3-small",
        dimensions: int = 768,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._client = AsyncOpenAI(api_key=api_key) if api_key else None

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        if not self._client:
            return [0.0] * self._dimensions

        response = await self._client.embeddings.create(
            model=self._model, input=text, dimensions=self._dimensions
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self._client:
            return [[0.0] * self._dimensions for _ in texts]

        response = await self._client.embeddings.create(
            model=self._model, input=texts, dimensions=self._dimensions
        )
        return [item.embedding for item in response.data]
