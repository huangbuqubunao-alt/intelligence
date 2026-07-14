import subprocess
import sys


def test_module_help_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "youtube_intel", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "usage: youtube-intel" in result.stdout
