"""LLM-based narration: send event to LLM for natural language generation."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

from claude_narrator.narration.template import TemplateNarrator

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a concise narrator for a coding assistant. "
    "Given a hook event JSON, generate a single short sentence (under 15 words) "
    "describing what is happening. Speak naturally, as if narrating to a developer. "
    "Only output the narration text, nothing else."
)


class LLMNarrator:
    """Generate narration using an LLM with template fallback."""

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "qwen2.5:3b",
        language: str = "en",
        timeout: float = 3.0,
    ) -> None:
        self._provider = provider
        self._model = model
        self._language = language
        self._timeout = timeout
        self._fallback = TemplateNarrator(language=language)
        self._recent_events: list[dict] = []

    def narrate(self, event: dict[str, Any]) -> str | None:
        """Synchronous wrapper — returns template result immediately.

        For async LLM narration, use narrate_async().
        The daemon should prefer narrate_async() when available.
        """
        return self._fallback.narrate(event)

    async def narrate_async(self, event: dict[str, Any]) -> str | None:
        """Generate narration via LLM, falling back to template on timeout."""
        self._recent_events.append(event)
        if len(self._recent_events) > 3:
            self._recent_events.pop(0)

        try:
            result = await asyncio.wait_for(
                self._call_llm(event), timeout=self._timeout
            )
            if result and result.strip():
                return result.strip()
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug("LLM narration failed (%s), using template fallback", e)

        return self._fallback.narrate(event)

    async def _call_llm(self, event: dict[str, Any]) -> str:
        prompt = (
            f"Language: {self._language}\n"
            f"Recent events: {json.dumps(self._recent_events[-3:], default=str)}\n"
            f"Current event: {json.dumps(event, default=str)}\n"
            f"Generate a single short narration sentence:"
        )

        if self._provider == "ollama":
            return await self._call_ollama(prompt)
        elif self._provider == "openai":
            return await self._call_openai(prompt)
        elif self._provider == "anthropic":
            return await self._call_anthropic(prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {self._provider}")

    async def _call_ollama(self, prompt: str) -> str:
        if httpx is None:
            raise ImportError("httpx is required for LLM narration")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "system": SYSTEM_PROMPT,
                    "stream": False,
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()["response"].strip()

    async def _call_openai(self, prompt: str) -> str:
        if httpx is None:
            raise ImportError("httpx is required for LLM narration")
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 50,
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    async def _call_anthropic(self, prompt: str) -> str:
        if httpx is None:
            raise ImportError("httpx is required for LLM narration")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": self._model,
                    "max_tokens": 50,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"].strip()
