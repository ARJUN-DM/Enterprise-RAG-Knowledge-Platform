"""Ollama LLM provider — runs local LLMs via the Ollama HTTP API.

Requires Ollama to be running (http://localhost:11434 by default).
"""

from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx

from app.providers.interfaces import LLMProvider


class OllamaLLMProvider(LLMProvider):
    """LLM provider backed by Ollama (local)."""

    def __init__(
        self, base_url: str = "http://localhost:11434", model: str = "llama3.2"
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self, prompt: str, system_prompt: str | None = None, **kwargs: object
    ) -> str:
        payload: dict[str, object] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self._base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("response", "")

    async def generate_stream(
        self, prompt: str, system_prompt: str | None = None, **kwargs: object
    ) -> AsyncGenerator[str, None]:
        payload: dict[str, object] = {
            "model": self._model,
            "prompt": prompt,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", f"{self._base_url}/api/generate", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
