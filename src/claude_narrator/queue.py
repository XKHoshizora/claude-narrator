"""Priority narration queue with overflow management."""

from __future__ import annotations

import asyncio
import heapq
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class Priority(IntEnum):
    HIGH = 0    # Notification, failures — interrupts playback
    MEDIUM = 1  # Stop, SubagentStart/Stop, SessionStart
    LOW = 2     # PreToolUse, PostToolUse, PreCompact


# Map hook event names to priority levels
EVENT_PRIORITY: dict[str, Priority] = {
    "Notification": Priority.HIGH,
    "PostToolUseFailure": Priority.HIGH,
    "Stop": Priority.MEDIUM,
    "ContextThreshold": Priority.MEDIUM,
    "SubagentStart": Priority.MEDIUM,
    "SubagentStop": Priority.MEDIUM,
    "SessionStart": Priority.MEDIUM,
    "PreToolUse": Priority.LOW,
    "PostToolUse": Priority.LOW,
    "PreCompact": Priority.LOW,
}

_counter = 0


def _next_seq() -> int:
    global _counter
    _counter += 1
    return _counter


@dataclass(order=True)
class NarrationItem:
    """An item in the narration queue."""
    priority: Priority
    _seq: int = field(default_factory=_next_seq, compare=True)
    text: str = field(compare=False, default="")
    event: dict[str, Any] = field(compare=False, default_factory=dict)


class NarrationQueue:
    """Priority queue with max size and overflow management."""

    def __init__(self, max_size: int = 5) -> None:
        self._max_size = max_size
        self._heap: list[NarrationItem] = []
        self._event = asyncio.Event()

    @property
    def size(self) -> int:
        return len(self._heap)

    @property
    def has_interrupt(self) -> bool:
        """Whether the queue contains a HIGH priority item."""
        return any(item.priority == Priority.HIGH for item in self._heap)

    async def put(self, item: NarrationItem) -> None:
        """Add item to queue, dropping low priority if full."""
        if len(self._heap) >= self._max_size and item.priority != Priority.HIGH:
            # Try to drop lowest priority (highest enum value) oldest item
            droppable = [
                (i, it) for i, it in enumerate(self._heap)
                if it.priority == Priority.LOW
            ]
            if droppable:
                idx, _ = droppable[0]
                self._heap.pop(idx)
                heapq.heapify(self._heap)

        heapq.heappush(self._heap, item)
        self._event.set()

    async def get(self) -> NarrationItem:
        """Get highest-priority item. Waits if empty."""
        while not self._heap:
            self._event.clear()
            await self._event.wait()
        item = heapq.heappop(self._heap)
        if not self._heap:
            self._event.clear()
        return item
