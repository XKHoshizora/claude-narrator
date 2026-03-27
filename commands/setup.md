---
description: Interactive setup wizard for Claude Narrator
allowed-tools: Bash, Read, Edit, AskUserQuestion
---

# Claude Narrator Setup

You are helping the user set up Claude Narrator, a TTS audio narration plugin for Claude Code.

## Step 1: Check Python Environment

Run this command to detect the Python environment:

```bash
which python3 && python3 --version 2>&1 || echo "PYTHON_NOT_FOUND"
```

If Python 3.10+ is not found, tell the user to install Python first.

## Step 2: Check if claude-narrator is installed

```bash
python3 -c "import claude_narrator; print(claude_narrator.__version__)" 2>&1 || echo "NOT_INSTALLED"
```

If NOT_INSTALLED, tell the user:
```
pip install claude-narrator
```
Then re-check.

## Step 3: Choose language

Use AskUserQuestion to ask the user their preferred narration language:
- English (en)
- Chinese (zh)
- Japanese (ja)

## Step 4: Choose TTS engine

Use AskUserQuestion to ask which TTS engine to use:
- edge-tts (recommended, free, high quality, requires internet)
- say (macOS only, zero dependencies)
- espeak (Linux, offline)
- openai (best quality, requires API key)

## Step 5: Choose verbosity

Use AskUserQuestion:
- minimal — Only task completion, errors, permission prompts
- normal (recommended) — Above + file operations, subagent activity
- verbose — Everything

## Step 6: Apply configuration

Run these commands based on user's choices:

```bash
claude-narrator config set general.language {language}
claude-narrator config set tts.engine {engine}
claude-narrator config set general.verbosity {verbosity}
```

## Step 7: Install hooks

```bash
claude-narrator install
```

## Step 8: Test TTS

Run a test based on the chosen language:
- English: `claude-narrator test "Hello, Claude Narrator is ready"`
- Chinese: `claude-narrator test "你好，Claude Narrator 已就绪"`
- Japanese: `claude-narrator test "こんにちは、Claude Narrator の準備ができました"`

Ask if the user heard the audio. If not, troubleshoot audio setup.

## Step 9: Start daemon

```bash
claude-narrator start
```

Tell the user setup is complete. They will now hear narration when Claude Code works.

Key commands to remember:
- `claude-narrator stop` — Stop narration
- `claude-narrator status` — Check status
- `/claude-narrator:configure` — Change settings

## Optional: Sound Effects

Ask the user if they want to enable sound effects using AskUserQuestion (options: Yes, No).

If yes:
```bash
claude-narrator config set sounds.enabled true
```

## Optional: Web UI

Ask if they want to enable the web monitoring dashboard (options: Yes, No).

If yes:
```bash
claude-narrator config set web.enabled true
claude-narrator restart
```

Tell the user the dashboard is available at http://127.0.0.1:19822.
