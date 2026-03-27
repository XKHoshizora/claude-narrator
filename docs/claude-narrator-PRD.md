# Claude Narrator — 项目需求文档

> **项目定位**: 一个开源的 Claude Code 插件，通过 TTS 语音实时播报 Claude Code 的工作状态，让开发者不用盯着终端也能知道 AI 在做什么。
>
> **差异化**: 现有生态中 statusline 类项目很多（claude-hud, ccstatusline, claude-dashboard 等），但 **TTS 语音播报** 方向几乎空白。本项目填补这一空缺。

---

## 1. 背景与动机

使用 Claude Code 时，如果不盯着终端屏幕，完全不知道它执行到哪了。尤其在以下场景中痛感强烈：

- 长时间运行的任务（重构、大规模文件修改）
- 多任务并行时，Claude Code 在另一个窗口运行
- 想离开座位休息，但又担心错过需要确认权限的提示

希望做一个插件，让 Claude Code 用语音"说出"自己正在做什么，做到什么步骤了。详细程度可以由用户配置。

---

## 2. 核心功能

### 2.1 事件监听

利用 Claude Code 的 **Hooks 系统** 监听以下生命周期事件：

| Hook 事件 | 触发时机 | 播报内容示例 |
|---|---|---|
| `PreToolUse` | 工具调用前 | "Reading src/app.py" |
| `PostToolUse` | 工具调用完成后 | "Finished editing app.py" |
| `PostToolUseFailure` | 工具调用失败 | "Command failed: npm test exit code 1" |
| `Stop` | Agent 完成响应 | "Task complete" |
| `Notification` | 需要用户注意 | "Permission needed" |
| `SubagentStart` | 子 Agent 启动 | "Starting subtask: explore directory" |
| `SubagentStop` | 子 Agent 完成 | "Subtask complete" |
| `SessionStart` | 会话开始 | "Session started, using Opus 4" |
| `PreCompact` | 上下文压缩前 | "Context nearly full, compacting" |

每个 Hook 通过 stdin 接收 JSON 数据，包含 `session_id`, `transcript_path`, `tool_name`, `tool_input` 等字段。

### 2.2 Verbosity 分级系统

用户可以设置播报详细程度，分为至少 3 个等级：

| 等级 | 说明 | 播报范围 |
|---|---|---|
| `minimal` | 只报关键节点 | Stop, Notification, 失败事件 |
| `normal`（默认） | 报主要操作 | 以上 + PreToolUse/PostToolUse（文件操作）, SubagentStart/Stop |
| `verbose` | 报所有事件 | 以上 + 每条 Bash 命令, 每次文件读取, SessionStart, PreCompact |

用户可通过配置文件或命令行参数设置等级。

### 2.3 TTS 引擎

支持多种 TTS 后端，用户可选择：

| 引擎 | 特点 | 适用场景 |
|---|---|---|
| **edge-tts**（默认推荐） | 免费、音质好、支持多语言 | 日常使用首选 |
| macOS `say` | 零依赖、系统原生 | macOS 用户的轻量选择 |
| espeak / piper | Linux 本地离线 | 离线环境 |
| OpenAI TTS API | 最自然 | 愿意付费追求体验的用户 |

要求：
- TTS 引擎通过抽象层实现，方便扩展新引擎
- 播放必须是异步的，不能阻塞 Hook 的返回
- 需要有队列机制：如果前一条还没播完，新消息进入队列，避免重叠
- 支持设置语言（至少英文、中文、日文）

### 2.4 智能播报文案生成

事件到播报文本的转换有两种模式：

**模式 A: 模板模式（默认）**
- 预定义模板，直接拼接
- 延迟极低
- 例: `PreToolUse + Write + /src/app.py` → "Writing to src/app.py"

**模式 B: LLM 模式（可选）**
- 将事件信息发给一个轻量 LLM（如本地 Ollama 或远程 API），生成更自然的播报
- 有一定延迟
- 例: 同样事件 → "I'm about to modify app.py now"
- 此模式为可选增强功能，不是 MVP 必须

---

## 3. 技术架构

### 3.1 整体架构

```
Claude Code
    │
    ├── Hook Events (stdin JSON)
    │       │
    │       ▼
    │   Hook Script (Python)
    │       │
    │       ├── Parse event & Verbosity filter
    │       │
    │       ├── Generate narration text (template / LLM)
    │       │
    │       └── Send to TTS Daemon ──► Audio playback
    │
    └── (Hook script returns immediately, never blocks Claude Code)
```

