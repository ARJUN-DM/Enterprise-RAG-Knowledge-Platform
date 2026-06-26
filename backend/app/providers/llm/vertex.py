"""Vertex AI LLM provider stub.

Demonstrates the Vertex AI / GCP path. Requires GCP credentials and
google-cloud-aiplatform. Not active without additional setup.
"""

from __future__ import annotations

from typing import AsyncGenerator

from app.providers.interfaces import LLMProvider


class VertexLLMProvider(LLMProvider):
    """LLM provider backed by Vertex AI (GCP). Stub — not active without GCP setup."""

    def __init__(self, model: str = "gemini-2.0-flash-001") -> None:
        self._model = model
        self._available = False
        try:
            import vertexai  # noqa: F401

            self._available = True
        except ImportError:
            pass

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self, prompt: str, system_prompt: str | None = None, **kwargs: object
    ) -> str:
        if not self._available:
            return (
                "Vertex AI provider requires GCP setup. Install google-cloud-aiplatform "
                "and configure GCP credentials. See docs/gcp-migration.md."
            )
        # Real implementation would use vertexai.generative_models
        msg = (
            "Vertex AI Gemini response (stub). Replace with real SDK calls. "
            "Your question was:\n\n" + prompt
        )
        return msg

    async def generate_stream(
        self, prompt: str, system_prompt: str | None = None, **kwargs: object
    ) -> AsyncGenerator[str, None]:
        if not self._available:
            yield (
                "Vertex AI provider requires GCP setup. See docs/gcp-migration.md."
            )
            return
        yield (
            "Vertex AI Gemini response (stub). Replace with real SDK calls."
        )
