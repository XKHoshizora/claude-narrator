import json
import sys

import pytest

from claude_narrator.installer import install_hooks, uninstall_hooks, _get_python_path


class TestInstallHooks:
    def test_install_creates_hooks_in_settings(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"
        settings_file.write_text("{}")

        install_hooks(claude_dir=tmp_claude_dir)

        settings = json.loads(settings_file.read_text())
        assert "hooks" in settings
        assert "PreToolUse" in settings["hooks"]
        assert "Stop" in settings["hooks"]
        assert "Notification" in settings["hooks"]

    def test_install_preserves_existing_settings(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"theme": "dark"}))

        install_hooks(claude_dir=tmp_claude_dir)

        settings = json.loads(settings_file.read_text())
        assert settings["theme"] == "dark"
        assert "hooks" in settings

    def test_install_preserves_existing_hooks(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"
        existing = {
            "hooks": {
                "PreToolUse": [{"matcher": "Write", "hooks": [{"type": "command", "command": "echo hi"}]}]
            }
        }
        settings_file.write_text(json.dumps(existing))

        install_hooks(claude_dir=tmp_claude_dir)

        settings = json.loads(settings_file.read_text())
        # Should have both existing and narrator hooks for PreToolUse
        pre_hooks = settings["hooks"]["PreToolUse"]
        assert len(pre_hooks) >= 2

    def test_install_creates_settings_if_missing(self, tmp_claude_dir):
        install_hooks(claude_dir=tmp_claude_dir)
        settings_file = tmp_claude_dir / "settings.json"
        assert settings_file.exists()

    def test_install_registers_new_tier1_events(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"
        settings_file.write_text("{}")
        install_hooks(claude_dir=tmp_claude_dir)
        settings = json.loads(settings_file.read_text())
        hooks = settings["hooks"]
        for event in ["StopFailure", "PostCompact", "SessionEnd", "TaskCreated",
                       "TaskCompleted", "PermissionDenied", "PermissionRequest"]:
            assert event in hooks, f"Missing Tier 1 event: {event}"

    def test_install_registers_new_tier2_events(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"
        settings_file.write_text("{}")
        install_hooks(claude_dir=tmp_claude_dir)
        settings = json.loads(settings_file.read_text())
        hooks = settings["hooks"]
        for event in ["WorktreeCreate", "WorktreeRemove", "CwdChanged", "FileChanged"]:
            assert event in hooks, f"Missing Tier 2 event: {event}"

    def test_uninstall_removes_new_events(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"
        settings_file.write_text("{}")
        install_hooks(claude_dir=tmp_claude_dir)
        uninstall_hooks(claude_dir=tmp_claude_dir)
        settings = json.loads(settings_file.read_text())
        hooks = settings.get("hooks", {})
        for event in ["StopFailure", "PostCompact", "SessionEnd", "TaskCreated",
                       "TaskCompleted", "WorktreeCreate", "FileChanged"]:
            assert event not in hooks, f"Event {event} not cleaned up"


class TestUninstallHooks:
    def test_uninstall_removes_narrator_hooks(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"

        install_hooks(claude_dir=tmp_claude_dir)
        uninstall_hooks(claude_dir=tmp_claude_dir)

        settings = json.loads(settings_file.read_text())
        hooks = settings.get("hooks", {})
        for event_hooks in hooks.values():
            for hook_group in event_hooks:
                for h in hook_group.get("hooks", []):
                    assert "claude_narrator" not in h.get("command", "")


class TestGetPythonPath:
    def test_returns_current_python(self):
        path = _get_python_path()
        assert sys.executable in path or "python" in path


from claude_narrator.installer import install_statusline, uninstall_statusline


class TestStatuslineInstall:
    def test_install_adds_statusline(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"
        settings_file.write_text("{}")
        install_statusline(claude_dir=tmp_claude_dir)
        settings = json.loads(settings_file.read_text())
        assert "statusLine" in settings
        assert "context_monitor" in settings["statusLine"]["command"]

    def test_uninstall_removes_ours(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"
        settings_file.write_text("{}")
        install_statusline(claude_dir=tmp_claude_dir)
        uninstall_statusline(claude_dir=tmp_claude_dir)
        settings = json.loads(settings_file.read_text())
        assert "statusLine" not in settings

    def test_uninstall_preserves_foreign(self, tmp_claude_dir):
        settings_file = tmp_claude_dir / "settings.json"
        settings_file.write_text(json.dumps({
            "statusLine": {"type": "command", "command": "claude-hud"}
        }))
        uninstall_statusline(claude_dir=tmp_claude_dir)
        settings = json.loads(settings_file.read_text())
        assert "statusLine" in settings  # Not ours, preserved
