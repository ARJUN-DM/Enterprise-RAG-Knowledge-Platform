"""Pluggable re-ranker for improving retrieval quality.

Current implementation: hybrid score (vector similarity + keyword overlap).
Can be replaced with:
- Cross-encoder model (e.g., BAAI/bge-reranker-v2-m3)
- Cohere Rerank API
- Instruct-based reranking
"""

from __future__ import annotations

from typing import Protocol


class Reranker(Protocol):
    """Protocol for reranker implementations."""

    async def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        """Re-rank chunks by relevance to the query."""
        ...
