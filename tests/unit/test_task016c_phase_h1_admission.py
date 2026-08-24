"""H1-A runtime admission tests for trusted scoring dispatches."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from youtube_intel.config import LocalScoringSettings, load_app_config
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
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
from youtube_intel.scoring import build_scoring_input
from youtube_intel.scoring_admission import (
    ScoringAdmissionRegistry,
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
    runtime._dependencies = SimpleNamespace(
        quality_judge_provider_factory=lambda: provider
    )
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


def _runtime_for_h1(
    project: Path,
    *,
    scoring_provider_factory: object,
    quality_judge_provider_factory: object | None = None,
) -> RuntimeOperations:
    (project / "config").mkdir(parents=True, exist_ok=True)
    (project / "vault").mkdir(exist_ok=True)
    (project / "config" / "channels.yaml").write_text(
        "channels:\n  - channel_id: channel-1\n", encoding="utf-8"
    )
    (project / "config" / "settings.yaml").write_text(
        f"""\
general:
  transcript_languages: [en]
  output_language: en
local_scoring:
  model: qwen3:8b
  expected_model_digest: sha256:{"4" * 64}
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
            scoring_provider_factory=scoring_provider_factory,  # type: ignore[arg-type]
            analysis_provider_factory=lambda: object(),  # type: ignore[arg-type]
            quality_judge_provider_factory=quality_judge_provider_factory,  # type: ignore[arg-type]
        ),
    )


def _active_scoring_job(
    repository: SQLiteStateRepository, *, owner: str, now: datetime
) -> JobRecord:
    repository.save_discovery_batch(
        DiscoveryBatch(
            channel_id="channel-1",
            video_ids=("video-1",),
            next_cursor=DiscoveryCursor(
                channel_id="channel-1",
                last_checked_at=now,
                latest_published_at=now,
                latest_video_id="video-1",
                provider_cursor="cursor-1",
            ),
            call=ProviderCallMetadata(provider="fake", started_at=now, finished_at=now),
        ),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="runtime-v1",
        now=now,
    )
    repository.advance_pipeline(
        "video-1",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="runtime-v1",
        now=now,
    )
    repository.advance_pipeline(
        "video-1",
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="runtime-v1",
        now=now,
    )
    repository.create_job(
        job_id="scoring-job",
        scope_key="video:video-1:SCORING",
        video_id="video-1",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="runtime-v1",
        max_attempts=3,
        available_at=now,
        now=now,
    )
    claimed = repository.claim_next_job(
        owner=owner, lease_until=now + timedelta(minutes=5), now=now
    )
    assert claimed is not None
    return claimed


def test_duplicate_primary_admission_is_denied() -> None:
    repository = _Repository()
    gate = _gate(repository)
    identity = _identity(ScoringDispatchRole.PRIMARY)

    gate.admit(identity, now=_NOW)

    with pytest.raises(ScoringDispatchDenied, match="already consumed"):
        gate.admit(identity, now=_NOW)


def test_public_trusted_scoring_rejects_caller_created_admission(tmp_path: Path) -> None:
    runtime = _runtime_for_h1(
        tmp_path / "project", scoring_provider_factory=lambda: object()
    )

    with pytest.raises(TypeError, match="unexpected keyword argument 'admission'"):
        runtime.run_primary_trusted_scoring(
            attempt=object(),  # type: ignore[arg-type]
            scoring_input=object(),  # type: ignore[arg-type]
            admission=_gate(_Repository()),
        )


def test_duplicate_repair_admission_is_denied() -> None:
    repository = _Repository()
    first = _gate(repository)
    second = _gate(repository)
    identity = _identity(ScoringDispatchRole.REPAIR)

    first.admit(identity, now=_NOW)

    with pytest.raises(ScoringDispatchDenied, match="already consumed"):
        second.admit(identity, now=_NOW)


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
    repository = _Repository()
    first = _live_judge_gate(repository)
    second = _live_judge_gate(repository)

    runtime._dispatch_quality_judge(
        operation_input=_judge_operation(),
        content_input=object(),  # type: ignore[arg-type]
        admission=first,
    )
    with pytest.raises(ScoringDispatchDenied, match="already consumed"):
        runtime._dispatch_quality_judge(
            operation_input=_judge_operation(),
            content_input=object(),  # type: ignore[arg-type]
            admission=second,
        )

    assert len(provider.calls) == 1


def test_concurrent_judge_admission_allows_only_one_provider_contact() -> None:
    runtime, provider = _judge_runtime()
    repository = _Repository()
    admissions = (_live_judge_gate(repository), _live_judge_gate(repository))

    def dispatch(admission: ScoringDispatchAdmission) -> str:
        try:
            runtime._dispatch_quality_judge(
                operation_input=_judge_operation(),
                content_input=object(),  # type: ignore[arg-type]
                admission=admission,
            )
        except ScoringDispatchDenied:
            return "denied"
        return "dispatched"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = set(executor.map(dispatch, admissions))

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


