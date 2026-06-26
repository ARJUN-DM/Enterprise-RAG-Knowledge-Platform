"""RAGEvaluator — computes all four evaluation metrics.

Metrics:
    1. Faithfulness: LLM-judged — what fraction of claims in the answer are
       supported by the retrieved context.
    2. Answer Relevance: cosine similarity between query and answer embeddings.
    3. Context Precision: fraction of retrieved chunks that contribute to the answer.
    4. Context Recall: overlap between retrieved chunks and relevant golden chunks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
from structlog import get_logger

from app.providers import get_embedding_provider, get_llm_provider

logger = get_logger(__name__)


@dataclass
class EvalResult:
    """Results from evaluating a single query/answer pair."""

    faithfulness: float = 0.0
    relevance: float = 0.0
    context_precision: float = 0.0
    context_recall: float = 0.0
    flagged: bool = False
    details: dict = field(default_factory=dict)

    @property
    def average(self) -> float:
        return (self.faithfulness + self.relevance + self.context_precision + self.context_recall) / 4.0


class RAGEvaluator:
    """Evaluates LLM answer quality using four metrics."""

    def __init__(self, faithfulness_threshold: float = 0.85) -> None:
        self._threshold = faithfulness_threshold

    async def evaluate(
        self,
        question: str,
        answer: str,
        retrieved_chunks: list[dict],
        golden_chunk_ids: set[str] | None = None,
    ) -> EvalResult:
        """Run all four evaluation metrics on a query/answer pair.

        Args:
            question: The user's question.
            answer: The LLM's answer.
            retrieved_chunks: Chunks retrieved by the query pipeline.
            golden_chunk_ids: Set of chunk IDs that are relevant per the golden QA set.

        Returns:
            EvalResult with all metrics populated.
        """
        result = EvalResult()

        # Metric 1: Faithfulness
        result.faithfulness = await self._compute_faithfulness(answer, retrieved_chunks)

        # Metric 2: Answer Relevance
        result.relevance = await self._compute_relevance(question, answer)

        # Metric 3: Context Precision
        result.context_precision = self._compute_context_precision(answer, retrieved_chunks)

        # Metric 4: Context Recall
        result.context_recall = self._compute_context_recall(
            retrieved_chunks, golden_chunk_ids
        )

        # Flag if faithfulness below threshold
        result.flagged = result.faithfulness < self._threshold

        result.details = {
            "faithfulness_threshold": self._threshold,
            "retrieved_count": len(retrieved_chunks),
            "golden_count": len(golden_chunk_ids) if golden_chunk_ids else 0,
        }

        return result

    async def _compute_faithfulness(
        self, answer: str, chunks: list[dict]
    ) -> float:
        """LLM-judged faithfulness: what fraction of claims are supported.

        Uses an LLM to extract claims from the answer and check each against
        the provided context. Falls back to citation-coverage heuristic if
        the LLM call fails.
        """
        if not answer or not chunks:
            return 0.0

        # Construct context text
        context_text = "\n\n".join(
            f"[Chunk {i+1}]: {c.get('content', '')[:500]}"
            for i, c in enumerate(chunks[:5])
        )

        judge_prompt = (
            "You are evaluating the faithfulness of an AI answer. "
            "Given the context and the answer, extract all factual claims "
            "from the answer and check if each claim is supported by the context.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Answer:\n{answer}\n\n"
            "Return ONLY a number between 0.0 and 1.0 representing the fraction "
            "of claims that are supported by the context. Return 1.0 if all claims "
            "are supported, 0.0 if none are. Do not include any other text."
        )

        try:
            llm = get_llm_provider()
            response = await llm.generate(
                prompt=judge_prompt,
                system_prompt="You are a strict evaluator. Return only a number.",
            )
            # Parse the number from response
            match = re.search(r"(\d+\.?\d*)", response.strip())
            if match:
                score = float(match.group(1))
                return max(0.0, min(1.0, score))
        except Exception as exc:
            logger.warning("faithfulness_llm_failed", error=str(exc))

        # Fallback: simple citation coverage heuristic
        citation_count = len(re.findall(r"\[Source\s*\d+\]", answer))
        if citation_count == 0:
            return 0.5  # Neutral score when no citations found
        return min(1.0, citation_count / max(len(chunks), 1) * 1.5)

    async def _compute_relevance(
        self, question: str, answer: str
    ) -> float:
        """Answer relevance via cosine similarity of query and answer embeddings."""
        if not question or not answer:
            return 0.0

        try:
            embedder = get_embedding_provider()
            q_emb = np.array(await embedder.embed(question))
            a_emb = np.array(await embedder.embed(answer))

            # Cosine similarity
            norm = np.linalg.norm(q_emb) * np.linalg.norm(a_emb)
            if norm == 0:
                return 0.0
            similarity = float(np.dot(q_emb, a_emb) / norm)
            return max(0.0, min(1.0, similarity))
        except Exception as exc:
            logger.warning("relevance_embedding_failed", error=str(exc))
            return 0.5

    def _compute_context_precision(
        self, answer: str, chunks: list[dict]
    ) -> float:
        """Context precision: fraction of retrieved chunks used in the answer.

        Checks which chunk IDs or content snippets appear in the answer text.
        """
        if not chunks:
            return 0.0

        used_count = 0
        for chunk in chunks:
            content_snippet = chunk.get("content", "")[:100]
            if content_snippet and content_snippet in answer:
                used_count += 1

        return used_count / len(chunks)

    def _compute_context_recall(
        self, retrieved_chunks: list[dict], golden_chunk_ids: set[str] | None
    ) -> float:
        """Context recall: overlap between retrieved and golden chunks."""
        if not golden_chunk_ids:
            return 0.0  # No golden set to compare against

        retrieved_ids = {c.get("chunk_id", "") for c in retrieved_chunks}
        if not retrieved_ids:
            return 0.0

        overlap = len(retrieved_ids & golden_chunk_ids)
        return overlap / len(golden_chunk_ids)
