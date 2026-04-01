# Claude Narrator Implementation Plan

> **状态: 已完成** — v0.1.0 MVP + v0.2.0 已发布。

**Goal:** Build a TTS audio narration plugin for Claude Code that speaks work status in real-time via hooks.

**Architecture:** Python asyncio daemon receives hook events via Unix Socket (HTTP fallback on Windows), generates narration text from JSON templates, synthesizes audio with edge-tts, and plays via pygame. Hook scripts are lightweight forwarders.

**Tech Stack:** Python 3.10+, edge-tts, pygame, click, httpx, pytest, pytest-asyncio

**Spec:** `docs/superpowers/specs/2026-03-27-claude-narrator-design.md`

---

## File Structure

```
claude-narrator/
├── src/claude_narrator/
│   ├── __init__.py              # Version string
│   ├── config.py                # Config loading, validation, deep merge, defaults
│   ├── ipc/
│   │   ├── __init__.py          # create_server() / create_client() platform factory
│   │   ├── base.py              # IPCServer / IPCClient ABCs
│   │   ├── unix_socket.py       # UnixSocketServer + UnixSocketClient
│   │   └── http.py              # HTTPServer + HTTPClient
│   ├── narration/
│   │   ├── __init__.py
│   │   ├── template.py          # TemplateNarrator: event → narration text
│   │   ├── coalescer.py         # EventCoalescer: merge rapid events (Phase 2)
│   │   └── llm.py               # LLMNarrator (Phase 3)
│   ├── tts/
│   │   ├── __init__.py          # create_engine() factory
│   │   ├── base.py              # TTSEngine ABC
│   │   ├── edge.py              # EdgeTTSEngine
│   │   ├── macos_say.py         # MacOSSayEngine (Phase 2)
│   │   ├── espeak.py            # EspeakEngine (Phase 2)
│   │   └── openai_tts.py        # OpenAITTSEngine (Phase 2)
│   ├── player.py                # AudioPlayer: pygame-based async playback
│   ├── queue.py                 # NarrationQueue: priority queue with max_size
│   ├── cache.py                 # AudioCache: LRU file cache (Phase 2)
│   ├── daemon.py                # Daemon: asyncio main loop, PID, lifecycle
│   ├── installer.py             # Install/uninstall hooks in settings.json
│   ├── cli.py                   # Click CLI entry point
│   └── hooks/
│       ├── __init__.py
│       └── on_event.py          # Hook script: stdin → IPC → exit
├── src/claude_narrator/i18n/
│   ├── en.json                  # English templates
│   ├── zh.json                  # Chinese templates (Phase 2)
│   └── ja.json                  # Japanese templates (Phase 2)
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── test_config.py
│   ├── test_ipc.py
│   ├── test_template.py
│   ├── test_tts.py
│   ├── test_player.py
│   ├── test_queue.py
│   ├── test_daemon.py
│   ├── test_hook.py
│   ├── test_installer.py
│   └── test_cli.py
├── pyproject.toml
├── .gitignore
├── LICENSE
└── README.md
```

---

## Phase 1: MVP

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `src/claude_narrator/__init__.py`
- Create: all `__init__.py` files for subpackages
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "setuptools-scm"]
build-backend = "setuptools.build_meta"

[project]
name = "claude-narrator"
version = "0.1.0"
description = "TTS audio narration for Claude Code - hear what Claude is doing"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [{ name = "hoshizora" }]
keywords = ["claude-code", "tts", "narration", "hooks", "plugin"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Topic :: Multimedia :: Sound/Audio :: Speech",
]
dependencies = [
    "edge-tts>=6.1.0",
    "pygame>=2.5.0",
    "click>=8.1.0",
]

[project.optional-dependencies]
openai = ["httpx>=0.27.0"]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]

[project.scripts]
claude-narrator = "claude_narrator.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
venv/
.pytest_cache/
.mypy_cache/
htmlcov/
.coverage
```

- [ ] **Step 3: Create LICENSE (MIT)**

```
MIT License

Copyright (c) 2026 hoshizora

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: Create package __init__.py files**

`src/claude_narrator/__init__.py`:
```python
"""Claude Narrator - TTS audio narration for Claude Code."""

__version__ = "0.1.0"
```

Create empty `__init__.py` in:
- `src/claude_narrator/ipc/__init__.py`
- `src/claude_narrator/narration/__init__.py`
- `src/claude_narrator/tts/__init__.py`
- `src/claude_narrator/hooks/__init__.py`

`tests/conftest.py`:
```python
"""Shared test fixtures for claude-narrator."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_config_dir(tmp_path):
    """Temporary config directory replacing ~/.claude-narrator/."""
    config_dir = tmp_path / ".claude-narrator"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def tmp_claude_dir(tmp_path):
    """Temporary ~/.claude/ directory for settings.json."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    return claude_dir
```

- [ ] **Step 5: Install in development mode and verify**

