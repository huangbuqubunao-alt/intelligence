"""Offline regression coverage for the installed console entry point."""

from __future__ import annotations

import subprocess
import sys
from importlib.metadata import distribution
from pathlib import Path


def _help_output(command: list[str]) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    return result.stdout


def test_installed_console_entry_maps_to_existing_cli_help() -> None:
    entry_points = distribution("youtube-intel").entry_points
    console_entry = next(entry_point for entry_point in entry_points if entry_point.name == "youtube-intel")

    assert console_entry.value == "youtube_intel.cli:main"

    console_command = Path(sys.executable).with_name("youtube-intel")
    assert console_command.is_file()

    assert _help_output([str(console_command), "--help"]) == _help_output(
        [sys.executable, "-m", "youtube_intel", "--help"]
    )
