"""Authoritative current Summary / Video Notes selection for one Content."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from youtube_intel.deep_analysis_persistence import (
    DeepAnalysisPersistenceStore,
    VerifiedPersistedDeepAnalysisRead,
    verify_persisted_deep_analysis_read,
)
from youtube_intel.note_v2 import NoteV2, build_note_v2
from youtube_intel.state import (
    IntegrityConflict,
    SQLiteStateRepository,
    format_utc_datetime,
    _parse_utc_datetime,
)


class ContentSummaryReadRejected(ValueError):
    """The current Summary pointer or its trusted target is unavailable."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CurrentContentSummaryBinding:
    video_id: str
    result_identity: str
    note_identity: str
    output_language: str
    promoted_at: datetime


@dataclass(frozen=True, slots=True)
class AuthoritativeContentSummaryRead:
    binding: CurrentContentSummaryBinding
    note: NoteV2


class ContentSummaryAuthority:
    """Own the explicit current-result pointer; never infer authority from recency."""

    def __init__(self, repository: SQLiteStateRepository) -> None:
        self._repository = repository
        self._store = DeepAnalysisPersistenceStore(repository)

    @staticmethod
    def _binding_from_row(row: sqlite3.Row) -> CurrentContentSummaryBinding:
        return CurrentContentSummaryBinding(
            video_id=str(row["video_id"]),
            result_identity=str(row["result_identity"]),
            note_identity=str(row["note_identity"]),
            output_language=str(row["output_language"]),
            promoted_at=_parse_utc_datetime(str(row["promoted_at"])),
        )

    def promote_verified_result(
        self,
        source: VerifiedPersistedDeepAnalysisRead,
        *,
        now: datetime,
    ) -> CurrentContentSummaryBinding:
        """Promote only a result already revalidated by this repository's store."""

        if (
            type(source) is not VerifiedPersistedDeepAnalysisRead
            or not verify_persisted_deep_analysis_read(source)
        ):
            raise ValueError("current Summary requires a verified persisted Deep Analysis read")

        persisted = self._store.read_persisted_deep_analysis_result(
            result_identity=source.result_identity
        )
        if persisted is None:
            raise ValueError("verified Deep Analysis result is not present in this repository")

        note = build_note_v2(persisted)
        video = self._repository.get_video(note.video_id)
        if video is None:
            raise ValueError("current Summary target Content does not exist")

        promoted_at = format_utc_datetime(now)
        connection = self._repository._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            target = connection.execute(
                "SELECT validated_at FROM deep_analysis_persisted_results "
                "WHERE result_identity = ?",
                (persisted.result_identity,),
            ).fetchone()
            if target is None:
                raise IntegrityConflict("current Summary target disappeared")

            current = connection.execute(
                "SELECT current.*, persisted.validated_at AS target_validated_at "
                "FROM current_content_summaries AS current "
                "JOIN deep_analysis_persisted_results AS persisted "
                "ON persisted.result_identity = current.result_identity "
                "WHERE current.video_id = ?",
                (note.video_id,),
            ).fetchone()

            if current is not None:
                if str(current["result_identity"]) == persisted.result_identity:
                    if (
                        str(current["note_identity"]) != note.identity
                        or str(current["output_language"]) != note.language
                    ):
                        raise IntegrityConflict("current Summary binding is inconsistent")
                    connection.execute("COMMIT")
                    return self._binding_from_row(current)

                if str(target["validated_at"]) <= str(current["target_validated_at"]):
                    raise IntegrityConflict(
                        "current Summary cannot regress to an older or ambiguous result"
                    )

            connection.execute(
                "INSERT INTO current_content_summaries "
                "(video_id, result_identity, note_identity, output_language, promoted_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(video_id) DO UPDATE SET "
                "result_identity=excluded.result_identity, "
                "note_identity=excluded.note_identity, "
                "output_language=excluded.output_language, "
                "promoted_at=excluded.promoted_at",
                (
                    note.video_id,
                    persisted.result_identity,
                    note.identity,
                    note.language,
                    promoted_at,
                ),
            )
            row = connection.execute(
                "SELECT * FROM current_content_summaries WHERE video_id = ?",
                (note.video_id,),
            ).fetchone()
            if row is None:
                raise IntegrityConflict("current Summary binding was not saved")
            connection.execute("COMMIT")
            return self._binding_from_row(row)
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def read_current(self, video_id: str) -> AuthoritativeContentSummaryRead:
        if not video_id.strip():
            raise ValueError("video_id must be non-empty")

        connection = self._repository._connect()
        try:
            row = connection.execute(
                "SELECT * FROM current_content_summaries WHERE video_id = ?",
                (video_id,),
            ).fetchone()
        finally:
            connection.close()

        if row is None:
            raise ContentSummaryReadRejected(
                "CURRENT_SUMMARY_MISSING", "current Summary is unavailable"
            )

        binding = self._binding_from_row(row)
        persisted = self._store.read_persisted_deep_analysis_result(
            result_identity=binding.result_identity
        )
        if persisted is None:
            raise ContentSummaryReadRejected(
                "CURRENT_SUMMARY_RESULT_INVALID",
                "current Summary target is not a verified Deep Analysis result",
            )

        try:
            note = build_note_v2(persisted)
        except ValueError as error:
            raise ContentSummaryReadRejected(
                "CURRENT_SUMMARY_NOTE_INVALID", "current Summary cannot be reconstructed"
            ) from error

        if (
            note.video_id != binding.video_id
            or note.identity != binding.note_identity
            or note.language != binding.output_language
            or self._repository.get_video(binding.video_id) is None
        ):
            raise ContentSummaryReadRejected(
                "CURRENT_SUMMARY_BINDING_INVALID",
                "current Summary pointer does not match its trusted result",
            )

        return AuthoritativeContentSummaryRead(binding=binding, note=note)


__all__ = [
    "AuthoritativeContentSummaryRead",
    "ContentSummaryAuthority",
    "ContentSummaryReadRejected",
    "CurrentContentSummaryBinding",
]
