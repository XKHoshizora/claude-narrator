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

    def test_normal_allows_session_start(self):
        assert should_narrate("SessionStart", None, "normal") is True

    def test_verbose_allows_everything(self):
        assert should_narrate("PreToolUse", "Bash", "verbose") is True
        assert should_narrate("SessionStart", None, "verbose") is True
        assert should_narrate("PreCompact", None, "verbose") is True


class TestNewEventVerbosity:
    """Tests for new hook events verbosity classification."""

    # Tier 1 — MINIMAL events
    def test_stop_failure_at_minimal(self):
        assert should_narrate("StopFailure", None, "minimal") is True

    def test_permission_denied_at_minimal(self):
        assert should_narrate("PermissionDenied", None, "minimal") is True

    def test_permission_request_at_minimal(self):
        assert should_narrate("PermissionRequest", None, "minimal") is True

    # Tier 1 — NORMAL events
    def test_session_end_at_normal(self):
        assert should_narrate("SessionEnd", None, "normal") is True

    def test_session_end_blocked_at_minimal(self):
        assert should_narrate("SessionEnd", None, "minimal") is False

    def test_post_compact_at_normal(self):
        assert should_narrate("PostCompact", None, "normal") is True

    def test_post_compact_blocked_at_minimal(self):
        assert should_narrate("PostCompact", None, "minimal") is False

    def test_task_created_at_normal(self):
        assert should_narrate("TaskCreated", None, "normal") is True

    def test_task_created_blocked_at_minimal(self):
        assert should_narrate("TaskCreated", None, "minimal") is False

    def test_task_completed_at_normal(self):
        assert should_narrate("TaskCompleted", None, "normal") is True

    # Tier 2 — VERBOSE only events
    def test_worktree_create_at_verbose(self):
        assert should_narrate("WorktreeCreate", None, "verbose") is True

    def test_worktree_create_blocked_at_normal(self):
        assert should_narrate("WorktreeCreate", None, "normal") is False

    def test_cwd_changed_at_verbose(self):
        assert should_narrate("CwdChanged", None, "verbose") is True

    def test_cwd_changed_blocked_at_normal(self):
        assert should_narrate("CwdChanged", None, "normal") is False

    def test_file_changed_at_verbose(self):
        assert should_narrate("FileChanged", None, "verbose") is True

    def test_file_changed_blocked_at_normal(self):
        assert should_narrate("FileChanged", None, "normal") is False
