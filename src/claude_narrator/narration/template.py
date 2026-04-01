"""Template-based narration: event -> text using i18n JSON templates."""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HIGH_PRIORITY_EVENTS = {
    "PostToolUseFailure", "Notification",
    "StopFailure", "PermissionRequest", "PermissionDenied",
}


def _shorten_path(path: str, max_parts: int = 3) -> str:
    """Shorten file path to last N components."""
    parts = Path(path).parts
    if len(parts) <= max_parts:
        return path
    return str(Path(*parts[-max_parts:]))


def _truncate(text: str, max_len: int = 80) -> str:
    """Truncate text to max length, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _extract_variables(event: dict[str, Any]) -> dict[str, str]:
    """Extract template variables from event data."""
    variables: dict[str, str] = {}
    variables["tool_name"] = event.get("tool_name", "unknown")
    from claude_narrator.tool_registry import get_display_name, get_tool_meta, parse_response as _parse_response
    variables["display_name"] = get_display_name(variables["tool_name"])
    variables["category"] = get_tool_meta(variables["tool_name"]).category.value

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
    if "threshold" in event:
        variables["threshold"] = str(event["threshold"])
    if "used_percentage" in event:
        variables["used_percentage"] = str(int(event["used_percentage"]))

    # Error fields (PostToolUseFailure, StopFailure)
    if "error" in event:
        err = event["error"]
        variables["error"] = _truncate(str(err))

    # Assistant message (Stop, StopFailure, SubagentStop)
    if "last_assistant_message" in event:
        variables["last_assistant_message"] = _truncate(
            str(event["last_assistant_message"])
        )

    # Agent fields (SubagentStart, SubagentStop, SessionStart)
    if "agent_type" in event:
        variables["agent_type"] = event["agent_type"]
    if "agent_id" in event:
        variables["agent_id"] = event["agent_id"]

    # Session fields
    if "source" in event:
        variables["source"] = event["source"]
    if "model" in event:
        variables["model"] = event["model"]

    # Compact fields
    if "compact_summary" in event:
        variables["compact_summary"] = _truncate(str(event["compact_summary"]))
    if "trigger" in event:
        variables["trigger"] = event["trigger"]

    # Notification fields
    if "notification_type" in event:
        variables["notification_type"] = event["notification_type"]
    if "title" in event:
        variables["title"] = event["title"]

    # Task fields (TaskCreated, TaskCompleted)
    if "task_subject" in event:
        variables["task_subject"] = _truncate(event["task_subject"], 60)
    if "teammate_name" in event:
        variables["teammate_name"] = event["teammate_name"]

    # Worktree fields
    if "name" in event:
        variables["name"] = event["name"]
    if "worktree_path" in event:
        variables["worktree_path"] = _shorten_path(event["worktree_path"])

    # CwdChanged fields
    if "old_cwd" in event:
        variables["old_cwd"] = _shorten_path(event["old_cwd"])
    if "new_cwd" in event:
        variables["new_cwd"] = _shorten_path(event["new_cwd"])

    # FileChanged fields
    if "file_path" not in variables and "file_path" in event:
        variables["file_path"] = _shorten_path(event["file_path"])
    if "event" in event:
        variables["file_event"] = event["event"]

    # PostToolUse result summary via registry
    if event.get("hook_event_name") == "PostToolUse" and "tool_response" in event:
        summary_vars = _parse_response(variables["tool_name"], event["tool_response"])
        variables.update(summary_vars)

    return variables


def _get_sub_key(event: dict[str, Any]) -> str:
    """Get the sub-key for template lookup. Falls back to tool_name."""
    event_name = event.get("hook_event_name", "")
    if event_name == "SessionStart":
        return event.get("source", "default")
    if event_name == "Notification":
        return event.get("notification_type", "default")
    return event.get("tool_name", "")


@dataclass
class PersonalityLayer:
    name: str
    prefixes: list[str] = field(default_factory=list)
    suffixes: list[str] = field(default_factory=list)
    templates: dict[str, Any] = field(default_factory=dict)


class TemplateNarrator:
    """Generate narration text from event using i18n templates."""

    def __init__(self, language: str = "en", personality: str | list[str] = "concise") -> None:
        # Normalize personality to list
        if isinstance(personality, str):
            personalities = [personality]
        else:
            personalities = list(personality)

        # Load base templates as fallback
        self._fallback = self._load_templates(language)

        # Load each personality as a layer
        self._layers: list[PersonalityLayer] = []
        for name in personalities:
            layer = self._load_personality(language, name)
            self._layers.append(layer)

        # Merge all prefixes and suffixes from all layers
        self._all_prefixes: list[str] = []
        self._all_suffixes: list[str] = []
        for layer in self._layers:
            self._all_prefixes.extend(layer.prefixes)
            self._all_suffixes.extend(layer.suffixes)

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

    def _load_personality(self, language: str, name: str) -> PersonalityLayer:
        if name == "concise":
            templates = self._load_templates(language)
            return PersonalityLayer(name="concise", templates=templates)

        try:
            ref = resources.files("claude_narrator.i18n").joinpath(f"{language}.{name}.json")
            data = json.loads(ref.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning("Failed to load %s.%s personality: %s", language, name, e)
            return PersonalityLayer(name=name)

        prefixes = data.pop("_prefixes", [])
        suffixes = data.pop("_suffixes", [])
        data.pop("_meta", None)

        # Special: tengu personality loads words from tengu_words.json
        if name == "tengu":
            prefixes = self._load_tengu_words()

        return PersonalityLayer(name=name, prefixes=prefixes, suffixes=suffixes, templates=data)

    def _load_tengu_words(self) -> list[str]:
        """Load tengu words: cached file > builtin snapshot."""
        # Check user cache first
        cached = Path.home() / ".claude-narrator" / "tengu_words.json"
        if cached.exists():
            try:
                words = json.loads(cached.read_text(encoding="utf-8"))
                if isinstance(words, list) and len(words) > 0:
                    return words
            except (json.JSONDecodeError, OSError):
                pass
        # Fallback to builtin
        try:
            ref = resources.files("claude_narrator.i18n").joinpath("tengu_words.json")
            return json.loads(ref.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def narrate(self, event: dict[str, Any]) -> str | None:
        """Generate narration text for an event. Returns None if no template."""
        # Handle coalesced events (preserve existing behavior)
        if event.get("_coalesced_count", 1) > 1:
            count = event["_coalesced_count"]
            tool = event.get("tool_name", "operations")
            return f"{count} {tool} operations"

        event_type = event.get("hook_event_name", "")
        sub_key = _get_sub_key(event)
        variables = _extract_variables(event)

        body = self._resolve_body(event_type, sub_key, variables)
        if body is None:
            return None

        prefix = self._pick_random(self._all_prefixes)
        suffix = self._pick_random(self._all_suffixes)
        return self._assemble(prefix, body, suffix)

    def _resolve_body(self, event_type: str, sub_key: str, variables: dict[str, str]) -> str | None:
        if event_type in HIGH_PRIORITY_EVENTS:
            # Longest template wins among all layers
            candidates: list[str] = []
            for layer in self._layers:
                text = self._render_from_layer(layer, event_type, sub_key, variables)
                if text:
                    candidates.append(text)
            # Also check fallback
            text = self._render_from_templates(self._fallback, event_type, sub_key, variables)
            if text:
                candidates.append(text)
            return max(candidates, key=len) if candidates else None
        else:
            # First match wins
            for layer in self._layers:
                text = self._render_from_layer(layer, event_type, sub_key, variables)
                if text:
                    return text
            # Fallback to base templates
            return self._render_from_templates(self._fallback, event_type, sub_key, variables)

    def _render_from_layer(self, layer: PersonalityLayer, event_type: str, sub_key: str, variables: dict) -> str | None:
        return self._render_from_templates(layer.templates, event_type, sub_key, variables)

    def _render_from_templates(self, templates: dict, event_type: str, sub_key: str, variables: dict) -> str | None:
        event_templates = templates.get(event_type)
        if not event_templates:
            return None
        template = event_templates.get(sub_key, event_templates.get("default"))
        if not template:
            return None
        try:
            return template.format_map(variables)
        except KeyError:
            return template

    @staticmethod
    def _pick_random(pool: list[str]) -> str | None:
        if not pool:
            return None
        return random.choice(pool)

    @staticmethod
    def _assemble(prefix: str | None, body: str, suffix: str | None) -> str:
        parts: list[str] = []
        if prefix:
            parts.append(f"{prefix}...")
        parts.append(body)
        if suffix:
            parts.append(suffix)
        return " ".join(parts)


# Built-in tengu words sourced from Claude Code v2.1.88 spinnerVerbs.ts (189 words).
# This URL is a third-party mirror kept as a supplementary update channel.
TENGU_GITHUB_URL = "https://raw.githubusercontent.com/levindixon/tengu_spinner_words/main/known-processing-words.json"


async def update_tengu_words(config_dir: Path) -> None:
    """Fetch latest tengu words from GitHub and cache locally. Silent on failure."""
    try:
        import httpx
    except ImportError:
        return
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(TENGU_GITHUB_URL, timeout=5.0)
            resp.raise_for_status()
            words = resp.json()
            if isinstance(words, list) and len(words) >= 10:
                config_dir.mkdir(parents=True, exist_ok=True)
                cache_file = config_dir / "tengu_words.json"
                cache_file.write_text(json.dumps(words, indent=2), encoding="utf-8")
                logger.info("Updated tengu words cache (%d words)", len(words))
    except Exception as e:
        logger.debug("Failed to update tengu words: %s", e)
