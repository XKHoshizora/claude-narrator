"""Custom event filter rules from config."""

from __future__ import annotations

from fnmatch import fnmatch
from typing import Any


def apply_filters(
    event: dict[str, Any],
    filters: dict[str, Any],
) -> tuple[bool, str | None]:
    """Apply custom filter rules.

    Returns (should_narrate, verbosity_override).
    should_narrate=False means skip this event entirely.
    verbosity_override is a string like "minimal" or None.
    """
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    # Check ignore_tools
    ignore_tools = filters.get("ignore_tools", [])
    if tool_name and tool_name in ignore_tools:
        return False, None

    # Check only_tools (whitelist)
    only_tools = filters.get("only_tools")
    if only_tools is not None and tool_name and tool_name not in only_tools:
        return False, None

    # Check ignore_paths
    file_path = ""
    if isinstance(tool_input, dict):
        file_path = tool_input.get("file_path", "")
    for pattern in filters.get("ignore_paths", []):
        if file_path and fnmatch(file_path, pattern):
            return False, None

    # Check custom_rules
    for rule in filters.get("custom_rules", []):
        match = rule.get("match", {})
        if _matches_rule(event, match):
            action = rule.get("action", "")
            if action == "skip":
                return False, None
            elif action == "force_verbosity":
                return True, rule.get("value")

    return True, None


def _matches_rule(event: dict[str, Any], match: dict[str, Any]) -> bool:
    """Check if an event matches a rule's match criteria."""
    if "tool" in match and event.get("tool_name") != match["tool"]:
        return False
    if "event" in match and event.get("hook_event_name") != match["event"]:
        return False
    if "input_contains" in match:
        tool_input = event.get("tool_input", {})
        input_str = str(tool_input) if isinstance(tool_input, dict) else str(tool_input)
        if match["input_contains"] not in input_str:
            return False
    return True
