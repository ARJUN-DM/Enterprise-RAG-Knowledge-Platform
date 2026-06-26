"""Provider registry and factory functions.

Usage:
    llm = get_llm_provider()
    embedder = get_embedding_provider()
"""

from __future__ import annotations

from app.config import settings
from app.providers.interfaces import EmbeddingProvider, LLMProvider


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider based on settings.llm_provider."""
    provider_name = settings.llm_provider.lower()

    if provider_name == "gemini":
        from app.providers.llm.gemini import GeminiLLMProvider

        return GeminiLLMProvider(api_key=settings.gemini_api_key)
    elif provider_name == "ollama":
        from app.providers.llm.ollama import OllamaLLMProvider

        base_url = settings.ollama_base_url or "http://host.docker.internal:11434"
        return OllamaLLMProvider(base_url=base_url, model=settings.ollama_model or "llama3.2")
    elif provider_name == "openai":
        from app.providers.llm.openai import OpenAILLMProvider

        return OpenAILLMProvider(api_key=settings.openai_api_key)
    elif provider_name == "claude":
        from app.providers.llm.claude import ClaudeLLMProvider

        return ClaudeLLMProvider(api_key=settings.anthropic_api_key)
    elif provider_name == "vertex":
        from app.providers.llm.vertex import VertexLLMProvider

        return VertexLLMProvider()
    elif provider_name == "nvidia-nim":
        from app.providers.llm.nvidia_nim import NvidiaNimLLMProvider

        return NvidiaNimLLMProvider(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            model=settings.nvidia_model,
            max_tokens=settings.nvidia_max_tokens,
        )
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider_name!r}. "
            f"Supported: gemini, ollama, openai, claude, vertex, nvidia-nim"
        )


def get_embedding_provider() -> EmbeddingProvider:
    """Return the configured embedding provider based on settings.embedding_provider."""
    provider_name = settings.embedding_provider.lower()

    if provider_name == "gemini":
        from app.providers.embeddings.gemini import GeminiEmbeddingProvider

        return GeminiEmbeddingProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_embedding_model,
        )
    elif provider_name == "sentence-transformers":
        from app.providers.embeddings.sentence_transformers import (
            SentenceTransformersEmbeddingProvider,
        )

        return SentenceTransformersEmbeddingProvider()
    elif provider_name == "openai":
        from app.providers.embeddings.openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(api_key=settings.openai_api_key)
    elif provider_name == "vertex":
        from app.providers.embeddings.vertex import VertexEmbeddingProvider

        return VertexEmbeddingProvider()
    elif provider_name == "nvidia-nim":
        from app.providers.embeddings.nvidia_nim import NvidiaNimEmbeddingProvider

        return NvidiaNimEmbeddingProvider()
    else:
        raise ValueError(
            f"Unknown embedding provider: {provider_name!r}. "
            f"Supported: gemini, sentence-transformers, openai, vertex, nvidia-nim"
        )
