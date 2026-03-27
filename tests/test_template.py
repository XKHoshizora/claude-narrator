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