def test_separate_admission_instances_share_one_active_lease_budget() -> None:
    repository = _Repository()
    first = _gate(repository)
    second = _gate(repository)
    identity = _identity(ScoringDispatchRole.PRIMARY)

    def dispatch(admission: ScoringDispatchAdmission) -> str:
        try:
            admission.admit(identity, now=_NOW)
        except ScoringDispatchDenied:
            return "denied"
        return "dispatched"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = set(executor.map(dispatch, (first, second)))

    assert results == {"denied", "dispatched"}


def test_two_sqlite_runtime_views_share_budget_without_sharing_admission_objects(
    tmp_path: Path,
) -> None:
    provider = _JudgeProvider()
    runtime_a = _runtime_for_h1(
        tmp_path / "project",
        scoring_provider_factory=lambda: object(),
        quality_judge_provider_factory=lambda: provider,
    )
    runtime_b = _runtime_for_h1(
        tmp_path / "project",
        scoring_provider_factory=lambda: object(),
        quality_judge_provider_factory=lambda: provider,
    )
    runtime_b._runtime_owner = runtime_a._runtime_owner
    claimed = _active_scoring_job(
        runtime_a._repository,
        owner=runtime_a._runtime_owner,
        now=datetime.now(UTC),
    )
    admission_a = runtime_a._scoring_admission_for(claimed.job_id)
    admission_b = runtime_b._scoring_admission_for(claimed.job_id)
    assert runtime_a._repository is not runtime_b._repository
    assert admission_a is not admission_b

    def dispatch(runtime: RuntimeOperations, admission: ScoringDispatchAdmission) -> str:
        try:
            runtime._dispatch_quality_judge(
                operation_input=_judge_operation(),
                content_input=object(),  # type: ignore[arg-type]
                admission=admission,
            )
        except ScoringDispatchDenied:
            return "denied"
        return "dispatched"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = set(
            executor.map(
                lambda pair: dispatch(*pair),
                ((runtime_a, admission_a), (runtime_b, admission_b)),
            )
        )

    assert results == {"denied", "dispatched"}
    assert len(provider.calls) == 1


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


def test_provider_factory_failure_is_dispatch_denied_before_provider_contact(
    tmp_path: Path,
) -> None:
    factory_calls: list[str] = []
    runtime = _runtime_for_h1(
        tmp_path / "project",
        scoring_provider_factory=lambda: (
            factory_calls.append("factory"),
            (_ for _ in ()).throw(RuntimeError("client construction failed")),
        )[1],
    )

    with pytest.raises(ScoringDispatchDenied, match="before external provider contact"):
        runtime._create_scoring_provider_for_dispatch()

    assert factory_calls == ["factory"]


def test_judge_factory_failure_is_denied_without_consuming_admission_budget(
    tmp_path: Path,
) -> None:
    factory_calls: list[str] = []
    runtime = _runtime_for_h1(
        tmp_path / "project",
        scoring_provider_factory=lambda: object(),
        quality_judge_provider_factory=lambda: (
            factory_calls.append("factory"),
            (_ for _ in ()).throw(RuntimeError("judge construction failed")),
        )[1]
    )
    claimed = _active_scoring_job(
        runtime._repository,
        owner=runtime._runtime_owner,
        now=datetime.now(UTC),
    )
    admission = runtime._scoring_admission_for(claimed.job_id)

    with pytest.raises(ScoringDispatchDenied, match="before external provider contact"):
        runtime._dispatch_quality_judge(
            operation_input=_judge_operation(),
            content_input=object(),  # type: ignore[arg-type]
            admission=admission,
        )

    assert factory_calls == ["factory"]
    provider = _JudgeProvider()
    runtime._dependencies = replace(
        runtime._dependencies,
        quality_judge_provider_factory=lambda: provider,
    )
    runtime._dispatch_quality_judge(
        operation_input=_judge_operation(),
        content_input=object(),  # type: ignore[arg-type]
        admission=admission,
    )
    assert len(provider.calls) == 1


@pytest.mark.parametrize("provider_error", [TimeoutError("timeout"), RuntimeError("lost")])
def test_provider_timeout_or_interruption_after_call_begins_becomes_unknown_provider_state(
    provider_error: Exception,
    tmp_path: Path,
) -> None:
    provider_calls: list[str] = []
    provider = SimpleNamespace(
        primary_attempt=lambda _input: (
            provider_calls.append("provider"),
            (_ for _ in ()).throw(provider_error),
        )[1]
    )
    runtime = _runtime_for_h1(
        tmp_path / "project", scoring_provider_factory=lambda: provider
    )
    claimed = _active_scoring_job(
        runtime._repository,
        owner=runtime._runtime_owner,
        now=datetime.now(UTC),
    )
    runtime._scoring_admission_for(claimed.job_id).admit(
        _identity(ScoringDispatchRole.PRIMARY), now=datetime.now(UTC)
    )

    with pytest.raises(UnknownProviderState, match="unknown after external dispatch"):
        runtime._dispatch_primary_attempt_after_admission(
            runtime._create_scoring_provider_for_dispatch(), object()  # type: ignore[arg-type]
        )

    assert provider_calls == ["provider"]


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
    assert not any(
        key.repository_scope == str((tmp_path / "state.sqlite").resolve())
        and key.job_id == job_id
        for key in ScoringAdmissionRegistry._states
    )


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
