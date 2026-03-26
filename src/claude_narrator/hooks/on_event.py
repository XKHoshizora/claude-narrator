"""Claude Code hook script: receive stdin JSON and forward to daemon.

Usage in hooks config:
  "command": "python -m claude_narrator.hooks.on_event"
"""

from __future__ import annotations

import json
import sys
from typing import IO, Any

from claude_narrator.ipc import create_client
from claude_narrator.ipc.base import IPCClient


def parse_event(stdin: IO[str]) -> dict[str, Any] | None:
    """Parse hook event from stdin JSON."""
    try:
        data = stdin.read()
        if not data.strip():
            return None
        return json.loads(data)
    except (json.JSONDecodeError, OSError):
        return None


def forward_event(
    event: dict[str, Any],
    client: IPCClient | None = None,
) -> None:
    """Forward event to daemon via IPC. Silent on failure."""
    if client is None:
        client = create_client()
    try:
        client.send(event)
    except Exception:
        pass  # Daemon not running — silently ignore


def main() -> None:
    """Entry point for hook script."""
    event = parse_event(sys.stdin)
    if event is not None:
        forward_event(event)


if __name__ == "__main__":
    main()
