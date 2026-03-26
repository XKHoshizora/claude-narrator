"""Abstract base classes for IPC server and client."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class IPCServer(ABC):
    """Server that receives events from hook scripts."""

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def events(self) -> AsyncIterator[dict[str, Any]]:
        yield {}  # pragma: no cover


class IPCClient(ABC):
    """Client used by hook scripts to send events to the daemon."""

    @abstractmethod
    def send(self, event: dict[str, Any]) -> None:
        """Send event to daemon. Fire-and-forget; never raises."""
