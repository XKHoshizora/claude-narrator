"""Context window monitor: statusline bridge + threshold announcements."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ContextMonitorCoroutine:
    """Periodically checks context.json and announces threshold crossings."""

    def __init__(
        self,
        config_dir: Path,
        thresholds: list[int],
        narrator: Any,
        queue: Any,
        poll_interval: float = 5.0,
    ) -> None:
        self._context_file = config_dir / "context.json"
        self._thresholds = sorted(thresholds)
        self._narrator = narrator
        self._queue = queue
        self._poll_interval = poll_interval
        self._announced: set[int] = set()
        self._last_percentage: float = 0.0

    async def run(self) -> None:
        """Main loop: poll context.json every N seconds."""
        while True:
            await asyncio.sleep(self._poll_interval)
            try:
                await self._check_thresholds()
            except Exception as e:
                logger.debug("Context monitor error: %s", e)

    async def _check_thresholds(self) -> None:
        if not self._context_file.exists():
            return
        try:
            data = json.loads(self._context_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        used_pct = data.get("used_percentage", 0)
        timestamp = data.get("timestamp", 0)

        # Skip stale data (older than 30 seconds)
        if time.time() - timestamp > 30:
            return

        # Reset announced set if usage dropped significantly (compaction or new session)
        if used_pct < self._last_percentage - 10:
            self._announced.clear()
        self._last_percentage = used_pct

        for threshold in self._thresholds:
            if used_pct >= threshold and threshold not in self._announced:
                self._announced.add(threshold)
                await self._announce(threshold, used_pct)

    async def _announce(self, threshold: int, actual: float) -> None:
        """Generate and queue a ContextThreshold narration."""
        event = {
            "hook_event_name": "ContextThreshold",
            "threshold": threshold,
            "used_percentage": actual,
        }
        if hasattr(self._narrator, "narrate_async"):
            text = await self._narrator.narrate_async(event)
        else:
            text = self._narrator.narrate(event)

        if text:
            from claude_narrator.queue import NarrationItem, Priority
            item = NarrationItem(text=text, priority=Priority.MEDIUM, event=event)
            await self._queue.put(item)
            logger.info("Context threshold %d%% announced", threshold)


def statusline_main() -> None:
    """Entry point when called as Claude Code statusline command.

    Reads stdin JSON from Claude Code, extracts context_window.used_percentage,
    writes to ~/.claude-narrator/context.json.

    Usage in settings.json:
      "statusLine": {"type": "command", "command": "python -m claude_narrator.context_monitor"}
    """
    config_dir = Path.home() / ".claude-narrator"
    config_dir.mkdir(parents=True, exist_ok=True)
    context_file = config_dir / "context.json"

    try:
        data = json.load(sys.stdin)
        ctx = data.get("context_window", {})
        used_pct = ctx.get("used_percentage")
        if used_pct is not None:
            context_file.write_text(json.dumps({
                "used_percentage": float(used_pct),
                "timestamp": time.time(),
            }), encoding="utf-8")
    except (json.JSONDecodeError, OSError, KeyError):
        pass


if __name__ == "__main__":
    statusline_main()
