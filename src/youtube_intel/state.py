"""SQLite state repository with explicit migrations and transaction boundaries."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import cast

from youtube_intel.domain import (
    Availability,
    DiscoveryBatch,
    DiscoveryCursor,
    ErrorCode,
    JobStatus,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    VideoMetadata,
    transition_pipeline,
)


class StateStoreError(Exception):
    """Base error for safe state-store failures."""


class MigrationError(StateStoreError):
    """Raised when migration history or application is invalid."""


class ConcurrencyConflict(StateStoreError):
    """Raised when an expected-state compare-and-swap is stale."""


class IntegrityConflict(StateStoreError):
    """Raised when a repository uniqueness or integrity rule is violated."""


class LeaseConflict(StateStoreError):
    """Raised when a worker no longer owns a live lease."""


class JobType(str, Enum):
    CHANNEL_DISCOVERY = "CHANNEL_DISCOVERY"
    VIDEO_STAGE = "VIDEO_STAGE"
    WEEKLY_REPORT = "WEEKLY_REPORT"


class JobAttemptOutcome(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    RETRY_PENDING = "RETRY_PENDING"
    FAILED_FINAL = "FAILED_FINAL"
    LEASE_EXPIRED = "LEASE_EXPIRED"


class ArtifactKind(str, Enum):
    SUBTITLE_SOURCE = "subtitle_source"
    TRANSCRIPT_CANONICAL = "transcript_canonical"
    AUDIO = "audio"
    SCORING_RAW = "scoring_raw"
    SCORING_STRUCTURED = "scoring_structured"
    ANALYSIS_RAW = "analysis_raw"
    ANALYSIS_STRUCTURED = "analysis_structured"
    VIDEO_NOTE = "video_note"
    WEEKLY_REPORT = "weekly_report"


class StorageRoot(str, Enum):
    DATA = "DATA"
    VAULT = "VAULT"


class RetentionClass(str, Enum):
    EPHEMERAL_AUDIO = "EPHEMERAL_AUDIO"
    RAW_RESPONSE_30D = "RAW_RESPONSE_30D"
    LONG_LIVED = "LONG_LIVED"


class ProviderCallStatus(str, Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_FINAL = "FAILED_FINAL"


class ReportStatus(str, Enum):
    PENDING = "PENDING"
    WRITTEN = "WRITTEN"


@dataclass(frozen=True, slots=True)
class _Migration:
    version: int
    name: str
    sql: str
    checksum: str


@dataclass(frozen=True, slots=True)
class SchemaVersion:
    version: int
    name: str
    checksum: str
    applied_at: datetime


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    foreign_keys: bool
    busy_timeout_ms: int
    synchronous: str
    journal_mode: str
    read_uncommitted: bool


@dataclass(frozen=True, slots=True)
class ChannelCursorRecord:
    channel_id: str
    last_checked_at: datetime | None
    latest_published_at: datetime | None
    latest_video_id: str | None
    provider_cursor: str | None
    last_error_code: str | None
    last_error_message: str | None
    revision: int
    updated_at: datetime

    def as_discovery_cursor(self) -> DiscoveryCursor:
        return DiscoveryCursor(
            channel_id=self.channel_id,
            last_checked_at=self.last_checked_at,
            latest_published_at=self.latest_published_at,
            latest_video_id=self.latest_video_id,
            provider_cursor=self.provider_cursor,
        )


@dataclass(frozen=True, slots=True)
class VideoRecord:
    video_id: str
    channel_id: str
    channel_name: str | None
    title: str | None
    description: str | None
    source_url: str | None
    published_at: datetime | None
    duration_seconds: int | None
    default_language: str | None
    available_languages: tuple[str, ...]
    live_status: LiveStatus | None
    availability: Availability | None
    pipeline_status: PipelineStatus
    pipeline_version: str
    score: float | None
    should_summarize: bool | None
    discovered_at: datetime
    updated_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class JobRecord:
    job_id: str
    scope_key: str
    video_id: str | None
    job_type: JobType
    target_stage: ProcessingStage
    pipeline_version: str
    status: JobStatus
    attempt_count: int
    max_attempts: int
    available_at: datetime
    lease_owner: str | None
    lease_until: datetime | None
    last_error_code: str | None
    last_error_message: str | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class JobAttemptRecord:
    attempt_id: int
    job_id: str
    attempt_number: int
    lease_owner: str
    started_at: datetime
    lease_until: datetime
    finished_at: datetime | None
    outcome: JobAttemptOutcome | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class ArtifactWrite:
    artifact_id: str
    artifact_key: str
    video_id: str | None
    job_id: str | None
    kind: ArtifactKind
    storage_root: StorageRoot
    relative_path: str
    content_hash: str
    provider: str | None
    model: str | None
    producer_version: str
    retention_class: RetentionClass
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_id: str
    artifact_key: str
    video_id: str | None
    job_id: str | None
    kind: ArtifactKind
    storage_root: StorageRoot
    relative_path: str
    content_hash: str
    provider: str | None
    model: str | None
    producer_version: str
    retention_class: RetentionClass
    created_at: datetime
    expires_at: datetime | None
    deleted_at: datetime | None


@dataclass(frozen=True, slots=True)
class ProviderCallRequest:
    operation: str
    normalized_input_hash: str
    provider: str
    model: str | None
    prompt_version: str | None
    schema_version: str | None
    deterministic_artifact_key: str

    @property
    def request_hash(self) -> str:
        return build_provider_request_hash(
            operation=self.operation,
            normalized_input_hash=self.normalized_input_hash,
            provider=self.provider,
            model=self.model,
            prompt_version=self.prompt_version,
            schema_version=self.schema_version,
        )


@dataclass(frozen=True, slots=True)
class VerifiedArtifact:
    artifact_key: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class ProviderCallRecord:
    request_hash: str
    operation: str
    provider: str
    model: str | None
    prompt_version: str | None
    schema_version: str | None
    status: ProviderCallStatus
    reservation_owner: str | None
    lease_until: datetime | None
    available_at: datetime
    attempt_count: int
    response_artifact_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    cost_microusd: int | None
    last_error_code: str | None
    last_error_message: str | None
    started_at: datetime
    finished_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProviderReservation:
    record: ProviderCallRecord
    acquired: bool
    recovered_from_artifact: bool


@dataclass(frozen=True, slots=True)
class ProviderCallCompletion:
    request_hash: str
    response_artifact_id: str
    input_tokens: int | None
    output_tokens: int | None
    cost_microusd: int | None


@dataclass(frozen=True, slots=True)
class ScoringSummaryWrite:
    """Final application decision persisted only with SCORING stage completion."""

    score: float
    should_summarize: bool

    def __post_init__(self) -> None:
        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, (int, float))
            or not math.isfinite(self.score)
            or not 0 <= self.score <= 10
        ):
            msg = "score must be a finite value in 0..10"
            raise ValueError(msg)
        if not isinstance(self.should_summarize, bool):
            msg = "should_summarize must be a bool"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ReportWrite:
    report_id: str
    timezone: str
    iso_year: int
    iso_week: int
    relative_path: str | None
    content_hash: str | None
    status: ReportStatus


@dataclass(frozen=True, slots=True)
class ReportRecord:
    report_id: str
    timezone: str
    iso_year: int
    iso_week: int
    report_type: str
    relative_path: str | None
    content_hash: str | None
    status: ReportStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WeeklyCandidateRecord:
    """Repository-selected inputs that a weekly report must verify locally."""

    video: VideoRecord
    score_artifact: ArtifactRecord
    analysis_artifact: ArtifactRecord | None
    note_artifact: ArtifactRecord


@dataclass(frozen=True, slots=True)
class StageCompletionResult:
    job: JobRecord
    video: VideoRecord
    artifacts: tuple[ArtifactRecord, ...]
    provider_call: ProviderCallRecord | None


def format_utc_datetime(value: datetime) -> str:
    """Return ADR-003's fixed-width UTC RFC 3339 representation."""

    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        msg = "value must be a UTC datetime"
        raise ValueError(msg)
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_utc_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.removesuffix("Z") + "+00:00")


def _latest_weekly_artifact(
    connection: sqlite3.Connection, video_id: str, kind: ArtifactKind
) -> sqlite3.Row | None:
    return cast(
        sqlite3.Row | None,
        connection.execute(
            "SELECT * FROM artifacts WHERE video_id = :video_id AND kind = :kind "
            "AND storage_root = :root AND deleted_at IS NULL "
            "ORDER BY created_at DESC, artifact_id ASC LIMIT 1",
            {
                "video_id": video_id,
                "kind": kind.value,
                "root": StorageRoot.DATA.value,
            },
        ).fetchone(),
    )


def _safe_error_message(value: str) -> str:
    first_line = value.splitlines()[0] if value.splitlines() else ""
    redacted = re.sub(
        r"(?i)\bBearer\s+\S+",
        "Bearer [REDACTED]",
        first_line,
    )
    redacted = re.sub(
        r"(?i)\b(api[_-]?key|token|secret|authorization)\b\s*[:=]?\s*\S+",
        r"\1=[REDACTED]",
        redacted,
    )
    redacted = re.sub(r"(?<!:)\b/(?:[^\s]+)", "[PATH]", redacted)
    return " ".join(redacted.split())[:500]


def _validate_sha256(value: str, *, field_name: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        msg = f"{field_name} must be a lowercase SHA-256 hexadecimal value"
        raise ValueError(msg)


def _validate_relative_path(value: str) -> None:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or ".." in path.parts
        or not path.parts
        or value.startswith("~")
        or re.match(r"^[A-Za-z]:", value) is not None
    ):
        msg = "artifact and report paths must be safe relative paths"
        raise ValueError(msg)


