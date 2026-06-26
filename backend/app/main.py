"""Enterprise RAG Knowledge Platform — FastAPI Application.

Registers all routers, middleware, observability, and the lifespan handler.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from structlog import get_logger

from app.api.v1.health import router as health_router
from app.config import settings
from app.db.session import Base, engine
from app.eval.router import router as eval_router
from app.ingestion.router import router as ingestion_router
from app.observability.logging import configure_logging
from app.observability.metrics import REQUEST_COUNT, REQUEST_LATENCY, router as metrics_router
from app.observability.tracing import configure_tracing
from app.query.router import router as query_router

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: configure observability, create tables, register metrics."""
    # Startup
    configure_logging()
    configure_tracing()
    logger.info("startup_begin")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")

    # Track document/chunk counts on startup
    try:
        from sqlalchemy import func, select

        from app.db.models import Chunk, Document

        async with engine.begin() as conn:
            doc_count = (await conn.execute(select(func.count(Document.id)))).scalar() or 0
            chunk_count = (await conn.execute(select(func.count(Chunk.id)))).scalar() or 0
        from app.observability.metrics import CHUNKS_TOTAL, DOCUMENTS_TOTAL

        DOCUMENTS_TOTAL.set(doc_count)
        CHUNKS_TOTAL.set(chunk_count)
        logger.info("metrics_initialized", documents=doc_count, chunks=chunk_count)
    except Exception:
        logger.warning("metrics_init_failed")

    yield

    # Shutdown
    await engine.dispose()
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="Enterprise RAG Knowledge Platform",
        description="Multi-tenant RAG knowledge assistant with RBAC, evaluation, and MCP integration.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── Middleware ──────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_trace_id(request: Request, call_next):
        """Attach a unique trace ID and instrument metrics."""
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request.state.trace_id = trace_id
        request.state.role = request.headers.get("X-User-Role", "unknown")

        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id

        # Record metrics
        role = request.state.role
        REQUEST_COUNT.labels(
            endpoint=request.url.path, method=request.method, role=role
        ).inc()

        return response

    # ── Observability instrumentation ───────────────────────────────────
    FastAPIInstrumentor.instrument_app(app, excluded_urls="/metrics")

    # ── Routers ─────────────────────────────────────────────────────────
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(metrics_router)
    app.include_router(ingestion_router)
    app.include_router(query_router)
    app.include_router(eval_router)

    return app


app = create_app()
