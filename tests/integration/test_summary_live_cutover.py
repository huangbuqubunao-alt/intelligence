"""Live Summary cutover: backend-authoritative Evidence in the production path.

Every test here drives ``RepositoryBackedAnalysisService.analyze`` — the only
live Summary production path — against a real ``SQLiteStateRepository`` and a
recording provider. The frozen invariant under test is:

    The LLM may interpret Evidence, select Evidence, and cite Evidence.
    The LLM may not author Evidence text, offsets, timestamps, or trusted IDs.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from youtube_intel.analysis import (
    SUMMARY_DRAFT_PROMPT_VERSION,
    AnalysisJobContext,
    AnalysisPolicyError,
    CloudCallBudget,
    RepositoryBackedAnalysisService,
    build_analysis_input,
    build_summary_evidence_registry,
    summary_draft_request,
)
from youtube_intel.config import LocalAnalysisSettings
from youtube_intel.domain import (
    AnalysisResult,
    Availability,
    ErrorCode,
    EvidenceSource,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    VideoMetadata,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    JobStatus,
    JobType,
    ProviderCallStatus,
    ProviderDispatchStatus,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
)
from youtube_intel.summary_draft import (
    SUMMARY_DRAFT_SCHEMA_VERSION,
    SummaryDraft,
    SummaryDraftPoint,
)
from youtube_intel.summary_evidence_candidates import TrustedEvidenceRegistry

# Freeze metadata and registry inputs at import; active job leases are anchored
# separately to their actual claim time, even after a long suite or restart.
NOW = datetime.now(UTC)
VIDEO_ID = "ausLKMojXaY"
PIPELINE = "pipeline-v1"
OWNER = "worker-cutover"
TITLE = "The Phone Number puzzle"
CHANNEL = "3Blue1Brown"
DESCRIPTION = "A short public product lesson."
TRANSCRIPT_TEXT = "canonical transcript for the live Summary cutover"
CUE_TEXTS = tuple(
    (f"cue{index} " + f"sentence{index} " * 20).strip() for index in range(6)
)
OTHER_CUE_TEXT = (
    "a completely different authoritative sentence " * 30
).strip()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _metadata() -> VideoMetadata:
    return VideoMetadata(
        video_id=VIDEO_ID,
        channel_id="UC_TEST",
        channel_name=CHANNEL,
        title=TITLE,
        description=DESCRIPTION,
        source_url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
        published_at=NOW,
        duration_seconds=44,
        default_language="en",
        available_languages=("en",),
        live_status=LiveStatus.ENDED,
        availability=Availability.PUBLIC,
    )


def _settings() -> LocalAnalysisSettings:
    return LocalAnalysisSettings(
        model="qwen3:8b",
        expected_model_digest="sha256:" + "1" * 64,
    )


def _seed(
    tmp_path: Path,
    *,
    cues: tuple[str, ...] = CUE_TEXTS,
    timed: bool = True,
) -> SQLiteStateRepository:
    tmp_path.mkdir(parents=True, exist_ok=True)
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    repository.upsert_video_metadata(
        _metadata(), pipeline_version=PIPELINE, now=NOW
    )
    for before, after in (
        (PipelineStatus.DISCOVERED, PipelineStatus.METADATA_READY),
        (PipelineStatus.METADATA_READY, PipelineStatus.TRANSCRIPT_READY),
    ):
        assert repository.advance_pipeline(
            VIDEO_ID,
            expected_status=before,
            target_status=after,
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
            content_hash=sha256(TRANSCRIPT_TEXT.encode()).hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    if timed:
        repository.create_timed_transcript(
            TimedTranscriptWrite.from_cues(
                video_id=VIDEO_ID,
                canonical_artifact_id="artifact-1",
                cues=tuple(
                    TimedTranscriptCueWrite(
                        start_ms=index * 1000,
                        end_ms=(index + 1) * 1000,
                        text=text,
                    )
                    for index, text in enumerate(cues)
                ),
            ),
            now=NOW,
        )
    # SCORED is deliberately not reachable through complete_stage: scoring uses
    # the runtime trusted-persistence entry, so drive it directly as production
    # does, then leave a RUNNING ANALYSIS job owned by OWNER.
    assert repository.advance_pipeline(
        VIDEO_ID,
        expected_status=PipelineStatus.TRANSCRIPT_READY,
        target_status=PipelineStatus.SCORED,
        pipeline_version=PIPELINE,
        now=NOW,
    )
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET should_summarize = 1 WHERE video_id = ?", (VIDEO_ID,)
        )
    finally:
        connection.close()
    _claim_analysis_job(repository, job_id="analysis-job")
    return repository


def _claim_analysis_job(
    repository: SQLiteStateRepository, *, job_id: str, now: datetime | None = None
) -> str:
    if now is None:
        now = datetime.now(UTC)
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:{VIDEO_ID}:ANALYSIS",
        video_id=VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.ANALYSIS,
        pipeline_version=PIPELINE,
        max_attempts=3,
        available_at=now,
        now=now,
    )
    assert repository.claim_next_job(
        owner=OWNER, lease_until=now + timedelta(minutes=10), now=now
    )
    assert repository.get_job(job_id).status is JobStatus.RUNNING
    return job_id


def _registry(repository: SQLiteStateRepository) -> TrustedEvidenceRegistry:
    verified = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert verified is not None
    return build_summary_evidence_registry(
        verified=verified,
        video_id=VIDEO_ID,
        title=TITLE,
        channel_name=CHANNEL,
        description=DESCRIPTION,
        transcript_text=TRANSCRIPT_TEXT,
    )


def _transcript_refs(
    registry: TrustedEvidenceRegistry,
) -> tuple[str, ...]:
    return tuple(
        candidate.ref
        for candidate in registry.candidates
        if candidate.source is EvidenceSource.TRANSCRIPT_SAMPLE
    )


def _first_transcript_ref(repository: SQLiteStateRepository) -> str:
    return _transcript_refs(_registry(repository))[0]


def _second_transcript_ref(repository: SQLiteStateRepository) -> str:
    return _transcript_refs(_registry(repository))[1]


def _draft(*refs: str) -> SummaryDraft:
    return SummaryDraft(
        one_sentence_summary="摘要",
        core_points=(
            SummaryDraftPoint(text="要点", kind="fact", evidence_refs=refs or ("x",)),
        ),
        keywords=("k",),
    )


class _RecordingProvider:
    """A provider that only cites what the backend actually issued."""

    def __init__(self, *, refs: tuple[str, ...] | None = None) -> None:
        self.events: list[str] = []
        self.generation_calls = 0
        self.seen: list[AnalysisResult] = []
        self._refs = refs
        self._responses: list[Any] = []
        self._raw: str | None = None
        self._request_hash: str | None = None

    def queue(self, response: Any) -> None:
        self._responses.append(response)

    def summarize(self, analysis_input: object) -> SummaryDraft:
        self.events.append("provider-call")
        self.generation_calls += 1
        if self._responses:
            response = self._responses.pop(0)
            if isinstance(response, BaseException):
                raise response
            draft = response
        else:
            assert self._refs is not None
            draft = _draft(*self._refs)
        self.seen.append(analysis_input)  # type: ignore[arg-type]
        self._raw = json.dumps({"model": "qwen3:8b", "done": True})
        self._request_hash = getattr(analysis_input, "request_hash")
        return draft

    def consume_raw_response(self, *, request_hash: str) -> str:
        assert self._request_hash == request_hash
        assert self._raw is not None
        return self._raw


class _ExplodingProvider:
    def __init__(self, failure: BaseException) -> None:
        self.failure = failure
        self.generation_calls = 0

    def summarize(self, analysis_input: object) -> SummaryDraft:
        del analysis_input
        self.generation_calls += 1
        raise self.failure


def _service(
    repository: SQLiteStateRepository,
    provider: Any,
    tmp_path: Path,
    *,
    job_id: str = "analysis-job",
) -> RepositoryBackedAnalysisService:
    return RepositoryBackedAnalysisService(
        provider=provider,
        settings=_settings(),
        repository=repository,
        context=AnalysisJobContext(job_id, OWNER, PIPELINE),
        artifact_root=tmp_path / "data",
        credential_resolver=SimpleNamespace(),
        budget=CloudCallBudget(limit=5),
    )


def _analyze(service: RepositoryBackedAnalysisService) -> Any:
    return service.analyze(
        video=_metadata(),
        transcript_text=TRANSCRIPT_TEXT,
        language="en",
        output_language="zh-CN",
    )


def _reopen(tmp_path: Path) -> SQLiteStateRepository:
    """Simulate a process restart: a fresh handle over the same database."""

    return SQLiteStateRepository(tmp_path / "state.sqlite3")


# --- 1. registry is built before the provider is contacted -----------------


def test_registry_is_built_before_any_provider_or_dispatch_state(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    ref = _first_transcript_ref(repository)
    provider = _RecordingProvider(refs=(ref,))
    events: list[str] = []
    real_read = repository.get_verified_timed_transcript
    real_reserve = repository.reserve_provider_call
    real_intent = repository.record_provider_dispatch_intent
    real_summarize = provider.summarize

    def read(*args: Any, **kwargs: Any) -> Any:
        events.append("read-verified-timed-transcript")
        return real_read(*args, **kwargs)

    def reserve(*args: Any, **kwargs: Any) -> Any:
        events.append("reserve-provider-call")
        return real_reserve(*args, **kwargs)

    def record_intent(*args: Any, **kwargs: Any) -> Any:
        events.append("dispatch-intent")
        return real_intent(*args, **kwargs)

    def summarize(analysis_input: object) -> SummaryDraft:
        events.append("provider-call")
        return real_summarize(analysis_input)

    repository.get_verified_timed_transcript = read  # type: ignore[method-assign]
    repository.reserve_provider_call = reserve  # type: ignore[method-assign]
    repository.record_provider_dispatch_intent = record_intent  # type: ignore[method-assign]
    provider.summarize = summarize  # type: ignore[method-assign]

    _analyze(_service(repository, provider, tmp_path))

    assert events[0] == "read-verified-timed-transcript"
    assert "reserve-provider-call" in events
    assert events.index("read-verified-timed-transcript") < events.index(
        "reserve-provider-call"
    )
    assert events.index("read-verified-timed-transcript") < events.index(
        "provider-call"
    )
    # The registry itself is bound to the request the provider receives.
    offer = provider.seen[0].trusted_evidence
    assert offer is not None
    assert offer.registry_identity == _registry(repository).identity_hash()


# --- 2. request identity is bound to the registry -------------------------


def _request_hash(registry: TrustedEvidenceRegistry) -> str:
    return build_analysis_input(
        video=_metadata(),
        transcript_text=TRANSCRIPT_TEXT,
        language="en",
        output_language="zh-CN",
        settings=_settings(),
        provider="ollama",
        operation="local-analysis",
        prompt_version=SUMMARY_DRAFT_PROMPT_VERSION,
        registry=registry,
    ).request_hash


def test_same_authoritative_input_and_registry_produce_the_same_request(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    assert _request_hash(_registry(repository)) == _request_hash(
        _registry(repository)
    )


def test_request_identity_changes_when_the_registry_changes(
    tmp_path: Path,
) -> None:
    baseline = _seed(tmp_path / "baseline")
    baseline_hash = _request_hash(_registry(baseline))

    # Candidate text changes: a different authoritative source span.
    retexted = _seed(tmp_path / "retexted", cues=CUE_TEXTS[:-1] + (OTHER_CUE_TEXT,))
    assert _registry(retexted).identity_hash() != _registry(baseline).identity_hash()
    assert _request_hash(_registry(retexted)) != baseline_hash

    # The cue range changes: one cue instead of six.
    reranged = _seed(tmp_path / "reranged", cues=CUE_TEXTS[:1])
    assert _registry(reranged).identity_hash() != _registry(baseline).identity_hash()
    assert _request_hash(_registry(reranged)) != baseline_hash

    # The authoritative transcript identity changes.
    other = _seed(tmp_path / "other", cues=tuple(f"other cue {i} text" for i in range(6)))
    assert _registry(other).identity_hash() != _registry(baseline).identity_hash()
    assert _request_hash(_registry(other)) != baseline_hash


def test_no_registry_means_no_distinct_identity_from_a_registry() -> None:
    """A request without a registry keeps the pre-cutover identity untouched."""

    without = build_analysis_input(
        video=_metadata(),
        transcript_text=TRANSCRIPT_TEXT,
        language="en",
        output_language="zh-CN",
        settings=_settings(),
        provider="ollama",
        operation="local-analysis",
        prompt_version=SUMMARY_DRAFT_PROMPT_VERSION,
    )
    assert without.trusted_evidence is None


def test_restart_reproduces_the_same_request_identity_and_reuses_the_cache(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    ref = _first_transcript_ref(repository)
    provider = _RecordingProvider(refs=(ref,))
    first = _analyze(_service(repository, provider, tmp_path))
    assert first is not None
    request_hash = first.result.request_hash
    registry_identity = _registry(repository).identity_hash()
    persisted = repository.get_provider_call(request_hash)
    assert persisted is not None
    assert persisted.prompt_version == SUMMARY_DRAFT_PROMPT_VERSION
    assert provider.generation_calls == 1

    # A restart: a fresh handle, a fresh ANALYSIS job, a fresh provider object.
    restarted_repository = _reopen(tmp_path)
    connection = restarted_repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET pipeline_status = ? WHERE video_id = ?",
            (PipelineStatus.SCORED.value, VIDEO_ID),
        )
    finally:
        connection.close()
    _claim_analysis_job(
        restarted_repository, job_id="analysis-after-restart"
    )
    # The registry is rebuilt from a fresh trusted read, not carried over.
    assert _registry(restarted_repository).identity_hash() == registry_identity
    assert _request_hash(_registry(restarted_repository)) == request_hash

    restarted_provider = _RecordingProvider(refs=(ref,))
    reused = _analyze(
        _service(
            restarted_repository,
            restarted_provider,
            tmp_path,
            job_id="analysis-after-restart",
        )
    )
    assert reused.result.request_hash == request_hash
    assert restarted_provider.generation_calls == 0
    assert provider.generation_calls == 1


# --- 3. hydration happens before artifact serialization and hashing --------


def test_hydration_precedes_artifact_serialization_and_hashing(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    ref = _first_transcript_ref(repository)
    issued = _registry(repository).by_ref()[ref]
    provider = _RecordingProvider(refs=(ref,))

    outcome = _analyze(_service(repository, provider, tmp_path))

    assert outcome is not None
    # The persisted result carries backend-owned text, never model text.
    assert outcome.result.evidence[0].excerpt == issued.text
    assert "要点" not in outcome.result.evidence[0].excerpt
    structured = repository.get_artifact_by_key(
        f"analysis/{outcome.result.request_hash}/structured"
    )
    assert structured is not None
    body = (tmp_path / "data" / structured.relative_path).read_bytes()
    assert structured.content_hash == sha256(body).hexdigest()
    persisted = AnalysisResult.model_validate_json(body)
    assert persisted.evidence == outcome.result.evidence
    assert persisted.evidence[0].excerpt == issued.text
    assert "excerpt" not in json.loads(body)["core_points"][0]


def test_only_selected_timed_refs_become_promotions(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    first, second = _transcript_refs(_registry(repository))[:2]
    provider = _RecordingProvider(refs=(first,))

    outcome = _analyze(_service(repository, provider, tmp_path))

    assert outcome is not None
    promoted = repository.list_summary_promoted_evidence_ids(VIDEO_ID)
    assert len(promoted) == 1
    resolved = repository.resolve_verified_evidence_text(promoted[0])
    assert resolved is not None
    assert resolved.excerpt == _registry(repository).by_ref()[first].text
    # The unselected candidate was never promoted.
    verified = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert verified is not None
    unselected = _registry(repository).by_ref()[second]
    assert unselected.text not in {
        text for text in (resolved.excerpt,)
    }
    # Metadata selections need no promotion at all.
    metadata_ref = next(
        candidate.ref
        for candidate in _registry(repository).candidates
        if candidate.source is EvidenceSource.TITLE
    )
    metadata_only = _RecordingProvider(refs=(metadata_ref,))
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET pipeline_status = ? WHERE video_id = ?",
            (PipelineStatus.SCORED.value, VIDEO_ID),
        )
    finally:
        connection.close()
    _claim_analysis_job(repository, job_id="metadata-only-job")
    before = repository.list_summary_promoted_evidence_ids(VIDEO_ID)
    outcome = _analyze(
        _service(repository, metadata_only, tmp_path, job_id="metadata-only-job")
    )
    assert outcome is not None
    assert repository.list_summary_promoted_evidence_ids(VIDEO_ID) == before


# --- 4. normal completion is the atomic ANALYSIS entry ---------------------


def test_normal_path_uses_complete_analysis_stage_and_no_standalone_promotion(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    ref = _first_transcript_ref(repository)
    provider = _RecordingProvider(refs=(ref,))
    recorded: dict[str, Any] = {"stage": [], "promote": []}
    real_stage = repository.complete_analysis_stage
    real_promote = repository.promote_summary_evidence

    def stage(**kwargs: Any) -> Any:
        recorded["stage"].append(kwargs)
        return real_stage(**kwargs)

    def promote(*args: Any, **kwargs: Any) -> Any:
        recorded["promote"].append((args, kwargs))
        return real_promote(*args, **kwargs)

    repository.complete_analysis_stage = stage  # type: ignore[method-assign]
    repository.promote_summary_evidence = promote  # type: ignore[method-assign]

    outcome = _analyze(_service(repository, provider, tmp_path))

    assert outcome is not None
    assert recorded["promote"] == [], (
        "the live path must never open a standalone promotion transaction "
        "before the stage transaction"
    )
    assert len(recorded["stage"]) == 1
    call = recorded["stage"][0]
    assert call["pipeline_version"] == PIPELINE
    assert call["provider_call"] is not None
    assert len(call["summary_promotions"]) == 1
    assert call["summary_promotions"][0][1].excerpt == _registry(repository).by_ref()[
        ref
    ].text
    assert repository.get_video(VIDEO_ID).pipeline_status is (
        PipelineStatus.ANALYSIS_READY
    )
    assert repository.get_job("analysis-job").status is JobStatus.SUCCEEDED
    promoted = repository.list_summary_promoted_evidence_ids(VIDEO_ID)
    assert len(promoted) == 1
    evidence = repository.resolve_verified_evidence_text(promoted[0])
    assert evidence is not None
    assert evidence.excerpt == _registry(repository).by_ref()[ref].text


def test_promotion_is_rolled_back_with_the_stage_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _seed(tmp_path)
    ref = _first_transcript_ref(repository)
    provider = _RecordingProvider(refs=(ref,))

    def inject(self: SQLiteStateRepository, point: str) -> None:
        if point == "stage.after_summary_promotion":
            from youtube_intel.state import IntegrityConflict

            raise IntegrityConflict(f"injected failure at {point}")

    monkeypatch.setattr(SQLiteStateRepository, "_inject_failure", inject)

    with pytest.raises(Exception):
        _analyze(_service(repository, provider, tmp_path))

    assert repository.list_summary_promoted_evidence_ids(VIDEO_ID) == ()
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.SCORED
    assert repository.get_job("analysis-job").status is JobStatus.RUNNING
    assert not list((tmp_path / "data" / "analysis").glob("*/structured.json"))


# --- 5. cache reuse is the second completion path -------------------------


def test_cache_reuse_completes_through_the_same_entry_with_no_promotions(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    ref = _first_transcript_ref(repository)
    first_provider = _RecordingProvider(refs=(ref,))
    first = _analyze(_service(repository, first_provider, tmp_path))
    assert first is not None
    promoted_before = repository.list_summary_promoted_evidence_ids(VIDEO_ID)

    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET pipeline_status = ? WHERE video_id = ?",
            (PipelineStatus.SCORED.value, VIDEO_ID),
        )
    finally:
        connection.close()
    _claim_analysis_job(repository, job_id="analysis-reordered")

    recorded: list[dict[str, Any]] = []
    real_stage = repository.complete_analysis_stage
    real_promote = repository.promote_summary_evidence
    promoted: list[Any] = []

    def stage(**kwargs: Any) -> Any:
        recorded.append(kwargs)
        return real_stage(**kwargs)

    def promote(*args: Any, **kwargs: Any) -> Any:
        promoted.append((args, kwargs))
        return real_promote(*args, **kwargs)

    repository.complete_analysis_stage = stage  # type: ignore[method-assign]
    repository.promote_summary_evidence = promote  # type: ignore[method-assign]
    reuse_provider = _RecordingProvider(refs=(ref,))

    reused = _analyze(
        _service(repository, reuse_provider, tmp_path, job_id="analysis-reordered")
    )

    assert reused is not None
    assert reused.result.request_hash == first.result.request_hash
    assert reuse_provider.generation_calls == 0, "cache reuse must not call a provider"
    assert promoted == []
    assert len(recorded) == 1
    assert recorded[0]["artifacts"] == ()
    assert recorded[0]["provider_call"] is None
    assert recorded[0]["summary_promotions"] == ()
    assert repository.list_summary_promoted_evidence_ids(VIDEO_ID) == promoted_before
    assert repository.get_video(VIDEO_ID).pipeline_status is (
        PipelineStatus.ANALYSIS_READY
    )
    assert repository.get_job("analysis-reordered").status is JobStatus.SUCCEEDED


# --- 6. canonical-only Content fails closed --------------------------------


def test_canonical_only_content_fails_closed_before_any_dispatch(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path, timed=False)
    assert repository.get_verified_timed_transcript(video_id=VIDEO_ID) is None
    provider = _RecordingProvider()
    dispatch: list[str] = []
    real_reserve = repository.reserve_provider_call

    def reserve(*args: Any, **kwargs: Any) -> Any:
        dispatch.append("reserve")
        return real_reserve(*args, **kwargs)

    repository.reserve_provider_call = reserve  # type: ignore[method-assign]

    with pytest.raises(AnalysisPolicyError) as raised:
        _analyze(_service(repository, provider, tmp_path))

    assert raised.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert raised.value.error.retryable is True
    assert provider.generation_calls == 0
    assert dispatch == []
    assert repository.list_summary_promoted_evidence_ids(VIDEO_ID) == ()
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.SCORED
    assert repository.get_job("analysis-job").status is JobStatus.RUNNING


# --- 7. failure classification --------------------------------------------


def _dispatch_after(
    tmp_path: Path, response: Any
) -> tuple[SQLiteStateRepository, ProviderDispatchStatus | None, Any]:
    repository = _seed(tmp_path)
    provider = _RecordingProvider()
    provider.queue(response)
    with pytest.raises(AnalysisPolicyError) as raised:
        _analyze(_service(repository, provider, tmp_path))
    assert raised.value.error.code is ErrorCode.INVALID_RESPONSE
    assert raised.value.error.retryable is False
    request_hash = provider.seen[0].request_hash if provider.seen else None
    if request_hash is None:
        connection = repository._connect()
        try:
            row = connection.execute(
                "SELECT request_hash FROM provider_calls"
            ).fetchone()
        finally:
            connection.close()
        request_hash = row[0]
    dispatch = repository.get_provider_dispatch(request_hash)
    call = repository.get_provider_call(request_hash)
    assert call is not None
    assert call.status is ProviderCallStatus.FAILED_FINAL
    return repository, None if dispatch is None else dispatch.status, provider


def test_unknown_evidence_ref_is_a_known_failure_not_dispatch_ambiguity(
    tmp_path: Path,
) -> None:
    _, dispatch, provider = _dispatch_after(
        tmp_path, _draft("t0-4-deadbeefdeadbeef")
    )
    assert dispatch is ProviderDispatchStatus.FAILED_KNOWN
    assert provider.generation_calls == 1


def test_foreign_evidence_ref_is_a_known_failure_not_dispatch_ambiguity(
    tmp_path: Path,
) -> None:
    other = _seed(tmp_path / "other", cues=tuple(f"foreign {i} cue" for i in range(6)))
    foreign_ref = _first_transcript_ref(other)
    _, dispatch, _ = _dispatch_after(tmp_path, _draft(foreign_ref))
    assert dispatch is ProviderDispatchStatus.FAILED_KNOWN


def test_hydration_validation_failure_is_a_known_failure_not_ambiguity(
    tmp_path: Path,
) -> None:
    """A draft that cannot become a persisted result is a local failure."""

    bad_kind = SummaryDraft.model_construct(
        one_sentence_summary="s",
        core_points=(
            SummaryDraftPoint.model_construct(
                text="t", kind="recommendation", evidence_refs=("r",)
            ),
        ),
        key_facts=(),
        product_opportunities=(),
        business_opportunities=(),
        actionable_directions=(),
        hypotheses_to_validate=(),
        action_recommendations=(),
        risks=(),
        keywords=("k",),
    )
    repository = _seed(tmp_path)
    provider = _RecordingProvider()
    provider.queue(bad_kind)
    with pytest.raises(AnalysisPolicyError) as raised:
        _analyze(_service(repository, provider, tmp_path))

    assert raised.value.error.code is ErrorCode.INVALID_RESPONSE
    assert raised.value.error.retryable is False
    request_hash = provider.seen[0].request_hash
    assert (
        repository.get_provider_dispatch(request_hash).status
        is ProviderDispatchStatus.FAILED_KNOWN
    )
    assert repository.list_summary_promoted_evidence_ids(VIDEO_ID) == ()
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.SCORED


def test_local_validation_failure_is_never_marked_ambiguous(
    tmp_path: Path,
) -> None:
    """No known-response failure may reach mark_provider_dispatch_ambiguous."""

    for index, response in enumerate(
        (
            _draft("t0-4-deadbeefdeadbeef"),
            _draft("no-such-ref-at-all"),
        )
    ):
        case = tmp_path / f"case{index}"
        repository = _seed(case)
        ambiguous: list[str] = []
        known: list[str] = []
        real_ambiguous = repository.mark_provider_dispatch_ambiguous
        real_known = repository.record_provider_dispatch_known_failure

        def mark(*args: Any, _inner=real_ambiguous, **kwargs: Any) -> Any:
            ambiguous.append("ambiguous")
            return _inner(*args, **kwargs)

        def record_known(*args: Any, _inner=real_known, **kwargs: Any) -> Any:
            known.append("known")
            return _inner(*args, **kwargs)

        repository.mark_provider_dispatch_ambiguous = mark  # type: ignore[method-assign]
        repository.record_provider_dispatch_known_failure = record_known  # type: ignore[method-assign]

        provider = _RecordingProvider()
        provider.queue(response)
        with pytest.raises(AnalysisPolicyError) as raised:
            _analyze(_service(repository, provider, case))
        assert raised.value.error.code is ErrorCode.INVALID_RESPONSE
        assert ambiguous == []
        assert known == ["known"]


def test_genuine_dispatch_ambiguity_is_unchanged(tmp_path: Path) -> None:
    """A transport-level unknown stays ambiguous, exactly as before."""

    repository = _seed(tmp_path)
    provider = _ExplodingProvider(TimeoutError("transport result unknown"))
    with pytest.raises(TimeoutError):
        _analyze(_service(repository, provider, tmp_path))

    connection = repository._connect()
    try:
        request_hash = connection.execute(
            "SELECT request_hash FROM provider_calls"
        ).fetchone()[0]
    finally:
        connection.close()
    assert (
        repository.get_provider_dispatch(request_hash).status
        is ProviderDispatchStatus.AMBIGUOUS
    )
    assert provider.generation_calls == 1
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.SCORED


def test_known_failure_transition_is_valid_after_a_received_response(
    tmp_path: Path,
) -> None:
    """A returned-but-uncommitted result can still be proven known-failed."""

    from youtube_intel.state import LeaseConflict, ProviderCallRequest

    repository = _seed(tmp_path)
    request = ProviderCallRequest(
        operation="local-analysis",
        normalized_input_hash="a" * 64,
        provider="ollama",
        model="qwen3:8b",
        prompt_version=SUMMARY_DRAFT_PROMPT_VERSION,
        schema_version="analysis-result-v1",
        deterministic_artifact_key="analysis/cutover-known/raw",
    )
    now = datetime.now(UTC)
    assert repository.reserve_provider_call(
        request,
        owner=OWNER,
        lease_until=now + timedelta(minutes=10),
        available_at=now,
        now=now,
        fail_closed_on_ambiguous_dispatch=True,
    ).acquired
    repository.record_provider_dispatch_intent(
        request.request_hash, owner=OWNER, now=now
    )
    repository.record_provider_dispatch_result_unknown(
        request.request_hash, owner=OWNER, now=now
    )
    record = repository.record_provider_dispatch_known_failure(
        request.request_hash, owner=OWNER, now=now
    )
    assert record.status is ProviderDispatchStatus.FAILED_KNOWN

    # A genuine ambiguity has no known-failure transition.
    other = ProviderCallRequest(
        operation="local-analysis",
        normalized_input_hash="b" * 64,
        provider="ollama",
        model="qwen3:8b",
        prompt_version=SUMMARY_DRAFT_PROMPT_VERSION,
        schema_version="analysis-result-v1",
        deterministic_artifact_key="analysis/cutover-ambiguous/raw",
    )
    assert repository.reserve_provider_call(
        other,
        owner=OWNER,
        lease_until=now + timedelta(minutes=10),
        available_at=now,
        now=now,
        fail_closed_on_ambiguous_dispatch=True,
    ).acquired
    repository.record_provider_dispatch_intent(
        other.request_hash, owner=OWNER, now=now
    )
    repository.mark_provider_dispatch_ambiguous(
        other.request_hash, owner=OWNER, now=now
    )
    with pytest.raises(LeaseConflict):
        repository.record_provider_dispatch_known_failure(
            other.request_hash, owner=OWNER, now=now
        )


# --- 8. the model-facing request carries no authority ---------------------


def test_live_request_offers_refs_and_text_only(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    ref = _first_transcript_ref(repository)
    provider = _RecordingProvider(refs=(ref,))
    _analyze(_service(repository, provider, tmp_path))
    analysis_input = provider.seen[0]
    offer = analysis_input.trusted_evidence
    assert offer is not None
    serialized = json.dumps(offer.model_dump(mode="json"), sort_keys=True)
    for forbidden in ("start_ms", "end_ms", "start_cue_index", "offset", "excerpt"):
        assert forbidden not in serialized
    draft_request = summary_draft_request(analysis_input)
    assert draft_request.schema["required"] == [
        "one_sentence_summary",
        "core_points",
        "keywords",
    ]
    assert "evidence" not in draft_request.schema["properties"]  # type: ignore[operator]
    assert "excerpt" not in json.dumps(draft_request.schema)
    assert SUMMARY_DRAFT_SCHEMA_VERSION == "summary-draft-v1"
    assert analysis_input.prompt_version == "analysis-prompt-v6"


def test_no_migration_is_required_for_the_cutover() -> None:
    """The cutover is a code change only: no schema change accompanies it."""

    repository = object.__new__(SQLiteStateRepository)
    migrations = repository._load_migrations()  # type: ignore[attr-defined]
    assert migrations
    assert not any("prompt" in getattr(item, "name", "").lower() for item in migrations)


def test_import_clock_does_not_expire_a_later_claim_or_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import youtube_intel.analysis as analysis_module

    current = [NOW + timedelta(minutes=11)]
    monkeypatch.setattr(
        f"{__name__}.datetime", SimpleNamespace(now=lambda _tz: current[0])
    )
    monkeypatch.setattr(analysis_module, "_utcnow", lambda: current[0])
    repository = _seed(tmp_path)
    ref = _first_transcript_ref(repository)
    provider = _RecordingProvider(refs=(ref,))
    outcome = _analyze(_service(repository, provider, tmp_path))
    assert outcome is not None
    first_job = repository.get_job("analysis-job")
    first_video = repository.get_video(VIDEO_ID)
    assert first_job is not None and first_video is not None
    assert first_job.status is JobStatus.SUCCEEDED
    assert first_video.pipeline_status is PipelineStatus.ANALYSIS_READY
    assert provider.generation_calls == 1
    assert repository.list_summary_promoted_evidence_ids(VIDEO_ID)
    request_hash = outcome.result.request_hash
    registry_identity = _registry(repository).identity_hash()

    current[0] += timedelta(minutes=11)
    restarted_repository = _reopen(tmp_path)
    connection = restarted_repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET pipeline_status = ? WHERE video_id = ?",
            (PipelineStatus.SCORED.value, VIDEO_ID),
        )
    finally:
        connection.close()
    _claim_analysis_job(restarted_repository, job_id="late-restart")
    restarted_provider = _RecordingProvider(refs=(ref,))
    reused = _analyze(
        _service(restarted_repository, restarted_provider, tmp_path, job_id="late-restart")
    )
    assert reused.result.request_hash == request_hash
    assert _registry(restarted_repository).identity_hash() == registry_identity
    assert restarted_provider.generation_calls == 0
    assert provider.generation_calls == 1
    restarted_job = restarted_repository.get_job("late-restart")
    restarted_video = restarted_repository.get_video(VIDEO_ID)
    assert restarted_job is not None and restarted_video is not None
    assert restarted_job.status is JobStatus.SUCCEEDED
    assert restarted_video.pipeline_status is PipelineStatus.ANALYSIS_READY


def test_actually_expired_analysis_lease_still_rejects_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import youtube_intel.analysis as analysis_module
    from youtube_intel.state import LeaseConflict

    monkeypatch.setattr(
        f"{__name__}.datetime", SimpleNamespace(now=lambda _tz: NOW)
    )
    repository = _seed(tmp_path)
    provider = _RecordingProvider(refs=(_first_transcript_ref(repository),))
    monkeypatch.setattr(analysis_module, "_utcnow", lambda: NOW + timedelta(minutes=11))
    with pytest.raises(LeaseConflict, match="job lease is not owned or has expired"):
        _analyze(_service(repository, provider, tmp_path))
    assert provider.generation_calls == 1
    expired_job = repository.get_job("analysis-job")
    uncompleted_video = repository.get_video(VIDEO_ID)
    assert expired_job is not None and uncompleted_video is not None
    assert expired_job.status is JobStatus.RUNNING
    assert uncompleted_video.pipeline_status is PipelineStatus.SCORED
    assert repository.list_summary_promoted_evidence_ids(VIDEO_ID) == ()
    assert repository.get_artifact_by_key(
        f"analysis/{provider.seen[0].request_hash}/structured"
    ) is None
