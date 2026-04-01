"""Install/uninstall narrator hooks into Claude Code settings.json."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CLAUDE_DIR = Path.home() / ".claude"
NARRATOR_MARKER = "claude_narrator.hooks.on_event"

HOOK_EVENTS = [
    # Existing
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "Stop",
    "Notification",
    "SubagentStart",
    "SubagentStop",
    "SessionStart",
    "PreCompact",
    # Tier 1 additions
    "StopFailure",
    "PostCompact",
    "SessionEnd",
    "TaskCreated",
    "TaskCompleted",
    "PermissionDenied",
    "PermissionRequest",
    # Tier 2 additions
    "WorktreeCreate",
    "WorktreeRemove",
    "CwdChanged",
    "FileChanged",
]


def _get_python_path() -> str:
    """Get the Python interpreter path where claude_narrator is installed."""
    return sys.executable


def _make_hook_entry(python_path: str) -> dict[str, Any]:
    """Create a single hook entry for narrator."""
    return {
        "matcher": "*",
        "hooks": [
            {
                "type": "command",
                "command": f"{python_path} -m {NARRATOR_MARKER}",
                "timeout": 5,
            }
        ],
    }


def install_hooks(claude_dir: Path | None = None) -> None:
    """Inject narrator hooks into ~/.claude/settings.json."""
    claude_dir = claude_dir or CLAUDE_DIR
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_file = claude_dir / "settings.json"

    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            settings = {}
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    python_path = _get_python_path()
    entry = _make_hook_entry(python_path)

    for event in HOOK_EVENTS:
        event_hooks = hooks.setdefault(event, [])
        # Don't add duplicate
        already = any(
            NARRATOR_MARKER in h.get("command", "")
            for group in event_hooks
            for h in group.get("hooks", [])
        )
        if not already:
            event_hooks.append(entry)

    settings["hooks"] = hooks
    settings_file.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Hooks installed to %s", settings_file)


def uninstall_hooks(claude_dir: Path | None = None) -> None:
    """Remove narrator hooks from ~/.claude/settings.json."""
    claude_dir = claude_dir or CLAUDE_DIR
    settings_file = claude_dir / "settings.json"
    if not settings_file.exists():
        return

    try:
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    hooks = settings.get("hooks", {})
    for event in HOOK_EVENTS:
        if event in hooks:
            hooks[event] = [
                group
                for group in hooks[event]
                if not any(
                    NARRATOR_MARKER in h.get("command", "")
                    for h in group.get("hooks", [])
                )
            ]
            if not hooks[event]:
                del hooks[event]

    if not hooks:
        settings.pop("hooks", None)

    settings_file.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Hooks uninstalled from %s", settings_file)


STATUSLINE_MARKER = "claude_narrator.context_monitor"


def install_statusline(claude_dir: Path | None = None) -> None:
    """Register context monitor as Claude Code statusline."""
    claude_dir = claude_dir or CLAUDE_DIR
    settings_file = claude_dir / "settings.json"

    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            settings = {}
    else:
        settings = {}

    # Warn if existing statusline is not ours
    existing = settings.get("statusLine")
    if existing and STATUSLINE_MARKER not in str(existing.get("command", "")):
        logger.warning(
            "Existing statusLine detected: %s. "
            "Context monitor will replace it. Only one statusLine can be active.",
            existing.get("command", "unknown"),
        )

    python_path = _get_python_path()
    settings["statusLine"] = {
        "type": "command",
        "command": f"{python_path} -m {STATUSLINE_MARKER}",
    }

    settings_file.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Statusline registered for context monitor")


def uninstall_statusline(claude_dir: Path | None = None) -> None:
    """Remove context monitor statusline from Claude Code settings."""
    claude_dir = claude_dir or CLAUDE_DIR
    settings_file = claude_dir / "settings.json"
    if not settings_file.exists():
        return

    try:
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    statusline = settings.get("statusLine", {})
    if STATUSLINE_MARKER in str(statusline.get("command", "")):
        del settings["statusLine"]
        settings_file.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Statusline unregistered")
