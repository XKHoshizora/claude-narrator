# Claude Narrator

**English** | [中文](docs/README.zh.md) | [日本語](docs/README.ja.md)

> TTS audio narration for Claude Code — hear what Claude is doing without watching the terminal.

Claude Narrator uses Claude Code's hooks system to speak work status in real-time. File reads, edits, command execution, task completion, permission prompts — all narrated by voice.

## Quick Start

### Option 1: pip install

```bash
pip install claude-narrator
claude-narrator install
claude-narrator start
```

### Option 2: Claude Code Plugin

```
/plugin install claude-narrator
/claude-narrator:setup
```

## Test

```bash
claude-narrator test "Hello, Claude Narrator is ready"
```

## Commands

```bash
claude-narrator start [-f|--foreground] [--web]  # Start daemon (foreground / with web UI)
claude-narrator stop                              # Stop daemon
claude-narrator restart [-f|--foreground]          # Restart daemon
claude-narrator status                            # Show daemon status
claude-narrator test "text"                       # Test TTS output
claude-narrator install                           # Install hooks into Claude Code
claude-narrator uninstall                         # Remove hooks
claude-narrator config get <key>                  # Get config value (e.g. general.verbosity)
claude-narrator config set <key> <value>          # Set config value
claude-narrator config reset                      # Reset to defaults
claude-narrator cache clear                       # Clear audio cache
```

## How It Works

```mermaid
flowchart LR
    CC[Claude Code] -->|Hook event| HS[Hook Script]
    HS -->|JSON via Unix Socket| D[TTS Daemon]
    D --> F[Verbosity Filter]
    F --> C[Event Coalescer]
    C --> N[Narration Generator<br/>Template / LLM]
    N --> Q[Priority Queue]
    Q --> TTS[TTS Engine]
    TTS --> P[Audio Playback]
```

- **Hook Script**: Lightweight forwarder — reads stdin JSON, sends to daemon, exits immediately. Never blocks Claude Code.
- **Daemon**: asyncio-based background process handling all logic.
- **Event Coalescer**: Merges rapid consecutive events (e.g., 5 Read calls → "5 Read operations").
- **Priority Queue**: HIGH (errors, notifications) interrupts current playback; LOW (tool calls) dropped when queue is full.

## Configuration

Config file: `~/.claude-narrator/config.json`

```json
{
  "general": {
    "verbosity": "normal",
    "language": "en",
    "enabled": true
  },
  "tts": {
    "engine": "edge-tts",
    "voice": "en-US-AriaNeural",
    "openai": {
      "api_key_env": "OPENAI_API_KEY",
      "model": "tts-1",
      "voice": "nova"
    }
  },
  "narration": {
    "mode": "template",
    "max_queue_size": 5,
    "max_narration_seconds": 15,
    "skip_rapid_events": true,
    "llm": {
      "provider": "ollama",
      "model": "qwen2.5:3b"
    }
  },
  "cache": {
    "enabled": true,
    "max_size_mb": 50
  },
  "filters": {
    "ignore_tools": [],
    "ignore_paths": [],
    "only_tools": null,
    "custom_rules": []
  },
  "web": {
    "enabled": false,
    "host": "127.0.0.1",
    "port": 19822
  }
}
```

### Verbosity Levels

| Level | What gets narrated |
|-------|-------------------|
| `minimal` | Task completion, errors, permission prompts |
| `normal` (default) | Above + file operations, subagent activity |
| `verbose` | Everything |

### TTS Engines

| Engine | Platform | Notes |
|--------|----------|-------|
| `edge-tts` (default) | All | Free, high quality, requires internet |
| `say` | macOS | System built-in, zero dependencies |
| `espeak` | Linux | Offline, install via package manager |
| `openai` | All | Best quality, requires API key |

### Languages

| Language | Code | Default Voice |
|----------|------|---------------|
| English | `en` | en-US-AriaNeural |
| Chinese | `zh` | zh-CN-XiaoxiaoNeural |
| Japanese | `ja` | ja-JP-NanamiNeural |

### Narration Modes

- **Template** (default): Fast, deterministic. Uses i18n JSON templates to generate short phrases like "Reading src/app.py".
- **LLM**: Natural language narration via Ollama (local), OpenAI, or Anthropic. Falls back to template on timeout (3s).

```bash
claude-narrator config set narration.mode llm
claude-narrator config set narration.llm.provider ollama
claude-narrator config set narration.llm.model qwen2.5:3b
```

### Custom Filters

Filter events by tool, file path, or custom rules:

```bash
# Ignore all Read events
claude-narrator config set filters.ignore_tools '["Read"]'

# Only narrate specific tools
claude-narrator config set filters.only_tools '["Write", "Edit", "Bash"]'
```

Config example with custom rules:

```json
{
  "filters": {
    "ignore_paths": ["node_modules/*", "*.lock"],
    "custom_rules": [
      {
        "match": { "tool": "Bash", "input_contains": "npm test" },
        "action": "skip"
      }
    ]
  }
}
```

### Sound Effects

Play short audio cues alongside (or instead of) TTS:

```json
{
  "sounds": {
    "enabled": true,
    "directory": "~/.claude-narrator/sounds",
    "events": {
      "Stop": "complete.wav",
      "Notification": "alert.wav",
      "PostToolUseFailure": "error.wav"
    }
  }
}
```

### Web UI

Real-time dashboard showing daemon status and event stream:

```bash
claude-narrator config set web.enabled true
claude-narrator restart
# Open http://127.0.0.1:19822
```

## Requirements

- Python 3.10+
- Claude Code v1.0.80+

## License

MIT
