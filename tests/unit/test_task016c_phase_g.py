"""TASK-016C Phase G trusted prewrite persistence cutover tests (RED first).

Covers the frozen Phase G contract: F->G enriched aggregate continuation,
PREWRITE_VALIDATE, ValidatedScoringWritePlan, tmp/fsync/promote filesystem
ordering, atomic SQLite registration, normal runtime scoring-stage cutover,
legacy isolation, idempotency and the failure matrix.

Reference documents (authoritative):
- agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md
- docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md
- docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_intel.config import LocalScoringSettings, load_app_config
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    ScoreResult,
    ScoringInput,
    VideoMetadata,
)
from youtube_intel.providers.ollama import (
    OllamaQualityJudgeProvider,
    parse_scoring_candidate,
)
from youtube_intel.quality import (
    _TRUSTED_SCORE_RESULT_SENTINEL,
    _TRUSTED_SCORING_CONTEXT_SENTINEL,
    TrustedScoreResult,
    _mint_trusted_scoring_context,
    build_scoring_candidate_hash,
)
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
from youtube_intel.scoring import (
    PhaseFTrustedScoringSuccess,
    PrimaryScoringAttempt,
    ScoringJobContext,
    ScoringPersistenceError,
    TrustedScoringPersistenceCommitter,
    _EnrichedQualityEvidence,
    _mint_phase_f_trusted_scoring_success,
    build_primary_scoring_attempt,
    build_scoring_input,
    build_scoring_request_identity,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    IntegrityConflict,
    JobStatus,
    JobType,
    ProviderCallStatus,
    RetentionClass,
    SQLiteStateRepository,
    StageCompletionResult,
    StorageRoot,
)

_EN_REASON = (
    "This response explains a concrete product strategy with useful trade-offs."
)

_MODEL = "qwen3:8b"
_DIGEST = "sha256:" + ("a" * 64)


def _settings() -> LocalScoringSettings:
    return LocalScoringSettings(
        model=_MODEL,
        expected_model_digest=_DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_transcript_chars=64,
        max_description_chars=32,
    )


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id="video-phase-g",
        channel_id="channel-phase-g",
        channel_name="Phase G Channel",
        title="A useful scoring title",
        description="A deliberately bounded scoring description.",
        source_url="https://example.invalid/watch?v=video-phase-g",
        published_at=datetime(2026, 8, 18, tzinfo=UTC),
        duration_seconds=120,
        default_language="en",
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _scoring_input(
    *, output_language: str = "en", video_id: str = "video-phase-g"
) -> ScoringInput:
    return build_scoring_input(
        video=_video_with_id(video_id),
        transcript_text="This transcript contains enough text for a stable sample.",
        language="en",
        output_language=output_language,
        settings=_settings(),
    )


def _candidate_fields(
    *,
    score: float = 8.0,
    reason: str = _EN_REASON,
) -> dict[str, object]:
    return {
        "score": score,
        "reason": reason,
        "topics": ["product strategy", "experimentation"],
        "should_summarize": True,
        "dimensions": {"product": 9.0, "practicality": 8.0},
    }


def _raw_response(
    inner: dict[str, object] | str,
    *,
    extra: dict[str, object] | None = None,
) -> str:
    inner_text = (
        inner
        if isinstance(inner, str)
        else json.dumps(inner, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    payload: dict[str, object] = {
        "model": _MODEL,
        "response": inner_text,
        "done": True,
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _identity(scoring_input: ScoringInput) -> object:
    return build_scoring_request_identity(
        scoring_input=scoring_input,
        model=_MODEL,
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
    )


def _build_attempt(
    *,
    scoring_input: ScoringInput,
    raw: str,
    candidate: object | None = None,
) -> PrimaryScoringAttempt:
    return build_primary_scoring_attempt(
        scoring_input=scoring_input,
        candidate=candidate if candidate is not None else parse_scoring_candidate(raw),
        final_raw_response=raw,
        provider="ollama",
        model=_MODEL,
        model_digest=_DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
    )


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def read(self, size: int = -1) -> bytes:
        if not isinstance(self._payload, bytes):
            return json.dumps(self._payload).encode("utf-8")
        return self._payload

    def close(self) -> None:
        pass


class _FakeTransport:
    def __init__(self, responses: list[object]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, str]] = []

    def __call__(self, request: object, timeout: float) -> _Response:
        method = getattr(request, "method")
        url = getattr(request, "full_url")
        self.requests.append((method, url))
        response = self._responses.pop(0)
        if isinstance(response, _Response):
            return response
        return _Response(response)


def _tags() -> dict[str, object]:
    return {"models": [{"name": _MODEL, "digest": "a" * 64}]}


def _generate(inner: dict[str, object]) -> dict[str, str]:
    return {
        "response": json.dumps(
            inner, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    }


def _judge_pass() -> dict[str, object]:
    return {
        "status": "PASS",
        "decision_confidence": "HIGH",
        "grounding_confidence": "MEDIUM",
        "usefulness_confidence": "MEDIUM",
        "signals": ["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
        "reason": None,
        "evidence_ids": ["title-1"],
    }


def _write_project(project: Path) -> None:
    (project / "config").mkdir(parents=True)
    (project / "vault").mkdir()
    (project / "config" / "channels.yaml").write_text(
        "channels:\n  - channel_id: UCtest000000000000000000000000000\n",
        encoding="utf-8",
    )
    (project / "config" / "settings.yaml").write_text(
        f"""\
