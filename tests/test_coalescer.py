import time
from unittest.mock import patch

import pytest
from claude_narrator.narration.coalescer import EventCoalescer


class TestEventCoalescer:
    @pytest.fixture
    def coalescer(self):
        return EventCoalescer(window_seconds=0.5)

    def test_single_event_held(self, coalescer):
        result = coalescer.process({"hook_event_name": "PreToolUse", "tool_name": "Read"})
        # First event for a new key returns None (previous flush) since no pending
        # Actually first call: no pending to flush, so flushed=None, then event becomes pending
        assert result is None

    def test_flush_returns_held_event(self, coalescer):
        coalescer.process({"hook_event_name": "PreToolUse", "tool_name": "Read"})
        result = coalescer.flush()
        assert result is not None
        assert result["tool_name"] == "Read"

    def test_rapid_same_tool_merged(self, coalescer):
        coalescer.process({"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "/a.py"}})
        coalescer.process({"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "/b.py"}})
        coalescer.process({"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "/c.py"}})
        result = coalescer.flush()
        assert result is not None
        assert result.get("_coalesced_count") == 3

    def test_different_tool_flushes_previous(self, coalescer):
        coalescer.process({"hook_event_name": "PreToolUse", "tool_name": "Read"})
        result = coalescer.process({"hook_event_name": "PreToolUse", "tool_name": "Write"})
        # Should flush the Read event
        assert result is not None
        assert result["tool_name"] == "Read"

    def test_high_priority_passes_immediately(self, coalescer):
        result = coalescer.process({"hook_event_name": "Notification"})
        assert result is not None
        assert result["hook_event_name"] == "Notification"

    def test_stop_passes_immediately(self, coalescer):
        result = coalescer.process({"hook_event_name": "Stop"})
        assert result is not None

    def test_window_expiry(self, coalescer):
        coalescer._window = 0.1  # 100ms window for test
        coalescer.process({"hook_event_name": "PreToolUse", "tool_name": "Read"})
        time.sleep(0.15)
        # New event after window should flush old
        result = coalescer.process({"hook_event_name": "PreToolUse", "tool_name": "Read"})
        assert result is not None  # Flushed the old one

    def test_flush_empty_returns_none(self, coalescer):
        assert coalescer.flush() is None
