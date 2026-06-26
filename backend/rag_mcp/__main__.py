"""Entry point for running the MCP server as a module.

    python -m rag_mcp

Runs with stdio transport for MCP protocol compatibility.
"""

from __future__ import annotations

import asyncio

from rag_mcp.server import main

asyncio.run(main())
