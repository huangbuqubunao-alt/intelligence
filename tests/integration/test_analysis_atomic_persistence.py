"""E1: atomic ANALYSIS persistence infrastructure (dormant, not wired to production)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from youtube_intel.domain import EvidenceSource, PipelineStatus, ProcessingStage
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    Availability,
    ConcurrencyConflict,
    EvidenceLineageKind,
    EvidenceRole,
    IntegrityConflict,
    JobStatus,
    JobType,
    LiveStatus,
    ProviderCallRequest,
    ProviderCallStatus,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    VideoMetadata,
)
from youtube_intel.summary_draft import SummaryDraft, SummaryDraftPoint
from youtube_intel.summary_evidence_authority import hydrate_summary_evidence
from youtube_intel.summary_evidence_candidates import build_trusted_evidence_registry
from youtube_intel.transcripts import _persist_original_transcript_evidence

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
VIDEO_ID = "ausLKMojXaY"
PIPELINE = "pipeline-v1"
CUE_TEXTS = tuple((f"cue{index} " + f"sentence{index} " * 15).strip() for index in range(12))


def td(**kwargs: float) -> timedelta:
    return timedelta(**kwargs)


def _provider_request() -> ProviderCallRequest:
    return ProviderCallRequest(
        operation="local-analysis",
        normalized_input_hash="a" * 64,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="analysis-prompt-v4",
        schema_version="analysis-result-v1",
        deterministic_artifact_key="analysis/e1/raw",
    )


def _seed(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=VIDEO_ID,
            channel_id="UC_TEST",
            channel_name="3Blue1Brown",
            title="The Phone Number puzzle",
            description="d",
            source_url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
            published_at=NOW,
            duration_seconds=44,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.ENDED,
            availability=Availability.PUBLIC,
        ),
        pipeline_version=PIPELINE,
        now=NOW,
    )
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="artifact-1",
            artifact_key=f"transcript/{VIDEO_ID}",
            video_id=VIDEO_ID,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=f"transcripts/{VIDEO_ID}/canonical.txt",
            content_hash=sha256("".join(CUE_TEXTS).encode()).hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    timed = repository.create_timed_transcript(
        TimedTranscriptWrite.from_cues(
            video_id=VIDEO_ID,
            canonical_artifact_id="artifact-1",
            cues=tuple(
                TimedTranscriptCueWrite(
                    start_ms=index * 1000,
                    end_ms=(index + 1) * 1000,
                    text=text,
                )
                for index, text in enumerate(CUE_TEXTS)
            ),
        ),
        now=NOW,
    )
    _persist_original_transcript_evidence(repository, timed=timed, language="en", now=NOW)
    return repository


def _drive_stage(
    repository: SQLiteStateRepository,
    *,
    job_id: str,
    expected: PipelineStatus,
    target: PipelineStatus,
    stage: ProcessingStage,
) -> None:
    """Advance one pipeline stage through its owned job, as production does."""
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:{VIDEO_ID}:{stage.value}",
        video_id=VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=stage,
        pipeline_version=PIPELINE,
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    repository.claim_next_job(owner="worker-1", lease_until=NOW + td(minutes=10), now=NOW)
    repository.complete_stage(
        job_id=job_id,
        owner="worker-1",
        video_id=VIDEO_ID,
        expected_status=expected,
        target_status=target,
        pipeline_version=PIPELINE,
        artifacts=(),
        provider_call=None,
        now=NOW,
    )


def _scored_with_job(repository: SQLiteStateRepository, *, job_id: str = "analysis-job") -> str:
    """Drive the video to SCORED and leave a RUNNING ANALYSIS job owned by worker-1."""
    _drive_stage(
        repository,
        job_id="job-metadata",
        expected=PipelineStatus.DISCOVERED,
        target=PipelineStatus.METADATA_READY,
        stage=ProcessingStage.METADATA,
    )
    _drive_stage(
        repository,
        job_id="job-transcript",
        expected=PipelineStatus.METADATA_READY,
        target=PipelineStatus.TRANSCRIPT_READY,
        stage=ProcessingStage.TRANSCRIPT,
    )
    # SCORED is deliberately not reachable through complete_stage: scoring
    # uses the runtime trusted-persistence entry, so drive it directly.
    assert repository.advance_pipeline(
        VIDEO_ID,
        expected_status=PipelineStatus.TRANSCRIPT_READY,
        target_status=PipelineStatus.SCORED,
        pipeline_version=PIPELINE,
        now=NOW,
    )
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:{VIDEO_ID}:ANALYSIS",
        video_id=VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.ANALYSIS,
        pipeline_version=PIPELINE,
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    repository.claim_next_job(owner="worker-1", lease_until=NOW + td(minutes=10), now=NOW)
    assert repository.get_job(job_id).status is JobStatus.RUNNING
    return job_id


def _promotion(repository: SQLiteStateRepository, *, video_id: str = VIDEO_ID):
    verified = repository.get_verified_timed_transcript(video_id=video_id)
    assert verified is not None
    registry = build_trusted_evidence_registry(
        transcript=verified,
        title="t",
        channel_name="c",
        description="d",
        input_identity="a" * 64,
    )
    ref = next(
        c.ref for c in registry.candidates if c.source is EvidenceSource.TRANSCRIPT_SAMPLE
    )
    hydrated = hydrate_summary_evidence(
        SummaryDraft(
            one_sentence_summary="s",
            core_points=(SummaryDraftPoint(text="t", kind="fact", evidence_refs=(ref,)),),
            keywords=("k",),
        ),
        registry,
        video_id=video_id,
        canonical_artifact_id="artifact-1",
        language="en",
        timed_transcript_id=verified.timed_transcript_id,
        timed_transcript_hash=verified.timed_transcript_hash,
    )
    return hydrated.promotions[0]


def _reserve(repository: SQLiteStateRepository) -> ProviderCallRequest:
    request = _provider_request()
    reservation = repository.reserve_provider_call(
        request,
        owner="worker-1",
        lease_until=NOW + td(minutes=10),
        available_at=NOW,
        now=NOW,
        fail_closed_on_ambiguous_dispatch=True,
    )
    assert reservation.acquired
    # Mirror the production dispatch sequence: durable intent, then result
    # unknown, before a durable success may be recorded.
    repository.record_provider_dispatch_intent(
        request.request_hash, owner="worker-1", now=NOW
    )
    repository.record_provider_dispatch_result_unknown(
        request.request_hash, owner="worker-1", now=NOW
    )
    return request


def _analysis_artifacts(repository: SQLiteStateRepository, request: ProviderCallRequest):
    from youtube_intel.state import ProviderCallCompletion

    raw = b'{"message":{"content":"{}"}}'
    structured = b'{"one_sentence_summary":"s"}'
    base = f"analysis/{request.request_hash}"
    return (
        ArtifactWrite(
            artifact_id=f"analysis-raw-{sha256(raw).hexdigest()[:16]}",
            artifact_key=f"{base}/raw",
            video_id=VIDEO_ID,
            job_id="analysis-job",
            kind=ArtifactKind.ANALYSIS_RAW,
            storage_root=StorageRoot.DATA,
            relative_path=f"{base}/raw.json",
            content_hash=sha256(raw).hexdigest(),
            provider="ollama",
            model="qwen3:8b",
            producer_version="analysis-raw-v1",
            retention_class=RetentionClass.RAW_RESPONSE_30D,
            expires_at=NOW + td(days=30),
        ),
        ArtifactWrite(
            artifact_id=f"analysis-structured-{sha256(structured).hexdigest()[:16]}",
            artifact_key=f"{base}/structured",
            video_id=VIDEO_ID,
            job_id="analysis-job",
            kind=ArtifactKind.ANALYSIS_STRUCTURED,
            storage_root=StorageRoot.DATA,
            relative_path=f"{base}/structured.json",
            content_hash=sha256(structured).hexdigest(),
            provider="ollama",
            model="qwen3:8b",
            producer_version="analysis-structured-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
    ), ProviderCallCompletion(
        request_hash=request.request_hash,
        response_artifact_id=f"analysis-raw-{sha256(raw).hexdigest()[:16]}",
        input_tokens=None,
        output_tokens=None,
        cost_microusd=None,
    )


# --- E1: standalone promotion still works ---------------------------------


def test_E1_standalone_promotion_semantics_unchanged(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    promotion = _promotion(repository)
    record = repository.promote_summary_evidence(
        promotion.as_evidence_write(), promotion.as_text_binding(), now=NOW
    )
    assert record.lineage_kind is EvidenceLineageKind.EXTRACTION
    assert record.role is EvidenceRole.PRIMARY_ORIGINAL
    assert repository.resolve_verified_evidence_text(record.evidence_id) is not None


def test_E2_in_transaction_promotion_creates_extraction_primary_original(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    _scored_with_job(repository)
    request = _reserve(repository)
    artifacts, completion = _analysis_artifacts(repository, request)
    promotion = _promotion(repository)
    result = repository.complete_analysis_stage(
        job_id="analysis-job",
        owner="worker-1",
        video_id=VIDEO_ID,
        pipeline_version=PIPELINE,
        artifacts=artifacts,
        provider_call=completion,
        summary_promotions=((promotion.as_evidence_write(), promotion.as_text_binding()),),
        now=NOW,
    )
    assert len(result.promoted_evidence) == 1
    assert result.promoted_evidence[0].lineage_kind is EvidenceLineageKind.EXTRACTION
    assert result.promoted_evidence[0].role is EvidenceRole.PRIMARY_ORIGINAL
    assert promotion.evidence_id in repository.list_summary_promoted_evidence_ids(VIDEO_ID)


def test_E3_repeated_promotion_is_idempotent(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    promotion = _promotion(repository)
    first = repository.promote_summary_evidence(
        promotion.as_evidence_write(), promotion.as_text_binding(), now=NOW
    )
    second = repository.promote_summary_evidence(
        promotion.as_evidence_write(), promotion.as_text_binding(), now=NOW
    )
    assert first.evidence_id == second.evidence_id
    assert first.created_at == second.created_at


def test_E4_conflicting_existing_evidence_fails_closed(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    promotion = _promotion(repository)
    repository.promote_summary_evidence(
        promotion.as_evidence_write(), promotion.as_text_binding(), now=NOW
    )
    with pytest.raises(IntegrityConflict):
        repository.promote_summary_evidence(
            promotion.as_evidence_write(),
            type(promotion.as_text_binding())(
                evidence_id=promotion.evidence_id,
                timed_transcript_id=promotion.timed_transcript_id,
                start_cue_index=promotion.start_cue_index,
                end_cue_index=promotion.end_cue_index,
                excerpt="different excerpt entirely",
                excerpt_hash=sha256(b"different excerpt entirely").hexdigest(),
            ),
            now=NOW,
        )


def test_E5_half_open_cue_range_remains_exact(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    promotion = _promotion(repository)
    verified = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert verified is not None
    window = verified.cues[promotion.start_cue_index : promotion.end_cue_index]
    assert len(window) == promotion.end_cue_index - promotion.start_cue_index
    assert promotion.excerpt == "\n".join(cue.text for cue in window)
    repository.promote_summary_evidence(
        promotion.as_evidence_write(), promotion.as_text_binding(), now=NOW
    )
    resolved = repository.resolve_verified_evidence_text(promotion.evidence_id)
    assert resolved is not None
    assert resolved.excerpt == promotion.excerpt


# --- E6: coherent commit -------------------------------------------------


def test_E6_analysis_transaction_commits_coherently(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    _scored_with_job(repository)
    request = _reserve(repository)
    artifacts, completion = _analysis_artifacts(repository, request)
    promotion = _promotion(repository)
    result = repository.complete_analysis_stage(
        job_id="analysis-job",
        owner="worker-1",
        video_id=VIDEO_ID,
        pipeline_version=PIPELINE,
        artifacts=artifacts,
        provider_call=completion,
        summary_promotions=((promotion.as_evidence_write(), promotion.as_text_binding()),),
        now=NOW,
    )
    assert result.job.status is JobStatus.SUCCEEDED
    assert result.video.pipeline_status is PipelineStatus.ANALYSIS_READY
    assert result.provider_call is not None
    assert result.provider_call.status is ProviderCallStatus.SUCCEEDED
    assert len(result.artifacts) == 2
    resolved = repository.resolve_verified_evidence_text(promotion.evidence_id)
    assert resolved is not None
    assert resolved.excerpt == promotion.excerpt


# --- E7-E10: rollback ----------------------------------------------------


@pytest.mark.parametrize(
    "failure_point",
    [
        "stage.after_summary_promotion",
        "stage.after_artifacts",
        "stage.after_provider_call",
        "stage.after_pipeline",
    ],
)
def test_E7_to_E10_injected_failure_rolls_back_all_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_point: str
) -> None:
    repository = _seed(tmp_path)
    _scored_with_job(repository)
    request = _reserve(repository)
    artifacts, completion = _analysis_artifacts(repository, request)
    promotion = _promotion(repository)

    original = SQLiteStateRepository._inject_failure

    def _inject(self: SQLiteStateRepository, point: str) -> None:
        if point == failure_point:
            raise IntegrityConflict(f"injected failure at {point}")
        original(self, point)

    monkeypatch.setattr(SQLiteStateRepository, "_inject_failure", _inject)

    with pytest.raises(IntegrityConflict):
        repository.complete_analysis_stage(
            job_id="analysis-job",
            owner="worker-1",
            video_id=VIDEO_ID,
            pipeline_version=PIPELINE,
            artifacts=artifacts,
            provider_call=completion,
            summary_promotions=((promotion.as_evidence_write(), promotion.as_text_binding()),),
            now=NOW,
        )

    # No promoted Evidence authority survives the rollback.
    assert promotion.evidence_id not in repository.list_summary_promoted_evidence_ids(VIDEO_ID)
    assert repository.resolve_verified_evidence_text(promotion.evidence_id) is None
    # No committed stage authority.
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.SCORED
    assert repository.get_job("analysis-job").status is JobStatus.RUNNING
    call = repository.get_provider_call(request.request_hash)
    assert call is None or call.status is not ProviderCallStatus.SUCCEEDED


# --- E11/E12: cache reuse ------------------------------------------------


def test_E11_cache_reuse_path_succeeds_without_promotions(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    _scored_with_job(repository)
    result = repository.complete_analysis_stage(
        job_id="analysis-job",
        owner="worker-1",
        video_id=VIDEO_ID,
        pipeline_version=PIPELINE,
        artifacts=(),
        provider_call=None,
        summary_promotions=(),
        now=NOW,
    )
    assert result.job.status is JobStatus.SUCCEEDED
    assert result.video.pipeline_status is PipelineStatus.ANALYSIS_READY
    assert result.provider_call is None
    assert result.artifacts == ()
    assert result.promoted_evidence == ()


def test_E12_cache_reuse_creates_no_evidence(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    _scored_with_job(repository)
    before = repository.list_canonical_coverage_evidence_ids(VIDEO_ID)
    repository.complete_analysis_stage(
        job_id="analysis-job",
        owner="worker-1",
        video_id=VIDEO_ID,
        pipeline_version=PIPELINE,
        artifacts=(),
        provider_call=None,
        summary_promotions=(),
        now=NOW,
    )
    assert repository.list_summary_promoted_evidence_ids(VIDEO_ID) == ()
    assert repository.list_canonical_coverage_evidence_ids(VIDEO_ID) == before


# --- E13-E15: guards -----------------------------------------------------


def test_E13_wrong_processing_stage_rejected(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    repository.create_job(
        job_id="metadata-job",
        scope_key=f"video:{VIDEO_ID}:METADATA",
        video_id=VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.METADATA,
        pipeline_version=PIPELINE,
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    repository.claim_next_job(owner="worker-1", lease_until=NOW + td(minutes=10), now=NOW)
    with pytest.raises(ConcurrencyConflict, match="ANALYSIS"):
        repository.complete_analysis_stage(
            job_id="metadata-job",
            owner="worker-1",
            video_id=VIDEO_ID,
            pipeline_version=PIPELINE,
            artifacts=(),
            provider_call=None,
            summary_promotions=(),
            now=NOW,
        )


def test_E14_wrong_transition_rejected(tmp_path: Path) -> None:
    """The video is not at SCORED, so the ANALYSIS transition cannot apply."""
    repository = _seed(tmp_path)
    _scored_with_job(repository, job_id="analysis-job-2")
    # Force the video back so the guarded UPDATE cannot match.
    repository._connect().execute(
        "UPDATE videos SET pipeline_status = ? WHERE video_id = ?",
        (PipelineStatus.SCORED.value, VIDEO_ID),
    )
    with pytest.raises((ConcurrencyConflict, IntegrityConflict)):
        repository.complete_analysis_stage(
            job_id="analysis-job-2",
            owner="worker-1",
            video_id=VIDEO_ID,
            pipeline_version="wrong-pipeline",
            artifacts=(),
            provider_call=None,
            summary_promotions=(),
            now=NOW,
        )


def test_E15_wrong_pipeline_version_rejected(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    _scored_with_job(repository)
    with pytest.raises(ConcurrencyConflict, match="scope"):
        repository.complete_analysis_stage(
            job_id="analysis-job",
            owner="worker-1",
            video_id=VIDEO_ID,
            pipeline_version="not-the-pipeline",
            artifacts=(),
            provider_call=None,
            summary_promotions=(),
            now=NOW,
        )


def test_E15b_wrong_owner_rejected(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    _scored_with_job(repository)
    with pytest.raises(Exception):
        repository.complete_analysis_stage(
            job_id="analysis-job",
            owner="someone-else",
            video_id=VIDEO_ID,
            pipeline_version=PIPELINE,
            artifacts=(),
            provider_call=None,
            summary_promotions=(),
            now=NOW,
        )


def test_E15c_foreign_video_promotion_rejected(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    _scored_with_job(repository)
    promotion = _promotion(repository)
    foreign = promotion.as_evidence_write()
    object.__setattr__(foreign, "video_id", "another-video")
    with pytest.raises(ConcurrencyConflict, match="foreign video"):
        repository.complete_analysis_stage(
            job_id="analysis-job",
            owner="worker-1",
            video_id=VIDEO_ID,
            pipeline_version=PIPELINE,
            artifacts=(),
            provider_call=None,
            summary_promotions=((foreign, promotion.as_text_binding()),),
            now=NOW,
        )
    assert repository.list_summary_promoted_evidence_ids(VIDEO_ID) == ()


# --- E16: existing complete_stage unchanged ------------------------------


def test_E16_existing_complete_stage_remains_compatible(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    _drive_stage(
        repository,
        job_id="job-metadata",
        expected=PipelineStatus.DISCOVERED,
        target=PipelineStatus.METADATA_READY,
        stage=ProcessingStage.METADATA,
    )
    repository.create_job(
        job_id="transcript-job",
        scope_key=f"video:{VIDEO_ID}:TRANSCRIPT",
        video_id=VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.TRANSCRIPT,
        pipeline_version=PIPELINE,
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    repository.claim_next_job(owner="worker-1", lease_until=NOW + td(minutes=10), now=NOW)
    result = repository.complete_stage(
        job_id="transcript-job",
        owner="worker-1",
        video_id=VIDEO_ID,
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version=PIPELINE,
        artifacts=(),
        provider_call=None,
        now=NOW,
    )
    assert result.video.pipeline_status is PipelineStatus.TRANSCRIPT_READY
    # The generic entry never acquires Summary Evidence authority.
    assert result.promoted_evidence == ()


def test_E16b_scored_completion_still_requires_runtime_entry(tmp_path: Path) -> None:
    """The existing SCORED trusted-persistence rule must not regress."""

    repository = _seed(tmp_path)
    with pytest.raises(IntegrityConflict, match="runtime trusted persistence entry"):
        repository.complete_stage(
            job_id="anything",
            owner="worker-1",
            video_id=VIDEO_ID,
            expected_status=PipelineStatus.TRANSCRIPT_READY,
            target_status=PipelineStatus.SCORED,
            pipeline_version=PIPELINE,
            artifacts=(),
            provider_call=None,
            now=NOW,
        )
