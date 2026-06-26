"""Batch evaluation runner.

Runs the evaluator against the golden QA dataset and checks the
faithfulness threshold for CI quality gating.
"""

from __future__ import annotations

import asyncio
import logging
import time

from structlog import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.eval.evaluator import RAGEvaluator
from app.eval.golden import GoldenQAItem, load_golden_qa
from app.eval.monitoring import LocalMonitoringProvider, ScoreRecord
from app.query.pipeline import answer_query, save_query

logger = get_logger(__name__)


async def run_golden_eval(
    golden_path: str = "evals/golden_qa.jsonl",
    faithfulness_threshold: float = 0.85,
    fail_on_threshold: bool = False,
) -> dict:
    """Run the evaluator against the golden QA dataset.

    For each item:
        1. Run the query pipeline to get an answer
        2. Evaluate the answer against the golden set
        3. Record scores via the monitoring provider

    Returns a summary dict with pass/fail status.
    """
    items = load_golden_qa(golden_path)
    if not items:
        logger.warning("no_golden_items", path=golden_path)
        return {"passed": True, "message": "No golden QA items to evaluate.", "scores": {}}

    evaluator = RAGEvaluator(faithfulness_threshold=faithfulness_threshold)
    monitor = LocalMonitoringProvider()

    all_scores: list[float] = []
    total_evaluated = 0
    flagged_count = 0

    async with async_session_factory() as db:
        for item in items:
            try:
                # Run query pipeline
                result = await answer_query(
                    question=item.question, role=item.role, db=db
                )
                query_id = await save_query(db, result)
                await db.flush()

                # Evaluate
                golden_ids = set(item.relevant_chunk_ids)
                eval_result = await evaluator.evaluate(
                    question=item.question,
                    answer=result.answer,
                    retrieved_chunks=[
                        {
                            "chunk_id": c.chunk_id,
                            "content": c.content,
                            "source": c.document,
                        }
                        for c in result.citations
                    ],
                    golden_chunk_ids=golden_ids if golden_ids else None,
                )

                # Record scores
                record = ScoreRecord(
                    query_id=str(query_id),
                    faithfulness=eval_result.faithfulness,
                    relevance=eval_result.relevance,
                    context_precision=eval_result.context_precision,
                    context_recall=eval_result.context_recall,
                    flagged=eval_result.flagged,
                )
                await monitor.record_scores(record, db)

                all_scores.append(eval_result.average)
                total_evaluated += 1
                if eval_result.flagged:
                    flagged_count += 1

                logger.info(
                    "golden_eval_item",
                    question=item.question[:60],
                    faithfulness=eval_result.faithfulness,
                    flagged=eval_result.flagged,
                )

            except Exception as exc:
                logger.error("golden_eval_failed", question=item.question[:60], error=str(exc))

        await db.commit()

    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
    passed = avg_score >= faithfulness_threshold and flagged_count == 0

    summary = {
        "passed": passed,
        "total_evaluated": total_evaluated,
        "flagged_count": flagged_count,
        "average_score": round(avg_score, 4),
        "threshold": faithfulness_threshold,
        "message": (
            "✅ All golden QA items passed quality checks."
            if passed
            else f"❌ {flagged_count} item(s) flagged. Average score {avg_score:.4f} below threshold {faithfulness_threshold}."
        ),
    }

    if fail_on_threshold and not passed:
        raise ValueError(summary["message"])

    return summary


def main() -> None:
    """CLI entrypoint for running golden eval."""
    logging.basicConfig(level=logging.INFO)
    import argparse

    parser = argparse.ArgumentParser(description="Run golden QA evaluation")
    parser.add_argument("--golden-path", default="evals/golden_qa.jsonl")
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--fail", action="store_true", help="Exit non-zero if threshold not met")
    args = parser.parse_args()

    summary = asyncio.run(
        run_golden_eval(
            golden_path=args.golden_path,
            faithfulness_threshold=args.threshold,
            fail_on_threshold=args.fail,
        )
    )
    print(summary["message"])
    print(f"  Total evaluated: {summary['total_evaluated']}")
    print(f"  Flagged: {summary['flagged_count']}")
    print(f"  Average score: {summary['average_score']}")
    print(f"  Threshold: {summary['threshold']}")


if __name__ == "__main__":
    main()
