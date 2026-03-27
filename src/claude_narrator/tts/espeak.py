"""espeak-ng TTS engine for Linux."""

from __future__ import annotations

import asyncio

from claude_narrator.tts.base import TTSEngine


class EspeakEngine(TTSEngine):
    """TTS using espeak-ng (Linux offline TTS)."""

    VOICE_MAP = {"en": "en", "zh": "zh", "ja": "ja"}

    def __init__(self, voice: str = "en") -> None:
        self._voice = voice

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        voice = self.VOICE_MAP.get(language, self._voice)
        proc = await asyncio.create_subprocess_exec(
            "espeak-ng", "--stdout", "-v", voice, text,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        return stdout or b""
