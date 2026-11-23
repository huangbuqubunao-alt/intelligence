"""Offline command parsing and safe dispatch for the application services."""

from __future__ import annotations

import argparse
import signal
import sqlite3
import sys
import threading
import time
from pathlib import Path
from types import FrameType
from typing import NoReturn, Sequence
from uuid import uuid4

from youtube_intel.config import AppConfig, ConfigError, load_app_config
from youtube_intel.logging import JsonlLogger
from youtube_intel.operations import CommandOutcome, ExitCode, Operations
from youtube_intel.public_subtitle_smoke import PublicSubtitleSmoke


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="youtube-intel", description="Local-first YouTube intelligence agent"
    )
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
    tick = commands.add_parser(
        "scheduler-tick",
        help="claim bounded due local automation work; execution remains governance-guarded",
    )
    tick.add_argument("--database", type=Path, required=True)
    tick.add_argument("--limit", type=int, default=20)
    api = commands.add_parser(
        "serve-api",
        help="serve the loopback-only local application API",
    )
    api.add_argument("--database", type=Path, required=True)
    api.add_argument("--port", type=int, default=8765)
    api.add_argument("--native-import-origin", action="append", default=[])
    api.add_argument("--native-picker-executable", type=Path)
    api.add_argument("--web-dir", type=Path)
    demo = commands.add_parser(
        "demo",
        help="launch an isolated zero-config showcase workspace with sample data",
    )
    demo.add_argument("--port", type=int, default=8765)
    demo.add_argument("--reset", action="store_true")
    demo.add_argument("--demo-root", type=Path)
    demo.add_argument("--web-dir", type=Path)
    demo.add_argument("--no-web", action="store_true")
    start = commands.add_parser(
        "start",
        help="launch a zero-config local workspace with real Ollama / Obsidian support",
    )
    start.add_argument("--port", type=int, default=8765)
    start.add_argument("--workspace-root", type=Path)
    start.add_argument("--vault", type=Path)
    start.add_argument("--web-dir", type=Path)
    start.add_argument("--no-web", action="store_true")
    start.add_argument("--check-only", action="store_true")
    commands.add_parser(
        "doctor", help="read-only configuration and local-resource checks"
    )
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
        if args.command == "smoke-public-subtitles" and _uses_global_configuration(
            effective_argv
        ):
            return ExitCode.USAGE_OR_CONFIGURATION
        _validate_arguments(args)
        if args.command == "smoke-public-subtitles":
            return (
                (smoke_runner or PublicSubtitleSmoke())
                .run(
                    temporary_root=args.temporary_root,
                    video_ids=tuple(args.video_id),
                    run_id=run_id,
                    directory_only=args.directory_only,
                )
                .exit_code
            )
        if args.command == "scheduler-tick":
            from youtube_intel.runtime_composition import (
                build_local_source_run_runtime,
            )

            project_root = _project_root(args.project_root)
            config = _load_config(project_root, args.settings, args.channels)
            composition = build_local_source_run_runtime(
                config=config,
                project_root=project_root,
                database=args.database,
            )
            with composition.backup_restore.background_work() as admitted:
                if not admitted:
                    print("Local configuration or protected work prevents scheduler admission.")
                    return ExitCode.USAGE_OR_CONFIGURATION
                runs = composition.product.scheduler_tick(limit=args.limit)
            for _ in runs:
                if composition.worker.run_once() is None:
                    break
            print(f"Claimed {len(runs)} durable automation run(s).")
            return ExitCode.OK
        if args.command == "demo":
            from youtube_intel.demo_showcase import serve_demo_showcase

            if args.port < 1024 or args.port > 65535:
                return ExitCode.USAGE_OR_CONFIGURATION
            project_root = _project_root(args.project_root)
            try:
                return serve_demo_showcase(
                    project_root,
                    port=args.port,
                    demo_root=args.demo_root,
                    reset=bool(args.reset),
                    web_dir=args.web_dir,
                    serve_web=not bool(args.no_web),
                )
            except ValueError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return ExitCode.USAGE_OR_CONFIGURATION
        if args.command == "start":
            from youtube_intel.workspace_launcher import serve_local_workspace

            if args.port < 1024 or args.port > 65535:
                return ExitCode.USAGE_OR_CONFIGURATION
            project_root = _project_root(args.project_root)
            try:
                return serve_local_workspace(
                    project_root,
                    port=args.port,
                    workspace_root=args.workspace_root,
                    vault_dir=args.vault,
                    web_dir=args.web_dir,
                    serve_web=not bool(args.no_web),
                    check_only=bool(args.check_only),
                )
            except (ConfigError, ValueError) as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return ExitCode.USAGE_OR_CONFIGURATION
            except OSError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return ExitCode.LOCAL_RESOURCE
        if args.command == "serve-api":
            from youtube_intel.fast_read_api import diagnose_vault_root_error
            from youtube_intel.local_api import serve_loopback
            from youtube_intel.runtime_composition import (
                build_local_source_run_runtime,
            )

            if args.port < 1024 or args.port > 65535:
                return ExitCode.USAGE_OR_CONFIGURATION
            project_root = _project_root(args.project_root)
            config = _load_config(project_root, args.settings, args.channels)
            stop_requested = False
            while True:
                try:
                    composition = build_local_source_run_runtime(
                        config=config,
                        project_root=project_root,
                        database=args.database,
                    )
                except OSError as err:
                    if diagnose_vault_root_error(config, err):
                        return ExitCode.LOCAL_RESOURCE
                    raise
                if args.native_import_origin:
                    if args.native_picker_executable is None:
                        raise ValueError("Native import requires its prepared selector")
                    composition.application.enable_native_import(tuple(args.native_import_origin), picker_executable=args.native_picker_executable)
                server = serve_loopback(
                    composition.application,
                    port=args.port,
                    static_dir=args.web_dir,
                )
                def request_stop(signum: int, frame: FrameType | None) -> None:
                    nonlocal stop_requested
                    stop_requested = True
                    # HTTPServer.shutdown must run outside serve_forever's
                    # thread. The normal finally then drains the owning worker.
                    threading.Thread(target=server.shutdown, daemon=True).start()

                previous_handlers = {
                    sig: signal.signal(sig, request_stop)
                    for sig in (signal.SIGTERM, signal.SIGINT)
                } if threading.current_thread() is threading.main_thread() else {}
                composition.worker.start()
                try:
                    server.serve_forever()
                finally:
                    server.server_close()
                    composition.application.shutdown_native_import()
                    composition.worker.stop()
                    for sig, handler in previous_handlers.items():
                        signal.signal(sig, handler)
                if stop_requested or not composition.backup_restore.restart_requested:
                    break
            return ExitCode.OK
        project_root = _project_root(args.project_root)
        config = _load_config(project_root, args.settings, args.channels)
    except (ConfigError, OSError, ValueError):
        print(
            "ERROR: Configuration or command arguments are invalid. "
            "Run `youtube-intel --help` and `youtube-intel doctor`.",
            file=sys.stderr,
        )
        return ExitCode.USAGE_OR_CONFIGURATION

    if args.command == "doctor":
        try:
            from youtube_intel.runtime import doctor

            report = doctor(config, project_root)
            print(report.render())
            return report.exit_code
        except _LocalResourceFailure:
            print(
                "ERROR: Doctor could not read a required local resource.",
                file=sys.stderr,
            )
            return ExitCode.LOCAL_RESOURCE
        except (OSError, sqlite3.Error):
            print(
                "ERROR: Doctor could not read the local filesystem or database.",
                file=sys.stderr,
            )
            return ExitCode.LOCAL_RESOURCE
        except Exception:
            print(
                "ERROR: Doctor failed safely before completing its checks.",
                file=sys.stderr,
            )
            return ExitCode.EXECUTION_FAILED

    return _run_operations(args, config, project_root, operations, run_id)


