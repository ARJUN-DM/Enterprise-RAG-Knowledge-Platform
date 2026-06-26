"""Evaluation dashboard API endpoints.

Provides:
    GET /api/v1/eval/scores       — Average scores and stats
    GET /api/v1/eval/flagged      — Flagged low-scoring evaluations
    GET /api/v1/eval/history      — Score history over time
    POST /api/v1/eval/run         — Trigger a golden eval run
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EvalScore, Query
from app.db.session import get_db_session
from app.eval.monitoring import LocalMonitoringProvider

router = APIRouter(prefix="/api/v1/eval", tags=["evaluation"])


@router.get("/scores")
async def get_average_scores(
    db: AsyncSession = Depends(get_db_session),
    hours: int = QueryParam(default=168, alias="hours", description="Time window in hours"),
) -> dict:
    """Get average evaluation scores over a time window."""
    monitor = LocalMonitoringProvider()
    return await monitor.get_average_scores(db, since_hours=hours)


@router.get("/flagged")
async def get_flagged(
    db: AsyncSession = Depends(get_db_session),
    limit: int = QueryParam(default=50, le=200),
) -> list[dict]:
    """Get flagged low-scoring evaluations."""
    monitor = LocalMonitoringProvider()
    return await monitor.get_flagged_scores(db, limit=limit)


@router.get("/history")
async def get_eval_history(
    db: AsyncSession = Depends(get_db_session),
    limit: int = QueryParam(default=100, le=500),
) -> list[dict]:
    """Get evaluation score history joined with query info."""
    stmt = (
        select(
            EvalScore.id,
            EvalScore.faithfulness,
            EvalScore.relevance,
            EvalScore.context_precision,
            EvalScore.context_recall,
            EvalScore.flagged,
            EvalScore.created_at,
            Query.question,
            Query.role,
            Query.trace_id,
        )
        .join(Query, EvalScore.query_id == Query.id)
        .order_by(desc(EvalScore.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    return [
        {
            "id": str(row.id),
            "faithfulness": row.faithfulness,
            "relevance": row.relevance,
            "context_precision": row.context_precision,
            "context_recall": row.context_recall,
            "flagged": row.flagged,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "question": row.question[:200] if row.question else "",
            "role": row.role,
            "trace_id": row.trace_id,
        }
        for row in rows
    ]


@router.post("/run")
async def trigger_eval_run(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Trigger a golden QA evaluation run (placeholder for async job)."""
    from app.eval.runner import run_golden_eval

    summary = await run_golden_eval()
    return summary
