"""Authentication and authorization module.

Uses a simple X-User-Role header for v1 (persona-based).
Structured so JWT/OAuth can replace it without changing business logic.
"""

from __future__ import annotations
