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
