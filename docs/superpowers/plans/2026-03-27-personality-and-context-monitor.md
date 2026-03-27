# Personality System + Context Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a personality-based narration system (concise/tengu/professional/casual) with three-slot composition (prefix/body/suffix) and layered multi-personality support, plus an optional context window utilization monitor.

**Architecture:** TemplateNarrator is refactored to load personality layers from `{lang}.{personality}.json` files. Each layer contributes prefix, body, and/or suffix slots. Multi-personality configs are composed by merging prefix/suffix pools and resolving body templates by priority. A separate ContextMonitor component optionally bridges Claude Code's statusline for threshold-based token usage announcements.

**Tech Stack:** Python 3.10+, existing claude-narrator infrastructure, httpx (optional for tengu auto-update)

**Spec:** `docs/superpowers/specs/2026-03-27-personality-and-context-monitor-design.md`

**IMPORTANT:** Always use `uv run python` not bare `python`.

---

## File Structure

### New Files

```
src/claude_narrator/i18n/
├── tengu_words.json           # 90 Tengu spinner words (JSON array)
├── en.tengu.json              # English Tengu personality
├── en.professional.json       # English professional personality
├── en.casual.json             # English casual personality
├── zh.tengu.json              # Chinese Tengu personality
├── zh.professional.json       # Chinese professional personality
├── zh.casual.json             # Chinese casual personality
├── ja.tengu.json              # Japanese Tengu personality
├── ja.professional.json       # Japanese professional personality
└── ja.casual.json             # Japanese casual personality

src/claude_narrator/
└── context_monitor.py         # Statusline bridge + threshold monitor coroutine

tests/
├── test_personality.py        # Personality system tests
└── test_context_monitor.py    # Context monitor tests
```

### Modified Files

