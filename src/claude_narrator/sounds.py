"""Sound effects playback for event types."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Suppress pygame welcome message
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


class SoundEffects:
    """Play short sound effects for event types."""

    def __init__(self, config: dict[str, Any], config_dir: Path) -> None:
        self._enabled = config.get("sounds", {}).get("enabled", False)
        self._sound_dir = Path(
            config.get("sounds", {}).get("directory", str(config_dir / "sounds"))
        )
        self._event_sounds: dict[str, str] = config.get("sounds", {}).get("events", {
            "Stop": "complete.wav",
            "Notification": "alert.wav",
            "PostToolUseFailure": "error.wav",
        })
        self._initialized = False

    def _ensure_init(self) -> bool:
        if not self._enabled:
            return False
        if not self._initialized:
            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                self._initialized = True
            except Exception as e:
                logger.debug("Sound effects init failed: %s", e)
                return False
        return True

    def play(self, event_name: str) -> None:
        """Play sound effect for an event type if configured."""
        if not self._ensure_init():
            return

        sound_file = self._event_sounds.get(event_name)
        if not sound_file:
            return

        sound_path = self._sound_dir / sound_file
        if not sound_path.exists():
            logger.debug("Sound file not found: %s", sound_path)
            return

        try:
            import pygame
            sound = pygame.mixer.Sound(str(sound_path))
            sound.play()
        except Exception as e:
            logger.debug("Sound effect playback error: %s", e)
