"""Abstract base class for TTS engines."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TTSEngine(ABC):
    """TTS engine that synthesizes text to audio bytes."""

    @abstractmethod
    async def synthesize(self, text: str, language: str = "en") -> bytes:
        """Synthesize text to audio bytes (MP3/WAV)."""

    @property
    def supports_streaming(self) -> bool:
        """Whether this engine supports streaming synthesis."""
        return False
