"""Tool metadata registry for Claude Code tools.

Maps tool names to display names, categories, and optional response parsers
for narration generation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Categories of Claude Code tools."""

    FILE = "file"
    COMMAND = "command"
    AGENT = "agent"
    SEARCH = "search"
    PLAN = "plan"
    TASK = "task"
    MCP = "mcp"
    WORKTREE = "worktree"
    NOTEBOOK = "notebook"
    OTHER = "other"


@dataclass(frozen=True)
class ToolMeta:
    """Metadata for a single tool.

    Attributes:
        name: The canonical tool name as used in Claude Code events.
        display_name: A human-friendly name for narration.
        category: The tool category.
        response_parser: Optional callable that extracts summary info from a
            tool response.  Signature: ``(response: Any) -> dict[str, str]``.
            Returns ``{}`` on failure or when no meaningful summary is possible.
    """

    name: str
    display_name: str
    category: ToolCategory
    response_parser: Callable[..., dict[str, str]] | None = None


# ---------------------------------------------------------------------------
# Response parsers
# ---------------------------------------------------------------------------


def _parse_bash_response(response: Any) -> dict[str, str]:
    """Parse a Bash/PowerShell tool response into result_summary."""
    if isinstance(response, dict) and "exit_code" in response:
        return {"result_summary": f"exit code {response['exit_code']}"}
    if isinstance(response, str) and response.strip():
        count = len(response.strip().splitlines())
        return {"result_summary": f"{count} lines of output"}
    return {}


def _parse_grep_response(response: Any) -> dict[str, str]:
    """Parse a Grep tool response — count matching lines."""
    if isinstance(response, str) and response.strip():
        count = len(response.strip().splitlines())
        return {"result_summary": f"{count} matches"}
    return {}


def _parse_glob_response(response: Any) -> dict[str, str]:
    """Parse a Glob tool response — count files found."""
    if isinstance(response, str) and response.strip():
        count = len(response.strip().splitlines())
        return {"result_summary": f"{count} files found"}
    return {}


def _parse_read_response(response: Any) -> dict[str, str]:
    """Parse a Read tool response — count lines."""
    if isinstance(response, str) and response.strip():
        count = len(response.strip().splitlines())
        return {"result_summary": f"{count} lines"}
    return {}


