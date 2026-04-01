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
            "tool_response": "success",
        }
        assert narrator.narrate(event) == "Command done: 1 lines of output"

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


class TestNewEvents:
    """Tests for new hook events added from Claude Code source analysis."""

    def test_stop_failure(self, narrator):
        event = {"hook_event_name": "StopFailure", "error": "timeout"}
        result = narrator.narrate(event)
        assert result is not None
        assert "timeout" in result

    def test_permission_denied(self, narrator):
        event = {"hook_event_name": "PermissionDenied", "tool_name": "Bash", "reason": "blocked by user"}
        result = narrator.narrate(event)
        assert result is not None
        assert "Bash" in result

    def test_permission_request(self, narrator):
        event = {"hook_event_name": "PermissionRequest", "tool_name": "Write"}
        result = narrator.narrate(event)
        assert result is not None
        assert "Write" in result

    def test_post_compact(self, narrator):
        event = {"hook_event_name": "PostCompact", "compact_summary": "Summary of compaction"}
        result = narrator.narrate(event)
        assert result is not None
        assert "compact" in result.lower()

    def test_session_end(self, narrator):
        event = {"hook_event_name": "SessionEnd", "reason": "clear"}
        result = narrator.narrate(event)
        assert result is not None
        assert "ended" in result.lower() or "Session" in result

    def test_task_created(self, narrator):
        event = {"hook_event_name": "TaskCreated", "task_subject": "Fix authentication bug"}
        result = narrator.narrate(event)
        assert result is not None
        assert "Fix authentication bug" in result

    def test_task_completed(self, narrator):
        event = {"hook_event_name": "TaskCompleted", "task_subject": "Run tests"}
        result = narrator.narrate(event)
        assert result is not None
        assert "Run tests" in result

    def test_worktree_create(self, narrator):
        event = {"hook_event_name": "WorktreeCreate", "name": "feature-branch"}
        result = narrator.narrate(event)
        assert result is not None
        assert "feature-branch" in result

    def test_worktree_remove(self, narrator):
        event = {"hook_event_name": "WorktreeRemove", "worktree_path": "/tmp/wt"}
        result = narrator.narrate(event)
        assert result is not None

    def test_cwd_changed(self, narrator):
        event = {"hook_event_name": "CwdChanged", "old_cwd": "/a", "new_cwd": "/b"}
        result = narrator.narrate(event)
        assert result is not None
        assert "/b" in result

    def test_file_changed(self, narrator):
        event = {"hook_event_name": "FileChanged", "file_path": "/src/app.py", "event": "change"}
        result = narrator.narrate(event)
        assert result is not None
        assert "app.py" in result


class TestSubKeyLookup:
    """Tests for sub-key based template lookup (SessionStart source variants)."""

    def test_session_start_startup(self):
        narrator = TemplateNarrator(language="en")
        event = {"hook_event_name": "SessionStart", "source": "startup"}
        result = narrator.narrate(event)
        assert result is not None
        assert "New session" in result

    def test_session_start_resume(self):
        narrator = TemplateNarrator(language="en")
        event = {"hook_event_name": "SessionStart", "source": "resume"}
        result = narrator.narrate(event)
        assert result is not None
        assert "Resuming" in result

    def test_session_start_no_source_uses_default(self):
        narrator = TemplateNarrator(language="en")
        event = {"hook_event_name": "SessionStart"}
        result = narrator.narrate(event)
        assert result is not None
        assert "Session started" in result


class TestExtractVariables:
    """Tests for enriched variable extraction."""

    def test_error_field(self):
        from claude_narrator.narration.template import _extract_variables
        event = {"hook_event_name": "StopFailure", "error": "connection timeout"}
        variables = _extract_variables(event)
        assert variables["error"] == "connection timeout"

    def test_task_subject(self):
        from claude_narrator.narration.template import _extract_variables
        event = {"hook_event_name": "TaskCreated", "task_subject": "Write unit tests"}
        variables = _extract_variables(event)
        assert variables["task_subject"] == "Write unit tests"

    def test_agent_type(self):
        from claude_narrator.narration.template import _extract_variables
        event = {"hook_event_name": "SubagentStart", "agent_type": "code-reviewer"}
        variables = _extract_variables(event)
        assert variables["agent_type"] == "code-reviewer"

    def test_truncate_long_error(self):
        from claude_narrator.narration.template import _extract_variables
        long_error = "x" * 200
        event = {"hook_event_name": "StopFailure", "error": long_error}
        variables = _extract_variables(event)
        assert len(variables["error"]) <= 80
        assert variables["error"].endswith("...")

    def test_file_path_from_event_level(self):
        from claude_narrator.narration.template import _extract_variables
        event = {"hook_event_name": "FileChanged", "file_path": "/long/deep/path/to/file.py", "event": "change"}
        variables = _extract_variables(event)
        assert "file_path" in variables
        assert "file.py" in variables["file_path"]


class TestTruncate:
    def test_short_text_unchanged(self):
        from claude_narrator.narration.template import _truncate
        assert _truncate("hello", 80) == "hello"

    def test_long_text_truncated(self):
        from claude_narrator.narration.template import _truncate
        result = _truncate("x" * 100, 80)
        assert len(result) == 80
        assert result.endswith("...")


