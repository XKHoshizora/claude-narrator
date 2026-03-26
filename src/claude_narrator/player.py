"""Audio player using pygame.mixer."""

from __future__ import annotations

import asyncio
import io
import logging
import os

# Suppress pygame welcome message
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Async audio player wrapping pygame.mixer."""

    def __init__(self) -> None:
        self._initialized = False
        self._init_mixer()

    def _init_mixer(self) -> None:
        try:
            pygame.mixer.init()
            self._initialized = True
        except pygame.error as e:
            logger.error("Failed to initialize audio mixer: %s", e)

    async def play(self, audio_data: bytes) -> None:
        """Play audio data (MP3 bytes). Blocks until playback starts."""
        if not self._initialized:
            return
        buf = io.BytesIO(audio_data)
        await asyncio.to_thread(self._play_sync, buf)

    def _play_sync(self, buf: io.BytesIO) -> None:
        try:
            pygame.mixer.music.load(buf)
            pygame.mixer.music.play()
        except pygame.error as e:
            logger.error("Playback error: %s", e)

    async def stop(self) -> None:
        """Stop current playback immediately."""
        if self._initialized:
            pygame.mixer.music.stop()

    @property
    def is_playing(self) -> bool:
        """Whether audio is currently playing."""
        if not self._initialized:
            return False
        return pygame.mixer.music.get_busy()

    async def wait_until_done(self) -> None:
        """Wait until current playback finishes."""
        while self.is_playing:
            await asyncio.sleep(0.1)

    def cleanup(self) -> None:
        """Release mixer resources."""
        if self._initialized:
            pygame.mixer.quit()
