"""RAG query pipeline.

Handles: embed → role-filtered vector search → re-rank → grounded prompt → LLM → cited answer.
"""

from __future__ import annotations
