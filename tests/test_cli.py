from click.testing import CliRunner

import pytest

from claude_narrator.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestCLI:
    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Usage" in result.output

    def test_test_command_exists(self, runner):
        result = runner.invoke(main, ["test", "--help"])
        assert result.exit_code == 0

    def test_start_command_exists(self, runner):
        result = runner.invoke(main, ["start", "--help"])
        assert result.exit_code == 0

    def test_stop_command_exists(self, runner):
        result = runner.invoke(main, ["stop", "--help"])
        assert result.exit_code == 0

    def test_install_command_exists(self, runner):
        result = runner.invoke(main, ["install", "--help"])
        assert result.exit_code == 0

    def test_uninstall_command_exists(self, runner):
        result = runner.invoke(main, ["uninstall", "--help"])
        assert result.exit_code == 0

    def test_status_command(self, runner):
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Status:" in result.output

    def test_restart_command_exists(self, runner):
        result = runner.invoke(main, ["restart", "--help"])
        assert result.exit_code == 0

    def test_config_get_help(self, runner):
        result = runner.invoke(main, ["config", "get", "--help"])
        assert result.exit_code == 0

    def test_config_set_help(self, runner):
        result = runner.invoke(main, ["config", "set", "--help"])
        assert result.exit_code == 0

    def test_config_reset_help(self, runner):
        result = runner.invoke(main, ["config", "reset", "--help"])
        assert result.exit_code == 0

    def test_cache_clear_help(self, runner):
        result = runner.invoke(main, ["cache", "clear", "--help"])
        assert result.exit_code == 0

    def test_reload_command_not_running(self, runner):
        result = runner.invoke(main, ["reload"])
        assert result.exit_code == 0
        assert "not running" in result.output.lower()
