"""Start an isolated, non-spending QA API using the normal application lifecycle.

Run from this checkout with PYTHONPATH=src. No arbitrary configuration, host,
database, vault or credential namespace overrides are accepted. This launcher
does not qualify a model or authorize a paid validation batch.
"""

from __future__ import annotations

import argparse
import fcntl
import signal
import threading
from pathlib import Path
from types import FrameType

from youtube_intel.config import AppConfig, AppSettings, load_settings
from youtube_intel.local_api import serve_loopback
from youtube_intel.model_settings import (
    MacOSBigModelQACredentialStore,
    MacOSMoonshotQACredentialStore,
)
from youtube_intel.runtime_composition import build_local_source_run_runtime

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_DIRECTORY = "user-readiness-candidate"


def validate_candidate_root(project_root: Path, *, repository_root: Path = REPOSITORY_ROOT) -> Path:
    """Refuse redirects before creating files, reading Keychain, or opening SQLite."""
    repository_root = repository_root.resolve(strict=True)
    expected = repository_root / ".var" / CANDIDATE_DIRECTORY
    if project_root.absolute() != expected:
        raise ValueError("QA root must be this checkout's dedicated candidate directory")
    for path in (expected.parent, expected, *expected.parents):
        if path.is_symlink():
            raise ValueError("QA paths must not contain symbolic links")
    if expected.exists():
        if not expected.is_dir():
            raise ValueError("QA root must be a directory")
        for path in expected.rglob("*"):
            if path.is_symlink() or (path.is_file() and path.stat().st_nlink != 1):
                raise ValueError("QA files must not link to another data owner")
    return expected


def candidate_config(project_root: Path, *, repository_root: Path = REPOSITORY_ROOT) -> AppConfig:
    root = validate_candidate_root(project_root, repository_root=repository_root)
    # Read only the tracked, non-secret example. Never load formal or candidate
    # settings whose storage paths could redirect a runtime/restore operation.
    settings = load_settings(repository_root / "config" / "settings.example.yaml").model_dump()
    settings["storage"] = {
        "data_dir": "data", "logs_dir": "logs", "templates_dir": "templates",
        "vault_root": str(root / "vault"), "vault_subdir": "YouTube Intel",
    }
    settings["cloud"]["enabled"] = False
    settings["intelligence"]["mode"] = "local-only"
    return AppConfig(channels=(), settings=AppSettings.model_validate(settings))


def serve_candidate(*, port: int = 6378, repository_root: Path = REPOSITORY_ROOT) -> None:
    if not 1024 <= port <= 65535:
        raise ValueError("QA port must be between 1024 and 65535")
    root = repository_root.resolve(strict=True) / ".var" / CANDIDATE_DIRECTORY
    config = candidate_config(root, repository_root=repository_root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Keep one owner across all restore restarts. No separate scheduler process
    # may accidentally drive the same QA database from a second launcher.
    with (root / "qa-launch.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("This QA candidate already has a running owner") from None
        for directory in ("data", "logs", "templates", "vault"):
            (root / directory).mkdir(exist_ok=True, mode=0o700)
        stop_requested = False
        while True:
            validate_candidate_root(root, repository_root=repository_root)
            composition = build_local_source_run_runtime(
                config=config, project_root=root, database=root / "state.sqlite3",
                credential_store=MacOSMoonshotQACredentialStore(),
                bigmodel_credential_store=MacOSBigModelQACredentialStore(),
                allow_environment_credentials=False, allow_cloud_execution=False,
            )
            server = serve_loopback(composition.application, port=port)

            def request_stop(signum: int, frame: FrameType | None) -> None:
                nonlocal stop_requested
                stop_requested = True
                threading.Thread(target=server.shutdown, daemon=True).start()

            previous_handlers = {
                sig: signal.signal(sig, request_stop)
                for sig in (signal.SIGTERM, signal.SIGINT)
            } if threading.current_thread() is threading.main_thread() else {}
            try:
                composition.worker.start()
                server.serve_forever()
            finally:
                server.server_close()
                composition.application.shutdown_native_import()
                composition.worker.stop()
                for sig, handler in previous_handlers.items():
                    signal.signal(sig, handler)
            if stop_requested or not composition.backup_restore.restart_requested:
                break


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=6378)
    args = parser.parse_args(argv)
    try:
        serve_candidate(port=args.port)
    except (OSError, ValueError):
        print("QA startup refused: check isolated paths, ownership and loopback port.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
