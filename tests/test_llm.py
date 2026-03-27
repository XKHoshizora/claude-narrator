from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from claude_narrator.narration.llm import LLMNarrator


class TestLLMNarrator:
    @pytest.fixture
    def narrator(self):
        return LLMNarrator(provider="ollama", model="test", language="en", timeout=1.0)

    def test_sync_narrate_uses_template_fallback(self, narrator):
        event = {"hook_event_name": "Stop"}
        result = narrator.narrate(event)
        assert result == "Task complete"

    async def test_async_narrate_calls_llm(self, narrator):
        with patch.object(narrator, "_call_llm", new_callable=AsyncMock, return_value="Finishing up the task"):
            result = await narrator.narrate_async({"hook_event_name": "Stop"})
            assert result == "Finishing up the task"

    async def test_async_narrate_falls_back_on_timeout(self, narrator):
        async def slow_llm(event):
            import asyncio
            await asyncio.sleep(5)
            return "too slow"

        with patch.object(narrator, "_call_llm", side_effect=slow_llm):
            narrator._timeout = 0.1
            result = await narrator.narrate_async({"hook_event_name": "Stop"})
            assert result == "Task complete"  # template fallback

    async def test_async_narrate_falls_back_on_error(self, narrator):
        with patch.object(narrator, "_call_llm", new_callable=AsyncMock, side_effect=Exception("connection error")):
            result = await narrator.narrate_async({"hook_event_name": "Stop"})
            assert result == "Task complete"

    def test_recent_events_limited_to_3(self, narrator):
        for i in range(5):
            narrator.narrate({"hook_event_name": "PreToolUse", "tool_name": f"tool{i}"})
        assert len(narrator._recent_events) <= 3
