"""Regression tests for scripts/security_scan.sh.

These tests create isolated temporary fixtures and invoke the scanner to verify
fail-closed behaviour, redaction, and cross-platform pattern coverage.
"""

from __future__ import annotations

import subprocess
import tarfile
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

SCANNER = ["bash", "scripts/security_scan.sh"]


def _aws_secret_value() -> str:
    """AWS-like secret built from fragments so the literal never appears in source."""
    return "A" * 20 + "1234"


def _openai_key_value() -> str:
    """OpenAI-like key built from fragments so the literal never appears in source."""
    return "sk-" + "abc" * 8 + "123"


def _bearer_value() -> str:
    """Bearer-like token built from fragments so the literal never appears in source."""
    return "eyJ" + "a" * 10 + "In0"


def _pem_value() -> str:
    """PEM-like key built from fragments so the literal never appears in source."""
    begin = "-----BEGIN" + " RSA PRIVATE KEY-----"
    end = "-----END" + " RSA PRIVATE KEY-----"
    return begin + "\n" + "M" * 32 + "\n" + end


def _wheel_secret() -> str:
    """Wheel fixture secret built from fragments so the literal never appears in source."""
    return "rc-wheel-" + "A" * 20 + "1234"


def _sdist_secret() -> str:
    """Sdist fixture secret built from fragments so the literal never appears in source."""
    return "rc-sdist-" + "A" * 20 + "1234"


def _aws_payload() -> str:
    return "AWS_SECRET_ACCESS_KEY" + " = '" + _aws_secret_value() + "'"


def _api_key_payload() -> str:
    return "API_KEY" + ' = "' + _openai_key_value() + '"'


def _bearer_payload() -> str:
    return "Authorization" + ': "Bearer ' + _bearer_value() + '"'


def _pem_payload() -> str:
    return _pem_value()


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
    ("filename", "payload_factory", "rule"),
    (
        ("aws_secret.py", _aws_payload, "aws-credential"),
        ("api_key.py", _api_key_payload, "api-key"),
        ("bearer.py", _bearer_payload, "bearer-auth"),
        ("pem.pem", _pem_payload, "pem-private-key"),
    ),
    ids=("aws-single-quote", "api-key-double-quote", "bearer-token", "pem-key"),
)
def test_credential_positive_cases_are_detected_and_redacted(
    tmp_path: Path, filename: str, payload_factory: Callable[[], str], rule: str
) -> None:
    payload = payload_factory()
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
    secret = _wheel_secret()
    wheel_path = wheel_dir / "fake-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as archive:
        archive.writestr("fake/leaked.py", "API_KEY" + " = '" + secret + "'\n")
    _init_git_fixture(tmp_path)

    exit_code, stdout, stderr = _run_scanner(tmp_path)

    combined = stdout + stderr
    assert exit_code != 0
    assert "generic-credential" in combined
    assert secret not in combined


def test_sdist_with_fake_secret_is_detected_and_redacted(tmp_path: Path) -> None:
    sdist_dir = tmp_path / "dist"
    sdist_dir.mkdir()
    secret = _sdist_secret()
    sdist_path = sdist_dir / "fake-0.0.0.tar.gz"
    with tarfile.open(sdist_path, "w:gz") as archive:
        data = ("API_KEY" + " = '" + secret + "'\n").encode("utf-8")
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
        ("fake_key.py", "API_KEY = 'fake_key_value'"),
        ("key_tag.py", "API_KEY = '<key>'"),
        ("shell_false.py", "import subprocess\nsubprocess.run('ls', shell=False)\n"),
        ("revision.py", 'MODEL_REVISION = "a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb"\n'),
    ),
    ids=("replace-me", "your-key", "dummy", "example-placeholder", "fake-key-value", "key-tag", "shell-false", "model-revision"),
)
def test_negative_cases_do_not_block(tmp_path: Path, filename: str, payload: str) -> None:
    (tmp_path / filename).write_text(payload, encoding="utf-8")
    _init_git_fixture(tmp_path)

    exit_code, stdout, stderr = _run_scanner(tmp_path)

    assert exit_code == 0, f"unexpected block for {filename}: {stdout}{stderr}"


def _bypass_secret() -> str:
    """A value that contains 'placeholder' but is not an allowed sentinel."""
    return "actual" + "placeholder" + "credential123456"


def test_placeholder_substring_does_not_bypass_scanner(tmp_path: Path) -> None:
    """A value that merely contains 'placeholder' must not be whitelisted."""
    secret = _bypass_secret()
    (tmp_path / "bypass.py").write_text(
        "API_KEY" + ' = "' + secret + '"\n', encoding="utf-8"
    )
    _init_git_fixture(tmp_path)

    exit_code, stdout, stderr = _run_scanner(tmp_path)

    combined = stdout + stderr
    assert exit_code != 0
    assert "generic-credential" in combined
    assert secret not in combined
