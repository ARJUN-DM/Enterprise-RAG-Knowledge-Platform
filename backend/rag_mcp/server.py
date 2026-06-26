"""MCP server exposing RBAC-aware document search and retrieval tools.

Uses the Python MCP SDK to implement the Model Context Protocol.
Connects to the same PostgreSQL database as the main API.

Run:
    python -m rag_mcp

Or via Docker (see Dockerfile.mcp).
"""

from __future__ import annotations

import json
import uuid

from structlog import get_logger

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from app.config import settings
from app.observability.logging import configure_logging
from app.providers import get_embedding_provider

logger = get_logger()

server = Server("rag-platform-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="search_documents",
            description="Search documents by semantic similarity with RBAC filtering. Only returns chunks the specified role is allowed to see.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "role": {
                        "type": "string",
                        "description": "User role (hr, engineering, admin)",
                        "enum": ["hr", "engineering", "admin"],
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (max 50)",
                        "default": 5,
                    },
                },
                "required": ["query", "role"],
            },
        ),
        Tool(
            name="get_document",
            description="Get a document's details and chunks with RBAC enforcement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document UUID",
                    },
                    "role": {
                        "type": "string",
                        "description": "User role (hr, engineering, admin)",
                        "enum": ["hr", "engineering", "admin"],
                    },
                },
                "required": ["document_id", "role"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a tool call."""
    if name == "search_documents":
        return await _search_documents(arguments)
    elif name == "get_document":
        return await _get_document(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def _search_documents(args: dict) -> list[TextContent]:
    """Search documents by semantic similarity with RBAC filtering."""
    query = args["query"]
    role = args["role"].strip().lower()
    top_k = min(int(args.get("top_k", 5)), 50)

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    embedder = get_embedding_provider()
    query_embedding = await embedder.embed(query)
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    results = []
    async with session_factory() as db:
        sql = text(
            """
            SELECT
                c.id, c.content, c.meta_data,
                d.name AS document_name, d.id AS document_id,
                1 - (c.embedding <=> :embedding::vector) AS similarity
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.embedding IS NOT NULL
              AND :role = ANY(c.allowed_roles)
            ORDER BY c.embedding <=> :embedding::vector
            LIMIT :top_k
            """
        )
        result = await db.execute(sql, {"embedding": embedding_str, "role": role, "top_k": top_k})
        for row in result.fetchall():
            meta = row.meta_data or {}
            results.append({
                "chunk_id": str(row.id),
                "document_id": str(row.document_id),
                "document_name": row.document_name,
                "content": row.content[:500],
                "section": meta.get("section_heading", ""),
                "similarity": round(float(row.similarity), 4),
            })

    await engine.dispose()

    return [TextContent(type="text", text=json.dumps(results, indent=2))]


async def _get_document(args: dict) -> list[TextContent]:
    """Get a document by ID with RBAC enforcement."""
    document_id = args["document_id"]
    role = args["role"].strip().lower()

    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        # Get document metadata
        from app.db.models import Document  # noqa: F811

        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            await engine.dispose()
            return [TextContent(type="text", text=json.dumps({"error": "Document not found"}, indent=2))]

        # Get chunks with RBAC filter
        sql = text(
            """
            SELECT id, content, meta_data, allowed_roles
            FROM chunks
            WHERE document_id = :doc_id
              AND :role = ANY(allowed_roles)
            ORDER BY created_at
            """
        )
        chunk_result = await db.execute(sql, {"doc_id": document_id, "role": role})
        chunks = []
        for row in chunk_result.fetchall():
            meta = row.meta_data or {}
            chunks.append({
                "chunk_id": str(row.id),
                "content": row.content,
                "section": meta.get("section_heading", ""),
            })

    await engine.dispose()

    return [TextContent(
        type="text",
        text=json.dumps({
            "document_id": document_id,
            "name": doc.name,
            "uploaded_by": doc.uploaded_by_role,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "accessible_chunks": len(chunks),
            "chunks": chunks,
        }, indent=2),
    )]


async def main() -> None:
    """Run the MCP server via stdio transport."""
    configure_logging()
    logger.info("mcp_server_starting", model="rag-platform")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
