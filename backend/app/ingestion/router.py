"""Upload API endpoint for document ingestion.

Accepts file uploads and triggers the ingestion pipeline as a background task.
Provides a GET /documents endpoint to list persisted documents with their
ingestion status.
"""

from __future__ import annotations

import os
import tempfile
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form, Query as QueryParam, status
from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.auth.dependencies import get_user_role
from app.db.models import Document, Chunk
from app.db.session import get_db_session
from app.ingestion.pipeline import IngestionTask, ingest_document

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt", ".docx"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    allowed_roles: str = Form("hr,engineering,admin"),
    role: str = Depends(get_user_role),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Upload a document for ingestion.

    The document is parsed, chunked, embedded, and stored as a background task.
    The response returns immediately with a document ID. A Document row is
    created immediately (status=queued) so it appears in the listing.
    """
    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({len(contents)} bytes). Max: {MAX_FILE_SIZE} bytes.",
        )

    # Parse allowed roles
    roles_list = [r.strip().lower() for r in allowed_roles.split(",") if r.strip()]
    if role not in roles_list and role != "admin":
        roles_list.append(role)

    # Write to temp file for parsing
    suffix = ext or ".tmp"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    doc_id = uuid.uuid4()

    # Create the Document row immediately with status=queued so it appears in listing
    doc = Document(
        id=doc_id,
        name=file.filename or "untitled",
        source="upload",
        uploaded_by_role=role,
        allowed_roles=roles_list,
        status="queued",
    )
    db.add(doc)
    await db.commit()

    # Schedule background ingestion
    background_tasks.add_task(
        _run_ingestion,
        tmp_path=tmp_path,
        file_name=file.filename or "untitled",
        uploaded_by_role=role,
        allowed_roles=roles_list,
        doc_id=doc_id,
    )

    return {
        "document_id": str(doc_id),
        "file_name": file.filename,
        "status": "queued",
        "message": "Document queued for ingestion.",
    }


async def _run_ingestion(
    tmp_path: str,
    file_name: str,
    uploaded_by_role: str,
    allowed_roles: list[str],
    doc_id: uuid.UUID,
) -> None:
    """Run ingestion in the background with its own DB session and track status."""
    from app.db.session import async_session_factory

    task = IngestionTask(
        file_path=tmp_path,
        file_name=file_name,
        uploaded_by_role=uploaded_by_role,
        allowed_roles=allowed_roles,
    )

    async with async_session_factory() as db:
        try:
            # Mark as processing
            doc = await db.execute(select(Document).where(Document.id == doc_id))
            doc_row = doc.scalar_one_or_none()
            if doc_row:
                doc_row.status = "processing"
                await db.flush()

            ingested_id = await ingest_document(task, db, doc_id=doc_id)

            # Mark as ingested with chunk count
            if doc_row:
                from sqlalchemy import func

                count_result = await db.execute(
                    select(func.count(Chunk.id)).where(Chunk.document_id == ingested_id)
                )
                chunk_count = count_result.scalar() or 0
                doc_row.status = "ingested"
                doc_row.chunk_count = chunk_count

            await db.commit()
            logger.info("ingestion_success", document_id=str(ingested_id))
        except Exception as exc:
            await db.rollback()
            logger.error("ingestion_failed", file_name=file_name, error=str(exc))
            # Mark as failed in a new transaction
            try:
                async with async_session_factory() as nested_db:
                    doc = await nested_db.execute(select(Document).where(Document.id == doc_id))
                    doc_row = doc.scalar_one_or_none()
                    if doc_row:
                        doc_row.status = "failed"
                        doc_row.error = str(exc)[:2000]
                        await nested_db.commit()
            except Exception as nested_exc:
                logger.error("status_update_failed", error=str(nested_exc))
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@router.get("")
async def list_documents(
    role: str = Depends(get_user_role),
    db: AsyncSession = Depends(get_db_session),
    limit: int = QueryParam(default=50, le=200),
) -> list[dict]:
    """List documents visible to the caller's role, with ingestion status.

    Admins see all documents. Other roles see only documents whose allowed_roles
    includes their role or that were uploaded by their role.
    """
    if role == "admin":
        stmt = select(Document).order_by(desc(Document.created_at)).limit(limit)
    else:
        stmt = (
            select(Document)
            .where(
                or_(
                    Document.allowed_roles.any(role),
                    Document.uploaded_by_role == role,
                )
            )
            .order_by(desc(Document.created_at))
            .limit(limit)
        )

    result = await db.execute(stmt)
    docs = result.scalars().all()

    return [
        {
            "id": str(d.id),
            "name": d.name,
            "uploaded_by_role": d.uploaded_by_role,
            "allowed_roles": d.allowed_roles or [],
            "status": d.status,
            "error": d.error,
            "chunk_count": d.chunk_count or 0,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    role: str = Depends(get_user_role),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Delete a document and its chunks, if the caller's role has access.

    - Admins may delete any document.
    - Other roles may delete documents whose `allowed_roles` include their role
      or that were uploaded by their role.
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # RBAC check: admin can delete anything; other roles need visibility
    if role != "admin":
        allowed = doc.allowed_roles or []
        if role not in allowed and doc.uploaded_by_role != role:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

    # Count chunks for metrics before deleting
    from sqlalchemy import func as sa_func

    count_result = await db.execute(
        select(sa_func.count(Chunk.id)).where(Chunk.document_id == document_id)
    )
    chunk_count = count_result.scalar() or 0

    # Delete chunks explicitly, then the document
    await db.execute(
        Chunk.__table__.delete().where(Chunk.document_id == document_id)
    )
    await db.execute(
        Document.__table__.delete().where(Document.id == document_id)
    )
    await db.commit()

    # Update Prometheus metrics
    try:
        from app.observability.metrics import CHUNKS_TOTAL, DOCUMENTS_TOTAL

        DOCUMENTS_TOTAL.dec()
        CHUNKS_TOTAL.dec(chunk_count)
    except Exception:
        pass

    logger.info("document_deleted", document_id=str(document_id), role=role, chunks=chunk_count)

    return {"deleted": True, "document_id": str(document_id)}
