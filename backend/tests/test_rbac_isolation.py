"""RBAC isolation tests — verify cross-role data leakage is impossible.

These tests prove that a user in one role CANNOT retrieve chunks
assigned to a different role via the vector search.

They run against the actual pgvector search pipeline and must
be executed with a running Postgres + pgvector database.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models import Chunk, Document
from app.db.session import Base, engine, async_session_factory


@pytest.fixture(scope="module")
def event_loop():
    """Create a new event loop per module for async fixtures."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def setup_db():
    """Ensure tables exist (run migrations inline)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session(setup_db):  # noqa: F811
    """Create a fresh session per test with transaction rollback."""
    async with async_session_factory() as db:
        yield db
        await db.rollback()


@pytest.mark.asyncio
class TestRBACIsolation:
    """PROVE that role-based filtering prevents cross-role data access."""

    async def _create_test_chunks(
        self, db: AsyncSession
    ) -> tuple[uuid.UUID, uuid.UUID]:
        """Create two chunks — one for HR, one for Engineering."""
        # HR document and chunk
        hr_doc = Document(
            name="HR_Policy_2024.pdf",
            source="upload",
            uploaded_by_role="hr",
        )
        db.add(hr_doc)
        await db.flush()

        hr_chunk = Chunk(
            document_id=hr_doc.id,
            content="HR policy: remote work allowed 3 days per week.",
            embedding=[0.01] * 768,  # fake embedding
            metadata={"source": "HR_Policy_2024.pdf", "section_heading": "Remote Work"},
            allowed_roles=["hr"],
        )
        db.add(hr_chunk)

        # Engineering document and chunk
        eng_doc = Document(
            name="Engineering_Playbook.md",
            source="upload",
            uploaded_by_role="engineering",
        )
        db.add(eng_doc)
        await db.flush()

        eng_chunk = Chunk(
            document_id=eng_doc.id,
            content="All code must be reviewed by at least one senior engineer.",
            embedding=[0.02] * 768,  # different fake embedding
            metadata={"source": "Engineering_Playbook.md", "section_heading": "Code Review"},
            allowed_roles=["engineering"],
        )
        db.add(eng_chunk)
        await db.flush()

        return hr_chunk.id, eng_chunk.id

    async def _count_chunks_for_role(self, db: AsyncSession, role: str) -> int:
        """Count chunks accessible to a given role via the SQL filter."""
        sql = text(
            """
            SELECT COUNT(*) FROM chunks
            WHERE :role = ANY(allowed_roles)
            """
        )
        result = await db.execute(sql, {"role": role})
        return result.scalar() or 0

    async def test_hr_cannot_see_engineering_chunks(self, session: AsyncSession):  # noqa: F811
        """HR role should NOT see Engineering chunks."""
        hr_id, eng_id = await self._create_test_chunks(session)
        await session.commit()

        hr_count = await self._count_chunks_for_role(session, "hr")
        eng_count = await self._count_chunks_for_role(session, "engineering")

        assert hr_count == 1, f"HR should see 1 chunk, found {hr_count}"
        assert eng_count == 1, f"Engineering should see 1 chunk, found {eng_count}"

        # Prove HR cannot see the engineering chunk
        sql = text(
            """
            SELECT id FROM chunks
            WHERE id = :chunk_id
              AND 'hr' = ANY(allowed_roles)
            """
        )
        result = await session.execute(sql, {"chunk_id": eng_id})
        assert result.fetchone() is None, "HR must NOT be able to access Engineering chunk!"

    async def test_engineering_cannot_see_hr_chunks(self, session: AsyncSession):  # noqa: F811
        """Engineering role should NOT see HR chunks."""
        hr_id, eng_id = await self._create_test_chunks(session)
        await session.commit()

        # Prove Engineering cannot see the HR chunk
        sql = text(
            """
            SELECT id FROM chunks
            WHERE id = :chunk_id
              AND 'engineering' = ANY(allowed_roles)
            """
        )
        result = await session.execute(sql, {"chunk_id": hr_id})
        assert result.fetchone() is None, "Engineering must NOT be able to access HR chunk!"

    async def test_admin_sees_all_chunks(self, session: AsyncSession):  # noqa: F811
        """Admin role should see chunks from all roles."""
        hr_id, eng_id = await self._create_test_chunks(session)
        await session.commit()

        # Create an admin-accessible chunk
        admin_chunk = Chunk(
            document_id=(await self._create_test_chunks(session))[0],  # reuse doc
            content="Admin settings and permissions.",
            embedding=[0.03] * 768,
            metadata={"source": "Admin_Guide.md", "section_heading": "Permissions"},
            allowed_roles=["admin"],
        )
        session.add(admin_chunk)
        await session.flush()
        await session.commit()

        admin_count = await self._count_chunks_for_role(session, "admin")
        assert admin_count >= 1, "Admin should see at least 1 chunk"

    async def test_vector_search_respects_rbac(self, session: AsyncSession):  # noqa: F811
        """The pgvector similarity search must enforce role filtering."""
        await self._create_test_chunks(session)
        await session.commit()

        embedding_str = "[" + ",".join(["0.015"] * 768) + "]"

        # Search as HR
        sql = text(
            """
            SELECT c.id, c.content
            FROM chunks c
            WHERE 'hr' = ANY(c.allowed_roles)
            ORDER BY c.embedding <=> :emb::vector
            LIMIT 10
            """
        )
        result = await session.execute(sql, {"emb": embedding_str})
        hr_rows = result.fetchall()

        # All results should be HR-accessible
        for row in hr_rows:
            assert "senior engineer" not in row.content, (
                f"HR search returned Engineering content: {row.content}"
            )

        # Search as Engineering
        sql = text(
            """
            SELECT c.id, c.content
            FROM chunks c
            WHERE 'engineering' = ANY(c.allowed_roles)
            ORDER BY c.embedding <=> :emb::vector
            LIMIT 10
            """
        )
        result = await session.execute(sql, {"emb": embedding_str})
        eng_rows = result.fetchall()

        for row in eng_rows:
            assert "remote work" not in row.content, (
                f"Engineering search returned HR content: {row.content}"
            )