def _run_operations(
    args: argparse.Namespace, config: AppConfig, project_root: Path,
    operations: Operations | None, run_id: str,
) -> ExitCode:
    if operations is not None:
        return _run_admitted_operations(args, config, project_root, operations, run_id)
    # Legacy CLI keeps its fast/scoring route. It still participates in the
    # machine apply barrier before bootstrap or any provider/job admission.
    from youtube_intel.local_intelligence_settings import legacy_configuration_admission

    try:
        data = _project_path(project_root, config.settings.storage.data_dir)
        with legacy_configuration_admission(data) as allowed:
            if not allowed:
                print("Local Intelligence configuration must settle before this command.", file=sys.stderr)
                return ExitCode.USAGE_OR_CONFIGURATION
            return _run_admitted_operations(args, config, project_root, None, run_id)
    except (OSError, ValueError, sqlite3.Error):
        print("Local configuration or protected work prevents this command.", file=sys.stderr)
        return ExitCode.LOCAL_RESOURCE


def _run_admitted_operations(
    args: argparse.Namespace, config: AppConfig, project_root: Path,
    operations: Operations | None, run_id: str,
) -> ExitCode:
    if operations is None:
        try:
            from youtube_intel.runtime import create_runtime_operations

            operations = create_runtime_operations(config, project_root)
        except (OSError, sqlite3.Error, ValueError):
            print(
                "ERROR: Local runtime initialization failed. Run `youtube-intel doctor` for details.",
                file=sys.stderr,
            )
            return ExitCode.LOCAL_RESOURCE

    logger = JsonlLogger(
        _project_path(project_root, config.settings.storage.logs_dir)
        / "operations.jsonl"
    )
    stage = str(args.command)
    started = time.monotonic()
    try:
        logger.emit(
            level="INFO",
            event="command.started",
            run_id=run_id,
            stage=stage,
            safe_message="command started",
        )
    except (OSError, ValueError):
        print(
            "ERROR: The local operations log is unavailable. "
            "Check the configured logs directory.",
            file=sys.stderr,
        )
        return ExitCode.LOCAL_RESOURCE
    try:
        outcome = _dispatch(args, operations)
    except _LocalResourceFailure:
        outcome = CommandOutcome(
            local_resource_failed=True,
            safe_message="A required local resource is unavailable.",
        )
    except (OSError, sqlite3.Error):
        outcome = CommandOutcome(
            local_resource_failed=True,
            safe_message=(
                "A required local file or database is unavailable. "
                "Run `youtube-intel doctor` for details."
            ),
        )
    except Exception:
        outcome = CommandOutcome(
            failed=1,
            attempted=1,
            safe_message=(
                "The command failed safely. Run `youtube-intel doctor` "
                "and inspect the local JSONL log."
            ),
        )

    duration_ms = int((time.monotonic() - started) * 1000)
    if outcome.exit_code is ExitCode.OK:
        event, message = "command.finished", "command completed"
    elif outcome.exit_code is ExitCode.LOCAL_RESOURCE:
        event, message = "command.failed", "local resource is unavailable"
    elif outcome.exit_code is ExitCode.USAGE_OR_CONFIGURATION:
        event, message = "command.failed", "command prerequisite is unavailable"
    else:
        event, message = "command.failed", "one or more executed items failed"
    try:
        logger.emit(
            level="INFO" if outcome.exit_code is ExitCode.OK else "ERROR",
            event=event,
            run_id=run_id,
            stage=stage,
            safe_message=message,
            duration_ms=duration_ms,
        )
    except (OSError, ValueError):
        print(
            "ERROR: The command finished but its local operations log could not be written.",
            file=sys.stderr,
        )
        return ExitCode.LOCAL_RESOURCE
    if outcome.safe_message is not None:
        print(
            outcome.safe_message,
            file=sys.stdout if outcome.exit_code is ExitCode.OK else sys.stderr,
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
        if separator != "-W" or not (
            year.isdigit()
            and len(year) == 4
            and week.isdigit()
            and len(week) == 2
            and 1 <= int(week) <= 53
        ):
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


__all__ = ["CommandOutcome", "ExitCode", "Operations", "main"]
