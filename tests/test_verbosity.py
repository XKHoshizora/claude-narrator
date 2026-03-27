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

    def test_normal_allows_file_ops(self):
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