class TestMissingFields:
    """Tests for graceful handling when expected event fields are missing."""

    def test_stop_failure_missing_error(self, narrator):
        event = {"hook_event_name": "StopFailure"}
        result = narrator.narrate(event)
        assert result is not None  # Falls back to raw template string

    def test_task_created_missing_subject(self, narrator):
        event = {"hook_event_name": "TaskCreated"}
        result = narrator.narrate(event)
        assert result is not None

    def test_task_completed_missing_subject(self, narrator):
        event = {"hook_event_name": "TaskCompleted"}
        result = narrator.narrate(event)
        assert result is not None

    def test_worktree_create_missing_name(self, narrator):
        event = {"hook_event_name": "WorktreeCreate"}
        result = narrator.narrate(event)
        assert result is not None

    def test_permission_denied_missing_tool(self, narrator):
        event = {"hook_event_name": "PermissionDenied"}
        result = narrator.narrate(event)
        assert result is not None

    def test_file_changed_missing_path(self, narrator):
        event = {"hook_event_name": "FileChanged"}
        result = narrator.narrate(event)
        assert result is not None

    def test_cwd_changed_missing_new_cwd(self, narrator):
        event = {"hook_event_name": "CwdChanged"}
        result = narrator.narrate(event)
        assert result is not None


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


class TestToolRegistryIntegration:
    def test_display_name_in_variables(self):
        from claude_narrator.narration.template import _extract_variables
        event = {"hook_event_name": "PreToolUse", "tool_name": "WebSearch", "tool_input": {}}
        variables = _extract_variables(event)
        assert variables["display_name"] == "web search"

    def test_category_in_variables(self):
        from claude_narrator.narration.template import _extract_variables
        event = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {}}
        variables = _extract_variables(event)
        assert variables["category"] == "command"

    def test_unknown_tool_display_name_is_raw(self):
        from claude_narrator.narration.template import _extract_variables
        event = {"hook_event_name": "PreToolUse", "tool_name": "FutureTool", "tool_input": {}}
        variables = _extract_variables(event)
        assert variables["display_name"] == "FutureTool"

    def test_result_summary_for_bash(self):
        from claude_narrator.narration.template import _extract_variables
        event = {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_response": {"exit_code": 0}}
        variables = _extract_variables(event)
        assert "result_summary" in variables

    def test_result_summary_for_grep(self):
        from claude_narrator.narration.template import _extract_variables
        event = {"hook_event_name": "PostToolUse", "tool_name": "Grep", "tool_response": "a:1:x\nb:2:y"}
        variables = _extract_variables(event)
        assert variables["result_summary"] == "2 matches"

    def test_no_result_summary_without_response(self):
        from claude_narrator.narration.template import _extract_variables
        event = {"hook_event_name": "PostToolUse", "tool_name": "Bash"}
        variables = _extract_variables(event)
        assert "result_summary" not in variables


class TestNotificationSubKey:
    def test_idle_prompt(self, narrator):
        event = {"hook_event_name": "Notification", "notification_type": "idle_prompt"}
        result = narrator.narrate(event)
        assert result is not None
        assert "input" in result.lower()

    def test_unknown_type_uses_default(self, narrator):
        event = {"hook_event_name": "Notification", "notification_type": "some_new_type"}
        result = narrator.narrate(event)
        assert result is not None
        assert "Attention" in result

    def test_no_type_uses_default(self, narrator):
        event = {"hook_event_name": "Notification"}
        result = narrator.narrate(event)
        assert result is not None


class TestEnrichedTemplates:
    def test_web_search_pre(self, narrator):
        event = {"hook_event_name": "PreToolUse", "tool_name": "WebSearch", "tool_input": {}}
        result = narrator.narrate(event)
        assert result is not None
        assert "web" in result.lower()

    def test_enter_plan_mode(self, narrator):
        event = {"hook_event_name": "PreToolUse", "tool_name": "EnterPlanMode", "tool_input": {}}
        result = narrator.narrate(event)
        assert result is not None
        assert "plan" in result.lower()

    def test_post_bash_with_summary(self, narrator):
        event = {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_response": "l1\nl2\nl3"}
        result = narrator.narrate(event)
        assert result is not None
        assert "3" in result

    def test_post_grep_with_summary(self, narrator):
        event = {"hook_event_name": "PostToolUse", "tool_name": "Grep", "tool_response": "a:1:x\nb:2:y"}
        result = narrator.narrate(event)
        assert result is not None
        assert "2" in result

    def test_notification_idle_zh(self):
        n = TemplateNarrator(language="zh")
        event = {"hook_event_name": "Notification", "notification_type": "idle_prompt"}
        result = n.narrate(event)
        assert result is not None
        assert "输入" in result

    def test_notification_idle_ja(self):
        n = TemplateNarrator(language="ja")
        event = {"hook_event_name": "Notification", "notification_type": "idle_prompt"}
        result = n.narrate(event)
        assert result is not None
        assert "入力" in result

    def test_default_uses_display_name(self, narrator):
        event = {"hook_event_name": "PreToolUse", "tool_name": "EnterWorktree", "tool_input": {}}
        result = narrator.narrate(event)
        assert result is not None
        assert "worktree" in result.lower()
