"""IPC layer: platform-aware server/client factory."""

from __future__ import annotations

import sys
from pathlib import Path

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
    if sys.platform == "win32":
        return HTTPServer(port=http_port)
    return UnixSocketServer(socket_path or DEFAULT_SOCKET_PATH)


def create_client(
    socket_path: Path | None = None,
    http_port: int = DEFAULT_HTTP_PORT,
) -> IPCClient:
    if sys.platform == "win32":
        return HTTPClient(port=http_port)
    return UnixSocketClient(socket_path or DEFAULT_SOCKET_PATH)
