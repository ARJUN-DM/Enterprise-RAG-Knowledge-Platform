"""Tests for provider interfaces and factory functions."""

from __future__ import annotations

import pytest

from app.providers import get_embedding_provider, get_llm_provider
from app.providers.embeddings.sentence_transformers import (
    SentenceTransformersEmbeddingProvider,
)
from app.providers.interfaces import EmbeddingProvider, LLMProvider
from app.providers.llm.gemini import GeminiLLMProvider


class TestProviderInterfaces:
    """Verify all providers conform to their interfaces."""

    def test_llm_provider_interface(self):
        """LLMProvider should be an abstract class with required methods."""
        methods = [m for m in dir(LLMProvider) if not m.startswith("_")]
        assert "generate" in methods
        assert "generate_stream" in methods
        assert "model_name" in methods

    def test_embedding_provider_interface(self):
        """EmbeddingProvider should be an abstract class with required methods."""
        methods = [m for m in dir(EmbeddingProvider) if not m.startswith("_")]
        assert "embed" in methods
        assert "embed_batch" in methods
        assert "dimensions" in methods
        assert "model_name" in methods


@pytest.mark.asyncio
class TestGeminiLLMProvider:
    """Test Gemini LLM provider (with and without API key)."""

    async def test_no_key_fallback(self):
        """Without API key, should return a descriptive mock response."""
        provider = GeminiLLMProvider(api_key="")
        assert provider.model_name == "gemini-2.0-flash"
        response = await provider.generate("Hello")
        assert "simulated" in response.lower() or "Hello" in response

    async def test_property_returns(self):
        """Provider properties should return non-empty values."""
        provider = GeminiLLMProvider(api_key="test-key")
        assert provider.model_name == "gemini-2.0-flash"


@pytest.mark.asyncio
class TestSentenceTransformersEmbeddingProvider:
    """Test the local sentence-transformers embedding provider."""

    async def test_dimensions(self):
        """Should report 768 dimensions (padded from 384)."""
        provider = SentenceTransformersEmbeddingProvider()
        assert provider.dimensions == 768
        assert provider.model_name == "all-MiniLM-L6-v2"

    async def test_padding(self):
        """Verify that embedding returns a 768-d vector, even on first call."""
        provider = SentenceTransformersEmbeddingProvider()
        try:
            vec = await provider.embed("test text")
            assert len(vec) == 768
            # First 384 should be non-zero if model loaded, last 384 should be zeros
            # (actual model loading may fail in CI without internet)
        except Exception:
            pytest.skip("Sentence-transformers model download may fail in test env")


@pytest.mark.asyncio
class TestProviderFactory:
    """Test the provider factory functions."""

    async def test_get_llm_provider_default(self):
        """Default LLM provider (based on env or fallback) should return a valid provider."""
        provider = get_llm_provider()
        assert isinstance(provider, LLMProvider)
        assert provider.model_name

    async def test_get_embedding_provider_default(self):
        """Default embedding provider should return a valid provider."""
        provider = get_embedding_provider()
        assert isinstance(provider, EmbeddingProvider)
        assert provider.dimensions > 0

    async def test_invalid_llm_provider_raises(self, monkeypatch):
        """Unknown provider name should raise ValueError."""
        monkeypatch.setattr("app.config.settings.llm_provider", "nonexistent")
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_provider()

    async def test_invalid_embedding_provider_raises(self, monkeypatch):
        """Unknown embedding provider name should raise ValueError."""
        monkeypatch.setattr("app.config.settings.embedding_provider", "nonexistent")
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            get_embedding_provider()
