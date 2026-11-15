"""Single-snapshot read accelerator for hot Content and Intelligence GET routes.

Preserves 100% payload, error, and fail-closed verification parity with
``LocalApiApplication`` without touching sealed qualification files or holding
persistent SQLite locks between HTTP requests.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import sqlite3
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from http import HTTPStatus
from pathlib import Path, PurePosixPath
from types import FrameType
from typing import Any, BinaryIO, cast
from urllib.parse import parse_qs, urlparse

from youtube_intel.backup_restore import BackupRestoreError
from youtube_intel.content_summary_read import (
    AuthoritativeContentSummaryReader,
    ContentSummaryReadRejected,
)
from youtube_intel.domain import (
    AnalysisCompleted,
    JobStatus,
    PipelineStatus,
    ProcessingStage,
)
from youtube_intel.extractive_summary import (
    PROVIDER as EXTRACTIVE_PROVIDER,
)
from youtube_intel.extractive_summary import (
    ExtractiveSummaryService,
)
from youtube_intel.local_api import (
    ApiError,
    LocalApiApplication,
    _timestamp,
    _video_dto,
    serve_loopback,
)
from youtube_intel.model_settings import CredentialStoreError
from youtube_intel.offline_transcription import OfflineError
from youtube_intel.operations import ExitCode
from youtube_intel.source_authority import MAX_TEXT_BYTES, read_managed, verify_source
from youtube_intel.source_run import SourceRunChildState, SourceRunRecord
from youtube_intel.state import (
    ArtifactKind,
    ArtifactRecord,
    CurrentLocalSummaryPointer,
    EvidenceLineageKind,
    EvidenceRecord,
    IntegrityConflict,
    JobRecord,
    SourceSubscriptionRecord,
    SQLiteStateRepository,
    VerifiedEvidenceText,
    VerifiedTimedTranscript,
    VideoRecord,
)
from youtube_intel.summary_evidence_authority import LegacySummaryNotCurrentAuthority
from youtube_intel.tracked_content_retry import TrackedContentRetryService
from youtube_intel.tracked_retry_context import RetryIntegrity
from youtube_intel.workspace_intelligence_hub import WorkspaceIntelligenceHub

_VIDEO_DETAIL_ROUTE = re.compile(r"^/api/v1/videos/([^/]+)$")
_WS_AI_DISTILL_ROUTE = re.compile(r"^/api/v1/workspace-ai/videos/([^/]+)/distill$")
_WS_AI_TRANSCRIBE_ROUTE = re.compile(
    r"^/api/v1/workspace-ai/videos/([^/]+)/transcribe$"
)
_WS_AI_OBSIDIAN_ROUTE = re.compile(r"^/api/v1/workspace-ai/videos/([^/]+)/obsidian$")
_WS_AI_CURATION_ROUTE = re.compile(r"^/api/v1/workspace-ai/videos/([^/]+)/curation$")
_YT_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_INLINE_HASH_MAX_BYTES = 65_536


def _media_fast_token(path: Path) -> tuple[object, ...] | None:
    try:
        st = os.stat(path)
        with path.open("rb") as handle:
            head = handle.read(65_536)
            if st.st_size > 65_536:
                handle.seek(max(0, st.st_size - 65_536))
                tail = handle.read(65_536)
            else:
                tail = b""
        return (
            st.st_dev,
            st.st_ino,
            st.st_size,
            st.st_mtime_ns,
            st.st_ctime_ns,
            hashlib.sha256(head + tail).digest(),
        )
    except OSError:
        return None


def _sqlite_state_token(db_path: object) -> tuple[object, ...] | None:
    if not isinstance(db_path, Path):
        return None
    try:
        db_st = os.stat(db_path)
        with db_path.open("rb") as db_file:
            db_file.seek(24)
            header_24_40 = db_file.read(16)
    except OSError:
        return None
    wal_path = Path(f"{db_path}-wal")
    wal_token: tuple[object, ...] = ()
    try:
        wal_st = os.stat(wal_path)
        wal_head = b""
        wal_tail = b""
        if wal_st.st_size > 0:
            with wal_path.open("rb") as wal_file:
                wal_head = wal_file.read(32)
                if wal_st.st_size > 64:
                    wal_file.seek(wal_st.st_size - 64)
                else:
                    wal_file.seek(0)
                wal_tail = wal_file.read(64)
        wal_token = (
            wal_st.st_dev,
            wal_st.st_ino,
            wal_st.st_size,
            wal_st.st_mtime_ns,
            wal_head,
            wal_tail,
        )
    except OSError:
        wal_token = ()
    journal_exists = os.path.exists(f"{db_path}-journal")
    return (
        db_st.st_dev,
        db_st.st_ino,
        db_st.st_size,
        db_st.st_mtime_ns,
        header_24_40,
        wal_token,
        journal_exists,
    )


def _data_root_token(data_root: Path | None) -> tuple[object, ...]:
    if data_root is None or not data_root.is_dir():
        return ()
    entries: list[tuple[object, ...]] = []
    root_str = str(data_root)
    for dirpath, dirnames, filenames in os.walk(root_str):
        dirnames.sort()
        filenames.sort()
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            try:
                st = os.stat(fpath, follow_symlinks=False)
                if st.st_size <= _INLINE_HASH_MAX_BYTES and os.path.isfile(fpath):
                    with open(fpath, "rb") as handle:
                        digest = hashlib.sha256(handle.read()).digest()
                    entries.append(
                        (
                            fpath[len(root_str) :],
                            st.st_dev,
                            st.st_ino,
                            st.st_size,
                            digest,
                        )
                    )
                else:
                    entries.append(
                        (
                            fpath[len(root_str) :],
                            st.st_dev,
                            st.st_ino,
                            st.st_size,
                            st.st_mtime_ns,
                            st.st_ctime_ns,
                        )
                    )
            except OSError:
                entries.append((fpath[len(root_str) :], None))
    return tuple(entries)


class _PinnedSnapshotConnection:
    """Non-closing wrapper over a caller-owned read-snapshot ``sqlite3.Connection``."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def __enter__(self) -> _PinnedSnapshotConnection:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def close(self) -> None:
        return None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)


class _SnapshotReadRepository:
    """Read-only repository view executing within a single SQLite read snapshot."""

    def __init__(
        self,
        repository: SQLiteStateRepository,
        connection: sqlite3.Connection,
        *,
        videos_by_id: dict[str, VideoRecord] | None = None,
    ) -> None:
        self._repository = repository
        self._connection = connection
        self._pinned = _PinnedSnapshotConnection(connection)
        self._videos: dict[str, VideoRecord | None] = (
            {} if videos_by_id is None else dict(videos_by_id)
        )
        self._artifacts: dict[str, ArtifactRecord | None] = {}
        self._evidence: dict[str, EvidenceRecord | None] = {}
        self._timed: dict[str, VerifiedTimedTranscript | None] = {}
        self._verified_text: dict[str, VerifiedEvidenceText | None] = {}

    def _connect(self, *, read_only: bool = False) -> sqlite3.Connection:  # noqa: ARG002
        return cast(sqlite3.Connection, self._pinned)

    def bind_source_storage(self, data_root: Path) -> None:
        self._repository.bind_source_storage(data_root)

    def get_video(self, video_id: str) -> VideoRecord | None:
        if video_id in self._videos:
            return self._videos[video_id]
        row = self._connection.execute(
            "SELECT * FROM videos WHERE video_id = :video_id",
            {"video_id": video_id},
        ).fetchone()
        record = None if row is None else self._repository._video_from_row(row)
        self._videos[video_id] = record
        return record

    def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        if artifact_id in self._artifacts:
            return self._artifacts[artifact_id]
        row = self._connection.execute(
            "SELECT * FROM artifacts WHERE artifact_id = :artifact_id",
            {"artifact_id": artifact_id},
        ).fetchone()
        record = None if row is None else self._repository._artifact_from_row(row)
        self._artifacts[artifact_id] = record
        return record

    def latest_artifact(
        self, video_id: str, kind: ArtifactKind
    ) -> ArtifactRecord | None:
        row = self._connection.execute(
            "SELECT * FROM artifacts WHERE video_id = :video_id AND kind = :kind "
            "AND deleted_at IS NULL ORDER BY created_at DESC, artifact_id DESC LIMIT 1",
            {"video_id": video_id, "kind": kind.value},
        ).fetchone()
        if row is None:
            return None
        record = self._repository._artifact_from_row(row)
        self._artifacts[record.artifact_id] = record
        return record

    def get_evidence(self, evidence_id: str) -> EvidenceRecord | None:
        if evidence_id in self._evidence:
            return self._evidence[evidence_id]
        row = self._connection.execute(
            "SELECT * FROM evidence WHERE evidence_id = :evidence_id",
            {"evidence_id": evidence_id},
        ).fetchone()
        record = None if row is None else self._repository._evidence_from_row(row)
        self._evidence[evidence_id] = record
        return record

    def list_evidence_for_presentation(self, video_id: str) -> tuple[str, ...]:
        promoted = self._repository._evidence_ids_for_lineages_in_snapshot(
            self._connection,
            video_id,
            lineage_kinds=(EvidenceLineageKind.EXTRACTION,),
        )
        canonical = self._repository._evidence_ids_for_lineages_in_snapshot(
            self._connection,
            video_id,
            lineage_kinds=(EvidenceLineageKind.ORIGINAL_TRANSCRIPT,),
        )
        return promoted + canonical

    def get_verified_timed_transcript(
        self, *, video_id: str
    ) -> VerifiedTimedTranscript | None:
        if (
            not isinstance(video_id, str)
            or not video_id.strip()
            or video_id != video_id.strip()
            or len(video_id) > 512
        ):
            raise ValueError("video identity is invalid")
        if video_id not in self._timed:
            self._timed[video_id] = (
                self._repository._get_verified_timed_transcript_in_transaction(
                    self._connection, video_id
                )
            )
        return self._timed[video_id]

    def resolve_verified_evidence_text(
        self, evidence_id: str
    ) -> VerifiedEvidenceText | None:
        if evidence_id not in self._verified_text:
            self._verified_text[evidence_id] = (
                self._repository._resolve_verified_evidence_text_in_transaction(
                    self._connection, evidence_id
                )
            )
        return self._verified_text[evidence_id]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._repository, name)


