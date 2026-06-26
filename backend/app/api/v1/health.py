from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db_session)) -> dict:
    """Health check endpoint that verifies the API and database are operational."""
    # Verify database connectivity
    result = await db.execute(text("SELECT 1 AS ok"))
    row = result.one_or_none()

    # Check pgvector extension
    vector_result = await db.execute(
        text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")
    )
    vector_row = vector_result.one_or_none()

    return {
        "status": "healthy",
        "database": "connected" if row else "unreachable",
        "pgvector": {
            "installed": vector_row is not None,
            "version": vector_row.extversion if vector_row else None,
        },
        "version": "0.1.0",
    }