Run: `cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator && pip install -e ".[dev]"`
Expected: Successful install, `claude-narrator --help` shows click help text (will fail until CLI exists — that's fine)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore LICENSE src/ tests/conftest.py
git commit -m "feat: project scaffolding with pyproject.toml and package structure"
```

---

### Task 2: Configuration System

**Files:**
- Create: `src/claude_narrator/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config**

`tests/test_config.py`:
```python
import json
from pathlib import Path

import pytest

from claude_narrator.config import (
    DEFAULT_CONFIG,
    load_config,
    deep_merge,
    validate_config,
)


class TestDefaultConfig:
    def test_has_general_section(self):
        assert "general" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["general"]["verbosity"] == "normal"
        assert DEFAULT_CONFIG["general"]["language"] == "en"
        assert DEFAULT_CONFIG["general"]["enabled"] is True

    def test_has_tts_section(self):
        assert DEFAULT_CONFIG["tts"]["engine"] == "edge-tts"
        assert DEFAULT_CONFIG["tts"]["voice"] == "en-US-AriaNeural"

    def test_has_narration_section(self):
        assert DEFAULT_CONFIG["narration"]["mode"] == "template"
        assert DEFAULT_CONFIG["narration"]["max_queue_size"] == 5
        assert DEFAULT_CONFIG["narration"]["max_narration_seconds"] == 15
        assert DEFAULT_CONFIG["narration"]["skip_rapid_events"] is True


class TestDeepMerge:
    def test_shallow_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        assert deep_merge(base, override) == {"a": 1, "b": 3}

    def test_nested_override(self):
        base = {"general": {"verbosity": "normal", "language": "en"}}
        override = {"general": {"verbosity": "verbose"}}
        result = deep_merge(base, override)
        assert result["general"]["verbosity"] == "verbose"
        assert result["general"]["language"] == "en"

    def test_add_new_key(self):
        base = {"a": 1}
        override = {"b": 2}
        assert deep_merge(base, override) == {"a": 1, "b": 2}


class TestValidateConfig:
    def test_valid_verbosity(self):
        config = deep_merge(DEFAULT_CONFIG, {"general": {"verbosity": "minimal"}})
        result = validate_config(config)
        assert result["general"]["verbosity"] == "minimal"

    def test_invalid_verbosity_falls_back(self):
        config = deep_merge(DEFAULT_CONFIG, {"general": {"verbosity": "invalid"}})
        result = validate_config(config)
        assert result["general"]["verbosity"] == "normal"

    def test_invalid_engine_falls_back(self):
        config = deep_merge(DEFAULT_CONFIG, {"tts": {"engine": "nonexistent"}})
        result = validate_config(config)
        assert result["tts"]["engine"] == "edge-tts"

    def test_invalid_language_falls_back(self):
        config = deep_merge(DEFAULT_CONFIG, {"general": {"language": "xx"}})
        result = validate_config(config)
        assert result["general"]["language"] == "en"

    def test_valid_language_zh(self):
        config = deep_merge(DEFAULT_CONFIG, {"general": {"language": "zh"}})
        result = validate_config(config)
        assert result["general"]["language"] == "zh"


class TestLoadConfig:
    def test_load_default_when_no_file(self, tmp_config_dir):
        result = load_config(config_dir=tmp_config_dir)
        assert result == validate_config(DEFAULT_CONFIG)

    def test_load_user_overrides(self, tmp_config_dir):
        config_file = tmp_config_dir / "config.json"
        config_file.write_text(json.dumps({"general": {"verbosity": "verbose"}}))
        result = load_config(config_dir=tmp_config_dir)
        assert result["general"]["verbosity"] == "verbose"
        assert result["general"]["language"] == "en"  # default preserved

    def test_load_malformed_json_falls_back(self, tmp_config_dir):
        config_file = tmp_config_dir / "config.json"
        config_file.write_text("not valid json{{{")
        result = load_config(config_dir=tmp_config_dir)
        assert result == validate_config(DEFAULT_CONFIG)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Implement config.py**

`src/claude_narrator/config.py`:
```python
"""Configuration loading, validation, and defaults."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".claude-narrator"
VALID_VERBOSITIES = ("minimal", "normal", "verbose")
VALID_ENGINES = ("edge-tts", "say", "espeak", "openai")
VALID_LANGUAGES = ("en", "zh", "ja")
VALID_MODES = ("template", "llm")

DEFAULT_CONFIG: dict[str, Any] = {
    "general": {
        "verbosity": "normal",
        "language": "en",
        "enabled": True,
    },
    "tts": {
        "engine": "edge-tts",
        "voice": "en-US-AriaNeural",
        "openai": {
            "api_key_env": "OPENAI_API_KEY",
            "model": "tts-1",
            "voice": "nova",
        },
    },
    "narration": {
        "mode": "template",
        "max_queue_size": 5,
        "max_narration_seconds": 15,
        "skip_rapid_events": True,
        "llm": {
            "provider": "ollama",
            "model": "qwen2.5:3b",
        },
    },
    "cache": {
        "enabled": True,
        "max_size_mb": 50,
    },
    "filters": {
        "ignore_tools": [],
        "ignore_paths": [],
        "only_tools": None,
        "custom_rules": [],
    },
}


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base. Returns new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate config values; invalid values fall back to defaults."""
    result = json.loads(json.dumps(config))  # deep copy

    general = result.get("general", {})
    if general.get("verbosity") not in VALID_VERBOSITIES:
        general["verbosity"] = DEFAULT_CONFIG["general"]["verbosity"]
    if general.get("language") not in VALID_LANGUAGES:
        general["language"] = DEFAULT_CONFIG["general"]["language"]
    result["general"] = general

    tts = result.get("tts", {})
    if tts.get("engine") not in VALID_ENGINES:
        tts["engine"] = DEFAULT_CONFIG["tts"]["engine"]
    result["tts"] = tts

    narration = result.get("narration", {})
    if narration.get("mode") not in VALID_MODES:
        narration["mode"] = DEFAULT_CONFIG["narration"]["mode"]
    result["narration"] = narration

    return result


def load_config(config_dir: Path | None = None) -> dict[str, Any]:
    """Load config from disk, merge with defaults, validate."""
    config_dir = config_dir or CONFIG_DIR
    config_file = config_dir / "config.json"

    if config_file.exists():
        try:
            user_config = json.loads(config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load config: %s. Using defaults.", e)
            user_config = {}
    else:
        user_config = {}

    merged = deep_merge(DEFAULT_CONFIG, user_config)
    return validate_config(merged)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/claude_narrator/config.py tests/test_config.py
git commit -m "feat: configuration system with defaults, deep merge, and validation"
```

---

### Task 3: IPC Layer

**Files:**
- Create: `src/claude_narrator/ipc/base.py`
- Create: `src/claude_narrator/ipc/unix_socket.py`
- Create: `src/claude_narrator/ipc/http.py`
- Modify: `src/claude_narrator/ipc/__init__.py`
- Create: `tests/test_ipc.py`

- [ ] **Step 1: Write failing tests for IPC**

`tests/test_ipc.py`:
```python
import asyncio
import json

import pytest

from claude_narrator.ipc.unix_socket import UnixSocketServer, UnixSocketClient
from claude_narrator.ipc.http import HTTPServer, HTTPClient
from claude_narrator.ipc import create_server, create_client


class TestUnixSocketIPC:
    @pytest.fixture
    def socket_path(self, tmp_path):
        return tmp_path / "test.sock"

    async def test_send_and_receive(self, socket_path):
        server = UnixSocketServer(socket_path)
        client = UnixSocketClient(socket_path)
        received = []

        async def collect_events():
            async for event in server.events():
                received.append(event)
                if len(received) >= 2:
                    break

        await server.start()
        try:
            task = asyncio.create_task(collect_events())
            await asyncio.sleep(0.05)

            client.send({"hook_event_name": "Stop", "session_id": "s1"})
            client.send({"hook_event_name": "PreToolUse", "tool_name": "Read"})

            await asyncio.wait_for(task, timeout=2.0)

            assert len(received) == 2
            assert received[0]["hook_event_name"] == "Stop"
            assert received[1]["tool_name"] == "Read"
        finally:
            await server.stop()

    async def test_client_silent_on_no_server(self, socket_path):
        client = UnixSocketClient(socket_path)
        # Should not raise
        client.send({"hook_event_name": "Stop"})


class TestHTTPIPC:
    async def test_send_and_receive(self):
        server = HTTPServer(host="127.0.0.1", port=0)  # port=0 for random port
        received = []

        async def collect_events():
            async for event in server.events():
                received.append(event)
                if len(received) >= 1:
                    break

        await server.start()
        actual_port = server.port
        try:
            task = asyncio.create_task(collect_events())
            await asyncio.sleep(0.05)

            client = HTTPClient(host="127.0.0.1", port=actual_port)
            client.send({"hook_event_name": "Stop", "session_id": "s1"})

            await asyncio.wait_for(task, timeout=2.0)
            assert len(received) == 1
            assert received[0]["hook_event_name"] == "Stop"
        finally:
            await server.stop()


class TestIPCFactory:
    def test_create_server_unix(self, tmp_path):
        server = create_server(socket_path=tmp_path / "test.sock")
        assert isinstance(server, UnixSocketServer)

    def test_create_client_unix(self, tmp_path):
        client = create_client(socket_path=tmp_path / "test.sock")
        assert isinstance(client, UnixSocketClient)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ipc.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement IPC base classes**

`src/claude_narrator/ipc/base.py`:
```python
"""Abstract base classes for IPC server and client."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class IPCServer(ABC):
    """Server that receives events from hook scripts."""

    @abstractmethod
    async def start(self) -> None:
        """Start listening for connections."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop listening and clean up."""

    @abstractmethod
    async def events(self) -> AsyncIterator[dict[str, Any]]:
        """Yield events as they arrive."""
        yield {}  # pragma: no cover


class IPCClient(ABC):
    """Client used by hook scripts to send events to the daemon."""

    @abstractmethod
    def send(self, event: dict[str, Any]) -> None:
        """Send event to daemon. Fire-and-forget; never raises."""
```

- [ ] **Step 4: Implement Unix Socket IPC**

`src/claude_narrator/ipc/unix_socket.py`:
```python
"""Unix Domain Socket IPC implementation."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
from pathlib import Path
from typing import Any, AsyncIterator

from claude_narrator.ipc.base import IPCClient, IPCServer

logger = logging.getLogger(__name__)


class UnixSocketServer(IPCServer):
    def __init__(self, socket_path: Path) -> None:
        self._path = socket_path
        self._server: asyncio.AbstractServer | None = None
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def start(self) -> None:
        self._path.unlink(missing_ok=True)
        self._server = await asyncio.start_unix_server(
            self._handle_client, path=str(self._path)
        )
        logger.info("Unix socket server listening on %s", self._path)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._path.unlink(missing_ok=True)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            data = await reader.read(65536)
            if data:
                for line in data.decode("utf-8").strip().split("\n"):
                    if line:
                        event = json.loads(line)
                        await self._queue.put(event)
        except Exception as e:
            logger.debug("Error handling client: %s", e)
        finally:
            writer.close()
            await writer.wait_closed()

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        while True:
            event = await self._queue.get()
            yield event


class UnixSocketClient(IPCClient):
    def __init__(self, socket_path: Path) -> None:
        self._path = socket_path

    def send(self, event: dict[str, Any]) -> None:
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(str(self._path))
            sock.sendall(json.dumps(event).encode("utf-8") + b"\n")
            sock.close()
        except Exception:
            pass  # Silent on failure — daemon may not be running
```

- [ ] **Step 5: Implement HTTP IPC**

`src/claude_narrator/ipc/http.py`:
```python
"""HTTP IPC implementation (Windows fallback)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator
from http.server import HTTPServer as BaseHTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError

from claude_narrator.ipc.base import IPCClient, IPCServer

logger = logging.getLogger(__name__)


class HTTPServer(IPCServer):
    def __init__(self, host: str = "127.0.0.1", port: int = 19821) -> None:
        self._host = host
        self._port = port
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._site: asyncio.Server | None = None

    @property
    def port(self) -> int:
        if self._site and self._site.sockets:
            return self._site.sockets[0].getsockname()[1]
        return self._port

    async def start(self) -> None:
        self._site = await asyncio.start_server(
            self._handle_client, self._host, self._port
        )
        if self._site.sockets:
            self._port = self._site.sockets[0].getsockname()[1]
        logger.info("HTTP server listening on %s:%d", self._host, self._port)

    async def stop(self) -> None:
        if self._site:
            self._site.close()
            await self._site.wait_closed()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            data = await reader.read(65536)
            text = data.decode("utf-8")
            # Extract JSON body from HTTP POST (simple parsing)
            body_start = text.find("\r\n\r\n")
            if body_start >= 0:
                body = text[body_start + 4:]
            else:
                body = text
            if body.strip():
                event = json.loads(body.strip())
                await self._queue.put(event)

            response = "HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
            writer.write(response.encode("utf-8"))
            await writer.drain()
        except Exception as e:
            logger.debug("Error handling HTTP client: %s", e)
        finally:
            writer.close()
            await writer.wait_closed()

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        while True:
            event = await self._queue.get()
            yield event


class HTTPClient(IPCClient):
    def __init__(self, host: str = "127.0.0.1", port: int = 19821) -> None:
        self._url = f"http://{host}:{port}/event"

    def send(self, event: dict[str, Any]) -> None:
        try:
            body = json.dumps(event).encode("utf-8")
            # Send as raw TCP to match our simple server
            import socket
            host, _, port_str = self._url.replace("http://", "").partition("/")
            host, _, port_s = host.partition(":")
            port = int(port_s)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((host, port))
            request = (
                f"POST /event HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"\r\n"
            ).encode("utf-8") + body
            sock.sendall(request)
            sock.recv(1024)  # Read response
            sock.close()
        except Exception:
            pass  # Silent on failure


- [ ] **Step 6: Implement IPC factory**

`src/claude_narrator/ipc/__init__.py`:
```python
"""IPC layer: platform-aware server/client factory."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from claude_narrator.ipc.base import IPCClient, IPCServer
from claude_narrator.ipc.unix_socket import UnixSocketClient, UnixSocketServer
from claude_narrator.ipc.http import HTTPClient, HTTPServer
from claude_narrator.config import CONFIG_DIR

DEFAULT_SOCKET_PATH = CONFIG_DIR / "narrator.sock"
DEFAULT_HTTP_PORT = 19821


def create_server(
    socket_path: Path | None = None,
    http_port: int = DEFAULT_HTTP_PORT,
) -> IPCServer:
    """Create IPC server based on platform."""
    if sys.platform == "win32":
        return HTTPServer(port=http_port)
    return UnixSocketServer(socket_path or DEFAULT_SOCKET_PATH)


def create_client(
    socket_path: Path | None = None,
    http_port: int = DEFAULT_HTTP_PORT,
) -> IPCClient:
    """Create IPC client based on platform."""
    if sys.platform == "win32":
        return HTTPClient(port=http_port)
    return UnixSocketClient(socket_path or DEFAULT_SOCKET_PATH)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/test_ipc.py -v`
Expected: All 5 tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/claude_narrator/ipc/ tests/test_ipc.py
git commit -m "feat: IPC layer with Unix Socket and HTTP fallback"
```

---

### Task 4: Narration Template Engine

**Files:**
- Create: `src/claude_narrator/i18n/en.json`
- Create: `src/claude_narrator/narration/template.py`
- Create: `tests/test_template.py`

- [ ] **Step 1: Create English template file**

`src/claude_narrator/i18n/en.json`:
```json
{
    "PreToolUse": {
        "Read": "Reading {file_path}",
        "Write": "Writing to {file_path}",
        "Edit": "Editing {file_path}",
        "Bash": "Running command",
        "Glob": "Searching files",
        "Grep": "Searching code",
        "Agent": "Starting agent",
        "default": "Using {tool_name}"
    },
    "PostToolUse": {
        "Read": "Read complete",
        "Write": "Write complete",
        "Edit": "Edit complete",
        "Bash": "Command complete",
        "default": "{tool_name} done"
    },
    "PostToolUseFailure": {
        "Bash": "Command failed",
        "default": "{tool_name} failed"
    },
    "Stop": {
        "default": "Task complete"
    },
    "Notification": {
        "default": "Attention needed"
    },
    "SubagentStart": {
        "default": "Starting subtask"
    },
    "SubagentStop": {
        "default": "Subtask complete"
    },
    "SessionStart": {
        "default": "Session started"
    },
    "PreCompact": {
        "default": "Compacting context"
    }
}
```

- [ ] **Step 2: Write failing tests for template narrator**

`tests/test_template.py`:
```python
import pytest

from claude_narrator.narration.template import TemplateNarrator


@pytest.fixture
def narrator():
    return TemplateNarrator(language="en")


class TestTemplateNarrator:
    def test_pre_tool_use_read(self, narrator):
        event = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/src/app.py"},
        }
        assert narrator.narrate(event) == "Reading /src/app.py"

    def test_pre_tool_use_write(self, narrator):
        event = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "/src/main.py"},
        }
        assert narrator.narrate(event) == "Writing to /src/main.py"

    def test_pre_tool_use_default(self, narrator):
        event = {
            "hook_event_name": "PreToolUse",
            "tool_name": "CustomTool",
            "tool_input": {},
        }
        assert narrator.narrate(event) == "Using CustomTool"

    def test_post_tool_use(self, narrator):
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_result": "success",
        }
        assert narrator.narrate(event) == "Command complete"

    def test_post_tool_use_failure(self, narrator):
        event = {
            "hook_event_name": "PostToolUseFailure",
            "tool_name": "Bash",
            "tool_result": "exit code 1",
        }
        assert narrator.narrate(event) == "Command failed"

    def test_stop(self, narrator):
        event = {"hook_event_name": "Stop", "reason": "done"}
        assert narrator.narrate(event) == "Task complete"

    def test_notification(self, narrator):
        event = {"hook_event_name": "Notification"}
        assert narrator.narrate(event) == "Attention needed"

    def test_subagent_start(self, narrator):
        event = {"hook_event_name": "SubagentStart"}
        assert narrator.narrate(event) == "Starting subtask"

    def test_session_start(self, narrator):
        event = {"hook_event_name": "SessionStart"}
        assert narrator.narrate(event) == "Session started"

    def test_unknown_event_returns_none(self, narrator):
        event = {"hook_event_name": "UnknownEvent"}
        assert narrator.narrate(event) is None

    def test_file_path_shortened(self, narrator):
        event = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/very/long/path/to/deeply/nested/file.py"},
        }
        result = narrator.narrate(event)
        assert "file.py" in result
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_template.py -v`
Expected: FAIL — ImportError

- [ ] **Step 4: Implement template narrator**

`src/claude_narrator/narration/template.py`:
```python
"""Template-based narration: event → text using i18n JSON templates."""

from __future__ import annotations

import json
import logging
from importlib import resources
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _shorten_path(path: str, max_parts: int = 3) -> str:
    """Shorten file path to last N components."""
    parts = Path(path).parts
    if len(parts) <= max_parts:
        return path
    return str(Path(*parts[-max_parts:]))


def _extract_variables(event: dict[str, Any]) -> dict[str, str]:
    """Extract template variables from event data."""
    variables: dict[str, str] = {}
    variables["tool_name"] = event.get("tool_name", "unknown")

    tool_input = event.get("tool_input", {})
    if isinstance(tool_input, dict):
        if "file_path" in tool_input:
            variables["file_path"] = _shorten_path(tool_input["file_path"])
        if "command" in tool_input:
            cmd = tool_input["command"]
            variables["command_short"] = cmd[:50] + "..." if len(cmd) > 50 else cmd
        if "pattern" in tool_input:
            variables["pattern"] = tool_input["pattern"]

    if "reason" in event:
        variables["reason"] = event["reason"]
    if "message" in event:
        variables["message"] = event["message"]

    return variables


class TemplateNarrator:
    """Generate narration text from event using i18n templates."""

    def __init__(self, language: str = "en") -> None:
        self._templates = self._load_templates(language)

    def _load_templates(self, language: str) -> dict[str, Any]:
        """Load i18n template file."""
        try:
            ref = resources.files("claude_narrator.i18n").joinpath(f"{language}.json")
            return json.loads(ref.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning("Failed to load %s templates: %s. Falling back to en.", language, e)
            if language != "en":
                return self._load_templates("en")
            return {}

    def narrate(self, event: dict[str, Any]) -> str | None:
        """Generate narration text for an event. Returns None if no template."""
        event_type = event.get("hook_event_name", "")
        templates = self._templates.get(event_type)
        if not templates:
            return None

        tool_name = event.get("tool_name", "")
        template = templates.get(tool_name, templates.get("default"))
        if not template:
            return None

        variables = _extract_variables(event)
        try:
            return template.format_map(variables)
        except KeyError:
            return template  # Return template as-is if variables missing
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_template.py -v`
Expected: All 11 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/claude_narrator/i18n/en.json src/claude_narrator/narration/template.py tests/test_template.py
git commit -m "feat: template-based narration engine with English i18n"
```

---

### Task 5: TTS Engine Base + Edge-TTS

**Files:**
- Create: `src/claude_narrator/tts/base.py`
- Create: `src/claude_narrator/tts/edge.py`
- Modify: `src/claude_narrator/tts/__init__.py`
- Create: `tests/test_tts.py`

- [ ] **Step 1: Write failing tests**

`tests/test_tts.py`:
```python
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from claude_narrator.tts.base import TTSEngine
from claude_narrator.tts.edge import EdgeTTSEngine
from claude_narrator.tts import create_engine


class TestTTSEngineInterface:
    def test_cannot_instantiate_base(self):
        with pytest.raises(TypeError):
            TTSEngine()


class TestEdgeTTSEngine:
    @pytest.fixture
    def engine(self):
        return EdgeTTSEngine(voice="en-US-AriaNeural")

    async def test_synthesize_returns_bytes(self, engine):
        fake_audio = b"\x00\x01\x02\x03" * 100
        mock_communicate = MagicMock()
        mock_communicate.save = AsyncMock()

        with patch("claude_narrator.tts.edge.edge_tts.Communicate", return_value=mock_communicate):
            with patch("claude_narrator.tts.edge._communicate_to_bytes", new_callable=AsyncMock, return_value=fake_audio):
                result = await engine.synthesize("Hello world", language="en")
                assert isinstance(result, bytes)
                assert len(result) > 0

    def test_supports_streaming_false(self, engine):
        assert engine.supports_streaming is False


class TestEngineFactory:
    def test_create_edge_engine(self):
        engine = create_engine({"tts": {"engine": "edge-tts", "voice": "en-US-AriaNeural"}})
        assert isinstance(engine, EdgeTTSEngine)

    def test_unknown_engine_falls_back_to_edge(self):
        engine = create_engine({"tts": {"engine": "nonexistent", "voice": "en-US-AriaNeural"}})
        assert isinstance(engine, EdgeTTSEngine)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_tts.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement TTS base and edge-tts engine**

`src/claude_narrator/tts/base.py`:
```python
"""Abstract base class for TTS engines."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TTSEngine(ABC):
    """TTS engine that synthesizes text to audio bytes."""

    @abstractmethod
    async def synthesize(self, text: str, language: str = "en") -> bytes:
        """Synthesize text to audio bytes (MP3/WAV)."""

    @property
    def supports_streaming(self) -> bool:
        """Whether this engine supports streaming synthesis."""
        return False
```

`src/claude_narrator/tts/edge.py`:
```python
"""Edge-TTS engine implementation."""

from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path

import edge_tts

from claude_narrator.tts.base import TTSEngine

logger = logging.getLogger(__name__)


async def _communicate_to_bytes(communicate: edge_tts.Communicate) -> bytes:
    """Collect edge-tts output into bytes."""
    chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)


class EdgeTTSEngine(TTSEngine):
    """TTS engine using Microsoft Edge TTS (free, high quality)."""

    # Language → default voice mapping
    VOICE_MAP = {
        "en": "en-US-AriaNeural",
        "zh": "zh-CN-XiaoxiaoNeural",
        "ja": "ja-JP-NanamiNeural",
    }

    def __init__(self, voice: str = "en-US-AriaNeural") -> None:
        self._voice = voice

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        """Synthesize text to MP3 bytes using edge-tts."""
        voice = self._voice
        if voice == "en-US-AriaNeural" and language != "en":
            voice = self.VOICE_MAP.get(language, voice)

        communicate = edge_tts.Communicate(text=text, voice=voice)
        return await _communicate_to_bytes(communicate)
```

`src/claude_narrator/tts/__init__.py`:
```python
"""TTS engine factory."""

from __future__ import annotations

from typing import Any

from claude_narrator.tts.base import TTSEngine
from claude_narrator.tts.edge import EdgeTTSEngine


def create_engine(config: dict[str, Any]) -> TTSEngine:
    """Create TTS engine from config."""
    tts_config = config.get("tts", {})
    engine_name = tts_config.get("engine", "edge-tts")
    voice = tts_config.get("voice", "en-US-AriaNeural")

    if engine_name == "edge-tts":
        return EdgeTTSEngine(voice=voice)

    # Fallback to edge-tts for unknown engines
    return EdgeTTSEngine(voice=voice)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_tts.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/claude_narrator/tts/ tests/test_tts.py
git commit -m "feat: TTS engine abstraction with edge-tts implementation"
```

---

### Task 6: Audio Player

**Files:**
- Create: `src/claude_narrator/player.py`
- Create: `tests/test_player.py`

- [ ] **Step 1: Write failing tests**

`tests/test_player.py`:
```python
from unittest.mock import patch, MagicMock

import pytest

from claude_narrator.player import AudioPlayer


class TestAudioPlayer:
    @pytest.fixture
    def player(self):
        with patch("claude_narrator.player.pygame") as mock_pg:
            mock_pg.mixer = MagicMock()
            p = AudioPlayer()
            yield p, mock_pg

    async def test_play_calls_pygame(self, player):
        p, mock_pg = player
        fake_audio = b"\x00\x01\x02" * 100
        await p.play(fake_audio)
        mock_pg.mixer.music.load.assert_called_once()
        mock_pg.mixer.music.play.assert_called_once()

    async def test_stop_calls_pygame_stop(self, player):
        p, mock_pg = player
        await p.stop()
        mock_pg.mixer.music.stop.assert_called_once()

    async def test_is_playing(self, player):
        p, mock_pg = player
        mock_pg.mixer.music.get_busy.return_value = True
        assert p.is_playing is True
        mock_pg.mixer.music.get_busy.return_value = False
        assert p.is_playing is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_player.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement audio player**

`src/claude_narrator/player.py`:
```python
"""Audio player using pygame.mixer."""

from __future__ import annotations

import asyncio
import io
import logging
import os

# Suppress pygame welcome message
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Async audio player wrapping pygame.mixer."""

    def __init__(self) -> None:
        self._initialized = False
        self._init_mixer()

    def _init_mixer(self) -> None:
        try:
            pygame.mixer.init()
            self._initialized = True
        except pygame.error as e:
            logger.error("Failed to initialize audio mixer: %s", e)

    async def play(self, audio_data: bytes) -> None:
        """Play audio data (MP3 bytes). Blocks until playback starts."""
        if not self._initialized:
            return
        buf = io.BytesIO(audio_data)
        await asyncio.to_thread(self._play_sync, buf)

    def _play_sync(self, buf: io.BytesIO) -> None:
        try:
            pygame.mixer.music.load(buf)
            pygame.mixer.music.play()
        except pygame.error as e:
            logger.error("Playback error: %s", e)

    async def stop(self) -> None:
        """Stop current playback immediately."""
        if self._initialized:
            pygame.mixer.music.stop()

    @property
    def is_playing(self) -> bool:
        """Whether audio is currently playing."""
        if not self._initialized:
            return False
        return pygame.mixer.music.get_busy()

    async def wait_until_done(self) -> None:
        """Wait until current playback finishes."""
        while self.is_playing:
            await asyncio.sleep(0.1)

    def cleanup(self) -> None:
        """Release mixer resources."""
        if self._initialized:
            pygame.mixer.quit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_player.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/claude_narrator/player.py tests/test_player.py
git commit -m "feat: async audio player with pygame.mixer"
```

---

### Task 7: Narration Queue

**Files:**
- Create: `src/claude_narrator/queue.py`
- Create: `tests/test_queue.py`

- [ ] **Step 1: Write failing tests**

`tests/test_queue.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_queue.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement priority queue**

`src/claude_narrator/queue.py`:
```python
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
                # Drop the oldest low-priority item
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_queue.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/claude_narrator/queue.py tests/test_queue.py
git commit -m "feat: priority narration queue with overflow management"
```

---

### Task 8: Daemon Core

**Files:**
- Create: `src/claude_narrator/daemon.py`
- Create: `tests/test_daemon.py`

- [ ] **Step 1: Write failing tests**

`tests/test_daemon.py`:
```python
import asyncio
import json
import os
import signal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_narrator.daemon import Daemon, PIDManager


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

        socket_path = tmp_config_dir / "test.sock"
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_daemon.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement daemon**

`src/claude_narrator/daemon.py`:
```python
"""TTS Daemon: asyncio main loop, PID management, event processing."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any

from claude_narrator.config import CONFIG_DIR, load_config
from claude_narrator.ipc import create_server
from claude_narrator.ipc.base import IPCServer
from claude_narrator.narration.template import TemplateNarrator
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
        self._narrator = TemplateNarrator(
            language=self._config["general"]["language"]
        )
        self._queue = NarrationQueue(
            max_size=self._config["narration"]["max_queue_size"]
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
        """Receive events from IPC and queue narration items."""
        assert self._server is not None
        async for event in self._server.events():
            if not self._running:
                break
            if not self._config["general"]["enabled"]:
                continue

            text = self._narrator.narrate(event)
            if text is None:
                continue

            event_name = event.get("hook_event_name", "")
            priority = EVENT_PRIORITY.get(event_name, Priority.LOW)
            item = NarrationItem(text=text, priority=priority, event=event)
            await self._queue.put(item)

            # If high priority, interrupt current playback
            if priority == Priority.HIGH and self._player and self._player.is_playing:
                await self._player.stop()

    async def _playback_loop(self) -> None:
        """Consume queue items and play TTS audio."""
        while self._running:
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            await self._tts_and_play(item.text)

    async def _tts_and_play(self, text: str) -> None:
        """Synthesize and play a narration text."""
        if not self._engine or not self._player:
            return
        try:
            audio = await self._engine.synthesize(
                text, language=self._config["general"]["language"]
            )
            await self._player.play(audio)
            await self._player.wait_until_done()
        except Exception as e:
            logger.error("TTS/playback error: %s", e)


def run_daemon(config_dir: Path | None = None, foreground: bool = False) -> None:
    """Entry point for starting the daemon."""
    daemon = Daemon(config_dir=config_dir)
    asyncio.run(daemon.start(foreground=foreground))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_daemon.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/claude_narrator/daemon.py tests/test_daemon.py
git commit -m "feat: daemon core with PID management and event processing loop"
```

---

### Task 9: Hook Script

**Files:**
- Create: `src/claude_narrator/hooks/on_event.py`
- Create: `tests/test_hook.py`

- [ ] **Step 1: Write failing tests**

`tests/test_hook.py`:
```python
import io
import json
from unittest.mock import patch, MagicMock

import pytest

from claude_narrator.hooks.on_event import parse_event, forward_event


class TestParseEvent:
    def test_parse_valid_json(self):
        data = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/src/app.py"},
            "session_id": "s1",
        })
        event = parse_event(io.StringIO(data))
        assert event["hook_event_name"] == "PreToolUse"
        assert event["tool_name"] == "Read"

    def test_parse_empty_stdin(self):
        event = parse_event(io.StringIO(""))
        assert event is None

    def test_parse_invalid_json(self):
        event = parse_event(io.StringIO("not json{{{"))
        assert event is None


class TestForwardEvent:
    def test_forward_calls_client_send(self):
        mock_client = MagicMock()
        event = {"hook_event_name": "Stop"}
        forward_event(event, client=mock_client)
        mock_client.send.assert_called_once_with(event)

    def test_forward_silent_on_error(self):
        mock_client = MagicMock()
        mock_client.send.side_effect = Exception("connection refused")
        event = {"hook_event_name": "Stop"}
        # Should not raise
        forward_event(event, client=mock_client)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_hook.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement hook script**

`src/claude_narrator/hooks/on_event.py`:
```python
"""Claude Code hook script: receive stdin JSON and forward to daemon.

Usage in hooks config:
  "command": "python -m claude_narrator.hooks.on_event"
"""

from __future__ import annotations

import json
import sys
from typing import IO, Any

from claude_narrator.ipc import create_client
from claude_narrator.ipc.base import IPCClient


def parse_event(stdin: IO[str]) -> dict[str, Any] | None:
    """Parse hook event from stdin JSON."""
    try:
        data = stdin.read()
        if not data.strip():
            return None
        return json.loads(data)
    except (json.JSONDecodeError, OSError):
        return None


def forward_event(
    event: dict[str, Any],
    client: IPCClient | None = None,
) -> None:
    """Forward event to daemon via IPC. Silent on failure."""
    if client is None:
        client = create_client()
    try:
        client.send(event)
    except Exception:
        pass  # Daemon not running — silently ignore


def main() -> None:
    """Entry point for hook script."""
    event = parse_event(sys.stdin)
    if event is not None:
        forward_event(event)


if __name__ == "__main__":
    main()
```

`src/claude_narrator/hooks/__init__.py` — keep empty.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_hook.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/claude_narrator/hooks/ tests/test_hook.py
git commit -m "feat: hook script for forwarding Claude Code events to daemon"
```

---

### Task 10: Installer

**Files:**
- Create: `src/claude_narrator/installer.py`
- Create: `tests/test_installer.py`

- [ ] **Step 1: Write failing tests**

`tests/test_installer.py`:
```python
import json
import sys

import pytest

from claude_narrator.installer import install_hooks, uninstall_hooks, _get_python_path


class TestInstallHooks:
    def test_install_creates_hooks_in_settings(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"
        settings_file.write_text("{}")

        install_hooks(claude_dir=tmp_claude_dir)

        settings = json.loads(settings_file.read_text())
        assert "hooks" in settings
        assert "PreToolUse" in settings["hooks"]
        assert "Stop" in settings["hooks"]
        assert "Notification" in settings["hooks"]

    def test_install_preserves_existing_settings(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"theme": "dark"}))

        install_hooks(claude_dir=tmp_claude_dir)

        settings = json.loads(settings_file.read_text())
        assert settings["theme"] == "dark"
        assert "hooks" in settings

    def test_install_preserves_existing_hooks(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"
        existing = {
            "hooks": {
                "PreToolUse": [{"matcher": "Write", "hooks": [{"type": "command", "command": "echo hi"}]}]
            }
        }
        settings_file.write_text(json.dumps(existing))

        install_hooks(claude_dir=tmp_claude_dir)

        settings = json.loads(settings_file.read_text())
        # Should have both existing and narrator hooks for PreToolUse
        pre_hooks = settings["hooks"]["PreToolUse"]
        assert len(pre_hooks) >= 2

    def test_install_creates_settings_if_missing(self, tmp_claude_dir):
        install_hooks(claude_dir=tmp_claude_dir)
        settings_file = tmp_claude_dir / "settings.json"
        assert settings_file.exists()


class TestUninstallHooks:
    def test_uninstall_removes_narrator_hooks(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"

        install_hooks(claude_dir=tmp_claude_dir)
        uninstall_hooks(claude_dir=tmp_claude_dir)

        settings = json.loads(settings_file.read_text())
        hooks = settings.get("hooks", {})
        for event_hooks in hooks.values():
            for hook_group in event_hooks:
                for h in hook_group.get("hooks", []):
                    assert "claude_narrator" not in h.get("command", "")


class TestGetPythonPath:
    def test_returns_current_python(self):
        path = _get_python_path()
        assert sys.executable in path or "python" in path
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_installer.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement installer**

`src/claude_narrator/installer.py`:
```python
"""Install/uninstall narrator hooks into Claude Code settings.json."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CLAUDE_DIR = Path.home() / ".claude"
NARRATOR_MARKER = "claude_narrator.hooks.on_event"

HOOK_EVENTS = [
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "Stop",
    "Notification",
    "SubagentStart",
    "SubagentStop",
    "SessionStart",
    "PreCompact",
]


def _get_python_path() -> str:
    """Get the Python interpreter path where claude_narrator is installed."""
    return sys.executable


def _make_hook_entry(python_path: str) -> dict[str, Any]:
    """Create a single hook entry for narrator."""
    return {
        "matcher": "*",
        "hooks": [
            {
                "type": "command",
                "command": f"{python_path} -m {NARRATOR_MARKER}",
                "timeout": 5,
            }
        ],
    }


def install_hooks(claude_dir: Path | None = None) -> None:
    """Inject narrator hooks into ~/.claude/settings.json."""
    claude_dir = claude_dir or CLAUDE_DIR
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_file = claude_dir / "settings.json"

    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            settings = {}
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    python_path = _get_python_path()
    entry = _make_hook_entry(python_path)

    for event in HOOK_EVENTS:
        event_hooks = hooks.setdefault(event, [])
        # Don't add duplicate
        already = any(
            NARRATOR_MARKER in h.get("command", "")
            for group in event_hooks
            for h in group.get("hooks", [])
        )
        if not already:
            event_hooks.append(entry)

    settings["hooks"] = hooks
    settings_file.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Hooks installed to %s", settings_file)


def uninstall_hooks(claude_dir: Path | None = None) -> None:
    """Remove narrator hooks from ~/.claude/settings.json."""
    claude_dir = claude_dir or CLAUDE_DIR
    settings_file = claude_dir / "settings.json"
    if not settings_file.exists():
        return

    try:
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    hooks = settings.get("hooks", {})
    for event in HOOK_EVENTS:
        if event in hooks:
            hooks[event] = [
                group
                for group in hooks[event]
                if not any(
                    NARRATOR_MARKER in h.get("command", "")
                    for h in group.get("hooks", [])
                )
            ]
            if not hooks[event]:
                del hooks[event]

    if not hooks:
        settings.pop("hooks", None)

    settings_file.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Hooks uninstalled from %s", settings_file)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_installer.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/claude_narrator/installer.py tests/test_installer.py
git commit -m "feat: installer for injecting/removing hooks in settings.json"
```

---

### Task 11: CLI

**Files:**
- Create: `src/claude_narrator/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

`tests/test_cli.py`:
```python
from click.testing import CliRunner

import pytest

from claude_narrator.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestCLI:
    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "claude-narrator" in result.output.lower() or "Usage" in result.output

    def test_test_command_exists(self, runner):
        result = runner.invoke(main, ["test", "--help"])
        assert result.exit_code == 0

    def test_start_command_exists(self, runner):
        result = runner.invoke(main, ["start", "--help"])
        assert result.exit_code == 0

    def test_stop_command_exists(self, runner):
        result = runner.invoke(main, ["stop", "--help"])
        assert result.exit_code == 0

    def test_install_command_exists(self, runner):
        result = runner.invoke(main, ["install", "--help"])
        assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement CLI**

`src/claude_narrator/cli.py`:
```python
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
        # Start as background process
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
```

Add `__main__.py` entry for daemon background launch:

`src/claude_narrator/__main__.py`:
```python
"""Allow running daemon via: python -m claude_narrator.daemon"""
from claude_narrator.daemon import run_daemon

if __name__ == "__main__":
    run_daemon()
```

Wait — this should be `src/claude_narrator/daemon.py` already has `run_daemon`. We need `__main__.py` at the claude_narrator level to support `python -m claude_narrator.daemon`. Actually, the daemon.py already needs a `if __name__ == "__main__"` guard. Let me add it to daemon.py.

Add to the bottom of `src/claude_narrator/daemon.py`:
```python
if __name__ == "__main__":
    run_daemon()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Verify end-to-end CLI**

Run: `claude-narrator --help`
Expected: Shows group help with start, stop, test, install, uninstall commands

Run: `claude-narrator install --help`
Expected: Shows install command help

- [ ] **Step 6: Commit**

```bash
git add src/claude_narrator/cli.py src/claude_narrator/__main__.py tests/test_cli.py
git commit -m "feat: CLI with start, stop, test, and install commands"
```

---

### Task 12: README and Integration Verification

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

`README.md`:
```markdown
# Claude Narrator

> TTS audio narration for Claude Code — hear what Claude is doing without watching the terminal.

Claude Narrator is a plugin that uses Claude Code's hooks system to speak out work status in real-time. It tells you when files are being read, edited, commands executed, tasks completed, and when your attention is needed.

## Quick Start

### Install

\`\`\`bash
pip install claude-narrator
claude-narrator install
claude-narrator start
\`\`\`

### Test

\`\`\`bash
claude-narrator test "Hello, this is a test"
\`\`\`

### Usage

\`\`\`bash
claude-narrator start        # Start the narration daemon
claude-narrator stop         # Stop the daemon
claude-narrator test "text"  # Test TTS output
claude-narrator install      # Install hooks into Claude Code
claude-narrator uninstall    # Remove hooks
\`\`\`

## Configuration

Config file: `~/.claude-narrator/config.json`

\`\`\`json
{
  "general": {
    "verbosity": "normal",
    "language": "en",
    "enabled": true
  },
  "tts": {
    "engine": "edge-tts",
    "voice": "en-US-AriaNeural"
  }
}
\`\`\`

### Verbosity Levels

| Level | What gets narrated |
|-------|-------------------|
| `minimal` | Task completion, errors, permission prompts |
| `normal` | Above + file operations, subagent activity |
| `verbose` | Everything |

### Supported TTS Engines

| Engine | Platform | Notes |
|--------|----------|-------|
| `edge-tts` (default) | All | Free, high quality, requires internet |
| `say` | macOS | System built-in, zero dependencies |
| `espeak` | Linux | Offline, install via package manager |
| `openai` | All | Best quality, requires API key |

## Requirements

- Python 3.10+
- Claude Code v1.0.80+

## License

MIT
```

- [ ] **Step 2: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Verify end-to-end installation flow**

Run:
```bash
pip install -e ".[dev]"
claude-narrator install
cat ~/.claude/settings.json | python -m json.tool | grep claude_narrator
```
Expected: Shows narrator hooks in settings.json

Run: `claude-narrator start -f &` (background, then `claude-narrator stop`)
Expected: Daemon starts and stops cleanly

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README with quick start and configuration guide"
```

---

## Phase 2: Polish

### Task 13: Verbosity Filter

**Files:**
- Create: `src/claude_narrator/narration/verbosity.py`
- Create: `tests/test_verbosity.py`

- [ ] **Step 1: Write failing tests**

`tests/test_verbosity.py`:
```python
import pytest
from claude_narrator.narration.verbosity import should_narrate


class TestVerbosityFilter:
    def test_minimal_allows_stop(self):
        assert should_narrate("Stop", "Read", "minimal") is True

    def test_minimal_allows_notification(self):
        assert should_narrate("Notification", None, "minimal") is True

    def test_minimal_allows_failure(self):
        assert should_narrate("PostToolUseFailure", "Bash", "minimal") is True

    def test_minimal_blocks_pre_tool_use(self):
        assert should_narrate("PreToolUse", "Read", "minimal") is False

    def test_minimal_blocks_session_start(self):
        assert should_narrate("SessionStart", None, "minimal") is False

    def test_normal_allows_pre_tool_use_file_ops(self):
        assert should_narrate("PreToolUse", "Read", "normal") is True
        assert should_narrate("PreToolUse", "Write", "normal") is True
        assert should_narrate("PreToolUse", "Edit", "normal") is True

    def test_normal_allows_subagent(self):
        assert should_narrate("SubagentStart", None, "normal") is True
        assert should_narrate("SubagentStop", None, "normal") is True

    def test_normal_blocks_bash_pre(self):
        assert should_narrate("PreToolUse", "Bash", "normal") is False

    def test_normal_blocks_session_start(self):
        assert should_narrate("SessionStart", None, "normal") is False

    def test_verbose_allows_everything(self):
        assert should_narrate("PreToolUse", "Bash", "verbose") is True
        assert should_narrate("SessionStart", None, "verbose") is True
        assert should_narrate("PreCompact", None, "verbose") is True
```

- [ ] **Step 2: Implement verbosity filter**

`src/claude_narrator/narration/verbosity.py`:
```python
"""Verbosity-based event filtering."""

from __future__ import annotations

# Events that always pass (minimal level)
MINIMAL_EVENTS = {"Stop", "Notification", "PostToolUseFailure"}

# Additional events for normal level
NORMAL_EVENTS = MINIMAL_EVENTS | {"SubagentStart", "SubagentStop"}

# Tools that pass at normal level for Pre/PostToolUse
NORMAL_TOOLS = {"Read", "Write", "Edit", "Glob", "Grep", "Agent"}


def should_narrate(
    event_name: str,
    tool_name: str | None,
    verbosity: str,
) -> bool:
    """Decide whether to narrate this event given the verbosity level."""
    if verbosity == "verbose":
        return True

    if event_name in MINIMAL_EVENTS:
        return True

    if verbosity == "minimal":
        return False

    # verbosity == "normal"
    if event_name in NORMAL_EVENTS:
        return True

    if event_name in ("PreToolUse", "PostToolUse") and tool_name in NORMAL_TOOLS:
        return True

    return False
```

- [ ] **Step 3: Integrate into daemon.py**

Add to `daemon.py` `_event_loop`:
```python
from claude_narrator.narration.verbosity import should_narrate

# In _event_loop, after getting event:
event_name = event.get("hook_event_name", "")
tool_name = event.get("tool_name")
verbosity = self._config["general"]["verbosity"]
if not should_narrate(event_name, tool_name, verbosity):
    continue
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_verbosity.py tests/test_daemon.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/claude_narrator/narration/verbosity.py tests/test_verbosity.py src/claude_narrator/daemon.py
git commit -m "feat: verbosity-based event filtering (minimal/normal/verbose)"
```

---

### Task 14: Event Coalescer

**Files:**
- Create: `src/claude_narrator/narration/coalescer.py`
- Create: `tests/test_coalescer.py`

- [ ] **Step 1: Write failing tests**

`tests/test_coalescer.py`:
```python
import asyncio
import time

import pytest
from claude_narrator.narration.coalescer import EventCoalescer


class TestEventCoalescer:
    @pytest.fixture
    def coalescer(self):
        return EventCoalescer(window_seconds=0.3)

    async def test_single_event_passes_through(self, coalescer):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read",
                 "tool_input": {"file_path": "/a.py"}}
        result = await coalescer.process(event)
        # First event should be held briefly then emitted
        await asyncio.sleep(0.4)
        result = coalescer.flush()
        assert result is not None
        assert result["hook_event_name"] == "PreToolUse"

    async def test_rapid_same_tool_merged(self, coalescer):
        for i in range(5):
            event = {"hook_event_name": "PreToolUse", "tool_name": "Read",
                     "tool_input": {"file_path": f"/file{i}.py"}}
            await coalescer.process(event)

        await asyncio.sleep(0.4)
        result = coalescer.flush()
        assert result is not None
        assert result.get("_coalesced_count", 1) == 5

    async def test_different_tools_not_merged(self, coalescer):
        await coalescer.process({"hook_event_name": "PreToolUse", "tool_name": "Read",
                                  "tool_input": {"file_path": "/a.py"}})
        await asyncio.sleep(0.4)
        r1 = coalescer.flush()

        await coalescer.process({"hook_event_name": "PreToolUse", "tool_name": "Write",
                                  "tool_input": {"file_path": "/b.py"}})
        await asyncio.sleep(0.4)
        r2 = coalescer.flush()

        assert r1 is not None
        assert r2 is not None
        assert r1["tool_name"] != r2["tool_name"]

    async def test_high_priority_not_held(self, coalescer):
        event = {"hook_event_name": "Notification"}
        result = await coalescer.process(event)
        assert result is not None  # High priority passes immediately
```

- [ ] **Step 2: Implement coalescer**

`src/claude_narrator/narration/coalescer.py`:
```python
"""Event coalescer: merge rapid consecutive events of the same type."""

from __future__ import annotations

import time
from typing import Any

from claude_narrator.queue import EVENT_PRIORITY, Priority

# Events that bypass coalescing
IMMEDIATE_EVENTS = {"Notification", "PostToolUseFailure", "Stop"}


class EventCoalescer:
    """Merge rapid consecutive events of the same tool type."""

    def __init__(self, window_seconds: float = 2.0) -> None:
        self._window = window_seconds
        self._pending: dict[str, Any] | None = None
        self._pending_key: str = ""
        self._pending_count: int = 0
        self._pending_time: float = 0.0

    def _event_key(self, event: dict[str, Any]) -> str:
        return f"{event.get('hook_event_name', '')}:{event.get('tool_name', '')}"

    async def process(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Process an event. Returns immediately for high-priority; holds others for coalescing."""
        event_name = event.get("hook_event_name", "")

        if event_name in IMMEDIATE_EVENTS:
            # Flush any pending event first, then return this one immediately
            return event

        key = self._event_key(event)
        now = time.monotonic()

        if self._pending is not None and key == self._pending_key:
            if now - self._pending_time < self._window:
                # Same key within window → merge
                self._pending_count += 1
                self._pending["_coalesced_count"] = self._pending_count
                return None

        # Different key or window expired → new pending
        self._pending = event
        self._pending_key = key
        self._pending_count = 1
        self._pending_time = now
        return None

    def flush(self) -> dict[str, Any] | None:
        """Flush the pending coalesced event."""
        if self._pending is None:
            return None
        result = self._pending
        if self._pending_count > 1:
            result["_coalesced_count"] = self._pending_count
        self._pending = None
        self._pending_key = ""
        self._pending_count = 0
        return result
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_coalescer.py -v`
Expected: All PASS

- [ ] **Step 4: Integrate into daemon and update template narrator for coalesced events**

Add coalesced count support to `narration/template.py` `_extract_variables`:
```python
if "_coalesced_count" in event:
    count = event["_coalesced_count"]
    variables["coalesced_count"] = str(count)
```

Update `TemplateNarrator.narrate()` to handle coalesced events:
```python
# After getting template text, if coalesced:
if event.get("_coalesced_count", 1) > 1:
    count = event["_coalesced_count"]
    tool = event.get("tool_name", "operations")
    return f"{count} {tool} operations"
```

- [ ] **Step 5: Commit**

```bash
git add src/claude_narrator/narration/coalescer.py tests/test_coalescer.py src/claude_narrator/narration/template.py src/claude_narrator/daemon.py
git commit -m "feat: event coalescer for merging rapid consecutive events"
```

---

### Task 15: Interruptible Playback

**Files:**
- Modify: `src/claude_narrator/daemon.py`
- Modify: `tests/test_daemon.py`

- [ ] **Step 1: Update daemon playback loop to support interruption**

In `daemon.py`, modify `_playback_loop`:
```python
async def _playback_loop(self) -> None:
    """Consume queue items and play TTS audio, with interrupt support."""
    while self._running:
        try:
            item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue

        await self._tts_and_play(item.text)

async def _tts_and_play(self, text: str) -> None:
    """Synthesize and play with interrupt checking."""
    if not self._engine or not self._player:
        return
    try:
        audio = await self._engine.synthesize(
            text, language=self._config["general"]["language"]
        )
        await self._player.play(audio)

        # Wait for playback to finish, but check for interrupts
        while self._player.is_playing:
            if self._queue.has_interrupt:
                await self._player.stop()
                break
            await asyncio.sleep(0.1)
    except Exception as e:
        logger.error("TTS/playback error: %s", e)
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_daemon.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add src/claude_narrator/daemon.py
git commit -m "feat: interruptible playback - high priority events stop current audio"
```

---

### Task 16: macOS Say Engine

**Files:**
- Create: `src/claude_narrator/tts/macos_say.py`
- Modify: `src/claude_narrator/tts/__init__.py`
- Modify: `tests/test_tts.py`

- [ ] **Step 1: Add tests**

Append to `tests/test_tts.py`:
```python
import sys
from claude_narrator.tts.macos_say import MacOSSayEngine

class TestMacOSSayEngine:
    @pytest.fixture
    def engine(self):
        return MacOSSayEngine(voice="Samantha")

    async def test_synthesize_calls_subprocess(self, engine):
        with patch("claude_narrator.tts.macos_say.asyncio.create_subprocess_exec") as mock_proc:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"audio data", b""))
            mock_process.returncode = 0
            mock_proc.return_value = mock_process

            with patch("builtins.open", MagicMock(return_value=MagicMock(
                __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=b"audio"))),
                __exit__=MagicMock()
            ))):
                with patch("pathlib.Path.unlink"):
                    with patch("pathlib.Path.exists", return_value=True):
                        result = await engine.synthesize("Hello", language="en")