def _parse_web_search_response(response: Any) -> dict[str, str]:
    """Parse a WebSearch tool response — count results."""
    if isinstance(response, str) and response.strip():
        count = len(response.strip().splitlines())
        return {"result_summary": f"{count} results"}
    return {}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, ToolMeta] = {
    # FILE
    "Read": ToolMeta("Read", "read file", ToolCategory.FILE, _parse_read_response),
    "Write": ToolMeta("Write", "write file", ToolCategory.FILE),
    "Edit": ToolMeta("Edit", "edit file", ToolCategory.FILE),
    "Glob": ToolMeta("Glob", "find files", ToolCategory.FILE, _parse_glob_response),
    # SEARCH
    "Grep": ToolMeta("Grep", "search code", ToolCategory.SEARCH, _parse_grep_response),
    "WebSearch": ToolMeta(
        "WebSearch",
        "web search",
        ToolCategory.SEARCH,
        _parse_web_search_response,
    ),
    "WebFetch": ToolMeta("WebFetch", "fetch web page", ToolCategory.SEARCH),
    "ToolSearch": ToolMeta("ToolSearch", "search tools", ToolCategory.SEARCH),
    # COMMAND
    "Bash": ToolMeta(
        "Bash", "shell command", ToolCategory.COMMAND, _parse_bash_response
    ),
    "PowerShell": ToolMeta(
        "PowerShell",
        "PowerShell command",
        ToolCategory.COMMAND,
        _parse_bash_response,
    ),
    "REPL": ToolMeta("REPL", "REPL", ToolCategory.COMMAND),
    # AGENT
    "Agent": ToolMeta("Agent", "sub-agent", ToolCategory.AGENT),
    "SendMessage": ToolMeta("SendMessage", "send message", ToolCategory.AGENT),
    "Brief": ToolMeta("Brief", "brief", ToolCategory.AGENT),
    # PLAN
    "EnterPlanMode": ToolMeta("EnterPlanMode", "enter plan mode", ToolCategory.PLAN),
    "ExitPlanMode": ToolMeta("ExitPlanMode", "exit plan mode", ToolCategory.PLAN),
    # TASK
    "TaskCreate": ToolMeta("TaskCreate", "create task", ToolCategory.TASK),
    "TaskUpdate": ToolMeta("TaskUpdate", "update task", ToolCategory.TASK),
    "TaskGet": ToolMeta("TaskGet", "get task", ToolCategory.TASK),
    "TaskList": ToolMeta("TaskList", "list tasks", ToolCategory.TASK),
    "TaskStop": ToolMeta("TaskStop", "stop task", ToolCategory.TASK),
    "TaskOutput": ToolMeta("TaskOutput", "task output", ToolCategory.TASK),
    "TeamCreate": ToolMeta("TeamCreate", "create team", ToolCategory.TASK),
    "TeamDelete": ToolMeta("TeamDelete", "delete team", ToolCategory.TASK),
    "CronCreate": ToolMeta("CronCreate", "create cron job", ToolCategory.TASK),
    "CronDelete": ToolMeta("CronDelete", "delete cron job", ToolCategory.TASK),
    "CronList": ToolMeta("CronList", "list cron jobs", ToolCategory.TASK),
    # MCP
    "MCPTool": ToolMeta("MCPTool", "MCP tool", ToolCategory.MCP),
    "ListMcpResources": ToolMeta(
        "ListMcpResources", "list MCP resources", ToolCategory.MCP
    ),
    "ReadMcpResource": ToolMeta(
        "ReadMcpResource", "read MCP resource", ToolCategory.MCP
    ),
    "McpAuth": ToolMeta("McpAuth", "MCP auth", ToolCategory.MCP),
    "Skill": ToolMeta("Skill", "invoke skill", ToolCategory.MCP),
    # WORKTREE
    "EnterWorktree": ToolMeta("EnterWorktree", "enter worktree", ToolCategory.WORKTREE),
    "ExitWorktree": ToolMeta("ExitWorktree", "exit worktree", ToolCategory.WORKTREE),
    # NOTEBOOK
    "NotebookEdit": ToolMeta("NotebookEdit", "edit notebook", ToolCategory.NOTEBOOK),
    # OTHER
    "AskUserQuestion": ToolMeta(
        "AskUserQuestion", "ask user", ToolCategory.OTHER
    ),
    "Config": ToolMeta("Config", "config", ToolCategory.OTHER),
    "RemoteTrigger": ToolMeta("RemoteTrigger", "remote trigger", ToolCategory.OTHER),
    "ScheduleCron": ToolMeta("ScheduleCron", "schedule cron", ToolCategory.OTHER),
    "Sleep": ToolMeta("Sleep", "sleep", ToolCategory.OTHER),
    "LSP": ToolMeta("LSP", "language server", ToolCategory.OTHER),
    "TodoWrite": ToolMeta("TodoWrite", "update todo", ToolCategory.OTHER),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_tool_meta(tool_name: str) -> ToolMeta:
    """Return the ``ToolMeta`` for *tool_name*.

    If the tool is not in the registry, a fallback ``ToolMeta`` with
    ``ToolCategory.OTHER`` and the raw name as display name is returned.
    """
    if tool_name in TOOL_REGISTRY:
        return TOOL_REGISTRY[tool_name]
    return ToolMeta(
        name=tool_name,
        display_name=tool_name,
        category=ToolCategory.OTHER,
    )


def get_display_name(tool_name: str) -> str:
    """Return the human-friendly display name for *tool_name*."""
    return get_tool_meta(tool_name).display_name


def parse_response(tool_name: str, response: Any) -> dict[str, str]:
    """Run the response parser for *tool_name*, if one exists.

    Returns an empty dict when no parser is registered, the tool is
    unknown, or the parser raises an exception.
    """
    meta = get_tool_meta(tool_name)
    if meta.response_parser is None:
        return {}
    try:
        return meta.response_parser(response)
    except Exception:
        logger.debug("Response parser failed for %s", tool_name, exc_info=True)
        return {}