general:
  transcript_languages: [en]
  output_language: en
local_scoring:
  model: qwen3:8b
  expected_model_digest: sha256:{"a" * 64}
  temperature: 0.0
  max_output_tokens: 1200
  max_transcript_chars: 64
  max_description_chars: 32
cloud:
  enabled: false
storage:
  data_dir: data
  logs_dir: logs
  templates_dir: templates
  vault_root: {project / "vault"}
  vault_subdir: YouTube Intel
""",
        encoding="utf-8",
    )


def _runtime(project: Path) -> RuntimeOperations:
    _write_project(project)
    config = load_app_config(
        channels_path=project / "config" / "channels.yaml",
        settings_path=project / "config" / "settings.yaml",
    )
    return RuntimeOperations(
        config=config,
        project_root=project,
        dependencies=RuntimeDependencies(
            discovery_source=object(),  # type: ignore[arg-type]
            metadata_provider=object(),  # type: ignore[arg-type]
            subtitle_adapter_factory=lambda: object(),  # type: ignore[arg-type]
            scoring_provider_factory=lambda: object(),  # type: ignore[arg-type]
            analysis_provider_factory=lambda: object(),  # type: ignore[arg-type]
        ),
    )


def _judge_runtime(project: Path) -> tuple[RuntimeOperations, _FakeTransport]:
    _write_project(project)
    config = load_app_config(
        channels_path=project / "config" / "channels.yaml",
        settings_path=project / "config" / "settings.yaml",
    )
    transport = _FakeTransport([_tags(), _generate(_judge_pass())])
    return (
        RuntimeOperations(
            config=config,
            project_root=project,
            dependencies=RuntimeDependencies(
                discovery_source=object(),  # type: ignore[arg-type]
                metadata_provider=object(),  # type: ignore[arg-type]
                subtitle_adapter_factory=lambda: object(),  # type: ignore[arg-type]
                scoring_provider_factory=lambda: object(),  # type: ignore[arg-type]
                analysis_provider_factory=lambda: object(),  # type: ignore[arg-type]
                quality_judge_provider_factory=lambda: OllamaQualityJudgeProvider(
                    settings=config.settings.local_scoring,
                    transport=transport,
                ),
            ),
        ),
        transport,
    )


# ---------------------------------------------------------------------------
# Phase G ingress: F->G enriched aggregate continuation
# ---------------------------------------------------------------------------


def test_runtime_returns_enriched_phase_f_success_aggregate(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)

    success = runtime.run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input
    )

    assert type(success) is PhaseFTrustedScoringSuccess
    assert type(success.trusted_result) is TrustedScoreResult
    assert type(success.primary_attempt) is PrimaryScoringAttempt
    assert success.canonical_scoring_input_bytes is not None
    assert success.canonical_quality_input_bytes is not None
    assert success.canonical_quality_result_bytes is not None
    assert success.canonical_quality_operation_bytes is not None
    assert success.canonical_attestation_bytes is not None
    assert success.canonical_structured_result_bytes is not None
    assert (
        hashlib.sha256(success.canonical_scoring_input_bytes).hexdigest()
        == success.canonical_scoring_input_hash
    )
    assert (
        hashlib.sha256(success.canonical_structured_result_bytes).hexdigest()
        == success.canonical_structured_result_hash
    )
    expected_input_hash = _identity(scoring_input).request_hash
    assert success.scoring_request_hash == expected_input_hash
    candidate_hash = build_scoring_candidate_hash(success.primary_attempt.candidate)
    assert success.candidate_hash == candidate_hash


# ---------------------------------------------------------------------------
# PREWRITE_VALIDATE: zero-write plan creation
# ---------------------------------------------------------------------------


def test_prewrite_validate_creates_plan_without_side_effects(tmp_path: Path) -> None:

    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)
    success = runtime.run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input
    )

    data_root = tmp_path / "project" / "data"
    before_files = set(data_root.rglob("*")) if data_root.exists() else set()
    before_artifacts = runtime._repository.get_artifact_by_key(
        f"scoring/{success.scoring_request_hash}/raw"
    )

    committer = runtime._trusted_scoring_committer(
        job_id="job-phase-g-1",
        owner="test-owner",
        pipeline_version="runtime-v1",
    )
    plan = committer.prewrite_validate(success)

    assert plan is not None
    assert type(plan).__name__ == "ValidatedScoringWritePlan"
    after_files = set(data_root.rglob("*")) if data_root.exists() else set()
    assert after_files == before_files
    after_artifacts = runtime._repository.get_artifact_by_key(
        f"scoring/{success.scoring_request_hash}/raw"
    )
    assert after_artifacts == before_artifacts


# ---------------------------------------------------------------------------
# Phase G helpers for filesystem + SQLite registration tests
# ---------------------------------------------------------------------------


_NOW = datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC)


def _transcript_content() -> str:
    return "This transcript contains enough text for a stable sample."


def _transcript_artifact(video_id: str, job_id: str) -> ArtifactWrite:
    content = _transcript_content().encode("utf-8")
    content_hash = hashlib.sha256(content).hexdigest()
    return ArtifactWrite(
        artifact_id=f"transcript-{video_id}",
        artifact_key=f"video:{video_id}:transcript:canonical",
        video_id=video_id,
        job_id=job_id,
        kind=ArtifactKind.TRANSCRIPT_CANONICAL,
        storage_root=StorageRoot.DATA,
        relative_path=f"transcripts/{video_id}.txt",
        content_hash=content_hash,
        provider="subtitle",
        model=None,
        producer_version="transcript-v1",
        retention_class=RetentionClass.LONG_LIVED,
        expires_at=None,
    )


def _write_transcript_file(data_root: Path, artifact: ArtifactWrite) -> None:
    path = data_root / artifact.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_transcript_content().encode("utf-8"))


def _video_with_id(video_id: str) -> VideoMetadata:
    base = _video()
    return VideoMetadata(
        video_id=video_id,
        channel_id=f"channel-{video_id}",
        channel_name=base.channel_name,
        title=base.title,
        description=base.description,
        source_url=f"https://example.invalid/watch?v={video_id}",
        published_at=base.published_at,
        duration_seconds=base.duration_seconds,
        default_language=base.default_language,
        live_status=base.live_status,
        availability=base.availability,
    )


def _setup_transcript_ready_video(
    repository: SQLiteStateRepository,
    data_root: Path,
    *,
    video_id: str,
    pipeline_version: str = "runtime-v1",
) -> None:
    repository.upsert_video_metadata(
        _video_with_id(video_id),
        pipeline_version=pipeline_version,
        now=_NOW,
    )
    repository.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version=pipeline_version,
        now=_NOW,
    )
    transcript_job_id = f"job-transcript-{video_id}"
    repository.create_job(
        job_id=transcript_job_id,
        scope_key=f"video:{video_id}:TRANSCRIPT",
        video_id=video_id,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.TRANSCRIPT,
        pipeline_version=pipeline_version,
        max_attempts=3,
        available_at=_NOW,
        now=_NOW,
    )
    repository.claim_next_job(
        owner="transcript-worker",
        lease_until=_NOW + timedelta(minutes=10),
        now=_NOW,
        video_id=video_id,
    )
    artifact = _transcript_artifact(video_id, transcript_job_id)
    _write_transcript_file(data_root, artifact)
    repository.complete_stage(
        job_id=transcript_job_id,
        owner="transcript-worker",
        video_id=video_id,
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version=pipeline_version,
        artifacts=(artifact,),
        provider_call=None,
        now=_NOW,
    )


def _setup_scoring_job(
    repository: SQLiteStateRepository,
    *,
    video_id: str,
    job_id: str,
    pipeline_version: str = "runtime-v1",
    claim: bool = True,
) -> None:
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:{video_id}:SCORING",
        video_id=video_id,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version=pipeline_version,
        max_attempts=3,
        available_at=_NOW,
        now=_NOW,
    )
    if claim:
        # Use a real future lease so the committer's real-time clock sees a valid lease.
        repository.claim_next_job(
            owner="test-owner",
            lease_until=datetime.now(UTC) + timedelta(minutes=10),
            now=_NOW,
            video_id=video_id,
        )


def _committer_and_plan(
    runtime: RuntimeOperations,
    *,
    job_id: str,
    video_id: str,
    owner: str = "test-owner",
    pipeline_version: str = "runtime-v1",
) -> tuple[TrustedScoringPersistenceCommitter, object]:
    scoring_input = _scoring_input(video_id=video_id)
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)
    success = runtime.run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input
    )
    committer = runtime._trusted_scoring_committer(
        job_id=job_id,
        owner=owner,
        pipeline_version=pipeline_version,
    )
    plan = committer.prewrite_validate(success)
    return committer, plan


# ---------------------------------------------------------------------------
# COMMIT: filesystem ordering and durability
# ---------------------------------------------------------------------------


def test_commit_writes_raw_and_structured_files(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-commit-files"
    job_id = "job-commit-files"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )

    result = committer.commit(plan)

    assert isinstance(result, StageCompletionResult)
    raw_path = runtime._data_root / plan.raw_artifact.relative_path
    structured_path = runtime._data_root / plan.structured_artifact.relative_path
    assert raw_path.exists()
    assert structured_path.exists()
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == plan.raw_envelope_hash
    assert (
        hashlib.sha256(structured_path.read_bytes()).hexdigest()
        == plan.structured_hash
    )
    assert not (raw_path.with_name(raw_path.name + ".tmp")).exists()
    assert not (structured_path.with_name(structured_path.name + ".tmp")).exists()


def test_commit_raises_when_final_file_already_exists(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-commit-exists"
    job_id = "job-commit-exists"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )
    raw_path = runtime._data_root / plan.raw_artifact.relative_path
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(b"stale final artifact")

    with pytest.raises(ScoringPersistenceError, match="partial artifact state"):
        committer.commit(plan)


def test_commit_raises_when_temporary_file_already_exists(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-commit-tmp-exists"
    job_id = "job-commit-tmp-exists"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )
    raw_path = runtime._data_root / plan.raw_artifact.relative_path
    tmp_path = raw_path.with_name(raw_path.name + ".tmp")
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_bytes(b"stale temporary artifact")

    with pytest.raises(ScoringPersistenceError, match="stale temporary"):
        committer.commit(plan)


# ---------------------------------------------------------------------------
# ATOMIC REGISTER: single SQLite transaction
# ---------------------------------------------------------------------------


def test_atomic_register_scoring_success_commits_all_rows(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-atomic"
    job_id = "job-atomic"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )
    committer.commit(plan)

    raw_record = runtime._repository.get_artifact_by_key(plan.raw_artifact.artifact_key)
    structured_record = runtime._repository.get_artifact_by_key(
        plan.structured_artifact.artifact_key
    )
    assert raw_record is not None
    assert structured_record is not None
    assert raw_record.content_hash == plan.raw_envelope_hash
    assert structured_record.content_hash == plan.structured_hash

    scoring_call = runtime._repository.get_provider_call(
        plan.scoring_call_request.request_hash
    )
    judge_call = runtime._repository.get_provider_call(
        plan.judge_call_request.request_hash
    )
    assert scoring_call is not None
    assert judge_call is not None
    assert scoring_call.status is ProviderCallStatus.SUCCEEDED
    assert judge_call.status is ProviderCallStatus.SUCCEEDED
    assert scoring_call.response_artifact_id == raw_record.artifact_id
    assert judge_call.response_artifact_id == raw_record.artifact_id

    video = runtime._repository.get_video(video_id)
    assert video is not None
    assert video.pipeline_status is PipelineStatus.SCORED
    assert video.score == plan.scoring_summary.score
    assert video.should_summarize == plan.scoring_summary.should_summarize

    job = runtime._repository.get_job(job_id)
    assert job is not None
    assert job.status is JobStatus.SUCCEEDED


def test_atomic_register_is_idempotent_for_filesystem_then_sqlite_retry(
    tmp_path: Path,
) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-idempotent"
    job_id = "job-idempotent"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )

    # First call writes files and commits SQLite.
    first = committer.commit(plan)
    # Second call with the same plan must be idempotent — the complete
    # committed graph matches, so it returns the existing result without
    # rewriting files or creating duplicate DB rows.
    second = committer.commit(plan)
    assert second.job.job_id == first.job.job_id

    # The SQLite state remains the same.
    video = runtime._repository.get_video(video_id)
    assert video is not None
    assert video.pipeline_status is PipelineStatus.SCORED
    job = runtime._repository.get_job(job_id)
    assert job is not None
    assert job.status is JobStatus.SUCCEEDED
    assert first.job.job_id == job_id


def test_atomic_register_fails_on_wrong_job_owner(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-wrong-owner"
    job_id = "job-wrong-owner"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="wrong-owner"
    )

    with pytest.raises(ScoringPersistenceError, match="job lease is not owned"):
        committer.commit(plan)


def test_atomic_register_fails_on_wrong_pipeline_status(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-wrong-status"
    job_id = "job-wrong-status"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    # Move video out of TRANSCRIPT_READY without finishing the job.
    runtime._repository.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.TRANSCRIPT_READY,
        target_status=PipelineStatus.SCORED,
        pipeline_version="runtime-v1",
        now=_NOW,
    )
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )

    with pytest.raises(
        ScoringPersistenceError, match="pipeline changed before atomic scoring registration"
    ):
        committer.commit(plan)


def test_load_scoring_rejects_corrupted_structured_artifact(
    tmp_path: Path,
) -> None:
    """M7: runtime content/hash binding rejects a corrupted artifact file."""

    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-corrupt-structured"
    job_id = "job-corrupt-structured"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )
    committer.commit(plan)

    structured_path = runtime._data_root / plan.structured_artifact.relative_path
    structured_path.write_bytes(b"corrupted structured content")

    with pytest.raises(ValueError, match="persisted artifact hash is invalid"):
        runtime._load_scoring(video_id)


# ---------------------------------------------------------------------------
# Runtime scoring-stage cutover and legacy isolation
# ---------------------------------------------------------------------------


class _FakeScoringProvider:
    """Returns a deterministic PRIMARY attempt without any network call."""

    def __init__(self, attempt: PrimaryScoringAttempt) -> None:
        self._attempt = attempt
        self.calls: list[ScoringInput] = []

    def primary_attempt(self, scoring_input: ScoringInput) -> PrimaryScoringAttempt:
        self.calls.append(scoring_input)
        return self._attempt


def test_scoring_stage_uses_trusted_route(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    orchestrator = runtime._orchestrator()
    handler = orchestrator.handlers[ProcessingStage.SCORING]
    code = handler.__code__
    names = set(code.co_names)
    # The trusted route must reference the new Phase F->G building blocks.
    assert "build_scoring_input" in names
    assert "run_primary_trusted_scoring" in names
    assert "_trusted_scoring_committer" in names
    # The legacy repository-backed service must not be the normal path.
    assert "RepositoryBackedScoringService" not in names


def test_repository_backed_scoring_service_remains_available_but_not_used(
    tmp_path: Path,
) -> None:
    from youtube_intel.scoring import RepositoryBackedScoringService

    runtime, _ = _judge_runtime(tmp_path / "project")
    # The class must still be importable and instantiable as a compatibility
    # boundary, even though the normal runtime scoring_stage no longer calls it.
    service = RepositoryBackedScoringService(
        provider=object(),  # type: ignore[arg-type]
        settings=runtime._config.settings.local_scoring,
        summary_threshold=runtime._config.settings.thresholds.summary_score,
        repository=runtime._repository,
        context=ScoringJobContext("legacy-compat-job", "legacy-owner", "runtime-v1"),
        artifact_root=runtime._data_root,
        clock=lambda: _NOW,
    )
    assert service is not None


# ---------------------------------------------------------------------------
# PREWRITE_VALIDATE M1-M10 mutation proof
# ---------------------------------------------------------------------------


def _unenriched_success(tmp_path: Path) -> tuple[RuntimeOperations, PhaseFTrustedScoringSuccess]:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)
    success = runtime.run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input
    )
    # Re-mint without enrichment to simulate a pre-Phase-G aggregate.
    unenriched = _mint_phase_f_trusted_scoring_success(
        trusted_result=success.trusted_result,
        primary_attempt=success.primary_attempt,
        enriched_evidence=None,
    )
    return runtime, unenriched


def test_prewrite_validate_rejects_non_aggregate(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    committer = runtime._trusted_scoring_committer(
        job_id="job-m1", owner="test-owner", pipeline_version="runtime-v1"
    )
    with pytest.raises(ValueError, match="PhaseFTrustedScoringSuccess"):
        committer.prewrite_validate(object())  # type: ignore[arg-type]


def test_prewrite_validate_rejects_unenriched_aggregate(tmp_path: Path) -> None:
    runtime, unenriched = _unenriched_success(tmp_path / "project")
    committer = runtime._trusted_scoring_committer(
        job_id="job-m2", owner="test-owner", pipeline_version="runtime-v1"
    )
    with pytest.raises(ValueError, match="missing the required Phase G quality evidence"):
        committer.prewrite_validate(unenriched)


def test_prewrite_validate_rejects_canonical_hash_mismatch(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)
    success = runtime.run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input
    )
    evidence = success._enriched_evidence  # type: ignore[attr-defined]
    mutated = _EnrichedQualityEvidence(
        canonical_scoring_input_bytes=evidence.canonical_scoring_input_bytes,
        canonical_scoring_input_hash="a" * 64,
        canonical_quality_input_bytes=evidence.canonical_quality_input_bytes,
        canonical_quality_input_hash=evidence.canonical_quality_input_hash,
        canonical_quality_result_bytes=evidence.canonical_quality_result_bytes,
        canonical_quality_result_hash=evidence.canonical_quality_result_hash,
        canonical_quality_operation_bytes=evidence.canonical_quality_operation_bytes,
        canonical_quality_operation_hash=evidence.canonical_quality_operation_hash,
        canonical_attestation_bytes=evidence.canonical_attestation_bytes,
        canonical_attestation_hash=evidence.canonical_attestation_hash,
        canonical_structured_result_bytes=evidence.canonical_structured_result_bytes,
        canonical_structured_result_hash=evidence.canonical_structured_result_hash,
    )
    mutated_success = _mint_phase_f_trusted_scoring_success(
        trusted_result=success.trusted_result,
        primary_attempt=success.primary_attempt,
        enriched_evidence=mutated,
    )
    committer = runtime._trusted_scoring_committer(
        job_id="job-m3", owner="test-owner", pipeline_version="runtime-v1"
    )
    with pytest.raises(ValueError, match="scoring_input"):
        committer.prewrite_validate(mutated_success)


def test_prewrite_validate_rejects_raw_response_hash_mutation(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)
    success = runtime.run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input
    )
    # Tamper with the primary attempt's raw response hash after minting.
    forged_attempt = PrimaryScoringAttempt(
        candidate=attempt.candidate,
        candidate_hash=attempt.candidate_hash,
        final_raw_response=attempt.final_raw_response,
        raw_response_hash="b" * 64,
        scoring_request_hash=attempt.scoring_request_hash,
        scoring_input_normalized_hash=attempt.scoring_input_normalized_hash,
        provider=attempt.provider,
        model=attempt.model,
        model_digest=attempt.model_digest,
        attempt_role=attempt.attempt_role,
    )
    object.__setattr__(success, "_primary_attempt", forged_attempt)
    committer = runtime._trusted_scoring_committer(
        job_id="job-m4", owner="test-owner", pipeline_version="runtime-v1"
    )
    with pytest.raises(ValueError, match="raw response hash"):
        committer.prewrite_validate(success)


def test_prewrite_validate_rejects_raw_reparse_mutation(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)
    success = runtime.run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input
    )
    # Forge a raw response that parses to a different candidate but keep hashes
    # self-consistent so the failure must come from the canonical reparse guard.
    forged_inner = dict(_candidate_fields())
    forged_inner["reason"] = "forged reparse reason"
    forged_raw = _raw_response(forged_inner)
    forged_raw_hash = hashlib.sha256(forged_raw.encode("utf-8")).hexdigest()
    forged_attempt = PrimaryScoringAttempt(
        candidate=attempt.candidate,
        candidate_hash=attempt.candidate_hash,
        final_raw_response=forged_raw,
        raw_response_hash=forged_raw_hash,
        scoring_request_hash=attempt.scoring_request_hash,
        scoring_input_normalized_hash=attempt.scoring_input_normalized_hash,
        provider=attempt.provider,
        model=attempt.model,
        model_digest=attempt.model_digest,
        attempt_role=attempt.attempt_role,
    )
    object.__setattr__(success, "_primary_attempt", forged_attempt)
    object.__setattr__(success, "_raw_response_hash", forged_raw_hash)
    committer = runtime._trusted_scoring_committer(
        job_id="job-m5", owner="test-owner", pipeline_version="runtime-v1"
    )
    with pytest.raises(ValueError, match="candidate does not match"):
        committer.prewrite_validate(success)


def test_prewrite_validate_rejects_candidate_result_binding_mutation(
    tmp_path: Path,
) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)
    success = runtime.run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input
    )
    # Forge a trusted result whose business fields disagree with the candidate.
    forged_result = ScoreResult.model_validate(
        {
            **success.trusted_result.result.model_dump(mode="json"),
            "score": 1.0,
        }
    )
    forged_trusted = TrustedScoreResult(
        sentinel=_TRUSTED_SCORE_RESULT_SENTINEL,
        result=forged_result,
    )
    object.__setattr__(success, "_trusted_result", forged_trusted)
    committer = runtime._trusted_scoring_committer(
        job_id="job-m6", owner="test-owner", pipeline_version="runtime-v1"
    )
    with pytest.raises(ValueError, match="business fields mismatch"):
        committer.prewrite_validate(success)


def test_prewrite_validate_rejects_runtime_authority_rotation(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)
    success = runtime.run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input
    )
    # Rotate the attempt provider so it no longer matches the runtime context.
    forged_attempt = PrimaryScoringAttempt(
        candidate=attempt.candidate,
        candidate_hash=attempt.candidate_hash,
        final_raw_response=attempt.final_raw_response,
        raw_response_hash=attempt.raw_response_hash,
        scoring_request_hash=attempt.scoring_request_hash,
        scoring_input_normalized_hash=attempt.scoring_input_normalized_hash,
        provider="forged-provider",
        model=attempt.model,
        model_digest=attempt.model_digest,
        attempt_role=attempt.attempt_role,
    )
    object.__setattr__(success, "_primary_attempt", forged_attempt)
    committer = runtime._trusted_scoring_committer(
        job_id="job-m7", owner="test-owner", pipeline_version="runtime-v1"
    )
    with pytest.raises(ValueError, match="attempt provider mismatches"):
        committer.prewrite_validate(success)


def test_prewrite_validate_rejects_provider_call_request_binding_mutation(
    tmp_path: Path,
) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)
    success = runtime.run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input
    )
    committer = runtime._trusted_scoring_committer(
        job_id="job-m8", owner="test-owner", pipeline_version="runtime-v1"
    )
    # Rotate only the committer's runtime scoring operation. The canonical
    # identity is rebuilt from the global constant, so the scoring ProviderCall
    # request_hash binding must fail.
    context = committer._scoring_context
    forged_context = _mint_trusted_scoring_context(
        sentinel=_TRUSTED_SCORING_CONTEXT_SENTINEL,
        scoring_provider=context.scoring_provider,
        scoring_model=context.scoring_model,
        scoring_model_digest=context.scoring_model_digest,
        output_language=context.output_language,
        scoring_schema_version=context.scoring_schema_version,
        scoring_prompt_version=context.scoring_prompt_version,
        scoring_operation="mutated-local-scoring",
        temperature=context.temperature,
        max_output_tokens=context.max_output_tokens,
        max_description_chars=context.max_description_chars,
    )
    object.__setattr__(committer, "_scoring_context", forged_context)
    with pytest.raises(ValueError, match="scoring ProviderCall request_hash"):
        committer.prewrite_validate(success)


def test_scoring_stage_rejects_bare_score_result_reentry(tmp_path: Path) -> None:
    """M9: a bare ScoreResult cannot be passed as a trusted attempt."""

    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    # A bare ScoreResult is the legacy/external boundary; it is not a
    # PrimaryScoringAttempt and must fail-closed at the trusted seam.
    bare_result = ScoreResult(
        schema_version="score-result-v2",
        score=8.0,
        reason="This response explains a concrete product strategy.",
        topics=("product",),
        should_summarize=True,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="scoring-prompt-v2",
        request_hash=scoring_input.request_hash,
        output_language=scoring_input.output_language,
    )
    with pytest.raises(
        ValueError, match="trusted scoring requires an exact PrimaryScoringAttempt"
    ):
        runtime.run_primary_trusted_scoring(
            attempt=bare_result,  # type: ignore[arg-type]
            scoring_input=scoring_input,
        )


# ===========================================================================
# Phase G Correction Round 1 — RED tests (must fail on current code)
# ===========================================================================


# --- R1: Atomic no-clobber promote -----------------------------------------


def test_r1_promote_does_not_overwrite_existing_final(tmp_path: Path) -> None:
    """R1: promote must atomically refuse to overwrite an existing final.

    Current code uses exists()+os.rename which is a TOCTOU race and
    POSIX rename can silently overwrite.  This test places a sentinel file
    at the final path and verifies its bytes survive the failed promote.
    """

    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-r1-overwrite"
    job_id = "job-r1-overwrite"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(runtime._repository, video_id=video_id, job_id=job_id)
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )
    raw_final = runtime._data_root / plan.raw_artifact.relative_path
    raw_final.parent.mkdir(parents=True, exist_ok=True)
    sentinel = b"pre-existing sentinel content"
    raw_final.write_bytes(sentinel)

    with pytest.raises(ScoringPersistenceError):
        committer.commit(plan)

    # The sentinel must be unchanged — overwrite-capable rename would
    # have replaced it.
    assert raw_final.read_bytes() == sentinel


def test_r1_promote_uses_atomic_link_not_rename(tmp_path: Path) -> None:
    """R1: the promote mechanism must be link-based (atomic no-replace),
    not rename-based (overwrite-capable).

    We inspect the source to confirm os.link is used for promotion.
    """

    import inspect

    source = inspect.getsource(TrustedScoringPersistenceCommitter._write_atomic_file)
    assert "os.link" in source, "promote must use os.link for atomic no-clobber"
    # os.rename must NOT appear as the promote primitive call.  We check
    # for the call pattern, not mentions in docstrings/comments.
    import re

    rename_calls = re.findall(r"^\s*os\.rename\(", source, re.MULTILINE)
    assert not rename_calls, "promote must not use overwrite-capable os.rename"


# --- R2: Strict same-plan idempotency --------------------------------------


def test_r2_same_plan_after_commit_is_idempotent(tmp_path: Path) -> None:
    """R2: committing the exact same plan twice must return the existing
    committed result, not fail with 'already exists'.

    Current code rejects the second commit because final files exist,
    but the amendment requires deterministic idempotency when the full
    committed graph matches.
    """

    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-r2-idempotent"
    job_id = "job-r2-idempotent"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(runtime._repository, video_id=video_id, job_id=job_id)
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )

    first = committer.commit(plan)
    # Second commit of the SAME plan must be idempotent.
    second = committer.commit(plan)

    assert second.job.job_id == first.job.job_id
    assert second.video.video_id == first.video.video_id
    assert second.video.score == first.video.score
    assert len(second.artifacts) == len(first.artifacts)
    assert len(second.artifacts) == 2


def test_r2_same_plan_with_raw_file_corrupt_rejects(tmp_path: Path) -> None:
    """R2: if final files exist but bytes don't match the plan, reject."""

    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-r2-corrupt"
    job_id = "job-r2-corrupt"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(runtime._repository, video_id=video_id, job_id=job_id)
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )
    committer.commit(plan)
    raw_final = runtime._data_root / plan.raw_artifact.relative_path
    raw_final.write_bytes(b"tampered raw content")

    with pytest.raises(ScoringPersistenceError):
        committer.commit(plan)


