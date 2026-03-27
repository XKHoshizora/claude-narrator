# Changelog

All notable changes to Claude Narrator will be documented in this file.

## [0.1.0] - 2026-03-27

### Phase 1: MVP
- Core daemon with asyncio event loop and PID management
- Hook script for forwarding Claude Code events via Unix Socket (HTTP fallback on Windows)
- Template-based narration engine with English i18n
- edge-tts integration for speech synthesis
- pygame-based async audio player
- Priority queue with overflow management (HIGH/MEDIUM/LOW)
- CLI commands: `start`, `stop`, `test`, `install`, `uninstall`
- Configuration system with deep merge and validation

### Phase 2: Polish
- Full CLI: `status`, `restart`, `reload`, `config get/set/reset`, `cache clear`
- Hot-reload config via `reload` command (SIGHUP signal, no daemon restart needed)
- Claude Code plugin format (`.claude-plugin/`) with `/claude-narrator:setup` wizard
- Verbosity filtering (minimal/normal/verbose)
- Event coalescer — merges rapid consecutive events
- Interruptible playback — high-priority events stop current audio
- Multi-language templates: Chinese (zh), Japanese (ja)
- LRU audio cache
- Additional TTS engines: macOS `say`, `espeak-ng`, OpenAI TTS API

### Phase 3: Enhancement
- LLM narration mode (Ollama/OpenAI/Anthropic) with template fallback
- Sound effects mode — event-type audio cues
- Custom event filter rules (ignore_tools, ignore_paths, custom_rules)
- Web UI dashboard at `http://localhost:19822`
