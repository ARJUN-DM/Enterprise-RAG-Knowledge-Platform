"""Nvidia NIM LLM provider (OpenAI-compatible).

Uses the OpenAI SDK to call NVIDIA's hosted, OpenAI-compatible Chat Completions API.
Default endpoint: https://integrate.api.nvidia.com/v1
Default model: meta/llama-3.3-70b-instruct

Key behaviours:
- Raises a clear error if the API key is missing (no silent stub fallback).
- Transient errors (429 / 5xx) are retried with exponential backoff.
- NEVER raises on empty content — falls back to reasoning_content, then empty string.
- Accepts optional history for multi-turn conversation memory.
"""

from __future__ import annotations

import asyncio
import traceback
from typing import AsyncGenerator

from openai import AsyncOpenAI
from structlog import get_logger

from app.providers.interfaces import LLMProvider

logger = get_logger(__name__)

MAX_RETRIES = 3
BASE_RETRY_DELAY_S = 1.0


class NvidiaNimLLMProvider(LLMProvider):
    """LLM provider backed by NVIDIA's hosted OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://integrate.api.nvidia.com/v1",
        model: str = "meta/llama-3.3-70b-instruct",
        max_tokens: int = 2048,
    ) -> None:
        if not api_key:
            raise RuntimeError(
                "NVIDIA_API_KEY is not set. "
                "Get your key from https://build.nvidia.com/ and set NVIDIA_API_KEY in your .env file."
            )
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_tokens = max_tokens
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[dict[str, str]] | None = None,
        **kwargs: object,
    ) -> str:
        """Send a prompt and return the generated response.

        Supports multi-turn conversation via the *history* parameter:
        - history: list of {"role": "user"|"assistant", "content": "..."} turns
          (most recent last, max 6 messages enforced upstream).

        Never raises on empty content — falls back to reasoning_content,
        then returns empty string (the pipeline provides a friendly fallback).
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    max_tokens=self._max_tokens,
                )

                if not response.choices or len(response.choices) == 0:
                    logger.warning(
                        "nvidia_generate_no_choices",
                        model=self._model,
                        attempt=attempt,
                        max_retries=MAX_RETRIES,
                    )
                    # Retry on early attempts; on last attempt return empty
                    # string so the pipeline's friendly fallback handles it.
                    if attempt < MAX_RETRIES:
                        raise RuntimeError("NVIDIA model returned no choices")
                    logger.warning(
                        "nvidia_generate_no_choices_final",
                        model=self._model,
                    )
                    return ""

                message = response.choices[0].message
                content = message.content

                if content is None or content.strip() == "":
                    # MiniMax M3 is a reasoning model that may put output in
                    # the hidden reasoning channel. Try to recover it.
                    reasoning: str | None = (
                        getattr(message, "reasoning_content", None)
                        or (message.model_extra or {}).get("reasoning_content")
                    )
                    if reasoning and reasoning.strip():
                        logger.warning(
                            "nvidia_generate_used_reasoning",
                            model=self._model,
                            reason_len=len(reasoning),
                        )
                        return reasoning

                    # Both visible content AND reasoning are empty — return
                    # empty string (pipeline provides a friendly fallback).
                    logger.warning(
                        "nvidia_generate_empty_content",
                        model=self._model,
                    )
                    return ""

                return content

            except Exception as exc:
                last_exc = exc
                if _is_transient(exc) and attempt < MAX_RETRIES:
                    delay = BASE_RETRY_DELAY_S * (2 ** (attempt - 1))
                    logger.warning(
                        "nvidia_generate_retry",
                        model=self._model,
                        attempt=attempt,
                        max_retries=MAX_RETRIES,
                        delay_s=delay,
                        error=str(exc),
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "nvidia_generate_failed",
                        model=self._model,
                        error=str(exc),
                        attempt=attempt,
                        traceback=traceback.format_exc(),
                    )
                    raise

        # Defensive — should not reach here
        raise RuntimeError(
            f"NVIDIA generate failed after {MAX_RETRIES} retries: {last_exc}"
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[dict[str, str]] | None = None,
        **kwargs: object,
    ) -> AsyncGenerator[str, None]:
        """Send a prompt and stream the response chunks.

        Supports multi-turn conversation via *history* (same as generate()).
        Falls back to reasoning_content when visible content is empty.
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                stream = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    max_tokens=self._max_tokens,
                    stream=True,
                )

                # Track if we yielded any content
                yielded_content = False

                async for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta:
                            # Primary: visible content
                            if delta.content:
                                yielded_content = True
                                yield delta.content
                            # Fallback: reasoning content
                            else:
                                reasoning = getattr(delta, "reasoning_content", None)
                                if reasoning:
                                    yielded_content = True
                                    yield reasoning

                if not yielded_content:
                    logger.warning(
                        "nvidia_stream_no_content",
                        model=self._model,
                    )

                # Success — exit the retry loop
                return

            except Exception as exc:
                last_exc = exc
                if _is_transient(exc) and attempt < MAX_RETRIES:
                    delay = BASE_RETRY_DELAY_S * (2 ** (attempt - 1))
                    logger.warning(
                        "nvidia_generate_stream_retry",
                        model=self._model,
                        attempt=attempt,
                        max_retries=MAX_RETRIES,
                        delay_s=delay,
                        error=str(exc),
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "nvidia_generate_stream_failed",
                        model=self._model,
                        error=str(exc),
                        attempt=attempt,
                        traceback=traceback.format_exc(),
                    )
                    raise

        # Defensive — should not reach here
        raise RuntimeError(
            f"NVIDIA generate_stream failed after {MAX_RETRIES} retries: {last_exc}"
        )


def _is_transient(exc: Exception) -> bool:
    """Return True if *exc* looks like a transient API error (429 / 5xx)."""
    msg = str(exc).lower()
    for pattern in ("429", "503", "500", "502", "resource_exhausted", "unavailable",
                    "rate limit", "too many requests", "internal server error",
                    "service unavailable", "bad gateway", "no choices"):
        if pattern in msg:
            return True
    return False