def test_r2_same_plan_with_partial_db_graph_rejects(tmp_path: Path) -> None:
    """R2: if DB graph is partial (only one ProviderCall SUCCEEDED), reject."""

    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-r2-partial"
    job_id = "job-r2-partial"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(runtime._repository, video_id=video_id, job_id=job_id)
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )
    committer.commit(plan)
    # Delete the Judge ProviderCall to simulate a partial graph.
    runtime._repository._connect().execute(
        "DELETE FROM provider_calls WHERE request_hash = :rh",
        {"rh": plan.judge_call_request.request_hash},
    ).close()

    with pytest.raises(ScoringPersistenceError):
        committer.commit(plan)


def test_r2_idempotent_retry_does_not_rewrite_files(tmp_path: Path) -> None:
    """R2: idempotent retry must not touch the final files."""

    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-r2-no-rewrite"
    job_id = "job-r2-no-rewrite"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(runtime._repository, video_id=video_id, job_id=job_id)
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )
    committer.commit(plan)
    raw_final = runtime._data_root / plan.raw_artifact.relative_path
    structured_final = runtime._data_root / plan.structured_artifact.relative_path
    raw_mtime_before = raw_final.stat().st_mtime_ns
    structured_mtime_before = structured_final.stat().st_mtime_ns

    committer.commit(plan)

    assert raw_final.stat().st_mtime_ns == raw_mtime_before
    assert structured_final.stat().st_mtime_ns == structured_mtime_before


