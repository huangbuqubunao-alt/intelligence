"""Integrity-checked backup archive for Intelligence-owned core local data."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Callable

from youtube_intel.state import format_utc_datetime

_BACKUP_FORMAT = "intelligence-core-backup-v1"
_MANIFEST_PATH = "manifest.json"
_DATABASE_ARCHIVE_PATH = "data/state.sqlite"
_MAX_MANIFEST_BYTES = 1_000_000
_MAX_ARCHIVE_FILES = 100_000
_MAX_TOTAL_UNCOMPRESSED_BYTES = 64 * 1024 * 1024 * 1024
_CHUNK = 1024 * 1024
_CORE_SCOPE = (
    "Following",
    "Content",
    "Transcript",
    "Summary / Video Notes",
    "Evidence",
    "Intelligence",
    "Topic",
    "Settings",
)


class CoreBackupError(ValueError):
    """A backup cannot be created or trusted without risking incomplete state."""


@dataclass(frozen=True, slots=True)
class CoreBackupInspection:
    format_version: str
    created_at: datetime
    schema_version: int
    artifact_count: int
    excluded_vault_artifact_count: int
    total_bytes: int
    core_scope: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CoreBackupResult:
    archive_path: Path
    inspection: CoreBackupInspection


@dataclass(frozen=True, slots=True)
class StagedCoreRestore:
    staging_root: Path
    data_root: Path
    inspection: CoreBackupInspection


def _sha256_stream(source: BinaryIO) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    while True:
        chunk = source.read(_CHUNK)
        if not chunk:
            break
        size += len(chunk)
        if size > _MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise CoreBackupError("backup file exceeds the supported V1 size limit")
        digest.update(chunk)
    return digest.hexdigest(), size


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or ".." in path.parts
        or not path.parts
        or value.startswith("~")
    ):
        raise CoreBackupError("backup contains an unsafe relative path")
    return path


def _safe_archive_path(value: str) -> str:
    return "/".join(_safe_relative_path(value).parts)


def _open_regular_under(root: Path, relative_path: str) -> BinaryIO:
    """Open one regular file without following a substituted symlink."""

    relative = _safe_relative_path(relative_path)
    if root.is_symlink():
        raise CoreBackupError("data root must not be a symlink")
    resolved_root = root.resolve(strict=True)
    if not resolved_root.is_dir():
        raise CoreBackupError("data root is not a directory")

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = os.open(resolved_root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in relative.parts[:-1]:
            next_directory = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | nofollow,
                dir_fd=directory,
            )
            os.close(directory)
            directory = next_directory
        file_descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | nofollow,
            dir_fd=directory,
        )
    except BaseException:
        os.close(directory)
        raise
    else:
        os.close(directory)

    try:
        mode = os.fstat(file_descriptor).st_mode
        if not stat.S_ISREG(mode):
            raise CoreBackupError("backup source is not a regular file")
        return os.fdopen(file_descriptor, "rb")
    except BaseException:
        os.close(file_descriptor)
        raise


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        is not None
    )


def _active_work_reasons(connection: sqlite3.Connection) -> tuple[str, ...]:
    checks = (
        (
            "jobs",
            "SELECT COUNT(*) FROM jobs "
            "WHERE status IN ('PENDING','RUNNING','RETRY_PENDING')",
            "pipeline jobs",
        ),
        (
            "provider_calls",
            "SELECT COUNT(*) FROM provider_calls "
            "WHERE status IN ('PENDING','FAILED_RETRYABLE')",
            "provider calls",
        ),
        (
            "provider_dispatch_states",
            "SELECT COUNT(*) FROM provider_dispatch_states "
            "WHERE status IN ('DISPATCH_INTENT_DURABLE','DISPATCHED_RESULT_UNKNOWN')",
            "provider dispatches",
        ),
        (
            "automation_runs",
            "SELECT COUNT(*) FROM automation_runs "
            "WHERE status IN ('CLAIMED','RUNNING')",
            "automation runs",
        ),
        (
            "source_runs",
            "SELECT COUNT(*) FROM source_runs "
            "WHERE state IN ('QUEUED','RUNNING','WAITING','PARTIAL')",
            "source runs",
        ),
        (
            "distillation_execution_checkpoints",
            "SELECT COUNT(*) FROM distillation_execution_checkpoints "
            "WHERE status = 'PENDING'",
            "distillation executions",
        ),
        (
            "source_run_video_executions",
            "SELECT COUNT(*) FROM source_run_video_executions "
            "WHERE state IN ('PENDING','WAITING','DEFERRED')",
            "source-run child executions",
        ),
        (
            "reports",
            "SELECT COUNT(*) FROM reports WHERE status = 'PENDING'",
            "pending reports",
        ),
    )
    active: list[str] = []
    for table, sql, label in checks:
        if not _table_exists(connection, table):
            continue
        count = int(connection.execute(sql).fetchone()[0])
        if count:
            active.append(f"{label}: {count}")
    return tuple(active)


def _database_facts(connection: sqlite3.Connection) -> tuple[int, int]:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity != ("ok",):
        raise CoreBackupError("SQLite integrity check failed")
    foreign_keys = tuple(connection.execute("PRAGMA foreign_key_check"))
    if foreign_keys:
        raise CoreBackupError("SQLite foreign-key check failed")
    schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if schema_version <= 0:
        raise CoreBackupError("SQLite schema version is invalid")
    reasons = _active_work_reasons(connection)
    if reasons:
        raise CoreBackupError(
            "backup requires a quiescent core state; active " + ", ".join(reasons)
        )
    vault_count = 0
    if _table_exists(connection, "artifacts"):
        vault_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM artifacts "
                "WHERE storage_root='VAULT' AND deleted_at IS NULL"
            ).fetchone()[0]
        )
    return schema_version, vault_count


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _snapshot_database(live_database: Path, destination: Path) -> None:
    if live_database.is_symlink() or not live_database.is_file():
        raise CoreBackupError("state database is unavailable or unsafe")
    source = sqlite3.connect(live_database, timeout=5.0)
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
        target.commit()
    except sqlite3.Error as error:
        raise CoreBackupError("SQLite backup snapshot failed") from error
    finally:
        target.close()
        source.close()


def _artifact_rows(connection: sqlite3.Connection) -> tuple[sqlite3.Row, ...]:
    if not _table_exists(connection, "artifacts"):
        return ()
    connection.row_factory = sqlite3.Row
    rows = tuple(
        connection.execute(
            "SELECT artifact_id, kind, relative_path, content_hash "
            "FROM artifacts "
            "WHERE storage_root='DATA' AND deleted_at IS NULL "
            "ORDER BY relative_path, artifact_id"
        )
    )
    seen: set[str] = set()
    for row in rows:
        relative = _safe_archive_path(str(row["relative_path"]))
        if relative == "state.sqlite" or relative in seen:
            raise CoreBackupError("DATA artifact paths are ambiguous")
        seen.add(relative)
    return rows


def _manifest(
    *,
    created_at: datetime,
    app_version: str,
    schema_version: int,
    database_hash: str,
    database_bytes: int,
    artifacts: list[dict[str, object]],
    excluded_vault_artifact_count: int,
) -> dict[str, object]:
    return {
        "format": _BACKUP_FORMAT,
        "created_at": format_utc_datetime(created_at),
        "app_version": app_version,
        "schema_version": schema_version,
        "core_scope": list(_CORE_SCOPE),
        "database": {
            "archive_path": _DATABASE_ARCHIVE_PATH,
            "sha256": database_hash,
            "bytes": database_bytes,
        },
        "artifacts": artifacts,
        "excluded_external": {
            "vault_artifact_count": excluded_vault_artifact_count,
            "vault_included": False,
        },
    }


def _parse_manifest(body: bytes) -> dict[str, object]:
    if len(body) > _MAX_MANIFEST_BYTES:
        raise CoreBackupError("backup manifest is too large")
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CoreBackupError("backup manifest is invalid") from error
    if not isinstance(value, dict):
        raise CoreBackupError("backup manifest must be an object")
    required = {
        "format",
        "created_at",
        "app_version",
        "schema_version",
        "core_scope",
        "database",
        "artifacts",
        "excluded_external",
    }
    if set(value) != required or value.get("format") != _BACKUP_FORMAT:
        raise CoreBackupError("backup manifest format is unsupported")
    if value.get("core_scope") != list(_CORE_SCOPE):
        raise CoreBackupError("backup core scope is unsupported")
    return value


def _manifest_datetime(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CoreBackupError("backup timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as error:
        raise CoreBackupError("backup timestamp is invalid") from error
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise CoreBackupError("backup timestamp is not UTC")
    return parsed


def _descriptor(value: object, *, label: str) -> tuple[str, str, int]:
    if not isinstance(value, dict) or set(value) != {
        "archive_path",
        "sha256",
        "bytes",
    }:
        raise CoreBackupError(f"{label} descriptor is invalid")
    archive_path = value.get("archive_path")
    digest = value.get("sha256")
    size = value.get("bytes")
    if (
        not isinstance(archive_path, str)
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
        or not isinstance(size, int)
        or isinstance(size, bool)
        or size < 0
    ):
        raise CoreBackupError(f"{label} descriptor is invalid")
    return _safe_archive_path(archive_path), digest, size


def _hash_zip_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    expected_hash: str,
    expected_size: int,
) -> None:
    if info.file_size != expected_size:
        raise CoreBackupError("backup file size does not match its manifest")
    mode = info.external_attr >> 16
    if mode and stat.S_ISLNK(mode):
        raise CoreBackupError("backup contains a symbolic link")
    with archive.open(info, "r") as source:
        digest, size = _sha256_stream(source)
    if size != expected_size or digest != expected_hash:
        raise CoreBackupError("backup file checksum does not match its manifest")


class CoreBackupService:
    """Create and verify a complete Intelligence-owned core-data backup archive."""

    def __init__(
        self,
        *,
        data_root: Path,
        app_version: str,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._data_root = data_root.resolve(strict=False)
        self._database = self._data_root / "state.sqlite"
        self._app_version = app_version
        self._now = now or (lambda: datetime.now(UTC))

    def create_backup(self, destination: Path) -> CoreBackupResult:
        now = self._now()
        if now.tzinfo is None or now.utcoffset() != UTC.utcoffset(now):
            raise CoreBackupError("backup clock must return UTC")
        if not self._data_root.is_dir() or self._data_root.is_symlink():
            raise CoreBackupError("data root is unavailable or unsafe")

        parent = destination.parent.resolve(strict=True)
        resolved_destination = (parent / destination.name).resolve(strict=False)
        if destination.name in {"", ".", ".."}:
            raise CoreBackupError("backup destination filename is invalid")
        if resolved_destination.is_relative_to(self._data_root):
            raise CoreBackupError("backup destination must be outside the live data root")
        if resolved_destination.exists():
            raise CoreBackupError("backup destination already exists")

        with tempfile.TemporaryDirectory(prefix=".intelligence-backup-", dir=parent) as work:
            work_root = Path(work)
            snapshot = work_root / "state.sqlite"
            temporary_archive = work_root / "backup.partial"
            _snapshot_database(self._database, snapshot)

            snapshot_connection = sqlite3.connect(snapshot)
            snapshot_connection.row_factory = sqlite3.Row
            try:
                schema_version, vault_count = _database_facts(snapshot_connection)
                rows = _artifact_rows(snapshot_connection)
            finally:
                snapshot_connection.close()

            with snapshot.open("rb") as database_source:
                database_hash, database_bytes = _sha256_stream(database_source)
            total_bytes = database_bytes
            artifacts: list[dict[str, object]] = []

            try:
                with zipfile.ZipFile(
                    temporary_archive,
                    "w",
                    compression=zipfile.ZIP_DEFLATED,
                    compresslevel=6,
                    allowZip64=True,
                ) as archive:
                    with snapshot.open("rb") as database_source:
                        with archive.open(
                            _DATABASE_ARCHIVE_PATH, "w", force_zip64=True
                        ) as database_target:
                            while True:
                                chunk = database_source.read(_CHUNK)
                                if not chunk:
                                    break
                                database_target.write(chunk)
                    for row in rows:
                        relative = _safe_archive_path(str(row["relative_path"]))
                        archive_path = f"data/{relative}"
                        with _open_regular_under(self._data_root, relative) as source:
                            digest = hashlib.sha256()
                            size = 0
                            with archive.open(archive_path, "w", force_zip64=True) as target:
                                while True:
                                    chunk = source.read(_CHUNK)
                                    if not chunk:
                                        break
                                    size += len(chunk)
                                    if size > _MAX_TOTAL_UNCOMPRESSED_BYTES:
                                        raise CoreBackupError(
                                            "backup artifact exceeds the supported V1 size limit"
                                        )
                                    digest.update(chunk)
                                    target.write(chunk)
                        total_bytes += size
                        if total_bytes > _MAX_TOTAL_UNCOMPRESSED_BYTES:
                            raise CoreBackupError(
                                "backup exceeds the supported V1 size limit"
                            )
                        expected = str(row["content_hash"])
                        if digest.hexdigest() != expected:
                            raise CoreBackupError(
                                "DATA artifact checksum disagrees with SQLite authority"
                            )
                        artifacts.append(
                            {
                                "artifact_id": str(row["artifact_id"]),
                                "kind": str(row["kind"]),
                                "relative_path": relative,
                                "archive_path": archive_path,
                                "sha256": expected,
                                "bytes": size,
                            }
                        )

                    manifest = _manifest(
                        created_at=now,
                        app_version=self._app_version,
                        schema_version=schema_version,
                        database_hash=database_hash,
                        database_bytes=database_bytes,
                        artifacts=artifacts,
                        excluded_vault_artifact_count=vault_count,
                    )
                    archive.writestr(
                        _MANIFEST_PATH,
                        json.dumps(
                            manifest,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8"),
                    )
            except (OSError, sqlite3.Error, zipfile.BadZipFile) as error:
                raise CoreBackupError("backup archive creation failed") from error

            inspection = self.inspect_backup(temporary_archive)
            with temporary_archive.open("rb") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary_archive, resolved_destination)
            _fsync_directory(parent)

        return CoreBackupResult(resolved_destination, inspection)

    def inspect_backup(self, archive_path: Path) -> CoreBackupInspection:
        if archive_path.is_symlink() or not archive_path.is_file():
            raise CoreBackupError("backup archive is unavailable or unsafe")

        try:
            with zipfile.ZipFile(archive_path, "r", allowZip64=True) as archive:
                infos = archive.infolist()
                if len(infos) > _MAX_ARCHIVE_FILES:
                    raise CoreBackupError("backup contains too many files")
                names = [info.filename for info in infos]
                if len(names) != len(set(names)):
                    raise CoreBackupError("backup contains duplicate paths")
                for name in names:
                    _safe_archive_path(name)
                by_name = {info.filename: info for info in infos}
                manifest_info = by_name.get(_MANIFEST_PATH)
                if manifest_info is None:
                    raise CoreBackupError("backup manifest is missing")
                if manifest_info.file_size > _MAX_MANIFEST_BYTES:
                    raise CoreBackupError("backup manifest is too large")
                manifest = _parse_manifest(archive.read(manifest_info))

                app_version = manifest.get("app_version")
                if not isinstance(app_version, str) or not app_version.strip():
                    raise CoreBackupError("backup app version is invalid")

                schema_version = manifest.get("schema_version")
                if (
                    not isinstance(schema_version, int)
                    or isinstance(schema_version, bool)
                    or schema_version <= 0
                ):
                    raise CoreBackupError("backup schema version is invalid")
                created_at = _manifest_datetime(manifest.get("created_at"))

                database_path, database_hash, database_bytes = _descriptor(
                    manifest.get("database"), label="database"
                )
                if database_path != _DATABASE_ARCHIVE_PATH:
                    raise CoreBackupError("backup database path is invalid")

                artifacts_value = manifest.get("artifacts")
                if not isinstance(artifacts_value, list):
                    raise CoreBackupError("backup artifact manifest is invalid")

                expected_names = {_MANIFEST_PATH, database_path}
                artifact_descriptors: dict[str, dict[str, object]] = {}
                total_bytes = database_bytes
                for value in artifacts_value:
                    if not isinstance(value, dict) or set(value) != {
                        "artifact_id",
                        "kind",
                        "relative_path",
                        "archive_path",
                        "sha256",
                        "bytes",
                    }:
                        raise CoreBackupError("backup artifact descriptor is invalid")
                    artifact_id = value.get("artifact_id")
                    kind = value.get("kind")
                    relative = value.get("relative_path")
                    if (
                        not isinstance(artifact_id, str)
                        or not artifact_id
                        or not isinstance(kind, str)
                        or not kind
                        or not isinstance(relative, str)
                    ):
                        raise CoreBackupError("backup artifact descriptor is invalid")
                    archive_member, digest, size = _descriptor(
                        {
                            "archive_path": value.get("archive_path"),
                            "sha256": value.get("sha256"),
                            "bytes": value.get("bytes"),
                        },
                        label="artifact",
                    )
                    safe_relative = _safe_archive_path(relative)
                    if archive_member != f"data/{safe_relative}":
                        raise CoreBackupError("backup artifact path binding is invalid")
                    if archive_member in expected_names:
                        raise CoreBackupError("backup artifact path is duplicated")
                    expected_names.add(archive_member)
                    total_bytes += size
                    if total_bytes > _MAX_TOTAL_UNCOMPRESSED_BYTES:
                        raise CoreBackupError("backup exceeds the supported V1 size limit")
                    artifact_descriptors[archive_member] = {
                        **value,
                        "relative_path": safe_relative,
                        "sha256": digest,
                        "bytes": size,
                    }

                if set(names) != expected_names:
                    raise CoreBackupError("backup contains unmanifested or missing files")

                database_info = by_name[database_path]
                _hash_zip_member(
                    archive,
                    database_info,
                    expected_hash=database_hash,
                    expected_size=database_bytes,
                )
                for name, value in artifact_descriptors.items():
                    _hash_zip_member(
                        archive,
                        by_name[name],
                        expected_hash=str(value["sha256"]),
                        expected_size=int(value["bytes"]),
                    )

                with tempfile.TemporaryDirectory(prefix=".intelligence-inspect-") as work:
                    database_copy = Path(work) / "state.sqlite"
                    with archive.open(database_info, "r") as source:
                        with database_copy.open("wb") as target:
                            while True:
                                chunk = source.read(_CHUNK)
                                if not chunk:
                                    break
                                target.write(chunk)

                    connection = sqlite3.connect(database_copy)
                    connection.row_factory = sqlite3.Row
                    try:
                        actual_schema, vault_count = _database_facts(connection)
                        rows = _artifact_rows(connection)
                    finally:
                        connection.close()

                if actual_schema != schema_version:
                    raise CoreBackupError("backup schema version disagrees with its database")

                live_schema = self._live_schema_version()
                if live_schema is not None and schema_version != live_schema:
                    raise CoreBackupError(
                        "backup schema version is incompatible with the current workspace"
                    )

                expected_artifacts = {
                    (
                        str(row["artifact_id"]),
                        str(row["kind"]),
                        _safe_archive_path(str(row["relative_path"])),
                        str(row["content_hash"]),
                    )
                    for row in rows
                }
                manifest_artifacts = {
                    (
                        str(value["artifact_id"]),
                        str(value["kind"]),
                        str(value["relative_path"]),
                        str(value["sha256"]),
                    )
                    for value in artifact_descriptors.values()
                }
                if manifest_artifacts != expected_artifacts:
                    raise CoreBackupError(
                        "backup artifact manifest disagrees with SQLite authority"
                    )

                external = manifest.get("excluded_external")
                if (
                    not isinstance(external, dict)
                    or set(external) != {"vault_artifact_count", "vault_included"}
                    or external.get("vault_included") is not False
                    or not isinstance(external.get("vault_artifact_count"), int)
                    or isinstance(external.get("vault_artifact_count"), bool)
                    or int(external["vault_artifact_count"]) != vault_count
                ):
                    raise CoreBackupError("backup external-scope declaration is invalid")

                return CoreBackupInspection(
                    format_version=_BACKUP_FORMAT,
                    created_at=created_at,
                    schema_version=schema_version,
                    artifact_count=len(artifact_descriptors),
                    excluded_vault_artifact_count=vault_count,
                    total_bytes=total_bytes,
                    core_scope=_CORE_SCOPE,
                )
        except zipfile.BadZipFile as error:
            raise CoreBackupError("backup archive is not a valid ZIP container") from error

    def stage_restore(
        self,
        archive_path: Path,
        *,
        staging_parent: Path,
    ) -> StagedCoreRestore:
        """Validate fully, then extract to staging without touching live data."""

        inspection = self.inspect_backup(archive_path)
        parent = staging_parent.resolve(strict=True)
        if parent.is_symlink() or not parent.is_dir():
            raise CoreBackupError("restore staging parent is unsafe")
        staging_root = Path(
            tempfile.mkdtemp(prefix=".intelligence-restore-", dir=parent)
        )
        staged_data = staging_root / "data"
        staged_data.mkdir(mode=0o700)
        try:
            with zipfile.ZipFile(archive_path, "r", allowZip64=True) as archive:
                manifest = _parse_manifest(archive.read(_MANIFEST_PATH))
                database_path, _, _ = _descriptor(
                    manifest.get("database"), label="database"
                )
                members = [database_path]
                for value in manifest["artifacts"]:  # type: ignore[index]
                    assert isinstance(value, dict)
                    member, _, _ = _descriptor(
                        {
                            "archive_path": value.get("archive_path"),
                            "sha256": value.get("sha256"),
                            "bytes": value.get("bytes"),
                        },
                        label="artifact",
                    )
                    members.append(member)

                for member in members:
                    relative = _safe_relative_path(member)
                    if relative.parts[0] != "data":
                        raise CoreBackupError("restore member escapes the data root")
                    local_relative = Path(*relative.parts[1:])
                    target = staged_data / local_relative
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    with archive.open(member, "r") as source, target.open("xb") as output:
                        while True:
                            chunk = source.read(_CHUNK)
                            if not chunk:
                                break
                            output.write(chunk)
            self._verify_staged_data(staged_data, inspection)
            return StagedCoreRestore(staging_root, staged_data, inspection)
        except BaseException:
            for root, directories, files in os.walk(staging_root, topdown=False):
                for filename in files:
                    Path(root, filename).unlink(missing_ok=True)
                for directory in directories:
                    Path(root, directory).rmdir()
            staging_root.rmdir()
            raise

    def _live_schema_version(self) -> int | None:
        if not self._database.is_file() or self._database.is_symlink():
            return None
        connection = sqlite3.connect(self._database)
        try:
            return int(connection.execute("PRAGMA user_version").fetchone()[0])
        finally:
            connection.close()

    @staticmethod
    def _verify_staged_data(
        data_root: Path,
        inspection: CoreBackupInspection,
    ) -> None:
        database = data_root / "state.sqlite"
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        try:
            schema_version, _vault_count = _database_facts(connection)
            rows = _artifact_rows(connection)
        finally:
            connection.close()
        if schema_version != inspection.schema_version:
            raise CoreBackupError("staged restore schema is invalid")
        if len(rows) != inspection.artifact_count:
            raise CoreBackupError("staged restore artifact count is invalid")
        for row in rows:
            relative = _safe_archive_path(str(row["relative_path"]))
            with _open_regular_under(data_root, relative) as source:
                digest, _size = _sha256_stream(source)
            if digest != str(row["content_hash"]):
                raise CoreBackupError("staged restore artifact checksum is invalid")


__all__ = [
    "CoreBackupError",
    "CoreBackupInspection",
    "CoreBackupResult",
    "CoreBackupService",
    "StagedCoreRestore",
]
