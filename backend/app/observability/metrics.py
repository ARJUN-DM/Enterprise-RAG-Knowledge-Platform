"""Prometheus metrics definitions and /metrics endpoint.

Exposes:
    - Request counts by endpoint and role
    - Request latencies
    - Token usage estimates
    - Evaluation score distributions
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY

router = APIRouter(tags=["metrics"])

# ── Metrics ──────────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "rag_requests_total",
    "Total request count by endpoint",
    labelnames=["endpoint", "method", "role"],
)

REQUEST_LATENCY = Histogram(
    "rag_request_latency_seconds",
    "Request latency in seconds",
    labelnames=["endpoint", "method"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

QUERY_LATENCY = Histogram(
    "rag_query_latency_seconds",
    "Query pipeline end-to-end latency",
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

CHUNKS_RETRIEVED = Histogram(
    "rag_chunks_retrieved",
    "Number of chunks retrieved per query",
    buckets=(1, 2, 3, 5, 10, 20, 50),
)

EVAL_FAITHFULNESS = Gauge(
    "rag_eval_faithfulness",
    "Faithfulness score from latest evaluation",
)

EVAL_RELEVANCE = Gauge(
    "rag_eval_relevance",
    "Relevance score from latest evaluation",
)

EVAL_CONTEXT_PRECISION = Gauge(
    "rag_eval_context_precision",
    "Context precision from latest evaluation",
)

EVAL_CONTEXT_RECALL = Gauge(
    "rag_eval_context_recall",
    "Context recall from latest evaluation",
)

DOCUMENTS_TOTAL = Gauge(
    "rag_documents_total",
    "Total number of ingested documents",
)

CHUNKS_TOTAL = Gauge(
    "rag_chunks_total",
    "Total number of chunks in the vector store",
)


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """Prometheus /metrics endpoint."""
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type="text/plain; charset=utf-8")