```

- [ ] **Step 2: Implement macOS say engine**

`src/claude_narrator/tts/macos_say.py`:
```python
"""macOS 'say' command TTS engine."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from claude_narrator.tts.base import TTSEngine


class MacOSSayEngine(TTSEngine):
    """TTS using macOS built-in 'say' command."""

    VOICE_MAP = {"en": "Samantha", "zh": "Ting-Ting", "ja": "Kyoko"}

    def __init__(self, voice: str = "Samantha") -> None:
        self._voice = voice

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        voice = self._voice
        if voice == "Samantha" and language != "en":
            voice = self.VOICE_MAP.get(language, voice)

        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as f:
            tmp_path = Path(f.name)

        try:
            proc = await asyncio.create_subprocess_exec(
                "say", "-v", voice, "-o", str(tmp_path), text,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()
            if tmp_path.exists():
                return tmp_path.read_bytes()
            return b""
        finally:
            tmp_path.unlink(missing_ok=True)
```

- [ ] **Step 3: Update factory in tts/__init__.py**

Add to `create_engine`:
```python
if engine_name == "say":
    from claude_narrator.tts.macos_say import MacOSSayEngine
    return MacOSSayEngine(voice=voice)
```

- [ ] **Step 4: Run tests and commit**

```bash
python -m pytest tests/test_tts.py -v
git add src/claude_narrator/tts/macos_say.py src/claude_narrator/tts/__init__.py tests/test_tts.py
git commit -m "feat: macOS say TTS engine"
```

---

### Task 17: Espeak Engine

**Files:**
- Create: `src/claude_narrator/tts/espeak.py`
- Modify: `src/claude_narrator/tts/__init__.py`

- [ ] **Step 1: Implement espeak engine**

`src/claude_narrator/tts/espeak.py`:
```python
"""espeak-ng TTS engine for Linux."""

from __future__ import annotations

import asyncio

from claude_narrator.tts.base import TTSEngine


class EspeakEngine(TTSEngine):
    """TTS using espeak-ng (Linux offline TTS)."""

    VOICE_MAP = {"en": "en", "zh": "zh", "ja": "ja"}

    def __init__(self, voice: str = "en") -> None:
        self._voice = voice

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        voice = self.VOICE_MAP.get(language, self._voice)
        proc = await asyncio.create_subprocess_exec(
            "espeak-ng", "--stdout", "-v", voice, text,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        return stdout or b""
```

- [ ] **Step 2: Update factory and commit**

Add to `tts/__init__.py` `create_engine`:
```python
if engine_name == "espeak":
    from claude_narrator.tts.espeak import EspeakEngine
    return EspeakEngine(voice=voice)
```

```bash
git add src/claude_narrator/tts/espeak.py src/claude_narrator/tts/__init__.py
git commit -m "feat: espeak-ng TTS engine for Linux"
```

---

### Task 18: OpenAI TTS Engine

**Files:**
- Create: `src/claude_narrator/tts/openai_tts.py`
- Modify: `src/claude_narrator/tts/__init__.py`

- [ ] **Step 1: Implement OpenAI TTS engine**

`src/claude_narrator/tts/openai_tts.py`:
```python
"""OpenAI TTS API engine."""

from __future__ import annotations

import os

import httpx

from claude_narrator.tts.base import TTSEngine


class OpenAITTSEngine(TTSEngine):
    """TTS using OpenAI's text-to-speech API."""

    def __init__(
        self,
        voice: str = "nova",
        model: str = "tts-1",
        api_key_env: str = "OPENAI_API_KEY",
    ) -> None:
        self._voice = voice
        self._model = model
        self._api_key = os.environ.get(api_key_env, "")

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY not set")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "input": text,
                    "voice": self._voice,
                    "response_format": "mp3",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.content
