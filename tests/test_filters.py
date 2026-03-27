import pytest
from claude_narrator.narration.filters import apply_filters


class TestCustomFilters:
    def test_empty_filters_allows_all(self):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read"}
        ok, override = apply_filters(event, {})
        assert ok is True
        assert override is None

    def test_ignore_tools(self):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read"}
        ok, _ = apply_filters(event, {"ignore_tools": ["Read"]})
        assert ok is False

    def test_only_tools_whitelist(self):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Bash"}
        ok, _ = apply_filters(event, {"only_tools": ["Read", "Write"]})
        assert ok is False

    def test_only_tools_allows_listed(self):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read"}
        ok, _ = apply_filters(event, {"only_tools": ["Read", "Write"]})
        assert ok is True

    def test_ignore_paths_glob(self):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read",
                 "tool_input": {"file_path": "node_modules/foo/bar.js"}}
        ok, _ = apply_filters(event, {"ignore_paths": ["node_modules/*"]})
        assert ok is False

    def test_ignore_paths_no_match(self):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read",
                 "tool_input": {"file_path": "src/app.py"}}
        ok, _ = apply_filters(event, {"ignore_paths": ["node_modules/*"]})
        assert ok is True

    def test_custom_rule_skip(self):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                 "tool_input": {"command": "npm test"}}
        rules = {"custom_rules": [
            {"match": {"tool": "Bash", "input_contains": "npm test"}, "action": "skip"}
        ]}
        ok, _ = apply_filters(event, rules)
        assert ok is False

    def test_custom_rule_force_verbosity(self):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                 "tool_input": {"command": "npm test"}}
        rules = {"custom_rules": [
            {"match": {"tool": "Bash", "input_contains": "npm test"},
             "action": "force_verbosity", "value": "minimal"}
        ]}
        ok, override = apply_filters(event, rules)
        assert ok is True
        assert override == "minimal"

    def test_custom_rule_no_match(self):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read"}
        rules = {"custom_rules": [
            {"match": {"tool": "Bash"}, "action": "skip"}
        ]}
        ok, _ = apply_filters(event, rules)
        assert ok is True
