"""Gemini embedding provider implementation.

Returns 768-dimensional embeddings (gemini-embedding-001).
Raises on embedding failure — no silent zero-vector fallback.
L2-normalizes each embedding so cosine-distance ranking stays well-behaved.
"""

from __future__ import annotations

import asyncio
import math
import traceback
from typing import Any

from structlog import get_logger

from app.providers.interfaces import EmbeddingProvider

logger = get_logger(__name__)

# Gemini embedding API caps a single batch at 100 requests.
# Documents with more than 100 chunks are split into sub-batches.
GEMINI_EMBED_BATCH_SIZE = 100

# Maximum retries for transient API errors (rate limits, temporary unavailability).
MAX_RETRIES = 4
# Base delay in seconds for exponential backoff.
BASE_RETRY_DELAY_S = 1.0

def _l2_normalize(vec: list[float]) -> list[float]:
    """L2-normalize a vector in-place and return it."""
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        for i in range(len(vec)):
            vec[i] /= norm
    return vec


def _is_transient_error(exc: Exception) -> bool:
    """Return True if *exc* is a transient API error worth retrying."""
    msg = str(exc).lower()
    # Check for known transient patterns in the error string.
    for pattern in ("429", "resource_exhausted", "503", "unavailable"):
        if pattern in msg:
            return True
    return False


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by Google Gemini."""

    def __init__(self, api_key: str = "", model: str = "gemini-embedding-001") -> None:
        self._api_key = api_key
        self._model = model
        self._client: Any = None
        self._dimensions = 768
        if api_key:
            try:
                from google import genai

                self._client = genai.Client(api_key=api_key)
            except Exception as exc:
                logger.warning("gemini_embed_client_init_failed", error=str(exc))
                self._client = None

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text string.

        This method sends one item to the API and is unaffected by batch limits.
        """
        if not self._client:
            raise RuntimeError(
                "Gemini client not initialized — check GEMINI_API_KEY"
            )

        try:
            from google.genai import types

            response = self._client.models.embed_content(
                model=self._model,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=self._dimensions,
                ),
            )
            if response.embeddings and len(response.embeddings) > 0:
                return _l2_normalize(response.embeddings[0].values)
            logger.warning("gemini_embed_empty_response", model=self._model)
            raise RuntimeError(
                f"Gemini embed returned empty response for model {self._model}"
            )
        except Exception as exc:
            logger.error(
                "gemini_embed_failed",
                model=self._model,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of text strings.

        Splits the input into sub-batches of at most ``GEMINI_EMBED_BATCH_SIZE``
        (default 100) to stay within the Gemini embedding API's per-request limit.
        Results are concatenated **in the original order** so they line up 1:1
        with the input chunks.

        Each sub-batch is retried up to ``MAX_RETRIES`` times with exponential
        backoff on transient errors (HTTP 429 / RESOURCE_EXHAUSTED, 503 / UNAVAILABLE).
        On persistent failure the exception propagates — no zero-vector fallback.
        """
        if not self._client:
            raise RuntimeError(
                "Gemini client not initialized — check GEMINI_API_KEY"
            )

        if not texts:
            return []

        from google.genai import types

        batch_size = GEMINI_EMBED_BATCH_SIZE
        all_embeddings: list[list[float]] = []

        for start in range(0, len(texts), batch_size):
            sub_batch = texts[start : start + batch_size]
            embeddings = await self._embed_sub_batch(
                sub_batch, start, types
            )
            all_embeddings.extend(embeddings)

        # Validate total count — mismatch means a silent bug or API regression.
        if len(all_embeddings) != len(texts):
            logger.error(
                "gemini_embed_batch_count_mismatch",
                expected=len(texts),
                got=len(all_embeddings),
            )
            raise RuntimeError(
                f"Embedding count mismatch: expected {len(texts)} embeddings "
                f"but got {len(all_embeddings)}"
            )

        return all_embeddings

    async def _embed_sub_batch(
        self,
        texts: list[str],
        start_index: int,
        types_module: Any,
    ) -> list[list[float]]:
        """Embed a single sub-batch with retry logic for transient errors."""
        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.models.embed_content(
                    model=self._model,
                    contents=texts,
                    config=types_module.EmbedContentConfig(
                        output_dimensionality=self._dimensions,
                    ),
                )

                if response.embeddings:
                    return [
                        _l2_normalize(e.values) for e in response.embeddings
                    ]

                logger.warning(
                    "gemini_embed_sub_batch_empty_response",
                    model=self._model,
                    batch_start=start_index,
                )
                raise RuntimeError(
                    f"Gemini embed_batch returned empty response for model "
                    f"{self._model} (sub-batch starting at {start_index})"
                )

            except Exception as exc:
                last_exc = exc
                if _is_transient_error(exc) and attempt < MAX_RETRIES:
                    delay = BASE_RETRY_DELAY_S * (2 ** (attempt - 1))
                    logger.warning(
                        "embed_batch_retry",
                        attempt=attempt,
                        max_retries=MAX_RETRIES,
                        delay_s=delay,
                        error=str(exc),
                        batch_start=start_index,
                    )
                    await asyncio.sleep(delay)
                else:
                    # Log and re-raise (either non-transient or out of retries).
                    logger.error(
                        "gemini_embed_sub_batch_failed",
                        model=self._model,
                        error=str(exc),
                        batch_start=start_index,
                        attempt=attempt,
                        traceback=traceback.format_exc(),
                    )
                    raise
        # Should not reach here, but defensive.
        raise RuntimeError("Unexpected: _embed_sub_batch exhausted all paths")
