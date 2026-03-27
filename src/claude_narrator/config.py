"""Configuration loading, validation, and defaults."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".claude-narrator"
VALID_VERBOSITIES = ("minimal", "normal", "verbose")
VALID_ENGINES = ("edge-tts", "say", "espeak", "openai")
VALID_LANGUAGES = ("en", "zh", "ja")
VALID_MODES = ("template", "llm")

DEFAULT_CONFIG: dict[str, Any] = {
    "general": {
        "verbosity": "normal",
        "language": "en",
        "enabled": True,
    },
    "tts": {
        "engine": "edge-tts",
        "voice": "en-US-AriaNeural",
        "openai": {
            "api_key_env": "OPENAI_API_KEY",
            "model": "tts-1",
            "voice": "nova",
        },
    },
    "narration": {
        "mode": "template",
        "max_queue_size": 5,
        "max_narration_seconds": 15,
        "skip_rapid_events": True,
        "llm": {
            "provider": "ollama",
            "model": "qwen2.5:3b",
        },
    },
    "cache": {
        "enabled": True,
        "max_size_mb": 50,
    },
    "filters": {
        "ignore_tools": [],
        "ignore_paths": [],
        "only_tools": None,
        "custom_rules": [],
    },
    "web": {
        "enabled": False,
        "host": "127.0.0.1",
        "port": 19822,
    },
}


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base. Returns new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate config values; invalid values fall back to defaults."""
    result = json.loads(json.dumps(config))  # deep copy

    general = result.get("general", {})
    if general.get("verbosity") not in VALID_VERBOSITIES:
        general["verbosity"] = DEFAULT_CONFIG["general"]["verbosity"]
    if general.get("language") not in VALID_LANGUAGES:
        general["language"] = DEFAULT_CONFIG["general"]["language"]
    result["general"] = general

    tts = result.get("tts", {})
    if tts.get("engine") not in VALID_ENGINES:
        tts["engine"] = DEFAULT_CONFIG["tts"]["engine"]
    result["tts"] = tts

    narration = result.get("narration", {})
    if narration.get("mode") not in VALID_MODES:
        narration["mode"] = DEFAULT_CONFIG["narration"]["mode"]
    result["narration"] = narration

    return result


def load_config(config_dir: Path | None = None) -> dict[str, Any]:
    """Load config from disk, merge with defaults, validate."""
    config_dir = config_dir or CONFIG_DIR
    config_file = config_dir / "config.json"

    if config_file.exists():
        try:
            user_config = json.loads(config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load config: %s. Using defaults.", e)
            user_config = {}
    else:
        user_config = {}

    merged = deep_merge(DEFAULT_CONFIG, user_config)
    return validate_config(merged)
