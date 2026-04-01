"""Verbosity-based event filtering."""

from __future__ import annotations

MINIMAL_EVENTS = {
    "Stop", "Notification", "PostToolUseFailure", "ContextThreshold",
    "StopFailure", "PermissionDenied", "PermissionRequest",
}
NORMAL_EVENTS = MINIMAL_EVENTS | {
    "SubagentStart", "SubagentStop",
    "SessionStart", "SessionEnd",
    "PostCompact", "TaskCreated", "TaskCompleted",
}
NORMAL_TOOLS = {"Read", "Write", "Edit", "Glob", "Grep", "Agent"}


def should_narrate(event_name: str, tool_name: str | None, verbosity: str) -> bool:
    """Decide whether to narrate this event given the verbosity level."""
    if verbosity == "verbose":
        return True
    if event_name in MINIMAL_EVENTS:
        return True
    if verbosity == "minimal":
        return False
    # verbosity == "normal"
    if event_name in NORMAL_EVENTS:
        return True
    if event_name in ("PreToolUse", "PostToolUse") and tool_name in NORMAL_TOOLS:
        return True
    return False
