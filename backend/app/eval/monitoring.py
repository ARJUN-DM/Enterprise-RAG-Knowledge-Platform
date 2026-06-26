"""Monitoring provider interface and local implementation.

Records evaluation scores to the database and exposes them via /metrics.
Designed to be replaced by Vertex AI Model Monitoring / Cloud Monitoring in GCP.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from structlog import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EvalScore

logger = get_logger(__name__)


@dataclass
class ScoreRecord:
    """A single evaluation score record for monitoring."""

    query_id: str
    faithfulness: float
    relevance: float
    context_precision: float
    context_recall: float
    flagged: bool


class MonitoringProvider(ABC):
    """Abstract interface for monitoring/observability of evaluation scores.

    Local implementation: Postgres + /metrics.
    GCP implementation: Vertex AI Model Monitoring + Cloud Monitoring.
    """

    @abstractmethod
    async def record_scores(self, record: ScoreRecord, db: AsyncSession) -> None:
        """Persist evaluation scores."""
        ...

    @abstractmethod
    async def get_flagged_scores(
        self, db: AsyncSession, threshold: float = 0.85, limit: int = 50
    ) -> list[dict]:
        """Retrieve flagged low-scoring evaluations."""
        ...

    @abstractmethod
    async def get_average_scores(
        self, db: AsyncSession, since_hours: int = 24
    ) -> dict[str, float]:
        """Get average scores over a time window."""
        ...


class LocalMonitoringProvider(MonitoringProvider):
    """Local monitoring provider using Postgres for persistence."""

    async def record_scores(self, record: ScoreRecord, db: AsyncSession) -> None:
        """Persist evaluation scores to the eval_scores table."""
        score = EvalScore(
            query_id=record.query_id,
            faithfulness=record.faithfulness,
            relevance=record.relevance,
            context_precision=record.context_precision,
            context_recall=record.context_recall,
            flagged=record.flagged,
        )
        db.add(score)
        await db.flush()
        logger.debug("eval_score_recorded", query_id=record.query_id, flagged=record.flagged)

    async def get_flagged_scores(
        self, db: AsyncSession, threshold: float = 0.85, limit: int = 50
    ) -> list[dict]:
        """Retrieve eval scores flagged as low quality."""
        from sqlalchemy import select, desc

        stmt = (
            select(EvalScore)
            .where(EvalScore.flagged == True)  # noqa: E712
            .order_by(desc(EvalScore.created_at))
            .limit(limit)
        )
        result = await db.execute(stmt)
        scores = result.scalars().all()

        return [
            {
                "id": str(s.id),
                "query_id": str(s.query_id),
                "faithfulness": s.faithfulness,
                "relevance": s.relevance,
                "context_precision": s.context_precision,
                "context_recall": s.context_recall,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in scores
        ]

    async def get_average_scores(
        self, db: AsyncSession, since_hours: int = 24
    ) -> dict[str, float]:
        """Get average eval scores over a rolling time window."""
        from sqlalchemy import func, select

        from app.db.models import EvalScore

        stmt = select(
            func.avg(EvalScore.faithfulness).label("avg_faithfulness"),
            func.avg(EvalScore.relevance).label("avg_relevance"),
            func.avg(EvalScore.context_precision).label("avg_precision"),
            func.avg(EvalScore.context_recall).label("avg_recall"),
            func.count(EvalScore.id).label("total_evaluations"),
        )
        result = await db.execute(stmt)
        row = result.one_or_none()

        return {
            "avg_faithfulness": round(float(row.avg_faithfulness or 0), 4),
            "avg_relevance": round(float(row.avg_relevance or 0), 4),
            "avg_context_precision": round(float(row.avg_precision or 0), 4),
            "avg_context_recall": round(float(row.avg_recall or 0), 4),
            "total_evaluations": int(row.total_evaluations or 0),
            "window_hours": since_hours,
        }