# --- R3: Direct repository PREWRITE bypass ---------------------------------


def test_r3_direct_repository_call_with_ordinary_dtos_rejects(
    tmp_path: Path,
) -> None:
    """R3: calling the repository registration directly with ordinary
    ArtifactWrite/ProviderCall DTOs and nonexistent files must reject.

    Current code exposes atomic_register_scoring_success as a public
    method that accepts plain DTOs — this is a PREWRITE bypass.
    """

    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-r3-bypass"
    job_id = "job-r3-bypass"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(runtime._repository, video_id=video_id, job_id=job_id)

    # The public method must not be callable by ordinary callers.
    assert not hasattr(
        runtime._repository, "atomic_register_scoring_success"
    ), "atomic_register_scoring_success must be private to close PREWRITE bypass"


def test_r3_ordinary_capability_substitute_rejects(tmp_path: Path) -> None:
    """R3: an ordinary caller-created substitute for the internal
    registration capability must be rejected.
    """

    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-r3-capability"
    job_id = "job-r3-capability"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(runtime._repository, video_id=video_id, job_id=job_id)
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )

    # Attempt to call the internal registrar with a forged capability.

    repo: SQLiteStateRepository = runtime._repository
    # If the registrar requires a sentinel-bound capability, a plain
    # call must fail with a type/guard error (not AttributeError from
    # blindly accessing attributes of an arbitrary object).
    with pytest.raises((TypeError, ValueError)):
        repo._atomic_register_scoring_success(
            registration=object(),  # type: ignore[arg-type]
            now=datetime.now(UTC),
        )