class _RequestSnapshotContext:
    """Per-request read projection context sharing one SQLite snapshot."""

    def __init__(
        self,
        inner: LocalApiApplication,
        connection: sqlite3.Connection,
        *,
        videos_by_id: dict[str, VideoRecord] | None = None,
        verified_source_memo: dict[tuple[object, ...], dict[str, Any] | None] | None = None,
        memo_lock: threading.Lock | None = None,
    ) -> None:
        self.inner = inner
        self.repo = inner._repository
        self.conn = connection
        self.snap_repo = _SnapshotReadRepository(
            self.repo, connection, videos_by_id=videos_by_id
        )
        self._verified_source_memo = (
            {} if verified_source_memo is None else verified_source_memo
        )
        self._memo_lock = memo_lock
        self._sources: tuple[SourceSubscriptionRecord, ...] | None = None
        self._runs: tuple[SourceRunRecord, ...] | None = None
        self._runs_by_source: dict[str, list[SourceRunRecord]] | None = None
        self._yt_retry_sources: dict[str, tuple[SourceSubscriptionRecord, ...]] | None = None
        self._local_pointers: dict[str, CurrentLocalSummaryPointer] | None = None
        self._notes: dict[str, dict[str, object]] = {}
        self._jobs_loaded = False
        self._newest_any_job: dict[str, JobRecord] = {}
        self._newest_transcript_job: dict[str, JobRecord] = {}
        self._retry_video_ids: set[str] | None = None
        self._snap_retry_service: TrackedContentRetryService | None = None

    def sources(self) -> tuple[SourceSubscriptionRecord, ...]:
        if self._sources is None:
            self._sources = tuple(
                self.repo._source_from_row(row)
                for row in self.conn.execute(
                    "SELECT * FROM source_subscriptions ORDER BY created_at DESC, source_id"
                )
            )
        return self._sources

    def yt_retry_sources_by_video(
        self,
    ) -> dict[str, tuple[SourceSubscriptionRecord, ...]]:
        if self._yt_retry_sources is None:
            grouped: dict[str, list[SourceSubscriptionRecord]] = {}
            for source in self.sources():
                if (
                    source.enabled
                    and source.source_type.value == "VIDEO_URL"
                    and source.video_id is not None
                ):
                    grouped.setdefault(source.video_id, []).append(source)
            self._yt_retry_sources = {k: tuple(v) for k, v in grouped.items()}
        return self._yt_retry_sources

    def runs_by_source(self) -> dict[str, list[SourceRunRecord]]:
        if self._runs_by_source is None:
            grouped: dict[str, list[SourceRunRecord]] = {}
            rows = self.conn.execute(
                "SELECT * FROM source_runs ORDER BY created_at ASC, run_id ASC"
            )
            for row in rows:
                run = self.repo._source_run_from_row(row)
                grouped.setdefault(run.source_id, []).append(run)
            self._runs_by_source = grouped
        return self._runs_by_source

    def local_summary_pointer(self, video_id: str) -> CurrentLocalSummaryPointer | None:
        if self._local_pointers is None:
            pointers: dict[str, CurrentLocalSummaryPointer] = {}
            for row in self.conn.execute(
                "SELECT video_id, analysis_artifact_id, output_language "
                "FROM current_content_summaries WHERE analysis_artifact_id IS NOT NULL"
            ):
                pointers[str(row["video_id"])] = CurrentLocalSummaryPointer(
                    artifact_id=str(row["analysis_artifact_id"]),
                    output_language=str(row["output_language"]),
                )
            self._local_pointers = pointers
        return self._local_pointers.get(video_id)

    def latest_content_job(self, video_id: str) -> JobRecord | None:
        if not self._jobs_loaded:
            for row in self.conn.execute(
                "SELECT * FROM jobs WHERE job_type = 'VIDEO_STAGE' AND video_id IS NOT NULL "
                "ORDER BY updated_at DESC, CASE WHEN status = 'SUCCEEDED' THEN 1 ELSE 0 END, job_id DESC"
            ):
                vid = str(row["video_id"])
                if vid not in self._newest_any_job:
                    self._newest_any_job[vid] = self.repo._job_from_row(row)
                if (
                    row["target_stage"] == ProcessingStage.TRANSCRIPT.value
                    and vid not in self._newest_transcript_job
                ):
                    self._newest_transcript_job[vid] = self.repo._job_from_row(row)
            self._jobs_loaded = True
        job = self._newest_any_job.get(video_id)
        if (
            job is not None
            and job.status is JobStatus.SUCCEEDED
            and job.target_stage is ProcessingStage.METADATA
        ):
            caption = self._newest_transcript_job.get(video_id)
            if caption is not None and caption.status is not JobStatus.SUCCEEDED:
                return caption
        return job

    def note_projection(self, video_id: str) -> dict[str, object]:
        if video_id in self._notes:
            return self._notes[video_id]
        projected = self._compute_note_projection(video_id)
        self._notes[video_id] = projected
        return projected

    def _compute_note_projection(self, video_id: str) -> dict[str, object]:
        local_pointer = self.local_summary_pointer(video_id)
        analysis_reader = self.inner._analysis_reader
        snap_repo_typed = cast(SQLiteStateRepository, self.snap_repo)
        if local_pointer is not None:
            artifact = self.snap_repo.get_artifact(local_pointer.artifact_id)
            if (
                artifact is not None
                and artifact.provider == EXTRACTIVE_PROVIDER
                and self.inner._data_root is not None
            ):
                analysis_reader = ExtractiveSummaryService(
                    snap_repo_typed, self.inner._data_root
                ).read
            if analysis_reader is None:
                return {
                    "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
                    "v2": {"status": "UNAVAILABLE", "code": "CURRENT_SUMMARY_INVALID"},
                }
            try:
                outcome = analysis_reader(video_id, local_pointer.artifact_id)
            except LegacySummaryNotCurrentAuthority:
                return {
                    "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
                    "v2": {
                        "status": "UNAVAILABLE",
                        "code": "CURRENT_SUMMARY_LEGACY_REGENERATION_REQUIRED",
                    },
                }
            except (ValueError, OSError):
                outcome = None
            if not isinstance(outcome, AnalysisCompleted):
                return {
                    "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
                    "v2": {"status": "UNAVAILABLE", "code": "CURRENT_SUMMARY_INVALID"},
                }
            result = outcome.result
            summary_language = local_pointer.output_language
            content = self.snap_repo.get_video(video_id)
            if result.provider == EXTRACTIVE_PROVIDER:
                summary_language = (
                    "und" if content is None else content.default_language or "und"
                )
            verified_refs = (
                {
                    item.evidence_id: self.snap_repo.resolve_verified_evidence_text(
                        item.evidence_id
                    )
                    for item in result.evidence
                }
                if content is not None and content.provider in {"LOCAL", "BILIBILI"}
                else {}
            )
            timed_points: list[dict[str, object]] = []
            for point in result.core_points:
                spans = [
                    verified_refs[eid]
                    for eid in point.evidence_ids
                    if verified_refs.get(eid) is not None
                ]
                if spans and all(
                    span is not None
                    and span.video_id == video_id
                    and span.start_ms is not None
                    and span.end_ms is not None
                    for span in spans
                ):
                    timed_points.append(
                        {
                            "text": point.text,
                            "start_seconds": min(
                                span.start_ms
                                for span in spans
                                if span is not None and span.start_ms is not None
                            )
                            / 1000,
                            "end_seconds": max(
                                span.end_ms
                                for span in spans
                                if span is not None and span.end_ms is not None
                            )
                            / 1000,
                            "evidence_ids": list(point.evidence_ids),
                        }
                    )
            return {
                "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
                "v2": {
                    "status": "AVAILABLE",
                    "note_identity": f"analysis/{result.request_hash}/structured",
                    "result_identity": result.request_hash,
                    "language": summary_language,
                    "summary": result.one_sentence_summary,
                    "method": (
                        "SOURCE_EXCERPTS"
                        if result.provider == EXTRACTIVE_PROVIDER
                        else "MODEL_SUMMARY"
                    ),
                    "core_points": [point.text for point in result.core_points],
                    "timestamped_key_points": timed_points,
                    "evidence_references": [
                        {
                            "evidence_id": item.evidence_id,
                            "source": item.source.value,
                            "excerpt": item.excerpt,
                            "start_seconds": (
                                None
                                if (ref := verified_refs.get(item.evidence_id)) is None
                                or ref.start_ms is None
                                else ref.start_ms / 1000
                            ),
                            "end_seconds": (
                                None
                                if ref is None or ref.end_ms is None
                                else ref.end_ms / 1000
                            ),
                        }
                        for item in result.evidence
                    ],
                },
            }
        try:
            current = AuthoritativeContentSummaryReader(snap_repo_typed).read_current(
                video_id
            )
        except ContentSummaryReadRejected as error:
            return {
                "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
                "v2": {"status": "UNAVAILABLE", "code": error.code},
            }
        note = current.note
        summary = next(
            (
                section.entries[0].text
                for section in note.sections
                if section.kind.value == "SUMMARY" and section.entries
            ),
            None,
        )
        core_point_entries = next(
            (
                tuple(section.entries)
                for section in note.sections
                if section.kind.value == "CORE_POINTS"
            ),
            (),
        )
        core_points = [entry.text for entry in core_point_entries]
        references_by_id = {
            reference.evidence_id: reference for reference in note.evidence_references
        }
        timestamped_key_points: list[dict[str, object]] = []
        for entry in core_point_entries:
            timed = [
                references_by_id[evidence_id]
                for evidence_id in entry.evidence_ids
                if evidence_id in references_by_id
                and references_by_id[evidence_id].start_seconds is not None
            ]
            if not timed:
                continue
            start_seconds = min(
                float(reference.start_seconds)
                for reference in timed
                if reference.start_seconds is not None
            )
            end_seconds = max(
                float(
                    reference.end_seconds
                    if reference.end_seconds is not None
                    else reference.start_seconds
                )
                for reference in timed
                if reference.start_seconds is not None
            )
            timestamped_key_points.append(
                {
                    "text": entry.text,
                    "start_seconds": start_seconds,
                    "end_seconds": end_seconds,
                    "evidence_ids": [
                        reference.evidence_id
                        for reference in sorted(
                            timed,
                            key=lambda item: (
                                float(item.start_seconds or 0),
                                item.evidence_id,
                            ),
                        )
                    ],
                }
            )
        return {
            "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
            "v2": {
                "status": "AVAILABLE",
                "note_identity": note.identity,
                "result_identity": current.result_identity,
                "language": note.language,
                "summary": summary,
                "core_points": core_points,
                "timestamped_key_points": timestamped_key_points,
                "evidence_references": [
                    {
                        "evidence_id": reference.evidence_id,
                        "source": reference.source,
                        "excerpt": reference.excerpt,
                        "start_seconds": reference.start_seconds,
                        "end_seconds": reference.end_seconds,
                    }
                    for reference in note.evidence_references
                ],
            },
        }

    def manual_content_source(self, video_id: str) -> str | None:
        video = self.snap_repo.get_video(video_id)
        note = self.note_projection(video_id).get("v2")
        if video is not None and video.provider == "LOCAL":
            for source in self.sources():
                if (
                    self.repo._manual_local_timed_context_hash(
                        self.conn, source.source_id, video_id
                    )
                    is not None
                    or self.repo._manual_local_text_context_hash(
                        self.conn, source.source_id, video_id
                    )
                    is not None
                ):
                    return source.source_id
            return None
        if (
            video is None
            or video.provider != "YOUTUBE"
            or not isinstance(note, dict)
            or note.get("status") != "AVAILABLE"
        ):
            return None
        if self.snap_repo.get_verified_timed_transcript(video_id=video_id) is None:
            return None
        row = self.conn.execute(
            "SELECT s.source_id FROM source_subscriptions AS s "
            "JOIN source_video_links AS l ON l.source_id = s.source_id "
            "WHERE l.video_id = ? ORDER BY s.created_at DESC, s.source_id LIMIT 1",
            (video_id,),
        ).fetchone()
        return None if row is None else str(row[0])

    def tracked_retry_status(self, video: VideoRecord) -> dict[str, object]:
        assert self.inner._tracked_content_retry is not None
        if self._retry_video_ids is None:
            self._retry_video_ids = {
                str(row[0])
                for row in self.conn.execute(
                    "SELECT DISTINCT video_id FROM tracked_content_retry_requests"
                )
            }
        if (
            video.video_id not in self._retry_video_ids
            and video.pipeline_status is not PipelineStatus.METADATA_READY
        ):
            return {
                "request": None,
                "retry_allowed": False,
                "expected_job_id": None,
            }
        if self._snap_retry_service is None:
            orig_retry = self.inner._tracked_content_retry
            self._snap_retry_service = TrackedContentRetryService(
                cast(SQLiteStateRepository, self.snap_repo),
                orig_retry.data_root,
                adapter_factory=orig_retry.adapter_factory,
                language_preferences=orig_retry.languages,
                metadata_for_video=orig_retry.metadata_for_video,
                now=orig_retry.now,
            )
        try:
            return self._snap_retry_service.status(video.video_id)
        except (RetryIntegrity, ValueError, OSError, sqlite3.Error):
            return {
                "request": None,
                "retry_allowed": False,
                "expected_job_id": None,
                "error_code": "RETRY_INTEGRITY_INVALID",
            }

    def video_dto_with_deep_analysis(
        self,
        video: VideoRecord,
        *,
        shared_da_status: tuple[str, str | None] | None = None,
    ) -> dict[str, object]:
        if self.inner._deep_analysis_service is None:
            projection = _video_dto(
                video,
                deep_analysis_status="UNAVAILABLE",
                deep_analysis_reason="Deep Analysis is unavailable.",
            )
        elif shared_da_status is not None:
            projection = _video_dto(
                video,
                deep_analysis_status=shared_da_status[0],
                deep_analysis_reason=shared_da_status[1],
            )
        else:
            da = self.inner._deep_analysis_service.status(content_id=video.video_id)
            projection = _video_dto(
                video,
                deep_analysis_status=da.availability.value,
                deep_analysis_reason=da.reason,
            )
        if video.provider in {"LOCAL", "BILIBILI"}:
            source = self.verified_source(video.video_id)
            if source is None:
                projection["processing_status"] = "SOURCE_UNAVAILABLE"
            else:
                projection.update(
                    {
                        "processing_status": source["status"],
                        "filename": source["filename"],
                        "media_kind": source["media_kind"],
                        "format": source["format"],
                        "imported_at": source["imported_at"],
                        "source_language": source["language"],
                        "duration_seconds": source["duration_seconds"],
                    }
                )
                if video.provider == "BILIBILI" and self.inner._data_root is not None:
                    artifact = self.snap_repo.get_artifact(
                        str(source["snapshot_artifact_id"])
                    )
                    if artifact is not None:
                        metadata = json.loads(
                            read_managed(
                                self.inner._data_root,
                                artifact.relative_path,
                                maximum=256 * 1024,
                            )
                        )
                        projection.update(
                            source_url=metadata["canonical_url"],
                            channel_name=metadata["uploader_name"],
                            uploader_id=metadata["uploader_id"],
                            published_at=metadata["published_at"],
                        )
        if (
            video.provider == "LOCAL"
            and self.inner._transcription_jobs is not None
            and projection.get("media_kind") in {"AUDIO", "VIDEO"}
        ):
            try:
                state = self.inner._transcription_jobs.status(video.video_id)["status"]
                if state in {"RUNNING", "FAILED", "INTERRUPTED"}:
                    projection["processing_status"] = (
                        "TRANSCRIPTION_FAILED" if state == "FAILED" else state
                    )
            except OfflineError:
                projection["processing_status"] = "SOURCE_UNAVAILABLE"
        if video.provider == "YOUTUBE":
            retry_sources = self.yt_retry_sources_by_video().get(video.video_id, ())
            if retry_sources:
                projection["source_id"] = retry_sources[0].source_id
            job = self.latest_content_job(video.video_id)
            projection["processing_job"] = (
                None
                if job is None
                else {
                    "status": job.status.value,
                    "stage": (
                        job.target_stage.value if job.target_stage is not None else None
                    ),
                    "retry_at": _timestamp(job.available_at),
                    "error_code": job.last_error_code,
                }
            )
            projection["retry_allowed"] = not (
                job is not None
                and job.status.value == "FAILED_FINAL"
                and job.last_error_code
                in {"CAPABILITY_UNAVAILABLE", "TRUST_INTEGRITY_INVALID"}
            )
            has_local_summary = self.local_summary_pointer(video.video_id) is not None
            if job is not None and job.status.value in {
                "PENDING",
                "RUNNING",
                "RETRY_PENDING",
                "FAILED_FINAL",
            }:
                projection["processing_status"] = (
                    ("RETRY_REQUIRED" if retry_sources else "RETRY_PENDING")
                    if job.status.value == "RETRY_PENDING"
                    else "FAILED"
                    if job.status.value == "FAILED_FINAL"
                    else "READING_CAPTIONS"
                    if job.target_stage is not None
                    and job.target_stage.value == "TRANSCRIPT"
                    else "FETCHING"
                )
            elif has_local_summary:
                summary = self.note_projection(video.video_id).get("v2")
                projection["processing_status"] = (
                    "ORGANIZED"
                    if isinstance(summary, dict) and summary.get("status") == "AVAILABLE"
                    else "NEEDS_ATTENTION"
                )
            elif (
                video.pipeline_status is PipelineStatus.TRANSCRIPT_READY
                and self.snap_repo.get_verified_timed_transcript(video_id=video.video_id)
                is None
            ):
                projection["processing_status"] = "NEEDS_ATTENTION"
                projection["caption_timing_status"] = "UNAVAILABLE"

            if retry_sources:
                runs_map = self.runs_by_source()
                source_runs_list: list[SourceRunRecord] = []
                for retry_src in retry_sources:
                    source_runs_list.extend(runs_map.get(retry_src.source_id, ()))
                source_runs_list.sort(key=lambda item: (item.created_at, item.run_id))
                source_runs = tuple(source_runs_list)
            else:
                source_runs = ()
            active_source = any(
                run.state.value in {"QUEUED", "RUNNING"} for run in source_runs
            )
            latest_run = source_runs[-1] if source_runs else None
            if (
                not active_source
                and latest_run is not None
                and latest_run.state.value == "NEEDS_ATTENTION"
                and any(
                    source.source_id == latest_run.source_id
                    and source.processing_policy.value == "DISCOVER_ONLY"
                    for source in retry_sources
                )
                and job is not None
                and job.status is JobStatus.SUCCEEDED
                and video.pipeline_status is PipelineStatus.TRANSCRIPT_READY
                and not has_local_summary
                and self.snap_repo.get_verified_timed_transcript(video_id=video.video_id)
                is not None
            ):
                projection["processing_status"] = "RETRY_REQUIRED"
                projection["summary_preparation_status"] = "NEEDS_ATTENTION"
            if (
                retry_sources
                and not active_source
                and job is not None
                and job.status is JobStatus.PENDING
                and job.last_error_code is not None
            ):
                projection["processing_status"] = "RETRY_REQUIRED"
            if active_source:
                projection["processing_status"] = "WAITING"
        if video.provider == "YOUTUBE" and self.inner._tracked_content_retry is not None:
            projection["tracked_content_retry"] = self.tracked_retry_status(video)
        return projection

    def pending_content_work(self) -> list[dict[str, object]]:
        rows = self.conn.execute(
            "SELECT s.source_id,s.video_id,s.canonical_url,s.created_at,NULL AS enrollment "
            "FROM source_subscriptions s LEFT JOIN videos v ON v.video_id=s.video_id "
            "WHERE s.provider='YOUTUBE' AND s.source_type='VIDEO_URL' AND v.video_id IS NULL "
            "UNION ALL SELECT o.source_id,o.canonical_identity,'https://www.youtube.com/watch?v='||o.canonical_identity,o.observed_at,o.enrollment "
            "FROM source_observations o JOIN source_subscriptions s USING(source_id) "
            "LEFT JOIN videos v ON v.video_id=o.canonical_identity "
            "WHERE s.provider='YOUTUBE' AND o.baseline=0 AND v.video_id IS NULL LIMIT 100"
        ).fetchall()
        if not rows:
            return []
        runs_map = self.runs_by_source()
        items: dict[str, dict[str, object]] = {}
        for row in rows:
            video_id = row["video_id"]
            if _YT_VIDEO_ID.fullmatch(video_id or "") is None:
                continue
            own_runs = runs_map.get(str(row["source_id"]), [])
            latest = own_runs[-1] if own_runs else None
            state = "WAITING"
            if row["enrollment"] in {"UNSUPPORTED", "UNAVAILABLE"} or (
                latest
                and latest.state.value in {"FAILED", "NEEDS_ATTENTION", "AMBIGUOUS"}
            ):
                state = "NEEDS_ATTENTION"
            elif latest and latest.state.value == "RUNNING":
                state = "FETCHING"
            items[str(video_id)] = {
                "video_id": video_id,
                "provider": "YOUTUBE",
                "title": row["canonical_url"],
                "source_url": row["canonical_url"],
                "channel_id": None,
                "channel_name": None,
                "published_at": None,
                "last_updated": row["created_at"],
                "processing_status": state,
                "work_kind": "DURABLE_CONTENT_IDENTITY",
                "source_id": row["source_id"],
            }
        return list(items.values())

    def verified_source(self, content_id: str) -> dict[str, Any] | None:
        snap_repo_typed = cast(SQLiteStateRepository, self.snap_repo)
        root = self.repo._source_data_root
        if root is not None:
            snap_row = self.conn.execute(
                "SELECT * FROM content_source_snapshots WHERE content_id=?",
                (content_id,),
            ).fetchone()
            if (
                snap_row is not None
                and snap_row["provider"] == "LOCAL"
                and snap_row["media_kind"] != "TEXT"
            ):
                vid_row = self.conn.execute(
                    "SELECT provider, availability FROM videos WHERE video_id=?",
                    (content_id,),
                ).fetchone()
                sub_row = self.conn.execute(
                    "SELECT provider FROM source_subscriptions WHERE source_id=?",
                    (snap_row["source_id"],),
                ).fetchone()
                art_row = self.conn.execute(
                    "SELECT * FROM artifacts WHERE artifact_id=?",
                    (snap_row["snapshot_artifact_id"],),
                ).fetchone()
                media_token = (
                    None
                    if art_row is None
                    else _media_fast_token(root / str(art_row["relative_path"]))
                )
                if media_token is not None:
                    memo_key: tuple[object, ...] = (
                        content_id,
                        tuple(snap_row),
                        None if vid_row is None else tuple(vid_row),
                        None if sub_row is None else tuple(sub_row),
                        None if art_row is None else tuple(art_row),
                        media_token,
                    )
                    if self._memo_lock is not None:
                        with self._memo_lock:
                            if memo_key in self._verified_source_memo:
                                return self._verified_source_memo[memo_key]
                    elif memo_key in self._verified_source_memo:
                        return self._verified_source_memo[memo_key]
                    raw_verified = verify_source(snap_repo_typed, self.conn, content_id)
                    cached_val = None if raw_verified is None else dict(raw_verified)
                    if self._memo_lock is not None:
                        with self._memo_lock:
                            if len(self._verified_source_memo) > 512:
                                self._verified_source_memo.clear()
                            self._verified_source_memo[memo_key] = cached_val
                    else:
                        self._verified_source_memo[memo_key] = cached_val
                    return cached_val
        raw_res = verify_source(snap_repo_typed, self.conn, content_id)
        return None if raw_res is None else dict(raw_res)

    def transcript_projection(self, video: VideoRecord) -> dict[str, object]:
        if video.provider in {"LOCAL", "BILIBILI"}:
            source = self.verified_source(video.video_id)
            if source is None:
                return {
                    "status": "UNAVAILABLE",
                    "code": f"{video.provider}_SOURCE_UNTRUSTED",
                }
            if source["status"] != "READY":
                return {"status": source["status"], "code": source["status"]}
        artifact = self.snap_repo.latest_artifact(
            video.video_id, ArtifactKind.TRANSCRIPT_CANONICAL
        )
        if artifact is not None:
            relative = PurePosixPath(artifact.relative_path)
            if (
                artifact.video_id != video.video_id
                or artifact.kind is not ArtifactKind.TRANSCRIPT_CANONICAL
                or artifact.deleted_at is not None
                or artifact.storage_root.value != "DATA"
                or relative.parts[:1] != ("transcripts",)
            ):
                text = None
            else:
                text = self.inner._safe_artifact_text(
                    self.inner._data_root,
                    artifact,
                    max_bytes=(
                        MAX_TEXT_BYTES
                        if video.provider in {"LOCAL", "BILIBILI"}
                        else 1_000_000
                    ),
                )
            if text is not None:
                timed = self.snap_repo.get_verified_timed_transcript(
                    video_id=video.video_id
                )
                return {
                    "status": "AVAILABLE",
                    **(
                        {
                            "timed_segments": [
                                {
                                    "start_ms": cue.start_ms,
                                    "end_ms": cue.end_ms,
                                    "text": cue.text,
                                }
                                for cue in timed.cues
                            ]
                        }
                        if timed is not None
                        else {}
                    ),
                    "text": text,
                    "created_at": _timestamp(artifact.created_at),
                    "content_length": len(text),
                }
            return {
                "status": "UNAVAILABLE",
                "code": "TRANSCRIPT_UNAVAILABLE",
                "reason": "The recorded canonical transcript cannot be safely read.",
            }
        row = self.conn.execute(
            "SELECT * FROM jobs WHERE video_id = :video_id AND job_type = 'VIDEO_STAGE' "
            "AND target_stage = 'TRANSCRIPT' "
            "ORDER BY updated_at DESC, CASE WHEN status = 'SUCCEEDED' THEN 1 ELSE 0 END, job_id DESC LIMIT 1",
            {"video_id": video.video_id},
        ).fetchone()
        job = None if row is None else self.repo._job_from_row(row)
        if job is not None and job.status is JobStatus.FAILED_FINAL:
            return {
                "status": "FAILED",
                "code": job.last_error_code or "TRANSCRIPT_FAILED",
                "reason": "Transcript processing ended without a canonical transcript.",
            }
        return {
            "status": "NOT_PROCESSED",
            "reason": "No canonical transcript has been recorded for this video.",
        }


