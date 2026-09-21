"""Authoritative current Summary / Video Notes read boundary."""

from __future__ import annotations

from dataclasses import dataclass

from youtube_intel.deep_analysis_persistence import (
    DeepAnalysisPersistenceStore,
    verify_persisted_deep_analysis_read,
)
from youtube_intel.note_v2 import NoteV2, NoteV2Error, build_note_v2
from youtube_intel.state import SQLiteStateRepository


class ContentSummaryReadRejected(ValueError):
    """The current Summary pointer or its verified target cannot be trusted."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CurrentContentSummary:
    """Structured current Summary projected only from verified persisted authority."""

    note: NoteV2
    result_identity: str


class AuthoritativeContentSummaryReader:
    """Resolve one Content to its explicit current verified Summary result."""

    def __init__(self, repository: SQLiteStateRepository) -> None:
        self._repository = repository
        self._store = DeepAnalysisPersistenceStore(repository)

    def read_current(self, video_id: str) -> CurrentContentSummary:
        if not video_id.strip():
            raise ContentSummaryReadRejected(
                "CONTENT_ID_INVALID", "Content identity is invalid"
            )
        if self._repository.get_video(video_id) is None:
            raise ContentSummaryReadRejected(
                "CONTENT_NOT_FOUND", "Content does not exist"
            )
        result = self._store.read_current_content_summary_result(video_id=video_id)
        if result is None:
            raise ContentSummaryReadRejected(
                "CURRENT_SUMMARY_MISSING",
                "No verified current Summary is available for this Content",
            )
        if not verify_persisted_deep_analysis_read(result):
            raise ContentSummaryReadRejected(
                "CURRENT_SUMMARY_INVALID",
                "Current Summary result failed verification",
            )
        try:
            note = build_note_v2(result)
        except NoteV2Error as error:
            raise ContentSummaryReadRejected(
                "CURRENT_SUMMARY_INVALID",
                "Current Summary could not be rebuilt from verified authority",
            ) from error
        if note.video_id != video_id:
            raise ContentSummaryReadRejected(
                "CURRENT_SUMMARY_TARGET_INVALID",
                "Current Summary does not belong to this Content",
            )
        return CurrentContentSummary(
            note=note,
            result_identity=result.result_identity,
        )
