"""Anthropic Claude LLM provider adapter.

Uses the anthropic Python SDK.
"""

from __future__ import annotations

from typing import AsyncGenerator

from anthropic import AsyncAnthropic

from app.providers.interfaces import LLMProvider


class ClaudeLLMProvider(LLMProvider):
    """LLM provider backed by Anthropic Claude."""

    def __init__(
        self, api_key: str = "", model: str = "claude-sonnet-4-20250514"
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = AsyncAnthropic(api_key=api_key) if api_key else None

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self, prompt: str, system_prompt: str | None = None, **kwargs: object
    ) -> str:
        if not self._client:
            return (
                "Claude provider: set ANTHROPIC_API_KEY in your .env to enable. "
                "Your question was:\n\n" + prompt
            )

        response = await self._client.messages.create(
            model=self._model,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        )
        return response.content[0].text if response.content else ""

    async def generate_stream(
        self, prompt: str, system_prompt: str | None = None, **kwargs: object
    ) -> AsyncGenerator[str, None]:
        if not self._client:
            yield (
                "Claude provider: set ANTHROPIC_API_KEY in your .env to enable."
            )
            return

        async with self._client.messages.stream(
            model=self._model,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        ) as stream:
            async for text in stream.text_stream:
                yield text
