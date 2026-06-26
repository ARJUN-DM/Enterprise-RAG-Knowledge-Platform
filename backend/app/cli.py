#!/usr/bin/env python3
"""CLI tool to test provider connectivity.

Usage:
    python -m app.cli llm         # Test the configured LLM provider
    python -m app.cli embed       # Test the configured embedding provider
    python -m app.cli all         # Test both
"""

from __future__ import annotations

import argparse
import asyncio


async def test_llm() -> None:
    """Test the configured LLM provider with a simple prompt."""
    from app.config import settings
    from app.providers import get_llm_provider

    print(f"LLM provider: {settings.llm_provider}")
    provider = get_llm_provider()
    print(f"  Model: {provider.model_name}")
    print("  Sending test prompt...")

    response = await provider.generate(
        "What is Retrieval-Augmented Generation? Answer in one sentence."
    )
    print(f"  Response: {response[:300]}")
    print("  ✅ LLM provider OK")


async def test_embedding() -> None:
    """Test the configured embedding provider."""
    from app.config import settings
    from app.providers import get_embedding_provider

    print(f"Embedding provider: {settings.embedding_provider}")
    provider = get_embedding_provider()
    print(f"  Model: {provider.model_name}")
    print(f"  Dimensions: {provider.dimensions}")
    print("  Embedding test text...")

    vec = await provider.embed("Hello, world!")
    print(f"  Vector length: {len(vec)}")
    print(f"  First 5 values: {vec[:5]}")

    batch = await provider.embed_batch(["First text", "Second text", "Third text"])
    print(f"  Batch size: {len(batch)}")
    print(f"  Each vector length: {len(batch[0]) if batch else 0}")
    print("  ✅ Embedding provider OK")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test RAG platform providers")
    parser.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["llm", "embed", "all"],
        help="Which provider(s) to test (default: all)",
    )
    args = parser.parse_args()

    if args.target in ("llm", "all"):
        await test_llm()
        print()

    if args.target in ("embed", "all"):
        await test_embedding()


if __name__ == "__main__":
    asyncio.run(main())
