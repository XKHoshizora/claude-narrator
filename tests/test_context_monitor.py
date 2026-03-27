import asyncio
import json
import time
from pathlib import Path

import pytest

from claude_narrator.context_monitor import ContextMonitorCoroutine, statusline_main
from claude_narrator.narration.template import TemplateNarrator
from claude_narrator.queue import NarrationQueue


class TestContextMonitorCoroutine:
    async def test_announces_at_threshold(self, tmp_path):
        context_file = tmp_path / "context.json"
        context_file.write_text(json.dumps({
            "used_percentage": 72.0,
            "timestamp": time.time(),
        }))
        narrator = TemplateNarrator("en", "concise")
        queue = NarrationQueue()
        monitor = ContextMonitorCoroutine(
            config_dir=tmp_path,
            thresholds=[50, 70, 85],
            narrator=narrator,
            queue=queue,
            poll_interval=0.1,
        )
        task = asyncio.create_task(monitor.run())
        await asyncio.sleep(0.3)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        # Should have announced 50% and 70% thresholds
        assert queue.size >= 1

    async def test_threshold_announced_only_once(self, tmp_path):
        context_file = tmp_path / "context.json"
        context_file.write_text(json.dumps({
            "used_percentage": 72.0,
            "timestamp": time.time(),
        }))
        narrator = TemplateNarrator("en", "concise")
        queue = NarrationQueue()
        monitor = ContextMonitorCoroutine(
            config_dir=tmp_path,
            thresholds=[70],
            narrator=narrator,
            queue=queue,
            poll_interval=0.1,
        )
        task = asyncio.create_task(monitor.run())
        await asyncio.sleep(0.4)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        # Should be announced exactly once despite multiple polls
        items = []
        while queue.size > 0:
            items.append(await asyncio.wait_for(queue.get(), timeout=0.1))
        assert len(items) == 1

    async def test_resets_on_usage_drop(self, tmp_path):
        context_file = tmp_path / "context.json"
        narrator = TemplateNarrator("en", "concise")
        queue = NarrationQueue()
        monitor = ContextMonitorCoroutine(
            config_dir=tmp_path,
            thresholds=[70],
            narrator=narrator,
            queue=queue,
            poll_interval=0.1,
        )
        # First: 75% -> announced
        context_file.write_text(json.dumps({"used_percentage": 75.0, "timestamp": time.time()}))
        await monitor._check_thresholds()
        assert 70 in monitor._announced

        # Drop to 30% -> reset
        context_file.write_text(json.dumps({"used_percentage": 30.0, "timestamp": time.time()}))
        await monitor._check_thresholds()
        assert len(monitor._announced) == 0

    async def test_stale_data_ignored(self, tmp_path):
        context_file = tmp_path / "context.json"
        context_file.write_text(json.dumps({
            "used_percentage": 90.0,
            "timestamp": time.time() - 60,  # 60 seconds old
        }))
        narrator = TemplateNarrator("en", "concise")
        queue = NarrationQueue()
        monitor = ContextMonitorCoroutine(
            config_dir=tmp_path,
            thresholds=[70, 85],
            narrator=narrator,
            queue=queue,
        )
        await monitor._check_thresholds()
        assert queue.size == 0  # stale, no announcement

    async def test_missing_file_no_crash(self, tmp_path):
        narrator = TemplateNarrator("en", "concise")
        queue = NarrationQueue()
        monitor = ContextMonitorCoroutine(
            config_dir=tmp_path,
            thresholds=[70],
            narrator=narrator,
            queue=queue,
        )
        await monitor._check_thresholds()  # Should not raise
        assert queue.size == 0


class TestStatuslineMain:
    def test_writes_context_json(self, tmp_path, monkeypatch):
        import io
        stdin_data = json.dumps({
            "context_window": {
                "used_percentage": 65.3,
                "context_window_size": 200000,
            }
        })
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
        monkeypatch.setattr("claude_narrator.context_monitor.Path.home", lambda: tmp_path)

        # Create the expected directory
        config_dir = tmp_path / ".claude-narrator"
        config_dir.mkdir(parents=True, exist_ok=True)

        statusline_main()

        context_file = config_dir / "context.json"
        assert context_file.exists()
        data = json.loads(context_file.read_text())
        assert data["used_percentage"] == 65.3
        assert "timestamp" in data
