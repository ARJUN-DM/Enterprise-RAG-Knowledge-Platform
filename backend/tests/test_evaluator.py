"""Tests for the RAG evaluation framework."""

from __future__ import annotations

import pytest

from app.eval.evaluator import RAGEvaluator


@pytest.mark.asyncio
class TestRAGEvaluator:
    """Verify evaluation metrics produce sensible values."""

    async def test_empty_inputs(self):
        """Empty answer or chunks should produce zero scores."""
        evaluator = RAGEvaluator()
        result = await evaluator.evaluate(
            question="Test?",
            answer="",
            retrieved_chunks=[],
        )
        assert result.faithfulness == 0.0
        assert result.relevance == 0.0
        assert result.context_precision == 0.0
        assert result.context_recall == 0.0

    async def test_context_precision_with_citations(self):
        """Context precision should reflect how many chunks are cited in the answer."""
        evaluator = RAGEvaluator()
        chunks = [
            {"chunk_id": "1", "content": "Alpha content here."},
            {"chunk_id": "2", "content": "Beta content here."},
        ]
        answer = "Alpha content here. [Source 1]"
        result = await evaluator.evaluate(
            question="Test?",
            answer=answer,
            retrieved_chunks=chunks,
        )
        # Only one chunk is referenced in the answer
        assert result.context_precision == 0.5

    async def test_context_recall_with_golden(self):
        """Context recall should compare retrieved vs golden chunk IDs."""
        evaluator = RAGEvaluator()
        chunks = [
            {"chunk_id": "1", "content": "Alpha"},
            {"chunk_id": "2", "content": "Beta"},
        ]
        golden = {"1", "3"}
        result = await evaluator.evaluate(
            question="Test?",
            answer="Alpha [Source 1]",
            retrieved_chunks=chunks,
            golden_chunk_ids=golden,
        )
        # 1 out of 2 golden chunks retrieved
        assert result.context_recall == 0.5

    async def test_flagged_when_below_threshold(self):
        """Scores below the faithfulness threshold should be flagged."""
        evaluator = RAGEvaluator(faithfulness_threshold=0.9)
        # With no chunks and no answer, faithfulness should be 0
        result = await evaluator.evaluate(
            question="Test?",
            answer="",
            retrieved_chunks=[],
        )
        assert result.flagged is True

    async def test_not_flagged_when_above_threshold(self):
        """Scores above the threshold should not be flagged."""
        evaluator = RAGEvaluator(faithfulness_threshold=0.0)
        result = await evaluator.evaluate(
            question="Test?",
            answer="Test answer [Source 1]",
            retrieved_chunks=[{"chunk_id": "1", "content": "Test answer content"}],
        )
        assert result.flagged is False
