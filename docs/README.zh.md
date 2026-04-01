# Claude Narrator

[English](../README.md) | **中文** | [日本語](README.ja.md)

> Claude Code 的 TTS 语音播报插件 —— 不看终端也能知道 AI 在做什么。

Claude Narrator 利用 Claude Code 的 Hooks 系统，实时用语音播报工作状态。文件读写、命令执行、任务完成、需要确认权限……统统用语音告诉你。

## 快速开始

### 方式一：pip 安装

```bash
pip install claude-narrator
claude-narrator install
claude-narrator start
```

### 方式二：Claude Code 插件

```
/plugin install claude-narrator
/claude-narrator:setup
```

## 测试语音

```bash
claude-narrator test "你好，Claude Narrator 已就绪"
```

## 常用命令

```bash
claude-narrator start [-f|--foreground] [--web]  # 启动守护进程（前台 / 带 Web UI）
claude-narrator stop                              # 停止守护进程
claude-narrator restart [-f|--foreground]          # 重启守护进程
claude-narrator reload                            # 热重载配置（不重启）
claude-narrator status                            # 查看运行状态
claude-narrator test "文本"                       # 测试语音输出
claude-narrator install                           # 安装 hooks 到 Claude Code
claude-narrator uninstall                         # 移除 hooks
claude-narrator config get <键>                   # 查看配置
claude-narrator config set <键> <值>              # 修改配置
claude-narrator config reset                      # 恢复默认配置
claude-narrator cache clear                       # 清除音频缓存
```

## 工作原理

```mermaid
flowchart LR
    CC[Claude Code] -->|Hook 事件| HS[Hook 脚本]
    HS -->|JSON via Unix Socket| D[TTS Daemon]
    D --> F[Verbosity 过滤]
    F --> C[事件合并]
    C --> N[播报文案生成<br/>模板 / LLM]
    N --> Q[优先级队列]
    Q --> TTS[TTS 引擎]
    TTS --> P[语音播放]
```

- **Hook 脚本**：输出 `{"async": true}` 让 Claude Code 立即继续，然后在后台转发事件到 Daemon。零阻塞。
- **Daemon**：基于 asyncio 的后台进程，处理所有逻辑。
- **工具注册表**：42 个工具注册了显示名、分类和结果解析器，提供差异化叙述。
- **事件合并**：0.5 秒窗口内相同工具的连续调用合并为一条（如 5 次 Read → "5 Read operations"）。
- **优先级队列**：高优先级（错误、通知）打断当前播放；低优先级（工具调用）队列满时丢弃。
- **音频缓存**：LRU 文件缓存集成到 TTS 路径——重复短语跳过网络请求。

## 配置

配置文件位于 `~/.claude-narrator/config.json`

```json
{
  "general": {
    "verbosity": "normal",
    "language": "zh",
    "enabled": true
  },
  "tts": {
    "engine": "edge-tts",
    "voice": "zh-CN-XiaoxiaoNeural",
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

### Verbosity 等级

| 等级 | 播报内容 |
|------|---------|
| `minimal` | 任务完成、错误、权限请求/拒绝、停止失败 |
| `normal`（默认） | 以上 + 文件操作、子任务、会话开始/结束、上下文压缩、任务生命周期 |
| `verbose` | 所有事件（含工作树操作、目录切换、文件监听）|

### 支持的 Hook 事件（20/27）

| 事件 | 等级 | 说明 |
|------|------|------|
| `PreToolUse` | normal（文件操作） | 工具执行前（通过 Tool Registry 支持 40+ 工具的差异化叙述） |
| `PostToolUse` | normal（文件操作） | 工具完成后（Bash/Grep/Glob/Read/WebSearch 含结果摘要） |
| `PostToolUseFailure` | minimal | 工具执行失败 |
| `Stop` | minimal | 任务完成 |
| `StopFailure` | minimal | 任务执行失败 |
| `Notification` | minimal | 需要用户注意（7 种通知类型：等待输入、权限确认、计算机使用模式等） |
| `PermissionRequest` | minimal | 权限请求等待 |
| `PermissionDenied` | minimal | 权限被拒绝 |
| `SubagentStart` | normal | 子代理启动 |
| `SubagentStop` | normal | 子代理完成 |
| `SessionStart` | normal | 会话开始（区分 startup/resume/clear/compact） |
| `SessionEnd` | normal | 会话结束 |
| `PreCompact` | verbose | 上下文压缩开始 |
| `PostCompact` | normal | 上下文压缩完成 |
| `TaskCreated` | normal | 团队任务创建 |
| `TaskCompleted` | normal | 团队任务完成 |
| `WorktreeCreate` | verbose | Git 工作树创建 |
| `WorktreeRemove` | verbose | Git 工作树移除 |
| `CwdChanged` | verbose | 工作目录切换 |
| `FileChanged` | verbose | 监听文件变更 |

### TTS 引擎

| 引擎 | 平台 | 说明 |
|------|------|------|
| `edge-tts`（默认） | 全平台 | 免费、音质好、需联网 |
| `say` | macOS | 系统自带、零依赖 |
| `espeak` | Linux | 离线可用 |
| `openai` | 全平台 | 音质最佳、需 API Key |

### 支持的语言

| 语言 | 代码 | 默认音色 |
|------|------|---------|
| English | `en` | en-US-AriaNeural |
| 中文 | `zh` | zh-CN-XiaoxiaoNeural |
| 日本語 | `ja` | ja-JP-NanamiNeural |

### 播报风格 (Personality)

设置播报风格：

```bash
claude-narrator config set narration.personality tengu
claude-narrator reload
```

| 风格 | 特点 | 示例 |
|------|------|------|
| `concise`（默认） | 简短直接 | "正在读取 app.py" |
| `tengu` | 趣味 + spinner 前缀 | "Cogitating... 潜入 app.py" |
| `professional` | 正式详细 | "正在读取源文件 app.py" |
| `casual` | 口语化 | "看看 app.py" |

多风格组合：

```bash
claude-narrator config set narration.personality '["tengu", "professional"]'
```

### 播报模式

- **模板模式**（默认）：快速、确定性。使用 i18n JSON 模板生成简短播报，如「正在读取 src/app.py」。
- **LLM 模式**：通过 Ollama（本地）、OpenAI 或 Anthropic 生成自然语言播报。超过 3 秒自动回退到模板。

```bash
claude-narrator config set narration.mode llm
claude-narrator config set narration.llm.provider ollama
claude-narrator config set narration.llm.model qwen2.5:3b
claude-narrator reload  # 无需重启即可生效
```

### 自定义过滤规则

按工具名、文件路径或自定义规则过滤事件：

```json
{
  "filters": {
    "ignore_tools": ["Read"],
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

### 音效模式

在语音播报之外（或替代语音）播放短音效：

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

实时仪表盘，显示守护进程状态和事件流：

```bash
claude-narrator config set web.enabled true
claude-narrator restart
# 打开 http://127.0.0.1:19822
```

### 上下文监控

Token 使用量达到阈值时语音提醒：

```bash
claude-narrator config set context_monitor.enabled true
claude-narrator reload
```

> **警告**：此功能占用 Claude Code 的 statusline 插槽。如果同时使用 claude-hud 等插件，会产生冲突。

## 环境要求

- Python 3.10+
- Claude Code v1.0.80+

## 许可证

MIT
