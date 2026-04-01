# Smart Narration Implementation Plan

> **状态: 已完成** — v0.4.0 已发布。

**Goal:** Make narrator's speech context-aware — differentiate 40+ tools, parse notification types, and summarize tool results.

**Architecture:** New `tool_registry.py` module holds tool metadata (display names, categories, response parsers). `template.py` integrates registry during variable extraction. `_get_sub_key()` gains Notification sub-key routing. All i18n templates updated.

**Tech Stack:** Python 3.10+, existing template/i18n system, no new dependencies.

---

### Task 1: Create Tool Registry Module with Tests

**Files:**
- Create: `src/claude_narrator/tool_registry.py`
- Create: `tests/test_tool_registry.py`

- [ ] **Step 1: Write failing tests for tool_registry**

```python
# tests/test_tool_registry.py
import pytest

from claude_narrator.tool_registry import (
    ToolCategory,
    ToolMeta,
    get_display_name,
    get_tool_meta,
    parse_response,
)


class TestGetToolMeta:
    def test_known_tool(self):
        meta = get_tool_meta("Bash")
        assert meta.name == "Bash"
        assert meta.display_name == "shell command"
        assert meta.category == ToolCategory.COMMAND

    def test_unknown_tool_returns_other(self):
        meta = get_tool_meta("SomeNewTool")
        assert meta.category == ToolCategory.OTHER
        assert meta.display_name == "SomeNewTool"

    def test_all_categories_represented(self):
        from claude_narrator.tool_registry import TOOL_REGISTRY
        categories_found = {m.category for m in TOOL_REGISTRY.values()}
        for cat in [ToolCategory.FILE, ToolCategory.COMMAND, ToolCategory.AGENT,
                    ToolCategory.SEARCH, ToolCategory.PLAN, ToolCategory.TASK, ToolCategory.MCP]:
            assert cat in categories_found, f"No tool registered for {cat}"


class TestGetDisplayName:
    def test_known_tool(self):
        assert get_display_name("Read") == "file read"

    def test_unknown_tool_returns_raw_name(self):
        assert get_display_name("FutureTool") == "FutureTool"


class TestParseResponse:
    def test_bash_exit_code(self):
        result = parse_response("Bash", {"exit_code": 0, "stdout": "ok"})
        assert "result_summary" in result
        assert "0" in result["result_summary"]

    def test_bash_string_output(self):
        result = parse_response("Bash", "line1\nline2\nline3")
        assert "result_summary" in result
        assert "3" in result["result_summary"]

    def test_grep_matches(self):
        result = parse_response("Grep", "file1.py:10:match\nfile2.py:20:match")
        assert "result_summary" in result
        assert "2" in result["result_summary"]

    def test_glob_files(self):
        result = parse_response("Glob", "a.py\nb.py\nc.py")
        assert "result_summary" in result
        assert "3" in result["result_summary"]

    def test_read_lines(self):
        content = "\n".join(f"line {i}" for i in range(50))
        result = parse_response("Read", content)
        assert "result_summary" in result
        assert "50" in result["result_summary"]

    def test_no_parser_returns_empty(self):
        result = parse_response("Edit", "some response")
        assert result == {}

    def test_unknown_tool_returns_empty(self):
        result = parse_response("FutureTool", "data")
        assert result == {}

    def test_parser_error_returns_empty(self):
        result = parse_response("Bash", None)
        assert result == {}

    def test_web_search_results(self):
        result = parse_response("WebSearch", "result1\nresult2\nresult3\nresult4\nresult5")
        assert "result_summary" in result
        assert "5" in result["result_summary"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator && uv run pytest tests/test_tool_registry.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement tool_registry.py**

```python
# src/claude_narrator/tool_registry.py
"""Tool metadata registry for enriched narration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class ToolCategory(str, Enum):
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
    name: str
    display_name: str
    category: ToolCategory
    response_parser: Callable[[Any], dict[str, str]] | None = None


# --- Response parsers ---

def _parse_bash_response(resp: Any) -> dict[str, str]:
    if isinstance(resp, dict):
        code = resp.get("exit_code") or resp.get("exitCode")
        if code is not None:
            return {"result_summary": f"exit code {code}"}
        stdout = resp.get("stdout", "")
        if isinstance(stdout, str) and stdout.strip():
            lines = stdout.strip().splitlines()
            return {"result_summary": f"{len(lines)} lines of output"}
    if isinstance(resp, str) and resp.strip():
        lines = resp.strip().splitlines()
        return {"result_summary": f"{len(lines)} lines of output"}
    return {}


def _parse_grep_response(resp: Any) -> dict[str, str]:
    if isinstance(resp, str) and resp.strip():
        lines = resp.strip().splitlines()
        return {"result_summary": f"{len(lines)} matches"}
    return {}


def _parse_glob_response(resp: Any) -> dict[str, str]:
    if isinstance(resp, str) and resp.strip():
        lines = resp.strip().splitlines()
        return {"result_summary": f"{len(lines)} files found"}
    return {}


def _parse_read_response(resp: Any) -> dict[str, str]:
    if isinstance(resp, str) and resp.strip():
        lines = resp.strip().splitlines()
        return {"result_summary": f"{len(lines)} lines"}
    return {}


def _parse_web_search_response(resp: Any) -> dict[str, str]:
    if isinstance(resp, str) and resp.strip():
        lines = resp.strip().splitlines()
        return {"result_summary": f"{len(lines)} results"}
    return {}


# --- Registry ---

TOOL_REGISTRY: dict[str, ToolMeta] = {
    # FILE
    "Read": ToolMeta("Read", "file read", ToolCategory.FILE, _parse_read_response),
    "Write": ToolMeta("Write", "file write", ToolCategory.FILE),
    "Edit": ToolMeta("Edit", "file edit", ToolCategory.FILE),
    "Glob": ToolMeta("Glob", "file search", ToolCategory.FILE, _parse_glob_response),
    # SEARCH
    "Grep": ToolMeta("Grep", "code search", ToolCategory.SEARCH, _parse_grep_response),
    "WebSearch": ToolMeta("WebSearch", "web search", ToolCategory.SEARCH, _parse_web_search_response),
    "WebFetch": ToolMeta("WebFetch", "web fetch", ToolCategory.SEARCH),
    "ToolSearch": ToolMeta("ToolSearch", "tool search", ToolCategory.SEARCH),
    # COMMAND
    "Bash": ToolMeta("Bash", "shell command", ToolCategory.COMMAND, _parse_bash_response),
    "PowerShell": ToolMeta("PowerShell", "PowerShell command", ToolCategory.COMMAND, _parse_bash_response),
    "REPL": ToolMeta("REPL", "REPL session", ToolCategory.COMMAND),
    # AGENT
    "Agent": ToolMeta("Agent", "subagent", ToolCategory.AGENT),
    "SendMessage": ToolMeta("SendMessage", "message", ToolCategory.AGENT),
    "Brief": ToolMeta("Brief", "brief output", ToolCategory.AGENT),
    # PLAN
    "EnterPlanMode": ToolMeta("EnterPlanMode", "plan mode", ToolCategory.PLAN),
    "ExitPlanMode": ToolMeta("ExitPlanMode", "plan exit", ToolCategory.PLAN),
    # TASK
    "TaskCreate": ToolMeta("TaskCreate", "task creation", ToolCategory.TASK),
    "TaskUpdate": ToolMeta("TaskUpdate", "task update", ToolCategory.TASK),
    "TaskGet": ToolMeta("TaskGet", "task query", ToolCategory.TASK),
    "TaskList": ToolMeta("TaskList", "task list", ToolCategory.TASK),
    "TaskStop": ToolMeta("TaskStop", "task stop", ToolCategory.TASK),
    "TaskOutput": ToolMeta("TaskOutput", "task output", ToolCategory.TASK),
    "TeamCreate": ToolMeta("TeamCreate", "team creation", ToolCategory.TASK),
    "TeamDelete": ToolMeta("TeamDelete", "team deletion", ToolCategory.TASK),
    # MCP
    "MCPTool": ToolMeta("MCPTool", "MCP tool", ToolCategory.MCP),
    "ListMcpResources": ToolMeta("ListMcpResources", "MCP resource list", ToolCategory.MCP),
    "ReadMcpResource": ToolMeta("ReadMcpResource", "MCP resource read", ToolCategory.MCP),
    "McpAuth": ToolMeta("McpAuth", "MCP authentication", ToolCategory.MCP),
    "Skill": ToolMeta("Skill", "skill invocation", ToolCategory.MCP),
    # WORKTREE
    "EnterWorktree": ToolMeta("EnterWorktree", "worktree entry", ToolCategory.WORKTREE),
    "ExitWorktree": ToolMeta("ExitWorktree", "worktree exit", ToolCategory.WORKTREE),
    # NOTEBOOK
    "NotebookEdit": ToolMeta("NotebookEdit", "notebook edit", ToolCategory.NOTEBOOK),
    # OTHER
    "AskUserQuestion": ToolMeta("AskUserQuestion", "user question", ToolCategory.OTHER),
    "Config": ToolMeta("Config", "configuration", ToolCategory.OTHER),
    "RemoteTrigger": ToolMeta("RemoteTrigger", "remote trigger", ToolCategory.OTHER),
    "ScheduleCron": ToolMeta("ScheduleCron", "scheduled task", ToolCategory.OTHER),
    "Sleep": ToolMeta("Sleep", "pause", ToolCategory.OTHER),
    "LSP": ToolMeta("LSP", "language server", ToolCategory.OTHER),
    "TodoWrite": ToolMeta("TodoWrite", "todo update", ToolCategory.OTHER),
}


def get_tool_meta(tool_name: str) -> ToolMeta:
    """Get tool metadata. Returns OTHER fallback for unknown tools."""
    if tool_name in TOOL_REGISTRY:
        return TOOL_REGISTRY[tool_name]
    return ToolMeta(tool_name, tool_name, ToolCategory.OTHER)


def get_display_name(tool_name: str) -> str:
    """Get human-readable display name for a tool."""
    return get_tool_meta(tool_name).display_name


def parse_response(tool_name: str, response: Any) -> dict[str, str]:
    """Parse tool response into summary variables. Returns empty dict on failure."""
    meta = get_tool_meta(tool_name)
    if meta.response_parser is None:
        return {}
    try:
        return meta.response_parser(response)
    except Exception:
        return {}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator && uv run pytest tests/test_tool_registry.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator
git add src/claude_narrator/tool_registry.py tests/test_tool_registry.py
git commit -m "feat: add tool registry with 40+ tools, categories, and response parsers"
```

---

### Task 2: Integrate Registry into template.py

**Files:**
- Modify: `src/claude_narrator/narration/template.py:36-127` (_extract_variables and _get_sub_key)
- Modify: `tests/test_template.py`

- [ ] **Step 1: Write failing tests for registry integration**

Append to `tests/test_template.py`:

```python
class TestToolRegistryIntegration:
    """Tests for tool registry integration in template narration."""

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
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_response": {"exit_code": 0, "stdout": "ok"},
        }
        variables = _extract_variables(event)
        assert "result_summary" in variables
        assert "0" in variables["result_summary"]

    def test_result_summary_for_grep(self):
        from claude_narrator.narration.template import _extract_variables
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Grep",
            "tool_response": "a.py:1:match\nb.py:2:match",
        }
        variables = _extract_variables(event)
        assert variables["result_summary"] == "2 matches"

    def test_no_result_summary_without_response(self):
        from claude_narrator.narration.template import _extract_variables
        event = {"hook_event_name": "PostToolUse", "tool_name": "Bash"}
        variables = _extract_variables(event)
        assert "result_summary" not in variables

    def test_pre_tool_use_no_result_summary(self):
        from claude_narrator.narration.template import _extract_variables
        event = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {}}
        variables = _extract_variables(event)
        assert "result_summary" not in variables


class TestNotificationSubKey:
    """Tests for Notification notification_type sub-key routing."""

    def test_idle_prompt(self, narrator):
        event = {"hook_event_name": "Notification", "notification_type": "idle_prompt", "message": "waiting"}
        result = narrator.narrate(event)
        assert result is not None
        assert "input" in result.lower()

    def test_unknown_notification_type_uses_default(self, narrator):
        event = {"hook_event_name": "Notification", "notification_type": "some_new_type", "message": "hi"}
        result = narrator.narrate(event)
        assert result is not None
        assert "Attention" in result or "needed" in result

    def test_no_notification_type_uses_default(self, narrator):
        event = {"hook_event_name": "Notification", "message": "hello"}
        result = narrator.narrate(event)
        assert result is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator && uv run pytest tests/test_template.py::TestToolRegistryIntegration tests/test_template.py::TestNotificationSubKey -v`
Expected: FAIL — `display_name` not in variables, Notification sub-key not routed

- [ ] **Step 3: Modify _extract_variables() in template.py**

Add at the top of `_extract_variables()`, right after `variables["tool_name"] = ...` (line 39):

```python
    # Tool registry enrichment
    from claude_narrator.tool_registry import get_display_name, get_tool_meta, parse_response as _parse_response
    variables["display_name"] = get_display_name(variables["tool_name"])
    variables["category"] = get_tool_meta(variables["tool_name"]).category.value
```

Add at the end of `_extract_variables()`, before `return variables` (line 119):

```python
    # PostToolUse result summary via registry
    if event.get("hook_event_name") == "PostToolUse" and "tool_response" in event:
        summary_vars = _parse_response(variables["tool_name"], event["tool_response"])
        variables.update(summary_vars)
```

- [ ] **Step 4: Modify _get_sub_key() in template.py**

Add a Notification branch after the SessionStart branch (line 126):

```python
def _get_sub_key(event: dict[str, Any]) -> str:
    """Get the sub-key for template lookup. Falls back to tool_name."""
    event_name = event.get("hook_event_name", "")
    if event_name == "SessionStart":
        return event.get("source", "default")
    if event_name == "Notification":
        return event.get("notification_type", "default")
    return event.get("tool_name", "")
```

- [ ] **Step 5: Run all tests**

Run: `cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator && uv run pytest -v`
Expected: All PASS (including new tests, existing 218 tests unchanged)

- [ ] **Step 6: Commit**

```bash
cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator
git add src/claude_narrator/narration/template.py tests/test_template.py
git commit -m "feat: integrate tool registry into template variable extraction and notification sub-keys"
```

---

### Task 3: Update i18n Base Templates (en/zh/ja)

**Files:**
- Modify: `src/claude_narrator/i18n/en.json`
- Modify: `src/claude_narrator/i18n/zh.json`
- Modify: `src/claude_narrator/i18n/ja.json`

- [ ] **Step 1: Write failing test for new templates**

Append to `tests/test_template.py`:

```python
class TestEnrichedTemplates:
    """Tests for new tool-specific and notification-type templates."""

    def test_web_search_pre(self, narrator):
        event = {"hook_event_name": "PreToolUse", "tool_name": "WebSearch", "tool_input": {}}
        result = narrator.narrate(event)
        assert result is not None
        assert "web" in result.lower() or "search" in result.lower()

    def test_enter_plan_mode(self, narrator):
        event = {"hook_event_name": "PreToolUse", "tool_name": "EnterPlanMode", "tool_input": {}}
        result = narrator.narrate(event)
        assert result is not None
        assert "plan" in result.lower()

    def test_post_bash_with_summary(self, narrator):
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_response": "line1\nline2\nline3",
        }
        result = narrator.narrate(event)
        assert result is not None
        assert "3" in result

    def test_post_grep_with_summary(self, narrator):
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Grep",
            "tool_response": "a:1:x\nb:2:y",
        }
        result = narrator.narrate(event)
        assert result is not None
        assert "2" in result

    def test_notification_idle_zh(self):
        narrator = TemplateNarrator(language="zh")
        event = {"hook_event_name": "Notification", "notification_type": "idle_prompt"}
        result = narrator.narrate(event)
        assert result is not None
        assert "输入" in result

    def test_notification_idle_ja(self):
        narrator = TemplateNarrator(language="ja")
        event = {"hook_event_name": "Notification", "notification_type": "idle_prompt"}
        result = narrator.narrate(event)
        assert result is not None
        assert "入力" in result
```

- [ ] **Step 2: Run test to see failures**

Run: `cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator && uv run pytest tests/test_template.py::TestEnrichedTemplates -v`
Expected: FAIL — no specific template for WebSearch, EnterPlanMode; no Notification sub-keys

- [ ] **Step 3: Update en.json**

Replace full content of `src/claude_narrator/i18n/en.json`:

```json
{
    "PreToolUse": {
        "Read": "Reading {file_path}",
        "Write": "Writing to {file_path}",
        "Edit": "Editing {file_path}",
        "Bash": "Running command",
        "Glob": "Searching files",
        "Grep": "Searching code",
        "Agent": "Starting agent",
        "WebSearch": "Searching the web",
        "WebFetch": "Fetching web page",
        "EnterPlanMode": "Entering plan mode",
        "ExitPlanMode": "Exiting plan mode",
        "TaskCreate": "Creating a task",
        "SendMessage": "Sending a message",
        "NotebookEdit": "Editing notebook",
        "Skill": "Invoking skill",
        "EnterWorktree": "Entering worktree",
        "ExitWorktree": "Exiting worktree",
        "default": "Using {display_name}"
    },
    "PostToolUse": {
        "Read": "Read complete: {result_summary}",
        "Write": "Write complete",
        "Edit": "Edit complete",
        "Bash": "Command done: {result_summary}",
        "Grep": "Search done: {result_summary}",
        "Glob": "Found {result_summary}",
        "WebSearch": "Web search done: {result_summary}",
        "default": "{display_name} done"
    },
    "PostToolUseFailure": {
        "Bash": "Command failed",
        "default": "{tool_name} failed"
    },
    "Stop": {
        "default": "Task complete"
    },
    "Notification": {
        "idle_prompt": "Waiting for your input",
        "worker_permission_prompt": "A worker needs your permission",
        "computer_use_enter": "Entering computer use mode",
        "computer_use_exit": "Exiting computer use mode",
        "auth_success": "Authentication successful",
        "elicitation_complete": "Server interaction completed",
        "elicitation_response": "Server response sent",
        "default": "Attention needed"
    },
    "SubagentStart": {
        "default": "Starting subtask"
    },
    "SubagentStop": {
        "default": "Subtask complete"
    },
    "SessionStart": {
        "startup": "New session started",
        "resume": "Resuming session",
        "clear": "Session cleared",
        "compact": "Session restarted after compaction",
        "default": "Session started"
    },
    "PreCompact": {
        "default": "Compacting context"
    },
    "StopFailure": {"default": "Task failed: {error}"},
    "PostCompact": {"default": "Context compacted"},
    "SessionEnd": {"default": "Session ended"},
    "TaskCreated": {"default": "New task: {task_subject}"},
    "TaskCompleted": {"default": "Task done: {task_subject}"},
    "PermissionDenied": {"default": "Permission denied for {tool_name}"},
    "PermissionRequest": {"default": "Permission needed for {tool_name}"},
    "WorktreeCreate": {"default": "Worktree created: {name}"},
    "WorktreeRemove": {"default": "Worktree removed"},
    "CwdChanged": {"default": "Changed to {new_cwd}"},
    "FileChanged": {"default": "File changed: {file_path}"},
    "ContextThreshold": {"default": "Context {threshold} percent used"}
}
```

- [ ] **Step 4: Update zh.json**

Apply same structural changes to `src/claude_narrator/i18n/zh.json`:
- `PreToolUse`: add `WebSearch`→"搜索网页", `WebFetch`→"获取网页", `EnterPlanMode`→"进入计划模式", `ExitPlanMode`→"退出计划模式", `TaskCreate`→"创建任务", `SendMessage`→"发送消息", `NotebookEdit`→"编辑笔记本", `Skill`→"调用技能", `EnterWorktree`→"进入工作树", `ExitWorktree`→"退出工作树", `default`→"使用 {display_name}"
- `PostToolUse`: `Read`→"读取完成: {result_summary}", `Bash`→"命令完成: {result_summary}", `Grep`→"搜索完成: {result_summary}", `Glob`→"找到 {result_summary}", `WebSearch`→"网页搜索完成: {result_summary}", `default`→"{display_name} 完成"
- `Notification`: add `idle_prompt`→"等待你的输入", `worker_permission_prompt`→"工作者需要你的权限", `computer_use_enter`→"进入计算机使用模式", `computer_use_exit`→"退出计算机使用模式", `auth_success`→"认证成功", `elicitation_complete`→"服务器交互完成", `elicitation_response`→"服务器响应已发送", `default`→"需要你的注意"

- [ ] **Step 5: Update ja.json**

Apply same structural changes to `src/claude_narrator/i18n/ja.json`:
- `PreToolUse`: add `WebSearch`→"ウェブ検索中", `WebFetch`→"ウェブページ取得中", `EnterPlanMode`→"プランモード開始", `ExitPlanMode`→"プランモード終了", `TaskCreate`→"タスク作成中", `SendMessage`→"メッセージ送信中", `NotebookEdit`→"ノートブック編集中", `Skill`→"スキル呼び出し", `EnterWorktree`→"ワークツリーに入る", `ExitWorktree`→"ワークツリーを出る", `default`→"{display_name} を使用中"
- `PostToolUse`: `Read`→"読み込み完了: {result_summary}", `Bash`→"コマンド完了: {result_summary}", `Grep`→"検索完了: {result_summary}", `Glob`→"{result_summary}", `WebSearch`→"ウェブ検索完了: {result_summary}", `default`→"{display_name} 完了"
- `Notification`: add `idle_prompt`→"入力をお待ちしています", `worker_permission_prompt`→"ワーカーが権限を必要としています", `computer_use_enter`→"コンピュータ使用モード開始", `computer_use_exit`→"コンピュータ使用モード終了", `auth_success`→"認証成功", `elicitation_complete`→"サーバー操作完了", `elicitation_response`→"サーバー応答送信済み", `default`→"確認が必要です"

- [ ] **Step 6: Run all tests**

Run: `cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator && uv run pytest -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator
git add src/claude_narrator/i18n/en.json src/claude_narrator/i18n/zh.json src/claude_narrator/i18n/ja.json tests/test_template.py
git commit -m "feat: enriched i18n base templates with tool-specific and notification-type entries"
```

---

### Task 4: Update Personality Templates (9 files)

**Files:**
- Modify: `src/claude_narrator/i18n/en.casual.json`
- Modify: `src/claude_narrator/i18n/en.professional.json`
- Modify: `src/claude_narrator/i18n/en.tengu.json`
- Modify: `src/claude_narrator/i18n/zh.casual.json`
- Modify: `src/claude_narrator/i18n/zh.professional.json`
- Modify: `src/claude_narrator/i18n/zh.tengu.json`
- Modify: `src/claude_narrator/i18n/ja.casual.json`
- Modify: `src/claude_narrator/i18n/ja.professional.json`
- Modify: `src/claude_narrator/i18n/ja.tengu.json`

- [ ] **Step 1: Update all 9 personality templates**

For each personality file, apply the same structural additions as the base templates but with tone-appropriate text:

**Key additions per file:**
- `PreToolUse`: add same new tool keys (WebSearch, EnterPlanMode, etc.) with personality-appropriate wording; change `default` to use `{display_name}`
- `PostToolUse`: add `Grep`, `Glob`, `WebSearch` with `{result_summary}`; change `default` to use `{display_name}`
- `Notification`: add 7 `notification_type` sub-keys with personality-appropriate wording

**Tone examples for Notification.idle_prompt:**
- casual en: "Hey, your turn"
- professional en: "Awaiting user input"
- tengu en: "the oracle awaits your words"
- casual zh: "轮到你了"
- professional zh: "正在等待用户输入"
- tengu zh: "神谕等待你的话语"
- casual ja: "あなたの番だよ"
- professional ja: "ユーザーの入力をお待ちしています"
- tengu ja: "神託があなたの言葉を待つ"

- [ ] **Step 2: Run all tests**

Run: `cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator && uv run pytest -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator
git add src/claude_narrator/i18n/*.json
git commit -m "feat: enriched personality templates with tool-specific and notification entries"
```

---

### Task 5: Update Documentation

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `docs/README.zh.md`
- Modify: `docs/README.ja.md`

- [ ] **Step 1: Update CHANGELOG.md**

Add a `[0.4.0]` section at the top documenting:
- Tool Registry: 40+ tools with display names, categories, response parsers
- Notification type-aware narration: 7 notification_type sub-keys
- PostToolUse result summaries for Bash, Grep, Glob, Read, WebSearch
- `{display_name}` variable for human-readable tool names in default templates

- [ ] **Step 2: Update README files**

In all 3 README files, update the "Supported Hook Events" table to note enriched narration for PreToolUse/PostToolUse/Notification events.

- [ ] **Step 3: Run final test suite**

Run: `cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator && uv run pytest -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
cd /Users/hoshizora/Desktop/AI-Agents/for-claude-code/claude-narrator
git add CHANGELOG.md README.md docs/README.zh.md docs/README.ja.md
git commit -m "docs: document smart narration features in changelog and readmes"
```
