import random
from unittest.mock import patch

import pytest

from claude_narrator.narration.template import TemplateNarrator, PersonalityLayer


class TestBackwardCompatibility:
    """Existing behavior must not change when personality is default."""

    def test_default_constructor(self):
        narrator = TemplateNarrator("en")
        event = {"hook_event_name": "Stop"}
        assert narrator.narrate(event) == "Task complete"

    def test_concise_explicit(self):
        narrator = TemplateNarrator("en", "concise")
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read",
                 "tool_input": {"file_path": "/app.py"}}
        assert narrator.narrate(event) == "Reading /app.py"

    def test_concise_no_prefix(self):
        narrator = TemplateNarrator("en", "concise")
        event = {"hook_event_name": "Stop"}
        result = narrator.narrate(event)
        assert "..." not in result

    def test_coalesced_unchanged(self):
        narrator = TemplateNarrator("en", "tengu")
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read",
                 "_coalesced_count": 5}
        assert narrator.narrate(event) == "5 Read operations"

    def test_unknown_event_returns_none(self):
        narrator = TemplateNarrator("en", "concise")
        assert narrator.narrate({"hook_event_name": "Unknown"}) is None


class TestTenguPersonality:
    def test_has_90_prefixes(self):
        narrator = TemplateNarrator("en", "tengu")
        assert len(narrator._all_prefixes) == 90

    def test_narrate_has_prefix(self):
        narrator = TemplateNarrator("en", "tengu")
        with patch("claude_narrator.narration.template.random.choice", return_value="Cogitating"):
            event = {"hook_event_name": "PreToolUse", "tool_name": "Read",
                     "tool_input": {"file_path": "/app.py"}}
            result = narrator.narrate(event)
            assert result.startswith("Cogitating...")
            assert "app.py" in result

    def test_tengu_body_template(self):
        narrator = TemplateNarrator("en", "tengu")
        with patch("claude_narrator.narration.template.random.choice", return_value="X"):
            event = {"hook_event_name": "Stop"}
            result = narrator.narrate(event)
            assert "mission accomplished" in result


class TestProfessionalPersonality:
    def test_no_prefix(self):
        narrator = TemplateNarrator("en", "professional")
        event = {"hook_event_name": "Stop"}
        result = narrator.narrate(event)
        assert "..." not in result
        assert "completed successfully" in result

    def test_formal_language(self):
        narrator = TemplateNarrator("en", "professional")
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read",
                 "tool_input": {"file_path": "/app.py"}}
        result = narrator.narrate(event)
        assert "Now reading" in result


class TestCasualPersonality:
    def test_casual_language(self):
        narrator = TemplateNarrator("en", "casual")
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read",
                 "tool_input": {"file_path": "/app.py"}}
        result = narrator.narrate(event)
        assert "Checking out" in result


class TestMultiPersonality:
    def test_tengu_prefix_with_professional_body(self):
        # tengu is first, so its body wins. But both contribute prefixes.
        narrator = TemplateNarrator("en", ["tengu", "professional"])
        with patch("claude_narrator.narration.template.random.choice", return_value="Vibing"):
            event = {"hook_event_name": "Stop"}
            result = narrator.narrate(event)
            assert result.startswith("Vibing...")

    def test_high_priority_longest_body(self):
        narrator = TemplateNarrator("en", ["concise", "professional"])
        event = {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash"}
        result = narrator.narrate(event)
        # professional's "Command execution encountered an error" is longer than concise's "Command failed"
        assert "encountered an error" in result or len(result) > len("Command failed")

    def test_first_layer_body_wins_for_normal_events(self):
        narrator = TemplateNarrator("en", ["professional", "casual"])
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read",
                 "tool_input": {"file_path": "/app.py"}}
        result = narrator.narrate(event)
        assert "Now reading" in result  # professional is first

    def test_prefix_pool_merged(self):
        narrator = TemplateNarrator("en", ["tengu", "concise"])
        assert len(narrator._all_prefixes) == 90  # only tengu has prefixes


class TestContextThreshold:
    def test_context_threshold_template(self):
        narrator = TemplateNarrator("en", "concise")
        event = {"hook_event_name": "ContextThreshold", "threshold": 70, "used_percentage": 72.5}
        result = narrator.narrate(event)
        assert "70" in result

    def test_context_threshold_tengu(self):
        narrator = TemplateNarrator("en", "tengu")
        with patch("claude_narrator.narration.template.random.choice", return_value="Ruminating"):
            event = {"hook_event_name": "ContextThreshold", "threshold": 85}
            result = narrator.narrate(event)
            assert "Ruminating..." in result
            assert "85" in result


class TestMultiLanguage:
    def test_chinese_tengu(self):
        narrator = TemplateNarrator("zh", "tengu")
        assert len(narrator._all_prefixes) == 90  # same tengu words

    def test_japanese_professional(self):
        narrator = TemplateNarrator("ja", "professional")
        event = {"hook_event_name": "Stop"}
        result = narrator.narrate(event)
        assert result is not None
