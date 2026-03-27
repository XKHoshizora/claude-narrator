---
description: Configure Claude Narrator settings interactively
allowed-tools: Bash, AskUserQuestion
---

# Configure Claude Narrator

Help the user change their Claude Narrator settings interactively.

## Step 1: Show current config

```bash
claude-narrator status
```

## Step 2: What to change?

Use AskUserQuestion to ask what the user wants to configure:
- Verbosity level (minimal/normal/verbose)
- TTS engine
- Language
- Enable/disable narrator

## Step 3: Apply changes

Based on the user's choice, run the appropriate `claude-narrator config set` command.

Examples:
```bash
claude-narrator config set general.verbosity verbose
claude-narrator config set tts.engine say
claude-narrator config set general.language zh
claude-narrator config set general.enabled false
```

## Step 4: Restart daemon

After changing config:
```bash
claude-narrator restart
```

Confirm the changes are applied by running `claude-narrator status` again.
