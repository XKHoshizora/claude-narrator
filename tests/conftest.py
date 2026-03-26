"""Shared test fixtures for claude-narrator."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_config_dir(tmp_path):
    """Temporary config directory replacing ~/.claude-narrator/."""
    config_dir = tmp_path / ".claude-narrator"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def tmp_claude_dir(tmp_path):
    """Temporary ~/.claude/ directory for settings.json."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    return claude_dir
