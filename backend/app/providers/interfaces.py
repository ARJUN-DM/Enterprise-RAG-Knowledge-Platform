from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface for Large Language Model providers.

    Implementations: Gemini, Claude, OpenAI, Vertex AI, Nvidia NIM.

    All implementations accept an optional *history* parameter for
    multi-turn conversation memory.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[dict[str, str]] | None = None,
        **kwargs: object,
    ) -> str:
        """Send a prompt to the LLM and return the generated response.

        Args:
            prompt: The current user question / prompt.
            system_prompt: Optional system instruction.
            history: Optional list of prior turns
                [{"role": "user"|"assistant", "content": "..."}] (most recent last).
                The caller should limit to ~6 messages (3 turns) to control tokens.
        """
        ...

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[dict[str, str]] | None = None,
        **kwargs: object,
    ):
        """Send a prompt and stream the response chunks.

        Yields str chunks as they arrive.

        Args:
            prompt: The current user question / prompt.
            system_prompt: Optional system instruction.
            history: Optional list of prior turns
                [{"role": "user"|"assistant", "content": "..."}] (most recent last).
        """
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier string (e.g. 'gemini-2.0-flash')."""
        ...


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding providers.

    Implementations: Gemini, sentence-transformers, OpenAI, Vertex AI, Nvidia NIM.
    """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text string."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of text strings."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the dimensionality of the embedding vectors."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier string."""
        ...
