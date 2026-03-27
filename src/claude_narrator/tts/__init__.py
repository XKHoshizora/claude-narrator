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

    if engine_name == "say":
        from claude_narrator.tts.macos_say import MacOSSayEngine
        return MacOSSayEngine(voice=voice)

    if engine_name == "espeak":
        from claude_narrator.tts.espeak import EspeakEngine
        return EspeakEngine(voice=voice)

    if engine_name == "openai":
        from claude_narrator.tts.openai_tts import OpenAITTSEngine
        openai_cfg = tts_config.get("openai", {})
        return OpenAITTSEngine(
            voice=openai_cfg.get("voice", "nova"),
            model=openai_cfg.get("model", "tts-1"),
            api_key_env=openai_cfg.get("api_key_env", "OPENAI_API_KEY"),
        )

    # Fallback
    return EdgeTTSEngine(voice=voice)
