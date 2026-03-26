import json
from pathlib import Path

import pytest

from claude_narrator.config import (
    DEFAULT_CONFIG,
    load_config,
    deep_merge,
    validate_config,
)


class TestDefaultConfig:
    def test_has_general_section(self):
        assert "general" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["general"]["verbosity"] == "normal"
        assert DEFAULT_CONFIG["general"]["language"] == "en"
        assert DEFAULT_CONFIG["general"]["enabled"] is True

    def test_has_tts_section(self):
        assert DEFAULT_CONFIG["tts"]["engine"] == "edge-tts"
        assert DEFAULT_CONFIG["tts"]["voice"] == "en-US-AriaNeural"

    def test_has_narration_section(self):
        assert DEFAULT_CONFIG["narration"]["mode"] == "template"
        assert DEFAULT_CONFIG["narration"]["max_queue_size"] == 5
        assert DEFAULT_CONFIG["narration"]["max_narration_seconds"] == 15
        assert DEFAULT_CONFIG["narration"]["skip_rapid_events"] is True


class TestDeepMerge:
    def test_shallow_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        assert deep_merge(base, override) == {"a": 1, "b": 3}

    def test_nested_override(self):
        base = {"general": {"verbosity": "normal", "language": "en"}}
        override = {"general": {"verbosity": "verbose"}}
        result = deep_merge(base, override)
        assert result["general"]["verbosity"] == "verbose"
        assert result["general"]["language"] == "en"

    def test_add_new_key(self):
        base = {"a": 1}
        override = {"b": 2}
        assert deep_merge(base, override) == {"a": 1, "b": 2}


class TestValidateConfig:
    def test_valid_verbosity(self):
        config = deep_merge(DEFAULT_CONFIG, {"general": {"verbosity": "minimal"}})
        result = validate_config(config)
        assert result["general"]["verbosity"] == "minimal"

    def test_invalid_verbosity_falls_back(self):
        config = deep_merge(DEFAULT_CONFIG, {"general": {"verbosity": "invalid"}})
        result = validate_config(config)
        assert result["general"]["verbosity"] == "normal"

    def test_invalid_engine_falls_back(self):
        config = deep_merge(DEFAULT_CONFIG, {"tts": {"engine": "nonexistent"}})
        result = validate_config(config)
        assert result["tts"]["engine"] == "edge-tts"

    def test_invalid_language_falls_back(self):
        config = deep_merge(DEFAULT_CONFIG, {"general": {"language": "xx"}})
        result = validate_config(config)
        assert result["general"]["language"] == "en"

    def test_valid_language_zh(self):
        config = deep_merge(DEFAULT_CONFIG, {"general": {"language": "zh"}})
        result = validate_config(config)
        assert result["general"]["language"] == "zh"


class TestLoadConfig:
    def test_load_default_when_no_file(self, tmp_config_dir):
        result = load_config(config_dir=tmp_config_dir)
        assert result == validate_config(DEFAULT_CONFIG)

    def test_load_user_overrides(self, tmp_config_dir):
        config_file = tmp_config_dir / "config.json"
        config_file.write_text(json.dumps({"general": {"verbosity": "verbose"}}))
        result = load_config(config_dir=tmp_config_dir)
        assert result["general"]["verbosity"] == "verbose"
        assert result["general"]["language"] == "en"  # default preserved

    def test_load_malformed_json_falls_back(self, tmp_config_dir):
        config_file = tmp_config_dir / "config.json"
        config_file.write_text("not valid json{{{")
        result = load_config(config_dir=tmp_config_dir)
        assert result == validate_config(DEFAULT_CONFIG)