def build_provider_request_hash(
    *,
    operation: str,
    normalized_input_hash: str,
    provider: str,
    model: str | None,
    prompt_version: str | None,
    schema_version: str | None,
) -> str:
    """Build the canonical ADR-003 provider-call cache key."""

    if not operation.strip() or not provider.strip():
        msg = "provider call operation and provider must be non-empty"
        raise ValueError(msg)
    _validate_sha256(normalized_input_hash, field_name="normalized_input_hash")
    canonical = json.dumps(
        [
            operation,
            normalized_input_hash,
            provider,
            model,
            prompt_version,
            schema_version,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _processing_stage_for_transition(
    current: PipelineStatus,
    target: PipelineStatus,
) -> ProcessingStage:
    if target in {
        PipelineStatus.METADATA_READY,
        PipelineStatus.DEFERRED,
        PipelineStatus.SKIPPED_DURATION_LIMIT,
    }:
        return ProcessingStage.METADATA
    if target is PipelineStatus.TRANSCRIPT_READY:
        return ProcessingStage.TRANSCRIPT
    if target in {PipelineStatus.SCORED, PipelineStatus.LOW_VALUE_READY}:
        return ProcessingStage.SCORING
    if target is PipelineStatus.ANALYSIS_READY:
        return ProcessingStage.ANALYSIS
    if target is PipelineStatus.NOTE_WRITTEN:
        return ProcessingStage.NOTE_WRITE
    if target is PipelineStatus.COMPLETE:
        return (
            ProcessingStage.SCORING
            if current is PipelineStatus.LOW_VALUE_READY
            else ProcessingStage.NOTE_WRITE
        )
    msg = "pipeline transition has no processing stage"
    raise ValueError(msg)


def _migration_statements(sql: str) -> Iterator[str]:
    buffer = ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                yield statement
            buffer = ""
    if buffer.strip():
        msg = "migration contains an incomplete SQL statement"
        raise MigrationError(msg)


@contextmanager
def _immediate_transaction(connection: sqlite3.Connection) -> Iterator[None]:
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        connection.rollback()
        raise
    else:
        connection.commit()


class SQLiteStateRepository:
    """Owns the approved SQLite schema and repository transaction semantics."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path)

    def _inject_failure(self, point: str) -> None:
        """Test seam for proving transaction rollback at named boundaries."""

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._database_path,
            isolation_level=None,
            timeout=5.0,
        )
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute("PRAGMA synchronous = NORMAL")
            settings = self._read_database_settings(connection)
            if (
                not settings.foreign_keys
                or settings.busy_timeout_ms != 5000
                or settings.synchronous != "NORMAL"
                or settings.read_uncommitted
            ):
                msg = "required SQLite connection settings could not be verified"
                raise StateStoreError(msg)
        except BaseException:
            connection.close()
            raise
        return connection

    @staticmethod
    def _read_database_settings(connection: sqlite3.Connection) -> DatabaseSettings:
        synchronous_codes = {0: "OFF", 1: "NORMAL", 2: "FULL", 3: "EXTRA"}
        foreign_keys = int(connection.execute("PRAGMA foreign_keys").fetchone()[0])
        busy_timeout = int(connection.execute("PRAGMA busy_timeout").fetchone()[0])
        synchronous = int(connection.execute("PRAGMA synchronous").fetchone()[0])
        journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
        read_uncommitted = int(
            connection.execute("PRAGMA read_uncommitted").fetchone()[0]
        )
        return DatabaseSettings(
            foreign_keys=foreign_keys == 1,
            busy_timeout_ms=busy_timeout,
            synchronous=synchronous_codes.get(synchronous, f"UNKNOWN-{synchronous}"),
            journal_mode=journal_mode.upper(),
            read_uncommitted=read_uncommitted == 1,
        )

    def _load_migrations(self) -> tuple[_Migration, ...]:
        name = "001_initial.sql"
        sql_bytes = (
            resources.files("youtube_intel")
            .joinpath("migrations", name)
            .read_bytes()
        )
        return (
            _Migration(
                version=1,
                name=name,
                sql=sql_bytes.decode("utf-8"),
                checksum=hashlib.sha256(sql_bytes).hexdigest(),
            ),
        )

    @staticmethod
    def _history_rows(connection: sqlite3.Connection) -> tuple[sqlite3.Row, ...]:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("schema_migrations",),
        ).fetchone()
        if table_exists is None:
            return ()
        return tuple(
            connection.execute(
                "SELECT version, name, checksum, applied_at "
                "FROM schema_migrations ORDER BY version"
            )
        )

    @staticmethod
    def _verify_history(
        connection: sqlite3.Connection,
        migrations: tuple[_Migration, ...],
    ) -> tuple[sqlite3.Row, ...]:
        try:
            rows = SQLiteStateRepository._history_rows(connection)
            user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        except sqlite3.Error as error:
            msg = "migration history mismatch: unreadable migration metadata"
            raise MigrationError(msg) from error

        if len(rows) > len(migrations):
            msg = "migration history mismatch: database version is unsupported"
            raise MigrationError(msg)
        for index, row in enumerate(rows):
            migration = migrations[index]
            if (
                row["version"] != migration.version
                or row["name"] != migration.name
                or row["checksum"] != migration.checksum
            ):
                msg = "migration history mismatch: version, name, or checksum differs"
                raise MigrationError(msg)
        expected_user_version = int(rows[-1]["version"]) if rows else 0
        if user_version != expected_user_version:
            msg = "migration history mismatch: PRAGMA user_version differs"
            raise MigrationError(msg)
        return rows

    def initialize(self, *, now: datetime) -> SchemaVersion:
        applied_at = format_utc_datetime(now)
        migrations = self._load_migrations()
        connection = self._connect()
        try:
            journal_mode = str(
                connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            )
            if journal_mode.upper() != "WAL":
                msg = "file database did not enable WAL journal mode"
                raise MigrationError(msg)
            rows = self._verify_history(connection, migrations)
            for migration in migrations[len(rows) :]:
                try:
                    with _immediate_transaction(connection):
                        for statement in _migration_statements(migration.sql):
                            connection.execute(statement)
                        connection.execute(
                            "INSERT INTO schema_migrations "
                            "(version, name, checksum, applied_at) "
                            "VALUES (:version, :name, :checksum, :applied_at)",
                            {
                                "version": migration.version,
                                "name": migration.name,
                                "checksum": migration.checksum,
                                "applied_at": applied_at,
                            },
                        )
                        connection.execute(
                            f"PRAGMA user_version = {migration.version}"
                        )
                except (sqlite3.Error, MigrationError) as error:
                    msg = f"failed to apply migration {migration.version}"
                    raise MigrationError(msg) from error
            self._verify_history(connection, migrations)
            version = self._schema_version(connection)
            if version is None:
                msg = "migration history mismatch: no applied migration"
                raise MigrationError(msg)
            return version
        finally:
            connection.close()

    @staticmethod
    def _schema_version(connection: sqlite3.Connection) -> SchemaVersion | None:
        rows = SQLiteStateRepository._history_rows(connection)
        if not rows:
            return None
        row = rows[-1]
        return SchemaVersion(
            version=int(row["version"]),
            name=str(row["name"]),
            checksum=str(row["checksum"]),
            applied_at=_parse_utc_datetime(str(row["applied_at"])),
        )

    def schema_version(self) -> SchemaVersion | None:
        connection = self._connect()
        try:
            return self._schema_version(connection)
        finally:
            connection.close()

    def database_settings(self) -> DatabaseSettings:
        connection = self._connect()
        try:
            return self._read_database_settings(connection)
        finally:
            connection.close()

    @staticmethod
    def _optional_datetime(value: object) -> datetime | None:
        return None if value is None else _parse_utc_datetime(str(value))

    @staticmethod
    def _cursor_from_row(row: sqlite3.Row) -> ChannelCursorRecord:
        return ChannelCursorRecord(
            channel_id=str(row["channel_id"]),
            last_checked_at=SQLiteStateRepository._optional_datetime(
                row["last_checked_at"]
            ),
            latest_published_at=SQLiteStateRepository._optional_datetime(
                row["latest_published_at"]
            ),
            latest_video_id=row["latest_video_id"],
            provider_cursor=row["provider_cursor"],
            last_error_code=row["last_error_code"],
            last_error_message=row["last_error_message"],
            revision=int(row["revision"]),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    @staticmethod
    def _video_from_row(row: sqlite3.Row) -> VideoRecord:
        languages = json.loads(str(row["available_languages_json"]))
        if not isinstance(languages, list) or not all(
            isinstance(language, str) for language in languages
        ):
            msg = "stored available languages are invalid"
            raise StateStoreError(msg)
        return VideoRecord(
            video_id=str(row["video_id"]),
            channel_id=str(row["channel_id"]),
            channel_name=row["channel_name"],
            title=row["title"],
            description=row["description"],
            source_url=row["source_url"],
            published_at=SQLiteStateRepository._optional_datetime(
                row["published_at"]
            ),
            duration_seconds=row["duration_seconds"],
            default_language=row["default_language"],
            available_languages=tuple(languages),
            live_status=(
                None if row["live_status"] is None else LiveStatus(row["live_status"])
            ),
            availability=(
                None
                if row["availability"] is None
                else Availability(row["availability"])
            ),
            pipeline_status=PipelineStatus(row["pipeline_status"]),
            pipeline_version=str(row["pipeline_version"]),
            score=row["score"],
            should_summarize=(
                None
                if row["should_summarize"] is None
                else bool(row["should_summarize"])
            ),
            discovered_at=_parse_utc_datetime(str(row["discovered_at"])),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
            completed_at=SQLiteStateRepository._optional_datetime(row["completed_at"]),
        )

    @staticmethod
    def _job_from_row(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            job_id=str(row["job_id"]),
            scope_key=str(row["scope_key"]),
            video_id=row["video_id"],
            job_type=JobType(row["job_type"]),
            target_stage=ProcessingStage(row["target_stage"]),
            pipeline_version=str(row["pipeline_version"]),
            status=JobStatus(row["status"]),
            attempt_count=int(row["attempt_count"]),
            max_attempts=int(row["max_attempts"]),
            available_at=_parse_utc_datetime(str(row["available_at"])),
            lease_owner=row["lease_owner"],
            lease_until=SQLiteStateRepository._optional_datetime(row["lease_until"]),
            last_error_code=row["last_error_code"],
            last_error_message=row["last_error_message"],
            created_at=_parse_utc_datetime(str(row["created_at"])),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
            finished_at=SQLiteStateRepository._optional_datetime(row["finished_at"]),
        )

    @staticmethod
    def _attempt_from_row(row: sqlite3.Row) -> JobAttemptRecord:
        return JobAttemptRecord(
            attempt_id=int(row["attempt_id"]),
            job_id=str(row["job_id"]),
            attempt_number=int(row["attempt_number"]),
            lease_owner=str(row["lease_owner"]),
            started_at=_parse_utc_datetime(str(row["started_at"])),
            lease_until=_parse_utc_datetime(str(row["lease_until"])),
            finished_at=SQLiteStateRepository._optional_datetime(row["finished_at"]),
            outcome=(
                None
                if row["outcome"] is None
                else JobAttemptOutcome(row["outcome"])
            ),
            error_code=row["error_code"],
            error_message=row["error_message"],
        )

    @staticmethod
    def _artifact_from_row(row: sqlite3.Row) -> ArtifactRecord:
        return ArtifactRecord(
            artifact_id=str(row["artifact_id"]),
            artifact_key=str(row["artifact_key"]),
            video_id=row["video_id"],
            job_id=row["job_id"],
            kind=ArtifactKind(row["kind"]),
            storage_root=StorageRoot(row["storage_root"]),
            relative_path=str(row["relative_path"]),
            content_hash=str(row["content_hash"]),
            provider=row["provider"],
            model=row["model"],
            producer_version=str(row["producer_version"]),
            retention_class=RetentionClass(row["retention_class"]),
            created_at=_parse_utc_datetime(str(row["created_at"])),
            expires_at=SQLiteStateRepository._optional_datetime(row["expires_at"]),
            deleted_at=SQLiteStateRepository._optional_datetime(row["deleted_at"]),
        )

    @staticmethod
    def _provider_call_from_row(row: sqlite3.Row) -> ProviderCallRecord:
        return ProviderCallRecord(
            request_hash=str(row["request_hash"]),
            operation=str(row["operation"]),
            provider=str(row["provider"]),
            model=row["model"],
            prompt_version=row["prompt_version"],
            schema_version=row["schema_version"],
            status=ProviderCallStatus(row["status"]),
            reservation_owner=row["reservation_owner"],
            lease_until=SQLiteStateRepository._optional_datetime(row["lease_until"]),
            available_at=_parse_utc_datetime(str(row["available_at"])),
            attempt_count=int(row["attempt_count"]),
            response_artifact_id=row["response_artifact_id"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            cost_microusd=row["cost_microusd"],
            last_error_code=row["last_error_code"],
            last_error_message=row["last_error_message"],
            started_at=_parse_utc_datetime(str(row["started_at"])),
            finished_at=SQLiteStateRepository._optional_datetime(row["finished_at"]),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    @staticmethod
    def _report_from_row(row: sqlite3.Row) -> ReportRecord:
        return ReportRecord(
            report_id=str(row["report_id"]),
            timezone=str(row["timezone"]),
            iso_year=int(row["iso_year"]),
            iso_week=int(row["iso_week"]),
            report_type=str(row["report_type"]),
            relative_path=row["relative_path"],
            content_hash=row["content_hash"],
            status=ReportStatus(row["status"]),
            created_at=_parse_utc_datetime(str(row["created_at"])),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    def get_channel_cursor(self, channel_id: str) -> ChannelCursorRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM channel_cursors WHERE channel_id = :channel_id",
                {"channel_id": channel_id},
            ).fetchone()
            return None if row is None else self._cursor_from_row(row)
        finally:
            connection.close()

    @staticmethod
    def _cursor_matches(
        current: ChannelCursorRecord | None,
        expected_cursor: DiscoveryCursor | None,
        expected_revision: int,
    ) -> bool:
        if current is None:
            return expected_cursor is None and expected_revision == 0
        return (
            expected_cursor is not None
            and current.revision == expected_revision
            and current.as_discovery_cursor() == expected_cursor
        )

    def save_discovery_batch(
        self,
        batch: DiscoveryBatch,
        *,
        expected_cursor: DiscoveryCursor | None,
        expected_revision: int,
        pipeline_version: str,
        now: datetime,
    ) -> ChannelCursorRecord:
        if batch.next_cursor.channel_id != batch.channel_id:
            msg = "discovery batch and next cursor channel differ"
            raise ValueError(msg)
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT * FROM channel_cursors WHERE channel_id = :channel_id",
                    {"channel_id": batch.channel_id},
                ).fetchone()
                current = None if row is None else self._cursor_from_row(row)
                if not self._cursor_matches(
                    current, expected_cursor, expected_revision
                ):
                    msg = "channel cursor changed before discovery batch commit"
                    raise ConcurrencyConflict(msg)
                for video_id in batch.video_ids:
                    connection.execute(
                        "INSERT INTO videos "
                        "(video_id, channel_id, pipeline_status, pipeline_version, "
                        "discovered_at, updated_at) "
                        "VALUES (:video_id, :channel_id, :pipeline_status, "
                        ":pipeline_version, :discovered_at, :updated_at) "
                        "ON CONFLICT(video_id) DO NOTHING",
                        {
                            "video_id": video_id,
                            "channel_id": batch.channel_id,
                            "pipeline_status": PipelineStatus.DISCOVERED.value,
                            "pipeline_version": pipeline_version,
                            "discovered_at": now_text,
                            "updated_at": now_text,
                        },
                    )
                self._inject_failure("discovery.after_candidates")
                cursor = batch.next_cursor
                if current is None:
                    connection.execute(
                        "INSERT INTO channel_cursors "
                        "(channel_id, last_checked_at, latest_published_at, "
                        "latest_video_id, provider_cursor, revision, updated_at) "
                        "VALUES (:channel_id, :last_checked_at, :latest_published_at, "
                        ":latest_video_id, :provider_cursor, 1, :updated_at)",
                        {
                            "channel_id": batch.channel_id,
                            "last_checked_at": (
                                None
                                if cursor.last_checked_at is None
                                else format_utc_datetime(cursor.last_checked_at)
                            ),
                            "latest_published_at": (
                                None
                                if cursor.latest_published_at is None
                                else format_utc_datetime(cursor.latest_published_at)
                            ),
                            "latest_video_id": cursor.latest_video_id,
                            "provider_cursor": cursor.provider_cursor,
                            "updated_at": now_text,
                        },
                    )
                else:
                    changed = connection.execute(
                        "UPDATE channel_cursors SET "
                        "last_checked_at = :last_checked_at, "
                        "latest_published_at = :latest_published_at, "
                        "latest_video_id = :latest_video_id, "
                        "provider_cursor = :provider_cursor, "
                        "last_error_code = NULL, last_error_message = NULL, "
                        "revision = revision + 1, updated_at = :updated_at "
                        "WHERE channel_id = :channel_id AND revision = :revision",
                        {
                            "channel_id": batch.channel_id,
                            "last_checked_at": (
                                None
                                if cursor.last_checked_at is None
                                else format_utc_datetime(cursor.last_checked_at)
                            ),
                            "latest_published_at": (
                                None
                                if cursor.latest_published_at is None
                                else format_utc_datetime(cursor.latest_published_at)
                            ),
                            "latest_video_id": cursor.latest_video_id,
                            "provider_cursor": cursor.provider_cursor,
                            "updated_at": now_text,
                            "revision": expected_revision,
                        },
                    ).rowcount
                    if changed != 1:
                        msg = "channel cursor changed before discovery batch commit"
                        raise ConcurrencyConflict(msg)
                saved = connection.execute(
                    "SELECT * FROM channel_cursors WHERE channel_id = :channel_id",
                    {"channel_id": batch.channel_id},
                ).fetchone()
                if saved is None:
                    msg = "channel cursor was not saved"
                    raise StateStoreError(msg)
                return self._cursor_from_row(saved)
        finally:
            connection.close()

    def get_video(self, video_id: str) -> VideoRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM videos WHERE video_id = :video_id",
                {"video_id": video_id},
            ).fetchone()
            return None if row is None else self._video_from_row(row)
        finally:
            connection.close()

    def list_videos_for_processing(
        self,
        *,
        pipeline_version: str,
        limit: int = 100,
    ) -> tuple[VideoRecord, ...]:
        """Return stable non-terminal video work without changing state."""

        if not pipeline_version.strip() or limit <= 0 or limit > 1000:
            raise ValueError("processing query arguments are invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM videos WHERE pipeline_version = :pipeline_version "
                "AND pipeline_status NOT IN (:complete, :duration_limit) "
                "ORDER BY discovered_at, video_id LIMIT :limit",
                {
                    "pipeline_version": pipeline_version,
                    "complete": PipelineStatus.COMPLETE.value,
                    "duration_limit": PipelineStatus.SKIPPED_DURATION_LIMIT.value,
                    "limit": limit,
                },
            ).fetchall()
            return tuple(self._video_from_row(row) for row in rows)
        finally:
            connection.close()

    def latest_video_job(
        self,
        video_id: str,
        *,
        target_stage: ProcessingStage | None = None,
    ) -> JobRecord | None:
        """Return the newest video-stage Job for user feedback."""

        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM jobs WHERE video_id = :video_id "
                "AND job_type = :job_type "
                "AND (:target_stage IS NULL OR target_stage = :target_stage) "
                "ORDER BY updated_at DESC, "
                "CASE WHEN status = :succeeded THEN 1 ELSE 0 END, "
                "job_id DESC LIMIT 1",
                {
                    "video_id": video_id,
                    "job_type": JobType.VIDEO_STAGE.value,
                    "succeeded": JobStatus.SUCCEEDED.value,
                    "target_stage": (
                        None if target_stage is None else target_stage.value
                    ),
                },
            ).fetchone()
            return None if row is None else self._job_from_row(row)
        finally:
            connection.close()

    def list_failed_video_jobs(self, *, limit: int = 100) -> tuple[JobRecord, ...]:
        """Return one newest final failure per video in stable order."""

        if limit <= 0 or limit > 1000:
            raise ValueError("failed job query limit is invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT j.* FROM jobs AS j WHERE j.job_type = :job_type "
                "AND j.status = :failed AND j.video_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM jobs AS newer "
                "WHERE newer.video_id = j.video_id AND newer.job_type = :job_type "
                "AND newer.status = :failed "
                "AND (newer.updated_at > j.updated_at OR "
                "(newer.updated_at = j.updated_at AND newer.job_id > j.job_id))) "
                "ORDER BY j.updated_at, j.job_id LIMIT :limit",
                {
                    "job_type": JobType.VIDEO_STAGE.value,
                    "failed": JobStatus.FAILED_FINAL.value,
                    "limit": limit,
                },
            ).fetchall()
            return tuple(self._job_from_row(row) for row in rows)
        finally:
            connection.close()

    def transcript_refresh_generation(self, video_id: str) -> int:
        """Return the durable refresh generation after final transcript failures."""

        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE video_id = :video_id "
                "AND job_type = :job_type AND target_stage = :target_stage "
                "AND status = :failed",
                {
                    "video_id": video_id,
                    "job_type": JobType.VIDEO_STAGE.value,
                    "target_stage": ProcessingStage.TRANSCRIPT.value,
                    "failed": JobStatus.FAILED_FINAL.value,
                },
            ).fetchone()
            return int(row[0])
        finally:
            connection.close()

    def latest_artifact(
        self,
        video_id: str,
        kind: ArtifactKind,
    ) -> ArtifactRecord | None:
        """Return the newest active indexed Artifact for an application loader."""

        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE video_id = :video_id AND kind = :kind "
                "AND deleted_at IS NULL ORDER BY created_at DESC, artifact_id DESC LIMIT 1",
                {"video_id": video_id, "kind": kind.value},
            ).fetchone()
            return None if row is None else self._artifact_from_row(row)
        finally:
            connection.close()

    def upsert_video_metadata(
        self,
        metadata: VideoMetadata,
        *,
        pipeline_version: str,
        now: datetime,
    ) -> VideoRecord:
        now_text = format_utc_datetime(now)
        languages = tuple(dict.fromkeys(metadata.available_languages))
        languages_json = json.dumps(
            languages,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO videos "
                    "(video_id, channel_id, channel_name, title, description, "
                    "source_url, published_at, duration_seconds, default_language, "
                    "available_languages_json, live_status, availability, "
                    "pipeline_status, pipeline_version, discovered_at, updated_at) "
                    "VALUES (:video_id, :channel_id, :channel_name, :title, "
                    ":description, :source_url, :published_at, :duration_seconds, "
                    ":default_language, :available_languages_json, :live_status, "
                    ":availability, :pipeline_status, :pipeline_version, "
                    ":discovered_at, :updated_at) "
                    "ON CONFLICT(video_id) DO UPDATE SET "
                    "channel_id = excluded.channel_id, "
                    "channel_name = excluded.channel_name, title = excluded.title, "
                    "description = excluded.description, source_url = excluded.source_url, "
                    "published_at = excluded.published_at, "
                    "duration_seconds = excluded.duration_seconds, "
                    "default_language = excluded.default_language, "
                    "available_languages_json = excluded.available_languages_json, "
                    "live_status = excluded.live_status, "
                    "availability = excluded.availability, updated_at = excluded.updated_at",
                    {
                        "video_id": metadata.video_id,
                        "channel_id": metadata.channel_id,
                        "channel_name": metadata.channel_name,
                        "title": metadata.title,
                        "description": metadata.description,
                        "source_url": metadata.source_url,
                        "published_at": format_utc_datetime(metadata.published_at),
                        "duration_seconds": metadata.duration_seconds,
                        "default_language": metadata.default_language,
                        "available_languages_json": languages_json,
                        "live_status": metadata.live_status.value,
                        "availability": metadata.availability.value,
                        "pipeline_status": PipelineStatus.DISCOVERED.value,
                        "pipeline_version": pipeline_version,
                        "discovered_at": now_text,
                        "updated_at": now_text,
                    },
                )
                row = connection.execute(
                    "SELECT * FROM videos WHERE video_id = :video_id",
                    {"video_id": metadata.video_id},
                ).fetchone()
                if row is None:
                    msg = "video metadata was not saved"
                    raise StateStoreError(msg)
                return self._video_from_row(row)
        finally:
            connection.close()

    def mark_video_unavailable(
        self,
        video_id: str,
        *,
        availability: Availability,
        now: datetime,
    ) -> bool:
        if availability is Availability.PUBLIC:
            msg = "unavailable marker cannot use public availability"
            raise ValueError(msg)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE videos SET availability = :availability, "
                    "updated_at = :updated_at WHERE video_id = :video_id",
                    {
                        "availability": availability.value,
                        "updated_at": format_utc_datetime(now),
                        "video_id": video_id,
                    },
                ).rowcount
                return changed == 1
        finally:
            connection.close()

    def advance_pipeline(
        self,
        video_id: str,
        *,
        expected_status: PipelineStatus,
        target_status: PipelineStatus,
        pipeline_version: str,
        now: datetime,
    ) -> bool:
        transition_pipeline(expected_status, target_status)
        completed_at = (
            format_utc_datetime(now)
            if target_status
            in {PipelineStatus.COMPLETE, PipelineStatus.SKIPPED_DURATION_LIMIT}
            else None
        )
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE videos SET pipeline_status = :target_status, "
                    "updated_at = :updated_at, completed_at = :completed_at "
                    "WHERE video_id = :video_id "
                    "AND pipeline_status = :expected_status "
                    "AND pipeline_version = :pipeline_version",
                    {
                        "target_status": target_status.value,
                        "updated_at": format_utc_datetime(now),
                        "completed_at": completed_at,
                        "video_id": video_id,
                        "expected_status": expected_status.value,
                        "pipeline_version": pipeline_version,
                    },
                ).rowcount
                return changed == 1
        finally:
            connection.close()

    @staticmethod
    def _validate_job_shape(
        *,
        scope_key: str,
        video_id: str | None,
        job_type: JobType,
        target_stage: ProcessingStage,
    ) -> None:
        if not scope_key.strip():
            msg = "scope_key must be non-empty"
            raise ValueError(msg)
        if job_type is JobType.VIDEO_STAGE:
            if video_id is None or target_stage in {
                ProcessingStage.DISCOVERY,
                ProcessingStage.WEEKLY_REPORT,
            }:
                msg = "video stage jobs require a video and video processing stage"
                raise ValueError(msg)
            expected_scope = f"video:{video_id}:{target_stage.value}"
            if scope_key != expected_scope:
                msg = "video job scope_key is not canonical"
                raise ValueError(msg)
        elif video_id is not None:
            msg = "global jobs must not reference a video"
            raise ValueError(msg)
        elif (
            job_type is JobType.CHANNEL_DISCOVERY
            and target_stage is not ProcessingStage.DISCOVERY
        ) or (
            job_type is JobType.WEEKLY_REPORT
            and target_stage is not ProcessingStage.WEEKLY_REPORT
        ):
            msg = "global job type and target stage differ"
            raise ValueError(msg)
        elif job_type is JobType.CHANNEL_DISCOVERY:
            parts = scope_key.split(":")
            if (
                len(parts) != 3
                or parts[0] != "channel"
                or not parts[1]
                or parts[2] != "discovery"
            ):
                msg = "channel discovery scope_key is not canonical"
                raise ValueError(msg)
        else:
            parts = scope_key.split(":")
            if (
                len(parts) != 4
                or parts[0] != "weekly"
                or not parts[1]
                or re.fullmatch(r"\d{4}-W\d{2}", parts[2]) is None
                or not parts[3]
            ):
                msg = "weekly report scope_key is not canonical"
                raise ValueError(msg)

    @staticmethod
    def _insert_job(
        connection: sqlite3.Connection,
        *,
        job_id: str,
        scope_key: str,
        video_id: str | None,
        job_type: JobType,
        target_stage: ProcessingStage,
        pipeline_version: str,
        max_attempts: int,
        available_at: str,
        now: str,
    ) -> None:
        connection.execute(
            "INSERT INTO jobs "
            "(job_id, scope_key, video_id, job_type, target_stage, "
            "pipeline_version, status, attempt_count, max_attempts, "
            "available_at, created_at, updated_at) "
            "VALUES (:job_id, :scope_key, :video_id, :job_type, :target_stage, "
            ":pipeline_version, :status, 0, :max_attempts, :available_at, "
            ":created_at, :updated_at)",
            {
                "job_id": job_id,
                "scope_key": scope_key,
                "video_id": video_id,
                "job_type": job_type.value,
                "target_stage": target_stage.value,
                "pipeline_version": pipeline_version,
                "status": JobStatus.PENDING.value,
                "max_attempts": max_attempts,
                "available_at": available_at,
                "created_at": now,
                "updated_at": now,
            },
        )

    def create_job(
        self,
        *,
        job_id: str,
        scope_key: str,
        video_id: str | None,
        job_type: JobType,
        target_stage: ProcessingStage,
        pipeline_version: str,
        max_attempts: int,
        available_at: datetime,
        now: datetime,
    ) -> JobRecord:
        self._validate_job_shape(
            scope_key=scope_key,
            video_id=video_id,
            job_type=job_type,
            target_stage=target_stage,
        )
        if max_attempts <= 0:
            msg = "max_attempts must be positive"
            raise ValueError(msg)
        connection = self._connect()
        try:
            try:
                with _immediate_transaction(connection):
                    self._insert_job(
                        connection,
                        job_id=job_id,
                        scope_key=scope_key,
                        video_id=video_id,
                        job_type=job_type,
                        target_stage=target_stage,
                        pipeline_version=pipeline_version,
                        max_attempts=max_attempts,
                        available_at=format_utc_datetime(available_at),
                        now=format_utc_datetime(now),
                    )
            except sqlite3.IntegrityError as error:
                msg = "active job already exists or job data is invalid"
                raise IntegrityConflict(msg) from error
            job = self.get_job(job_id)
            if job is None:
                msg = "created job could not be read"
                raise StateStoreError(msg)
            return job
        finally:
            connection.close()

    def get_job(self, job_id: str) -> JobRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = :job_id",
                {"job_id": job_id},
            ).fetchone()
            return None if row is None else self._job_from_row(row)
        finally:
            connection.close()

    def list_job_attempts(self, job_id: str) -> tuple[JobAttemptRecord, ...]:
        connection = self._connect()
        try:
            return tuple(
                self._attempt_from_row(row)
                for row in connection.execute(
                    "SELECT * FROM job_attempts WHERE job_id = :job_id "
                    "ORDER BY attempt_number",
                    {"job_id": job_id},
                )
            )
        finally:
            connection.close()

    def claim_next_job(
        self,
        *,
        owner: str,
        lease_until: datetime,
        now: datetime,
        video_id: str | None = None,
    ) -> JobRecord | None:
        if not owner.strip():
            msg = "lease owner must be non-empty"
            raise ValueError(msg)
        if video_id is not None and not video_id.strip():
            msg = "video_id filter must be non-empty when provided"
            raise ValueError(msg)
        now_text = format_utc_datetime(now)
        lease_text = format_utc_datetime(lease_until)
        if lease_text <= now_text:
            msg = "lease_until must be after now"
            raise ValueError(msg)
        video_filter = ""
        params: dict[str, object] = {
            "status": JobStatus.PENDING.value,
            "now": now_text,
        }
        if video_id is not None:
            video_filter = " AND video_id = :video_id"
            params["video_id"] = video_id
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT * FROM jobs WHERE status = :status "
                    "AND available_at <= :now AND attempt_count < max_attempts "
                    f"{video_filter} "
                    "ORDER BY available_at, created_at, job_id LIMIT 1",
                    params,
                ).fetchone()
                if row is None:
                    return None
                attempt_number = int(row["attempt_count"]) + 1
                changed = connection.execute(
                    "UPDATE jobs SET status = :running, attempt_count = :attempt, "
                    "lease_owner = :owner, lease_until = :lease_until, "
                    "updated_at = :now WHERE job_id = :job_id "
                    "AND status = :pending AND attempt_count = :previous_attempt",
                    {
                        "running": JobStatus.RUNNING.value,
                        "attempt": attempt_number,
                        "owner": owner,
                        "lease_until": lease_text,
                        "now": now_text,
                        "job_id": row["job_id"],
                        "pending": JobStatus.PENDING.value,
                        "previous_attempt": row["attempt_count"],
                    },
                ).rowcount
                if changed != 1:
                    msg = "job changed before claim"
                    raise ConcurrencyConflict(msg)
                connection.execute(
                    "INSERT INTO job_attempts "
                    "(job_id, attempt_number, lease_owner, started_at, lease_until) "
                    "VALUES (:job_id, :attempt_number, :owner, :started_at, "
                    ":lease_until)",
                    {
                        "job_id": row["job_id"],
                        "attempt_number": attempt_number,
                        "owner": owner,
                        "started_at": now_text,
                        "lease_until": lease_text,
                    },
                )
                claimed = connection.execute(
                    "SELECT * FROM jobs WHERE job_id = :job_id",
                    {"job_id": row["job_id"]},
                ).fetchone()
                if claimed is None:
                    msg = "claimed job could not be read"
                    raise StateStoreError(msg)
                return self._job_from_row(claimed)
        finally:
            connection.close()

    def renew_job(
        self,
        job_id: str,
        *,
        owner: str,
        lease_until: datetime,
        now: datetime,
    ) -> bool:
        now_text = format_utc_datetime(now)
        lease_text = format_utc_datetime(lease_until)
        if lease_text <= now_text:
            msg = "lease_until must be after now"
            raise ValueError(msg)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE jobs SET lease_until = :lease_until, updated_at = :now "
                    "WHERE job_id = :job_id AND status = :running "
                    "AND lease_owner = :owner AND lease_until > :now",
                    {
                        "lease_until": lease_text,
                        "now": now_text,
                        "job_id": job_id,
                        "running": JobStatus.RUNNING.value,
                        "owner": owner,
                    },
                ).rowcount
                if changed == 0:
                    return False
                attempt_changed = connection.execute(
                    "UPDATE job_attempts SET lease_until = :lease_until "
                    "WHERE job_id = :job_id AND finished_at IS NULL "
                    "AND lease_owner = :owner",
                    {
                        "lease_until": lease_text,
                        "job_id": job_id,
                        "owner": owner,
                    },
                ).rowcount
                if attempt_changed != 1:
                    msg = "active job attempt is missing"
                    raise StateStoreError(msg)
                return True
        finally:
            connection.close()

    @staticmethod
    def _owned_running_job(
        connection: sqlite3.Connection,
        *,
        job_id: str,
        owner: str,
        now: str,
    ) -> sqlite3.Row:
        row: sqlite3.Row | None = connection.execute(
            "SELECT * FROM jobs WHERE job_id = :job_id AND status = :running "
            "AND lease_owner = :owner AND lease_until > :now",
            {
                "job_id": job_id,
                "running": JobStatus.RUNNING.value,
                "owner": owner,
                "now": now,
            },
        ).fetchone()
        if row is None:
            msg = "job lease is not owned or has expired"
            raise LeaseConflict(msg)
        return row

    def fail_job(
        self,
        job_id: str,
        *,
        owner: str,
        error_code: ErrorCode,
        error_message: str,
        retry_at: datetime | None,
        now: datetime,
    ) -> JobRecord:
        now_text = format_utc_datetime(now)
        retry_text = None if retry_at is None else format_utc_datetime(retry_at)
        safe_message = _safe_error_message(error_message)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = self._owned_running_job(
                    connection, job_id=job_id, owner=owner, now=now_text
                )
                retryable = retry_text is not None and int(
                    row["attempt_count"]
                ) < int(row["max_attempts"])
                status = (
                    JobStatus.RETRY_PENDING if retryable else JobStatus.FAILED_FINAL
                )
                finished_at = None if retryable else now_text
                available_at = retry_text if retryable else row["available_at"]
                attempt_changed = connection.execute(
                    "UPDATE job_attempts SET finished_at = :now, outcome = :outcome, "
                    "error_code = :error_code, error_message = :error_message "
                    "WHERE job_id = :job_id AND finished_at IS NULL "
                    "AND lease_owner = :owner",
                    {
                        "now": now_text,
                        "outcome": status.value,
                        "error_code": error_code.value,
                        "error_message": safe_message,
                        "job_id": job_id,
                        "owner": owner,
                    },
                ).rowcount
                if attempt_changed != 1:
                    msg = "active job attempt is missing"
                    raise StateStoreError(msg)
                connection.execute(
                    "UPDATE jobs SET status = :status, available_at = :available_at, "
                    "lease_owner = NULL, lease_until = NULL, "
                    "last_error_code = :error_code, "
                    "last_error_message = :error_message, updated_at = :now, "
                    "finished_at = :finished_at WHERE job_id = :job_id",
                    {
                        "status": status.value,
                        "available_at": available_at,
                        "error_code": error_code.value,
                        "error_message": safe_message,
                        "now": now_text,
                        "finished_at": finished_at,
                        "job_id": job_id,
                    },
                )
                saved = connection.execute(
                    "SELECT * FROM jobs WHERE job_id = :job_id", {"job_id": job_id}
                ).fetchone()
                return self._job_from_row(saved)
        finally:
            connection.close()

    def complete_job(
        self,
        job_id: str,
        *,
        owner: str,
        now: datetime,
    ) -> JobRecord:
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = self._owned_running_job(
                    connection, job_id=job_id, owner=owner, now=now_text
                )
                if row["video_id"] is not None:
                    msg = "video stage jobs must complete with pipeline state atomically"
                    raise StateStoreError(msg)
                attempt_changed = connection.execute(
                    "UPDATE job_attempts SET finished_at = :now, outcome = :outcome "
                    "WHERE job_id = :job_id AND finished_at IS NULL "
                    "AND lease_owner = :owner",
                    {
                        "now": now_text,
                        "outcome": JobAttemptOutcome.SUCCEEDED.value,
                        "job_id": job_id,
                        "owner": owner,
                    },
                ).rowcount
                if attempt_changed != 1:
                    msg = "active job attempt is missing"
                    raise StateStoreError(msg)
                connection.execute(
                    "UPDATE jobs SET status = :succeeded, lease_owner = NULL, "
                    "lease_until = NULL, last_error_code = NULL, "
                    "last_error_message = NULL, updated_at = :now, finished_at = :now "
                    "WHERE job_id = :job_id",
                    {
                        "succeeded": JobStatus.SUCCEEDED.value,
                        "now": now_text,
                        "job_id": job_id,
                    },
                )
                saved = connection.execute(
                    "SELECT * FROM jobs WHERE job_id = :job_id", {"job_id": job_id}
                ).fetchone()
                return self._job_from_row(saved)
        finally:
            connection.close()

    def reclaim_expired_jobs(self, *, now: datetime) -> tuple[JobRecord, ...]:
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                expired = tuple(
                    connection.execute(
                        "SELECT * FROM jobs WHERE status = :running "
                        "AND lease_until <= :now ORDER BY lease_until, created_at, job_id",
                        {"running": JobStatus.RUNNING.value, "now": now_text},
                    )
                )
                recovered: list[JobRecord] = []
                for row in expired:
                    retryable = int(row["attempt_count"]) < int(row["max_attempts"])
                    status = (
                        JobStatus.RETRY_PENDING
                        if retryable
                        else JobStatus.FAILED_FINAL
                    )
                    finished_at = None if retryable else now_text
                    attempt_changed = connection.execute(
                        "UPDATE job_attempts SET finished_at = :now, "
                        "outcome = :outcome, error_code = :error_code, "
                        "error_message = :error_message "
                        "WHERE job_id = :job_id AND finished_at IS NULL",
                        {
                            "now": now_text,
                            "outcome": JobAttemptOutcome.LEASE_EXPIRED.value,
                            "error_code": "LEASE_EXPIRED",
                            "error_message": "job lease expired",
                            "job_id": row["job_id"],
                        },
                    ).rowcount
                    if attempt_changed != 1:
                        msg = "expired job attempt is missing"
                        raise StateStoreError(msg)
                    connection.execute(
                        "UPDATE jobs SET status = :status, available_at = :now, "
                        "lease_owner = NULL, lease_until = NULL, "
                        "last_error_code = :error_code, "
                        "last_error_message = :error_message, updated_at = :now, "
                        "finished_at = :finished_at WHERE job_id = :job_id",
                        {
                            "status": status.value,
                            "now": now_text,
                            "error_code": "LEASE_EXPIRED",
                            "error_message": "job lease expired",
                            "finished_at": finished_at,
                            "job_id": row["job_id"],
                        },
                    )
                    saved = connection.execute(
                        "SELECT * FROM jobs WHERE job_id = :job_id",
                        {"job_id": row["job_id"]},
                    ).fetchone()
                    recovered.append(self._job_from_row(saved))
                return tuple(recovered)
        finally:
            connection.close()

    def activate_retry_jobs(self, *, now: datetime) -> tuple[JobRecord, ...]:
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                due = tuple(
                    connection.execute(
                        "SELECT job_id FROM jobs WHERE status = :retry_pending "
                        "AND available_at <= :now ORDER BY available_at, created_at, job_id",
                        {
                            "retry_pending": JobStatus.RETRY_PENDING.value,
                            "now": now_text,
                        },
                    )
                )
                activated: list[JobRecord] = []
                for due_row in due:
                    connection.execute(
                        "UPDATE jobs SET status = :pending, updated_at = :now "
                        "WHERE job_id = :job_id AND status = :retry_pending",
                        {
                            "pending": JobStatus.PENDING.value,
                            "now": now_text,
                            "job_id": due_row["job_id"],
                            "retry_pending": JobStatus.RETRY_PENDING.value,
                        },
                    )
                    saved = connection.execute(
                        "SELECT * FROM jobs WHERE job_id = :job_id",
                        {"job_id": due_row["job_id"]},
                    ).fetchone()
                    activated.append(self._job_from_row(saved))
                return tuple(activated)
        finally:
            connection.close()

    def rerun_job(
        self,
        old_job_id: str,
        *,
        new_job_id: str,
        available_at: datetime,
        now: datetime,
    ) -> JobRecord:
        old = self.get_job(old_job_id)
        if old is None or old.status not in {
            JobStatus.SUCCEEDED,
            JobStatus.FAILED_FINAL,
        }:
            msg = "manual rerun requires a terminal source job"
            raise ValueError(msg)
        return self.create_job(
            job_id=new_job_id,
            scope_key=old.scope_key,
            video_id=old.video_id,
            job_type=old.job_type,
            target_stage=old.target_stage,
            pipeline_version=old.pipeline_version,
            max_attempts=old.max_attempts,
            available_at=available_at,
            now=now,
        )

    @staticmethod
    def _validate_artifact(artifact: ArtifactWrite) -> None:
        if not artifact.artifact_id.strip() or not artifact.artifact_key.strip():
            msg = "artifact identifiers must be non-empty"
            raise ValueError(msg)
        if not artifact.producer_version.strip():
            msg = "artifact producer_version must be non-empty"
            raise ValueError(msg)
        _validate_sha256(artifact.content_hash, field_name="content_hash")
        _validate_relative_path(artifact.relative_path)

    def _upsert_artifact_in_transaction(
        self,
        connection: sqlite3.Connection,
        artifact: ArtifactWrite,
        *,
        now: str,
    ) -> ArtifactRecord:
        self._validate_artifact(artifact)
        expires_at = (
            None
            if artifact.expires_at is None
            else format_utc_datetime(artifact.expires_at)
        )
        existing = connection.execute(
            "SELECT * FROM artifacts WHERE artifact_key = :artifact_key",
            {"artifact_key": artifact.artifact_key},
        ).fetchone()
        if existing is not None:
            record = self._artifact_from_row(existing)
            if (
                record.artifact_id != artifact.artifact_id
                or record.video_id != artifact.video_id
                or record.job_id != artifact.job_id
                or record.kind is not artifact.kind
                or record.storage_root is not artifact.storage_root
                or record.relative_path != artifact.relative_path
                or record.content_hash != artifact.content_hash
                or record.provider != artifact.provider
                or record.model != artifact.model
                or record.producer_version != artifact.producer_version
                or record.retention_class is not artifact.retention_class
                or record.expires_at != artifact.expires_at
            ):
                msg = "artifact key already identifies different content"
                raise IntegrityConflict(msg)
            return record
        connection.execute(
            "INSERT INTO artifacts "
            "(artifact_id, artifact_key, video_id, job_id, kind, storage_root, "
            "relative_path, content_hash, provider, model, producer_version, "
            "retention_class, created_at, expires_at) "
            "VALUES (:artifact_id, :artifact_key, :video_id, :job_id, :kind, "
            ":storage_root, :relative_path, :content_hash, :provider, :model, "
            ":producer_version, :retention_class, :created_at, :expires_at)",
            {
                "artifact_id": artifact.artifact_id,
                "artifact_key": artifact.artifact_key,
                "video_id": artifact.video_id,
                "job_id": artifact.job_id,
                "kind": artifact.kind.value,
                "storage_root": artifact.storage_root.value,
                "relative_path": artifact.relative_path,
                "content_hash": artifact.content_hash,
                "provider": artifact.provider,
                "model": artifact.model,
                "producer_version": artifact.producer_version,
                "retention_class": artifact.retention_class.value,
                "created_at": now,
                "expires_at": expires_at,
            },
        )
        row = connection.execute(
            "SELECT * FROM artifacts WHERE artifact_key = :artifact_key",
            {"artifact_key": artifact.artifact_key},
        ).fetchone()
        if row is None:
            msg = "artifact was not saved"
            raise StateStoreError(msg)
        return self._artifact_from_row(row)

    def upsert_artifact(
        self,
        artifact: ArtifactWrite,
        *,
        now: datetime,
    ) -> ArtifactRecord:
        connection = self._connect()
        try:
            try:
                with _immediate_transaction(connection):
                    return self._upsert_artifact_in_transaction(
                        connection,
                        artifact,
                        now=format_utc_datetime(now),
                    )
            except sqlite3.IntegrityError as error:
                msg = "artifact data violates repository integrity"
                raise IntegrityConflict(msg) from error
        finally:
            connection.close()

    def get_artifact_by_key(self, artifact_key: str) -> ArtifactRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE artifact_key = :artifact_key",
                {"artifact_key": artifact_key},
            ).fetchone()
            return None if row is None else self._artifact_from_row(row)
        finally:
            connection.close()

    def mark_artifact_deleted(
        self,
        artifact_id: str,
        expected_content_hash: str,
        now: datetime,
    ) -> bool:
        """Record an already-performed file deletion with hash compare-and-swap.

        The repository never deletes a file. Callers must verify storage-root and
        filesystem boundaries before invoking this index-only confirmation.
        """

        _validate_sha256(expected_content_hash, field_name="expected_content_hash")
        if not artifact_id.strip():
            msg = "artifact_id must be non-empty"
            raise ValueError(msg)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE artifacts SET deleted_at = :now "
                    "WHERE artifact_id = :artifact_id "
                    "AND content_hash = :content_hash AND deleted_at IS NULL",
                    {
                        "now": format_utc_datetime(now),
                        "artifact_id": artifact_id,
                        "content_hash": expected_content_hash,
                    },
                ).rowcount
                return changed == 1
        finally:
            connection.close()

    def list_expired_artifacts(
        self,
        retention_class: RetentionClass,
        now: datetime,
        limit: int,
    ) -> tuple[ArtifactRecord, ...]:
        """Return registered, undeleted expired artifacts in stable cleanup order."""

        if limit <= 0:
            msg = "limit must be positive"
            raise ValueError(msg)
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM artifacts "
                "WHERE retention_class = :retention_class "
                "AND expires_at IS NOT NULL AND expires_at <= :now "
                "AND deleted_at IS NULL "
                "ORDER BY expires_at ASC, created_at ASC, artifact_id ASC "
                "LIMIT :limit",
                {
                    "retention_class": retention_class.value,
                    "now": now_text,
                    "limit": limit,
                },
            ).fetchall()
            return tuple(self._artifact_from_row(row) for row in rows)
        finally:
            connection.close()

    @staticmethod
    def _provider_request_matches(
        row: sqlite3.Row, request: ProviderCallRequest
    ) -> bool:
        return (
            str(row["operation"]) == request.operation
            and str(row["provider"]) == request.provider
            and (None if row["model"] is None else str(row["model"])) == request.model
            and (
                None
                if row["prompt_version"] is None
                else str(row["prompt_version"])
            )
            == request.prompt_version
            and (
                None
                if row["schema_version"] is None
                else str(row["schema_version"])
            )
            == request.schema_version
        )

    def reserve_provider_call(
        self,
        request: ProviderCallRequest,
        *,
        owner: str,
        lease_until: datetime,
        available_at: datetime,
        now: datetime,
        verified_artifact: VerifiedArtifact | None = None,
    ) -> ProviderReservation:
        _validate_sha256(request.request_hash, field_name="request_hash")
        if not request.operation.strip() or not request.provider.strip():
            msg = "provider call operation and provider must be non-empty"
            raise ValueError(msg)
        if not request.deterministic_artifact_key.strip():
            msg = "deterministic artifact key must be non-empty"
            raise ValueError(msg)
        if not owner.strip():
            msg = "reservation owner must be non-empty"
            raise ValueError(msg)
        now_text = format_utc_datetime(now)
        lease_text = format_utc_datetime(lease_until)
        available_text = format_utc_datetime(available_at)
        if lease_text <= now_text:
            msg = "provider call lease_until must be after now"
            raise ValueError(msg)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                    {"request_hash": request.request_hash},
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO provider_calls "
                        "(request_hash, operation, provider, model, prompt_version, "
                        "schema_version, status, reservation_owner, lease_until, "
                        "available_at, attempt_count, started_at, updated_at) "
                        "VALUES (:request_hash, :operation, :provider, :model, "
                        ":prompt_version, :schema_version, :status, :owner, "
                        ":lease_until, :available_at, 1, :started_at, :updated_at)",
                        {
                            "request_hash": request.request_hash,
                            "operation": request.operation,
                            "provider": request.provider,
                            "model": request.model,
                            "prompt_version": request.prompt_version,
                            "schema_version": request.schema_version,
                            "status": ProviderCallStatus.PENDING.value,
                            "owner": owner,
                            "lease_until": lease_text,
                            "available_at": available_text,
                            "started_at": now_text,
                            "updated_at": now_text,
                        },
                    )
                    inserted = connection.execute(
                        "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                        {"request_hash": request.request_hash},
                    ).fetchone()
                    if inserted is None:
                        msg = "provider call reservation was not saved"
                        raise StateStoreError(msg)
                    return ProviderReservation(
                        record=self._provider_call_from_row(inserted),
                        acquired=True,
                        recovered_from_artifact=False,
                    )
                if not self._provider_request_matches(row, request):
                    msg = "request hash already identifies a different provider call"
                    raise IntegrityConflict(msg)
                record = self._provider_call_from_row(row)
                if record.status in {
                    ProviderCallStatus.SUCCEEDED,
                    ProviderCallStatus.FAILED_FINAL,
                }:
                    return ProviderReservation(record, False, False)
                if (
                    record.status is ProviderCallStatus.PENDING
                    and record.lease_until is not None
                    and record.lease_until > now
                ) or (
                    record.status is ProviderCallStatus.FAILED_RETRYABLE
                    and record.available_at > now
                ):
                    return ProviderReservation(record, False, False)

                artifact_row = connection.execute(
                    "SELECT * FROM artifacts WHERE artifact_key = :artifact_key",
                    {"artifact_key": request.deterministic_artifact_key},
                ).fetchone()
                if artifact_row is not None:
                    artifact = self._artifact_from_row(artifact_row)
                    if (
                        verified_artifact is None
                        or verified_artifact.artifact_key != artifact.artifact_key
                        or verified_artifact.content_hash != artifact.content_hash
                    ):
                        msg = "deterministic artifact exists without a verified hash"
                        raise IntegrityConflict(msg)
                    connection.execute(
                        "UPDATE provider_calls SET status = :succeeded, "
                        "reservation_owner = NULL, lease_until = NULL, "
                        "response_artifact_id = :artifact_id, finished_at = :now, "
                        "updated_at = :now, last_error_code = NULL, "
                        "last_error_message = NULL WHERE request_hash = :request_hash",
                        {
                            "succeeded": ProviderCallStatus.SUCCEEDED.value,
                            "artifact_id": artifact.artifact_id,
                            "now": now_text,
                            "request_hash": request.request_hash,
                        },
                    )
                    recovered = connection.execute(
                        "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                        {"request_hash": request.request_hash},
                    ).fetchone()
                    if recovered is None:
                        msg = "recovered provider call could not be read"
                        raise StateStoreError(msg)
                    return ProviderReservation(
                        self._provider_call_from_row(recovered), False, True
                    )
                if verified_artifact is not None:
                    msg = "verified artifact is not indexed by its deterministic key"
                    raise IntegrityConflict(msg)
                connection.execute(
                    "UPDATE provider_calls SET status = :pending, "
                    "reservation_owner = :owner, lease_until = :lease_until, "
                    "available_at = :available_at, attempt_count = attempt_count + 1, "
                    "last_error_code = NULL, last_error_message = NULL, "
                    "finished_at = NULL, updated_at = :now "
                    "WHERE request_hash = :request_hash",
                    {
                        "pending": ProviderCallStatus.PENDING.value,
                        "owner": owner,
                        "lease_until": lease_text,
                        "available_at": available_text,
                        "now": now_text,
                        "request_hash": request.request_hash,
                    },
                )
                taken = connection.execute(
                    "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                    {"request_hash": request.request_hash},
                ).fetchone()
                if taken is None:
                    msg = "provider call takeover could not be read"
                    raise StateStoreError(msg)
                return ProviderReservation(
                    self._provider_call_from_row(taken), True, False
                )
        finally:
            connection.close()

    def get_provider_call(self, request_hash: str) -> ProviderCallRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                {"request_hash": request_hash},
            ).fetchone()
            return None if row is None else self._provider_call_from_row(row)
        finally:
            connection.close()

    def _complete_provider_call_in_transaction(
        self,
        connection: sqlite3.Connection,
        completion: ProviderCallCompletion,
        *,
        owner: str,
        now: str,
    ) -> ProviderCallRecord:
        for value in (
            completion.input_tokens,
            completion.output_tokens,
            completion.cost_microusd,
        ):
            if value is not None and value < 0:
                msg = "provider usage and cost values must be non-negative"
                raise ValueError(msg)
        row = connection.execute(
            "SELECT * FROM provider_calls WHERE request_hash = :request_hash "
            "AND status = :pending AND reservation_owner = :owner "
            "AND lease_until > :now",
            {
                "request_hash": completion.request_hash,
                "pending": ProviderCallStatus.PENDING.value,
                "owner": owner,
                "now": now,
            },
        ).fetchone()
        if row is None:
            msg = "provider call reservation is not owned or has expired"
            raise LeaseConflict(msg)
        artifact_exists = connection.execute(
            "SELECT 1 FROM artifacts WHERE artifact_id = :artifact_id",
            {"artifact_id": completion.response_artifact_id},
        ).fetchone()
        if artifact_exists is None:
            msg = "provider response artifact is not indexed"
            raise IntegrityConflict(msg)
        connection.execute(
            "UPDATE provider_calls SET status = :succeeded, "
            "reservation_owner = NULL, lease_until = NULL, "
            "response_artifact_id = :artifact_id, input_tokens = :input_tokens, "
            "output_tokens = :output_tokens, cost_microusd = :cost_microusd, "
            "last_error_code = NULL, last_error_message = NULL, "
            "finished_at = :now, updated_at = :now "
            "WHERE request_hash = :request_hash",
            {
                "succeeded": ProviderCallStatus.SUCCEEDED.value,
                "artifact_id": completion.response_artifact_id,
                "input_tokens": completion.input_tokens,
                "output_tokens": completion.output_tokens,
                "cost_microusd": completion.cost_microusd,
                "now": now,
                "request_hash": completion.request_hash,
            },
        )
        saved = connection.execute(
            "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
            {"request_hash": completion.request_hash},
        ).fetchone()
        if saved is None:
            msg = "completed provider call could not be read"
            raise StateStoreError(msg)
        return self._provider_call_from_row(saved)

    def complete_provider_call(
        self,
        request_hash: str,
        *,
        owner: str,
        response_artifact_id: str,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_microusd: int | None,
        now: datetime,
    ) -> ProviderCallRecord:
        completion = ProviderCallCompletion(
            request_hash=request_hash,
            response_artifact_id=response_artifact_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_microusd=cost_microusd,
        )
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                return self._complete_provider_call_in_transaction(
                    connection,
                    completion,
                    owner=owner,
                    now=format_utc_datetime(now),
                )
        finally:
            connection.close()

    def fail_provider_call(
        self,
        request_hash: str,
        *,
        owner: str,
        retryable: bool,
        available_at: datetime,
        error_code: ErrorCode,
        error_message: str,
        now: datetime,
    ) -> ProviderCallRecord:
        now_text = format_utc_datetime(now)
        available_text = format_utc_datetime(available_at)
        status = (
            ProviderCallStatus.FAILED_RETRYABLE
            if retryable
            else ProviderCallStatus.FAILED_FINAL
        )
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE provider_calls SET status = :status, "
                    "reservation_owner = NULL, lease_until = NULL, "
                    "available_at = :available_at, last_error_code = :error_code, "
                    "last_error_message = :error_message, finished_at = :finished_at, "
                    "updated_at = :now WHERE request_hash = :request_hash "
                    "AND status = :pending AND reservation_owner = :owner "
                    "AND lease_until > :now",
                    {
                        "status": status.value,
                        "available_at": available_text,
                        "error_code": error_code.value,
                        "error_message": _safe_error_message(error_message),
                        "finished_at": None if retryable else now_text,
                        "now": now_text,
                        "request_hash": request_hash,
                        "pending": ProviderCallStatus.PENDING.value,
                        "owner": owner,
                    },
                ).rowcount
                if changed != 1:
                    msg = "provider call reservation is not owned or has expired"
                    raise LeaseConflict(msg)
                saved = connection.execute(
                    "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                    {"request_hash": request_hash},
                ).fetchone()
                if saved is None:
                    msg = "failed provider call could not be read"
                    raise StateStoreError(msg)
                return self._provider_call_from_row(saved)
        finally:
            connection.close()

    @staticmethod
    def _finish_job_success_in_transaction(
        connection: sqlite3.Connection,
        *,
        job_id: str,
        owner: str,
        now: str,
    ) -> JobRecord:
        changed = connection.execute(
            "UPDATE job_attempts SET finished_at = :now, outcome = :outcome "
            "WHERE job_id = :job_id AND finished_at IS NULL "
            "AND lease_owner = :owner",
            {
                "now": now,
                "outcome": JobAttemptOutcome.SUCCEEDED.value,
                "job_id": job_id,
                "owner": owner,
            },
        ).rowcount
        if changed != 1:
            msg = "active job attempt is missing"
            raise StateStoreError(msg)
        connection.execute(
            "UPDATE jobs SET status = :succeeded, lease_owner = NULL, "
            "lease_until = NULL, last_error_code = NULL, last_error_message = NULL, "
            "updated_at = :now, finished_at = :now WHERE job_id = :job_id",
            {
                "succeeded": JobStatus.SUCCEEDED.value,
                "now": now,
                "job_id": job_id,
            },
        )
        saved = connection.execute(
            "SELECT * FROM jobs WHERE job_id = :job_id", {"job_id": job_id}
        ).fetchone()
        if saved is None:
            msg = "completed job could not be read"
            raise StateStoreError(msg)
        return SQLiteStateRepository._job_from_row(saved)

    def complete_stage(
        self,
        *,
        job_id: str,
        owner: str,
        video_id: str,
        expected_status: PipelineStatus,
        target_status: PipelineStatus,
        pipeline_version: str,
        artifacts: tuple[ArtifactWrite, ...],
        provider_call: ProviderCallCompletion | None,
        now: datetime,
        scoring_summary: ScoringSummaryWrite | None = None,
    ) -> StageCompletionResult:
        transition_pipeline(expected_status, target_status)
        is_scoring_completion = (
            expected_status is PipelineStatus.TRANSCRIPT_READY
            and target_status is PipelineStatus.SCORED
        )
        if is_scoring_completion and scoring_summary is None:
            msg = "scoring summary is required for TRANSCRIPT_READY -> SCORED"
            raise IntegrityConflict(msg)
        if not is_scoring_completion and scoring_summary is not None:
            msg = "scoring summary is only allowed for TRANSCRIPT_READY -> SCORED"
            raise IntegrityConflict(msg)
        expected_stage = _processing_stage_for_transition(
            expected_status, target_status
        )
        if any(
            artifact.job_id != job_id or artifact.video_id != video_id
            for artifact in artifacts
        ):
            msg = "stage artifacts must reference the completed job and video"
            raise IntegrityConflict(msg)
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            try:
                with _immediate_transaction(connection):
                    job_row = self._owned_running_job(
                        connection, job_id=job_id, owner=owner, now=now_text
                    )
                    if (
                        job_row["video_id"] != video_id
                        or job_row["pipeline_version"] != pipeline_version
                    ):
                        msg = "job scope does not match stage completion"
                        raise ConcurrencyConflict(msg)
                    if job_row["target_stage"] != expected_stage.value:
                        msg = "job target stage does not match pipeline transition"
                        raise ConcurrencyConflict(msg)
                    stored_artifacts = tuple(
                        self._upsert_artifact_in_transaction(
                            connection,
                            artifact,
                            now=now_text,
                        )
                        for artifact in artifacts
                    )
                    self._inject_failure("stage.after_artifacts")
                    completed_call = (
                        None
                        if provider_call is None
                        else self._complete_provider_call_in_transaction(
                            connection,
                            provider_call,
                            owner=owner,
                            now=now_text,
                        )
                    )
                    self._inject_failure("stage.after_provider_call")
                    completed_at = (
                        now_text
                        if target_status
                        in {
                            PipelineStatus.COMPLETE,
                            PipelineStatus.SKIPPED_DURATION_LIMIT,
                        }
                        else None
                    )
                    if scoring_summary is None:
                        changed = connection.execute(
                            "UPDATE videos SET pipeline_status = :target_status, "
                            "updated_at = :now, completed_at = :completed_at "
                            "WHERE video_id = :video_id "
                            "AND pipeline_status = :expected_status "
                            "AND pipeline_version = :pipeline_version",
                            {
                                "target_status": target_status.value,
                                "now": now_text,
                                "completed_at": completed_at,
                                "video_id": video_id,
                                "expected_status": expected_status.value,
                                "pipeline_version": pipeline_version,
                            },
                        ).rowcount
                    else:
                        changed = connection.execute(
                            "UPDATE videos SET pipeline_status = :target_status, "
                            "score = :score, should_summarize = :should_summarize, "
                            "updated_at = :now, completed_at = :completed_at "
                            "WHERE video_id = :video_id "
                            "AND pipeline_status = :expected_status "
                            "AND pipeline_version = :pipeline_version",
                            {
                                "target_status": target_status.value,
                                "score": scoring_summary.score,
                                "should_summarize": int(
                                    scoring_summary.should_summarize
                                ),
                                "now": now_text,
                                "completed_at": completed_at,
                                "video_id": video_id,
                                "expected_status": expected_status.value,
                                "pipeline_version": pipeline_version,
                            },
                        ).rowcount
                    if changed != 1:
                        msg = "pipeline changed before stage completion"
                        raise ConcurrencyConflict(msg)
                    self._inject_failure("stage.after_scoring_summary")
                    self._inject_failure("stage.after_pipeline")
                    job = self._finish_job_success_in_transaction(
                        connection, job_id=job_id, owner=owner, now=now_text
                    )
                    video_row = connection.execute(
                        "SELECT * FROM videos WHERE video_id = :video_id",
                        {"video_id": video_id},
                    ).fetchone()
                    if video_row is None:
                        msg = "completed video could not be read"
                        raise StateStoreError(msg)
                    return StageCompletionResult(
                        job=job,
                        video=self._video_from_row(video_row),
                        artifacts=stored_artifacts,
                        provider_call=completed_call,
                    )
            except sqlite3.IntegrityError as error:
                msg = "stage completion violates repository integrity"
                raise IntegrityConflict(msg) from error
        finally:
            connection.close()

    def upsert_report(self, report: ReportWrite, *, now: datetime) -> ReportRecord:
        if not report.report_id.strip() or not report.timezone.strip():
            msg = "report identifiers and timezone must be non-empty"
            raise ValueError(msg)
        if report.relative_path is not None:
            _validate_relative_path(report.relative_path)
        if report.content_hash is not None:
            _validate_sha256(report.content_hash, field_name="content_hash")
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            try:
                with _immediate_transaction(connection):
                    connection.execute(
                        "INSERT INTO reports "
                        "(report_id, timezone, iso_year, iso_week, report_type, "
                        "relative_path, content_hash, status, created_at, updated_at) "
                        "VALUES (:report_id, :timezone, :iso_year, :iso_week, 'weekly', "
                        ":relative_path, :content_hash, :status, :created_at, :updated_at) "
                        "ON CONFLICT(timezone, iso_year, iso_week, report_type) "
                        "DO UPDATE SET relative_path = excluded.relative_path, "
                        "content_hash = excluded.content_hash, status = excluded.status, "
                        "updated_at = excluded.updated_at",
                        {
                            "report_id": report.report_id,
                            "timezone": report.timezone,
                            "iso_year": report.iso_year,
                            "iso_week": report.iso_week,
                            "relative_path": report.relative_path,
                            "content_hash": report.content_hash,
                            "status": report.status.value,
                            "created_at": now_text,
                            "updated_at": now_text,
                        },
                    )
                    self._inject_failure("report.before_commit")
                    row = connection.execute(
                        "SELECT * FROM reports WHERE timezone = :timezone "
                        "AND iso_year = :iso_year AND iso_week = :iso_week "
                        "AND report_type = 'weekly'",
                        {
                            "timezone": report.timezone,
                            "iso_year": report.iso_year,
                            "iso_week": report.iso_week,
                        },
                    ).fetchone()
                    if row is None:
                        msg = "weekly report was not saved"
                        raise StateStoreError(msg)
                    return self._report_from_row(row)
            except sqlite3.IntegrityError as error:
                msg = "weekly report violates repository integrity"
                raise IntegrityConflict(msg) from error
        finally:
            connection.close()

    def get_report(
        self,
        *,
        timezone: str,
        iso_year: int,
        iso_week: int,
    ) -> ReportRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM reports WHERE timezone = :timezone "
                "AND iso_year = :iso_year AND iso_week = :iso_week "
                "AND report_type = 'weekly'",
                {
                    "timezone": timezone,
                    "iso_year": iso_year,
                    "iso_week": iso_week,
                },
            ).fetchone()
            return None if row is None else self._report_from_row(row)
        finally:
            connection.close()

    def list_weekly_candidates(
        self, *, start_utc: datetime, end_utc: datetime
    ) -> tuple[WeeklyCandidateRecord, ...]:
        """Return deterministically ordered potential weekly-report inputs.

        Artifact bytes and their domain payloads remain untrusted until the
        reporting service verifies them against these indexed records.
        """
        if start_utc >= end_utc:
            msg = "weekly candidate window must be non-empty"
            raise ValueError(msg)
        start_text = format_utc_datetime(start_utc)
        end_text = format_utc_datetime(end_utc)
        connection = self._connect()
        try:
            videos = connection.execute(
                "SELECT * FROM videos WHERE pipeline_status = :complete "
                "AND should_summarize = 1 AND score IS NOT NULL "
                "AND completed_at >= :start AND completed_at < :end "
                "ORDER BY score DESC, video_id ASC",
                {
                    "complete": PipelineStatus.COMPLETE.value,
                    "start": start_text,
                    "end": end_text,
                },
            ).fetchall()
            candidates: list[WeeklyCandidateRecord] = []
            for row in videos:
                video = self._video_from_row(row)
                note = connection.execute(
                    "SELECT * FROM artifacts WHERE artifact_key = :key "
                    "AND kind = :kind AND storage_root = :root "
                    "AND deleted_at IS NULL",
                    {
                        "key": f"video-note/{video.pipeline_version}/{video.video_id}",
                        "kind": ArtifactKind.VIDEO_NOTE.value,
                        "root": StorageRoot.VAULT.value,
                    },
                ).fetchone()
                score = _latest_weekly_artifact(
                    connection, video.video_id, ArtifactKind.SCORING_STRUCTURED
                )
                analysis = _latest_weekly_artifact(
                    connection, video.video_id, ArtifactKind.ANALYSIS_STRUCTURED
                )
                if note is not None and score is not None:
                    candidates.append(
                        WeeklyCandidateRecord(
                            video=video,
                            score_artifact=self._artifact_from_row(score),
                            analysis_artifact=(
                                None
                                if analysis is None
                                else self._artifact_from_row(analysis)
                            ),
                            note_artifact=self._artifact_from_row(note),
                        )
                    )
            return tuple(candidates)
        finally:
            connection.close()