```

- [ ] **Step 2: Update factory and commit**

Add to `tts/__init__.py` `create_engine`:
```python
if engine_name == "openai":
    from claude_narrator.tts.openai_tts import OpenAITTSEngine
    openai_cfg = tts_config.get("openai", {})
    return OpenAITTSEngine(
        voice=openai_cfg.get("voice", "nova"),
        model=openai_cfg.get("model", "tts-1"),
        api_key_env=openai_cfg.get("api_key_env", "OPENAI_API_KEY"),
    )
```

```bash
git add src/claude_narrator/tts/openai_tts.py src/claude_narrator/tts/__init__.py
git commit -m "feat: OpenAI TTS engine"
```

---

### Task 19: Multi-language Templates

**Files:**
- Create: `src/claude_narrator/i18n/zh.json`
- Create: `src/claude_narrator/i18n/ja.json`

- [ ] **Step 1: Create Chinese templates**

`src/claude_narrator/i18n/zh.json`:
```json
{
    "PreToolUse": {
        "Read": "正在读取 {file_path}",
        "Write": "准备写入 {file_path}",
        "Edit": "准备编辑 {file_path}",
        "Bash": "执行命令",
        "Glob": "搜索文件",
        "Grep": "搜索内容",
        "Agent": "启动代理",
        "default": "调用 {tool_name}"
    },
    "PostToolUse": {
        "Read": "读取完成",
        "Write": "写入完成",
        "Edit": "编辑完成",
        "Bash": "命令完成",
        "default": "{tool_name} 完成"
    },
    "PostToolUseFailure": {
        "Bash": "命令失败",
        "default": "{tool_name} 失败"
    },
    "Stop": {
        "default": "任务完成"
    },
    "Notification": {
        "default": "需要你的注意"
    },
    "SubagentStart": {
        "default": "启动子任务"
    },
    "SubagentStop": {
        "default": "子任务完成"
    },
    "SessionStart": {
        "default": "会话开始"
    },
    "PreCompact": {
        "default": "上下文压缩中"
    }
}
```

- [ ] **Step 2: Create Japanese templates**

`src/claude_narrator/i18n/ja.json`:
```json
{
    "PreToolUse": {
        "Read": "{file_path} を読み込み中",
        "Write": "{file_path} に書き込み中",
        "Edit": "{file_path} を編集中",
        "Bash": "コマンド実行中",
        "Glob": "ファイル検索中",
        "Grep": "コード検索中",
        "Agent": "エージェント起動",
        "default": "{tool_name} を使用中"
    },
    "PostToolUse": {
        "Read": "読み込み完了",
        "Write": "書き込み完了",
        "Edit": "編集完了",
        "Bash": "コマンド完了",
        "default": "{tool_name} 完了"
    },
    "PostToolUseFailure": {
        "Bash": "コマンド失敗",
        "default": "{tool_name} 失敗"
    },
    "Stop": {
        "default": "タスク完了"
    },
    "Notification": {
        "default": "確認が必要です"
    },
    "SubagentStart": {
        "default": "サブタスク開始"
    },
    "SubagentStop": {
        "default": "サブタスク完了"
    },
    "SessionStart": {
        "default": "セッション開始"
    },
    "PreCompact": {
        "default": "コンテキスト圧縮中"
    }
}
```

- [ ] **Step 3: Test language loading**

Add to `tests/test_template.py`:
```python
class TestMultiLanguage:
    def test_chinese_narrator(self):
        narrator = TemplateNarrator(language="zh")
        event = {"hook_event_name": "Stop"}
        assert narrator.narrate(event) == "任务完成"

    def test_japanese_narrator(self):
        narrator = TemplateNarrator(language="ja")
        event = {"hook_event_name": "Stop"}
        assert narrator.narrate(event) == "タスク完了"

    def test_fallback_to_english(self):
        narrator = TemplateNarrator(language="xx")
        event = {"hook_event_name": "Stop"}
        assert narrator.narrate(event) == "Task complete"
