"""Skill management commands.

Commands for managing Codex/Claude skill integration.
"""

import contextlib
import os
import re
from importlib import resources
from pathlib import Path

import click

from .helpers import console

SKILL_NAME = "notebooklm"
TARGET_CHOICES = click.Choice(["codex", "claude"], case_sensitive=False)
TARGET_HELP = "Skill target platform."


def get_skill_source_content() -> str | None:
    """Read the skill source file from package data."""
    try:
        # Python 3.9+ way to read package data (use / operator for path traversal)
        return (resources.files("notebooklm") / "data" / "SKILL.md").read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError):
        return None


def get_package_version() -> str:
    """Get the current package version."""
    try:
        from .. import __version__

        return __version__
    except ImportError:
        return "unknown"


def get_skill_version(skill_path: Path) -> str | None:
    """Extract version from skill file header comment."""
    if not skill_path.exists():
        return None

    with open(skill_path, encoding="utf-8") as f:
        content = f.read(500)  # Read first 500 chars

    match = re.search(r"notebooklm-py v([\d.]+)", content)
    return match.group(1) if match else None


def resolve_skill_destination(target: str) -> tuple[Path, Path]:
    """Resolve destination directory and file for a target platform."""
    target = target.lower()
    if target == "codex":
        codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
        skill_dir = codex_home / "skills" / SKILL_NAME
    elif target == "claude":
        skill_dir = Path.home() / ".claude" / "skills" / SKILL_NAME
    else:
        raise ValueError(f"Unknown target: {target}")

    return skill_dir, skill_dir / "SKILL.md"


@click.group()
def skill():
    """Manage Codex/Claude skill integration."""
    pass


@skill.command()
@click.option(
    "--target",
    type=TARGET_CHOICES,
    default="codex",
    show_default=True,
    help=TARGET_HELP,
)
def install(target: str):
    """Install or update the NotebookLM skill for Codex or Claude Code.

    Copies the skill file to the selected target skill directory
    and embeds the current package version for tracking.
    """
    target = target.lower()
    skill_dest_dir, skill_dest = resolve_skill_destination(target)

    # Read skill content from package data
    content = get_skill_source_content()
    if content is None:
        console.print("[red]Error:[/red] Skill source not found in package data.")
        console.print("This may indicate an incomplete or corrupted installation.")
        console.print("Try reinstalling: pip install --force-reinstall notebooklm-py")
        raise SystemExit(1)

    # Create destination directory
    skill_dest_dir.mkdir(parents=True, exist_ok=True)

    # Embed version in skill file (after frontmatter)
    version = get_package_version()
    version_comment = f"<!-- notebooklm-py v{version} -->\n"

    # Insert after the closing --- of frontmatter
    if "---" in content:
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = f"---{parts[1]}---\n{version_comment}{parts[2]}"
        else:
            content = version_comment + content
    else:
        content = version_comment + content

    # Write to destination
    with open(skill_dest, "w", encoding="utf-8") as f:
        f.write(content)

    console.print(f"[green]Installed[/green] NotebookLM skill to {skill_dest}")
    console.print(f"  Target: {target}")
    console.print(f"  Version: {version}")
    console.print("")
    if target == "codex":
        console.print("Codex will now recognize NotebookLM commands.")
        console.print("Try: [cyan]/notebooklm[/cyan] or ask Codex to 'create a podcast about X'")
    else:
        console.print("Claude Code will now recognize NotebookLM commands.")
        console.print("Try: [cyan]/notebooklm[/cyan] or ask Claude to 'create a podcast about X'")


@skill.command()
@click.option(
    "--target",
    type=TARGET_CHOICES,
    default="codex",
    show_default=True,
    help=TARGET_HELP,
)
def status(target: str):
    """Check if the skill is installed and show version info."""
    target = target.lower()
    _, skill_dest = resolve_skill_destination(target)

    cli_version = get_package_version()
    skill_version = get_skill_version(skill_dest)

    if not skill_dest.exists():
        console.print("[yellow]Not installed[/yellow]")
        console.print(f"  Target: {target}")
        console.print(f"  Path: {skill_dest}")
        console.print(f"  CLI version: {cli_version}")
        console.print("")
        console.print(f"Run [cyan]notebooklm skill install --target {target}[/cyan] to install.")
        return

    console.print(f"[green]Installed[/green] at {skill_dest}")
    console.print(f"  Target: {target}")
    console.print(f"  Skill version: {skill_version or 'unknown'}")
    console.print(f"  CLI version:   {cli_version}")

    if skill_version and skill_version != cli_version:
        console.print("")
        console.print(
            f"[yellow]Version mismatch![/yellow] Run "
            f"[cyan]notebooklm skill install --target {target}[/cyan] to update."
        )


@skill.command()
@click.option(
    "--target",
    type=TARGET_CHOICES,
    default="codex",
    show_default=True,
    help=TARGET_HELP,
)
def uninstall(target: str):
    """Remove the NotebookLM skill from Codex or Claude Code."""
    target = target.lower()
    skill_dest_dir, skill_dest = resolve_skill_destination(target)

    if not skill_dest.exists():
        console.print("[yellow]Skill not installed[/yellow]")
        return

    # Remove the skill file
    skill_dest.unlink()

    # Remove the directory if empty
    with contextlib.suppress(OSError):
        skill_dest_dir.rmdir()

    console.print(f"[green]Uninstalled[/green] NotebookLM skill (target: {target})")
    if target == "codex":
        console.print("Codex will no longer recognize NotebookLM commands.")
    else:
        console.print("Claude Code will no longer recognize NotebookLM commands.")


@skill.command()
@click.option(
    "--target",
    type=TARGET_CHOICES,
    default="codex",
    show_default=True,
    help=TARGET_HELP,
)
def show(target: str):
    """Display the skill file content."""
    target = target.lower()
    _, skill_dest = resolve_skill_destination(target)

    if not skill_dest.exists():
        console.print("[yellow]Skill not installed[/yellow]")
        console.print(f"Run [cyan]notebooklm skill install --target {target}[/cyan] first.")
        return

    with open(skill_dest, encoding="utf-8") as f:
        content = f.read()

    console.print(content)