# --- R4: SQLite-after-promote failure semantics ----------------------------


def test_r4_sqlite_failure_leaves_promoted_finals(tmp_path: Path) -> None:
    """R4: if SQLite fails after files are promoted, the promoted finals
    must remain (orphan state for Phase H), and no fake success.
    """

    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-r4-sqlite-fail"
    job_id = "job-r4-sqlite-fail"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(runtime._repository, video_id=video_id, job_id=job_id)
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )

    def fail_after_promote(point: str) -> None:
        if point == "atomic_register.after_artifacts":
            raise RuntimeError("injected SQLite failure after artifacts")

    runtime._repository._inject_failure = fail_after_promote  # type: ignore[method-assign]

    with pytest.raises(ScoringPersistenceError):
        committer.commit(plan)

    # Promoted finals must still exist — no cleanup/retry.
    raw_final = runtime._data_root / plan.raw_artifact.relative_path
    structured_final = runtime._data_root / plan.structured_artifact.relative_path
    assert raw_final.exists(), "promoted raw final must remain as orphan"
    assert structured_final.exists(), "promoted structured final must remain as orphan"
    # No fake success: video must NOT be SCORED.
    video = runtime._repository.get_video(video_id)
    assert video is not None
    assert video.pipeline_status is not PipelineStatus.SCORED


