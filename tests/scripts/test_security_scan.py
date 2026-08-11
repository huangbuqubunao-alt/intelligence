"""Regression tests for scripts/security_scan.sh.

These tests create isolated temporary fixtures and invoke the scanner to verify
fail-closed behaviour, redaction, and cross-platform pattern coverage.
"""

from __future__ import annotations

import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

SCANNER = ["bash", "scripts/security_scan.sh"]


def _init_git_fixture(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "probe@example.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Probe"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)


def _run_scanner(cwd: Path) -> tuple[int, str, str]:
    result = subprocess.run(
        SCANNER + [str(cwd)],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


@pytest.mark.parametrize(
    ("filename", "payload", "rule"),
    (
        ("aws_secret.py", "AWS_SECRET_ACCESS_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCY12345678'", "aws-credential"),
        ("api_key.py", 'API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"', "generic-credential"),
        ("bearer.py", 'Authorization: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"', "bearer-auth"),
        ("pem.pem", "-----BEGIN RSA PRIVATE KEY-----\nMIIEpQIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MhgwKVPSmwaFkYLv\n-----END RSA PRIVATE KEY-----", "pem-private-key"),
    ),
    ids=("aws-single-quote", "api-key-double-quote", "bearer-token", "pem-key"),
)
def test_credential_positive_cases_are_detected_and_redacted(
    tmp_path: Path, filename: str, payload: str, rule: str
) -> None:
    (tmp_path / filename).write_text(payload, encoding="utf-8")
    _init_git_fixture(tmp_path)

    exit_code, stdout, stderr = _run_scanner(tmp_path)

    combined = stdout + stderr
    assert exit_code != 0, f"expected failure for {rule}"
    assert rule in combined
    assert "fingerprint=" in combined
    assert payload not in combined


def test_multiline_subprocess_shell_true_is_detected(tmp_path: Path) -> None:
    (tmp_path / "subprocess_call.py").write_text(
        "import subprocess\n\n"
        "subprocess.run(\n"
        "    command,\n"
        "    shell=True,\n"
        ")\n",
        encoding="utf-8",
    )
    _init_git_fixture(tmp_path)

    exit_code, stdout, stderr = _run_scanner(tmp_path)

    combined = stdout + stderr
    assert exit_code != 0
    assert "subprocess-shell-true" in combined
    assert "shell=True" not in combined


def test_wheel_with_fake_secret_is_detected_and_redacted(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "dist"
    wheel_dir.mkdir()
    secret = "rc-wheel-ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"
    wheel_path = wheel_dir / "fake-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as archive:
        archive.writestr("fake/leaked.py", f"API_KEY = '{secret}'\n")
    _init_git_fixture(tmp_path)

    exit_code, stdout, stderr = _run_scanner(tmp_path)

    combined = stdout + stderr
    assert exit_code != 0
    assert "generic-credential" in combined
    assert secret not in combined


def test_sdist_with_fake_secret_is_detected_and_redacted(tmp_path: Path) -> None:
    sdist_dir = tmp_path / "dist"
    sdist_dir.mkdir()
    secret = "rc-sdist-ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"
    sdist_path = sdist_dir / "fake-0.0.0.tar.gz"
    with tarfile.open(sdist_path, "w:gz") as archive:
        data = f"API_KEY = '{secret}'\n".encode("utf-8")
        info = tarfile.TarInfo(name="fake/leaked.py")
        info.size = len(data)
        archive.addfile(info, fileobj=__import__("io").BytesIO(data))
    _init_git_fixture(tmp_path)

    exit_code, stdout, stderr = _run_scanner(tmp_path)

    combined = stdout + stderr
    assert exit_code != 0
    assert "generic-credential" in combined
    assert secret not in combined


def test_corrupt_wheel_extract_fails_closed(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "corrupt-0.0.0-py3-none-any.whl").write_text("not a zip", encoding="utf-8")
    _init_git_fixture(tmp_path)

    exit_code, _stdout, stderr = _run_scanner(tmp_path)

    assert exit_code != 0
    assert "wheel-extract-failure" in stderr


def test_invalid_python_syntax_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("def broken(\n", encoding="utf-8")
    _init_git_fixture(tmp_path)

    exit_code, _stdout, stderr = _run_scanner(tmp_path)

    assert exit_code != 0
    assert "ast-parse-failure" in stderr


@pytest.mark.parametrize(
    ("filename", "payload"),
    (
        ("replace_me.py", "API_KEY = 'REPLACE_ME'"),
        ("your_key.py", "SECRET_KEY = \"YOUR_KEY\""),
        ("dummy.py", "ACCESS_TOKEN = 'dummy'"),
        ("example.py", "CLIENT_SECRET = 'example_placeholder'"),
        ("shell_false.py", "import subprocess\nsubprocess.run('ls', shell=False)\n"),
        ("revision.py", 'MODEL_REVISION = "a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb"\n'),
    ),
    ids=("replace-me", "your-key", "dummy", "example-placeholder", "shell-false", "model-revision"),
)
def test_negative_cases_do_not_block(tmp_path: Path, filename: str, payload: str) -> None:
    (tmp_path / filename).write_text(payload, encoding="utf-8")
    _init_git_fixture(tmp_path)

    exit_code, stdout, stderr = _run_scanner(tmp_path)

    assert exit_code == 0, f"unexpected block for {filename}: {stdout}{stderr}"
