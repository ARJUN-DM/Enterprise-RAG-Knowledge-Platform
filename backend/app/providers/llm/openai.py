"""OpenAI LLM provider adapter.

Uses the OpenAI Python SDK. Works with any OpenAI-compatible endpoint
(e.g., OpenAI API, Azure, local proxies).
"""

from __future__ import annotations

from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.providers.interfaces import LLMProvider


class OpenAILLMProvider(LLMProvider):
    """LLM provider backed by OpenAI or any OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url) if api_key else None  # type: ignore[arg-type]

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self, prompt: str, system_prompt: str | None = None, **kwargs: object
    ) -> str:
        if not self._client:
            return (
                "OpenAI provider: set OPENAI_API_KEY in your .env to enable. "
                "Your question was:\n\n" + prompt
            )

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    async def generate_stream(
        self, prompt: str, system_prompt: str | None = None, **kwargs: object
    ) -> AsyncGenerator[str, None]:
        if not self._client:
            yield (
                "OpenAI provider: set OPENAI_API_KEY in your .env to enable."
            )
            return

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
