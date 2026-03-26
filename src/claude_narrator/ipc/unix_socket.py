"""Unix Domain Socket IPC implementation."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
from pathlib import Path
from typing import Any, AsyncIterator

from claude_narrator.ipc.base import IPCClient, IPCServer

logger = logging.getLogger(__name__)

# macOS AF_UNIX path limit is 104 bytes; Linux is 108 bytes.
_UNIX_PATH_MAX = 104


def _bind_unix_socket(path: Path) -> socket.socket:
    """Bind a Unix domain socket, working around OS path-length limits.

    If the absolute path exceeds the platform limit we temporarily chdir into
    the socket's parent directory and bind using only the filename (which is
    always short).
    """
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    abs_path = str(path.resolve())
    if len(abs_path.encode()) <= _UNIX_PATH_MAX:
        sock.bind(abs_path)
    else:
        # Bind via a short relative path by chdiring to the parent directory.
        orig_dir = os.getcwd()
        try:
            os.chdir(str(path.parent))
            sock.bind(path.name)
        finally:
            os.chdir(orig_dir)
    return sock


class UnixSocketServer(IPCServer):
    def __init__(self, socket_path: Path) -> None:
        self._path = Path(socket_path)
        self._server: asyncio.AbstractServer | None = None
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def start(self) -> None:
        self._path.unlink(missing_ok=True)
        srv_sock = _bind_unix_socket(self._path)
        srv_sock.listen(128)
        self._server = await asyncio.start_unix_server(
            self._handle_client, sock=srv_sock
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
        self._path = Path(socket_path)

    def send(self, event: dict[str, Any]) -> None:
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            abs_path = str(self._path.resolve())
            if len(abs_path.encode()) <= _UNIX_PATH_MAX:
                sock.connect(abs_path)
            else:
                orig_dir = os.getcwd()
                try:
                    os.chdir(str(self._path.parent))
                    sock.connect(self._path.name)
                finally:
                    os.chdir(orig_dir)
            sock.sendall(json.dumps(event).encode("utf-8") + b"\n")
            sock.close()
        except Exception:
            pass  # Silent on failure — daemon may not be running
