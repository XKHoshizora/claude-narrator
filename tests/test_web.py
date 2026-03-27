import asyncio
import json

import pytest

from claude_narrator.web import WebUI


class TestWebUI:
    async def test_start_and_stop(self):
        ui = WebUI(host="127.0.0.1", port=0)
        await ui.start()
        assert ui._server is not None
        await ui.stop()

    def test_add_event(self):
        ui = WebUI()
        ui.add_event("Task complete", "medium")
        assert len(ui._events) == 1
        assert ui._events[0]["text"] == "Task complete"
        assert ui._events[0]["priority"] == "medium"

    def test_event_limit(self):
        ui = WebUI()
        for i in range(150):
            ui.add_event(f"event {i}")
        assert len(ui._events) == 100

    async def test_serves_html(self):
        ui = WebUI(host="127.0.0.1", port=0)
        await ui.start()
        port = ui._server.sockets[0].getsockname()[1]
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
            await writer.drain()
            response = (await reader.read(8192)).decode("utf-8")
            writer.close()
            await writer.wait_closed()
            assert "200 OK" in response
            assert "Claude Narrator" in response
        finally:
            await ui.stop()

    async def test_api_status(self):
        ui = WebUI(host="127.0.0.1", port=0)
        ui.set_config({"general": {"verbosity": "normal"}})
        ui.add_event("Test event", "low")
        await ui.start()
        port = ui._server.sockets[0].getsockname()[1]
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(b"GET /api/status HTTP/1.1\r\nHost: localhost\r\n\r\n")
            await writer.drain()
            response = (await reader.read(8192)).decode("utf-8")
            writer.close()
            await writer.wait_closed()
            # Extract JSON body
            body = response.split("\r\n\r\n", 1)[1]
            data = json.loads(body)
            assert "config" in data
            assert "events" in data
            assert len(data["events"]) == 1
        finally:
            await ui.stop()
