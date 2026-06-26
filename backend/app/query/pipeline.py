"""Core RAG query pipeline.

Steps:
    1. Query condensation (for follow-up questions with history)
    2. Embed the user query (or condensed standalone query)
    3. Role-filtered vector search (pgvector)
    4. Re-rank
    5. De-duplicate
    6. Short-circuit on low similarity (friendly greeting)
    7. Grounded prompt construction
    8. LLM call with history (multi-turn memory)
    9. Empty-answer fallback
    10. Structured response with citations
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from structlog import get_logger

from app.db.models import Chunk, Query
from app.providers import get_embedding_provider, get_llm_provider
from app.query.prompts import (
    MULTI_TURN_SYSTEM_PROMPT,
    MULTI_TURN_USER_PROMPT,
    SYSTEM_PROMPT,
    USER_PROMPT,
    format_citation_text,
)

logger = get_logger(__name__)

# Friendly greeting used for greeting/chit-chat messages
GREETING_REPLY = (
    "Hello! I'm your enterprise knowledge assistant. I can answer questions about "
    "the documents in your organization using our knowledge base. Try asking me "
    "something like 'What documents are available?' or ask a specific question "
    "about your uploaded documents."
)

# Message shown when the user's role has no documents uploaded yet
NO_DOCS_REPLY = (
    "I don't have any documents available for your role yet \u2014 upload some "
    "on the Upload page."
)

# Fallback when the LLM returned empty content for a document-grounded query
EMPTY_ANSWER_FALLBACK = (
    "I couldn't generate a response for that \u2014 try rephrasing your "
    "question about the documents."
)


# Explicit greeting/chit-chat detection set.
# We use exact or word-prefix matching on the normalized (lowercased,
# punctuation-stripped) message.  Only messages with 4 or fewer words are
# considered — real document questions are almost always longer.
_GREETING_WORDS: set[str] = {"hi", "hello", "hey", "yo", "thanks"}
_GREETING_TWO_WORDS: set[str] = {"thank you", "good morning", "good evening"}
_GREETING_THREE_WORDS: set[str] = {"how are you"}


def _is_greeting(question: str) -> bool:
    """Return True if *question* looks like a simple greeting or pleasantry.

    Uses a small explicit heuristic — no ML or similarity threshold.
    """
    msg = question.lower().strip()
    words = msg.split()
    if len(words) > 4:
        return False
    # Strip common punctuation from each word for clean matching
    clean = [w.strip(".,!?;:'\"") for w in words]

    # Single-word greetings
    if clean[0] in _GREETING_WORDS:
        return True
    # Two-word greetings
    if len(clean) >= 2 and " ".join(clean[:2]) in _GREETING_TWO_WORDS:
        return True
    # Three-word greetings
    if len(clean) >= 3 and " ".join(clean[:3]) in _GREETING_THREE_WORDS:
        return True
    return False


@dataclass
class Citation:
    """A single source citation for an answer."""

    chunk_id: str
    document: str
    section: str
    similarity: float
    content: str


@dataclass
class QueryResult:
    """Structured result from the query pipeline."""

    answer: str
    citations: list[Citation] = field(default_factory=list)
    trace_id: str = ""
    latency_ms: int = 0
    steps: dict = field(default_factory=dict)
    role: str = ""
    question: str = ""


async def search_chunks(
    query_text: str,
    role: str,
    db: AsyncSession,
    top_k: int = 8,
) -> list[dict]:
    """Search chunks by vector similarity with RBAC filtering.

    Uses pgvector <=> (cosine distance) operator with role filtering.
    """
    embedder = get_embedding_provider()
    query_embedding = await embedder.embed(query_text)

    # Use pgvector cosine distance with role filter
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
    sql = text(
        """
        SELECT
            c.id,
            c.content,
            c.meta_data,
            c.document_id,
            d.name AS document_name,
            1 - (c.embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
          AND :role = ANY(c.allowed_roles)
        ORDER BY c.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
        """
    )

    result = await db.execute(
        sql,
        {
            "embedding": embedding_str,
            "role": role,
            "top_k": top_k,
        },
    )

    rows = result.fetchall()
    chunks = []
    for row in rows:
        meta = row.meta_data or {}
        chunks.append(
            {
                "chunk_id": str(row.id),
                "document_id": str(row.document_id),
                "content": row.content,
                "source": row.document_name,
                "section_heading": meta.get("section_heading", ""),
                "metadata": meta,
                "similarity": float(row.similarity),
            }
        )

    return chunks


async def _rerank_chunks(chunks: list[dict], query_text: str) -> list[dict]:
    """Re-rank chunks using a simple cross-encoder approach.

    Current implementation uses dot-product re-scoring with query expansion.
    Can be replaced with a cross-encoder model for better results.
    """
    # For now, the chunks are already ordered by vector similarity.
    # This function is a placeholder for a cross-encoder re-ranker.
    # The simple approach: re-score based on keyword overlap with query.
    query_words = set(query_text.lower().split())
    for chunk in chunks:
        content_words = set(chunk["content"].lower().split())
        overlap = len(query_words & content_words) / max(len(query_words), 1)
        # Blend: 70% vector similarity + 30% keyword overlap
        chunk["relevance_score"] = 0.7 * chunk["similarity"] + 0.3 * overlap

    chunks.sort(key=lambda c: c["relevance_score"], reverse=True)
    return chunks


def _condense_query(question: str, history: list[dict[str, str]]) -> str:
    """Condense a follow-up question into a standalone retrieval query.

    Uses a lightweight heuristic: prepend the last user question context.
    This is robust enough for common follow-up patterns like "list them one
    by one" or "tell me more about that."
    """
    # Collect prior user messages for context
    prev_user_msgs = [
        h["content"] for h in history if h["role"] == "user"
    ]
    if not prev_user_msgs:
        return question

    # Use the most recent user question as context for disambiguation
    context = prev_user_msgs[-1]
    return f"{question} - referring to: {context}"


async def answer_query(
    question: str,
    role: str,
    db: AsyncSession,
    top_k: int = 8,
    trace_id: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> QueryResult:
    """Run the full query pipeline end-to-end.

    Args:
        question: The user's question.
        role: The RBAC role for filtering.
        db: Database session.
        top_k: Number of chunks to retrieve.
        trace_id: Optional trace ID for observability.
        history: Optional multi-turn history
            [{"role": "user"|"assistant", "content": "..."}]
            (most recent last, max ~6 messages).
    """
    trace_id = trace_id or str(uuid.uuid4())
    # Initialise ALL timing keys so early-return paths never leave a key
    # missing (which would produce "NaNs" in the frontend).
    steps: dict[str, float] = {
        "condense_ms": 0,
        "embed_ms": 0,
        "search_ms": 0,
        "rerank_ms": 0,
        "prompt_ms": 0,
        "llm_ms": 0,
    }
    start_time = time.time()

    # Step 0: Condense query for retrieval (if history present)
    history = history or []
    retrieval_query = (
        _condense_query(question, history) if history else question
    )
    steps["condense_ms"] = 0  # heuristic is instant

    # Step 1: Embed query
    t0 = time.time()
    embedder = get_embedding_provider()
    query_embedding = await embedder.embed(retrieval_query)
    steps["embed_ms"] = round((time.time() - t0) * 1000)

    # Step 2: Role-filtered vector search
    t0 = time.time()
    chunks = await search_chunks(retrieval_query, role, db, top_k=top_k)
    steps["search_ms"] = round((time.time() - t0) * 1000)

    # Step 3: Re-rank
    t0 = time.time()
    chunks = await _rerank_chunks(chunks, retrieval_query)
    steps["rerank_ms"] = round((time.time() - t0) * 1000)

    # De-duplicate exact-content chunks — keep the highest-similarity instance
    seen_contents: set[str] = set()
    deduped: list[dict] = []
    for c in chunks:
        content = c.get("content", "")
        if content not in seen_contents:
            seen_contents.add(content)
            deduped.append(c)
    chunks = deduped

    # Step 3.5: Short-circuit for greetings and no-documents cases
    #
    # With sentence-transformers embeddings, cosine similarities fall in the
    # ~0.2–0.4 range even for relevant chunks, so an absolute similarity
    # threshold cannot distinguish greetings from real questions.  Instead we
    # use an explicit heuristic for greeting detection and a check for zero
    # retrieved chunks.  All other queries proceed to the full RAG + LLM path
    # regardless of absolute similarity.
    if not chunks:
        total_ms = round((time.time() - start_time) * 1000)
        logger.info(
            "query_no_documents_for_role",
            trace_id=trace_id,
            role=role,
        )
        return QueryResult(
            answer=NO_DOCS_REPLY,
            citations=[],
            trace_id=trace_id,
            latency_ms=total_ms,
            steps=steps,
            role=role,
            question=question,
        )

    if _is_greeting(question):
        total_ms = round((time.time() - start_time) * 1000)
        logger.info(
            "query_short_circuit_greeting",
            trace_id=trace_id,
            role=role,
        )
        return QueryResult(
            answer=GREETING_REPLY,
            citations=[],
            trace_id=trace_id,
            latency_ms=total_ms,
            steps=steps,
            role=role,
            question=question,
        )

    # Step 4: Build grounded prompt (use multi-turn variant when history present)
    t0 = time.time()
    context = format_citation_text(chunks)
    if history:
        system_prompt = MULTI_TURN_SYSTEM_PROMPT.format(context=context)
        user_prompt = MULTI_TURN_USER_PROMPT.format(question=question)
    else:
        system_prompt = SYSTEM_PROMPT.format(context=context)
        user_prompt = USER_PROMPT.format(question=question)
    steps["prompt_ms"] = round((time.time() - t0) * 1000)

    # Step 5: LLM call with history (multi-turn memory)
    t0 = time.time()
    llm = get_llm_provider()
    answer_text = await llm.generate(
        prompt=user_prompt,
        system_prompt=system_prompt,
        history=history or None,  # pass None when empty to keep interface clean
    )
    steps["llm_ms"] = round((time.time() - t0) * 1000)

    # Step 5.5: Friendly fallback if LLM returned empty
    if not answer_text.strip():
        logger.warning(
            "query_empty_answer_fallback",
            trace_id=trace_id,
        )
        answer_text = EMPTY_ANSWER_FALLBACK

    total_ms = round((time.time() - start_time) * 1000)

    # Build citations (use deduped chunks, which may be fewer than top_k)
    citations = [
        Citation(
            chunk_id=c["chunk_id"],
            document=c["source"],
            section=c.get("section_heading", ""),
            similarity=round(c["similarity"], 4),
            content=c["content"][:200] + "..." if len(c["content"]) > 200 else c["content"],
        )
        for c in chunks[:top_k]
    ]

    return QueryResult(
        answer=answer_text,
        citations=citations,
        trace_id=trace_id,
        latency_ms=total_ms,
        steps=steps,
        role=role,
        question=question,
    )


async def save_query(db: AsyncSession, result: QueryResult) -> uuid.UUID:
    """Persist a query and its result to the database."""
    query_id = uuid.uuid4()
    q = Query(
        id=query_id,
        role=result.role,
        question=result.question,
        answer=result.answer,
        trace_id=result.trace_id,
        latency_ms=result.latency_ms,
    )
    db.add(q)
    await db.flush()
    return query_id
