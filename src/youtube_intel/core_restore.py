"""Explicit-confirmation, restart-boundary restore coordination for core backups."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from youtube_intel.core_backup import (
    CoreBackupError,
    CoreBackupInspection,
    CoreBackupService,
    StagedCoreRestore,
)
from youtube_intel.state import format_utc_datetime

_PENDING_FORMAT = "intelligence-pending-restore-v1"
_CONTROL_DIR = ".intelligence-restore"
_PENDING_FILE = "pending.json"
_STAGED_DIR = "staged"
_PREVIOUS_DIR = "previous"
_FAILED_DIR = "failed"


class CoreRestoreError(ValueError):
    """A confirmed restore could not proceed without risking current data."""


@dataclass(frozen=True, slots=True)
class PendingCoreRestore:
    staging_root: Path
    live_data_relative: str
    confirmed_live_fingerprint: str
    scheduled_at: datetime
    backup_created_at: datetime
    schema_version: int


@dataclass(frozen=True, slots=True)
class AppliedCoreRestore:
    restored_data_root: Path
    previous_data_root: Path
    inspection: CoreBackupInspection


def _parse_utc(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CoreRestoreError(f"{label} timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as error:
        raise CoreRestoreError(f"{label} timestamp is invalid") from error
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise CoreRestoreError(f"{label} timestamp is not UTC")
    return parsed


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _remove_fixed_staging_root(path: Path, expected_parent: Path) -> None:
    resolved_parent = expected_parent.resolve(strict=True)
    resolved = path.resolve(strict=True)
    if resolved.parent != resolved_parent or path.is_symlink():
        raise CoreRestoreError("restore staging root is outside the managed boundary")
    shutil.rmtree(resolved)


class CoreRestoreCoordinator:
    """Stage, confirm and apply one restore only at a process restart boundary."""

    def __init__(
        self,
        *,
        project_root: Path,
        data_root: Path,
        app_version: str,
        now: callable[[], datetime] | None = None,
    ) -> None:
        self._project_root = project_root.resolve(strict=True)
        if not self._project_root.is_dir() or project_root.is_symlink():
            raise CoreRestoreError("project root is unavailable or unsafe")

        self._data_root = data_root.resolve(strict=False)
        try:
            relative = self._data_root.relative_to(self._project_root)
        except ValueError as error:
            raise CoreRestoreError("data root must stay inside the project root") from error
        if not relative.parts:
            raise CoreRestoreError("data root cannot be the project root")
        if self._data_root == self._project_root / _CONTROL_DIR:
            raise CoreRestoreError("data root conflicts with restore control storage")
        self._live_data_relative = relative.as_posix()

        self._control_root = self._project_root / _CONTROL_DIR
        self._staged_parent = self._control_root / _STAGED_DIR
        self._pending_path = self._control_root / _PENDING_FILE
        self._app_version = app_version
        self._now = now or (lambda: datetime.now(UTC))
        self._backup = CoreBackupService(
            data_root=self._data_root,
            app_version=app_version,
            now=self._now,
        )

    def stage_backup(self, archive_path: Path) -> StagedCoreRestore:
        self._ensure_control_directories()
        return self._backup.stage_restore(
            archive_path,
            staging_parent=self._staged_parent,
        )

    def schedule_restore(
        self,
        staged: StagedCoreRestore,
        *,
        confirmed: bool,
    ) -> PendingCoreRestore:
        """Persist intent only after an explicit caller confirmation."""

        if not confirmed:
            raise CoreRestoreError("restore requires explicit confirmation")
        self._ensure_control_directories()
        if self._pending_path.exists():
            raise CoreRestoreError("another restore is already pending")

        staging_root = self._managed_staging_root(staged.staging_root)
        inspection = self._backup.inspect_staged_restore(staging_root)
        if inspection != staged.inspection:
            raise CoreRestoreError("staged restore changed before confirmation")

        try:
            live_fingerprint = self._backup.live_core_fingerprint()
        except CoreBackupError as error:
            raise CoreRestoreError(
                "current workspace is not quiescent and integrity-checked"
            ) from error

        now = self._now()
        if now.tzinfo is None or now.utcoffset() != UTC.utcoffset(now):
            raise CoreRestoreError("restore clock must return UTC")

        marker = {
            "format": _PENDING_FORMAT,
            "staging_name": staging_root.name,
            "live_data_relative": self._live_data_relative,
            "confirmed_live_fingerprint": live_fingerprint,
            "scheduled_at": format_utc_datetime(now),
            "backup_created_at": format_utc_datetime(inspection.created_at),
            "schema_version": inspection.schema_version,
        }
        body = json.dumps(
            marker,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        descriptor, temporary = tempfile.mkstemp(
            prefix=".pending-",
            dir=self._control_root,
        )
        temporary_path = Path(temporary)
        try:
            with os.fdopen(descriptor, "wb") as target:
                target.write(body)
                target.flush()
                os.fsync(target.fileno())
            if self._pending_path.exists():
                raise CoreRestoreError("another restore became pending")
            os.replace(temporary_path, self._pending_path)
            _fsync_directory(self._control_root)
        finally:
            temporary_path.unlink(missing_ok=True)

        pending = self.read_pending()
        if pending is None:
            raise CoreRestoreError("pending restore marker was not saved")
        return pending

    def read_pending(self) -> PendingCoreRestore | None:
        if not self._pending_path.exists():
            return None
        if self._pending_path.is_symlink() or not self._pending_path.is_file():
            raise CoreRestoreError("pending restore marker is unsafe")
        try:
            value = json.loads(self._pending_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CoreRestoreError("pending restore marker is invalid") from error
        required = {
            "format",
            "staging_name",
            "live_data_relative",
            "confirmed_live_fingerprint",
            "scheduled_at",
            "backup_created_at",
            "schema_version",
        }
        if (
            not isinstance(value, dict)
            or set(value) != required
            or value.get("format") != _PENDING_FORMAT
        ):
            raise CoreRestoreError("pending restore marker format is invalid")

        staging_name = value.get("staging_name")
        live_relative = value.get("live_data_relative")
        fingerprint = value.get("confirmed_live_fingerprint")
        schema_version = value.get("schema_version")
        if (
            not isinstance(staging_name, str)
            or not staging_name
            or "/" in staging_name
            or "\\" in staging_name
            or staging_name in {".", ".."}
            or not isinstance(live_relative, str)
            or live_relative != self._live_data_relative
            or not _valid_sha256(fingerprint)
            or not isinstance(schema_version, int)
            or isinstance(schema_version, bool)
            or schema_version <= 0
        ):
            raise CoreRestoreError("pending restore marker values are invalid")

        staging_root = self._managed_staging_root(self._staged_parent / staging_name)
        return PendingCoreRestore(
            staging_root=staging_root,
            live_data_relative=live_relative,
            confirmed_live_fingerprint=str(fingerprint),
            scheduled_at=_parse_utc(value.get("scheduled_at"), label="scheduled"),
            backup_created_at=_parse_utc(
                value.get("backup_created_at"), label="backup-created"
            ),
            schema_version=schema_version,
        )

    def cancel_pending_restore(self) -> bool:
        pending = self.read_pending()
        if pending is None:
            return False
        self._pending_path.unlink()
        _fsync_directory(self._control_root)
        _remove_fixed_staging_root(pending.staging_root, self._staged_parent)
        return True

    def apply_pending_on_startup(self) -> AppliedCoreRestore | None:
        """Apply only a previously confirmed marker before any runtime DB opens."""

        pending = self.read_pending()
        if pending is None:
            return None

        inspection = self._backup.inspect_staged_restore(pending.staging_root)
        if (
            inspection.created_at != pending.backup_created_at
            or inspection.schema_version != pending.schema_version
        ):
            raise CoreRestoreError("pending restore no longer matches its staged backup")

        if self._data_root.is_symlink() or not self._data_root.is_dir():
            raise CoreRestoreError("current data root is unavailable or unsafe")

        try:
            current_fingerprint = self._backup.live_core_fingerprint()
        except CoreBackupError as error:
            raise CoreRestoreError(
                "current workspace cannot be revalidated before restore"
            ) from error
        if current_fingerprint != pending.confirmed_live_fingerprint:
            raise CoreRestoreError(
                "current data changed after restore confirmation; live data was not touched"
            )

        staged_fingerprint = CoreBackupService(
            data_root=pending.staging_root / "data",
            app_version=self._app_version,
            now=self._now,
        ).live_core_fingerprint()

        previous_parent = self._control_root / _PREVIOUS_DIR
        failed_parent = self._control_root / _FAILED_DIR
        previous_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        failed_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        token = pending.staging_root.name
        previous_root = previous_parent / token
        failed_root = failed_parent / token
        if previous_root.exists() or failed_root.exists():
            raise CoreRestoreError("restore rollback destination already exists")
        previous_root.mkdir(mode=0o700)
        previous_data = previous_root / "data"
        staged_data = pending.staging_root / "data"

        moved_current = False
        installed_restore = False
        try:
            os.replace(self._data_root, previous_data)
            moved_current = True
            _fsync_directory(self._data_root.parent)

            try:
                os.replace(staged_data, self._data_root)
                installed_restore = True
                _fsync_directory(self._data_root.parent)
            except BaseException:
                os.replace(previous_data, self._data_root)
                moved_current = False
                _fsync_directory(self._data_root.parent)
                raise

            restored_fingerprint = CoreBackupService(
                data_root=self._data_root,
                app_version=self._app_version,
                now=self._now,
            ).live_core_fingerprint()
            if restored_fingerprint != staged_fingerprint:
                raise CoreRestoreError(
                    "restored data changed during the restart-boundary swap"
                )
        except BaseException as error:
            if installed_restore and moved_current:
                failed_root.mkdir(mode=0o700)
                failed_data = failed_root / "data"
                try:
                    os.replace(self._data_root, failed_data)
                    os.replace(previous_data, self._data_root)
                    _fsync_directory(self._data_root.parent)
                    moved_current = False
                except BaseException as rollback_error:
                    raise CoreRestoreError(
                        "restore failed and automatic rollback could not complete"
                    ) from rollback_error
                self._pending_path.unlink(missing_ok=True)
                _fsync_directory(self._control_root)
            if isinstance(error, CoreRestoreError):
                raise
            raise CoreRestoreError("restart-boundary restore failed safely") from error

        self._pending_path.unlink()
        _fsync_directory(self._control_root)
        manifest = pending.staging_root / "manifest.json"
        manifest.unlink(missing_ok=True)
        try:
            pending.staging_root.rmdir()
        except OSError:
            pass

        return AppliedCoreRestore(
            restored_data_root=self._data_root,
            previous_data_root=previous_data,
            inspection=inspection,
        )

    def _ensure_control_directories(self) -> None:
        for path in (self._control_root, self._staged_parent):
            if path.exists():
                if path.is_symlink() or not path.is_dir():
                    raise CoreRestoreError("restore control directory is unsafe")
            else:
                path.mkdir(mode=0o700, parents=True)
        _fsync_directory(self._control_root)

    def _managed_staging_root(self, path: Path) -> Path:
        if not self._staged_parent.exists():
            raise CoreRestoreError("restore staging parent does not exist")
        parent = self._staged_parent.resolve(strict=True)
        resolved = path.resolve(strict=True)
        if path.is_symlink() or not resolved.is_dir() or resolved.parent != parent:
            raise CoreRestoreError("restore staging root is outside the managed boundary")
        return resolved


def apply_pending_core_restore(
    *,
    project_root: Path,
    data_root: Path,
    app_version: str,
    now: callable[[], datetime] | None = None,
) -> AppliedCoreRestore | None:
    """Small startup seam used before a repository connection is opened."""

    coordinator = CoreRestoreCoordinator(
        project_root=project_root,
        data_root=data_root,
        app_version=app_version,
        now=now,
    )
    return coordinator.apply_pending_on_startup()


__all__ = [
    "AppliedCoreRestore",
    "CoreRestoreCoordinator",
    "CoreRestoreError",
    "PendingCoreRestore",
    "apply_pending_core_restore",
]
