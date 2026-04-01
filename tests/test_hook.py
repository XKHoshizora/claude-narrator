import io
import json
from unittest.mock import patch, MagicMock

import pytest

from claude_narrator.hooks.on_event import main, parse_event, forward_event


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


class TestAsyncHookProtocol:
    def test_main_outputs_async_marker_first(self):
        """Verify hook outputs {"async": true} on stdout before processing."""
        stdin_data = json.dumps({"hook_event_name": "Stop"})
        stdout_buf = io.StringIO()
        with patch("claude_narrator.hooks.on_event.sys.stdin", io.StringIO(stdin_data)), \
             patch("claude_narrator.hooks.on_event.sys.stdout", stdout_buf), \
             patch("claude_narrator.hooks.on_event.forward_event"):
            main()
        output = stdout_buf.getvalue()
        first_line = output.split("\n")[0]
        parsed = json.loads(first_line)
        assert parsed == {"async": True}

    def test_main_still_forwards_event(self):
        """Verify hook still forwards event to daemon after async marker."""
        stdin_data = json.dumps({"hook_event_name": "Stop"})
        with patch("claude_narrator.hooks.on_event.sys.stdin", io.StringIO(stdin_data)), \
             patch("claude_narrator.hooks.on_event.sys.stdout", io.StringIO()), \
             patch("claude_narrator.hooks.on_event.forward_event") as mock_fwd:
            main()
        mock_fwd.assert_called_once()
        assert mock_fwd.call_args[0][0]["hook_event_name"] == "Stop"