```

- [ ] **Step 4: Run tests and commit**

```bash
python -m pytest tests/test_template.py -v
git add src/claude_narrator/i18n/ tests/test_template.py
git commit -m "feat: Chinese and Japanese narration templates"
```

---

### Task 20: Audio Cache

**Files:**
- Create: `src/claude_narrator/cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write failing tests**

`tests/test_cache.py`:
```python
import pytest
from claude_narrator.cache import AudioCache


class TestAudioCache:
    @pytest.fixture
    def cache(self, tmp_path):
        return AudioCache(cache_dir=tmp_path / "cache", max_size_mb=1)

    def test_get_miss(self, cache):
        assert cache.get("edge-tts", "voice", "en", "hello") is None

    def test_put_and_get(self, cache):
        audio = b"\x00\x01\x02" * 100
        cache.put("edge-tts", "voice", "en", "hello", audio)
        result = cache.get("edge-tts", "voice", "en", "hello")
        assert result == audio

    def test_eviction_on_size_limit(self, cache):
        # Fill cache beyond 1MB
        big_audio = b"\x00" * (600 * 1024)  # 600KB
        cache.put("e", "v", "en", "a", big_audio)
        cache.put("e", "v", "en", "b", big_audio)
        # Adding third should evict oldest
        cache.put("e", "v", "en", "c", big_audio)
        # At least one old entry should be evicted
        total = sum(1 for x in [cache.get("e", "v", "en", k) for k in "abc"] if x)
        assert total <= 2

    def test_clear(self, cache):
        cache.put("e", "v", "en", "hello", b"audio")
        cache.clear()
        assert cache.get("e", "v", "en", "hello") is None
```

