import asyncio
import os
from pathlib import Path

import pytest

from claude_narrator.daemon import PIDManager


class TestPIDManager:
    def test_write_and_read_pid(self, tmp_path):
        pid_file = tmp_path / "daemon.pid"
        mgr = PIDManager(pid_file)
        mgr.write(12345)
        assert mgr.read() == 12345

    def test_read_nonexistent(self, tmp_path):
        pid_file = tmp_path / "daemon.pid"
        mgr = PIDManager(pid_file)
        assert mgr.read() is None

    def test_is_running_false_for_nonexistent_pid(self, tmp_path):
        pid_file = tmp_path / "daemon.pid"
        mgr = PIDManager(pid_file)
        mgr.write(999999)  # Unlikely to be a real PID
        assert mgr.is_running() is False

    def test_cleanup(self, tmp_path):
        pid_file = tmp_path / "daemon.pid"
        mgr = PIDManager(pid_file)
        mgr.write(12345)
        mgr.cleanup()
        assert not pid_file.exists()

    def test_is_running_true_for_self(self, tmp_path):
        pid_file = tmp_path / "daemon.pid"
        mgr = PIDManager(pid_file)
        mgr.write(os.getpid())
        assert mgr.is_running() is True


class TestDaemon:
    async def test_daemon_processes_event(self, tmp_config_dir):
        """Daemon receives an event, generates narration, and queues it."""
        from claude_narrator.daemon import Daemon
        from claude_narrator.ipc.unix_socket import UnixSocketServer, UnixSocketClient

        socket_path = tmp_config_dir / "t.sock"
        config = {
            "general": {"verbosity": "verbose", "language": "en", "enabled": True},
            "tts": {"engine": "edge-tts", "voice": "en-US-AriaNeural"},
            "narration": {"mode": "template", "max_queue_size": 5, "max_narration_seconds": 15, "skip_rapid_events": False},
            "cache": {"enabled": False},
            "filters": {"ignore_tools": [], "ignore_paths": [], "only_tools": None, "custom_rules": []},
        }

        narrated_texts = []

        async def fake_tts_and_play(text: str) -> None:
            narrated_texts.append(text)

        daemon = Daemon(config=config, config_dir=tmp_config_dir)
        daemon._tts_and_play = fake_tts_and_play
        daemon._server = UnixSocketServer(socket_path)

        await daemon._server.start()
        task = asyncio.create_task(daemon._event_loop())

        await asyncio.sleep(0.05)
        client = UnixSocketClient(socket_path)
        client.send({
            "hook_event_name": "Stop",
            "session_id": "s1",
            "transcript_path": "/tmp/t.txt",
            "cwd": "/tmp",
        })

        await asyncio.sleep(0.5)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await daemon._server.stop()

        assert len(narrated_texts) >= 1
        assert "Task complete" in narrated_texts[0]

    def test_reload_config_updates_narrator(self, tmp_config_dir):
        """reload_config() re-reads config and rebuilds narrator."""
        import json
        from claude_narrator.daemon import Daemon

        config = {
            "general": {"verbosity": "normal", "language": "en", "enabled": True},
            "tts": {"engine": "edge-tts", "voice": "en-US-AriaNeural"},
            "narration": {"mode": "template", "max_queue_size": 5,
                          "max_narration_seconds": 15, "skip_rapid_events": True},
            "cache": {"enabled": False},
            "filters": {},
            "web": {"enabled": False},
        }

        # Write initial config
        config_file = tmp_config_dir / "config.json"
        config_file.write_text(json.dumps(config))

        daemon = Daemon(config=config, config_dir=tmp_config_dir)
        assert daemon._config["general"]["language"] == "en"

        # Change language in config file
        config["general"]["language"] = "zh"
        config_file.write_text(json.dumps(config))

        daemon.reload_config()
        assert daemon._config["general"]["language"] == "zh"

    def test_reload_config_rebuilds_engine(self, tmp_config_dir):
        """reload_config() rebuilds TTS engine from new config."""
        import json
        from claude_narrator.daemon import Daemon
        from claude_narrator.tts.edge import EdgeTTSEngine

        config = {
            "general": {"verbosity": "normal", "language": "en", "enabled": True},
            "tts": {"engine": "edge-tts", "voice": "en-US-AriaNeural"},
            "narration": {"mode": "template", "max_queue_size": 5,
                          "max_narration_seconds": 15, "skip_rapid_events": True},
            "cache": {"enabled": False},
            "filters": {},
            "web": {"enabled": False},
        }

        config_file = tmp_config_dir / "config.json"
        config_file.write_text(json.dumps(config))

        daemon = Daemon(config=config, config_dir=tmp_config_dir)
        daemon._engine = EdgeTTSEngine(voice="en-US-AriaNeural")

        # Change voice
        config["tts"]["voice"] = "zh-CN-XiaoxiaoNeural"
        config_file.write_text(json.dumps(config))

        daemon.reload_config()
        assert isinstance(daemon._engine, EdgeTTSEngine)
        assert daemon._engine._voice == "zh-CN-XiaoxiaoNeural"


class TestCacheIntegration:
    def test_cache_enabled_by_default(self, tmp_config_dir):
        from claude_narrator.daemon import Daemon
        config = {
            "general": {"verbosity": "normal", "language": "en", "enabled": True},
            "tts": {"engine": "edge-tts", "voice": "en-US-AriaNeural"},
            "narration": {"mode": "template", "max_queue_size": 5,
                          "max_narration_seconds": 15, "skip_rapid_events": True},
            "cache": {"enabled": True, "max_size_mb": 50},
            "filters": {},
        }
        daemon = Daemon(config=config, config_dir=tmp_config_dir)
        assert daemon._cache is not None

    def test_cache_disabled(self, tmp_config_dir):
        from claude_narrator.daemon import Daemon
        config = {
            "general": {"verbosity": "normal", "language": "en", "enabled": True},
            "tts": {"engine": "edge-tts", "voice": "en-US-AriaNeural"},
            "narration": {"mode": "template", "max_queue_size": 5,
                          "max_narration_seconds": 15, "skip_rapid_events": True},
            "cache": {"enabled": False},
            "filters": {},
        }
        daemon = Daemon(config=config, config_dir=tmp_config_dir)
        assert daemon._cache is None

    def test_coalescer_window_is_half_second(self, tmp_config_dir):
        from claude_narrator.daemon import Daemon
        config = {
            "general": {"verbosity": "normal", "language": "en", "enabled": True},
            "tts": {"engine": "edge-tts", "voice": "en-US-AriaNeural"},
            "narration": {"mode": "template", "max_queue_size": 5,
                          "max_narration_seconds": 15, "skip_rapid_events": True},
            "cache": {"enabled": False},
            "filters": {},
        }
        daemon = Daemon(config=config, config_dir=tmp_config_dir)
        assert daemon._coalescer._window == 0.5
