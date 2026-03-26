"""Template-based narration: event → text using i18n JSON templates."""

from __future__ import annotations

import json
import logging
from importlib import resources
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _shorten_path(path: str, max_parts: int = 3) -> str:
    """Shorten file path to last N components."""
    parts = Path(path).parts
    if len(parts) <= max_parts:
        return path
    return str(Path(*parts[-max_parts:]))


def _extract_variables(event: dict[str, Any]) -> dict[str, str]:
    """Extract template variables from event data."""
    variables: dict[str, str] = {}
    variables["tool_name"] = event.get("tool_name", "unknown")

    tool_input = event.get("tool_input", {})
    if isinstance(tool_input, dict):
        if "file_path" in tool_input:
            variables["file_path"] = _shorten_path(tool_input["file_path"])
        if "command" in tool_input:
            cmd = tool_input["command"]
            variables["command_short"] = cmd[:50] + "..." if len(cmd) > 50 else cmd
        if "pattern" in tool_input:
            variables["pattern"] = tool_input["pattern"]

    if "reason" in event:
        variables["reason"] = event["reason"]
    if "message" in event:
        variables["message"] = event["message"]

    return variables


class TemplateNarrator:
    """Generate narration text from event using i18n templates."""

    def __init__(self, language: str = "en") -> None:
        self._templates = self._load_templates(language)

    def _load_templates(self, language: str) -> dict[str, Any]:
        """Load i18n template file."""
        try:
            ref = resources.files("claude_narrator.i18n").joinpath(f"{language}.json")
            return json.loads(ref.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning("Failed to load %s templates: %s. Falling back to en.", language, e)
            if language != "en":
                return self._load_templates("en")
            return {}

    def narrate(self, event: dict[str, Any]) -> str | None:
        """Generate narration text for an event. Returns None if no template."""
        event_type = event.get("hook_event_name", "")
        templates = self._templates.get(event_type)
        if not templates:
            return None

        tool_name = event.get("tool_name", "")
        template = templates.get(tool_name, templates.get("default"))
        if not template:
            return None

        variables = _extract_variables(event)
        try:
            return template.format_map(variables)
        except KeyError:
            return template  # Return template as-is if variables missing
