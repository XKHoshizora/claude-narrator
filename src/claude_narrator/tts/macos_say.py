"""macOS 'say' command TTS engine."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from claude_narrator.tts.base import TTSEngine


class MacOSSayEngine(TTSEngine):
    """TTS using macOS built-in 'say' command."""

    VOICE_MAP = {"en": "Samantha", "zh": "Ting-Ting", "ja": "Kyoko"}

    def __init__(self, voice: str = "Samantha") -> None:
        self._voice = voice

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        voice = self._voice
        if voice == "Samantha" and language != "en":
            voice = self.VOICE_MAP.get(language, voice)

        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as f:
            tmp_path = Path(f.name)

        try:
            proc = await asyncio.create_subprocess_exec(
                "say", "-v", voice, "-o", str(tmp_path), text,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()
            if tmp_path.exists():
                return tmp_path.read_bytes()
            return b""
        finally:
            tmp_path.unlink(missing_ok=True)
