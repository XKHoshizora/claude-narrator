"""OpenAI TTS API engine."""

from __future__ import annotations

import os

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

from claude_narrator.tts.base import TTSEngine


class OpenAITTSEngine(TTSEngine):
    """TTS using OpenAI's text-to-speech API."""

    def __init__(
        self,
        voice: str = "nova",
        model: str = "tts-1",
        api_key_env: str = "OPENAI_API_KEY",
    ) -> None:
        self._voice = voice
        self._model = model
        self._api_key = os.environ.get(api_key_env, "")

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        if not _HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for OpenAI TTS. Install with: pip install httpx"
            )

        if not self._api_key:
            raise ValueError("OPENAI_API_KEY not set")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "input": text,
                    "voice": self._voice,
                    "response_format": "mp3",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.content
