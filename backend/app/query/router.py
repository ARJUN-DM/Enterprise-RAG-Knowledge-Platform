"""Query API endpoints.

Provides:
    POST /api/v1/query - Ask a question (non-streaming), with optional history
    GET  /api/v1/query/stream - Ask a question (SSE streaming)
    GET  /api/v1/query/history - Get query history

All query endpoints wrap provider calls in try/except so an LLM or embedding
failure returns a 502/503 with a descriptive JSON detail instead of a bare 500.
DB persistence failures are also caught so a logging hiccup never causes 500.
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam, status
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.auth.dependencies import get_user_role
from app.db.models import EvalScore, Query
from app.db.session import get_db_session
from app.query.pipeline import answer_query, save_query

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["query"])

# Max history messages we accept from the client (6 = 3 user + 3 assistant turns)
MAX_HISTORY_MESSAGES = 6


def _validate_and_limit_history(raw_history: list | None) -> list[dict[str, str]]:
    """Validate and limit the conversation history from the request body.

    Accepts at most MAX_HISTORY_MESSAGES items. Each item must have
    'role' (user|assistant) and 'content' (str). Silently drops invalid items.
    """
    if not raw_history or not isinstance(raw_history, list):
        return []
    validated: list[dict[str, str]] = []
    for item in raw_history[-MAX_HISTORY_MESSAGES:]:
        if isinstance(item, dict):
            role = item.get("role", "")
            content = item.get("content", "")
            if role in ("user", "assistant") and isinstance(content, str):
                validated.append({"role": role, "content": content})
    return validated


@router.post("/query")
async def ask_question(
    body: dict,
    role: str = Depends(get_user_role),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Ask a question and get a cited answer.

    Accepts optional 'history' field: list of
    {"role": "user"|"assistant", "content": "..."} turns (most recent last).
    """
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question is required.")

    trace_id = body.get("trace_id") or str(uuid.uuid4())

    # Validate and limit history
    history = _validate_and_limit_history(body.get("history"))

    try:
        result = await answer_query(
            question=question,
            role=role,
            db=db,
            trace_id=trace_id,
            history=history or None,
        )
    except Exception as exc:
        logger.error("query_failed", error=str(exc), trace_id=trace_id, role=role)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "The AI provider (LLM or embedding model) failed to process your request.",
                "trace_id": trace_id,
                "message": str(exc)[:500],
            },
        )

    # Best-effort persistence: a DB hiccup must never produce a bare 500.
    try:
        query_id = await save_query(db, result)
        await db.commit()
    except Exception as exc:
        logger.error(
            "query_persistence_failed",
            error=str(exc),
            trace_id=trace_id,
            role=role,
        )
        await db.rollback()
        query_id = uuid.UUID(int=0)  # sentinel UUID for unpersisted queries

    return {
        "query_id": str(query_id),
        "answer": result.answer,
        "citations": [
            {
                "chunk_id": c.chunk_id,
                "document": c.document,
                "section": c.section,
                "similarity": c.similarity,
                "content_preview": c.content,
            }
            for c in result.citations
        ],
        "trace_id": result.trace_id,
        "latency_ms": result.latency_ms,
        "steps": result.steps,
    }


@router.get("/query/stream")
async def stream_answer(
    question: str = QueryParam(..., description="The question to ask"),
    role: str = Depends(get_user_role),
    db: AsyncSession = Depends(get_db_session),
):
    """Ask a question and stream the answer via SSE (Server-Sent Events)."""
    trace_id = str(uuid.uuid4())

    try:
        result = await answer_query(question=question, role=role, db=db, trace_id=trace_id)
    except Exception as exc:
        logger.error("query_stream_failed", error=str(exc), trace_id=trace_id, role=role)

        async def error_generator():
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": "The AI provider failed to process your request.",
                    "trace_id": trace_id,
                    "message": str(exc)[:500],
                }),
            }

        return EventSourceResponse(error_generator())

    # Best-effort persistence
    try:
        query_id = await save_query(db, result)
        await db.commit()
    except Exception as exc:
        logger.error(
            "query_stream_persistence_failed",
            error=str(exc),
            trace_id=trace_id,
            role=role,
        )
        await db.rollback()
        query_id = uuid.UUID(int=0)

    async def event_generator():
        # First send metadata
        yield {
            "event": "metadata",
            "data": json.dumps({
                "query_id": str(query_id),
                "trace_id": trace_id,
                "latency_ms": result.latency_ms,
                "citations": [
                    {
                        "chunk_id": c.chunk_id,
                        "document": c.document,
                        "section": c.section,
                        "similarity": c.similarity,
                    }
                    for c in result.citations
                ],
            }),
        }

        # Then stream the answer one character at a time
        for chunk in result.answer:
            yield {"event": "token", "data": json.dumps({"token": chunk})}

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())


@router.get("/query/history")
async def query_history(
    role: str = Depends(get_user_role),
    db: AsyncSession = Depends(get_db_session),
    limit: int = QueryParam(default=50, le=100),
) -> list[dict]:
    """Get recent query history."""
    stmt = (
        select(Query)
        .where(Query.role == role)
        .order_by(desc(Query.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    queries = result.scalars().all()

    return [
        {
            "id": str(q.id),
            "question": q.question,
            "answer": q.answer[:500] if q.answer else None,
            "trace_id": q.trace_id,
            "latency_ms": q.latency_ms,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        }
        for q in queries
    ]
