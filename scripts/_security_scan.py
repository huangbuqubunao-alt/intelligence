"""Layered security and leak scanner for Release Candidate validation.

This scanner is intentionally written in standard-library Python so that regex
and AST behaviour is identical on macOS and Linux. The bash wrapper
scripts/security_scan.sh invokes it.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Final

_TRACKED_EXTENSIONS: Final = frozenset(
    {
        ".py",
        ".sh",
        ".toml",
        ".yaml",
        ".yml",
        ".json",
        ".md",
        ".txt",
        ".cfg",
        ".ini",
        ".pem",
    }
)

_ARTIFACT_TEXT_EXTENSIONS: Final = frozenset({".py", ".txt", ".cfg", ".toml", ".ini"})

_SUBPROCESS_NAMES: Final = frozenset({"run", "Popen", "call", "check_call", "check_output"})

_CREDENTIAL_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    (
        "api-key",
        re.compile(
            r"\b(?:"
            r"sk-[a-zA-Z0-9_-]{20,}"
            r"|sk-proj-[a-zA-Z0-9_-]{20,}"
            r"|AIza[a-zA-Z0-9_-]{35,}"
            r"|AKIA[0-9A-Z]{16}"
            r"|ghp_[a-zA-Z0-9]{36}"
            r"|ghs_[a-zA-Z0-9]{36}"
            r"|xox[baprs]-[0-9a-zA-Z_-]{10,}"
            r"|SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}"
            r")\b"
        ),
    ),
    (
        "bearer-auth",
        re.compile(
            "(?i)(?:Authorization|Bearer)\\s*[:=]\\s*['\"](?:Bearer\\s+)?[A-Za-z0-9._-]{8,}['\"]"
        ),
    ),
    (
        "pem-private-key",
        re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+|DSA\s+|OPENSSH\s+|)PRIVATE\s+KEY-----"),
    ),
    (
        "aws-credential",
        re.compile(
            "(?i)(?:AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|AWS_SESSION_TOKEN)\\s*="
            "\\s*['\"][A-Za-z0-9/+=]{16,}['\"]"
        ),
    ),
    (
        "generic-credential",
        re.compile(
            "(?i)(?:api[_-]?key|secret[_-]?key|password|access[_-]?token|private[_-]?key"
            "|client[_-]?secret|authorization)\\s*=\\s*['\"][^\"'$]{6,}['\"]"
        ),
    ),
    (
        "url-with-credentials",
        re.compile(r"https?://[^\"'/\s]+:[^\"'/\s]+@"),
    ),
)

_PLACEHOLDER_RE: Final = re.compile(
    r"(?i)(?:test_fixture|placeholder|example|fake[_-]?key|dummy|YOUR_KEY|<key>|REPLACE_ME|probe)"
)

# Best-effort entropy heuristic: base64-ish strings of length >= 32.
_ENTROPY_RE: Final = re.compile(r"[A-Za-z0-9+/]{32,}={0,2}")

# Safe contexts where high-entropy strings are expected.
_ENTROPY_EXCLUDE_RE: Final = re.compile(
    r"(?i)(?:"
    r"checksum|content_hash|SHA-256|sha256|GLOB|NOT\s+GLOB"
    r"|[0-9a-f]{64}"
    r"|base64|import|docstring|annotation"
    r"|test_fixture|placeholder|example|REPLACE_ME|YOUR_KEY"
    r")"
)

_PRINT_RE: Final = re.compile(r"(?:^|[^a-zA-Z0-9_])print\s*\(")

_IGNORED_PRINT_FILES: Final = frozenset({"cloud_llm.py", "public_subtitle_smoke.py"})

_GITIGNORE_PATTERNS: Final = frozenset(
    {
        ".venv/",
        "dist/",
        "build/",
        "__pycache__/",
        "/data/",
        "*.env",
        "*.key",
        "*.pem",
    }
)


class ScannerFailure(Exception):
    """A required scanning step could not complete."""


class Finding:
    """One redacted scanner finding."""

    __slots__ = ("rule", "path", "line", "fingerprint", "root")

    def __init__(self, rule: str, path: Path, line: int, text: str, root: Path) -> None:
        self.rule = rule
        self.path = path
        self.line = line
        self.fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        self.root = root

    def __str__(self) -> str:
        rel = self._relative_path()
        return f"rule={self.rule} path={rel} line={self.line} fingerprint={self.fingerprint}"

    def _relative_path(self) -> str:
        try:
            return str(self.path.relative_to(self.root))
        except ValueError:
            return str(self.path.name)


def _run_git_ls_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        text=False,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ScannerFailure(f"git ls-files failed: {stderr}")
    raw_paths = [p for p in result.stdout.split(b"\0") if p]
    if not raw_paths:
        raise ScannerFailure("git tracked file enumeration returned no files")
    tracked: list[Path] = []
    for raw in raw_paths:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise ScannerFailure(f"git ls-files returned non-UTF-8 path: {raw!r}")
        path = root / text
        if path.suffix.lower() in _TRACKED_EXTENSIONS:
            tracked.append(path)
    return tracked


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise ScannerFailure(f"file read failed: {path} ({exc})") from exc


def _scan_text_for_credentials(path: Path, findings: list[Finding], root: Path) -> None:
    content = _read_text(path)
    lines = content.splitlines()
    for line_number, line in enumerate(lines, start=1):
        for rule, pattern in _CREDENTIAL_PATTERNS:
            for match in pattern.finditer(line):
                matched = match.group(0)
                if _PLACEHOLDER_RE.search(matched):
                    continue
                findings.append(Finding(rule, path, line_number, matched, root))


def _scan_python_ast(path: Path, findings: list[Finding], root: Path) -> None:
    content = _read_text(path)
    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError as exc:
        raise ScannerFailure(f"ast-parse-failure: {path}: {exc}") from exc

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        value = func.value
        if not isinstance(value, ast.Name) or value.id != "subprocess":
            continue
        if func.attr not in _SUBPROCESS_NAMES:
            continue
        for keyword in node.keywords:
            if keyword.arg != "shell":
                continue
            keyword_value = keyword.value
            if isinstance(keyword_value, ast.Constant) and keyword_value.value is True:
                line_number = getattr(node, "lineno", 0)
                findings.append(
                    Finding(
                        "subprocess-shell-true",
                        path,
                        line_number,
                        f"subprocess.{func.attr}(shell=True)",
                        root,
                    )
                )


def _scan_high_entropy(path: Path, warnings: list[str], root: Path) -> None:
    content = _read_text(path)
    for line_number, line in enumerate(content.splitlines(), start=1):
        for match in _ENTROPY_RE.finditer(line):
            candidate = match.group(0)
            if _ENTROPY_EXCLUDE_RE.search(candidate):
                continue
            rel = _relative_path(path, root)
            warnings.append(
                f"rule=high-entropy path={rel} "
                f"line={line_number} fingerprint={hashlib.sha256(candidate.encode()).hexdigest()[:16]}"
            )


def _scan_print_calls(path: Path, warnings: list[str], root: Path) -> None:
    content = _read_text(path)
    for line_number, line in enumerate(content.splitlines(), start=1):
        if _PRINT_RE.search(line) and "cloud_llm.py" not in str(path):
            rel = _relative_path(path, root)
            warnings.append(
                f"rule=print-call path={rel} line={line_number}"
            )


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path.name)


def _check_tracked_sensitive_files(root: Path, findings: list[Finding]) -> None:
    env_files = _run_git_ls_files_with_patterns(root, {"*.env", ".env", ".env.*", "*.env.*"})
    for path in env_files:
        if path.suffix.lower() in {".example", ".sample", ".template"}:
            continue
        findings.append(Finding("tracked-env-file", path, 0, str(path), root))

    key_files = _run_git_ls_files_with_patterns(
        root, {"*.key", "*.pem", "*.p12", "*.pfx", "*.cer", "*.crt"}
    )
    for path in key_files:
        findings.append(Finding("tracked-key-file", path, 0, str(path), root))

    db_files = _run_git_ls_files_with_patterns(
        root, {"*.sqlite", "*.sqlite3", "*.db", "*.mdb"}
    )
    for path in db_files:
        findings.append(Finding("tracked-database-file", path, 0, str(path), root))


def _run_git_ls_files_with_patterns(root: Path, patterns: set[str]) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", *patterns],
        cwd=root,
        capture_output=True,
        text=False,
        check=False,
    )
    if result.returncode != 0:
        return []
    paths: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        paths.append(root / text)
    return paths


def _check_gitignore(root: Path, warnings: list[str]) -> None:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        warnings.append("rule=gitignore-missing path=.gitignore")
        return
    content = gitignore.read_text(encoding="utf-8", errors="replace")
    missing = [p for p in _GITIGNORE_PATTERNS if p not in content]
    if missing:
        warnings.append(f"rule=gitignore-incomplete missing={','.join(missing)}")


def _scan_build_artifacts(dist_dir: Path, findings: list[Finding], root: Path) -> None:
    if not dist_dir.exists():
        return
    artifacts = list(dist_dir.glob("*.whl")) + list(dist_dir.glob("*.tar.gz"))
    if not artifacts:
        return

    tmp = Path(tempfile.mkdtemp(prefix="security_scan_artifacts_"))
    try:
        for artifact in artifacts:
            if artifact.name.endswith(".whl"):
                _extract_wheel(artifact, tmp / "wheel", findings)
            elif artifact.name.endswith(".tar.gz"):
                _extract_sdist(artifact, tmp / "sdist", findings)

        for subdir in (tmp / "wheel", tmp / "sdist"):
            if not subdir.exists():
                continue
            for path in subdir.rglob("*"):
                if not path.is_file():
                    continue
                suffix = path.suffix.lower()
                if suffix in _ARTIFACT_TEXT_EXTENSIONS:
                    _scan_text_for_credentials(path, findings, root)
                    if suffix == ".py":
                        _scan_python_ast(path, findings, root)
                if suffix in {".env", ""} and path.name == ".env":
                    findings.append(Finding("artifact-env-file", path, 0, str(path), root))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _extract_wheel(path: Path, target: Path, findings: list[Finding]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(path, "r") as archive:
            archive.extractall(target)
    except Exception as exc:
        raise ScannerFailure(f"wheel-extract-failure: {path}: {exc}") from exc


def _extract_sdist(path: Path, target: Path, findings: list[Finding]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(path, "r:gz") as archive:
            archive.extractall(target, filter="data")
    except Exception as exc:
        raise ScannerFailure(f"sdist-extract-failure: {path}: {exc}") from exc


def _check_license_in_wheel(dist_dir: Path, warnings: list[str], root: Path) -> None:
    for whl in dist_dir.glob("*.whl"):
        rel = _relative_path(whl, root)
        try:
            with zipfile.ZipFile(whl, "r") as archive:
                has_license = any(
                    "LICENSE" in name.upper()
                    or "COPYING" in name.upper()
                    or "NOTICE" in name.upper()
                    for name in archive.namelist()
                )
        except Exception as exc:
            warnings.append(f"rule=wheel-license-check-failed path={rel} message={exc}")
            continue
        if not has_license:
            warnings.append(
                f"rule=wheel-license-missing path={rel} "
                "message=project license is UNRESOLVED (see RELEASE_BLOCKERS.md)"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RC security scanner")
    parser.add_argument("root", nargs="?", default=".", help="repository root")
    parser.add_argument(
        "--dist",
        default="dist",
        help="distribution artifact directory relative to root",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    findings: list[Finding] = []
    warnings: list[str] = []

    print("=== YouTube Intelligence Agent — RC Security Scan ===")
    print(f"Root   : {root}")
    print(f"Dist   : {root / args.dist}")
    print(f"Date   : {datetime_now()}")
    print("")

    try:
        tracked = _run_git_ls_files(root)
        for path in tracked:
            _scan_text_for_credentials(path, findings, root)
            if path.suffix.lower() == ".py":
                _scan_python_ast(path, findings, root)
            if path.suffix.lower() == ".py":
                _scan_high_entropy(path, warnings, root)
                _scan_print_calls(path, warnings, root)

        _check_tracked_sensitive_files(root, findings)
        _check_gitignore(root, warnings)
        _scan_build_artifacts(root / args.dist, findings, root)
        _check_license_in_wheel(root / args.dist, warnings, root)
    except ScannerFailure as exc:
        print(f"error=scanner-failure message={exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error=unexpected-scanner-failure message={exc}", file=sys.stderr)
        return 1

    if warnings:
        print("--- WARN items (review, not blocking) ---")
        for warning in warnings:
            print(f"WARN: {warning}")
        print("")

    if findings:
        print("--- FINDINGS ---")
        for finding in findings:
            print(f"FAIL: {finding}")
        print("")
        print(f"status=findings count={len(findings)}")
        return 1

    print("status=clean")
    return 0


def datetime_now() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    sys.exit(main())
