"""Gemini LLM provider implementation.

Uses the google-genai SDK. Falls back to a mock when API key is empty so the
app works without a paid key (returns a descriptive message).
"""

from __future__ import annotations

import traceback
from typing import Any, AsyncGenerator

from structlog import get_logger

from app.providers.interfaces import LLMProvider

logger = get_logger(__name__)


class GeminiLLMProvider(LLMProvider):
    """LLM provider backed by Google Gemini (google-genai SDK)."""

    def __init__(self, api_key: str = "", model: str = "gemini-2.0-flash") -> None:
        self._api_key = api_key
        self._model = model
        self._client = None
        if api_key:
            try:
                from google import genai

                self._client = genai.Client(api_key=api_key)
            except Exception as exc:
                logger.warning("gemini_client_init_failed", error=str(exc))
                self._client = None

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self, prompt: str, system_prompt: str | None = None, **kwargs: Any
    ) -> str:
        if not self._client:
            return (
                "I'm a simulated response. Set GEMINI_API_KEY in your .env "
                "to enable the real Gemini LLM. Your question was:\n\n" + prompt
            )

        try:
            from google.genai import types

            config = types.GenerateContentConfig() if not system_prompt else types.GenerateContentConfig(
                system_instruction=system_prompt,
            )

            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )
            if not response.text:
                logger.warning("gemini_empty_response", model=self._model)
                return "The model returned an empty response. Please try rephrasing your question."
            return response.text
        except Exception as exc:
            logger.error(
                "gemini_generate_failed",
                model=self._model,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            raise

    async def generate_stream(
        self, prompt: str, system_prompt: str | None = None, **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        if not self._client:
            yield (
                "I'm a simulated response. Set GEMINI_API_KEY in your .env "
                "to enable the real Gemini LLM."
            )
            return

        try:
            from google.genai import types

            config = types.GenerateContentConfig() if not system_prompt else types.GenerateContentConfig(
                system_instruction=system_prompt,
            )

            stream = self._client.models.generate_content_stream(
                model=self._model,
                contents=prompt,
                config=config,
            )
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            logger.error(
                "gemini_stream_failed",
                model=self._model,
                error=str(exc),
            )
            yield f"\n[Error during generation: {exc}]"
