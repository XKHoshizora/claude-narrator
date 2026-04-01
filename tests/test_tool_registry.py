"""Tests for the tool registry module."""

from __future__ import annotations

import pytest

from claude_narrator.tool_registry import (
    TOOL_REGISTRY,
    ToolCategory,
    ToolMeta,
    get_display_name,
    get_tool_meta,
    parse_response,
)


class TestGetToolMeta:
    def test_known_tool_bash(self):
        meta = get_tool_meta("Bash")
        assert meta.category == ToolCategory.COMMAND
        assert meta.display_name == "shell command"

    def test_known_tool_read(self):
        meta = get_tool_meta("Read")
        assert meta.category == ToolCategory.FILE
        assert meta.response_parser is not None

    def test_unknown_tool_returns_other(self):
        meta = get_tool_meta("SomeFutureTool")
        assert meta.category == ToolCategory.OTHER
        assert meta.display_name == "SomeFutureTool"
        assert meta.name == "SomeFutureTool"


class TestAllCategoriesRepresented:
    def test_all_categories_in_registry(self):
        categories_in_registry = {meta.category for meta in TOOL_REGISTRY.values()}
        for cat in ToolCategory:
            assert cat in categories_in_registry, (
                f"Category {cat.name} not represented in TOOL_REGISTRY"
            )


class TestGetDisplayName:
    def test_known_tool(self):
        assert get_display_name("Bash") == "shell command"

    def test_unknown_tool(self):
        assert get_display_name("UnknownTool123") == "UnknownTool123"


class TestParseResponse:
    def test_bash_exit_code_dict(self):
        response = {"exit_code": 0}
        result = parse_response("Bash", response)
        assert result == {"result_summary": "exit code 0"}

    def test_bash_exit_code_nonzero(self):
        response = {"exit_code": 1}
        result = parse_response("Bash", response)
        assert result == {"result_summary": "exit code 1"}

    def test_bash_string_response(self):
        response = "line1\nline2\nline3"
        result = parse_response("Bash", response)
        assert result == {"result_summary": "3 lines of output"}

    def test_bash_empty_string(self):
        response = ""
        result = parse_response("Bash", response)
        assert result == {}

    def test_grep_response(self):
        response = "file1.py:10:match1\nfile2.py:20:match2"
        result = parse_response("Grep", response)
        assert result == {"result_summary": "2 matches"}

    def test_grep_empty(self):
        response = ""
        result = parse_response("Grep", response)
        assert result == {}

    def test_glob_response(self):
        response = "src/a.py\nsrc/b.py\nsrc/c.py"
        result = parse_response("Glob", response)
        assert result == {"result_summary": "3 files found"}

    def test_read_response(self):
        response = "line1\nline2\nline3\nline4\nline5"
        result = parse_response("Read", response)
        assert result == {"result_summary": "5 lines"}

    def test_web_search_response(self):
        response = "result1\nresult2"
        result = parse_response("WebSearch", response)
        assert result == {"result_summary": "2 results"}

    def test_tool_without_parser_returns_empty(self):
        # Write has no response parser
        result = parse_response("Write", "some output")
        assert result == {}

    def test_unknown_tool_returns_empty(self):
        result = parse_response("NonExistentTool", "some output")
        assert result == {}

    def test_none_input_returns_empty(self):
        result = parse_response("Bash", None)
        assert result == {}

    def test_none_input_grep(self):
        result = parse_response("Grep", None)
        assert result == {}


class TestToolMeta:
    def test_frozen_dataclass(self):
        meta = get_tool_meta("Bash")
        with pytest.raises(AttributeError):
            meta.name = "something_else"  # type: ignore[misc]

    def test_tool_meta_fields(self):
        meta = get_tool_meta("Bash")
        assert isinstance(meta.name, str)
        assert isinstance(meta.display_name, str)
        assert isinstance(meta.category, ToolCategory)


class TestToolRegistry:
    def test_registry_has_at_least_40_tools(self):
        assert len(TOOL_REGISTRY) >= 40

    def test_registry_values_are_tool_meta(self):
        for name, meta in TOOL_REGISTRY.items():
            assert isinstance(meta, ToolMeta), f"{name} is not a ToolMeta"
            assert meta.name == name