# --- R5: Failure injection (temp/fsync/promote/dir-fsync/final-verify) -----


def test_r5_temp_write_failure_no_sqlite_registration(tmp_path: Path) -> None:
    """R5: temp write failure must leave no SQLite registration."""

    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-r5-temp-fail"
    job_id = "job-r5-temp-fail"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(runtime._repository, video_id=video_id, job_id=job_id)
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )

    original_write = committer._write_atomic_file

    def failing_write(*, final_path, content, expected_hash, video_id):
        raise ScoringPersistenceError(
            __import__("youtube_intel.domain", fromlist=["AppError", "ErrorCode", "ProcessingStage"]).AppError(
                code=__import__("youtube_intel.domain", fromlist=["ErrorCode"]).ErrorCode.LOCAL_RESOURCE,
                message="injected temp write failure",
                retryable=False,
                video_id=video_id,
                stage=ProcessingStage.SCORING,
            )
        )

    committer._write_atomic_file = failing_write  # type: ignore[method-assign]
    with pytest.raises(ScoringPersistenceError):
        committer.commit(plan)

    # Restore and verify no DB success.
    committer._write_atomic_file = original_write  # type: ignore[method-assign]
    video = runtime._repository.get_video(video_id)
    assert video is not None
    assert video.pipeline_status is not PipelineStatus.SCORED