| File | Changes |
|------|---------|
| `src/claude_narrator/narration/template.py` | Rewrite: personality loading, PersonalityLayer, three-slot composition |
| `src/claude_narrator/config.py` | Add personality, tengu_prefix_auto_update, context_monitor to defaults + validation |
| `src/claude_narrator/daemon.py` | Pass personality to narrator; optionally start context monitor; update reload_config |
| `src/claude_narrator/narration/llm.py` | Accept personality param, forward to fallback |
| `src/claude_narrator/narration/verbosity.py` | Add ContextThreshold to MINIMAL_EVENTS |
| `src/claude_narrator/queue.py` | Add ContextThreshold to EVENT_PRIORITY |
| `src/claude_narrator/installer.py` | Register/unregister statusline for context_monitor |
| `src/claude_narrator/i18n/en.json` | Add ContextThreshold template |
| `src/claude_narrator/i18n/zh.json` | Add ContextThreshold template |
| `src/claude_narrator/i18n/ja.json` | Add ContextThreshold template |
| `pyproject.toml` | Add package-data for i18n/*.json if needed |

---

## Task 1: Config Update

**Files:**
- Modify: `src/claude_narrator/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Add new constants and DEFAULT_CONFIG fields**

In `config.py`, add:
```python
VALID_PERSONALITIES = ("concise", "tengu", "professional", "casual")
```

In `DEFAULT_CONFIG`, add to `"narration"` section:
```python
"personality": "concise",
"tengu_prefix_auto_update": False,
```

Add new top-level section:
```python
"context_monitor": {
    "enabled": False,
    "thresholds": [50, 70, 85, 95],
},
```

- [ ] **Step 2: Add personality validation in validate_config()**

```python
# After existing narration validation
personality = narration.get("personality", "concise")
if isinstance(personality, str):
    if personality not in VALID_PERSONALITIES:
        narration["personality"] = "concise"
elif isinstance(personality, list):
    valid = [p for p in personality if p in VALID_PERSONALITIES]
    narration["personality"] = valid if valid else "concise"
else:
    narration["personality"] = "concise"
result["narration"] = narration

# Validate context_monitor
ctx = result.get("context_monitor", {})
thresholds = ctx.get("thresholds", [50, 70, 85, 95])
if not isinstance(thresholds, list) or not all(isinstance(t, (int, float)) and 0 < t <= 100 for t in thresholds):
    ctx["thresholds"] = [50, 70, 85, 95]
result["context_monitor"] = ctx
```

- [ ] **Step 3: Add tests**

Append to `tests/test_config.py`:
```python
class TestPersonalityConfig:
    def test_default_personality(self):
        assert DEFAULT_CONFIG["narration"]["personality"] == "concise"

    def test_valid_single(self):
        config = deep_merge(DEFAULT_CONFIG, {"narration": {"personality": "tengu"}})
        assert validate_config(config)["narration"]["personality"] == "tengu"

    def test_valid_multi(self):
        config = deep_merge(DEFAULT_CONFIG, {"narration": {"personality": ["tengu", "professional"]}})
        assert validate_config(config)["narration"]["personality"] == ["tengu", "professional"]

    def test_invalid_falls_back(self):
        config = deep_merge(DEFAULT_CONFIG, {"narration": {"personality": "invalid"}})
        assert validate_config(config)["narration"]["personality"] == "concise"

    def test_mixed_filters_invalid(self):
        config = deep_merge(DEFAULT_CONFIG, {"narration": {"personality": ["tengu", "invalid"]}})
        assert validate_config(config)["narration"]["personality"] == ["tengu"]

class TestContextMonitorConfig:
    def test_default_disabled(self):
        assert DEFAULT_CONFIG["context_monitor"]["enabled"] is False

    def test_default_thresholds(self):
        assert DEFAULT_CONFIG["context_monitor"]["thresholds"] == [50, 70, 85, 95]

    def test_invalid_thresholds(self):
        config = deep_merge(DEFAULT_CONFIG, {"context_monitor": {"thresholds": "bad"}})
        assert validate_config(config)["context_monitor"]["thresholds"] == [50, 70, 85, 95]
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_config.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/claude_narrator/config.py tests/test_config.py
git commit -m "feat: add personality and context_monitor config fields"
```

---

## Task 2: Tengu Words + Personality Template Files

**Files:**
- Create: `src/claude_narrator/i18n/tengu_words.json`
- Create: 9 personality template files
- Modify: `src/claude_narrator/i18n/en.json`, `zh.json`, `ja.json` (add ContextThreshold)

- [ ] **Step 1: Create tengu_words.json**

`src/claude_narrator/i18n/tengu_words.json`: JSON array of 90 words (the complete list from the Tengu repo).

- [ ] **Step 2: Create en.tengu.json**

Complete file with `_meta`, `_prefixes: []` (loaded dynamically from tengu_words.json), `_suffixes: []`, and whimsical English templates for all 10 event types (PreToolUse, PostToolUse, PostToolUseFailure, Stop, Notification, SubagentStart, SubagentStop, SessionStart, PreCompact, ContextThreshold).

- [ ] **Step 3: Create en.professional.json**

Formal English templates. `_prefixes: []`, `_suffixes: []`.

- [ ] **Step 4: Create en.casual.json**

Casual English templates. `_prefixes: []`, `_suffixes: []`.

- [ ] **Step 5: Create zh.tengu.json, zh.professional.json, zh.casual.json**

Chinese equivalents of the three personalities.

- [ ] **Step 6: Create ja.tengu.json, ja.professional.json, ja.casual.json**

Japanese equivalents of the three personalities.

- [ ] **Step 7: Add ContextThreshold to existing base templates**

In `en.json`: `"ContextThreshold": { "default": "Context {threshold} percent used" }`
In `zh.json`: `"ContextThreshold": { "default": "上下文已使用 {threshold}%" }`
In `ja.json`: `"ContextThreshold": { "default": "コンテキスト {threshold}% 使用中" }`

- [ ] **Step 8: Commit**

```bash
git add src/claude_narrator/i18n/
git commit -m "feat: personality template files (tengu/professional/casual × en/zh/ja)"
```

---

## Task 3: Rewrite TemplateNarrator

**Files:**
- Modify: `src/claude_narrator/narration/template.py`
- Create: `tests/test_personality.py`

- [ ] **Step 1: Write failing tests**

`tests/test_personality.py` — tests for PersonalityLayer, three-slot composition, layered composition, backward compatibility, tengu word loading. Key tests:

```python
class TestBackwardCompatibility:
    def test_default_matches_old_behavior(self):
        narrator = TemplateNarrator("en")  # no personality arg
        event = {"hook_event_name": "Stop"}
        assert narrator.narrate(event) == "Task complete"

    def test_concise_explicit(self):
        narrator = TemplateNarrator("en", "concise")
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "/app.py"}}
        assert narrator.narrate(event) == "Reading /app.py"

class TestTenguPersonality:
    def test_has_prefix(self):
        narrator = TemplateNarrator("en", "tengu")
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "/app.py"}}
        result = narrator.narrate(event)
        assert "..." in result
        assert "app.py" in result

    def test_prefix_from_tengu_words(self):
        narrator = TemplateNarrator("en", "tengu")
        assert len(narrator._all_prefixes) == 90

class TestMultiPersonality:
    def test_prefix_from_tengu_body_from_first(self):
        narrator = TemplateNarrator("en", ["tengu", "professional"])
        # tengu is first, so tengu's body wins for normal events
        # but tengu also contributes prefixes
        event = {"hook_event_name": "Stop"}
        result = narrator.narrate(event)
        assert "..." in result  # has tengu prefix

    def test_high_priority_longest_body(self):
        narrator = TemplateNarrator("en", ["concise", "professional"])
        event = {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash"}
        result = narrator.narrate(event)
        assert len(result) > len("Command failed")

class TestCoalescedPreserved:
    def test_coalesced_unchanged(self):
        narrator = TemplateNarrator("en", "tengu")
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read", "_coalesced_count": 5}
        assert narrator.narrate(event) == "5 Read operations"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_personality.py -v`

- [ ] **Step 3: Implement PersonalityLayer and rewrite TemplateNarrator**

Rewrite `template.py`:
- Add `PersonalityLayer` dataclass
- New `__init__(language, personality="concise")` that loads layers
- Special handling: personality "tengu" → load tengu_words.json as prefixes
- `_resolve_body()`: first-match for normal events, longest for HIGH_PRIORITY_EVENTS
- `_assemble(prefix, body, suffix)`: join non-empty parts
- Preserve `_extract_variables()`, `_shorten_path()`, coalesced handling
- Add `threshold` and `used_percentage` to `_extract_variables()`

- [ ] **Step 4: Run all tests**

Run: `uv run python -m pytest tests/test_personality.py tests/test_template.py -v`
Expected: All pass (new + existing backward-compat)

- [ ] **Step 5: Run full suite**

Run: `uv run python -m pytest tests/ -v`
Expected: 128+ tests pass, no regressions

- [ ] **Step 6: Commit**

```bash
git add src/claude_narrator/narration/template.py tests/test_personality.py
git commit -m "feat: personality-based narration with three-slot composition"
```

---

## Task 4: Daemon + LLM Integration

**Files:**
- Modify: `src/claude_narrator/daemon.py`
- Modify: `src/claude_narrator/narration/llm.py`
- Modify: `src/claude_narrator/narration/verbosity.py`
- Modify: `src/claude_narrator/queue.py`

- [ ] **Step 1: Pass personality to TemplateNarrator in daemon.py**

Update both the `__init__` and `reload_config()` template narrator creation:
```python
self._narrator = TemplateNarrator(
    language=self._config["general"]["language"],
    personality=self._config["narration"].get("personality", "concise"),
)
```

- [ ] **Step 2: Pass personality to LLMNarrator in daemon.py and llm.py**

Update LLMNarrator constructor to accept `personality` and forward to fallback TemplateNarrator.

- [ ] **Step 3: Add ContextThreshold to verbosity.py and queue.py**

In `verbosity.py`: `MINIMAL_EVENTS = {"Stop", "Notification", "PostToolUseFailure", "ContextThreshold"}`
In `queue.py`: `"ContextThreshold": Priority.MEDIUM`

- [ ] **Step 4: Run all tests**

Run: `uv run python -m pytest tests/ -v`

- [ ] **Step 5: Commit**

```bash
git add src/claude_narrator/daemon.py src/claude_narrator/narration/llm.py src/claude_narrator/narration/verbosity.py src/claude_narrator/queue.py
git commit -m "feat: personality integration in daemon, LLM narrator, verbosity, and queue"
```

---

## Task 5: Tengu Auto-Update

**Files:**
- Modify: `src/claude_narrator/narration/template.py`
- Modify: `src/claude_narrator/daemon.py`

- [ ] **Step 1: Add tengu words loading with cache support**

In `template.py`, add method to load tengu words with priority: cached file > builtin snapshot.
Add module-level `async def update_tengu_words(config_dir)` that fetches from GitHub raw URL and caches.

- [ ] **Step 2: Call auto-update in daemon.start()**

```python
if self._config["narration"].get("tengu_prefix_auto_update", False):
    from claude_narrator.narration.template import update_tengu_words
    await update_tengu_words(self._config_dir)
```

- [ ] **Step 3: Add tests**

Test builtin loading, cached preference, mock auto-update success/failure.

- [ ] **Step 4: Commit**

```bash
git add src/claude_narrator/narration/template.py src/claude_narrator/daemon.py tests/test_personality.py
git commit -m "feat: tengu words auto-update from GitHub with local cache"
```

---

## Task 6: Context Monitor

**Files:**
- Create: `src/claude_narrator/context_monitor.py`
- Create: `tests/test_context_monitor.py`
- Modify: `src/claude_narrator/daemon.py`

- [ ] **Step 1: Create context_monitor.py**

Two components:
1. `statusline_main()` — reads stdin JSON, writes `context.json`
2. `ContextMonitorCoroutine` — polls `context.json`, checks thresholds, queues narrations

- [ ] **Step 2: Integrate into daemon**

In `daemon.start()`, if `context_monitor.enabled`:
```python
from claude_narrator.context_monitor import ContextMonitorCoroutine
monitor = ContextMonitorCoroutine(config_dir=..., thresholds=..., narrator=..., queue=...)
tasks.append(monitor.run())
```

- [ ] **Step 3: Write tests**

`tests/test_context_monitor.py` — threshold detection, once-only announcement, reset on drop, stale data, missing file.

- [ ] **Step 4: Commit**

```bash
git add src/claude_narrator/context_monitor.py tests/test_context_monitor.py src/claude_narrator/daemon.py
git commit -m "feat: context monitor with statusline bridge and threshold announcements"
```

---

## Task 7: Installer Update

**Files:**
- Modify: `src/claude_narrator/installer.py`
- Modify: `tests/test_installer.py`

- [ ] **Step 1: Add install_statusline() and uninstall_statusline()**

Register/remove statusline entry in `~/.claude/settings.json` with conflict warning.

- [ ] **Step 2: Update tests**

- [ ] **Step 3: Commit**

```bash
git add src/claude_narrator/installer.py tests/test_installer.py
git commit -m "feat: statusline registration for context monitor"
```

---

## Task 8: Documentation Update

**Files:** README.md, docs/README.zh.md, docs/README.ja.md, CHANGELOG.md, commands/setup.md, commands/configure.md

- [ ] **Step 1: Update all READMEs** with Personality and Context Monitor sections
- [ ] **Step 2: Update CHANGELOG** with v0.2.0 entries
- [ ] **Step 3: Update commands** with personality selection and context monitor setup
- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "docs: personality system and context monitor documentation"
```

---

## Verification

- [ ] `uv run python -m pytest tests/ -v` — all tests pass (128 existing + ~30 new)
- [ ] Manual: `personality: "concise"` → identical to current behavior
- [ ] Manual: `personality: "tengu"` → prefix + whimsical body
- [ ] Manual: `personality: ["tengu", "professional"]` → prefix + professional body
- [ ] Manual: `context_monitor.enabled: true` → threshold announcements work
- [ ] All 3 languages × 4 personalities load without error
