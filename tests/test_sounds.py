from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

from claude_narrator.sounds import SoundEffects


class TestSoundEffects:
    def test_disabled_by_default(self, tmp_path):
        se = SoundEffects(config={}, config_dir=tmp_path)
        assert se._enabled is False

    def test_enabled_when_configured(self, tmp_path):
        config = {"sounds": {"enabled": True}}
        se = SoundEffects(config=config, config_dir=tmp_path)
        assert se._enabled is True

    def test_play_does_nothing_when_disabled(self, tmp_path):
        se = SoundEffects(config={}, config_dir=tmp_path)
        se.play("Stop")  # Should not raise

    def test_play_skips_unmapped_event(self, tmp_path):
        config = {"sounds": {"enabled": True, "events": {}}}
        se = SoundEffects(config=config, config_dir=tmp_path)
        se._initialized = True  # Skip pygame init
        se.play("UnknownEvent")  # Should not raise

    def test_play_skips_missing_file(self, tmp_path):
        config = {"sounds": {"enabled": True, "events": {"Stop": "complete.wav"}}}
        se = SoundEffects(config=config, config_dir=tmp_path)
        se._initialized = True
        se.play("Stop")  # File doesn't exist, should not raise
