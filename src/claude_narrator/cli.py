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
@click.option("--web", is_flag=True, help="Enable web UI dashboard")
def start(foreground: bool, web: bool) -> None:
    """Start the TTS narration daemon."""
    pid_mgr = PIDManager(CONFIG_DIR / "daemon.pid")
    if pid_mgr.is_running():
        click.echo(f"Daemon already running (PID {pid_mgr.read()})")
        return

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if foreground:
        if web:
            click.echo("Web UI will be available (configure via config set web.enabled true)")
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


@main.command()
def status() -> None:
    """Show daemon status."""
    pid_mgr = PIDManager(CONFIG_DIR / "daemon.pid")
    if pid_mgr.is_running():
        config = load_config()
        click.echo(f"Status:    Running (PID {pid_mgr.read()})")
        click.echo(f"Engine:    {config['tts']['engine']}")
        click.echo(f"Voice:     {config['tts']['voice']}")
        click.echo(f"Verbosity: {config['general']['verbosity']}")
        click.echo(f"Language:  {config['general']['language']}")
    else:
        click.echo("Status:    Stopped")


@main.command()
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground")
def restart(foreground: bool) -> None:
    """Restart the daemon (stop then start)."""
    import time
    pid_mgr = PIDManager(CONFIG_DIR / "daemon.pid")
    pid = pid_mgr.read()
    if pid is not None and pid_mgr.is_running():
        try:
            os.kill(pid, signal.SIGTERM)
            click.echo(f"Stopped daemon (PID {pid})")
        except ProcessLookupError:
            pass
        pid_mgr.cleanup()
        time.sleep(1)

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


@main.group("config")
def config_group() -> None:
    """Manage configuration."""


@config_group.command("get")
@click.argument("key")
def config_get(key: str) -> None:
    """Get a config value (e.g. general.verbosity)."""
    config = load_config()
    parts = key.split(".")
    value = config
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            click.echo(f"Key not found: {key}", err=True)
            raise SystemExit(1)
    if isinstance(value, dict):
        import json
        click.echo(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        click.echo(f"{value}")


@config_group.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a config value (e.g. general.verbosity verbose)."""
    import json as json_mod
    config_file = CONFIG_DIR / "config.json"
    if config_file.exists():
        user_config = json_mod.loads(config_file.read_text(encoding="utf-8"))
    else:
        user_config = {}

    if value.lower() == "true":
        parsed = True
    elif value.lower() == "false":
        parsed = False
    elif value.isdigit():
        parsed = int(value)
    else:
        parsed = value

    parts = key.split(".")
    target = user_config
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = parsed

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        json_mod.dumps(user_config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    click.echo(f"Set {key} = {parsed}")


@config_group.command("reset")
def config_reset() -> None:
    """Reset config to defaults."""
    import json as json_mod
    from claude_narrator.config import DEFAULT_CONFIG
    config_file = CONFIG_DIR / "config.json"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        json_mod.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    click.echo("Config reset to defaults.")


@main.group("cache")
def cache_group() -> None:
    """Manage audio cache."""


@cache_group.command("clear")
def cache_clear() -> None:
    """Clear the audio cache."""
    cache_dir = CONFIG_DIR / "cache"
    if cache_dir.exists():
        import shutil
        count = len(list(cache_dir.glob("*")))
        shutil.rmtree(cache_dir)
        click.echo(f"Cleared {count} cached files.")
    else:
        click.echo("Cache is empty.")