def test_r5_sqlite_transaction_rollback_no_partial_graph(
    tmp_path: Path,
) -> None:
    """R5: SQLite transaction rollback must leave no partial
    Artifact/ProviderCall/stage graph.
    """

    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-r5-rollback"
    job_id = "job-r5-rollback"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(runtime._repository, video_id=video_id, job_id=job_id)
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )

    def fail_before_job_finish(point: str) -> None:
        if point == "atomic_register.after_pipeline":
            raise RuntimeError("injected failure before job finish")

    runtime._repository._inject_failure = fail_before_job_finish  # type: ignore[method-assign]

    with pytest.raises(ScoringPersistenceError):
        committer.commit(plan)

    # No partial graph: no Artifact rows, no ProviderCall rows.
    raw_record = runtime._repository.get_artifact_by_key(plan.raw_artifact.artifact_key)
    assert raw_record is None, "raw Artifact must not exist after rollback"
    scoring_call = runtime._repository.get_provider_call(
        plan.scoring_call_request.request_hash
    )
    assert scoring_call is None, "ProviderCall must not exist after rollback"


# ---------------------------------------------------------------------------
# Phase G Correction Round 1 — M14 targeted final-file verification
# ---------------------------------------------------------------------------


def test_m14_registration_rejects_missing_final_files(tmp_path: Path) -> None:
    """M14: the DB registrar must verify promoted finals exist and match
    the plan hashes before registering any Artifact rows.

    Without this verification, a forged or prematurely minted registration
    capability could write a DB graph that claims files which were never
    promoted.
    """

    from youtube_intel.state import _mint_scoring_registration_capability

    runtime, _ = _judge_runtime(tmp_path / "project")
    video_id = "video-m14-missing-finals"
    job_id = "job-m14-missing-finals"
    _setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    _setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    committer, plan = _committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )

    # Mint a valid registration capability, but do not write the files.
    registration = _mint_scoring_registration_capability(
        job_id=committer._context.job_id,
        owner=committer._context.owner,
        video_id=plan.video_id,
        pipeline_version=committer._context.pipeline_version,
        raw_artifact=plan.raw_artifact,
        structured_artifact=plan.structured_artifact,
        scoring_call_request=plan.scoring_call_request,
        judge_call_request=plan.judge_call_request,
        scoring_call_completion=plan.scoring_call_completion,
        judge_call_completion=plan.judge_call_completion,
        scoring_summary=plan.scoring_summary,
        raw_final_path=runtime._data_root / plan.raw_artifact.relative_path,
        structured_final_path=runtime._data_root
        / plan.structured_artifact.relative_path,
        raw_envelope_hash=plan.raw_envelope_hash,
        structured_hash=plan.structured_hash,
    )

    with pytest.raises(
        (IntegrityConflict, ScoringPersistenceError),
        match="final file does not exist|raw final file",
    ):
        runtime._repository._atomic_register_scoring_success(
            registration=registration,
            now=datetime.now(UTC),
        )
