"""TTS Daemon: asyncio main loop, PID management, event processing."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

from claude_narrator.config import CONFIG_DIR, load_config
from claude_narrator.ipc import create_server
from claude_narrator.ipc.base import IPCServer
from claude_narrator.narration.coalescer import EventCoalescer
from claude_narrator.narration.template import TemplateNarrator
from claude_narrator.narration.verbosity import should_narrate
from claude_narrator.player import AudioPlayer
from claude_narrator.queue import EVENT_PRIORITY, NarrationItem, NarrationQueue, Priority
from claude_narrator.tts import create_engine
from claude_narrator.tts.base import TTSEngine

logger = logging.getLogger(__name__)


class PIDManager:
    """Manage daemon PID file."""

    def __init__(self, pid_file: Path) -> None:
        self._pid_file = pid_file

    def write(self, pid: int) -> None:
        self._pid_file.write_text(str(pid))

    def read(self) -> int | None:
        if not self._pid_file.exists():
            return None
        try:
            return int(self._pid_file.read_text().strip())
        except (ValueError, OSError):
            return None

    def is_running(self) -> bool:
        pid = self.read()
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def cleanup(self) -> None:
        self._pid_file.unlink(missing_ok=True)


class Daemon:
    """Main TTS narration daemon."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        config_dir: Path | None = None,
    ) -> None:
        self._config_dir = config_dir or CONFIG_DIR
        self._config = config or load_config(self._config_dir)
        self._pid_mgr = PIDManager(self._config_dir / "daemon.pid")
        if self._config["narration"]["mode"] == "llm":
            from claude_narrator.narration.llm import LLMNarrator
            llm_cfg = self._config["narration"].get("llm", {})
            self._narrator = LLMNarrator(
                provider=llm_cfg.get("provider", "ollama"),
                model=llm_cfg.get("model", "qwen2.5:3b"),
                language=self._config["general"]["language"],
            )
        else:
            self._narrator = TemplateNarrator(
                language=self._config["general"]["language"]
            )
        self._queue = NarrationQueue(
            max_size=self._config["narration"]["max_queue_size"]
        )
        self._coalescer = EventCoalescer(
            window_seconds=2.0 if self._config["narration"]["skip_rapid_events"] else 0.0
        )
        self._engine: TTSEngine | None = None
        self._player: AudioPlayer | None = None
        self._server: IPCServer | None = None
        self._running = False

    async def start(self, foreground: bool = False) -> None:
        """Start the daemon."""
        if self._pid_mgr.is_running():
            logger.error("Daemon already running (PID %s)", self._pid_mgr.read())
            return

        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._pid_mgr.write(os.getpid())
        self._running = True

        self._engine = create_engine(self._config)
        self._player = AudioPlayer()
        self._server = self._server or create_server(
            socket_path=self._config_dir / "narrator.sock"
        )

        logger.info("Daemon starting (PID %d)", os.getpid())

        try:
            await self._server.start()
            await asyncio.gather(
                self._event_loop(),
                self._playback_loop(),
            )
        except asyncio.CancelledError:
            pass
        finally:
            await self._shutdown()

    async def stop(self) -> None:
        """Signal the daemon to stop."""
        self._running = False

    async def _shutdown(self) -> None:
        logger.info("Daemon shutting down")
        if self._server:
            await self._server.stop()
        if self._player:
            await self._player.stop()
            self._player.cleanup()
        self._pid_mgr.cleanup()

    async def _event_loop(self) -> None:
        """Receive events from IPC, coalesce, queue narration items, and play them."""
        assert self._server is not None
        async for event in self._server.events():
            if not self._config["general"]["enabled"]:
                continue

            event_name = event.get("hook_event_name", "")
            tool_name = event.get("tool_name")
            if not should_narrate(event_name, tool_name, self._config["general"]["verbosity"]):
                continue

            # Coalesce rapid events
            coalesced = self._coalescer.process(event)
            if coalesced is None:
                continue

            if hasattr(self._narrator, "narrate_async"):
                text = await self._narrator.narrate_async(coalesced)
            else:
                text = self._narrator.narrate(coalesced)
            if text is None:
                continue

            priority = EVENT_PRIORITY.get(
                coalesced.get("hook_event_name", ""), Priority.LOW
            )
            item = NarrationItem(text=text, priority=priority, event=coalesced)
            await self._queue.put(item)

            # If high priority, interrupt current playback
            if priority == Priority.HIGH and self._player and self._player.is_playing:
                await self._player.stop()

            # Drain queue: play all queued items immediately
            while self._queue.size > 0:
                queued = await self._queue.get()
                await self._tts_and_play(queued.text)

    async def _playback_loop(self) -> None:
        """Consume queue items and play TTS audio."""
        while self._running:
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            await self._tts_and_play(item.text)

    async def _tts_and_play(self, text: str) -> None:
        """Synthesize and play a narration text with interrupt support."""
        if not self._engine or not self._player:
            return
        try:
            audio = await self._engine.synthesize(
                text, language=self._config["general"]["language"]
            )
            await self._player.play(audio)
            # Wait for playback, but check for high-priority interrupts
            while self._player.is_playing:
                if self._queue.has_interrupt:
                    await self._player.stop()
                    break
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error("TTS/playback error: %s", e)


def run_daemon(config_dir: Path | None = None, foreground: bool = False) -> None:
    """Entry point for starting the daemon."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    daemon = Daemon(config_dir=config_dir)
    asyncio.run(daemon.start(foreground=foreground))


if __name__ == "__main__":
    run_daemon()