### 3.2 关键设计决策

1. **Daemon 进程**: TTS 播放应该由一个常驻后台进程处理。Hook 脚本通过 Unix socket 或 HTTP 把文本发给 Daemon，然后立即退出。这样 Hook 不会因为 TTS 延迟而阻塞 Claude Code。

2. **语言选择**: 推荐 **Python**，因为：
   - edge-tts 是 Python 库
   - Claude Code 的 Hook 生态大量使用 Python
   - asyncio 天然适合处理 TTS 队列

3. **配置文件**: 使用 `~/.claude-narrator/config.json`

### 3.3 配置文件示例

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
    "skip_rapid_events": true,
    "llm": {
      "provider": "ollama",
      "model": "qwen2.5:3b"
    }
  }
}
```

---

## 4. 安装与使用

### 4.1 安装流程

目标: 一条命令完成安装

```bash
# Option 1: pip install
pip install claude-narrator
claude-narrator install

# Option 2: manual
git clone https://github.com/<user>/claude-narrator
cd claude-narrator
python install.py
```

`install` 命令自动完成：
1. 创建配置目录 `~/.claude-narrator/`
2. 生成默认配置文件
3. 向 `~/.claude/settings.json` 注入 Hooks 配置
4. 启动 TTS Daemon

### 4.2 日常使用

```bash
# Start/stop the daemon
claude-narrator start
claude-narrator stop

# Change settings
claude-narrator config set verbosity verbose
claude-narrator config set tts.engine say
claude-narrator config set language zh

# Test TTS
claude-narrator test "Hello, this is a test message"

