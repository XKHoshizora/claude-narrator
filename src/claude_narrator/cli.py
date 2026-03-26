"""CLI entry point for claude-narrator."""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

import click

from claude_narrator.config import CONFIG_DIR, load_config
from claude_narrator.daemon import PIDManager, run_daemon
from claude_narrator.installer import install_hooks, uninstall_hooks

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(package_name="claude-narrator")
def main() -> None:
    """Claude Narrator — TTS audio narration for Claude Code."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


@main.command()
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground (don't daemonize)")
def start(foreground: bool) -> None:
    """Start the TTS narration daemon."""
    pid_mgr = PIDManager(CONFIG_DIR / "daemon.pid")
    if pid_mgr.is_running():
        click.echo(f"Daemon already running (PID {pid_mgr.read()})")
        return

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if foreground:
        click.echo("Starting daemon in foreground...")
        run_daemon(foreground=True)
    else:
        click.echo("Starting daemon in background...")
        proc = subprocess.Popen(
            [sys.executable, "-m", "claude_narrator.daemon"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        click.echo(f"Daemon started (PID {proc.pid})")


@main.command()
def stop() -> None:
    """Stop the TTS narration daemon."""
    pid_mgr = PIDManager(CONFIG_DIR / "daemon.pid")
    pid = pid_mgr.read()
    if pid is None or not pid_mgr.is_running():
        click.echo("Daemon is not running.")
        pid_mgr.cleanup()
        return

    try:
        os.kill(pid, signal.SIGTERM)
        click.echo(f"Daemon stopped (PID {pid})")
    except ProcessLookupError:
        click.echo("Daemon process not found.")
    pid_mgr.cleanup()


@main.command("test")
@click.argument("text")
def test_tts(text: str) -> None:
    """Test TTS by playing the given text."""
    import asyncio
    from claude_narrator.tts import create_engine
    from claude_narrator.player import AudioPlayer

    config = load_config()

    async def _test():
        engine = create_engine(config)
        player = AudioPlayer()
        try:
            click.echo(f"Synthesizing: {text}")
            audio = await engine.synthesize(text, language=config["general"]["language"])
            click.echo(f"Playing ({len(audio)} bytes)...")
            await player.play(audio)
            await player.wait_until_done()
            click.echo("Done.")
        finally:
            player.cleanup()

    asyncio.run(_test())


@main.command()
def install() -> None:
    """Install narrator hooks into Claude Code settings.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Create default config if not exists
    config_file = CONFIG_DIR / "config.json"
    if not config_file.exists():
        from claude_narrator.config import DEFAULT_CONFIG
        import json
        config_file.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        click.echo(f"Created default config: {config_file}")

    install_hooks()
    click.echo("Hooks installed. Run 'claude-narrator start' to begin.")


@main.command()
def uninstall() -> None:
    """Remove narrator hooks from Claude Code settings.json."""
    uninstall_hooks()
    click.echo("Hooks removed from settings.json.")
