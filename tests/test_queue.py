import asyncio

import pytest

from claude_narrator.queue import NarrationItem, NarrationQueue, Priority


class TestNarrationQueue:
    @pytest.fixture
    def queue(self):
        return NarrationQueue(max_size=3)

    async def test_put_and_get(self, queue):
        item = NarrationItem(text="Hello", priority=Priority.MEDIUM)
        await queue.put(item)
        result = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert result.text == "Hello"

    async def test_high_priority_comes_first(self, queue):
        await queue.put(NarrationItem(text="low", priority=Priority.LOW))
        await queue.put(NarrationItem(text="high", priority=Priority.HIGH))
        await queue.put(NarrationItem(text="med", priority=Priority.MEDIUM))

        r1 = await asyncio.wait_for(queue.get(), timeout=1.0)
        r2 = await asyncio.wait_for(queue.get(), timeout=1.0)
        r3 = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert r1.text == "high"
        assert r2.text == "med"
        assert r3.text == "low"

    async def test_max_size_drops_low_priority(self, queue):
        await queue.put(NarrationItem(text="low1", priority=Priority.LOW))
        await queue.put(NarrationItem(text="low2", priority=Priority.LOW))
        await queue.put(NarrationItem(text="low3", priority=Priority.LOW))
        # Queue is full (3). Adding another should drop oldest low priority.
        await queue.put(NarrationItem(text="med1", priority=Priority.MEDIUM))
        assert queue.size <= 3

    async def test_high_priority_never_dropped(self, queue):
        await queue.put(NarrationItem(text="high1", priority=Priority.HIGH))
        await queue.put(NarrationItem(text="high2", priority=Priority.HIGH))
        await queue.put(NarrationItem(text="high3", priority=Priority.HIGH))
        await queue.put(NarrationItem(text="high4", priority=Priority.HIGH))
        # All HIGH items must be kept even if exceeding max_size
        items = []
        while queue.size > 0:
            items.append(await asyncio.wait_for(queue.get(), timeout=1.0))
        assert all(i.priority == Priority.HIGH for i in items)

    def test_empty_size(self, queue):
        assert queue.size == 0

    def test_has_interrupt(self, queue):
        assert queue.has_interrupt is False


class TestNewEventPriorities:
    """Tests for new event priority mappings."""

    def test_tier1_high_priority(self):
        from claude_narrator.queue import EVENT_PRIORITY, Priority
        for event in ["StopFailure", "PermissionDenied", "PermissionRequest"]:
            assert EVENT_PRIORITY[event] == Priority.HIGH, f"{event} should be HIGH"

    def test_tier1_medium_priority(self):
        from claude_narrator.queue import EVENT_PRIORITY, Priority
        for event in ["SessionEnd", "PostCompact", "TaskCreated", "TaskCompleted"]:
            assert EVENT_PRIORITY[event] == Priority.MEDIUM, f"{event} should be MEDIUM"

    def test_tier2_low_priority(self):
        from claude_narrator.queue import EVENT_PRIORITY, Priority
        for event in ["WorktreeCreate", "WorktreeRemove", "CwdChanged", "FileChanged"]:
            assert EVENT_PRIORITY[event] == Priority.LOW, f"{event} should be LOW"