- [ ] **Step 2: Implement cache**

`src/claude_narrator/cache.py`:
```python
"""LRU file-based audio cache."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioCache:
    """File-based LRU audio cache."""

    def __init__(self, cache_dir: Path, max_size_mb: int = 50) -> None:
        self._dir = cache_dir
        self._max_bytes = max_size_mb * 1024 * 1024
        self._dir.mkdir(parents=True, exist_ok=True)

    def _key(self, engine: str, voice: str, lang: str, text: str) -> str:
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"{engine}_{voice}_{lang}_{text_hash}"

    def _path(self, key: str) -> Path:
        return self._dir / f"{key}.mp3"

    def get(self, engine: str, voice: str, lang: str, text: str) -> bytes | None:
        path = self._path(self._key(engine, voice, lang, text))
        if path.exists():
            path.touch()  # Update access time for LRU
            return path.read_bytes()
        return None

    def put(self, engine: str, voice: str, lang: str, text: str, audio: bytes) -> None:
        self._evict_if_needed(len(audio))
        path = self._path(self._key(engine, voice, lang, text))
        path.write_bytes(audio)

    def clear(self) -> None:
        for f in self._dir.glob("*.mp3"):
            f.unlink(missing_ok=True)

    def _evict_if_needed(self, incoming_bytes: int) -> None:
        files = sorted(self._dir.glob("*.mp3"), key=lambda f: f.stat().st_mtime)
        total = sum(f.stat().st_size for f in files) + incoming_bytes
        while total > self._max_bytes and files:
            oldest = files.pop(0)
            total -= oldest.stat().st_size
            oldest.unlink(missing_ok=True)
```

