"""User-explicit one-way publication, independent of generation qualification."""

from pathlib import Path

from youtube_intel.deep_analysis_persistence import (
    DeepAnalysisPersistenceError,
    DeepAnalysisPersistenceStore,
    VerifiedPersistedDeepAnalysisRead,
    require_trusted_note_eligibility,
)
from youtube_intel.providers.obsidian import (
    NotePersistenceError,
    NoteWriteContext,
    ObsidianNoteSink,
)
from youtube_intel.state import SQLiteStateRepository


class DeepAnalysisPublishError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__("Deep Analysis could not be published to Obsidian.")


class DeepAnalysisObsidianPublisher:
    def __init__(
        self, repository: SQLiteStateRepository, *, vault_root: Path | None,
        vault_subdir: str = ".",
    ) -> None:
        self._repository = repository
        self._store = DeepAnalysisPersistenceStore(repository)
        self._vault_root = vault_root
        self._vault_subdir = vault_subdir

    def _eligible_read(self, content_id: str) -> VerifiedPersistedDeepAnalysisRead:
        source = self._store.read_deep_analysis_result_for_content(video_id=content_id)
        try:
            require_trusted_note_eligibility(source)
        except DeepAnalysisPersistenceError:
            raise DeepAnalysisPublishError("RESULT_INELIGIBLE") from None
        if source is None or source.durable_result is None:
            raise DeepAnalysisPublishError("RESULT_INELIGIBLE")
        return source

    def status(self, *, content_id: str) -> dict[str, object]:
        if self._vault_root is None:
            return {"state": "NO_VAULT"}
        try:
            source = self._eligible_read(content_id)
        except DeepAnalysisPublishError as error:
            return {"state": error.code}
        return {"state": "AVAILABLE", "result_identity": source.result_identity}

    def publish(self, *, content_id: str, result_identity: str) -> dict[str, object]:
        if self._vault_root is None:
            raise DeepAnalysisPublishError("NO_VAULT")
        source = self._eligible_read(content_id)
        if source.result_identity != result_identity:
            raise DeepAnalysisPublishError("RESULT_CHANGED")
        video = self._repository.get_video(content_id)
        if video is None:
            raise DeepAnalysisPublishError("RESULT_INELIGIBLE")
        sink = ObsidianNoteSink(
            vault_root=self._vault_root,
            vault_subdir=self._vault_subdir,
            repository=self._repository,
            context=NoteWriteContext(job_id="explicit-publish", owner="local-ui", pipeline_version="deep-analysis-obsidian-v1"),
        )
        try:
            ref, state = sink.upsert_deep_analysis_note(source, title=video.title or content_id)
        except NotePersistenceError as error:
            raise DeepAnalysisPublishError("WRITE_FAILED") from error
        return {"state": state, "relative_path": ref.relative_path, "note_kind": ref.kind.value}
