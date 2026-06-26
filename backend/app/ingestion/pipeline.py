"""Document ingestion pipeline.

Orchestrates: parse → chunk → embed → store.
Abstracted so it can run inline (FastAPI background tasks) or via a
task queue (Celery / PubSub) in production.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.db.models import Chunk, Document
from app.ingestion.chunker import chunk_document
from app.ingestion.parsers import parse_document
from app.providers import get_embedding_provider

logger = get_logger(__name__)


class IngestionTask:
    """Represents a single document ingestion task."""

    def __init__(
        self,
        file_path: str | Path,
        file_name: str,
        uploaded_by_role: str,
        allowed_roles: list[str] | None = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.file_name = file_name
        self.uploaded_by_role = uploaded_by_role
        self.allowed_roles = allowed_roles or [uploaded_by_role]


async def ingest_document(
    task: IngestionTask,
    db: AsyncSession,
    doc_id: uuid.UUID | None = None,
    progress_callback: Callable[[str, float], None] | None = None,
) -> uuid.UUID:
    """Ingest a single document end-to-end.

    Steps:
        1. Parse file into (text, metadata) segments
        2. Chunk segments at heading/paragraph boundaries
        3. Embed each chunk via configured EmbeddingProvider
        4. Store Document + Chunks in Postgres

    Args:
        task: The ingestion task with file path and metadata.
        db: Database session.
        doc_id: Pre-assigned document ID (from the upload endpoint). If None, a new one is generated.
        progress_callback: Optional progress callback.

    Returns the document ID.
    """
    logger.info("ingesting_document", name=task.file_name)

    if progress_callback:
        progress_callback("Parsing document...", 0.1)

    # Step 1: Parse
    segments = parse_document(task.file_path)

    if progress_callback:
        progress_callback("Chunking content...", 0.25)

    # Step 2: Chunk
    chunks_data = chunk_document(segments)

    if not chunks_data:
        raise ValueError(f"No content extracted from {task.file_name}")

    if progress_callback:
        progress_callback(f"Chunked into {len(chunks_data)} pieces", 0.4)

    # Step 3: Embed
    embedder = get_embedding_provider()
    texts_to_embed = [chunk["content"] for chunk in chunks_data]

    if progress_callback:
        progress_callback("Generating embeddings...", 0.5)

    embeddings = await embedder.embed_batch(texts_to_embed)

    if progress_callback:
        progress_callback("Storing in database...", 0.8)

    # Step 4: Store
    if doc_id is None:
        doc_id = uuid.uuid4()

    # Ensure the Document row exists (created by upload endpoint or create now)
    existing = await db.execute(select(Document).where(Document.id == doc_id))
    document = existing.scalar_one_or_none()
    if document is None:
        document = Document(
            id=doc_id,
            name=task.file_name,
            source="upload",
            uploaded_by_role=task.uploaded_by_role,
            allowed_roles=task.allowed_roles,
        )
        db.add(document)
        await db.flush()

    for chunk_data, embedding in zip(chunks_data, embeddings):
        chunk = Chunk(
            document_id=doc_id,
            content=chunk_data["content"],
            embedding=embedding,
            meta_data={
                # Use original file name, NOT the parser's temp filename (e.g. "tmp....pdf")
                "source": task.file_name,
                "section_heading": chunk_data.get("section_heading", ""),
            },
            allowed_roles=task.allowed_roles,
        )
        db.add(chunk)

    await db.flush()

    if progress_callback:
        progress_callback("Done", 1.0)

    logger.info(
        "ingestion_complete",
        document_id=str(doc_id),
        chunk_count=len(chunks_data),
        file_name=task.file_name,
    )

    return doc_id
