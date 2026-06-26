"""Add status, error, allowed_roles, and chunk_count columns to documents table.

Revision ID: 0002_add_document_status
Revises: None (initial migration — tables created by Base.metadata.create_all)
Create Date: 2026-06-22
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_add_document_status"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add columns for document status tracking."""
    op.add_column("documents", sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"))
    op.add_column("documents", sa.Column("error", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("allowed_roles", postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column("documents", sa.Column("chunk_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove the added columns."""
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "allowed_roles")
    op.drop_column("documents", "error")
    op.drop_column("documents", "status")
