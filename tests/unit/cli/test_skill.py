"""Tests for skill CLI commands."""

import os
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from notebooklm.notebooklm_cli import cli

from .conftest import get_cli_module

# Get the actual skill module (not the click group that shadows it)
skill_module = get_cli_module("skill")


@pytest.fixture
def runner():
    return CliRunner()


class TestResolveSkillDestination:
    """Tests for target destination resolution."""

    def test_resolve_codex_uses_codex_home(self, tmp_path):
        with patch.dict(os.environ, {"CODEX_HOME": str(tmp_path / "custom-codex")}, clear=False):
            skill_dir, skill_file = skill_module.resolve_skill_destination("codex")

        assert skill_dir == tmp_path / "custom-codex" / "skills" / "notebooklm"
        assert skill_file == skill_dir / "SKILL.md"

    def test_resolve_codex_falls_back_to_home_dot_codex(self, tmp_path):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("notebooklm.cli.skill.Path.home", return_value=tmp_path),
        ):
            skill_dir, skill_file = skill_module.resolve_skill_destination("codex")

        assert skill_dir == tmp_path / ".codex" / "skills" / "notebooklm"
        assert skill_file == skill_dir / "SKILL.md"

    def test_resolve_claude_uses_home_dot_claude(self, tmp_path):
        with patch("notebooklm.cli.skill.Path.home", return_value=tmp_path):
            skill_dir, skill_file = skill_module.resolve_skill_destination("claude")

        assert skill_dir == tmp_path / ".claude" / "skills" / "notebooklm"
        assert skill_file == skill_dir / "SKILL.md"


