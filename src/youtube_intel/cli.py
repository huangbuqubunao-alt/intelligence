"""Offline command parsing and safe dispatch for the application services."""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
import time
from dataclasses import dataclass
from enum import IntEnum
from importlib import resources
from pathlib import Path
from typing import NoReturn, Protocol, Sequence
from uuid import uuid4

from youtube_intel.config import AppConfig, ConfigError, load_app_config
from youtube_intel.logging import JsonlLogger
from youtube_intel.public_subtitle_smoke import PublicSubtitleSmoke


class ExitCode(IntEnum):
    OK = 0
    EXECUTION_FAILED = 1
    USAGE_OR_CONFIGURATION = 2
    LOCAL_RESOURCE = 3


@dataclass(frozen=True, slots=True)
class CommandOutcome:
    """A service result that keeps partial failure visible to the CLI."""

    attempted: int = 0
    failed: int = 0
    prerequisite_failed: bool = False
    local_resource_failed: bool = False

    def __post_init__(self) -> None:
        if self.attempted < 0 or self.failed < 0 or self.failed > self.attempted:
            raise ValueError("command outcome counts are invalid")
        if self.prerequisite_failed and self.local_resource_failed:
            raise ValueError("command outcome has conflicting terminal categories")

    @property
    def exit_code(self) -> ExitCode:
        if self.local_resource_failed:
            return ExitCode.LOCAL_RESOURCE
        if self.prerequisite_failed:
            return ExitCode.USAGE_OR_CONFIGURATION
        if self.failed:
            return ExitCode.EXECUTION_FAILED
        return ExitCode.OK


class Operations(Protocol):
    """Frozen application-service boundary; concrete wiring stays outside parsing."""

    def check(self, *, channel: str | None, limit: int | None) -> CommandOutcome: ...

    def process(self, *, video: str | None, resume: bool) -> CommandOutcome: ...

    def retry(self, *, video: str | None, failed_only: bool) -> CommandOutcome: ...

    def weekly(self, *, week: str | None) -> CommandOutcome: ...