class FastReadApiApplication:
    """Drop-in wrapper around ``LocalApiApplication`` accelerating hot GET reads."""

    def __init__(
        self,
        inner: LocalApiApplication,
        *,
        workspace_hub: WorkspaceIntelligenceHub | None = None,
    ) -> None:
        self._inner = inner
        self._workspace_hub = (
            workspace_hub
            if workspace_hub is not None
            else WorkspaceIntelligenceHub(
                repository=inner._repository,
                data_root=inner._data_root,
                now=inner._now,
            )
        )
        self._cache_lock = threading.Lock()
        self._mutation_epoch = 0
        self._route_cache: dict[str, tuple[tuple[object, ...], str]] = {}
        self._local_av_ids: tuple[str, ...] = ()
        self._verified_source_memo: dict[tuple[object, ...], dict[str, Any] | None] = {}

    def _bump_mutation_epoch(self) -> None:
        with self._cache_lock:
            self._mutation_epoch += 1
            self._route_cache.clear()

    def _cache_fingerprint(self) -> tuple[object, ...] | None:
        repo = self._inner._repository
        if "latest_distillation_execution_for_video" in repo.__dict__:
            return None
        db_token = _sqlite_state_token(getattr(repo, "_database_path", None))
        if db_token is None:
            return None
        hub_token = (
            _sqlite_state_token(self._workspace_hub.db_path)
            if self._workspace_hub.has_sidecar_db()
            else None
        )
        data_token = _data_root_token(self._inner._data_root)
        da_service = self._inner._deep_analysis_service
        da_route = (
            None
            if da_service is None
            else str(da_service._capability.execution_route())
        )
        li_settings = self._inner._local_intelligence_settings
        li_adm = None if li_settings is None else li_settings.admission_allowed()
        tx_jobs = self._inner._transcription_jobs
        tx_states: list[tuple[str, str]] = []
        with self._cache_lock:
            local_av_ids = self._local_av_ids
            mutation_epoch = self._mutation_epoch
        if tx_jobs is not None and local_av_ids:
            for vid in local_av_ids:
                try:
                    tx_states.append((vid, str(tx_jobs.status(vid)["status"])))
                except OfflineError as err:
                    tx_states.append((vid, f"OFFLINE:{err.code}"))
        return (
            mutation_epoch,
            db_token,
            hub_token,
            data_token,
            da_route,
            self._inner._cloud_execution_enabled,
            self._inner._cloud_intelligence_qualified,
            self._inner._cloud_credential_available,
            self._inner._local_distillation_available,
            li_adm,
            tuple(tx_states),
        )

    def enable_native_import(
        self, origins: tuple[str, ...], *, picker_executable: Path
    ) -> None:
        self._inner.enable_native_import(origins, picker_executable=picker_executable)

    def shutdown_native_import(self) -> None:
        self._inner.shutdown_native_import()

    def native_request(
        self, method: str, route: str, body: bytes, origin: str
    ) -> tuple[int, dict[str, object]]:
        if method not in {"GET", "HEAD"}:
            self._bump_mutation_epoch()
        res = self._inner.native_request(method, route, body, origin)
        if method not in {"GET", "HEAD"}:
            self._bump_mutation_epoch()
        return res

    def handle_stream(
        self,
        path: str,
        stream: BinaryIO,
        length: int,
        *,
        cancelled: Callable[[], bool] | None = None,
    ) -> tuple[int, dict[str, object]]:
        self._bump_mutation_epoch()
        try:
            return self._inner.handle_stream(path, stream, length, cancelled=cancelled)
        finally:
            self._bump_mutation_epoch()

    def backup_download(
        self, path: str
    ) -> tuple[int, dict[str, str], bytes | Path] | None:
        parsed = urlparse(path)
        if parsed.path.rstrip("/") == "/api/v1/workspace-ai/obsidian-bundle.zip":
            q_params = parse_qs(parsed.query, keep_blank_values=False) if parsed.query else {}
            req_scope = (q_params.get("scope") or ["must_watch"])[0]
            try:
                filename, zip_bytes, _, _ = self._workspace_hub.build_obsidian_vault_zip(
                    scope=req_scope
                )
            except ValueError as err:
                err_bytes = json.dumps(
                    {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": str(err) or "Request values are invalid.",
                        }
                    }
                ).encode("utf-8")
                return (
                    int(HTTPStatus.UNPROCESSABLE_ENTITY),
                    {"Content-Type": "application/json; charset=utf-8"},
                    err_bytes,
                )
            return (
                int(HTTPStatus.OK),
                {
                    "Content-Type": "application/zip",
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
                zip_bytes,
            )
        return self._inner.backup_download(path)

    def _cached_or_compute(
        self, route: str, compute: Callable[[], dict[str, object]]
    ) -> dict[str, object]:
        fp_before = self._cache_fingerprint()
        if fp_before is not None:
            with self._cache_lock:
                cached = self._route_cache.get(route)
            if cached is not None and cached[0] == fp_before:
                return cast(dict[str, object], json.loads(cached[1]))
        payload = compute()
        fp_after = self._cache_fingerprint()
        if fp_after is not None:
            serialized = json.dumps(payload, ensure_ascii=False)
            with self._cache_lock:
                if len(self._route_cache) > 64:
                    self._route_cache.clear()
                self._route_cache[route] = (fp_after, serialized)
        return payload

    def _handle_workspace_ai(
        self,
        method: str,
        route: str,
        body: bytes,
        *,
        query: str = "",
    ) -> tuple[int, dict[str, object]]:
        if method not in {"GET", "HEAD"}:
            self._bump_mutation_epoch()
        try:
            if route == "/api/v1/workspace-ai/settings":
                if method == "GET":
                    return HTTPStatus.OK, self._workspace_hub.get_settings()
                if method == "PUT":
                    data = self._inner._body(body)
                    return HTTPStatus.OK, self._workspace_hub.update_settings(data)
                raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found.")
            if route == "/api/v1/workspace-ai/research/sessions" and method == "GET":
                return HTTPStatus.OK, self._workspace_hub.list_research_sessions()
            if route == "/api/v1/workspace-ai/research/ask" and method == "POST":
                data = self._inner._body(body)
                return HTTPStatus.OK, self._workspace_hub.ask_research_question(data)
            if route == "/api/v1/workspace-ai/weekly-brief" and method == "GET":
                q_params = parse_qs(query, keep_blank_values=False) if query else {}
                vals = q_params.get("brief_id")
                req_brief_id = vals[0] if vals else None
                return HTTPStatus.OK, self._workspace_hub.get_latest_weekly_brief(
                    brief_id=req_brief_id
                )
            if (
                route == "/api/v1/workspace-ai/weekly-brief/generate"
                and method == "POST"
            ):
                self._inner._body(body)
                return HTTPStatus.OK, self._workspace_hub.generate_weekly_brief()
            if route == "/api/v1/workspace-ai/sync-status" and method == "GET":
                return HTTPStatus.OK, self._workspace_hub.get_sync_status()
            if route == "/api/v1/workspace-ai/sync-pending" and method == "POST":
                data = self._inner._body(body) if body.strip() else {}
                raw_limit = data.get("limit", 20) if isinstance(data, dict) else 20
                return HTTPStatus.OK, self._workspace_hub.sync_pending_videos(
                    limit=int(cast(int, raw_limit))
                )
            if route == "/api/v1/workspace-ai/backup" and method == "GET":
                return HTTPStatus.OK, self._workspace_hub.export_backup_snapshot()
            if route == "/api/v1/workspace-ai/obsidian-bundle" and method == "GET":
                q_params = parse_qs(query, keep_blank_values=False) if query else {}
                req_scope = (q_params.get("scope") or ["must_watch"])[0]
                return HTTPStatus.OK, self._workspace_hub.export_obsidian_vault_bundle(
                    scope=req_scope
                )
            if route == "/api/v1/workspace-ai/restore" and method == "POST":
                data = self._inner._body(body)
                return HTTPStatus.OK, self._workspace_hub.restore_backup_snapshot(data)
            if route == "/api/v1/workspace-ai/curation/batch" and method == "POST":
                data = self._inner._body(body)
                return (
                    HTTPStatus.OK,
                    self._workspace_hub.batch_update_video_curation(data),
                )
            distill_m = _WS_AI_DISTILL_ROUTE.fullmatch(route)
            if distill_m is not None and method == "POST":
                self._inner._body(body)
                return HTTPStatus.OK, self._workspace_hub.distill_video(distill_m[1])
            tx_m = _WS_AI_TRANSCRIBE_ROUTE.fullmatch(route)
            if tx_m is not None and method == "POST":
                self._inner._body(body)
                return HTTPStatus.OK, self._workspace_hub.transcribe_and_distill_local_video(
                    tx_m[1]
                )
            obs_m = _WS_AI_OBSIDIAN_ROUTE.fullmatch(route)
            if obs_m is not None and method == "GET":
                return HTTPStatus.OK, self._workspace_hub.get_video_obsidian_export(
                    obs_m[1]
                )
            cur_m = _WS_AI_CURATION_ROUTE.fullmatch(route)
            if cur_m is not None and method == "POST":
                data = self._inner._body(body)
                return HTTPStatus.OK, self._workspace_hub.update_video_curation(
                    cur_m[1], data
                )
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found.")
        except ApiError as err:
            return err.status, {
                "error": {"code": err.code, "message": err.message}
            }
        except CredentialStoreError:
            return HTTPStatus.SERVICE_UNAVAILABLE, {
                "error": {
                    "code": "CREDENTIAL_STORE_UNAVAILABLE",
                    "message": "System credential store is unavailable.",
                }
            }
        except (ValueError, KeyError) as err:
            return HTTPStatus.UNPROCESSABLE_ENTITY, {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(err) or "Request values are invalid.",
                }
            }
        finally:
            if method not in {"GET", "HEAD"}:
                self._bump_mutation_epoch()

    def handle(
        self, method: str, path: str, body: bytes = b""
    ) -> tuple[int, dict[str, object]]:
        parsed_url = urlparse(path)
        route = parsed_url.path.rstrip("/") or "/"
        if route.startswith("/api/v1/workspace-ai/"):
            return self._handle_workspace_ai(
                method, route, body, query=parsed_url.query
            )
        if method == "GET":
            detail_match = _VIDEO_DETAIL_ROUTE.fullmatch(route)
            if route in {"/api/v1/videos", "/api/v1/intelligence"} or (
                detail_match is not None
            ):
                try:
                    if route == "/api/v1/videos":
                        return HTTPStatus.OK, self._cached_or_compute(
                            route, self._fast_get_videos
                        )
                    if route == "/api/v1/intelligence":
                        return HTTPStatus.OK, self._cached_or_compute(
                            route, self._fast_get_intelligence
                        )
                    assert detail_match is not None
                    vid = detail_match[1]
                    return HTTPStatus.OK, self._cached_or_compute(
                        route, lambda: self._fast_get_video_detail(vid)
                    )
                except OfflineError as error:
                    return HTTPStatus.CONFLICT, {
                        "error": {
                            "code": error.code,
                            "message": "Local transcription is unavailable or could not complete.",
                        }
                    }
                except ApiError:
                    raise
                except IntegrityConflict as error:
                    raise ApiError(
                        HTTPStatus.CONFLICT,
                        "CONFLICT",
                        "Preference or feedback command conflicts with existing history.",
                    ) from error
                except CredentialStoreError:
                    raise ApiError(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        "CREDENTIAL_STORE_UNAVAILABLE",
                        "System credential store is unavailable.",
                    ) from None
                except BackupRestoreError as error:
                    raise ApiError(
                        HTTPStatus.CONFLICT,
                        "BACKUP_RESTORE_REJECTED",
                        str(error),
                    ) from error
                except (ValueError, KeyError) as error:
                    raise ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "VALIDATION_ERROR",
                        "Request values are invalid or unavailable.",
                    ) from error
        if method not in {"GET", "HEAD"}:
            self._bump_mutation_epoch()
        try:
            status_code, resp_payload = self._inner.handle(method, path, body)
            if (
                method == "GET"
                and status_code == HTTPStatus.OK
                and self._workspace_hub.has_sidecar_db()
            ):
                if route == "/api/v1/dashboard":
                    wb = self._workspace_hub.get_latest_weekly_brief().get("weekly_brief")
                    filtered_attention = self._filter_superseded_dashboard_attention(
                        resp_payload.get("needs_attention")
                    )
                    enriched_pinned = self._workspace_hub.enrich_topics_items(
                        resp_payload.get("pinned_topics")
                    )
                    resp_payload = {
                        **resp_payload,
                        "pinned_topics": enriched_pinned,
                        "needs_attention": filtered_attention,
                        "saved_intelligence_ids": self._read_saved_intelligence_ids(),
                        "workspace_sync_status": self._workspace_hub.get_sync_status(),
                    }
                    if wb is not None:
                        resp_payload["workspace_weekly_brief"] = wb
                elif route == "/api/v1/topics":
                    resp_payload = self._workspace_hub.enrich_topics_list_dto(resp_payload)
                elif route.startswith("/api/v1/topics/"):
                    resp_payload = self._workspace_hub.enrich_topic_detail_dto(resp_payload)
                elif route == "/api/v1/settings":
                    resp_payload = {
                        **resp_payload,
                        "workspace_ai": self._workspace_hub.get_settings(),
                    }
            return status_code, resp_payload
        finally:
            if method not in {"GET", "HEAD"}:
                self._bump_mutation_epoch()

    def _read_saved_intelligence_ids(self) -> list[str]:
        conn = self._inner._repository._connect(read_only=True)
        try:
            rows = conn.execute(
                "SELECT intelligence_id FROM saved_intelligences "
                "ORDER BY saved_at DESC, intelligence_id ASC LIMIT 200"
            ).fetchall()
            return [str(r[0]) for r in rows]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def _filter_superseded_dashboard_attention(
        self, raw_items: object
    ) -> list[dict[str, object]]:
        if not isinstance(raw_items, list):
            return []
        policy_svc = getattr(self._inner, "_source_policy_service", None)
        briefs_map = self._workspace_hub.get_video_briefs_map()
        conn = self._inner._repository._connect(read_only=True)
        try:
            kept: list[dict[str, object]] = []
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                if item.get("attention_reason") != "EXECUTION_CONDITION_UNRESOLVED":
                    kept.append(item)
                    continue
                source_id = item.get("source_id")
                run_id = item.get("run_id")
                if not isinstance(source_id, str) or not isinstance(run_id, str):
                    kept.append(item)
                    continue
                child_states = [
                    str(r[0])
                    for r in conn.execute(
                        "SELECT state FROM source_run_video_executions WHERE run_id = ?",
                        (run_id,),
                    ).fetchall()
                ]
                if any(
                    st not in {"COMPLETED", "FAILED", "SKIPPED"} for st in child_states
                ):
                    kept.append(item)
                    continue
                has_focus = False
                if policy_svc is not None:
                    try:
                        eff_policy = policy_svc.effective_policy(source_id)
                        has_focus = bool(getattr(eff_policy, "focus_rules", ()))
                    except Exception:
                        has_focus = False
                if has_focus and child_states:
                    continue
                linked_vids = [
                    str(r[0])
                    for r in conn.execute(
                        "SELECT video_id FROM source_video_links WHERE source_id = ?",
                        (source_id,),
                    ).fetchall()
                ]
                if linked_vids and all(vid in briefs_map for vid in linked_vids):
                    continue
                kept.append(item)
            return kept
        finally:
            conn.close()

    def _fast_get_videos(self) -> dict[str, object]:
        repo = self._inner._repository
        conn = repo._connect(read_only=True)
        try:
            conn.execute("BEGIN")
            try:
                videos = [
                    repo._video_from_row(row)
                    for row in conn.execute(
                        "SELECT * FROM videos ORDER BY updated_at DESC, video_id LIMIT 200"
                    )
                ]
                videos_by_id = {video.video_id: video for video in videos}
                ctx = _RequestSnapshotContext(
                    self._inner,
                    conn,
                    videos_by_id=videos_by_id,
                    verified_source_memo=self._verified_source_memo,
                    memo_lock=self._cache_lock,
                )
                shared_da: tuple[str, str | None] | None = None
                da_service = self._inner._deep_analysis_service
                if (
                    da_service is not None
                    and videos
                    and da_service._capability.execution_route() is None
                ):
                    da_status = da_service.status(content_id=videos[0].video_id)
                    shared_da = (da_status.availability.value, da_status.reason)
                projected = [
                    ctx.video_dto_with_deep_analysis(
                        video, shared_da_status=shared_da
                    )
                    for video in videos
                ]
                next_local_av_ids = tuple(
                    str(item["video_id"])
                    for item in projected
                    if item.get("provider") == "LOCAL"
                    and item.get("media_kind") in {"AUDIO", "VIDEO"}
                )
                with self._cache_lock:
                    self._local_av_ids = next_local_av_ids
                briefs_map = self._workspace_hub.get_video_briefs_map()
                if briefs_map:
                    projected = [
                        self._workspace_hub.enrich_video_list_item(item, brief)
                        if (brief := briefs_map.get(str(item["video_id"]))) is not None
                        else item
                        for item in projected
                    ]
                return {"videos": projected + ctx.pending_content_work()}
            finally:
                conn.rollback()
        finally:
            conn.close()

    def _fast_get_intelligence(self) -> dict[str, object]:
        repo = self._inner._repository
        custom_latest_exec = "latest_distillation_execution_for_video" in repo.__dict__
        conn = repo._connect(read_only=True)
        try:
            conn.execute("BEGIN")
            try:
                current_ids = [
                    str(row["intelligence_id"])
                    for row in conn.execute(
                        "SELECT intelligence_id FROM intelligences "
                        "WHERE current_revision_id IS NOT NULL "
                        "ORDER BY created_at DESC, intelligence_id ASC LIMIT 100"
                    )
                ]
                intelligence = [
                    self._inner._intelligence_projection(intelligence_id)
                    for intelligence_id in current_ids
                ]
                checkpoint_video_ids = {
                    str(row[0])
                    for row in conn.execute(
                        "SELECT DISTINCT video_id FROM distillation_execution_checkpoints"
                    )
                }
                top_videos = [
                    repo._video_from_row(row)
                    for row in conn.execute(
                        "SELECT * FROM videos ORDER BY updated_at DESC, video_id LIMIT 100"
                    )
                ]
                activity: list[dict[str, object]] = []
                for video in top_videos:
                    if custom_latest_exec or video.video_id in checkpoint_video_ids:
                        execution = repo.latest_distillation_execution_for_video(
                            video.video_id
                        )
                        if execution is not None and execution.status != "SUCCEEDED":
                            activity.append(
                                {
                                    "video_id": video.video_id,
                                    "title": video.title,
                                    **self._inner._distillation_execution_dto(execution),
                                }
                            )
                seen: set[str] = {str(item["video_id"]) for item in activity}
                child_rows = conn.execute(
                    "SELECT child.video_id, v.title, child.state "
                    "FROM source_runs AS r "
                    "JOIN source_subscriptions AS s ON s.source_id = r.source_id "
                    "JOIN source_run_video_executions AS child ON child.run_id = r.run_id "
                    "JOIN videos AS v ON v.video_id = child.video_id "
                    "WHERE s.processing_policy = 'STANDARD_INTELLIGENCE' "
                    "AND child.distillation_execution_id IS NULL "
                    "AND child.state NOT IN ('COMPLETED', 'SKIPPED') "
                    "ORDER BY r.created_at ASC, r.run_id ASC, child.video_id ASC"
                ).fetchall()
                for child_row in child_rows:
                    vid = str(child_row["video_id"])
                    if vid in seen:
                        continue
                    state_value = SourceRunChildState(str(child_row["state"])).value
                    activity.append(
                        {
                            "video_id": vid,
                            "title": str(child_row["title"]),
                            "status": state_value,
                        }
                    )
                    seen.add(vid)

                tracked_std_sources = [
                    str(row[0])
                    for row in conn.execute(
                        "SELECT s.source_id FROM source_subscriptions AS s "
                        "WHERE s.processing_policy = 'STANDARD_INTELLIGENCE' "
                        "AND EXISTS ("
                        "  SELECT 1 FROM source_tracking_state AS t WHERE t.source_id = s.source_id"
                        ") "
                        "ORDER BY s.created_at DESC, s.source_id"
                    )
                ]
                if tracked_std_sources:
                    ctx = _RequestSnapshotContext(
                        self._inner,
                        conn,
                        videos_by_id={v.video_id: v for v in top_videos},
                    )
                    for source_id in tracked_std_sources:
                        src_videos = [
                            repo._video_from_row(row)
                            for row in conn.execute(
                                "SELECT v.* FROM source_video_links AS link "
                                "JOIN videos AS v ON v.video_id = link.video_id "
                                "WHERE link.source_id = :source_id "
                                "ORDER BY link.discovered_at DESC, v.video_id DESC LIMIT 100",
                                {"source_id": source_id},
                            )
                        ]
                        for video in src_videos:
                            if video.video_id in seen:
                                continue
                            ctx.snap_repo._videos.setdefault(video.video_id, video)
                            has_exec = False
                            if custom_latest_exec or video.video_id in checkpoint_video_ids:
                                has_exec = (
                                    repo.latest_distillation_execution_for_video(
                                        video.video_id
                                    )
                                    is not None
                                )
                            if (
                                not has_exec
                                and ctx.manual_content_source(video.video_id) is None
                            ):
                                activity.append(
                                    {
                                        "video_id": video.video_id,
                                        "title": video.title,
                                        "status": "WAITING_CONTENT",
                                    }
                                )
                                seen.add(video.video_id)
                if activity and self._workspace_hub.has_sidecar_db():
                    activity = self._filter_superseded_intelligence_activity(
                        conn, intelligence, activity
                    )
                return {"intelligence": intelligence, "activity": activity}
            finally:
                conn.rollback()
        finally:
            conn.close()

    def _filter_superseded_intelligence_activity(
        self,
        conn: sqlite3.Connection,
        intelligence: Sequence[Mapping[str, object]],
        activity: Sequence[dict[str, object]],
    ) -> list[dict[str, object]]:
        available_vids: set[str] = set()
        for item in intelligence:
            if item.get("status") != "AVAILABLE" or item.get("trusted") is not True:
                continue
            card = item.get("card")
            if isinstance(card, dict) and isinstance(card.get("video_id"), str):
                available_vids.add(str(card["video_id"]))
            prov = item.get("source_provenance")
            if isinstance(prov, list):
                for p in prov:
                    if isinstance(p, dict) and isinstance(p.get("content_id"), str):
                        available_vids.add(str(p["content_id"]))
        briefs_map = self._workspace_hub.get_video_briefs_map()
        active_statuses = {
            "RUNNING",
            "PENDING",
            "FETCHING",
            "READING_CAPTIONS",
            "ORGANIZING",
            "WAITING_MODEL",
        }
        kept: list[dict[str, object]] = []
        for act in activity:
            vid = str(act.get("video_id") or "")
            status = str(act.get("status") or "")
            if act.get("can_cancel") is True or status in active_statuses:
                kept.append(act)
                continue
            if vid and vid in available_vids:
                continue
            brief = briefs_map.get(vid) if vid else None
            if brief is not None:
                if bool(brief.get("is_short_noise")) or (
                    brief.get("recommendation_tier") == "SKIP_NOISE"
                ):
                    continue
                if brief.get("source_basis") == "METADATA_ONLY":
                    has_timed = (
                        conn.execute(
                            "SELECT 1 FROM timed_transcripts WHERE video_id = ? LIMIT 1",
                            (vid,),
                        ).fetchone()
                        is not None
                    )
                    has_active_job = (
                        conn.execute(
                            "SELECT 1 FROM jobs WHERE video_id = ? "
                            "AND status IN ('PENDING', 'RUNNING') LIMIT 1",
                            (vid,),
                        ).fetchone()
                        is not None
                    )
                    if not has_timed and not has_active_job:
                        continue
            kept.append(act)
        return kept

    def _fast_get_video_detail(self, video_id: str) -> dict[str, object]:
        repo = self._inner._repository
        custom_latest_exec = "latest_distillation_execution_for_video" in repo.__dict__
        conn = repo._connect(read_only=True)
        try:
            conn.execute("BEGIN")
            try:
                ctx = _RequestSnapshotContext(
                    self._inner,
                    conn,
                    verified_source_memo=self._verified_source_memo,
                    memo_lock=self._cache_lock,
                )
                video = ctx.snap_repo.get_video(video_id)
                if video is None:
                    pending = next(
                        (
                            item
                            for item in ctx.pending_content_work()
                            if item["video_id"] == video_id
                        ),
                        None,
                    )
                    if pending is not None:
                        return {
                            "video": pending,
                            "transcript": {"status": "NOT_AVAILABLE"},
                            "note": {"v2": {"status": "UNAVAILABLE"}},
                            "scoring": {"status": "NOT_AVAILABLE"},
                            "intelligence_result": self._inner._distillation_execution_dto(
                                None
                            ),
                            "history": [],
                            "cloud_intelligence_available": False,
                        }
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Video was not found."
                    )
                manual_source = ctx.manual_content_source(video.video_id)
                has_checkpoint = (
                    conn.execute(
                        "SELECT 1 FROM distillation_execution_checkpoints WHERE video_id = ? LIMIT 1",
                        (video.video_id,),
                    ).fetchone()
                    is not None
                )
                latest_exec = (
                    repo.latest_distillation_execution_for_video(video.video_id)
                    if (custom_latest_exec or has_checkpoint)
                    else None
                )
                pending_synth_ids = [
                    str(row[0])
                    for row in conn.execute(
                        "SELECT execution_id FROM distillation_execution_checkpoints "
                        "WHERE video_id=? AND status='PENDING' AND invocation_count=0 "
                        "AND execution_id LIKE 'distillation:system-synthesis-%'",
                        (video.video_id,),
                    )
                ]
                pending_synth = [
                    self._inner._distillation_execution_dto(execution)
                    for identity in pending_synth_ids
                    if (execution := repo.get_distillation_execution(identity))
                    is not None
                ]
                waiting_execs = (
                    [
                        self._inner._distillation_execution_dto(wait)
                        for wait in repo.list_waiting_model_executions_for_video(
                            video.video_id
                        )
                    ]
                    if has_checkpoint
                    else []
                )
                detail_payload: dict[str, object] = {
                    "video": ctx.video_dto_with_deep_analysis(video),
                    "scoring": self._inner._scoring_projection(video.video_id),
                    "transcript": ctx.transcript_projection(video),
                    "note": ctx.note_projection(video.video_id),
                    "intelligence_result": self._inner._distillation_execution_dto(
                        latest_exec
                    ),
                    "manual_intelligence_eligible": manual_source is not None,
                    "local_intelligence": self._inner._content_local_intelligence_status(
                        video.video_id, manual_source
                    ),
                    "pending_synthesis_executions": pending_synth,
                    "waiting_model_executions": waiting_execs,
                    "cloud_intelligence_available": (
                        self._inner._cloud_execution_enabled
                        and video.provider == "YOUTUBE"
                        and self._inner._cloud_intelligence_qualified
                        and self._inner._cloud_credential_available
                    ),
                    "history": self._inner._history_projection(video.video_id),
                }
                brief = self._workspace_hub.get_video_brief(video.video_id)
                if brief is not None:
                    detail_payload = self._workspace_hub.enrich_video_detail(
                        detail_payload, brief
                    )
                return detail_payload
            finally:
                conn.rollback()
        finally:
            conn.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def run_cli_with_fast_reads(argv: Sequence[str] | None = None) -> ExitCode:
    """CLI entrypoint wrapper activating ``FastReadApiApplication`` for ``serve-api``."""

    from youtube_intel import cli
    from youtube_intel.config import ConfigError
    from youtube_intel.runtime_composition import build_local_source_run_runtime

    effective_argv = tuple(sys.argv[1:] if argv is None else argv)
    parser = cli._build_parser()
    try:
        args = parser.parse_args(effective_argv)
        if args.command != "serve-api":
            return cli.main(effective_argv)
        cli._validate_arguments(args)
        if args.port < 1024 or args.port > 65535:
            return ExitCode.USAGE_OR_CONFIGURATION
        project_root = cli._project_root(args.project_root)
        config = cli._load_config(project_root, args.settings, args.channels)
        stop_requested = False
        while True:
            composition = build_local_source_run_runtime(
                config=config,
                project_root=project_root,
                database=args.database,
            )
            if args.native_import_origin:
                if args.native_picker_executable is None:
                    raise ValueError("Native import requires its prepared selector")
                composition.application.enable_native_import(
                    tuple(args.native_import_origin),
                    picker_executable=args.native_picker_executable,
                )
            fast_app = FastReadApiApplication(composition.application)
            server = serve_loopback(
                cast(LocalApiApplication, fast_app),
                port=args.port,
            )

            def request_stop(signum: int, frame: FrameType | None) -> None:
                nonlocal stop_requested
                stop_requested = True
                threading.Thread(target=server.shutdown, daemon=True).start()

            previous_handlers = (
                {
                    sig: signal.signal(sig, request_stop)
                    for sig in (signal.SIGTERM, signal.SIGINT)
                }
                if threading.current_thread() is threading.main_thread()
                else {}
            )
            composition.worker.start()
            auto_sync_stop = threading.Event()

            def _auto_sync_loop() -> None:
                while not auto_sync_stop.wait(45.0):
                    try:
                        if not fast_app._workspace_hub.has_sidecar_db():
                            continue
                        st = fast_app._workspace_hub.get_sync_status()
                        if int(cast(int, st.get("pending_count", 0))) <= 0:
                            continue
                        res = fast_app._workspace_hub.sync_pending_videos(limit=3)
                        if int(cast(int, res.get("synced_count", 0))) > 0:
                            fast_app._bump_mutation_epoch()
                    except Exception:
                        continue

            auto_sync_thread = threading.Thread(
                target=_auto_sync_loop, name="workspace-ai-auto-sync", daemon=True
            )
            auto_sync_thread.start()
            try:
                server.serve_forever()
            finally:
                auto_sync_stop.set()
                server.server_close()
                composition.application.shutdown_native_import()
                composition.worker.stop()
                for sig, handler in previous_handlers.items():
                    signal.signal(sig, handler)
            if stop_requested or not composition.backup_restore.restart_requested:
                break
        return ExitCode.OK
    except (ConfigError, OSError, ValueError):
        return cli.main(effective_argv)
