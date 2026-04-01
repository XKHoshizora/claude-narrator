# Changelog

All notable changes to Claude Narrator will be documented in this file.

## [0.4.0] - 2026-04-01

### 智能叙述增强（Smart Narration）
- **Tool Registry**：新增工具元数据注册表（`tool_registry.py`），42 个 Claude Code 工具注册了 display_name、category 和可选的 response_parser
- **工具特化叙述**：PreToolUse/PostToolUse 模板新增 10+ 个工具专用条目（WebSearch、EnterPlanMode、TaskCreate 等），default 模板改用 `{display_name}` 人类可读名
- **Notification 类型解析**：Notification 事件从统一的"需要注意"细化为 7 个 notification_type 子键（idle_prompt、worker_permission_prompt、computer_use_enter 等）
- **PostToolUse 结果摘要**：Bash/Grep/Glob/Read/WebSearch 5 个工具注册了 response_parser，PostToolUse 模板使用 `{result_summary}` 变量（如"搜索完成: 12 matches"）
- 所有 12 个 i18n 模板文件（3 语言 × 4 人格）全部同步更新
- **Tengu Words 更新**：从第三方 GitHub 的 90 词更新为 Claude Code 官方源码 `spinnerVerbs.ts` 的完整 187 词

### 性能优化
- **异步 Hook 协议**：hook 脚本输出 `{"async": true}` 让 Claude Code 立即放行，不再等待 Python 冷启动（~100-200ms → ~1ms）
- **TTS 缓存集成**：`AudioCache` 模块集成到 daemon 的 TTS 路径，重复短语从网络请求（1-5s）降至磁盘缓存读取（~1ms）
- **合并窗口缩短**：事件合并窗口从 2.0 秒缩短至 0.5 秒，提升响应速度

## [0.3.0] - 2026-04-01

### 扩展 Hook 事件覆盖（基于 Claude Code v2.1.88 源码分析）
- 支持的 hook 事件从 9 种扩展到 20 种（27 种中选取了有叙述价值的事件）
- **Tier 1 新增**（高价值）：`StopFailure`、`PostCompact`、`SessionEnd`、`TaskCreated`、`TaskCompleted`、`PermissionDenied`、`PermissionRequest`
- **Tier 2 新增**（增强）：`WorktreeCreate`、`WorktreeRemove`、`CwdChanged`、`FileChanged`
- 跳过低价值事件：`UserPromptSubmit`、`Setup`、`Elicitation`/`ElicitationResult`、`ConfigChange`、`InstructionsLoaded`、`TeammateIdle`

### 丰富变量提取
- 新增 `error`、`last_assistant_message`、`agent_type`、`task_subject`、`compact_summary` 等模板变量
- 长文本自动截断（80 字符），避免 TTS 朗读过长内容
- `SessionStart` 支持 `source` 子键区分 startup/resume/clear/compact

### 模板子键查找
- 新增 `_get_sub_key()` 机制，非工具事件可按上下文子键选择不同模板
- SessionStart: "新会话开始" vs "恢复会话" vs "压缩后重启会话"
- SessionEnd: 按 reason 区分
- FileChanged: 按 event 类型（change/add/unlink）区分

### 语音级别更新
- `StopFailure`、`PermissionDenied`、`PermissionRequest` 加入 MINIMAL（始终播报）
- `SessionStart`、`SessionEnd`、`PostCompact`、`TaskCreated`、`TaskCompleted` 加入 NORMAL
- Tier 2 事件仅在 VERBOSE 级别播报

### i18n 模板
- 所有 12 个模板文件（3 语言 × 4 人格）均添加新事件模板
- 各人格保持风格一致（casual 口语化、professional 正式、tengu 趣味化）

## [0.2.0] - 2026-03-27

### Personality System
- 4 built-in narration personalities: concise, tengu, professional, casual
- Three-slot composition (prefix/body/suffix) with multi-personality layering
- 90 Tengu spinner words from Anthropic's vocabulary
- Optional auto-update of tengu words from GitHub (`tengu_prefix_auto_update`)
- Multi-language support (en/zh/ja) for all personalities

### Context Monitor
- Optional statusline bridge for context window utilization tracking
- Threshold-based voice announcements (configurable, default: 50%, 70%, 85%, 95%)
- New `ContextThreshold` event type with personality-aware templates
- Warning: conflicts with claude-hud (only one statusline allowed)

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