class TestSkillInstall:
    """Tests for skill install command."""

    def test_skill_install_defaults_to_codex_target(self, runner, tmp_path):
        """Test that install uses codex target by default."""
        skill_dest = tmp_path / "skills" / "notebooklm" / "SKILL.md"
        mock_source_content = "---\nname: notebooklm\n---\n# Test"

        with (
            patch.object(
                skill_module,
                "resolve_skill_destination",
                return_value=(skill_dest.parent, skill_dest),
            ) as mock_resolve,
            patch.object(skill_module, "get_skill_source_content", return_value=mock_source_content),
        ):
            result = runner.invoke(cli, ["skill", "install"])

        assert result.exit_code == 0
        assert "installed" in result.output.lower()
        assert "target: codex" in result.output.lower()
        assert skill_dest.exists()
        mock_resolve.assert_called_once_with("codex")

    def test_skill_install_claude_target(self, runner, tmp_path):
        """Test that install supports claude target."""
        skill_dest = tmp_path / "skills" / "notebooklm" / "SKILL.md"
        mock_source_content = "---\nname: notebooklm\n---\n# Test"

        with (
            patch.object(
                skill_module,
                "resolve_skill_destination",
                return_value=(skill_dest.parent, skill_dest),
            ) as mock_resolve,
            patch.object(skill_module, "get_skill_source_content", return_value=mock_source_content),
        ):
            result = runner.invoke(cli, ["skill", "install", "--target", "claude"])

        assert result.exit_code == 0
        assert "installed" in result.output.lower()
        assert "target: claude" in result.output.lower()
        assert skill_dest.exists()
        mock_resolve.assert_called_once_with("claude")

    def test_skill_install_source_not_found(self, runner, tmp_path):
        """Test error when source file doesn't exist."""
        skill_dest = tmp_path / "skills" / "notebooklm" / "SKILL.md"

        with (
            patch.object(
                skill_module,
                "resolve_skill_destination",
                return_value=(skill_dest.parent, skill_dest),
            ),
            patch.object(skill_module, "get_skill_source_content", return_value=None),
        ):
            result = runner.invoke(cli, ["skill", "install"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()


class TestSkillStatus:
    """Tests for skill status command."""

    def test_skill_status_not_installed_codex(self, runner, tmp_path):
        """Test status when codex target is not installed."""
        skill_dest = tmp_path / "skills" / "notebooklm" / "SKILL.md"

        with patch.object(
            skill_module, "resolve_skill_destination", return_value=(skill_dest.parent, skill_dest)
        ):
            result = runner.invoke(cli, ["skill", "status"])

        assert result.exit_code == 0
        assert "not installed" in result.output.lower()
        assert "target: codex" in result.output.lower()

    def test_skill_status_installed_claude(self, runner, tmp_path):
        """Test status when claude target is installed."""
        skill_dest = tmp_path / "skills" / "notebooklm" / "SKILL.md"
        skill_dest.parent.mkdir(parents=True)
        skill_dest.write_text("<!-- notebooklm-py v0.1.0 -->\n# Test")

        with patch.object(
            skill_module, "resolve_skill_destination", return_value=(skill_dest.parent, skill_dest)
        ):
            result = runner.invoke(cli, ["skill", "status", "--target", "claude"])

        assert result.exit_code == 0
        assert "installed" in result.output.lower()
        assert "target: claude" in result.output.lower()


class TestSkillUninstall:
    """Tests for skill uninstall command."""

    def test_skill_uninstall_removes_codex_file(self, runner, tmp_path):
        """Test that uninstall removes the codex skill file."""
        skill_dest = tmp_path / "skills" / "notebooklm" / "SKILL.md"
        skill_dest.parent.mkdir(parents=True)
        skill_dest.write_text("# Test")

        with patch.object(
            skill_module, "resolve_skill_destination", return_value=(skill_dest.parent, skill_dest)
        ):
            result = runner.invoke(cli, ["skill", "uninstall"])

        assert result.exit_code == 0
        assert not skill_dest.exists()
        assert "target: codex" in result.output.lower()

    def test_skill_uninstall_not_installed_claude(self, runner, tmp_path):
        """Test uninstall for claude target when skill doesn't exist."""
        skill_dest = tmp_path / "skills" / "notebooklm" / "SKILL.md"

        with patch.object(
            skill_module, "resolve_skill_destination", return_value=(skill_dest.parent, skill_dest)
        ):
            result = runner.invoke(cli, ["skill", "uninstall", "--target", "claude"])

        assert result.exit_code == 0
        assert "not installed" in result.output.lower()


class TestSkillShow:
    """Tests for skill show command."""

    def test_skill_show_displays_codex_content(self, runner, tmp_path):
        """Test that show displays codex skill content."""
        skill_dest = tmp_path / "skills" / "notebooklm" / "SKILL.md"
        skill_dest.parent.mkdir(parents=True)
        skill_dest.write_text("# NotebookLM Skill\nTest content")

        with patch.object(
            skill_module, "resolve_skill_destination", return_value=(skill_dest.parent, skill_dest)
        ):
            result = runner.invoke(cli, ["skill", "show"])

        assert result.exit_code == 0
        assert "NotebookLM Skill" in result.output

    def test_skill_show_not_installed_claude(self, runner, tmp_path):
        """Test show for claude target when skill doesn't exist."""
        skill_dest = tmp_path / "skills" / "notebooklm" / "SKILL.md"

        with patch.object(
            skill_module, "resolve_skill_destination", return_value=(skill_dest.parent, skill_dest)
        ):
            result = runner.invoke(cli, ["skill", "show", "--target", "claude"])

        assert result.exit_code == 0
        assert "not installed" in result.output.lower()

    def test_skill_invalid_target_rejected(self, runner):
        """Test invalid --target is rejected by click."""
        result = runner.invoke(cli, ["skill", "install", "--target", "invalid"])
        assert result.exit_code == 2


class TestSkillVersionExtraction:
    """Tests for version extraction logic."""

    def test_get_skill_version_extracts_version(self, tmp_path):
        """Test version extraction from skill file."""
        from notebooklm.cli.skill import get_skill_version

        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nname: test\n---\n<!-- notebooklm-py v1.2.3 -->\n# Test")

        version = get_skill_version(skill_file)
        assert version == "1.2.3"

    def test_get_skill_version_no_version(self, tmp_path):
        """Test version extraction when no version present."""
        from notebooklm.cli.skill import get_skill_version

        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("# Test\nNo version here")

        version = get_skill_version(skill_file)
        assert version is None

    def test_get_skill_version_file_not_exists(self, tmp_path):
        """Test version extraction when file doesn't exist."""
        from notebooklm.cli.skill import get_skill_version

        skill_file = tmp_path / "nonexistent.md"
        version = get_skill_version(skill_file)
        assert version is None
