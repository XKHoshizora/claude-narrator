# Claude Narrator

> TTS audio narration for Claude Code — hear what Claude is doing without watching the terminal.

Claude Narrator is a plugin that uses Claude Code's hooks system to speak out work status in real-time. It tells you when files are being read, edited, commands executed, tasks completed, and when your attention is needed.

## Quick Start

```bash
pip install claude-narrator
claude-narrator install
claude-narrator start
```

## Test

```bash
claude-narrator test "Hello, this is a test"
```

## Usage

```bash
claude-narrator start        # Start the narration daemon
claude-narrator stop         # Stop the daemon
claude-narrator test "text"  # Test TTS output
claude-narrator install      # Install hooks into Claude Code
claude-narrator uninstall    # Remove hooks
```

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
    "voice": "en-US-AriaNeural"
  }
}
```

### Verbosity Levels

| Level | What gets narrated |
|-------|-------------------|
| `minimal` | Task completion, errors, permission prompts |
| `normal` | Above + file operations, subagent activity |
| `verbose` | Everything |

### Supported TTS Engines

| Engine | Platform | Notes |
|--------|----------|-------|
| `edge-tts` (default) | All | Free, high quality, requires internet |
| `say` | macOS | System built-in, zero dependencies |
| `espeak` | Linux | Offline, install via package manager |
| `openai` | All | Best quality, requires API key |

## Requirements

- Python 3.10+
- Claude Code v1.0.80+

## License

MIT