class _UnavailableOperations:
    """Fail closed until an explicit composition root supplies the services."""

    @staticmethod
    def _result() -> CommandOutcome:
        return CommandOutcome(prerequisite_failed=True)

    def check(self, *, channel: str | None, limit: int | None) -> CommandOutcome:
        del channel, limit
        return self._result()

    def process(self, *, video: str | None, resume: bool) -> CommandOutcome:
        del video, resume
        return self._result()

    def retry(self, *, video: str | None, failed_only: bool) -> CommandOutcome:
        del video, failed_only
        return self._result()

    def weekly(self, *, week: str | None) -> CommandOutcome:
        del week
        return self._result()


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="youtube-intel", description="Local-first YouTube intelligence agent")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="project root containing config/ (defaults to the installed project root)",
    )
    parser.add_argument("--settings", type=Path, default=Path("config/settings.yaml"))
    parser.add_argument("--channels", type=Path, default=Path("config/channels.yaml"))
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="check all or one channel")
    check.add_argument("--channel")
    check.add_argument("--limit", type=int)

    process = commands.add_parser("process", help="process a video or pending work")
    process.add_argument("--video")
    process.add_argument("--resume", action="store_true")

    retry = commands.add_parser("retry", help="retry a video or failed work")
    retry.add_argument("--video")
    retry.add_argument("--failed-only", action="store_true")

    weekly = commands.add_parser("weekly", help="generate one weekly report")
    weekly.add_argument("--week")
    commands.add_parser("doctor", help="read-only configuration and local-resource checks")
    smoke = commands.add_parser(
        "smoke-public-subtitles",
        help="run the restricted public subtitle release-QA smoke",
    )
    smoke.add_argument("--temporary-root", type=Path, required=True)
    smoke.add_argument("--video-id", action="append", required=True)
    smoke.add_argument("--directory-only", action="store_true")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    operations: Operations | None = None,
    smoke_runner: PublicSubtitleSmoke | None = None,
) -> ExitCode:
    """Run one command and return the ADR-011 exit code without raising failures."""

    # Every invocation receives an in-memory UUID4, including the strictly
    # read-only doctor path.  Doctor deliberately never persists it as JSONL.
    run_id = str(uuid4())
    effective_argv = tuple(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    try:
        args = parser.parse_args(effective_argv)
        if args.command == "smoke-public-subtitles" and _uses_global_configuration(effective_argv):
            return ExitCode.USAGE_OR_CONFIGURATION
        _validate_arguments(args)
        if args.command == "smoke-public-subtitles":
            return (smoke_runner or PublicSubtitleSmoke()).run(
                temporary_root=args.temporary_root,
                video_ids=tuple(args.video_id),
                run_id=run_id,
                directory_only=args.directory_only,
            ).exit_code
        project_root = _project_root(args.project_root)
        config = _load_config(project_root, args.settings, args.channels)
    except (ConfigError, OSError, ValueError):
        return ExitCode.USAGE_OR_CONFIGURATION

    if args.command == "doctor":
        try:
            return _doctor(config, project_root).exit_code
        except _LocalResourceFailure:
            return ExitCode.LOCAL_RESOURCE
        except (OSError, sqlite3.Error):
            return ExitCode.LOCAL_RESOURCE
        except Exception:
            return ExitCode.EXECUTION_FAILED

    logger = JsonlLogger(_project_path(project_root, config.settings.storage.logs_dir) / "operations.jsonl")
    stage = str(args.command)
    started = time.monotonic()
    logger.emit(
        level="INFO",
        event="command.started",
        run_id=run_id,
        stage=stage,
        safe_message="command started",
    )
    try:
        outcome = _dispatch(args, operations or _UnavailableOperations())
    except _LocalResourceFailure:
        outcome = CommandOutcome(local_resource_failed=True)
    except (OSError, sqlite3.Error):
        outcome = CommandOutcome(local_resource_failed=True)
    except Exception:
        outcome = CommandOutcome(failed=1, attempted=1)

    duration_ms = int((time.monotonic() - started) * 1000)
    if outcome.exit_code is ExitCode.OK:
        event, message = "command.finished", "command completed"
    elif outcome.exit_code is ExitCode.LOCAL_RESOURCE:
        event, message = "command.failed", "local resource is unavailable"
    elif outcome.exit_code is ExitCode.USAGE_OR_CONFIGURATION:
        event, message = "command.failed", "command prerequisite is unavailable"
    else:
        event, message = "command.failed", "one or more executed items failed"
    logger.emit(
        level="INFO" if outcome.exit_code is ExitCode.OK else "ERROR",
        event=event,
        run_id=run_id,
        stage=stage,
        safe_message=message,
        duration_ms=duration_ms,
    )
    return outcome.exit_code


def _uses_global_configuration(argv: Sequence[str]) -> bool:
    return any(
        argument == option or argument.startswith(f"{option}=")
        for argument in argv
        for option in ("--project-root", "--settings", "--channels")
    )


def _validate_arguments(args: argparse.Namespace) -> None:
    if args.command == "check" and args.limit is not None and args.limit <= 0:
        raise ValueError("limit must be positive")
    if args.command == "process" and args.resume and args.video is None:
        raise ValueError("--resume requires --video")
    if args.command == "weekly" and args.week is not None:
        year, separator, week = args.week.partition("-W")
        if separator != "-W" or not (year.isdigit() and len(year) == 4 and week.isdigit() and len(week) == 2 and 1 <= int(week) <= 53):
            raise ValueError("week must use YYYY-Www")


def _project_root(value: Path) -> Path:
    root = value.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project root must be a directory")
    return root


def _project_path(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError("project path must be relative")
    resolved = (root / candidate).resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("project path escapes project root") from error
    return resolved


def _load_config(root: Path, settings: Path, channels: Path) -> AppConfig:
    return load_app_config(
        _project_path(root, channels),
        _project_path(root, settings),
    )


def _dispatch(args: argparse.Namespace, operations: Operations) -> CommandOutcome:
    if args.command == "check":
        return operations.check(channel=args.channel, limit=args.limit)
    if args.command == "process":
        return operations.process(video=args.video, resume=args.resume)
    if args.command == "retry":
        return operations.retry(video=args.video, failed_only=args.failed_only)
    if args.command == "weekly":
        return operations.weekly(week=args.week)
    raise ValueError("unknown command")


class _LocalResourceFailure(Exception):
    pass


def _doctor(config: AppConfig, root: Path) -> CommandOutcome:
    storage = config.settings.storage
    data_dir = _project_path(root, storage.data_dir)
    _project_path(root, storage.logs_dir)
    _project_path(root, storage.templates_dir)
    _verify_database(data_dir / "state.sqlite")
    _verify_vault_boundary(Path(storage.vault_root), storage.vault_subdir)
    # Pydantic validation already checks enabled Provider configuration.  Do not
    # read environment values or contact the configured loopback/remote endpoint.
    return CommandOutcome()


def _verify_database(path: Path) -> None:
    if not path.is_file():
        raise _LocalResourceFailure
    expected = hashlib.sha256(
        resources.files("youtube_intel").joinpath("migrations", "001_initial.sql").read_bytes()
    ).hexdigest()
    try:
        with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
            row = connection.execute(
                "SELECT version, name, checksum FROM schema_migrations ORDER BY version DESC LIMIT 1"
            ).fetchone()
            user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    except (OSError, sqlite3.Error) as error:
        raise _LocalResourceFailure from error
    if row != (1, "001_initial.sql", expected) or user_version != 1:
        raise _LocalResourceFailure


def _verify_vault_boundary(vault_root: Path, vault_subdir: str) -> None:
    if not vault_root.is_dir():
        raise _LocalResourceFailure
    root = vault_root.resolve(strict=True)
    target = (root / vault_subdir).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as error:
        raise _LocalResourceFailure from error


__all__ = ["CommandOutcome", "ExitCode", "Operations", "main"]
