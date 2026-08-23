"""H1-A runtime admission tests for trusted scoring dispatches."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    Availability,
    DiscoveryBatch,
    DiscoveryCursor,
    JobStatus,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    QualityJudgeOperationInput,
    VideoMetadata,
)
from youtube_intel.jobs import PipelineJobPlanner
from youtube_intel.pipeline import PipelineOrchestrator
from youtube_intel.retry import RetryPolicy
from youtube_intel.runtime import RuntimeOperations
from youtube_intel.scoring import build_scoring_input
from youtube_intel.scoring_admission import (
    ScoringDispatchAdmission,
    ScoringDispatchDenied,
    ScoringDispatchIdentity,
    ScoringDispatchRole,
    UnknownProviderState,
    build_judge_scoring_dispatch_identity,
    build_primary_scoring_dispatch_identity,
    build_repair_scoring_dispatch_identity,
)
from youtube_intel.state import (
    JobRecord,
    JobType,
    ProviderCallRecord,
    ProviderCallStatus,
    SQLiteStateRepository,
)

_NOW = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)


class _Repository:
    def __init__(self, *, owner: str = "runtime-a") -> None:
        self.job = _job(owner=owner)
        self.calls: dict[str, ProviderCallRecord] = {}

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.job if job_id == self.job.job_id else None

    def get_provider_call(self, request_hash: str) -> ProviderCallRecord | None:
        return self.calls.get(request_hash)


def _job(*, owner: str) -> JobRecord:
    return JobRecord(
        job_id="scoring-job",
        scope_key="video:video-1:SCORING",
        video_id="video-1",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="runtime-v1",
        status=JobStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        available_at=_NOW,
        lease_owner=owner,
        lease_until=_NOW + timedelta(minutes=5),
        last_error_code=None,
        last_error_message=None,
        created_at=_NOW,
        updated_at=_NOW,
        finished_at=None,
    )


def _identity(role: ScoringDispatchRole, suffix: str = "a") -> ScoringDispatchIdentity:
    return ScoringDispatchIdentity(
        role=role,
        operation="local-scoring-v1",
        normalized_input_hash=(suffix * 64)[:64],
        request_hash=(suffix * 64)[:64],
    )


def _gate(repository: _Repository, *, owner: str = "runtime-a") -> ScoringDispatchAdmission:
    return ScoringDispatchAdmission(repository=repository, job_id="scoring-job", owner=owner)


def _live_judge_gate(repository: _Repository) -> ScoringDispatchAdmission:
    repository.job = replace(
        repository.job, lease_until=datetime.now(UTC) + timedelta(minutes=5)
    )
    return _gate(repository)


def _provider_call(request_hash: str, status: ProviderCallStatus) -> ProviderCallRecord:
    return ProviderCallRecord(
        request_hash=request_hash,
        operation="local-scoring-v1",
        provider="ollama",
        model="qwen3:8b",
        prompt_version="scoring-prompt-v1",
        schema_version="scoring-result-v1",
        status=status,
        reservation_owner="other-runtime",
        lease_until=_NOW + timedelta(minutes=5),
        available_at=_NOW,
        attempt_count=1,
        response_artifact_id=None,
        input_tokens=None,
        output_tokens=None,
        cost_microusd=None,
        last_error_code=None,
        last_error_message=None,
        started_at=_NOW,
        finished_at=None,
        updated_at=_NOW,
    )


class _JudgeProvider:
    def __init__(self) -> None:
        self.calls: list[QualityJudgeOperationInput] = []

    def judge(
        self,
        operation_input: QualityJudgeOperationInput,
        *,
        content_input: object,
    ) -> object:
        del content_input
        self.calls.append(operation_input)
        return object()


def _judge_operation(role: str = "PRIMARY") -> QualityJudgeOperationInput:
    return QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": "1" * 64,
            "attempt_role": role,
            "candidate_hash": "2" * 64,
            "quality_input_hash": "3" * 64,
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v1",
            "schema_version": "content-quality-result-v1",
            "judge_provider": "ollama",
            "judge_model": "qwen3:8b",
            "judge_model_digest": "sha256:" + ("4" * 64),
        }
    )


def _judge_runtime() -> tuple[RuntimeOperations, _JudgeProvider]:
    runtime = object.__new__(RuntimeOperations)
    provider = _JudgeProvider()
    runtime._quality_judge_provider = provider
    return runtime, provider


def _primary_scoring_input() -> object:
    return build_scoring_input(
        video=VideoMetadata(
            video_id="video-1",
            channel_id="channel-1",
            channel_name="Channel",
            title="A scoring title",
            description="A scoring description.",
            source_url="https://example.invalid/video-1",
            published_at=_NOW,
            duration_seconds=60,
            live_status="none",
            availability=Availability.PUBLIC,
        ),
        transcript_text="A stable transcript sample for identity testing.",
        language="en",
        output_language="en",
        settings=LocalScoringSettings(
            model="qwen3:8b",
            expected_model_digest="sha256:" + ("4" * 64),
            temperature=0.0,
            max_output_tokens=1200,
            max_transcript_chars=64,
            max_description_chars=32,
        ),
    )


def _primary_context() -> object:
    return SimpleNamespace(
        scoring_model="qwen3:8b",
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
        scoring_operation="local-scoring-v1",
    )


def test_duplicate_primary_admission_is_denied() -> None:
    repository = _Repository()
    gate = _gate(repository)
    identity = _identity(ScoringDispatchRole.PRIMARY)

    gate.admit(identity, now=_NOW)

    with pytest.raises(ScoringDispatchDenied, match="already consumed"):
        gate.admit(identity, now=_NOW)


def test_duplicate_repair_admission_is_denied() -> None:
    repository = _Repository()
    gate = _gate(repository)
    identity = _identity(ScoringDispatchRole.REPAIR)

    gate.admit(identity, now=_NOW)

    with pytest.raises(ScoringDispatchDenied, match="already consumed"):
        gate.admit(identity, now=_NOW)


def test_duplicate_judge_admission_is_denied_without_consuming_other_role() -> None:
    repository = _Repository()
    gate = _gate(repository)
    primary = _identity(ScoringDispatchRole.PRIMARY_JUDGE, "b")
    repair = _identity(ScoringDispatchRole.REPAIR_JUDGE, "c")

    gate.admit(primary, now=_NOW)

    with pytest.raises(ScoringDispatchDenied, match="already consumed"):
        gate.admit(primary, now=_NOW)
    gate.admit(repair, now=_NOW)


def test_judge_dispatch_without_a_live_lease_is_rejected_before_provider_contact() -> None:
    repository = _Repository()
    repository.job = replace(repository.job, status=JobStatus.PENDING)
    runtime, provider = _judge_runtime()

    with pytest.raises(ScoringDispatchDenied, match="lease"):
        runtime._dispatch_quality_judge(
            operation_input=_judge_operation(),
            content_input=object(),  # type: ignore[arg-type]
            admission=_live_judge_gate(repository),
        )

    assert provider.calls == []


def test_expired_lease_blocks_real_judge_dispatch_before_provider_contact() -> None:
    repository = _Repository()
    repository.job = replace(
        repository.job, lease_until=datetime.now(UTC) - timedelta(seconds=1)
    )
    runtime, provider = _judge_runtime()

    with pytest.raises(ScoringDispatchDenied, match="lease"):
        runtime._dispatch_quality_judge(
            operation_input=_judge_operation(),
            content_input=object(),  # type: ignore[arg-type]
            admission=_gate(repository),
        )

    assert provider.calls == []


def test_duplicate_judge_dispatch_is_rejected_before_a_second_provider_contact() -> None:
    runtime, provider = _judge_runtime()
    gate = _live_judge_gate(_Repository())

    runtime._dispatch_quality_judge(
        operation_input=_judge_operation(),
        content_input=object(),  # type: ignore[arg-type]
        admission=gate,
    )
    with pytest.raises(ScoringDispatchDenied, match="already consumed"):
        runtime._dispatch_quality_judge(
            operation_input=_judge_operation(),
            content_input=object(),  # type: ignore[arg-type]
            admission=gate,
        )

    assert len(provider.calls) == 1


def test_concurrent_judge_admission_allows_only_one_provider_contact() -> None:
    runtime, provider = _judge_runtime()
    gate = _live_judge_gate(_Repository())

    def dispatch() -> str:
        try:
            runtime._dispatch_quality_judge(
                operation_input=_judge_operation(),
                content_input=object(),  # type: ignore[arg-type]
                admission=gate,
            )
        except ScoringDispatchDenied:
            return "denied"
        return "dispatched"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = set(executor.map(lambda _value: dispatch(), range(2)))

    assert results == {"denied", "dispatched"}
    assert len(provider.calls) == 1


def test_judge_budget_is_exhausted_after_primary_and_repair_dispatches() -> None:
    runtime, provider = _judge_runtime()
    gate = _live_judge_gate(_Repository())

    runtime._dispatch_quality_judge(
        operation_input=_judge_operation("PRIMARY"),
        content_input=object(),  # type: ignore[arg-type]
        admission=gate,
    )
    runtime._dispatch_quality_judge(
        operation_input=_judge_operation("REPAIR"),
        content_input=object(),  # type: ignore[arg-type]
        admission=gate,
    )
    with pytest.raises(ScoringDispatchDenied, match="already consumed"):
        runtime._dispatch_quality_judge(
            operation_input=_judge_operation("PRIMARY"),
            content_input=object(),  # type: ignore[arg-type]
            admission=gate,
        )

    assert len(provider.calls) == 2


def test_competing_runtime_cannot_admit_under_another_claimant_lease() -> None:
    repository = _Repository(owner="runtime-a")

    def attempt(owner: str) -> str:
        try:
            _gate(repository, owner=owner).admit(
                _identity(ScoringDispatchRole.PRIMARY), now=_NOW
            )
        except ScoringDispatchDenied:
            return "denied"
        return "admitted"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = set(executor.map(attempt, ("runtime-a", "runtime-b")))

    assert results == {"admitted", "denied"}


def test_repair_identity_is_stable_after_restart() -> None:
    kwargs = dict(
        primary_scoring_request_hash="1" * 64,
        primary_normalized_input_hash="2" * 64,
        primary_raw_response_hash="3" * 64,
        primary_failure_class="JUDGE_REJECT",
        repair_prompt_version="scoring-repair-prompt-v1",
        repair_schema_version="scoring-result-v1",
        scoring_provider="ollama",
        scoring_model="qwen3:8b",
        scoring_model_digest="sha256:" + ("4" * 64),
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
        output_language="en",
    )

    before_restart = build_repair_scoring_dispatch_identity(**kwargs)
    after_restart = build_repair_scoring_dispatch_identity(**kwargs)

    assert after_restart == before_restart
    assert before_restart.role is ScoringDispatchRole.REPAIR


def test_primary_identity_is_stable_after_restart_and_does_not_collide_with_repair() -> None:
    scoring_input = _primary_scoring_input()
    context = _primary_context()
    primary_before_restart = build_primary_scoring_dispatch_identity(
        scoring_input=scoring_input,  # type: ignore[arg-type]
        context=context,  # type: ignore[arg-type]
    )
    primary_after_restart = build_primary_scoring_dispatch_identity(
        scoring_input=scoring_input,  # type: ignore[arg-type]
        context=context,  # type: ignore[arg-type]
    )
    repair = build_repair_scoring_dispatch_identity(
        primary_scoring_request_hash=primary_before_restart.request_hash,
        primary_normalized_input_hash=primary_before_restart.normalized_input_hash,
        primary_raw_response_hash="3" * 64,
        primary_failure_class="JUDGE_REJECT",
        repair_prompt_version="scoring-repair-prompt-v1",
        repair_schema_version="scoring-result-v1",
        scoring_provider="ollama",
        scoring_model="qwen3:8b",
        scoring_model_digest="sha256:" + ("4" * 64),
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
        output_language="en",
    )

    assert primary_after_restart == primary_before_restart
    assert primary_before_restart.role is ScoringDispatchRole.PRIMARY
    assert repair.request_hash != primary_before_restart.request_hash


def test_judge_identities_are_role_distinct_and_stable_after_restart() -> None:
    def identity(role: str) -> ScoringDispatchIdentity:
        return build_judge_scoring_dispatch_identity(
            QualityJudgeOperationInput.model_validate(
                {
                    "scoring_request_hash": "1" * 64,
                    "attempt_role": role,
                    "candidate_hash": "2" * 64,
                    "quality_input_hash": "3" * 64,
                    "policy_version": "content-quality-policy-v1",
                    "prompt_version": "content-quality-prompt-v1",
                    "schema_version": "content-quality-result-v1",
                    "judge_provider": "ollama",
                    "judge_model": "qwen3:8b",
                    "judge_model_digest": "sha256:" + ("4" * 64),
                }
            )
        )

    primary_before_restart = identity("PRIMARY")
    primary_after_restart = identity("PRIMARY")
    repair = identity("REPAIR")

    assert primary_after_restart == primary_before_restart
    assert primary_before_restart.role is ScoringDispatchRole.PRIMARY_JUDGE
    assert repair.role is ScoringDispatchRole.REPAIR_JUDGE
    assert repair.request_hash != primary_before_restart.request_hash


def test_existing_pending_provider_call_blocks_dispatch() -> None:
    repository = _Repository()
    identity = _identity(ScoringDispatchRole.PRIMARY)
    repository.calls[identity.request_hash] = _provider_call(
        identity.request_hash, ProviderCallStatus.PENDING
    )
    dispatches: list[str] = []

    with pytest.raises(ScoringDispatchDenied, match="existing provider state"):
        _gate(repository).admit(identity, now=_NOW)
        dispatches.append("external")

    assert dispatches == []


def test_unknown_provider_state_blocks_retry() -> None:
    repository = _Repository()
    identity = _identity(ScoringDispatchRole.PRIMARY)
    repository.calls[identity.request_hash] = _provider_call(
        identity.request_hash, ProviderCallStatus.FAILED_RETRYABLE
    )

    with pytest.raises(ScoringDispatchDenied, match="existing provider state") as raised:
        _gate(repository).admit(identity, now=_NOW)

    assert raised.value.error.retryable is False


@pytest.mark.parametrize("provider_error", [TimeoutError("timeout"), RuntimeError("lost")])
def test_provider_failure_after_admission_becomes_unknown_provider_state(
    provider_error: Exception,
) -> None:
    runtime = object.__new__(RuntimeOperations)
    runtime._dependencies = SimpleNamespace(
        scoring_provider_factory=lambda: SimpleNamespace(
            primary_attempt=lambda _input: (_ for _ in ()).throw(provider_error)
        )
    )
    gate = _gate(_Repository())
    gate.admit(_identity(ScoringDispatchRole.PRIMARY), now=_NOW)

    with pytest.raises(UnknownProviderState, match="unknown after external dispatch"):
        runtime._dispatch_primary_attempt_after_admission(object())  # type: ignore[arg-type]


def _unknown_state_repository(tmp_path) -> tuple[SQLiteStateRepository, str]:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=_NOW)
    repository.save_discovery_batch(
        DiscoveryBatch(
            channel_id="channel-1",
            video_ids=("video-1",),
            next_cursor=DiscoveryCursor(
                channel_id="channel-1",
                last_checked_at=_NOW,
                latest_published_at=_NOW,
                latest_video_id="video-1",
                provider_cursor="cursor-1",
            ),
            call=ProviderCallMetadata(provider="fake", started_at=_NOW, finished_at=_NOW),
        ),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="runtime-v1",
        now=_NOW,
    )
    repository.advance_pipeline(
        "video-1",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="runtime-v1",
        now=_NOW,
    )
    repository.advance_pipeline(
        "video-1",
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="runtime-v1",
        now=_NOW,
    )
    job_id = "unknown-scoring-job"
    repository.create_job(
        job_id=job_id,
        scope_key="video:video-1:SCORING",
        video_id="video-1",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="runtime-v1",
        max_attempts=3,
        available_at=_NOW,
        now=_NOW,
    )
    return repository, job_id


def test_unknown_provider_state_is_atomically_terminal_and_survives_restart(tmp_path) -> None:
    repository, job_id = _unknown_state_repository(tmp_path)
    claimed = repository.claim_next_job(
        owner="runtime-a", lease_until=_NOW + timedelta(minutes=5), now=_NOW
    )
    assert claimed is not None

    def contacted_provider(job: JobRecord, _video: object) -> None:
        _gate_for_sqlite(repository, job).admit(
            _identity(ScoringDispatchRole.PRIMARY), now=_NOW
        )
        raise UnknownProviderState("scoring provider outcome is unknown after external dispatch")

    orchestrator = PipelineOrchestrator(
        repository=repository,
        planner=PipelineJobPlanner(
            repository=repository, pipeline_version="runtime-v1", max_attempts=3
        ),
        owner="runtime-a",
        lease_seconds=300,
        retry_policy=RetryPolicy(1, 1, 0),
        handlers={ProcessingStage.SCORING: contacted_provider},
        clock=lambda: _NOW,
    )

    orchestrator._execute(claimed, now=_NOW)

    saved = repository.get_job(job_id)
    assert saved is not None
    assert saved.status is JobStatus.FAILED_FINAL
    assert saved.last_error_code == "UNKNOWN_PROVIDER_STATE"
    assert repository.list_job_attempts(job_id)[0].outcome.value == "FAILED_FINAL"

    restarted = SQLiteStateRepository(tmp_path / "state.sqlite")
    restarted.initialize(now=_NOW + timedelta(minutes=1))
    after_restart = restarted.get_job(job_id)
    assert after_restart is not None
    assert after_restart.last_error_code == "UNKNOWN_PROVIDER_STATE"
    assert restarted.claim_next_job(
        owner="runtime-b",
        lease_until=_NOW + timedelta(minutes=6),
        now=_NOW + timedelta(minutes=1),
    ) is None


def _gate_for_sqlite(
    repository: SQLiteStateRepository, job: JobRecord
) -> ScoringDispatchAdmission:
    return ScoringDispatchAdmission(
        repository=repository, job_id=job.job_id, owner=job.lease_owner or ""
    )


def test_expired_scoring_lease_is_finalized_before_generic_reclaim(tmp_path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=_NOW)
    repository.save_discovery_batch(
        DiscoveryBatch(
            channel_id="channel-1",
            video_ids=("video-1",),
            next_cursor=DiscoveryCursor(
                channel_id="channel-1",
                last_checked_at=_NOW,
                latest_published_at=_NOW,
                latest_video_id="video-1",
                provider_cursor="cursor-1",
            ),
            call=ProviderCallMetadata(
                provider="fake", started_at=_NOW, finished_at=_NOW
            ),
        ),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="runtime-v1",
        now=_NOW,
    )
    repository.create_job(
        job_id="expired-scoring-job",
        scope_key="video:video-1:SCORING",
        video_id="video-1",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="runtime-v1",
        max_attempts=3,
        available_at=_NOW,
        now=_NOW,
    )
    repository.claim_next_job(
        owner="runtime-a", lease_until=_NOW + timedelta(minutes=1), now=_NOW
    )

    recovered = repository.reclaim_expired_jobs(now=_NOW + timedelta(minutes=2))

    assert recovered[0].status is JobStatus.FAILED_FINAL
    assert recovered[0].last_error_code == "UNKNOWN_PROVIDER_STATE"
    assert repository.claim_next_job(
        owner="runtime-b",
        lease_until=_NOW + timedelta(minutes=3),
        now=_NOW + timedelta(minutes=2),
    ) is None