# Check status
claude-narrator status
```

---

## 5. 项目结构

```
claude-narrator/
├── src/
│   └── claude_narrator/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point (click/typer)
│       ├── daemon.py           # TTS Daemon (asyncio, queue management)
│       ├── config.py           # Config loading & validation
│       ├── installer.py        # Installer (inject hooks into settings.json)
│       ├── hooks/              # Claude Code Hook scripts
│       │   ├── on_event.py     # Unified entry: receive stdin JSON, forward to Daemon
│       │   └── (single script dispatches by hook_event_name)
│       ├── narration/          # Narration text generation
│       │   ├── template.py     # Template mode
│       │   └── llm.py          # LLM mode (optional)
│       ├── tts/                # TTS engine abstraction
│       │   ├── base.py         # Abstract base class
│       │   ├── edge.py         # edge-tts
│       │   ├── macos_say.py    # macOS say
│       │   ├── espeak.py       # espeak/piper
│       │   └── openai_tts.py   # OpenAI TTS
│       └── i18n/               # Multilingual narration templates
│           ├── en.json         # English (default)
│           ├── zh.json         # Chinese
│           └── ja.json         # Japanese
├── tests/
│   ├── test_narration.py
│   ├── test_tts_engines.py
│   ├── test_config.py
│   └── test_hooks.py
├── pyproject.toml
├── README.md                   # English README (primary)
├── README.zh.md                # Chinese README
├── LICENSE                     # MIT
└── CONTRIBUTING.md
```

---

## 6. 多语言播报模板示例

### English (en.json) — 默认语言

```json
{
  "PreToolUse": {
    "Read": "Reading {file_path}",
    "Write": "Writing to {file_path}",
    "Edit": "Editing {file_path}",
    "Bash": "Running: {command_short}",
    "Glob": "Searching files: {pattern}",
    "Grep": "Searching for: {query}",
    "default": "Using tool: {tool_name}"
  },
  "PostToolUse": {
    "Read": "Finished reading {file_path}",
    "Write": "Finished writing {file_path}",
    "Edit": "Finished editing {file_path}",
    "Bash": "Command complete",
    "default": "{tool_name} done"
  },
  "PostToolUseFailure": {
    "Bash": "Command failed",
    "default": "{tool_name} failed"
  },
  "Stop": {
    "default": "Task complete"
  },
  "Notification": {
    "permission_prompt": "Permission needed",
    "idle_prompt": "Waiting for your input",
    "default": "{message}"
  },
  "SubagentStart": {
    "default": "Starting subtask: {agent_type}"
  },
  "SubagentStop": {
    "default": "Subtask complete"
  },
  "SessionStart": {
    "default": "Session started"
  },
  "PreCompact": {
    "default": "Compacting context"
  }
}
```

### 中文 (zh.json)

```json
{
  "PreToolUse": {
    "Read": "正在读取 {file_path}",
    "Write": "准备写入 {file_path}",
    "Edit": "准备编辑 {file_path}",
    "Bash": "执行命令: {command_short}",
    "Glob": "搜索文件: {pattern}",
    "Grep": "搜索内容: {query}",
    "default": "调用工具: {tool_name}"
  },
  "PostToolUse": {
    "Read": "{file_path} 读取完成",
    "Write": "{file_path} 写入完成",
    "Edit": "{file_path} 修改完成",
    "Bash": "命令执行完成",
    "default": "{tool_name} 完成"
  },
  "PostToolUseFailure": {
    "Bash": "命令执行失败",
    "default": "{tool_name} 执行失败"
  },
  "Stop": {
    "default": "任务完成了"
  },
  "Notification": {
    "permission_prompt": "需要你确认权限",
    "idle_prompt": "在等你操作",
    "default": "{message}"
  },
  "SubagentStart": {
    "default": "启动子任务: {agent_type}"
  },
  "SubagentStop": {
    "default": "子任务完成"
  },
  "SessionStart": {
    "default": "会话已启动"
  },
  "PreCompact": {
    "default": "上下文准备压缩"
  }
}
```

### 日本語 (ja.json)

```json
{
  "PreToolUse": {
    "Read": "{file_path} を読み込み中",
    "Write": "{file_path} に書き込み中",
    "Edit": "{file_path} を編集中",
    "Bash": "コマンド実行: {command_short}",
    "Glob": "ファイル検索: {pattern}",
    "Grep": "検索中: {query}",
    "default": "ツール使用: {tool_name}"
  },
  "PostToolUse": {
    "Read": "{file_path} 読み込み完了",
    "Write": "{file_path} 書き込み完了",
    "Edit": "{file_path} 編集完了",
    "Bash": "コマンド完了",
    "default": "{tool_name} 完了"
  },
  "PostToolUseFailure": {
    "Bash": "コマンド失敗",
    "default": "{tool_name} 失敗"
  },
  "Stop": {
    "default": "タスク完了"
  },
  "Notification": {
    "permission_prompt": "権限の確認が必要です",
    "idle_prompt": "入力を待っています",
    "default": "{message}"
  },
  "SubagentStart": {
    "default": "サブタスク開始: {agent_type}"
  },
  "SubagentStop": {
    "default": "サブタスク完了"
  },
  "SessionStart": {
    "default": "セッション開始"
  },
  "PreCompact": {
    "default": "コンテキスト圧縮中"
  }
}
```

---

## 7. 开发计划

### Phase 1: MVP（目标 1-2 天）

- [ ] 项目脚手架搭建 (pyproject.toml, 目录结构)
- [ ] 配置文件加载 (config.py)
- [ ] Hook 脚本: 接收 stdin JSON 并解析事件
- [ ] TTS 引擎: 先实现 edge-tts 一个后端
- [ ] 简单 Daemon: asyncio 队列 + 异步播放
- [ ] 模板模式播报文案 (英文，作为默认语言)
- [ ] 安装脚本: 自动注入 hooks 到 settings.json
- [ ] CLI: `start`, `stop`, `test` 命令
- [ ] 基本 README (英文)

### Phase 2: 完善（目标 1 周）

- [ ] 支持所有 TTS 引擎 (say, espeak, openai)
- [ ] Verbosity 三级过滤
- [ ] 多语言模板 (zh, ja)
- [ ] 队列优化: 去重、汇总快速连续事件
- [ ] `config` CLI 命令
- [ ] 追加中文 README (README.zh.md)
- [ ] 单元测试
- [ ] PyPI 发布

### Phase 3: 增强（可选）

- [ ] LLM 模式播报
- [ ] Claude Code Plugin 格式打包 (参考 claude-hud 的 .claude-plugin)
- [ ] 自定义事件过滤规则
- [ ] Web UI 控制面板（查看事件流、调整设置）
- [ ] 音效模式（不用语音，用不同音效表示不同事件）

---

## 8. 参考资料

### 8.1 Claude Code 官方文档

| 文档 | URL | 重点内容 |
|---|---|---|
| Hooks 参考 | https://code.claude.com/docs/en/hooks | 所有 Hook 事件的 JSON 输入/输出 schema，matcher 用法 |
| Statusline 自定义 | https://code.claude.com/docs/en/statusline | stdin JSON 数据结构（session_id, transcript_path, model, cost, current_usage 等字段） |
| Claude Code SDK Hooks | https://platform.claude.com/docs/en/agent-sdk/hooks | SDK 层面的 Hooks API，TypeScript/Python 类型定义 |

### 8.2 参考项目（架构与实现参考）

| 项目 | URL | 参考价值 |
|---|---|---|
| claude-hud | https://github.com/jarrodwatts/claude-hud | **重点参考**: Plugin 架构 (.claude-plugin 目录)、statusline API 使用方式、transcript JSONL 解析 |
| ccstatusline | https://github.com/sirmalloc/ccstatusline | Widget 系统设计、JSON stdin 解析、多 widget 组合渲染 |
| claude-code-hooks-mastery | https://github.com/disler/claude-code-hooks-mastery | **重点参考**: 全部 12 个 Hook 事件的实际使用示例、TTS 通知集成（已有 Stop/Notification 事件的音频播报实现） |
| claude-code-hooks-notification | https://www.npmjs.com/package/@claude-code-hooks/notification | 跨平台通知实现 (macOS/Linux/Windows)、Hook stdin JSON 解析示例 |
| claude-dashboard | https://github.com/uppinote20/claude-dashboard | Plugin 安装流程参考 (`/plugin marketplace add` + `/plugin install`)、多主题/多语言配置系统 |
| claude-code-hooks-observability | https://github.com/disler/claude-code-hooks-multi-agent-observability | 全事件实时监控 UI、事件分类 emoji 系统、多 Agent 追踪 |

### 8.3 TTS 引擎文档

| 引擎 | URL | 备注 |
|---|---|---|
| edge-tts (Python) | https://github.com/rany2/edge-tts | 默认推荐引擎，免费、支持多语言多音色，async API |
| OpenAI TTS API | https://platform.openai.com/docs/guides/text-to-speech | 付费，音质最自然，`tts-1` / `tts-1-hd` 两个模型 |
| piper (本地 TTS) | https://github.com/rhasspy/piper | 高质量离线 TTS，支持多语言，适合无网环境 |
| macOS `say` 命令 | https://ss64.com/mac/say.html | 零依赖系统命令，`-v` 指定音色，`-r` 控制语速 |

### 8.4 社区教程与博客

| 标题 | URL | 内容 |
|---|---|---|
| Claude Code Hooks 完整指南 (12 事件) | https://claudefa.st/blog/tools/hooks/hooks-guide | 所有 Hook 事件的 JSON schema、三种 handler 类型 (command/prompt/agent)、结构化输出格式 |
| Claude Code Hooks 自动化实战 (DataCamp) | https://www.datacamp.com/tutorial/claude-code-hooks | 从零搭建 Hook 的完整教程，包括通知、自动格式化、测试自动化 |
| Claude Code Hooks macOS 通知 (Medium) | https://nakamasato.medium.com/claude-code-hooks-automating-macos-notifications-for-task-completion-42d200e751cc | Stop 事件 + transcript 解析 + osascript 通知的完整实现 |
| Statusline 自定义教程 (DEV) | https://dev.to/rajeshroyal/statusline-build-your-dream-status-bar-for-claude-code-50p5 | statusline 的各种玩法和自定义思路 |

---

## 9. 约束与注意事项

1. **不能阻塞 Claude Code**: Hook 脚本必须快速返回。TTS 播放必须异步进行。
2. **兼容性**: 需要支持 macOS 和 Linux。Windows 为低优先级。
3. **Claude Code 版本**: 目标兼容 v1.0.80+ (statusline/hooks API 稳定版)。
4. **隐私**: 不收集任何用户数据。播报内容纯本地处理（除非用户主动选择 OpenAI TTS 等云服务）。
5. **资源占用**: Daemon 进程应尽可能轻量，空闲时接近零 CPU 占用。
6. **国际化**: 默认语言为英文 (en)。所有用户可见的字符串（README、CLI 输出、错误信息、配置注释）以英文为主。多语言播报模板作为 i18n 支持提供。