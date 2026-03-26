"""TTS engine factory."""

from __future__ import annotations

from typing import Any

from claude_narrator.tts.base import TTSEngine
from claude_narrator.tts.edge import EdgeTTSEngine


def create_engine(config: dict[str, Any]) -> TTSEngine:
    """Create TTS engine from config."""
    tts_config = config.get("tts", {})
    engine_name = tts_config.get("engine", "edge-tts")
    voice = tts_config.get("voice", "en-US-AriaNeural")

    if engine_name == "edge-tts":
        return EdgeTTSEngine(voice=voice)

    # Fallback to edge-tts for unknown engines
    return EdgeTTSEngine(voice=voice)
