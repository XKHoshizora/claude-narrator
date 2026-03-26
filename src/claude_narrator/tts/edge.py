"""Edge-TTS engine implementation."""

from __future__ import annotations

import logging

import edge_tts

from claude_narrator.tts.base import TTSEngine

logger = logging.getLogger(__name__)


async def _communicate_to_bytes(communicate: edge_tts.Communicate) -> bytes:
    """Collect edge-tts output into bytes."""
    chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)


class EdgeTTSEngine(TTSEngine):
    """TTS engine using Microsoft Edge TTS (free, high quality)."""

    VOICE_MAP = {
        "en": "en-US-AriaNeural",
        "zh": "zh-CN-XiaoxiaoNeural",
        "ja": "ja-JP-NanamiNeural",
    }

    def __init__(self, voice: str = "en-US-AriaNeural") -> None:
        self._voice = voice

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        """Synthesize text to MP3 bytes using edge-tts."""
        voice = self._voice
        if voice == "en-US-AriaNeural" and language != "en":
            voice = self.VOICE_MAP.get(language, voice)

        communicate = edge_tts.Communicate(text=text, voice=voice)
        return await _communicate_to_bytes(communicate)