- [ ] **Step 3: Integrate into daemon**

In `daemon.py`, add cache to `_tts_and_play`:
```python
from claude_narrator.cache import AudioCache

# In __init__:
cache_config = self._config.get("cache", {})
if cache_config.get("enabled", True):
    self._cache = AudioCache(
        cache_dir=self._config_dir / "cache",
        max_size_mb=cache_config.get("max_size_mb", 50),
    )
else:
    self._cache = None

# In _tts_and_play:
lang = self._config["general"]["language"]
engine_name = self._config["tts"]["engine"]
voice = self._config["tts"]["voice"]

if self._cache:
    cached = self._cache.get(engine_name, voice, lang, text)
    if cached:
        await self._player.play(cached)
        # ... wait logic
        return

audio = await self._engine.synthesize(text, language=lang)

if self._cache:
    self._cache.put(engine_name, voice, lang, text, audio)
```

- [ ] **Step 4: Run tests and commit**

```bash
python -m pytest tests/test_cache.py -v
git add src/claude_narrator/cache.py tests/test_cache.py src/claude_narrator/daemon.py
git commit -m "feat: LRU audio cache for frequently used narrations"
```

---

### Task 21: Full CLI (config, status, restart, cache)

**Files:**
- Modify: `src/claude_narrator/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add config, status, restart, cache commands**

Add to `cli.py`:
```python
@main.command()
def restart() -> None:
    """Restart the daemon."""
    from click import Context
    ctx = click.get_current_context()
    ctx.invoke(stop)
    import time
    time.sleep(1)
    ctx.invoke(start)


