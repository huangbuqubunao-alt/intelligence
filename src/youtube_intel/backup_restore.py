"""Bounded, local-only backup and restart-boundary restore for core data."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import threading
import time
import uuid
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable, cast

from .content_summary_read import (
    AuthoritativeContentSummaryReader,
    ContentSummaryReadRejected,
)
from .deep_analysis_persistence import DeepAnalysisPersistenceStore
from .evidence_translation import (
    EvidenceTranslationPresentationService,
    EvidenceTranslator,
)
from .research_lite import RESEARCH_AUTHORITY_TABLES, ResearchLiteService
from .source_authority import (
    BytesReader,
    ChunkReader,
    managed_directory,
    open_managed,
    require_space,
    stage_stream,
)
from .source_run import SOURCE_RUN_ACTIVE_STATES
from .state import SQLiteStateRepository

FORMAT_NAME = "intelligence-core-backup"
FORMAT_VERSION = 1
LATEST_SCHEMA_VERSION = 44
MAX_ARCHIVE_BYTES = 8 * 1024 * 1024 * 1024
MAX_ARCHIVE_FILES = 10_002
MAX_MEMBER_BYTES = 2 * 1024 * 1024 * 1024
MAX_DATA_FILE_BYTES = 2 * 1024 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024 * 1024
_PASSIVE_ADMISSION_WAIT_SECONDS = 20.0
_ID = re.compile(r"^[a-f0-9]{32}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_BACKUP_FILE_NAME = re.compile(r"^Intelligence-Backup-\d{4}-\d{2}-\d{2}\.zip$")
_SECRET_COLUMN = re.compile(
    r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|cookie|secret[_-]?value|credential[_-]?value)",
    re.IGNORECASE,
)
_TERMINAL_JOBS = {"SUCCEEDED", "FAILED_FINAL"}
_TERMINAL_PROVIDER_CALLS = {"SUCCEEDED", "FAILED_FINAL"}
_TERMINAL_DISPATCH = {"SUCCESS_DURABLY_RECORDED", "FAILED_KNOWN"}
_TERMINAL_SOURCE_RUNS = {"COMPLETED", "FAILED", "CANCELLED"}
# The live-execution states are defined once in source_run so this quiescence
# gate and every other "is this run still working?" caller cannot drift apart.
# A settled NEEDS_ATTENTION run is decided per run by _is_settled_attention_source_run.
_ACTIVE_SOURCE_RUN_STATES = frozenset(state.value for state in SOURCE_RUN_ACTIVE_STATES)
_TERMINAL_SOURCE_RUN_CHILDREN = {"COMPLETED", "SKIPPED", "FAILED", "AMBIGUOUS"}
_AMBIGUOUS_DISTILLATION_OUTCOMES = {
    "TRANSPORT_OUTCOME_UNKNOWN": {1},
    "RESERVED_DISPATCH_OUTCOME_UNKNOWN": {1},
    "DISPATCH_CLAIM_STATE_UNKNOWN": {0, 1},
    "PRIOR_ATTEMPT_STATE_UNKNOWN": {0, 1},
}
DEEP_ANALYSIS_AUTHORITY_TABLES = frozenset({
    "deep_analysis_persisted_results", "deep_analysis_evidence",
    "evidence", "evidence_text_bindings", "timed_transcripts",
    "timed_transcript_cues", "artifacts", "videos",
})
_REQUIRED_TABLES = {
    "content_source_snapshots", "evidence_source_ranges",
    "schema_migrations",
    "source_subscriptions",
    "source_tracking_state",
    "source_observations",
    "source_checks",
    "videos",
    "artifacts",
    "current_content_summaries",
    "evidence",
    "intelligences",
    "topics",
    "global_user_settings",
    "jobs",
    "provider_calls",
    "provider_dispatch_states",
    "source_runs",
    "distillation_execution_checkpoints",
    "distillation_no_new_intelligence_results",
    "distillation_cloud_authorizations",
    "distillation_openai_cloud_authorizations",
    "distillation_moonshot_cloud_authorizations",
    "distillation_unidentified_http_responses",
    "distillation_openai_unidentified_http_responses",
    "distillation_moonshot_unidentified_http_responses",
    "distillation_cloud_response_failures",
    "evidence_translation_presentations",
    "intelligence_revisions", "intelligence_revision_evidence",
    "intelligence_state_history", "distillation_cards", "dependency_edges", "source_video_links",
} | DEEP_ANALYSIS_AUTHORITY_TABLES | RESEARCH_AUTHORITY_TABLES


class BackupRestoreError(ValueError):
    """An archive, authority, or activation failed a bounded safety check."""


class _MaintenanceActive(BackupRestoreError):
    """A known operation on this service owns or awaits the maintenance window."""


class _ReadOnlyEvidenceTranslator:
    def translate(
        self, *, excerpt: str, source_language: str, target_language: str
    ) -> str:
        raise AssertionError("Backup validation must never request a translation.")


@dataclass(frozen=True, slots=True)
class BackupResult:
    backup_id: str
    file_name: str
    size_bytes: int
    created_at: str
    preview: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RestorePreview:
    restore_id: str
    archive_sha256: str
    preview: dict[str, Any]



class _BoundedZipReader:
    def __init__(self, stream: BinaryIO) -> None:
        self.stream = stream

    def read(self, size: int = -1) -> bytes:
        remaining = os.fstat(self.stream.fileno()).st_size - self.stream.tell()
        actual = remaining if size < 0 else min(size, remaining)
        if actual > 16 * 1024 * 1024:
            raise BackupRestoreError("Backup ZIP metadata exceeds the supported size.")
        return self.stream.read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self.stream.seek(offset, whence)

    def tell(self) -> int:
        return self.stream.tell()

    def seekable(self) -> bool:
        return True

def machine_configuration_root(data_root: Path) -> Path:
    identity = Path(os.path.abspath(data_root))
    scope = hashlib.sha256(os.fsencode(identity)).hexdigest()
    return identity.parent / ".local-intelligence" / scope


class BackupRestoreService:
    """Owns private archive/staging paths and operates only on core DATA/SQLite."""

    def __init__(
        self,
        *,
        database: Path,
        data_root: Path,
        control_root: Path | None = None,
        current_local_summary_validator: Callable[
            [SQLiteStateRepository, Path, str, str], object
        ]
        | None = None,
    ) -> None:
        self.database = database.expanduser().resolve()
        self.data_root = data_root.expanduser().resolve()
        self.current_local_summary_validator = current_local_summary_validator
        self.control_root = (
            control_root.expanduser().resolve()
            if control_root is not None
            else self.database.parent / ".intelligence-backup-restore"
        )
        self.backup_root = self.control_root / "backups"
        self.staging_root = self.control_root / "staging"
        self.marker_path = self.control_root / "restore-state.json"
        self.result_path = self.control_root / "last-restore.json"
        self._restart_requested = False
        self._staged_lock = threading.RLock()
        self._staged: dict[str, tuple[str, str]] = {}
        self._background_lock = threading.RLock()
        self._background_suspended = 0
        self._background_active = 0
        self._native_import_active = 0
        self._background_wakeup: Callable[[], None] | None = None
        self._configuration_allowed: Callable[[], bool] = lambda: True
        self._maintenance_condition = threading.Condition()
        self._passive_maintenance_owner: int | None = None
        self._maintenance_command = False
        self._ordinary_admission_waiters = 0
        self._ensure_control_root()
        if not self.marker_path.exists():
            self._cleanup_unconfirmed_staging()

    def _ensure_control_root(self) -> None:
        self.control_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.control_root.is_symlink() or not self.control_root.is_dir():
            raise BackupRestoreError("Backup service storage is unsafe.")
        try:
            os.chmod(self.control_root, 0o700)
        except OSError:
            pass
        for path in (self.backup_root, self.staging_root):
            path.mkdir(mode=0o700, exist_ok=True)
            if path.is_symlink() or not path.is_dir():
                raise BackupRestoreError("Backup service storage is unsafe.")
            try:
                os.chmod(path, 0o700)
            except OSError:
                pass

    @property
    def restart_requested(self) -> bool:
        return self._restart_requested

    @property
    def restore_pending(self) -> bool:
        return self.marker_path.exists()

    def request_restart(self) -> None:
        self._restart_requested = True

    def bind_background_wakeup(self, wakeup: Callable[[], None]) -> None:
        self._background_wakeup = wakeup

    def bind_configuration_guard(self, allowed: Callable[[], bool]) -> None:
        self._configuration_allowed = allowed

    @property
    def machine_configuration_root(self) -> Path:
        return machine_configuration_root(self.data_root)

    @contextmanager
    def admission_lock(self, *, exclusive: bool = False) -> Iterator[None]:
        from contextlib import ExitStack

        from .tracked_retry_context import store_lock

        # One machine/DATA pair can be opened by CLI and GUI using different
        # database paths. Share the stable sibling lock as well as preserving
        # the existing database lock used by Content retry and Backup.
        anchor = self.machine_configuration_root / ".admission"
        with ExitStack() as stack:
            for root in (anchor.parent.parent, anchor.parent):
                descriptor = stack.enter_context(managed_directory(root, create=True))
                identity = os.fstat(descriptor)
                if identity.st_uid != os.getuid() or identity.st_mode & 0o022:
                    raise ValueError("Machine configuration directory is unsafe.")
            stack.enter_context(store_lock(anchor, exclusive=exclusive))
            if anchor.parent != self.database.absolute().parent:
                stack.enter_context(store_lock(self.database, exclusive=exclusive))
            yield

    @contextmanager
    def ordinary_admission_lock(self) -> Iterator[None]:
        """Let a known local status read finish before one ordinary admission.

        Never wait for an OS lock or a real maintenance command. Ownership and
        SH acquisition share the condition, so a fresh passive poll cannot enter
        the release/acquire gap. The condition is released before caller IO.
        """
        from contextlib import ExitStack

        from .tracked_retry_context import RetryConflict

        deadline = time.monotonic() + _PASSIVE_ADMISSION_WAIT_SECONDS
        with ExitStack() as stack:
            with self._maintenance_condition:
                self._ordinary_admission_waiters += 1
                try:
                    while self._passive_maintenance_owner is not None:
                        if self._maintenance_command or self._passive_maintenance_owner == threading.get_ident():
                            raise RetryConflict("Protected maintenance prevents ordinary admission")
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise RetryConflict("Passive status verification did not finish in time")
                        self._maintenance_condition.wait(remaining)
                    if self._maintenance_command:
                        raise RetryConflict("Protected maintenance prevents ordinary admission")
                    # Existing store locks stay nonblocking. An unknown external
                    # holder or unsafe inode is never reclassified as passive.
                    stack.enter_context(self.admission_lock())
                finally:
                    self._ordinary_admission_waiters -= 1
                    self._maintenance_condition.notify_all()
            yield

    @property
    def background_allowed(self) -> bool:
        with self._background_lock:
            return (not self._background_suspended and not self.restore_pending
                and not self.restart_requested and self._configuration_allowed())

    @contextmanager
    def background_work(self, *, native_import: bool = False) -> Iterator[bool]:
        """Atomically admit work against protected archive/restore windows."""
        from contextlib import ExitStack

        from .tracked_retry_context import RetryConflict, RetryIntegrity

        with ExitStack() as stack:
            try:
                stack.enter_context(self.admission_lock())
            except (RetryConflict, RetryIntegrity):
                yield False
                return
            with self._background_work_count(native_import=native_import) as allowed:
                yield allowed

    @contextmanager
    def _background_work_count(self, *, native_import: bool) -> Iterator[bool]:
        with self._background_lock:
            allowed = self.background_allowed
            if allowed:
                self._background_active += 1
                if native_import:
                    self._native_import_active += 1
        try:
            yield allowed
        finally:
            if allowed:
                with self._background_lock:
                    self._background_active -= 1
                    if native_import:
                        self._native_import_active -= 1

    def _require_native_import_idle(self) -> None:
        with self._background_lock:
            if self._native_import_active:
                raise BackupRestoreError("A local snapshot is being created. Wait for its import before Restore.")

    @contextmanager
    def _maintenance_window(self, *, passive: bool) -> Iterator[None]:
        # Only this instance's passive status verification may be waited for.
        # Actual commands and OS lock holders remain explicit busy blockers.
        with self._maintenance_condition:
            if (self._maintenance_command or self._passive_maintenance_owner == threading.get_ident()
                or (passive and self._ordinary_admission_waiters)):
                raise _MaintenanceActive("Another Backup, Restore or model configuration operation is in progress.")
            if not passive:
                self._maintenance_command = True
                self._maintenance_condition.notify_all()
            try:
                while self._passive_maintenance_owner is not None:
                    self._maintenance_condition.wait()
                    if passive and (self._maintenance_command or self._ordinary_admission_waiters):
                        raise _MaintenanceActive("Another Backup, Restore or model configuration operation is in progress.")
                if passive:
                    self._passive_maintenance_owner = threading.get_ident()
            except BaseException:
                if not passive:
                    self._maintenance_command = False
                self._maintenance_condition.notify_all()
                raise
        try:
            yield
        finally:
            with self._maintenance_condition:
                if passive:
                    self._passive_maintenance_owner = None
                else:
                    self._maintenance_command = False
                self._maintenance_condition.notify_all()

    @contextmanager
    def _protect_background(self, *, configuration: bool = False, passive: bool = False) -> Iterator[None]:
        # Existing active work remains visible to the quiescence check; do not
        # wait holding SQLite while that work needs SQLite to settle.
        from .tracked_retry_context import RetryConflict, RetryIntegrity

        try:
            with self._maintenance_window(passive=passive), self.admission_lock(exclusive=True):
                if not configuration and not self._configuration_allowed():
                    raise BackupRestoreError("Local model configuration is applying or this runtime is stale.")
                with self._background_lock:
                    self._background_suspended += 1
                try:
                    yield
                finally:
                    with self._background_lock:
                        self._background_suspended -= 1
                    if self._background_wakeup is not None:
                        self._background_wakeup()
        except (RetryConflict, RetryIntegrity) as error:
            self._require_native_import_idle()
            raise BackupRestoreError("Content retry is still writing; wait before Backup or Restore.") from error

    @contextmanager
    def configuration_window(self) -> Iterator[None]:
        """Exclusive source/configuration CAS window; caller retains durable latch."""
        with self._live_transaction(configuration=True) as connection, self._staged_lock:
            if self.restore_pending or self._staged:
                raise BackupRestoreError("Finish or cancel Restore before changing the local model.")
            reasons = self._quiescence_reasons(connection)
            self._verify_core_database(connection)
            if reasons:
                raise BackupRestoreError("Local model configuration is blocked: " + ", ".join(reasons))
            self._live_artifacts(connection)
            yield

    def readiness(self) -> dict[str, object]:
        try:
            with self._live_transaction(passive=True) as connection:
                reasons = self._quiescence_reasons(connection)
                self._verify_core_database(connection)
                if not reasons:
                    self._live_artifacts(connection)
        except (OSError, sqlite3.Error, BackupRestoreError) as error:
            return {
                "ready": False,
                "reasons": ["MAINTENANCE_ACTIVE" if isinstance(error, _MaintenanceActive) else "DATABASE_UNAVAILABLE"],
                "message": str(error) if isinstance(error, BackupRestoreError) else "Core data is unavailable.",
                "restore_pending": self.restore_pending,
            }
        restore_pending = self.restore_pending
        effective_reasons = reasons or (["RESTORE_PENDING"] if restore_pending else [])
        return {
            "ready": not effective_reasons,
            "reasons": effective_reasons,
            "message": self._readiness_message(effective_reasons),
            "restore_pending": restore_pending,
            "last_restore": self._last_result(),
        }

    def create_backup(self) -> BackupResult:
        if self.restore_pending:
            raise BackupRestoreError("A Restore is already pending restart.")
        self._ensure_control_root()
        backup_id = uuid.uuid4().hex
        temp_path = self.backup_root / f".{backup_id}.tmp"
        published_path = self.backup_root / f"{backup_id}.zip"
        snapshot_path = self.backup_root / f".{backup_id}.sqlite"
        try:
            with self._live_transaction() as connection:
                reasons = self._quiescence_reasons(connection)
                if reasons:
                    raise BackupRestoreError(
                        "Backup is temporarily unavailable: " + ", ".join(reasons)
                    )
                self._verify_core_database(connection)
                artifacts = self._live_artifacts(connection)
                total = sum(record["size_bytes"] for record in artifacts.values())
                database_size = int(connection.execute("PRAGMA page_count").fetchone()[0]) * int(connection.execute("PRAGMA page_size").fetchone()[0])
                if total + database_size + 16 * 1024 * 1024 > MAX_TOTAL_BYTES:
                    raise BackupRestoreError("Core data exceeds the supported aggregate backup size.")
                self._require_disk_space(self.backup_root, total + 2 * database_size + 64 * 1024 * 1024)
                self._snapshot_database(snapshot_path)
                snapshot = sqlite3.connect(snapshot_path)
                snapshot.row_factory = sqlite3.Row
                try:
                    integrity = snapshot.execute("PRAGMA integrity_check").fetchone()
                    if integrity is None or integrity[0] != "ok":
                        raise BackupRestoreError("SQLite snapshot failed integrity_check.")
                    self._require_disk_space(self.backup_root, total + snapshot_path.stat().st_size + 64 * 1024 * 1024)
                    manifest = self._manifest(snapshot, snapshot_path, artifacts)
                    self._validate_snapshot_authority(
                        snapshot,
                        repository=SQLiteStateRepository(snapshot_path),
                        data_root=self.data_root,
                    )
                    self._write_archive(temp_path, snapshot_path, artifacts, manifest)
                finally:
                    snapshot.close()
            self._publish_no_replace(temp_path, published_path)
            size = published_path.stat().st_size
            if size > MAX_ARCHIVE_BYTES:
                published_path.unlink(missing_ok=True)
                raise BackupRestoreError("Backup exceeds the supported archive size.")
            created = str(manifest["created_at"])
            result = BackupResult(
                backup_id=backup_id,
                file_name=f"Intelligence-Backup-{created[:10]}.zip",
                size_bytes=size,
                created_at=created,
                preview=self._public_preview(manifest),
            )
            self._write_json(self.control_root / f"backup-{backup_id}.json", {
                "backup_id": backup_id,
                "file_name": result.file_name,
                "created_at": created,
                "size_bytes": size,
                "preview": result.preview,
            })
            return result
        finally:
            temp_path.unlink(missing_ok=True)
            snapshot_path.unlink(missing_ok=True)

    def backup_metadata(self, backup_id: str) -> dict[str, object] | None:
        if not _ID.fullmatch(backup_id):
            return None
        path = self.control_root / f"backup-{backup_id}.json"
        if not path.is_file() or path.is_symlink():
            return None
        try:
            value = json.loads(path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def backup_download(self, backup_id: str) -> tuple[Path, str] | None:
        metadata = self.backup_metadata(backup_id)
        path = self.backup_root / f"{backup_id}.zip"
        if metadata is None or not path.is_file() or path.is_symlink():
            return None
        file_name = metadata.get("file_name")
        if not isinstance(file_name, str) or _BACKUP_FILE_NAME.fullmatch(file_name) is None:
            return None
        return path, file_name

    def stage_restore(self, archive_bytes: bytes) -> RestorePreview:
        return self.stage_restore_stream(BytesReader(archive_bytes), len(archive_bytes))

    def stage_restore_stream(self, source: ChunkReader, length: int, *, cancelled: Callable[[], bool] | None = None) -> RestorePreview:
        with self._protect_background(), self._staged_lock:
            self._require_native_import_idle()
            if self.restore_pending or self._staged:
                raise BackupRestoreError("A Restore is already staged or pending restart.")
            if not 0 < length <= MAX_ARCHIVE_BYTES:
                raise BackupRestoreError("Backup archive size is outside the supported limit.")
            restore_id = uuid.uuid4().hex
            stage_dir = self.staging_root / restore_id
            stage_dir.mkdir(mode=0o700)
            archive_path = stage_dir / "selected.zip"
            try:
                with stage_stream(stage_dir, source, length, maximum=MAX_ARCHIVE_BYTES) as staged:
                    archive_hash = staged.digest
                    staged.publish(stage_dir, "selected.zip")
                with self._read_archive_identity(archive_path, archive_hash) as archive:
                    manifest = self._extract_and_validate(archive, stage_dir)
                if cancelled and cancelled():
                    raise BackupRestoreError("Restore upload was cancelled before staging completed.")
                manifest_hash = hashlib.sha256(self._manifest_bytes(manifest)).hexdigest()
                marker = {
                    "version": 1, "state": "STAGED", "restore_id": restore_id,
                    "archive_sha256": archive_hash, "manifest_sha256": manifest_hash,
                    "created_at": self._utc_now(),
                }
                self._write_json(stage_dir / "stage.json", marker)
                self._staged[restore_id] = (archive_hash, manifest_hash)
                return RestorePreview(restore_id=restore_id, archive_sha256=archive_hash,
                                      preview=self._public_preview(manifest))
            except Exception as error:
                shutil.rmtree(stage_dir, ignore_errors=True)
                if isinstance(error, (OSError, EOFError, ValueError)) and not isinstance(error, BackupRestoreError):
                    raise BackupRestoreError("Restore upload failed: insufficient disk space, timeout, incomplete or unsafe archive.") from error
                raise

    def cancel_restore(self, restore_id: str) -> bool:
        with self._protect_background(), self._staged_lock:
            if not _ID.fullmatch(restore_id) or self.restore_pending or restore_id not in self._staged:
                return False
            stage_dir = self.staging_root / restore_id
            if not stage_dir.is_dir() or stage_dir.is_symlink():
                return False
            shutil.rmtree(stage_dir)
            self._staged.pop(restore_id, None)
            return True

    def confirm_restore(self, restore_id: str) -> dict[str, object]:
        with self._protect_background(), self._staged_lock:
            self._require_native_import_idle()
            if not _ID.fullmatch(restore_id) or self.restore_pending:
                raise BackupRestoreError("Restore confirmation is no longer valid.")
            inspected = self._staged.get(restore_id)
            if inspected is None:
                raise BackupRestoreError("Restore confirmation is no longer valid.")
            stage_dir = self.staging_root / restore_id
            if not stage_dir.is_dir() or stage_dir.is_symlink():
                raise BackupRestoreError("Inspected backup staging is unavailable.")
            stage_state = self._read_json(stage_dir / "stage.json")
            if (
                stage_state.get("version") != 1
                or stage_state.get("state") != "STAGED"
                or stage_state.get("restore_id") != restore_id
                or (stage_state.get("archive_sha256"), stage_state.get("manifest_sha256")) != inspected
            ):
                raise BackupRestoreError("Inspected backup staging is unavailable.")
            archive_path = stage_dir / "selected.zip"
            with self._read_archive_identity(archive_path, inspected[0]) as archive:
                manifest = self._extract_and_validate(archive, stage_dir, clear_existing=False)
            if hashlib.sha256(self._manifest_bytes(manifest)).hexdigest() != inspected[1]:
                raise BackupRestoreError("Inspected manifest changed after staging.")
            marker = {
                "version": 1,
                "state": "PENDING",
                "restore_id": restore_id,
                "archive_sha256": inspected[0],
                "manifest_sha256": inspected[1],
                "confirmed_at": self._utc_now(),
            }
            self._write_json(self.marker_path, marker)
            self.request_restart()
            return {
                "pending": True,
                "restart_required": True,
                "restore_id": restore_id,
                "message": "Restore is ready and will apply before processing resumes.",
            }

    def recover_and_apply_pending_restore(self) -> None:
        with self._protect_background():
            self._recover_and_apply_pending_restore()

    def _recover_and_apply_pending_restore(self) -> None:
        """Run before repositories and workers open; recover finite marker states."""
        if not self.marker_path.exists():
            return
        marker = self._read_json(self.marker_path)
        restore_id = marker.get("restore_id")
        state = marker.get("state")
        if marker.get("version") != 1 or not isinstance(restore_id, str) or not _ID.fullmatch(restore_id):
            raise BackupRestoreError("Restore recovery state is invalid; startup stopped safely.")
        stage_dir = self.staging_root / restore_id
        if state == "PENDING":
            try:
                manifest = self._validated_restore_manifest(restore_id, stage_dir, marker)
            except (BackupRestoreError, OSError, sqlite3.Error, zipfile.BadZipFile):
                self._write_result(restore_id, "REJECTED", "Pending Restore failed validation; current data was kept.")
                self._remove_marker_and_stage(restore_id)
                return
            self._activate_staged_pair(restore_id, stage_dir, manifest, marker)
            return
        if state == "APPLYING":
            self._rollback_activation(restore_id)
            self._write_result(restore_id, "ROLLED_BACK", "Restore activation was interrupted; previous data was restored.")
            self._remove_marker_and_stage(restore_id)
            return
        if state == "VALIDATED":
            try:
                manifest = self._validated_restore_manifest(restore_id, stage_dir, marker)
                self._verify_live_pair(manifest)
            except Exception as validation_error:
                try:
                    self._rollback_after_validation_failure(
                        restore_id, "Restore revalidation failed; previous data was restored."
                    )
                except Exception as rollback_error:
                    raise BackupRestoreError(
                        "Restore revalidation failed and automatic rollback needs recovery; startup stopped safely."
                    ) from (rollback_error or validation_error)
                return
            marker.update({"state": "APPLIED"})
            self._write_json(self.marker_path, marker)
            self._retire_rollback(restore_id)
            self._write_result(restore_id, "APPLIED", "Restore completed successfully.")
            self._remove_marker_and_stage(restore_id)
            return
        if state == "APPLIED":
            try:
                manifest = self._validated_restore_manifest(restore_id, stage_dir, marker)
                self._verify_live_pair(manifest)
            except Exception as validation_error:
                try:
                    self._rollback_after_validation_failure(
                        restore_id, "Committed Restore could not be verified; previous data was restored."
                    )
                except Exception as rollback_error:
                    raise BackupRestoreError(
                        "Committed Restore validation failed and recovery needs attention; startup stopped safely."
                    ) from (rollback_error or validation_error)
                return
            self._retire_rollback(restore_id)
            self._write_result(restore_id, "APPLIED", "Restore completed successfully.")
            self._remove_marker_and_stage(restore_id)
            return
        raise BackupRestoreError("Restore recovery state is unsupported; startup stopped safely.")

    def _validated_restore_manifest(
        self, restore_id: str, stage_dir: Path, marker: dict[str, Any]
    ) -> dict[str, Any]:
        if not stage_dir.is_dir() or stage_dir.is_symlink():
            raise BackupRestoreError("Restore staging is unavailable or unsafe.")
        stage_state = self._read_json(stage_dir / "stage.json")
        archive_path = stage_dir / "selected.zip"
        if (
            stage_state.get("version") != 1
            or stage_state.get("state") != "STAGED"
            or stage_state.get("restore_id") != restore_id
            or stage_state.get("archive_sha256") != marker.get("archive_sha256")
            or stage_state.get("manifest_sha256") != marker.get("manifest_sha256")
        ):
            raise BackupRestoreError("Restore archive identity changed after inspection.")
        with self._read_archive_identity(archive_path, str(marker.get("archive_sha256"))) as archive:
            manifest = self._extract_and_validate(archive, stage_dir, clear_existing=False)
        if hashlib.sha256(self._manifest_bytes(manifest)).hexdigest() != marker.get("manifest_sha256"):
            raise BackupRestoreError("Restore manifest identity changed after inspection.")
        return manifest

    def _rollback_after_validation_failure(self, restore_id: str, message: str) -> None:
        if not self._rollback_pair_available(restore_id):
            raise BackupRestoreError("Previous Restore data pair is no longer available.")
        self._rollback_activation(restore_id)
        self._write_result(restore_id, "ROLLED_BACK", message)
        self._remove_marker_and_stage(restore_id)

    def _rollback_pair_available(self, restore_id: str) -> bool:
        _, old_db, _, old_data, _, _ = self._activation_paths(restore_id)
        return (
            old_db.is_file()
            and not old_db.is_symlink()
            and old_data.is_dir()
            and not old_data.is_symlink()
        )

    def _activate_staged_pair(
        self,
        restore_id: str,
        stage_dir: Path,
        manifest: dict[str, Any],
        marker: dict[str, Any],
    ) -> None:
        new_db, old_db, new_data, old_data, old_wal, old_shm = self._activation_paths(restore_id)
        try:
            self._remove_if_exists(new_db)
            self._remove_if_exists(new_data)
            self._copy_staged_pair(stage_dir, new_db, new_data)
            self._checkpoint_live_database()
            marker.update({"state": "APPLYING"})
            self._write_json(self.marker_path, marker)
            self._rename_if_exists(self.database, old_db)
            self._rename_if_exists(self.database.with_name(self.database.name + "-wal"), old_wal)
            self._rename_if_exists(self.database.with_name(self.database.name + "-shm"), old_shm)
            self._rename_if_exists(self.data_root, old_data)
            self._rename_noreplace(new_db, self.database)
            self._rename_noreplace(new_data, self.data_root)
            self._verify_live_pair(manifest)
            marker.update({"state": "VALIDATED"})
            self._write_json(self.marker_path, marker)
        except Exception:
            try:
                self._rollback_activation(restore_id)
                self._write_result(restore_id, "ROLLED_BACK", "Restore activation failed; previous data was restored.")
                self._remove_marker_and_stage(restore_id)
            except Exception as rollback_error:
                raise BackupRestoreError(
                    "Restore activation failed and automatic rollback needs recovery; startup stopped safely."
                ) from rollback_error
            return
        self._recover_and_apply_pending_restore()

    def _copy_staged_pair(self, stage_dir: Path, new_db: Path, new_data: Path) -> None:
        database_source = stage_dir / "database" / "state.sqlite"
        data_source = stage_dir / "data"
        required = database_source.stat().st_size + sum(p.stat().st_size for p in data_source.rglob("*") if p.is_file())
        database_bytes = database_source.stat().st_size
        if self.database.parent.stat().st_dev == self.data_root.parent.stat().st_dev:
            self._require_disk_space(self.database.parent, required)
        else:
            self._require_disk_space(self.database.parent, database_bytes)
            self._require_disk_space(self.data_root.parent, required - database_bytes)
        self._copy_file_exclusive(database_source, new_db)
        self._copy_tree_allowlisted(data_source, new_data)

    def _copy_tree_allowlisted(self, source: Path, destination: Path) -> None:
        destination.mkdir(mode=0o700)
        for path in sorted(source.rglob("*")):
            if path.is_symlink():
                raise BackupRestoreError("Staged DATA contains a symbolic link.")
            relative = path.relative_to(source)
            target = destination / relative
            if path.is_dir():
                target.mkdir(mode=0o700, exist_ok=True)
            elif path.is_file():
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                self._copy_file_exclusive(path, target)
            else:
                raise BackupRestoreError("Staged DATA contains an unsupported file type.")

    def _verify_live_pair(self, manifest: dict[str, Any]) -> None:
        self._verify_file_record(self.database, manifest["database"])
        with sqlite3.connect(self.database) as connection:
            connection.row_factory = sqlite3.Row
            self._verify_core_database(connection)
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise BackupRestoreError("Restored SQLite integrity_check failed.")
            repository = SQLiteStateRepository(self.database)
            reasons = self._quiescence_reasons(connection, repository=repository)
            if reasons:
                raise BackupRestoreError("Restored backup contains active work: " + ", ".join(reasons))
            self._validate_snapshot_authority(
                connection,
                repository=SQLiteStateRepository(self.database),
                data_root=self.data_root,
            )
            self._verify_artifacts(connection, manifest, self.data_root)
        self._checkpoint_live_database()
        self._verify_file_record(self.database, manifest["database"])

    def _rollback_activation(self, restore_id: str) -> None:
        new_db, old_db, new_data, old_data, old_wal, old_shm = self._activation_paths(restore_id)
        failed_db = self.database.with_name(f".{self.database.name}.m10-{restore_id}.failed")
        failed_data = self.data_root.with_name(f".{self.data_root.name}.m10-{restore_id}.failed")
        if old_db.exists():
            if self.database.exists():
                self._remove_if_exists(self.database.with_name(self.database.name + "-wal"))
                self._remove_if_exists(self.database.with_name(self.database.name + "-shm"))
            self._rename_if_exists(self.database, failed_db)
            self._rename_noreplace(old_db, self.database)
        if old_data.exists():
            self._rename_if_exists(self.data_root, failed_data)
            self._rename_noreplace(old_data, self.data_root)
        self._rename_if_exists(old_wal, self.database.with_name(self.database.name + "-wal"))
        self._rename_if_exists(old_shm, self.database.with_name(self.database.name + "-shm"))
        self._remove_if_exists(failed_db)
        self._remove_if_exists(failed_data)
        self._remove_if_exists(new_db)
        self._remove_if_exists(new_data)

    def _retire_rollback(self, restore_id: str) -> None:
        _, old_db, _, old_data, old_wal, old_shm = self._activation_paths(restore_id)
        for path in (old_db, old_data, old_wal, old_shm):
            self._remove_if_exists(path)

    def _activation_paths(self, restore_id: str) -> tuple[Path, Path, Path, Path, Path, Path]:
        db_prefix = f".{self.database.name}.m10-{restore_id}"
        data_prefix = f".{self.data_root.name}.m10-{restore_id}"
        return (
            self.database.with_name(db_prefix + ".new"),
            self.database.with_name(db_prefix + ".old"),
            self.data_root.with_name(data_prefix + ".new"),
            self.data_root.with_name(data_prefix + ".old"),
            self.database.with_name(db_prefix + ".wal"),
            self.database.with_name(db_prefix + ".shm"),
        )

    def _checkpoint_live_database(self) -> None:
        connection = sqlite3.connect(self.database, timeout=5)
        try:
            result = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if result is None or result[0] != 0:
                raise BackupRestoreError("Live SQLite database is still in use.")
        finally:
            connection.close()

    @staticmethod
    def _rename_noreplace(source: Path, destination: Path) -> None:
        if source.is_symlink() or not source.exists():
            raise BackupRestoreError("Restore activation source is unavailable.")
        if os.name == "posix" and hasattr(ctypes.CDLL(None), "renamex_np"):
            renamex = ctypes.CDLL(None, use_errno=True).renamex_np
            renamex.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
            renamex.restype = ctypes.c_int
            if renamex(os.fsencode(source), os.fsencode(destination), 0x00000004) == 0:
                return
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code), str(destination))
        if os.name == "posix" and hasattr(ctypes.CDLL(None), "renameat2"):
            libc = ctypes.CDLL(None, use_errno=True)
            renameat2 = libc.renameat2
            renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
            renameat2.restype = ctypes.c_int
            if renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 1) == 0:
                return
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code), str(destination))
        raise OSError(errno.ENOTSUP, "no atomic no-replace rename is available")

    def _rename_if_exists(self, source: Path, destination: Path) -> None:
        if not source.exists() and not source.is_symlink():
            return
        self._rename_noreplace(source, destination)

    @staticmethod
    def _remove_if_exists(path: Path) -> None:
        if not path.exists() and not path.is_symlink():
            return
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            raise BackupRestoreError("Restore rollback path has an unsupported file type.")

    def _extract_and_validate(
        self, archive_stream: BinaryIO, stage_dir: Path, *, clear_existing: bool = True
    ) -> dict[str, Any]:
        try:
            archive = zipfile.ZipFile(archive_stream)
        except (OSError, zipfile.BadZipFile) as error:
            raise BackupRestoreError("Backup archive is invalid or truncated.") from error
        with archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_ARCHIVE_FILES:
                raise BackupRestoreError("Backup archive has an unsupported file count.")
            names: set[str] = set()
            folded: set[str] = set()
            total = 0
            for info in infos:
                name = self._safe_archive_path(info.filename)
                if info.is_dir():
                    raise BackupRestoreError("Backup archive contains an unexpected directory entry.")
                if name in names or name.casefold() in folded:
                    raise BackupRestoreError("Backup archive contains duplicate paths.")
                names.add(name)
                folded.add(name.casefold())
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode) or (mode and not stat.S_ISREG(mode)):
                    raise BackupRestoreError("Backup archive contains a symbolic or special file.")
                if info.file_size > MAX_MEMBER_BYTES:
                    raise BackupRestoreError("Backup archive member exceeds the supported size.")
                total += info.file_size
                if total > MAX_TOTAL_BYTES:
                    raise BackupRestoreError("Backup archive expands beyond the supported limit.")
                if info.file_size > 1024 * 1024 and info.compress_size == 0:
                    raise BackupRestoreError("Backup archive has an unsafe compression ratio.")
                if info.compress_size and info.file_size / info.compress_size > 1000:
                    raise BackupRestoreError("Backup archive has an unsafe compression ratio.")
            if "manifest.json" not in names or "database/state.sqlite" not in names:
                raise BackupRestoreError("Backup archive is missing required entries.")
            if archive.getinfo("manifest.json").file_size > 16 * 1024 * 1024:
                raise BackupRestoreError("Backup manifest exceeds the supported size.")
            try:
                raw_manifest = archive.read("manifest.json")
                manifest = json.loads(raw_manifest.decode("utf-8"), parse_constant=self._reject_json_constant)
            except (UnicodeError, ValueError, KeyError) as error:
                raise BackupRestoreError("Backup manifest is invalid.") from error
            self._validate_manifest_shape(manifest)
            manifest = cast(dict[str, Any], manifest)
            expected_names = {"manifest.json", "database/state.sqlite"}
            expected_names.update(
                f"data/{record['relative_path']}" for record in manifest["data_files"]
            )
            if names != expected_names:
                raise BackupRestoreError("Backup archive contains missing or unexpected files.")
            if clear_existing:
                self._require_disk_space(stage_dir, total)
                (stage_dir / "database").mkdir(mode=0o700)
                (stage_dir / "data").mkdir(mode=0o700)
            database_file = stage_dir / "database" / "state.sqlite"
            if clear_existing:
                self._extract_member(archive, "database/state.sqlite", database_file)
            self._verify_file_record(database_file, manifest["database"])
            for record in manifest["data_files"]:
                target = stage_dir / "data" / Path(*PurePosixPath(record["relative_path"]).parts)
                if clear_existing:
                    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    self._extract_member(archive, f"data/{record['relative_path']}", target)
                self._verify_file_record(target, record)
        connection = sqlite3.connect(stage_dir / "database" / "state.sqlite")
        connection.row_factory = sqlite3.Row
        try:
            self._verify_core_database(connection)
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise BackupRestoreError("Backup SQLite failed integrity_check.")
            repository = SQLiteStateRepository(stage_dir / "database" / "state.sqlite")
            reasons = self._quiescence_reasons(connection, repository=repository, data_root=stage_dir / "data")
            if reasons:
                raise BackupRestoreError("Backup contains active work: " + ", ".join(reasons))
            self._validate_snapshot_authority(
                connection, repository=repository, data_root=stage_dir / "data"
            )
            self._verify_artifacts(connection, manifest, stage_dir / "data")
        except sqlite3.Error as error:
            raise BackupRestoreError("Backup SQLite is corrupt or unreadable.") from error
        finally:
            connection.close()
        self._verify_stage_tree(stage_dir, manifest)
        return manifest

    @staticmethod
    def _verify_stage_tree(stage_dir: Path, manifest: dict[str, Any]) -> None:
        expected_files = {
            "selected.zip",
            "database/state.sqlite",
            *(f"data/{record['relative_path']}" for record in manifest["data_files"]),
        }
        if (stage_dir / "stage.json").is_file():
            expected_files.add("stage.json")
        expected_dirs = {"database", "data"}
        for name in expected_files:
            parent = PurePosixPath(name).parent
            while parent != PurePosixPath("."):
                expected_dirs.add(parent.as_posix())
                parent = parent.parent
        actual_files: set[str] = set()
        actual_dirs: set[str] = set()
        for path in stage_dir.rglob("*"):
            if path.is_symlink():
                raise BackupRestoreError("Restore staging contains a symbolic link.")
            relative = path.relative_to(stage_dir).as_posix()
            if path.is_file():
                actual_files.add(relative)
            elif path.is_dir():
                actual_dirs.add(relative)
            else:
                raise BackupRestoreError("Restore staging contains an unsupported file type.")
        if actual_files != expected_files or actual_dirs != expected_dirs:
            raise BackupRestoreError("Restore staging contains unmanifested files.")

    @staticmethod
    def _extract_member(archive: zipfile.ZipFile, name: str, target: Path) -> None:
        info = archive.getinfo(name)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(target, flags, 0o600)
        try:
            with os.fdopen(fd, "wb", closefd=False) as output, archive.open(info) as source:
                shutil.copyfileobj(source, output, length=1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
        finally:
            os.close(fd)

    @staticmethod
    def _safe_archive_path(value: str) -> str:
        if not value or "\\" in value or "\x00" in value or value.startswith("/") or ":" in value:
            raise BackupRestoreError("Backup archive contains an unsafe path.")
        path = PurePosixPath(value)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise BackupRestoreError("Backup archive contains an unsafe path.")
        if path.as_posix() != value or any(ord(char) < 32 for char in value):
            raise BackupRestoreError("Backup archive path is not normalized.")
        return value

    @staticmethod
    def _validate_manifest_shape(manifest: object) -> None:
        if not isinstance(manifest, dict):
            raise BackupRestoreError("Backup manifest must be an object.")
        expected = {
            "format", "format_version", "created_at", "application_version",
            "schema_version", "database", "data_files", "counts", "exclusions",
        }
        if set(manifest) != expected:
            raise BackupRestoreError("Backup manifest fields are incomplete or unsupported.")
        if manifest.get("format") != FORMAT_NAME or manifest.get("format_version") != FORMAT_VERSION:
            raise BackupRestoreError("Backup format is incompatible.")
        if manifest.get("schema_version") not in {34, 35, 36, 37, 38, 39, 40, 41, 42, 43, LATEST_SCHEMA_VERSION}:
            raise BackupRestoreError("Backup database schema is incompatible.")
        if not isinstance(manifest.get("application_version"), str) or not isinstance(
            manifest.get("created_at"), str
        ):
            raise BackupRestoreError("Backup application metadata is invalid.")
        try:
            datetime.fromisoformat(manifest["created_at"].replace("Z", "+00:00"))
        except ValueError as error:
            raise BackupRestoreError("Backup creation timestamp is invalid.") from error
        database = manifest.get("database")
        if not isinstance(database, dict) or set(database) != {"path", "size_bytes", "sha256"}:
            raise BackupRestoreError("Backup database manifest is invalid.")
        if database.get("path") != "database/state.sqlite":
            raise BackupRestoreError("Backup database path is unsupported.")
        if not BackupRestoreService._valid_hash_size(database):
            raise BackupRestoreError("Backup database integrity metadata is invalid.")
        files = manifest.get("data_files")
        if not isinstance(files, list) or len(files) > MAX_ARCHIVE_FILES - 2:
            raise BackupRestoreError("Backup DATA manifest is invalid.")
        paths: set[str] = set()
        neutral = manifest["schema_version"] >= 38
        tracked = manifest["schema_version"] >= 40
        for record in files:
            fields = {"relative_path", "size_bytes", "sha256", "artifacts"}
            if neutral:
                fields.add("retained_subtitle_derivations")
            if tracked:
                fields.add("tracked_content_retry_files")
            if not isinstance(record, dict) or set(record) != fields:
                raise BackupRestoreError("Backup DATA record is invalid.")
            if not isinstance(record["relative_path"], str):
                raise BackupRestoreError("Backup DATA path is invalid.")
            path = BackupRestoreService._safe_archive_path(record["relative_path"])
            if path in paths or not BackupRestoreService._valid_hash_size(record):
                raise BackupRestoreError("Backup DATA integrity metadata is invalid.")
            if record["size_bytes"] > MAX_DATA_FILE_BYTES:
                raise BackupRestoreError("Backup DATA artifact exceeds the supported size.")
            paths.add(path)
            if not isinstance(record["artifacts"], list) or (not record["artifacts"] and not (neutral and record["retained_subtitle_derivations"]) and not (tracked and record["tracked_content_retry_files"])):
                raise BackupRestoreError("Backup DATA artifact identity is missing.")
            for artifact in record["artifacts"]:
                if not isinstance(artifact, dict) or set(artifact) != {
                    "artifact_id", "kind", "video_id"
                }:
                    raise BackupRestoreError("Backup artifact identity is invalid.")
                if not all(isinstance(artifact[field], str) and artifact[field] for field in artifact):
                    raise BackupRestoreError("Backup artifact identity is invalid.")
            if neutral:
                refs = record["retained_subtitle_derivations"]
                if not isinstance(refs,list) or any(not isinstance(ref,dict) or set(ref) != {
                    "archive_id","proof_version","video_id","proof_sha256"
                } or not all(isinstance(value,str) and value for value in ref.values())
                    or ref["proof_version"] != "failed-caption-derivation-v1"
                    or not _SHA256.fullmatch(ref["archive_id"]) or not _SHA256.fullmatch(ref["proof_sha256"])
                    for ref in refs):
                    raise BackupRestoreError("Backup neutral retention identity is invalid.")
                identities = [ref["archive_id"] for ref in refs]
                if identities != sorted(set(identities)):
                    raise BackupRestoreError("Backup neutral retention identities are not unique and sorted.")
            if tracked:
                refs = record['tracked_content_retry_files']
                if (not isinstance(refs,list) or any(not isinstance(ref,dict) or set(ref)!={'request_id','role','state','proof_sha256'}
                    or not all(isinstance(value,str) and value for value in ref.values())
                    or not ref['request_id'].startswith('tracked-content-retry:v1:')
                    or ref['role'] not in {'CAPTURE','RAW_SOURCE','CANONICAL_DERIVATION','SUMMARY_DERIVATION','WRITE_BUFFER'}
                    or ref['state'] not in {'VERIFIED','RETAINED_PARTIAL'} or not _SHA256.fullmatch(ref['proof_sha256']) for ref in refs)):
                    raise BackupRestoreError('Backup Content retry file references are invalid.')
                identities=[ref['request_id'] for ref in refs]
                if identities != sorted(set(identities)):
                    raise BackupRestoreError('Backup Content retry file references are not unique and sorted.')
        counts = manifest.get("counts")
        count_fields = {"following", "content", "summaries", "evidence", "intelligence", "topics", "settings", "data_artifacts", "data_bytes"}
        if tracked:
            count_fields.add("tracked_retry_retained_files")
        if neutral:
            count_fields.add("retained_derivations")
        if not isinstance(counts, dict) or set(counts) != count_fields or any(type(value) is not int or value < 0 for value in counts.values()):
            raise BackupRestoreError("Backup object counts are invalid.")
        exclusions = manifest.get("exclusions")
        if exclusions != {"vault": True, "credentials": True, "model_weights": True}:
            raise BackupRestoreError("Backup exclusion declarations are invalid.")

    @staticmethod
    def _valid_hash_size(record: dict[str, Any]) -> bool:
        return (
            type(record.get("size_bytes")) is int
            and record["size_bytes"] >= 0
            and isinstance(record.get("sha256"), str)
            and bool(_SHA256.fullmatch(record["sha256"]))
        )

    @staticmethod
    def _verify_file_record(path: Path, record: dict[str, Any]) -> None:
        size, digest = BackupRestoreService._hash_path_with_size(path)
        if size != record["size_bytes"] or digest != record["sha256"]:
            raise BackupRestoreError("Backup file hash or size does not match its manifest.")

    def _verify_artifacts(
        self, connection: sqlite3.Connection, manifest: dict[str, Any], root: Path
    ) -> None:
        expected = self._artifact_records(connection, root)
        manifest_records = {
            record["relative_path"]: record for record in manifest["data_files"]
        }
        if set(expected) != set(manifest_records):
            raise BackupRestoreError("Backup DATA set does not match current database authority.")
        actual_files: set[str] = set()
        if root.exists():
            for path in root.rglob("*"):
                if path.is_symlink():
                    raise BackupRestoreError("Staged DATA contains a symbolic link.")
                if path.is_file():
                    actual_files.add(path.relative_to(root).as_posix())
                elif not path.is_dir():
                    raise BackupRestoreError("Staged DATA contains an unsupported file type.")
        if actual_files != set(manifest_records):
            raise BackupRestoreError("Staged DATA contains unmanifested files.")
        counts = manifest["counts"]
        actual_counts = {
            "following": self._count(connection, "source_subscriptions"),
            "content": self._count(connection, "videos"),
            "summaries": self._count(connection, "current_content_summaries"),
            "evidence": self._count(connection, "evidence"),
            "intelligence": self._count(connection, "intelligences"),
            "topics": self._count(connection, "topics"),
            "settings": self._count(connection, "global_user_settings"),
            "data_artifacts": sum(len(record["artifacts"]) for record in expected.values()),
            "data_bytes": sum(record["size_bytes"] for record in expected.values()),
        }
        if int(connection.execute("PRAGMA user_version").fetchone()[0]) >= 38:
            actual_counts["retained_derivations"] = sum(len(record["retained_subtitle_derivations"]) for record in expected.values())
        if int(connection.execute('PRAGMA user_version').fetchone()[0]) >= 40:
            actual_counts['tracked_retry_retained_files']=sum(bool(record['tracked_content_retry_files']) and not record['artifacts'] for record in expected.values())
        if counts != actual_counts:
            raise BackupRestoreError("Backup preview counts do not match its database.")
        for relative, authority in expected.items():
            record = manifest_records[relative]
            if record != authority:
                raise BackupRestoreError("Backup DATA metadata does not match database authority.")
            self._verify_file_record(root / Path(*PurePosixPath(relative).parts), record)

    def _artifact_records(self, connection: sqlite3.Connection, root: Path) -> dict[str, dict[str, Any]]:
        rows = connection.execute(
            "SELECT artifact_id, video_id, kind, relative_path, content_hash "
            "FROM artifacts WHERE storage_root = 'DATA' AND deleted_at IS NULL "
            "ORDER BY relative_path, artifact_id"
        ).fetchall()
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            relative = self._safe_archive_path(str(row["relative_path"]))
            digest = str(row["content_hash"])
            if not _SHA256.fullmatch(digest):
                raise BackupRestoreError("A live DATA artifact has invalid hash authority.")
            record = grouped.get(relative)
            if record is None:
                record = {"relative_path": relative, "sha256": digest, "size_bytes": 0, "artifacts": []}
                grouped[relative] = record
            elif record["sha256"] != digest:
                raise BackupRestoreError("Multiple DATA artifacts disagree about one file.")
            record["artifacts"].append({
                "artifact_id": str(row["artifact_id"]),
                "kind": str(row["kind"]),
                "video_id": str(row["video_id"]),
            })
        if int(connection.execute("PRAGMA user_version").fetchone()[0]) >= 38:
            repository = SQLiteStateRepository(self.database)
            try:
                repository.verify_retained_subtitle_derivations(connection,data_root=root)
            except Exception as error:
                raise BackupRestoreError("Neutral subtitle retention proof failed validation.") from error
            for record in grouped.values():
                record["retained_subtitle_derivations"] = []
            for row in connection.execute("SELECT * FROM retained_subtitle_derivations ORDER BY relative_path,archive_id"):
                relative = self._safe_archive_path(str(row["relative_path"]))
                digest = str(row["derived_sha256"])
                record = grouped.get(relative)
                if record is None:
                    record = {"relative_path":relative,"sha256":digest,"size_bytes":int(row["size_bytes"]),"artifacts":[],"retained_subtitle_derivations":[]}
                    grouped[relative] = record
                elif record["sha256"] != digest:
                    raise BackupRestoreError("Neutral and ordinary DATA references disagree.")
                record["size_bytes"] = int(row["size_bytes"])
                record["retained_subtitle_derivations"].append({"archive_id":str(row["archive_id"]),"proof_version":str(row["proof_version"]),"video_id":str(row["video_id"]),"proof_sha256":str(row["proof_sha256"])})
        if int(connection.execute('PRAGMA user_version').fetchone()[0]) >= 40:
            from .tracked_retry_reader import verify_all

            database=Path(connection.execute('PRAGMA database_list').fetchone()[2])
            repository=SQLiteStateRepository(database)
            repository.bind_source_storage(root)
            try:
                verified=verify_all(repository,root,settled=True)
            except Exception as error:
                raise BackupRestoreError('Content retry ownership or file closure failed validation.') from error
            for record in grouped.values():
                record['tracked_content_retry_files']=[]
            for _request,_execution,files in verified:
                for row in files:
                    if row['state'] not in {'VERIFIED','RETAINED_PARTIAL'}:
                        continue
                    relative=self._safe_archive_path(row['relative_path'])
                    record=grouped.get(relative)
                    if record is None:
                        record=dict(relative_path=relative,sha256=row['observed_sha256'],size_bytes=row['observed_size_bytes'],artifacts=[],retained_subtitle_derivations=[],tracked_content_retry_files=[])
                        grouped[relative]=record
                    if record['sha256']!=row['observed_sha256']:
                        raise BackupRestoreError('Content retry and ordinary DATA references disagree.')
                    record['tracked_content_retry_files'].append({key:row[key] for key in ('request_id','role','state','proof_sha256')})
        for relative, record in grouped.items():
            size, actual_hash = self._safe_hash_data_file(root, relative)
            if actual_hash != record["sha256"]:
                raise BackupRestoreError("A referenced DATA artifact changed or is missing.")
            if size > MAX_DATA_FILE_BYTES:
                raise BackupRestoreError("A referenced DATA artifact exceeds the supported size.")
            if record.get("retained_subtitle_derivations") and record["size_bytes"] != size:
                raise BackupRestoreError("Neutral DATA size changed or is missing.")
            record["size_bytes"] = size
        self._verify_complete_data_set(root,set(grouped))
        return grouped

    @staticmethod
    def _verify_complete_data_set(root: Path, indexed: set[str]) -> None:
        actual: set[str] = set()
        if root.is_symlink() or (root.exists() and not root.is_dir()):
            raise BackupRestoreError("DATA storage root is unsafe.")
        if root.exists():
            for path in root.rglob("*"):
                if path.is_symlink():
                    raise BackupRestoreError("DATA contains a symbolic link.")
                if path.is_file():
                    actual.add(path.relative_to(root).as_posix())
                elif not path.is_dir():
                    raise BackupRestoreError("DATA contains an unsupported file type.")
        if actual != indexed:
            raise BackupRestoreError("DATA contains unindexed files; Backup cannot omit stored bytes.")

    @staticmethod
    def _safe_hash_data_file(root: Path, relative: str) -> tuple[int, str]:
        if root.is_symlink() or not root.is_dir():
            raise BackupRestoreError("DATA storage root is unavailable or unsafe.")
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        directory_fd = os.open(root, flags)
        try:
            parts = PurePosixPath(relative).parts
            for part in parts[:-1]:
                child = os.open(part, flags, dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = child
            file_flags = (
                os.O_RDONLY
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_NONBLOCK", 0)
            )
            file_fd = os.open(parts[-1], file_flags, dir_fd=directory_fd)
            try:
                metadata = os.fstat(file_fd)
                if not stat.S_ISREG(metadata.st_mode):
                    raise BackupRestoreError("A referenced DATA artifact is not a regular file.")
                hasher = hashlib.sha256()
                size = 0
                while chunk := os.read(file_fd, 1024 * 1024):
                    size += len(chunk)
                    hasher.update(chunk)
                after = os.fstat(file_fd)
                if (metadata.st_ino, metadata.st_size, metadata.st_mtime_ns) != (
                    after.st_ino, after.st_size, after.st_mtime_ns
                ) or size != metadata.st_size:
                    raise BackupRestoreError("A referenced DATA artifact changed while reading.")
                return size, hasher.hexdigest()
            finally:
                os.close(file_fd)
        except OSError as error:
            raise BackupRestoreError("A referenced DATA artifact is missing or unsafe.") from error
        finally:
            os.close(directory_fd)

    def _live_artifacts(self, connection: sqlite3.Connection) -> dict[str, dict[str, Any]]:
        return self._artifact_records(connection, self.data_root)

    def _verify_core_database(self, connection: sqlite3.Connection) -> None:
        tables = {
            str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if not _REQUIRED_TABLES <= tables:
            raise BackupRestoreError("SQLite database is missing required Intelligence tables.")
        version_row = connection.execute("PRAGMA user_version").fetchone()
        if version_row is None or int(version_row[0]) not in {34, 35, 36, 37, 38, 39, 40, 41, 42, 43, LATEST_SCHEMA_VERSION}:
            raise BackupRestoreError("SQLite database schema is not compatible with this version.")
        # Schema guards protect execution even before the first synthesis row exists.
        from .system_synthesis_persistence import (
            verify_schema as verify_synthesis_schema,
        )
        try:
            verify_synthesis_schema(connection)
        except Exception as error:
            raise BackupRestoreError("System synthesis provenance failed validation.") from error
        if int(version_row[0]) >= 40:
            from .tracked_retry_reader import verify_schema
            try:
                verify_schema(connection)
            except Exception as error:
                raise BackupRestoreError('Content retry schema authority is incompatible.') from error
        for table in tables:
            quoted = table.replace('"', '""')
            for column in connection.execute(f'PRAGMA table_info("{quoted}")'):
                if _SECRET_COLUMN.search(str(column[1])):
                    raise BackupRestoreError("Database schema contains a credential-like field; backup is disabled.")
        repository = SQLiteStateRepository(self.database)
        migrations = tuple(item for item in repository._load_migrations() if item.version <= int(version_row[0]))
        if not migrations or migrations[-1].version != int(version_row[0]):
            raise BackupRestoreError("Application migration lineage is inconsistent.")
        try:
            history = repository._verify_history(connection, migrations)
        except Exception as error:
            raise BackupRestoreError("SQLite migration history is incompatible.") from error
        if len(history) != len(migrations):
            raise BackupRestoreError("SQLite migration history is incomplete.")
        try:
            repository.verify_cloud_audit_database(connection)
            from .distillation_cancellation import (
                verify_database as verify_cancellations,
            )
            verify_cancellations(connection)
            from .cloud_wait_cancellation import (
                verify_database as verify_cloud_cancellations,
            )
            verify_cloud_cancellations(connection, repository=repository)
            from .cloud_http_observation import (
                verify_database as verify_http_observations,
            )
            verify_http_observations(connection, repository=repository)
            if int(version_row[0]) >= 38:
                repository._verify_retained_subtitle_schema(connection)
            ResearchLiteService(repository).verify_schema(connection)
            from .source_authority import verify_source_schema
            verify_source_schema(connection)
            from .following_tracking import verify_tracking
            verify_tracking(connection)
        except Exception as error:
            raise BackupRestoreError("Research persistence constraints are incompatible.") from error
        membership_columns = tuple(
            (row[1], row[2], row[3], row[5])
            for row in connection.execute("PRAGMA table_info(deep_analysis_evidence)")
        )
        membership_foreign_keys = {
            (row[2], row[3], row[4])
            for row in connection.execute("PRAGMA foreign_key_list(deep_analysis_evidence)")
        }
        if membership_columns != (
            ("result_identity", "TEXT", 1, 1), ("evidence_id", "TEXT", 1, 2), ("created_at", "TEXT", 1, 0),
        ) or membership_foreign_keys != {
            ("deep_analysis_persisted_results", "result_identity", "result_identity"),
            ("evidence", "evidence_id", "evidence_id"),
        }:
            raise BackupRestoreError("Deep Analysis membership constraints are incompatible.")
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise BackupRestoreError("SQLite database has broken foreign-key authority.")

    def _validate_snapshot_authority(
        self,
        connection: sqlite3.Connection,
        *,
        repository: SQLiteStateRepository,
        data_root: Path,
    ) -> None:
        repository.bind_source_storage(data_root)
        from .system_synthesis_persistence import verify_database as verify_synthesis
        try:
            verify_synthesis(repository, connection)
        except Exception as error:
            raise BackupRestoreError("System synthesis provenance failed validation.") from error
        from .long_distillation_persistence import (
            verify_database as verify_long_database,
        )
        try:
            verify_long_database(repository, connection)
        except Exception as error:
            raise BackupRestoreError("Long timed input provenance failed validation.") from error
        if int(connection.execute("PRAGMA user_version").fetchone()[0]) >= 39:
            from .distillation import verify_local_text_input_proof
            try:
                repository._verify_local_text_proof_schema(connection)
                for proof in connection.execute("SELECT execution_id FROM local_text_input_proofs"):
                    execution_id = str(proof[0])
                    verified_proof = verify_local_text_input_proof(repository, connection, execution_id)
                    execution = repository.get_distillation_execution(execution_id)
                    usage = repository.get_distillation_resource_usage(execution_id)
                    # Cancellation is an immutable sidecar receipt: the original
                    # zero-call WAITING_MODEL ledger deliberately stays unchanged.
                    ledger_status = "WAITING_MODEL" if execution is not None and execution.status == "CANCELLED" else None if execution is None else execution.status
                    if execution is None or any(getattr(execution, key) != getattr(usage, key) for key in (
                        "execution_id", "source_id", "video_id", "reason", "use_case", "selected_provider",
                        "selected_model", "budget_state", "invocation_count", "intelligence_id", "revision_id",
                    )) or usage.status != ledger_status:
                        raise ValueError("text proof execution/ledger association is invalid")
                    if execution.status == "SUCCEEDED":
                        from .intelligence_read import AuthoritativeIntelligenceReader
                        if execution.intelligence_id is None or execution.revision_id is None:
                            raise ValueError("text result identity is missing")
                        AuthoritativeIntelligenceReader(repository).read_recorded_card(execution.intelligence_id, execution.revision_id)
                    elif execution.status == "SUCCEEDED_NO_NEW_INTELLIGENCE":
                        result = connection.execute("SELECT * FROM distillation_no_new_intelligence_results WHERE execution_id=?", (execution_id,)).fetchone()
                        ids = [e["evidence_id"] for e in json.loads(verified_proof.input_json)["evidence"]]
                        if (result is None or json.loads(result["evidence_ids_json"]) != ids
                            or hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest() != result["evidence_set_hash"]
                            or usage.invocation_count != 1 or usage.outcome != "NO_NEW_INTELLIGENCE"
                            or usage.actual_provider != execution.selected_provider or usage.actual_model != execution.selected_model):
                            raise ValueError("text NO_NEW input/ledger association is invalid")
                missing = connection.execute(
                    "SELECT 1 FROM distillation_execution_checkpoints d LEFT JOIN local_text_input_proofs p "
                    "ON p.execution_id=d.execution_id WHERE d.execution_id LIKE 'distillation:local-text-v2:%' "
                    "AND p.execution_id IS NULL LIMIT 1").fetchone()
                if missing is not None:
                    raise ValueError("text execution has no original input proof")
                # Reverse-check produced revisions even when every execution
                # sidecar has disappeared. The shared reader recognizes the
                # reserved version family and requires all exact associations.
                from .intelligence_read import AuthoritativeIntelligenceReader
                reader = AuthoritativeIntelligenceReader(repository)
                for revision in connection.execute("SELECT intelligence_id,revision_id FROM intelligence_revisions"):
                    if reader._requires_local_text_card(str(revision["revision_id"])):
                        reader.read_recorded_card(str(revision["intelligence_id"]), str(revision["revision_id"]))
            except Exception as error:
                raise BackupRestoreError("Local text input proof failed validation.") from error
        from .following_tracking import verify_tracking
        try:
            verify_tracking(connection, repository=repository)
        except Exception as error:
            raise BackupRestoreError("Following Content relationship failed validation.") from error
        from .source_authority import verify_source
        for source in connection.execute("SELECT content_id FROM content_source_snapshots"):
            if verify_source(repository,connection,str(source[0])) is None:
                raise BackupRestoreError("Imported source snapshot authority failed validation.")
        for evidence in connection.execute("SELECT e.evidence_id FROM evidence e JOIN videos v USING(video_id) WHERE v.provider IN ('LOCAL','BILIBILI') AND e.availability='AVAILABLE'"):
            if repository._resolve_verified_evidence_text_in_transaction(connection,str(evidence[0])) is None:
                raise BackupRestoreError('Imported source Evidence failed validation.')
        # Reverify every result and its complete membership graph on the staged
        # snapshot, before any live state is replaced. Legacy rows remain legacy.
        deep_analysis = DeepAnalysisPersistenceStore(repository)
        try:
            ResearchLiteService(repository).verify_database(connection)
        except Exception as error:
            raise BackupRestoreError("Research provenance failed validation.") from error
        try:
            for result in connection.execute("SELECT * FROM deep_analysis_persisted_results"):
                deep_analysis._verify_row(result, connection)
        except Exception as error:
            raise BackupRestoreError("Deep Analysis Evidence authority failed validation.") from error
        orphan = connection.execute(
            "SELECT 1 FROM current_content_summaries c LEFT JOIN videos v "
            "ON v.video_id = c.video_id WHERE v.video_id IS NULL LIMIT 1"
        ).fetchone()
        if orphan:
            raise BackupRestoreError("Current Summary points to missing Content.")
        summary_reader = AuthoritativeContentSummaryReader(repository)
        for pointer in connection.execute(
            "SELECT video_id, result_identity, analysis_artifact_id "
            "FROM current_content_summaries"
        ):
            video_id = str(pointer[0])
            has_verified_summary = pointer[1] is not None
            has_local_summary = pointer[2] is not None
            if has_verified_summary == has_local_summary:
                raise BackupRestoreError("A current Summary has an ambiguous authority binding.")
            if has_verified_summary:
                try:
                    current = summary_reader.read_current(video_id)
                except ContentSummaryReadRejected as error:
                    raise BackupRestoreError("A current Summary failed authority validation.") from error
                if current.result_identity != pointer[1]:
                    raise BackupRestoreError("A current Summary pointer changed during validation.")
            else:
                artifact_id = str(pointer[2])
                artifact = connection.execute(
                    "SELECT artifact_id FROM artifacts WHERE artifact_id=?",
                    (artifact_id,),
                ).fetchone()
                if artifact is None:
                    raise BackupRestoreError("A current Summary artifact is missing.")
                summary_artifact = repository.get_artifact(artifact_id)
                from .extractive_summary import PROVIDER as EXTRACTIVE_PROVIDER
                from .extractive_summary import ExtractiveSummaryService
                if summary_artifact is not None and summary_artifact.provider == EXTRACTIVE_PROVIDER:
                    try:
                        ExtractiveSummaryService(repository,data_root).read(video_id,artifact_id)
                    except Exception as error:
                        raise BackupRestoreError("A source Summary failed authority validation.") from error
                    continue
                if self.current_local_summary_validator is None:
                    raise BackupRestoreError(
                        "A current local Summary cannot be validated by the production reader."
                    )
                try:
                    self.current_local_summary_validator(
                        repository, data_root, video_id, artifact_id
                    )
                except Exception as error:
                    raise BackupRestoreError(
                        "A current Summary failed authority validation."
                    ) from error
        translation_reader = EvidenceTranslationPresentationService(
            repository,
            cast(EvidenceTranslator, _ReadOnlyEvidenceTranslator()),
            now=lambda: datetime.now(UTC),
        )
        for row in connection.execute(
            "SELECT evidence_id, target_language FROM evidence_translation_presentations"
        ):
            if translation_reader.read(
                evidence_id=str(row[0]), target_language=str(row[1])
            ) is None:
                raise BackupRestoreError("Evidence translation presentation failed hash validation.")

    def _quiescence_reasons(
        self, connection: sqlite3.Connection, *, repository: SQLiteStateRepository | None = None, data_root: Path | None = None
    ) -> list[str]:
        reasons: list[str] = []
        with self._background_lock:
            if self._background_active:
                reasons.append("SOURCE_RUN_ACTIVE")
        repository = repository or SQLiteStateRepository(self.database)
        repository.bind_source_storage(data_root or self.data_root)
        # Reverse-check retained reserved authorities even when an attacker has
        # removed every checkpoint. The forward execution loop below cannot
        # discover an orphan card/revision/receipt by itself.
        from .long_distillation_persistence import (
            verify_database as verify_long_database,
        )
        try:
            verify_long_database(repository, connection)
        except Exception as error:
            raise BackupRestoreError("Long timed result provenance failed validation.") from error
        if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_checks'").fetchone() is not None:
            if connection.execute("SELECT 1 FROM source_checks WHERE status='RUNNING' LIMIT 1").fetchone() is not None:
                reasons.append("SOURCE_RUN_ACTIVE")
        for (status,) in connection.execute("SELECT DISTINCT status FROM jobs"):
            if status not in _TERMINAL_JOBS:
                reasons.append("JOBS_ACTIVE")
                break
        for (status,) in connection.execute("SELECT DISTINCT status FROM provider_calls"):
            if status not in _TERMINAL_PROVIDER_CALLS:
                reasons.append("PROVIDER_CALL_UNRESOLVED")
                break
        tracked_ambiguous: set[str] = set()
        if int(connection.execute('PRAGMA user_version').fetchone()[0]) >= 40:
            from .tracked_retry_reader import verify_request
            if connection.execute("SELECT 1 FROM tracked_content_retry_executions WHERE state IN ('QUEUED','ACQUIRING','FINALIZING','ATTENTION') LIMIT 1").fetchone():
                reasons.append('TRACKED_CONTENT_RETRY_ACTIVE')
            for row in connection.execute("SELECT request_id,provider_call_hash FROM tracked_content_retry_executions WHERE state='AMBIGUOUS'"):
                try:
                    verify_request(repository,data_root or self.data_root,row['request_id'],settled=True)
                except Exception:
                    continue
                tracked_ambiguous.add(row['provider_call_hash'])
        for row in connection.execute("SELECT request_hash,status FROM provider_dispatch_states"):
            if row['status'] not in _TERMINAL_DISPATCH and not (row['status']=='AMBIGUOUS' and row['request_hash'] in tracked_ambiguous):
                reasons.append('PROVIDER_DISPATCH_UNRESOLVED')
                break
        source_run_columns = {
            str(row[1]) for row in connection.execute('PRAGMA table_info("source_runs")')
        }
        if "state" in source_run_columns:
            if {"run_id", "source_id", "attention_reason"} <= source_run_columns:
                for run in connection.execute(
                    "SELECT run_id, source_id, state, attention_reason FROM source_runs"
                ):
                    state = str(run["state"])
                    if state in _TERMINAL_SOURCE_RUNS:
                        continue
                    if state in _ACTIVE_SOURCE_RUN_STATES:
                        reasons.append("SOURCE_RUN_ACTIVE")
                        break
                    if self._is_terminal_ambiguous_source_run(
                        connection, repository, run
                    ):
                        continue
                    if self._is_cloud_completed_local_wait_source_run(connection, run):
                        continue
                    if self._is_settled_attention_source_run(connection, run, repository):
                        continue
                    if self._is_cancelled_model_wait_source_run(connection, repository, run):
                        continue
                    reasons.append("SOURCE_RUN_ACTIVE")
                    break
            else:
                # Older databases lack the identity and attention fields needed
                # to prove the narrow terminal-ambiguous exception. Preserve the
                # prior fail-closed state-only check for those schemas.
                for (state,) in connection.execute(
                    "SELECT DISTINCT state FROM source_runs"
                ):
                    if state not in _TERMINAL_SOURCE_RUNS:
                        reasons.append("SOURCE_RUN_ACTIVE")
                        break
        for (execution_id,) in connection.execute(
            "SELECT execution_id FROM distillation_execution_checkpoints"
        ):
            try:
                execution = repository.get_distillation_execution(str(execution_id))
            except Exception as error:
                raise BackupRestoreError("A distillation checkpoint failed validation.") from error
            if execution is None:
                raise BackupRestoreError("A distillation checkpoint is missing its authority.")
            status = getattr(execution.status, "value", str(execution.status))
            if status in {"PENDING", "RUNNING", "WAITING_BUDGET", "WAITING_MODEL"}:
                if status == "WAITING_MODEL" and self._is_cloud_completed_local_wait(
                    connection, str(execution_id)
                ):
                    continue
                reasons.append("DISTILLATION_ACTIVE")
                break
            if status == "AMBIGUOUS" and not self._is_terminal_ambiguous_execution(
                repository, str(execution_id)
            ):
                raise BackupRestoreError("An ambiguous distillation checkpoint failed validation.")
        return reasons

    def _is_cancelled_model_wait_source_run(
        self, connection: sqlite3.Connection, repository: SQLiteStateRepository, run: sqlite3.Row,
    ) -> bool:
        if run["state"] != "NEEDS_ATTENTION" or run["attention_reason"] != "MODEL_UNAVAILABLE":
            return False
        children = connection.execute(
            "SELECT * FROM source_run_video_executions WHERE run_id=?", (run["run_id"],),
        ).fetchall()
        has_cancelled_wait = False
        for child in children:
            if child["state"] in _TERMINAL_SOURCE_RUN_CHILDREN:
                continue
            if child["state"] != "WAITING" or child["distillation_execution_id"] is None:
                return False
            execution = repository.get_distillation_execution(str(child["distillation_execution_id"]))
            if (
                execution is None or execution.status != "CANCELLED"
                or execution.source_id != run["source_id"] or execution.video_id != child["video_id"]
            ):
                return False
            has_cancelled_wait = True
        return has_cancelled_wait

    def _is_settled_attention_source_run(
        self, connection: sqlite3.Connection, run: sqlite3.Row, repository: SQLiteStateRepository
    ) -> bool:
        """Whether a NEEDS_ATTENTION run holds no resumable execution authority.

        A run that asks for attention is settled as far as *this* run is
        concerned: nothing is executing and no checkpoint will advance on its
        own.  That is only safe to treat as quiescent when the run also holds no
        child work and its source holds no open distillation checkpoint, because
        either of those can still change and still be resumed.  Anything the
        database cannot prove stays blocking, so corrupt state fails closed.
        """
        if str(run["state"]) != "NEEDS_ATTENTION":
            return False
        if connection.execute(
            "SELECT 1 FROM source_run_video_executions WHERE run_id = ? AND state "
            "NOT IN ('COMPLETED','SKIPPED','FAILED','AMBIGUOUS') LIMIT 1",
            (str(run["run_id"]),),
        ).fetchone() is not None:
            return False
        open_rows = connection.execute(
            "SELECT c.execution_id FROM distillation_execution_checkpoints AS c "
            "WHERE source_id = ? AND status IN "
            "('PENDING','RUNNING','WAITING_BUDGET','WAITING_MODEL') "
            "AND NOT (c.status = 'PENDING' AND c.invocation_count = 1 AND EXISTS ("
            "SELECT 1 FROM distillation_no_new_intelligence_results AS result "
            "WHERE result.execution_id = c.execution_id))",
            (str(run["source_id"]),),
        ).fetchall()
        from .long_distillation_persistence import is_long
        for row in open_rows:
            execution_id = str(row[0])
            # Long cancellation retains raw WAITING_MODEL. Only its fully
            # reverified logical cancellation closes this new work authority;
            # every legacy/unknown/uncancelled checkpoint stays blocking.
            if is_long(execution_id):
                execution = repository.get_distillation_execution(execution_id)
                if execution is not None and execution.status == "CANCELLED":
                    continue
            return False
        return True

    def _is_cloud_completed_local_wait_source_run(
        self, connection: sqlite3.Connection, run: sqlite3.Row
    ) -> bool:
        if (
            str(run["state"]) != "NEEDS_ATTENTION"
            or run["attention_reason"] != "MODEL_UNAVAILABLE"
        ):
            return False
        children = connection.execute(
            "SELECT video_id, state, distillation_execution_id "
            "FROM source_run_video_executions WHERE run_id = ?",
            (str(run["run_id"]),),
        ).fetchall()
        if not children:
            return False
        has_waiting_child = False
        for child in children:
            if child["state"] in _TERMINAL_SOURCE_RUN_CHILDREN:
                continue
            if child["state"] != "WAITING" or not isinstance(
                child["distillation_execution_id"], str
            ):
                return False
            has_waiting_child = True
            if not self._is_cloud_completed_local_wait(
                connection,
                child["distillation_execution_id"],
                source_id=str(run["source_id"]),
                video_id=str(child["video_id"]),
            ):
                return False
        return has_waiting_child

    @staticmethod
    def _is_cloud_completed_local_wait(
        connection: sqlite3.Connection,
        local_execution_id: str,
        *,
        source_id: str | None = None,
        video_id: str | None = None,
    ) -> bool:
        # The local wait remains immutable history. Treat it as quiescent only
        # when a later, separately consented cloud execution for that exact
        # Source and Video has an admitted card and a confirmed HTTP response.
        return connection.execute(
            "SELECT 1 FROM distillation_execution_checkpoints AS local "
            "JOIN distillation_resource_usage AS local_usage "
            "ON local_usage.execution_id = local.execution_id "
            "JOIN source_run_video_executions AS child "
            "ON child.distillation_execution_id = local.execution_id "
            "JOIN source_runs AS run ON run.run_id = child.run_id "
            "JOIN distillation_execution_checkpoints AS cloud "
            "ON cloud.source_id = local.source_id AND cloud.video_id = local.video_id "
            "JOIN distillation_moonshot_cloud_authorizations AS consent "
            "ON consent.execution_id = cloud.execution_id "
            "JOIN distillation_resource_usage AS cloud_usage "
            "ON cloud_usage.execution_id = cloud.execution_id "
            "JOIN distillation_cards AS card ON card.revision_id = cloud.revision_id "
            "WHERE local.execution_id = :execution_id "
            "AND (:source_id IS NULL OR local.source_id = :source_id) "
            "AND (:video_id IS NULL OR local.video_id = :video_id) "
            "AND local.selected_provider = 'ollama' "
            "AND local.status = 'WAITING_MODEL' AND local.invocation_count = 0 "
            "AND local_usage.status = 'WAITING_MODEL' "
            "AND local_usage.invocation_count = 0 "
            "AND local_usage.actual_provider IS NULL "
            "AND run.source_id = local.source_id "
            "AND run.state = 'NEEDS_ATTENTION' "
            "AND run.attention_reason = 'MODEL_UNAVAILABLE' "
            "AND child.video_id = local.video_id AND child.state = 'WAITING' "
            "AND cloud.execution_id != local.execution_id "
            "AND cloud.created_at >= local.created_at "
            "AND cloud.selected_provider = 'moonshot' "
            "AND cloud.selected_model = 'kimi-k2.6' "
            "AND cloud.status = 'SUCCEEDED' "
            "AND cloud.budget_state = 'ADMITTED' "
            "AND cloud.invocation_count = 1 "
            "AND consent.consent_kind = 'USER_CONFIRMATION' "
            "AND consent.provider = cloud.selected_provider "
            "AND consent.model = cloud.selected_model "
            "AND cloud_usage.status = 'SUCCEEDED' "
            "AND cloud_usage.outcome = 'ADMITTED' "
            "AND cloud_usage.invocation_count = 1 "
            "AND cloud_usage.actual_provider = cloud.selected_provider "
            "AND cloud_usage.actual_model = cloud.selected_model "
            "AND cloud_usage.http_status_code = 200 "
            "AND cloud_usage.revision_id = cloud.revision_id "
            "AND card.source_id = local.source_id "
            "AND card.video_id = local.video_id LIMIT 1",
            {
                "execution_id": local_execution_id,
                "source_id": source_id,
                "video_id": video_id,
            },
        ).fetchone() is not None

    @staticmethod
    def _execution_status(execution: object) -> str:
        status = getattr(execution, "status", "")
        return str(getattr(status, "value", status))

    def _is_terminal_ambiguous_execution(
        self,
        repository: SQLiteStateRepository,
        execution_id: str,
        *,
        source_id: str | None = None,
        video_id: str | None = None,
    ) -> bool:
        try:
            execution = repository.get_distillation_execution(execution_id)
        except Exception as error:
            raise BackupRestoreError("An ambiguous distillation checkpoint failed validation.") from error
        if execution is None or self._execution_status(execution) != "AMBIGUOUS":
            return False
        try:
            usage = repository.get_distillation_resource_usage(execution_id)
        except Exception as error:
            raise BackupRestoreError("An ambiguous distillation resource record is missing.") from error

        allowed_invocations = _AMBIGUOUS_DISTILLATION_OUTCOMES.get(usage.outcome)
        if (
            usage.execution_id != execution.execution_id
            or usage.status != "AMBIGUOUS"
            or usage.invocation_count not in (allowed_invocations or set())
            or usage.invocation_count != execution.invocation_count
            or usage.budget_state != execution.budget_state
            or not usage.budget_state.strip()
            or usage.reason != execution.reason
            or usage.use_case != execution.use_case
            or usage.source_id != execution.source_id
            or usage.video_id != execution.video_id
            or usage.selected_provider != execution.selected_provider
            or usage.selected_model != execution.selected_model
            or execution.intelligence_id is not None
            or execution.revision_id is not None
            or usage.intelligence_id is not None
            or usage.revision_id is not None
            or usage.actual_provider is not None
            or usage.actual_model is not None
            or usage.input_tokens is not None
            or usage.output_tokens is not None
            or usage.cost_microunits is not None
            or usage.duration_ms is not None
            or (source_id is not None and execution.source_id != source_id)
            or (video_id is not None and execution.video_id != video_id)
        ):
            raise BackupRestoreError("An ambiguous distillation resource record failed validation.")
        return True

    def _is_terminal_ambiguous_source_run(
        self,
        connection: sqlite3.Connection,
        repository: SQLiteStateRepository,
        run: sqlite3.Row,
    ) -> bool:
        if (
            str(run["state"]) != "NEEDS_ATTENTION"
            or run["attention_reason"] != "AMBIGUOUS_EXTERNAL_OUTCOME"
        ):
            return False
        children = connection.execute(
            "SELECT video_id, state, distillation_execution_id "
            "FROM source_run_video_executions WHERE run_id = :run_id ORDER BY video_id",
            {"run_id": str(run["run_id"])},
        ).fetchall()
        if not children:
            return False
        has_ambiguous_child = False
        for child in children:
            state = str(child["state"])
            if state not in _TERMINAL_SOURCE_RUN_CHILDREN:
                return False
            if state != "AMBIGUOUS":
                continue
            execution_id = child["distillation_execution_id"]
            if not isinstance(execution_id, str) or not execution_id:
                return False
            has_ambiguous_child = True
            if not self._is_terminal_ambiguous_execution(
                repository,
                execution_id,
                source_id=str(run["source_id"]),
                video_id=str(child["video_id"]),
            ):
                return False
        return has_ambiguous_child

    def _live_transaction(self, *, configuration: bool = False, passive: bool = False) -> Any:
        service = self

        class Transaction:
            def __enter__(self) -> sqlite3.Connection:
                self.protection = service._protect_background(configuration=configuration, passive=passive)
                self.protection.__enter__()
                try:
                    self.connection = sqlite3.connect(service.database, timeout=1, isolation_level=None)
                    self.connection.row_factory = sqlite3.Row
                    self.connection.execute("PRAGMA foreign_keys=ON")
                    self.connection.execute("BEGIN IMMEDIATE")
                    return self.connection
                except BaseException:
                    if hasattr(self, "connection"):
                        self.connection.close()
                    self.protection.__exit__(None, None, None)
                    raise

            def __exit__(self, *_: object) -> None:
                try:
                    self.connection.execute("ROLLBACK")
                finally:
                    self.connection.close()
                    self.protection.__exit__(None, None, None)

        return Transaction()

    def _snapshot_database(self, target_path: Path) -> None:
        source = sqlite3.connect(self.database, timeout=1)
        target = sqlite3.connect(target_path)
        try:
            source.backup(target, pages=256, sleep=0.01)
            target.commit()
        except sqlite3.Error as error:
            raise BackupRestoreError("SQLite backup snapshot failed.") from error
        finally:
            source.close()
            target.close()

    def _manifest(
        self,
        connection: sqlite3.Connection,
        snapshot_path: Path,
        artifacts: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        db_size, db_hash = self._hash_path_with_size(snapshot_path)
        counts = {
            "following": self._count(connection, "source_subscriptions"),
            "content": self._count(connection, "videos"),
            "summaries": self._count(connection, "current_content_summaries"),
            "evidence": self._count(connection, "evidence"),
            "intelligence": self._count(connection, "intelligences"),
            "topics": self._count(connection, "topics"),
            "settings": self._count(connection, "global_user_settings"),
            "data_artifacts": sum(len(row["artifacts"]) for row in artifacts.values()),
            "data_bytes": sum(row["size_bytes"] for row in artifacts.values()),
        }
        neutral = int(connection.execute("PRAGMA user_version").fetchone()[0]) >= 38
        if neutral:
            counts["retained_derivations"] = sum(len(row["retained_subtitle_derivations"]) for row in artifacts.values())
        if int(connection.execute('PRAGMA user_version').fetchone()[0]) >= 40:
            counts['tracked_retry_retained_files']=sum(bool(row['tracked_content_retry_files']) and not row['artifacts'] for row in artifacts.values())
        try:
            app_version = package_version("youtube-intel")
        except PackageNotFoundError:
            app_version = "unknown"
        return {
            "format": FORMAT_NAME,
            "format_version": FORMAT_VERSION,
            "created_at": self._utc_now(),
            "application_version": app_version,
            "schema_version": int(connection.execute("PRAGMA user_version").fetchone()[0]),
            "database": {"path": "database/state.sqlite", "size_bytes": db_size, "sha256": db_hash},
            "data_files": [
                {
                    "relative_path": relative,
                    "size_bytes": record["size_bytes"],
                    "sha256": record["sha256"],
                    "artifacts": record["artifacts"],
                    **({"retained_subtitle_derivations": record["retained_subtitle_derivations"]} if neutral else {}),
                    **({"tracked_content_retry_files": record["tracked_content_retry_files"]} if int(connection.execute("PRAGMA user_version").fetchone()[0]) >= 40 else {}),
                }
                for relative, record in sorted(artifacts.items())
            ],
            "counts": counts,
            "exclusions": {"vault": True, "credentials": True, "model_weights": True},
        }

    @staticmethod
    def _count(connection: sqlite3.Connection, table: str) -> int:
        return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])

    def _write_archive(
        self,
        target: Path,
        snapshot_path: Path,
        artifacts: dict[str, dict[str, Any]],
        manifest: dict[str, Any],
    ) -> None:
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            self._zip_write(archive, "manifest.json", self._manifest_bytes(manifest))
            self._zip_write_file(archive, "database/state.sqlite", snapshot_path)
            for relative in sorted(artifacts):
                self._zip_write_data_file(
                    archive, f"data/{relative}", relative, artifacts[relative]
                )
        if target.stat().st_size > MAX_ARCHIVE_BYTES:
            raise BackupRestoreError("Backup exceeds the supported archive size.")

    @staticmethod
    def _zip_write(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (stat.S_IFREG | 0o600) << 16
        archive.writestr(info, data)

    @staticmethod
    def _zip_write_file(archive: zipfile.ZipFile, name: str, path: Path) -> None:
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (stat.S_IFREG | 0o600) << 16
        with archive.open(info, "w", force_zip64=True) as output, path.open("rb") as source:
            shutil.copyfileobj(source, output, length=1024 * 1024)

    def _zip_write_data_file(
        self,
        archive: zipfile.ZipFile,
        archive_name: str,
        relative: str,
        authority: dict[str, Any],
    ) -> None:
        info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (stat.S_IFREG | 0o600) << 16
        if any(artifact["kind"] == "audio" for artifact in authority["artifacts"]):
            info.compress_type = zipfile.ZIP_STORED
        root_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        directory_fd = os.open(self.data_root, root_flags)
        try:
            parts = PurePosixPath(relative).parts
            for part in parts[:-1]:
                child = os.open(part, root_flags, dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = child
            file_fd = os.open(
                parts[-1],
                os.O_RDONLY
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_NONBLOCK", 0),
                dir_fd=directory_fd,
            )
            try:
                before = os.fstat(file_fd)
                if not stat.S_ISREG(before.st_mode):
                    raise BackupRestoreError("A referenced DATA artifact is not a regular file.")
                hasher = hashlib.sha256()
                size = 0
                with archive.open(info, "w", force_zip64=True) as output:
                    while chunk := os.read(file_fd, 1024 * 1024):
                        size += len(chunk)
                        hasher.update(chunk)
                        output.write(chunk)
                after = os.fstat(file_fd)
                if (
                    (before.st_ino, before.st_size, before.st_mtime_ns)
                    != (after.st_ino, after.st_size, after.st_mtime_ns)
                    or size != authority["size_bytes"]
                    or hasher.hexdigest() != authority["sha256"]
                ):
                    raise BackupRestoreError("A referenced DATA artifact changed while copying.")
            finally:
                os.close(file_fd)
        except OSError as error:
            raise BackupRestoreError(
                "A referenced DATA artifact changed or disappeared while copying."
            ) from error
        finally:
            os.close(directory_fd)

    @staticmethod
    def _manifest_bytes(manifest: dict[str, Any]) -> bytes:
        cleaned = json.loads(json.dumps(manifest))
        return json.dumps(cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def _public_preview(self, manifest: dict[str, Any]) -> dict[str, object]:
        counts = manifest["counts"]
        return {
            "backup_date": manifest["created_at"],
            "application_version": manifest["application_version"],
            "schema_version": manifest["schema_version"],
            "following_count": counts["following"],
            "content_count": counts["content"],
            "summary_count": counts["summaries"],
            "evidence_count": counts["evidence"],
            "intelligence_count": counts["intelligence"],
            "topic_count": counts["topics"],
            "settings_included": True,
            "data_artifact_count": counts["data_artifacts"],
            "data_size_bytes": counts["data_bytes"],
            "data_file_count": len({record["relative_path"] for record in manifest["data_files"]}),
            "data_file_size_bytes": counts["data_bytes"],
            "vault_excluded": True,
        }

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    @staticmethod
    def _readiness_message(reasons: list[str]) -> str:
        if not reasons:
            return "Core data is quiescent and ready for backup."
        messages = {
            "RESTORE_PENDING": "A confirmed Restore is waiting to apply at restart.",
            "JOBS_ACTIVE": "A processing job is pending or running.",
            "PROVIDER_CALL_UNRESOLVED": "A local or provider call is unresolved.",
            "PROVIDER_DISPATCH_UNRESOLVED": "A dispatch state is unresolved.",
            "SOURCE_RUN_ACTIVE": "A Following Source Run is active.",
            "DISTILLATION_ACTIVE": "A distillation checkpoint is still active.",
        }
        return " ".join(messages.get(reason, "Core data is not quiescent.") for reason in reasons)

    @staticmethod
    def _reject_json_constant(_: str) -> None:
        raise ValueError("non-finite JSON number")

    @staticmethod
    def _write_exclusive(path: Path, data: bytes) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags, 0o600)
        try:
            with os.fdopen(fd, "wb", closefd=False) as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
        finally:
            os.close(fd)
        BackupRestoreService._fsync_dir(path.parent)

    @staticmethod
    def _copy_file_exclusive(source: Path, destination: Path) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        source_flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        source_fd = os.open(source, source_flags)
        try:
            if not stat.S_ISREG(os.fstat(source_fd).st_mode):
                raise BackupRestoreError("Staged file is not a regular file.")
            destination_fd = os.open(destination, flags, 0o600)
            try:
                with os.fdopen(destination_fd, "wb", closefd=False) as output, os.fdopen(
                    source_fd, "rb", closefd=False
                ) as input_file:
                    shutil.copyfileobj(input_file, output, length=1024 * 1024)
                    output.flush()
                    os.fsync(output.fileno())
            finally:
                os.close(destination_fd)
        finally:
            os.close(source_fd)
        BackupRestoreService._fsync_dir(destination.parent)

    @staticmethod
    def _require_disk_space(root: Path, required: int) -> None:
        try:
            with managed_directory(root) as descriptor:
                require_space(descriptor, required)
        except OSError as error:
            raise BackupRestoreError("Insufficient available disk space for Backup or Restore.") from error

    @staticmethod
    @contextmanager
    def _read_archive_identity(path: Path, expected_hash: str) -> Iterator[BinaryIO]:
        try:
            with open_managed(path.parent, path.name, maximum=MAX_ARCHIVE_BYTES) as stream:
                def verify() -> None:
                    stream.seek(0)
                    hasher = hashlib.sha256()
                    size = 0
                    while chunk := stream.read(1024 * 1024):
                        size += len(chunk)
                        if size > MAX_ARCHIVE_BYTES:
                            raise BackupRestoreError("Inspected backup archive exceeds the supported size.")
                        hasher.update(chunk)
                    if size != os.fstat(stream.fileno()).st_size or hasher.hexdigest() != expected_hash:
                        raise BackupRestoreError("Restore archive identity changed after inspection.")
                    stream.seek(0)
                verify()
                yield cast(BinaryIO, _BoundedZipReader(stream))
                verify()
        except (OSError, ValueError) as error:
            if isinstance(error, BackupRestoreError):
                raise
            raise BackupRestoreError("Inspected backup archive is missing, changed or unsafe.") from error

    @staticmethod
    def _hash_path_with_size(path: Path) -> tuple[int, str]:
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        try:
            file_fd = os.open(path, flags)
        except OSError as error:
            raise BackupRestoreError("Backup file is missing or unsafe.") from error
        try:
            metadata = os.fstat(file_fd)
            if not stat.S_ISREG(metadata.st_mode):
                raise BackupRestoreError("Backup file is missing or unsafe.")
            hasher = hashlib.sha256()
            size = 0
            while chunk := os.read(file_fd, 1024 * 1024):
                size += len(chunk)
                hasher.update(chunk)
            after = os.fstat(file_fd)
            if (metadata.st_ino, metadata.st_size, metadata.st_mtime_ns) != (
                after.st_ino, after.st_size, after.st_mtime_ns
            ) or size != metadata.st_size:
                raise BackupRestoreError("Backup file changed while being read.")
            return size, hasher.hexdigest()
        except OSError as error:
            raise BackupRestoreError("Backup file changed or became unavailable.") from error
        finally:
            os.close(file_fd)

    def _write_json(self, path: Path, value: dict[str, Any]) -> None:
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self._write_exclusive(temporary, data)
        os.replace(temporary, path)
        self._fsync_dir(path.parent)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024:
                raise BackupRestoreError("Restore recovery metadata is unavailable.")
            value = json.loads(path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError) as error:
            raise BackupRestoreError("Restore recovery metadata is invalid.") from error
        if not isinstance(value, dict):
            raise BackupRestoreError("Restore recovery metadata is invalid.")
        return value

    @staticmethod
    def _publish_no_replace(source: Path, destination: Path) -> None:
        if source.is_symlink() or destination.exists() or destination.is_symlink():
            raise BackupRestoreError("Backup destination already exists or is unsafe.")
        os.link(source, destination, follow_symlinks=False)
        BackupRestoreService._fsync_dir(destination.parent)
        source.unlink()

    @staticmethod
    def _fsync_dir(path: Path) -> None:
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass

    def _write_result(self, restore_id: str, state: str, message: str) -> None:
        self._write_json(self.result_path, {
            "restore_id": restore_id,
            "state": state,
            "message": message,
            "completed_at": self._utc_now(),
        })

    def _last_result(self) -> dict[str, object] | None:
        try:
            return self._read_json(self.result_path)
        except BackupRestoreError:
            return None

    def _remove_marker_and_stage(self, restore_id: str) -> None:
        self.marker_path.unlink(missing_ok=True)
        self._fsync_dir(self.control_root)
        self._remove_if_exists(self.staging_root / restore_id)
        with self._staged_lock:
            self._staged.pop(restore_id, None)

    def _cleanup_unconfirmed_staging(self) -> None:
        for path in self.staging_root.iterdir():
            if path.is_dir() and not path.is_symlink() and _ID.fullmatch(path.name):
                shutil.rmtree(path)
