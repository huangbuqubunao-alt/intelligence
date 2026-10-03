"""Deterministic source excerpts through the existing Summary authority contract.

This adapter performs no inference, translation, model dispatch or network call.
It is provider-neutral: citations resolve through the same durable Evidence reader.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisPoint,
    AnalysisResult,
    EvidenceExcerpt,
    EvidenceSource,
    PointKind,
    ProviderCallMetadata,
)
from youtube_intel.research_contract import digest
from youtube_intel.source_authority import read_managed, sha256, write_managed
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
)
from youtube_intel.summary_evidence_authority import require_current_summary_authority

PROVIDER = "extractive-source"


class ExtractiveSummaryService:
    def __init__(self, repository: SQLiteStateRepository, data_root: Path) -> None:
        self.repository = repository
        self.data_root = data_root
        repository.bind_source_storage(data_root)

    def _result(self, content_id: str) -> AnalysisResult:
        excerpts = []
        for eid in self.repository.list_evidence_for_presentation(content_id):
            verified = self.repository.resolve_verified_evidence_text(eid)
            if verified is None or verified.video_id != content_id:
                raise ValueError("Summary source authority is unavailable")
            if len(verified.excerpt) > 2000:
                continue
            excerpts.append(
                EvidenceExcerpt(
                    evidence_id=eid,
                    source=EvidenceSource.TRANSCRIPT_SAMPLE,
                    excerpt=verified.excerpt,
                )
            )
            if len(excerpts) == 6:
                break
        if not excerpts:
            raise ValueError("Summary requires durable source Evidence")
        identity = digest(
            {
                "contract": "extractive-summary-v1",
                "content_id": content_id,
                "evidence": [e.model_dump(mode="json") for e in excerpts],
            }
        )
        return AnalysisResult(
            provider=PROVIDER,
            model="deterministic-excerpts-v1",
            prompt_version="analysis-prompt-v6",
            request_hash=identity,
            one_sentence_summary=excerpts[0].excerpt[:500],
            core_points=tuple(
                AnalysisPoint(
                    text=e.excerpt, kind=PointKind.FACT, evidence_ids=(e.evidence_id,)
                )
                for e in excerpts
            ),
            keywords=("source excerpts",),
            evidence=tuple(excerpts),
        )

    def create(self, content_id: str, *, now: datetime) -> str:
        result = self._result(content_id)
        payload = result.model_dump_json().encode("utf-8")
        artifact_id = f"summary/{result.request_hash}/structured"
        relative = f"transcripts/summaries/{result.request_hash}.json"
        write_managed(self.data_root, relative, payload)
        self.repository.upsert_artifact(
            ArtifactWrite(
                artifact_id=artifact_id,
                artifact_key=artifact_id,
                video_id=content_id,
                job_id=None,
                kind=ArtifactKind.ANALYSIS_STRUCTURED,
                storage_root=StorageRoot.DATA,
                relative_path=relative,
                content_hash=sha256(payload),
                provider=PROVIDER,
                model=result.model,
                producer_version="extractive-summary-v1",
                retention_class=RetentionClass.LONG_LIVED,
                expires_at=None,
            ),
            now=now,
        )
        require_current_summary_authority(result, self.repository)
        self.repository.promote_current_local_summary(
            video_id=content_id, artifact_id=artifact_id, output_language="en", now=now
        )
        return artifact_id

    def read(self, content_id: str, artifact_id: str) -> AnalysisCompleted:
        artifact = self.repository.get_artifact(artifact_id)
        if (
            artifact is None
            or artifact.video_id != content_id
            or artifact.provider != PROVIDER
            or artifact.kind is not ArtifactKind.ANALYSIS_STRUCTURED
            or artifact.storage_root is not StorageRoot.DATA
            or artifact.deleted_at is not None
        ):
            raise ValueError("Summary authority is invalid")
        payload = read_managed(
            self.data_root, artifact.relative_path, maximum=1_000_000
        )
        result = AnalysisResult.model_validate_json(payload)
        if (
            sha256(payload) != artifact.content_hash
            or result != self._result(content_id)
            or artifact.artifact_id != f"summary/{result.request_hash}/structured"
        ):
            raise ValueError("Summary provenance is invalid")
        require_current_summary_authority(result, self.repository)
        return AnalysisCompleted(
            result=result,
            call=ProviderCallMetadata(
                provider=PROVIDER,
                model=result.model,
                started_at=artifact.created_at,
                finished_at=artifact.created_at,
            ),
        )
