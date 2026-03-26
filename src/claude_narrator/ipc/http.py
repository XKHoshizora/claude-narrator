"""HTTP IPC implementation (Windows fallback)."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
from typing import Any, AsyncIterator

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
        self._host = host
        self._port = port

    def send(self, event: dict[str, Any]) -> None:
        try:
            body = json.dumps(event).encode("utf-8")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((self._host, self._port))
            request = (
                f"POST /event HTTP/1.1\r\n"
                f"Host: {self._host}:{self._port}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"\r\n"
            ).encode("utf-8") + body
            sock.sendall(request)
            sock.recv(1024)  # Read response
            sock.close()
        except Exception:
            pass  # Silent on failure
