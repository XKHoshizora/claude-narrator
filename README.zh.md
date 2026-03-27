# Claude Narrator

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
claude-narrator start          # 启动语音播报守护进程
claude-narrator stop           # 停止守护进程
claude-narrator restart        # 重启守护进程
claude-narrator status         # 查看运行状态
claude-narrator test "文本"    # 测试语音输出
claude-narrator install        # 安装 hooks 到 Claude Code
claude-narrator uninstall      # 移除 hooks
claude-narrator config get <键>       # 查看配置
claude-narrator config set <键> <值>  # 修改配置
claude-narrator config reset          # 恢复默认配置
claude-narrator cache clear           # 清除音频缓存
```

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
    "voice": "zh-CN-XiaoxiaoNeural"
  }
}
```

### Verbosity 等级

| 等级 | 播报内容 |
|------|---------|
| `minimal` | 任务完成、错误、权限请求 |
| `normal`（默认） | 以上 + 文件操作、子任务 |
| `verbose` | 所有事件 |

### 支持的 TTS 引擎

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

## 工作原理

```
Claude Code Hook 事件 → Hook 脚本（转发 JSON）→ Unix Socket → TTS Daemon → 语音播放
```

1. Claude Code 通过 Hooks 系统在每个操作前后触发事件
2. 轻量级 Hook 脚本将事件 JSON 转发给后台 Daemon（不阻塞 Claude Code）
3. Daemon 根据 verbosity 过滤事件、合并连续重复事件
4. 使用模板生成播报文案，通过 TTS 引擎合成语音并播放

## 环境要求

- Python 3.10+
- Claude Code v1.0.80+

## 许可证

MIT
