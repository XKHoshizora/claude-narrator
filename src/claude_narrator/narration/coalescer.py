"""Event coalescer: merge rapid consecutive events of the same type."""

from __future__ import annotations

import time
from typing import Any

IMMEDIATE_EVENTS = {"Notification", "PostToolUseFailure", "Stop"}


class EventCoalescer:
    """Merge rapid consecutive events of the same tool type."""

    def __init__(self, window_seconds: float = 2.0) -> None:
        self._window = window_seconds
        self._pending: dict[str, Any] | None = None
        self._pending_key: str = ""
        self._pending_count: int = 0
        self._pending_time: float = 0.0

    def _event_key(self, event: dict[str, Any]) -> str:
        return f"{event.get('hook_event_name', '')}:{event.get('tool_name', '')}"

    def process(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Process an event. Returns immediately for high-priority; holds others for coalescing.

        Returns the event to narrate, or None if it was absorbed into a pending coalesce.
        Call flush() periodically to emit held events after the window expires.
        """
        event_name = event.get("hook_event_name", "")

        if event_name in IMMEDIATE_EVENTS:
            # Flush pending, then return this immediately
            self._pending = None
            self._pending_key = ""
            self._pending_count = 0
            return event

        key = self._event_key(event)
        now = time.monotonic()

        if self._pending is not None and key == self._pending_key:
            if now - self._pending_time < self._window:
                self._pending_count += 1
                self._pending["_coalesced_count"] = self._pending_count
                return None

        # Different key or window expired - flush old, start new
        flushed = self.flush()
        self._pending = event.copy()
        self._pending_key = key
        self._pending_count = 1
        self._pending_time = now
        return flushed

    def flush(self) -> dict[str, Any] | None:
        """Flush the pending coalesced event."""
        if self._pending is None:
            return None
        result = self._pending
        if self._pending_count > 1:
            result["_coalesced_count"] = self._pending_count
        self._pending = None
        self._pending_key = ""
        self._pending_count = 0
        return result