@main.command()
def status() -> None:
    """Show daemon status."""
    pid_mgr = PIDManager(CONFIG_DIR / "daemon.pid")
    if pid_mgr.is_running():
        config = load_config()
        click.echo(f"Status: Running (PID {pid_mgr.read()})")
        click.echo(f"Engine: {config['tts']['engine']}")
        click.echo(f"Verbosity: {config['general']['verbosity']}")
        click.echo(f"Language: {config['general']['language']}")
    else:
        click.echo("Status: Stopped")


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
            click.echo(f"Key not found: {key}")
            return
    click.echo(f"{key} = {value}")


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

    # Parse value
    if value.lower() in ("true", "false"):
        parsed_value = value.lower() == "true"
    elif value.isdigit():
        parsed_value = int(value)
    else:
        parsed_value = value

    parts = key.split(".")
    target = user_config
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = parsed_value

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        json_mod.dumps(user_config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    click.echo(f"Set {key} = {parsed_value}")


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
    from claude_narrator.cache import AudioCache
    cache = AudioCache(cache_dir=CONFIG_DIR / "cache")
    cache.clear()
    click.echo("Audio cache cleared.")
```

- [ ] **Step 2: Add CLI tests**

Append to `tests/test_cli.py`:
```python
    def test_status_command(self, runner):
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0

    def test_config_get(self, runner):
        result = runner.invoke(main, ["config", "get", "--help"])
        assert result.exit_code == 0

    def test_config_set(self, runner):
        result = runner.invoke(main, ["config", "set", "--help"])
        assert result.exit_code == 0

    def test_cache_clear(self, runner):
        result = runner.invoke(main, ["cache", "clear", "--help"])
        assert result.exit_code == 0
```

- [ ] **Step 3: Run tests and commit**

```bash
python -m pytest tests/test_cli.py -v
git add src/claude_narrator/cli.py tests/test_cli.py
git commit -m "feat: full CLI with config, status, restart, and cache commands"
```

---

### Task 22: Claude Code Plugin Format

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `commands/setup.md`
- Create: `commands/configure.md`
- Create: `commands/status.md`

- [ ] **Step 1: Create plugin.json**

`.claude-plugin/plugin.json`:
```json
{
    "name": "claude-narrator",
    "description": "TTS audio narration for Claude Code — hear what Claude is doing",
    "version": "0.1.0",
    "commands": [
        {
            "name": "setup",
            "description": "Interactive setup wizard for Claude Narrator",
            "entrypoint": "./commands/setup.md"
        },
        {
            "name": "configure",
            "description": "Configure narrator settings interactively",
            "entrypoint": "./commands/configure.md"
        },
        {
            "name": "status",
            "description": "Check narrator daemon status",
            "entrypoint": "./commands/status.md"
        }
    ],
    "author": "hoshizora",
    "license": "MIT",
    "homepage": "https://github.com/hoshizora/claude-narrator",
    "keywords": ["tts", "narration", "audio", "hooks", "accessibility"]
}
```

- [ ] **Step 2: Create marketplace.json**

`.claude-plugin/marketplace.json`:
```json
{
    "owner": "hoshizora",
    "description": "Hear what Claude Code is doing — TTS audio narration of work status via hooks",
    "category": "accessibility",
    "tags": ["tts", "audio", "narration", "hooks", "accessibility"],
    "source": "./"
}
```

- [ ] **Step 3: Create setup command**

`commands/setup.md`:
```markdown
---
name: setup
description: Interactive setup wizard for Claude Narrator
tools: [Bash, Read, Edit, AskUserQuestion]
---

# Claude Narrator Setup

You are setting up Claude Narrator, a TTS narration plugin. Follow these steps:

## Step 1: Check Python

Run `which python3 && python3 --version` to verify Python 3.10+ is available.

## Step 2: Check if claude-narrator is installed

Run `python3 -m claude_narrator --help 2>&1 || echo "NOT_INSTALLED"`.

If NOT_INSTALLED, tell the user to install it first:
```
pip install claude-narrator
```

## Step 3: Install hooks

Run `claude-narrator install` to inject hooks into settings.json.

## Step 4: Test TTS

Ask the user what language they prefer using AskUserQuestion (options: English, Chinese, Japanese).

Then run: `claude-narrator test "Hello, Claude Narrator is working"` (or the equivalent in their chosen language).

## Step 5: Start daemon

Run `claude-narrator start` to start the background daemon.

Tell the user setup is complete and they will now hear narration of Claude Code's work.
```

- [ ] **Step 4: Create configure and status commands**

`commands/configure.md`:
```markdown
---
name: configure
description: Configure narrator settings interactively
tools: [Bash, AskUserQuestion]
---

# Configure Claude Narrator

Use AskUserQuestion to let the user choose settings, then apply with `claude-narrator config set`.

1. Ask verbosity level (minimal/normal/verbose)
2. Ask TTS engine (edge-tts/say/espeak/openai)
3. Ask language (en/zh/ja)
4. Apply each choice with `claude-narrator config set <key> <value>`
5. Restart daemon: `claude-narrator restart`
```

`commands/status.md`:
```markdown
---
name: status
description: Check narrator daemon status
tools: [Bash]
---

Run `claude-narrator status` and show the output to the user.
```

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/ commands/
git commit -m "feat: Claude Code plugin format with setup, configure, and status commands"
```

---

### Task 23: PyPI Packaging + Chinese README

**Files:**
- Create: `README.zh.md`
- Verify: `pyproject.toml` is ready for publishing

- [ ] **Step 1: Create Chinese README**

`README.zh.md`:
```markdown
# Claude Narrator

> Claude Code 的 TTS 语音播报插件 —— 不看终端也能知道 AI 在做什么。

Claude Narrator 利用 Claude Code 的 Hooks 系统，实时用语音播报工作状态。文件读写、命令执行、任务完成、需要确认权限……统统用语音告诉你。

## 快速开始

\`\`\`bash
pip install claude-narrator
claude-narrator install
claude-narrator start
\`\`\`

## 测试

\`\`\`bash
claude-narrator test "你好，这是一条测试消息"
\`\`\`

## 配置

配置文件: `~/.claude-narrator/config.json`

\`\`\`json
{
  "general": {
    "verbosity": "normal",
    "language": "zh",
    "enabled": true
  },
  "tts": {
    "engine": "edge-tts",
    "voice": "zh-CN-XiaoxiaoNeural"
  }
}
\`\`\`

### Verbosity 等级

| 等级 | 播报内容 |
|------|---------|
| `minimal` | 任务完成、错误、权限请求 |
| `normal` | 以上 + 文件操作、子任务 |
| `verbose` | 所有事件 |

## 要求

- Python 3.10+
- Claude Code v1.0.80+

## 许可

MIT
```

- [ ] **Step 2: Verify packaging**

Run: `cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator && python -m build --sdist --wheel`
Expected: Creates dist/ with .tar.gz and .whl files

- [ ] **Step 3: Commit**

```bash
git add README.zh.md
git commit -m "docs: add Chinese README"
```

---

## Phase 3: Enhancement

### Task 24: LLM Narration Mode

**Files:**
- Create: `src/claude_narrator/narration/llm.py`
- Modify: `src/claude_narrator/narration/__init__.py`
- Modify: `src/claude_narrator/daemon.py`

- [ ] **Step 1: Implement LLM narrator**

`src/claude_narrator/narration/llm.py`:
```python
"""LLM-based narration: send event to LLM for natural language generation."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from claude_narrator.narration.template import TemplateNarrator

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a concise narrator for a coding assistant.
Given a hook event JSON, generate a single short sentence (under 15 words)
describing what is happening. Speak naturally, as if narrating to a developer.
Only output the narration text, nothing else."""


class LLMNarrator:
    """Generate narration using an LLM with template fallback."""

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "qwen2.5:3b",
        language: str = "en",
        timeout: float = 3.0,
    ) -> None:
        self._provider = provider
        self._model = model
        self._language = language
        self._timeout = timeout
        self._fallback = TemplateNarrator(language=language)
        self._recent_events: list[dict] = []

    async def narrate(self, event: dict[str, Any]) -> str | None:
        """Generate narration via LLM, falling back to template on timeout."""
        self._recent_events.append(event)
        if len(self._recent_events) > 3:
            self._recent_events.pop(0)

        try:
            result = await asyncio.wait_for(
                self._call_llm(event), timeout=self._timeout
            )
            return result
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug("LLM narration failed (%s), using template fallback", e)
            return self._fallback.narrate(event)

    async def _call_llm(self, event: dict[str, Any]) -> str:
        prompt = (
            f"Language: {self._language}\n"
            f"Recent events: {json.dumps(self._recent_events[-3:], default=str)}\n"
            f"Current event: {json.dumps(event, default=str)}\n"
            f"Generate narration:"
        )

        if self._provider == "ollama":
            return await self._call_ollama(prompt)
        elif self._provider == "openai":
            return await self._call_openai(prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {self._provider}")

    async def _call_ollama(self, prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "system": SYSTEM_PROMPT,
                    "stream": False,
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()["response"].strip()

    async def _call_openai(self, prompt: str) -> str:
        import os
        api_key = os.environ.get("OPENAI_API_KEY", "")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 50,
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
```

- [ ] **Step 2: Integrate into daemon**

In `daemon.py`, update narrator creation:
```python
if self._config["narration"]["mode"] == "llm":
    from claude_narrator.narration.llm import LLMNarrator
    llm_cfg = self._config["narration"].get("llm", {})
    self._narrator = LLMNarrator(
        provider=llm_cfg.get("provider", "ollama"),
        model=llm_cfg.get("model", "qwen2.5:3b"),
        language=self._config["general"]["language"],
    )
```

Note: LLMNarrator.narrate() is async, so `_event_loop` needs `text = await self._narrator.narrate(event)` — update the narrator interface to support both sync and async.

- [ ] **Step 3: Test and commit**

```bash
python -m pytest tests/ -v
git add src/claude_narrator/narration/llm.py src/claude_narrator/daemon.py
git commit -m "feat: LLM-based narration mode with template fallback"
```

---

### Task 25: Sound Effects Mode

**Files:**
- Modify: `src/claude_narrator/daemon.py`
- Modify: `src/claude_narrator/config.py`

- [ ] **Step 1: Add sound effects support to config**

Add to `DEFAULT_CONFIG`:
```python
"sounds": {
    "enabled": False,
    "directory": str(CONFIG_DIR / "sounds"),
    "events": {
        "Stop": "complete.wav",
        "Notification": "alert.wav",
        "PostToolUseFailure": "error.wav",
        "PreToolUse": "tick.wav",
    },
},
```

- [ ] **Step 2: Add sound playback to daemon**

In `daemon.py`, after queuing narration:
```python
async def _play_sound_effect(self, event_name: str) -> None:
    """Play a sound effect for the event type if configured."""
    sounds_cfg = self._config.get("sounds", {})
    if not sounds_cfg.get("enabled", False):
        return

    sound_dir = Path(sounds_cfg.get("directory", self._config_dir / "sounds"))
    events = sounds_cfg.get("events", {})
    sound_file = events.get(event_name)
    if not sound_file:
        return

    sound_path = sound_dir / sound_file
    if sound_path.exists():
        try:
            import pygame
            sound = pygame.mixer.Sound(str(sound_path))
            sound.play()
        except Exception as e:
            logger.debug("Sound effect error: %s", e)
```

- [ ] **Step 3: Commit**

```bash
git add src/claude_narrator/daemon.py src/claude_narrator/config.py
git commit -m "feat: sound effects mode for event-type audio cues"
```

---

### Task 26: Custom Event Filter Rules

**Files:**
- Create: `src/claude_narrator/narration/filters.py`
- Create: `tests/test_filters.py`

- [ ] **Step 1: Implement custom filters**

`src/claude_narrator/narration/filters.py`:
```python
"""Custom event filter rules from config."""

from __future__ import annotations

from typing import Any


def apply_custom_filters(
    event: dict[str, Any],
    filters: dict[str, Any],
) -> tuple[bool, str | None]:
    """Apply custom filter rules. Returns (should_narrate, verbosity_override)."""
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    # Check ignore_tools
    if tool_name in filters.get("ignore_tools", []):
        return False, None

    # Check only_tools
    only = filters.get("only_tools")
    if only is not None and tool_name and tool_name not in only:
        return False, None

    # Check ignore_paths
    file_path = tool_input.get("file_path", "") if isinstance(tool_input, dict) else ""
    for pattern in filters.get("ignore_paths", []):
        if _match_glob(file_path, pattern):
            return False, None

    # Check custom_rules
    for rule in filters.get("custom_rules", []):
        match = rule.get("match", {})
        if _matches_rule(event, match):
            action = rule.get("action", "")
            if action == "skip":
                return False, None
            elif action == "force_verbosity":
                return True, rule.get("value")

    return True, None


def _matches_rule(event: dict, match: dict) -> bool:
    if "tool" in match and event.get("tool_name") != match["tool"]:
        return False
    if "input_contains" in match:
        tool_input = event.get("tool_input", {})
        if isinstance(tool_input, dict):
            input_str = str(tool_input)
        else:
            input_str = str(tool_input)
        if match["input_contains"] not in input_str:
            return False
    return True


def _match_glob(path: str, pattern: str) -> bool:
    """Simple glob matching."""
    from fnmatch import fnmatch
    return fnmatch(path, pattern)
```

- [ ] **Step 2: Test and commit**

```bash
python -m pytest tests/test_filters.py -v
git add src/claude_narrator/narration/filters.py tests/test_filters.py
git commit -m "feat: custom event filter rules from config"
```

---

### Task 27: Web UI Control Panel

**Files:**
- Create: `src/claude_narrator/web.py`

- [ ] **Step 1: Implement minimal web UI**

`src/claude_narrator/web.py`:
```python
"""Minimal web UI for monitoring and controlling the narrator daemon."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from claude_narrator.config import load_config, CONFIG_DIR

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Claude Narrator</title>
    <style>
        body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #1a1a2e; color: #e0e0e0; }
        h1 { color: #64ffda; }
        .event { padding: 8px 12px; margin: 4px 0; border-radius: 4px; background: #16213e; border-left: 3px solid #64ffda; }
        .event.high { border-left-color: #ff6b6b; }
        .event.medium { border-left-color: #ffd93d; }
        .config { background: #16213e; padding: 16px; border-radius: 8px; margin: 16px 0; }
        pre { background: #0f3460; padding: 12px; border-radius: 4px; overflow-x: auto; }
        #events { max-height: 400px; overflow-y: auto; }
    </style>
</head>
<body>
    <h1>Claude Narrator</h1>
    <div class="config">
        <h2>Configuration</h2>
        <pre id="config"></pre>
    </div>
    <h2>Recent Events</h2>
    <div id="events"></div>
    <script>
        async function refresh() {
            const r = await fetch('/api/status');
            const data = await r.json();
            document.getElementById('config').textContent = JSON.stringify(data.config, null, 2);
            const eventsDiv = document.getElementById('events');
            eventsDiv.innerHTML = data.events.map(e =>
                `<div class="event ${e.priority}">${e.time} — ${e.text}</div>`
            ).join('');
        }
        refresh();
        setInterval(refresh, 2000);
    </script>
</body>
</html>"""


class WebUI:
    """Simple web UI server for daemon monitoring."""

    def __init__(self, host: str = "127.0.0.1", port: int = 19822) -> None:
        self._host = host
        self._port = port
        self._events: list[dict[str, Any]] = []
        self._server: asyncio.Server | None = None

    def add_event(self, text: str, priority: str = "low") -> None:
        import time
        self._events.append({
            "time": time.strftime("%H:%M:%S"),
            "text": text,
            "priority": priority,
        })
        if len(self._events) > 100:
            self._events.pop(0)

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle, self._host, self._port
        )

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        data = await reader.read(4096)
        request = data.decode("utf-8", errors="replace")

        if "GET /api/status" in request:
            config = load_config()
            body = json.dumps({"config": config, "events": self._events[-50:]})
            response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n{body}"
        else:
            body = HTML_TEMPLATE
            response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\n\r\n{body}"

        writer.write(response.encode("utf-8"))
        await writer.drain()
        writer.close()
        await writer.wait_closed()
```

- [ ] **Step 2: Add --web flag to daemon start**

In `daemon.py`, optionally start WebUI:
```python
# In Daemon.start():
if self._config.get("web", {}).get("enabled", False):
    from claude_narrator.web import WebUI
    self._web = WebUI()
    await self._web.start()
```

In `cli.py`, add `--web` flag to start command.

- [ ] **Step 3: Commit**

```bash
git add src/claude_narrator/web.py src/claude_narrator/daemon.py src/claude_narrator/cli.py
git commit -m "feat: web UI control panel for daemon monitoring"
```

---

## Verification

After completing all tasks, run the full verification suite:

- [ ] **All unit tests pass**: `python -m pytest tests/ -v`
- [ ] **Install flow**: `pip install -e ".[dev]" && claude-narrator install`
- [ ] **Daemon lifecycle**: `claude-narrator start && claude-narrator status && claude-narrator stop`
- [ ] **TTS test**: `claude-narrator test "Hello world"`
- [ ] **Config flow**: `claude-narrator config set general.verbosity verbose && claude-narrator config get general.verbosity`
- [ ] **Cache**: `claude-narrator cache clear`
- [ ] **Hooks in settings.json**: Verify narrator hooks present in `~/.claude/settings.json`
- [ ] **Cross-platform**: Test on macOS (Unix Socket) and verify HTTP fallback logic
