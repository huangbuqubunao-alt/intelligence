"""TASK-016C Phase H2-B final correction — Round 5 / capability-policy RED tests.

Approved objectives under test:

- the semantic REPAIR and REPAIR_JUDGE provider APIs are gone; providers expose
  only role-neutral transport whose manual use can never enter the authoritative
  RuntimeOperations H2-B continuation (behavioral, real provider + fake
  transport, not merely hasattr);
- a successful H2-B-only build constructs the aggregate as a lexical local only,
  terminalizes exactly once with ``ErrorCode.CAPABILITY_UNAVAILABLE`` +
  ``H2B_PASS_AWAITING_H2C`` + ``retry_at=None`` -> ``FAILED_FINAL`` ->
  ``TERMINAL``, persists nothing, and exposes no aggregate on the runtime,
  globals, or caches;
- ``RuntimeOperations.retry()`` excludes ``CAPABILITY_UNAVAILABLE`` jobs by code
  only (altered detail still excluded; same detail on another code follows that
  code's ordinary retry policy; mixed/repeated/only-candidate semantics);
- the two exhaustive ErrorCode boundary consumers map ``CAPABILITY_UNAVAILABLE``
  safely while every existing mapping (especially LOCAL_RESOURCE) is unchanged;
- the ErrorCode taxonomy is exactly nine members.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import timedelta
from importlib import resources
from pathlib import Path
from typing import Any

import pytest

import youtube_intel.h2_evidence as h2_evidence_module
import youtube_intel.runtime as runtime_module
from youtube_intel.domain import (
    AppError,
    ErrorCode,
    JobStatus,
    ProcessingStage,
)
from youtube_intel.h2_evidence import PhaseH2BValidatedRepairResult
from youtube_intel.providers.ollama import (
    OllamaQualityJudgeProvider,
    OllamaScoringProvider,
    build_task016c_repair_generate_body,
    parse_scoring_candidate,
    seal_primary_raw_capture,
)
from youtube_intel.scoring_admission import (
    ScoringAdmissionRegistry,
    ScoringDispatchIdentity,
    ScoringDispatchRole,
)
from youtube_intel.state import ArtifactKind, JobType

NOW_DELAY = timedelta(minutes=5)


def _load_support(name: str, file_name: str) -> Any:
    support_path = Path(__file__).with_name(file_name)
    specification = importlib.util.spec_from_file_location(name, support_path)
    assert specification is not None and specification.loader is not None
    support = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = support
    specification.loader.exec_module(support)
    return support


_FLOW = _load_support(
    "_h2b_final_correction_flow_support", "test_task016c_phase_h2b_repair_flow.py"
)


def _scoring_prompt() -> str:
    return (
        resources.files("youtube_intel")
        .joinpath("prompts", "scoring.md")
        .read_text(encoding="utf-8")
    )


def _setup_video_job(
    runtime: Any,
    *,
    job_id: str,
    video_id: str | None = None,
) -> Any:
    """Discover one video, advance it to TRANSCRIPT_READY, create+claim a job."""

    selected_video = video_id if video_id is not None else _FLOW.VIDEO_ID
    repository = runtime._repository
    repository.save_discovery_batch(
        _FLOW.DiscoveryBatch(
            channel_id=_FLOW.CHANNEL_ID,
            video_ids=(selected_video,),
            next_cursor=_FLOW.DiscoveryCursor(
                channel_id=_FLOW.CHANNEL_ID,
                last_checked_at=_FLOW.NOW,
                latest_published_at=_FLOW.NOW,
                latest_video_id=selected_video,
                provider_cursor="cursor-1",
            ),
            call=_FLOW.ProviderCallMetadata(
                provider="fake", started_at=_FLOW.NOW, finished_at=_FLOW.NOW
            ),
        ),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="runtime-v1",
        now=_FLOW.NOW,
    )
    repository.advance_pipeline(
        selected_video,
        expected_status=_FLOW.PipelineStatus.DISCOVERED,
        target_status=_FLOW.PipelineStatus.METADATA_READY,
        pipeline_version="runtime-v1",
        now=_FLOW.NOW,
    )
    repository.advance_pipeline(
        selected_video,
        expected_status=_FLOW.PipelineStatus.METADATA_READY,
        target_status=_FLOW.PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="runtime-v1",
        now=_FLOW.NOW,
    )
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:{selected_video}:SCORING",
        video_id=selected_video,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="runtime-v1",
        max_attempts=3,
        available_at=_FLOW.NOW,
        now=_FLOW.NOW,
    )
    claimed = repository.claim_next_job(
        owner=runtime._runtime_owner,
        lease_until=_FLOW.NOW + NOW_DELAY,
        now=_FLOW.NOW,
    )
    assert claimed is not None and claimed.job_id == job_id
    return claimed


def _terminal_job(
    tmp_path: Path,
    *,
    error_code: str,
    message: str,
    job_id: str = "capability-job",
    video_id: str | None = None,
) -> tuple[Any, Any]:
    runtime = _FLOW._runtime(tmp_path, _FLOW._FakeTransport([]))
    job = _setup_video_job(runtime, job_id=job_id, video_id=video_id)
    runtime._repository.fail_job(
        job.job_id,
        owner=runtime._runtime_owner,
        error_code=ErrorCode(error_code),
        error_message=message,
        retry_at=None,
        now=_FLOW.NOW,
    )
    saved = runtime._repository.get_job(job.job_id)
    assert saved is not None and saved.status is JobStatus.FAILED_FINAL
    return runtime, saved


def _assert_no_aggregate_exposure(runtime: Any) -> None:
    # No runtime attribute/property/container may hold the aggregate.
    for value in vars(runtime).values():
        assert type(value) is not PhaseH2BValidatedRepairResult
        if isinstance(value, (dict, list, tuple, set, frozenset)):
            for contained in value:
                assert type(contained) is not PhaseH2BValidatedRepairResult
    # No module-global/cache registration either.
    for module in (runtime_module, h2_evidence_module):
        for name in dir(module):
            if name.startswith("__"):
                continue
            assert (
                type(getattr(module, name, None)) is not PhaseH2BValidatedRepairResult
            )


# ---------------------------------------------------------------------------
# Provider boundary: semantic APIs removed, role-neutral transport only
# ---------------------------------------------------------------------------


def test_semantic_repair_provider_apis_are_absent(tmp_path: Path) -> None:
    transport = _FLOW._FakeTransport([_FLOW._tags(), _FLOW._tags()])
    runtime = _FLOW._runtime(tmp_path, transport)
    job = _setup_video_job(runtime, job_id="scoring-job")
    admission = runtime._scoring_admission_for(job.job_id)
    admission.admit(
        ScoringDispatchIdentity(
            role=ScoringDispatchRole.PRIMARY,
            operation="local-scoring",
            normalized_input_hash="p" * 64,
            request_hash="p" * 64,
        ),
        now=_FLOW.NOW,
    )
    admission.consume_repair_role(
        ScoringDispatchIdentity(
            role=ScoringDispatchRole.REPAIR,
            operation="local-scoring-repair-v1",
            normalized_input_hash="a" * 64,
            request_hash="a" * 64,
        ),
        now=_FLOW.NOW,
    )

    scoring_provider = OllamaScoringProvider(
        settings=runtime._config.settings.local_scoring,
        prompt=_scoring_prompt(),
        transport=transport,
    )
    judge_provider = OllamaQualityJudgeProvider(
        settings=runtime._config.settings.local_scoring,
        transport=transport,
    )
    forbidden_scoring = (
        "dispatch_exact_repair_generate",
        "dispatch_repair",
        "execute_repair",
        "run_exact_repair",
        "repair_generate",
        "send_admitted_repair",
    )
    forbidden_judge = (
        "judge_exact_model_content",
        "dispatch_repair_judge",
        "execute_repair_judge",
        "send_admitted_repair_judge",
    )
    for name in forbidden_scoring:
        assert not hasattr(scoring_provider, name), name
        assert not hasattr(OllamaScoringProvider, name), name
    for name in forbidden_judge:
        assert not hasattr(judge_provider, name), name
        assert not hasattr(OllamaQualityJudgeProvider, name), name


def test_manual_role_neutral_repair_transport_produces_no_authoritative_h2b(
    tmp_path: Path,
) -> None:
    repair_inner = _FLOW._valid_candidate()
    transport = _FLOW._FakeTransport(
        [_FLOW._tags(), _FLOW._outer(repair_inner)]
    )
    runtime = _FLOW._runtime(tmp_path, transport)
    repository = runtime._repository
    job = _setup_video_job(runtime, job_id="scoring-job")
    admission = runtime._scoring_admission_for(job.job_id)
    admission.admit(
        ScoringDispatchIdentity(
            role=ScoringDispatchRole.PRIMARY,
            operation="local-scoring",
            normalized_input_hash="p" * 64,
            request_hash="p" * 64,
        ),
        now=_FLOW.NOW,
    )
    repair_identity = ScoringDispatchIdentity(
        role=ScoringDispatchRole.REPAIR,
        operation="local-scoring-repair-v1",
        normalized_input_hash="a" * 64,
        request_hash="a" * 64,
    )
    admission.consume_repair_role(repair_identity, now=_FLOW.NOW)

    # The attacker drives the remaining role-neutral transport directly with
    # arbitrary self-consistent repair-looking bytes.
    provider = OllamaScoringProvider(
        settings=runtime._config.settings.local_scoring,
        prompt=_scoring_prompt(),
        transport=transport,
    )
    body = build_task016c_repair_generate_body(
        model=runtime._config.settings.local_scoring.model,
        prompt="prompt_version: scoring-prompt-v2\nattacker payload",
        temperature=0.0,
        max_output_tokens=1200,
    )
    raw = provider.dispatch_exact_generate(
        body=body,
        body_sha256=hashlib.sha256(body).hexdigest(),
        body_length=len(body),
    )

    # Network traffic may occur — it is not authoritative H2-B execution.
    assert transport.tags_calls == 1
    assert transport.generate_calls == 1
    assert type(raw) is bytes
    # Pure parsing remains allowed — it grants no execution provenance.
    assert parse_scoring_candidate(seal_primary_raw_capture(raw).utf8) is not None

    # But nothing entered the authoritative RuntimeOperations H2-B continuation.
    _assert_no_aggregate_exposure(runtime)
    assert repository.get_provider_call("a" * 64) is None
    assert repository.latest_artifact(_FLOW.VIDEO_ID, ArtifactKind.SCORING_STRUCTURED) is None
    saved = repository.get_job(job.job_id)
    assert saved is not None
    assert saved.status is JobStatus.RUNNING  # unchanged by manual transport
    # No terminalization/error was caused by the manual traffic.
    attempts = repository.list_job_attempts(job.job_id)
    assert all(attempt.error_code is None for attempt in attempts)


def test_manual_valid_raw_response_cannot_be_injected_into_h2b_continuation(
    tmp_path: Path,
) -> None:
    repair_inner = _FLOW._valid_candidate()
    transport = _FLOW._FakeTransport([_FLOW._tags(), _FLOW._outer(repair_inner)])
    runtime = _FLOW._runtime(tmp_path, transport)
    job = _setup_video_job(runtime, job_id="scoring-job")

    provider = OllamaScoringProvider(
        settings=runtime._config.settings.local_scoring,
        prompt=_scoring_prompt(),
        transport=transport,
    )
    body = build_task016c_repair_generate_body(
        model=runtime._config.settings.local_scoring.model,
        prompt="prompt_version: scoring-prompt-v2\nattacker payload",
        temperature=0.0,
        max_output_tokens=1200,
    )
    raw = provider.dispatch_exact_generate(
        body=body,
        body_sha256=hashlib.sha256(body).hexdigest(),
        body_length=len(body),
    )

    # The manually obtained raw is perfectly valid repair-looking data: pure
    # parsing succeeds — but parsing grants no execution provenance.
    assert parse_scoring_candidate(seal_primary_raw_capture(raw).utf8) is not None

    # There is no caller-facing raw-to-authoritative-H2-B ingress on the runtime.
    for name in (
        "_h2b_execute_repair",
        "_h2b_ingest_raw",
        "_h2b_accept_raw",
        "submit_repair_raw",
        "continue_repair",
    ):
        assert not hasattr(runtime, name), name
    _assert_no_aggregate_exposure(runtime)
    assert runtime._repository.get_job(job.job_id).status is JobStatus.RUNNING


def test_manual_role_neutral_judge_transport_produces_no_authoritative_h2b(
    tmp_path: Path,
) -> None:
    judge_raw = json.dumps(
        {
            "status": "PASS",
            "decision_confidence": "HIGH",
            "grounding_confidence": "MEDIUM",
            "usefulness_confidence": "MEDIUM",
            "signals": ["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
            "reason": None,
            "evidence_ids": ["title-1"],
        }
    )
    transport = _FLOW._FakeTransport([_FLOW._tags(), _FLOW._outer(judge_raw)])
    runtime = _FLOW._runtime(tmp_path, transport)
    job = _setup_video_job(runtime, job_id="scoring-job")

    judge_provider = OllamaQualityJudgeProvider(
        settings=runtime._config.settings.local_scoring,
        transport=transport,
    )
    body = json.dumps(
        {"model": _FLOW.MODEL, "prompt": "attacker judge payload", "stream": False},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    raw = judge_provider.dispatch_exact_generate(
        body=body,
        body_sha256=hashlib.sha256(body).hexdigest(),
        body_length=len(body),
    )

    assert transport.tags_calls == 1
    assert transport.generate_calls == 1
    assert type(raw) is bytes
    # Manual judge-looking traffic/raw cannot enter any authoritative
    # continuation: no aggregate, no job transition, no persistence.
    _assert_no_aggregate_exposure(runtime)
    assert runtime._repository.get_job(job.job_id).status is JobStatus.RUNNING
    assert (
        runtime._repository.latest_artifact(
            _FLOW.VIDEO_ID, ArtifactKind.SCORING_STRUCTURED
        )
        is None
    )


def test_role_neutral_transport_rejects_payload_integrity_mismatch_before_contact(
    tmp_path: Path,
) -> None:
    transport = _FLOW._FakeTransport([_FLOW._tags()])
    runtime = _FLOW._runtime(tmp_path, transport)
    del runtime
    provider = OllamaScoringProvider(
        settings=_FLOW._runtime(tmp_path / "s", _FLOW._FakeTransport([]))
        ._config.settings.local_scoring,
        prompt=_scoring_prompt(),
        transport=transport,
    )
    body = b'{"prompt":"x"}'
    from youtube_intel.scoring_admission import ScoringDispatchDenied

    with pytest.raises(ScoringDispatchDenied, match="payload"):
        provider.dispatch_exact_generate(
            body=body, body_sha256="f" * 64, body_length=len(body)
        )
    assert transport.requests == []


# ---------------------------------------------------------------------------
# Transitional H2-B PASS and aggregate lifetime
# ---------------------------------------------------------------------------


def test_full_h2b_pass_terminalizes_capability_unavailable_once(tmp_path: Path) -> None:
    transport = _FLOW._FakeTransport(
        _FLOW._repair_script(
            primary_inner="{not-json",
            repair_inner=_FLOW._valid_candidate(),
            judge_status="PASS",
        )
    )
    runtime = _FLOW._runtime(tmp_path, transport)

    _FLOW._run_process(runtime)

    # The validated H2-B PASS enters H2-C on a v1-generation Job and
    # persists the complete REPAIR_H2C lineage graph exactly once.
    job = _FLOW._assert_h2c_repair_success(runtime)
    attempts = runtime._repository.list_job_attempts(job.job_id)
    assert len(attempts) == 1
    assert attempts[0].outcome.value == "SUCCEEDED"
    # The legitimate admitted path made exactly one REPAIR and one Judge
    # contact; the H2-C replay adds zero network contact.
    assert transport.tags_calls == 3
    assert transport.generate_calls == 3
    # H1 consumption accounting: the flow made exactly one admitted REPAIR and
    # one admitted REPAIR_JUDGE contact (each transport requires the prior
    # state-only consumption), and the success transition released the shared
    # admission state as cleanup — without renewing any dispatch authority.
    from youtube_intel import scoring_admission as scoring_admission_module

    scope = scoring_admission_module._repository_scope(runtime._repository)
    matching = [
        key
        for key in ScoringAdmissionRegistry._states
        if key.repository_scope == scope and key.job_id == job.job_id
    ]
    assert matching == []


def test_successful_h2b_exposes_no_aggregate_anywhere(tmp_path: Path) -> None:
    transport = _FLOW._FakeTransport(
        _FLOW._repair_script(
            primary_inner="{not-json",
            repair_inner=_FLOW._valid_candidate(),
            judge_status="PASS",
        )
    )
    runtime = _FLOW._runtime(tmp_path, transport)

    _FLOW._run_process(runtime)

    _assert_no_aggregate_exposure(runtime)
    assert not hasattr(runtime, "_last_h2b_validated_repair_result")
    assert not hasattr(runtime, "last_h2b_result")
    assert not hasattr(runtime, "h2b_result")
    assert not hasattr(runtime, "repair_result")


def test_transitional_terminal_cannot_be_claimed_recovered_or_retried(
    tmp_path: Path,
) -> None:
    transport = _FLOW._FakeTransport(
        _FLOW._repair_script(
            primary_inner="{not-json",
            repair_inner=_FLOW._valid_candidate(),
            judge_status="PASS",
        )
    )
    runtime = _FLOW._runtime(tmp_path, transport)
    _FLOW._run_process(runtime)
    # The H2-C success is final: no scoring rerun, no claim, no resurrection.
    job = _FLOW._assert_h2c_repair_success(runtime)
    assert job.status is JobStatus.SUCCEEDED
    baseline_requests = len(transport.requests)
    before_jobs = len(
        runtime._repository.list_failed_video_jobs()
    )

    # No claim/recovery path resurrects a scoring job for the scored video.
    assert (
        runtime._repository.claim_next_job(
            owner="other-runtime",
            lease_until=_FLOW.NOW + NOW_DELAY,
            now=_FLOW.NOW + timedelta(minutes=1),
            video_id=_FLOW.VIDEO_ID,
        )
        is None
    )
    # Manual retry finds no final failed candidate and dispatches nothing.
    outcome = runtime.retry(video=None, failed_only=False)
    assert outcome.safe_message == "No final failed video job is available to retry."
    assert len(transport.requests) == baseline_requests
    assert len(runtime._repository.list_failed_video_jobs()) == before_jobs
    # The authoritative pointer is immutable: still this exact job.
    assert _FLOW._scoring_job(runtime).job_id == job.job_id


# ---------------------------------------------------------------------------
# RuntimeOperations.retry() CAPABILITY_UNAVAILABLE exclusion
# ---------------------------------------------------------------------------


def test_retry_excludes_capability_unavailable_with_exact_detail(tmp_path: Path) -> None:
    runtime, job = _terminal_job(
        tmp_path,
        error_code="CAPABILITY_UNAVAILABLE",
        message="H2B_PASS_AWAITING_H2C",
    )

    outcome = runtime.retry(video=None, failed_only=False)

    assert outcome.safe_message == "No final failed video job is available to retry."
    saved = runtime._repository.get_job(job.job_id)
    assert saved is not None
    assert saved.status is JobStatus.FAILED_FINAL
    # No new job, no claim, no transport.
    assert runtime._repository.latest_video_job(
        _FLOW.VIDEO_ID, target_stage=ProcessingStage.SCORING
    ).job_id == job.job_id


def test_retry_excludes_capability_unavailable_with_altered_detail(
    tmp_path: Path,
) -> None:
    runtime, job = _terminal_job(
        tmp_path,
        error_code="CAPABILITY_UNAVAILABLE",
        message="ATTACKER_CHANGED_DETAIL",
    )

    outcome = runtime.retry(video=None, failed_only=False)

    # The code-only predicate excludes the job regardless of its detail.
    assert outcome.safe_message == "No final failed video job is available to retry."
    assert runtime._repository.latest_video_job(
        _FLOW.VIDEO_ID, target_stage=ProcessingStage.SCORING
    ).job_id == job.job_id


def test_h2b_detail_on_other_code_does_not_spoof_exclusion(tmp_path: Path) -> None:
    runtime, job = _terminal_job(
        tmp_path,
        error_code="LOCAL_RESOURCE",
        message="H2B_PASS_AWAITING_H2C",
    )

    runtime.retry(video=None, failed_only=False)

    # The job follows its ordinary retry policy: a manual rerun job is created.
    latest = runtime._repository.latest_video_job(
        _FLOW.VIDEO_ID, target_stage=ProcessingStage.SCORING
    )
    assert latest.job_id != job.job_id
    assert latest.job_id.startswith("retry-")


def test_mixed_retry_skips_capability_and_retries_ordinary(tmp_path: Path) -> None:
    video_b = "video-b-mixed"
    runtime = _FLOW._runtime(tmp_path, _FLOW._FakeTransport([]))
    repository = runtime._repository
    repository.save_discovery_batch(
        _FLOW.DiscoveryBatch(
            channel_id=_FLOW.CHANNEL_ID,
            video_ids=(_FLOW.VIDEO_ID, video_b),
            next_cursor=_FLOW.DiscoveryCursor(
                channel_id=_FLOW.CHANNEL_ID,
                last_checked_at=_FLOW.NOW,
                latest_published_at=_FLOW.NOW,
                latest_video_id=video_b,
                provider_cursor="cursor-1",
            ),
            call=_FLOW.ProviderCallMetadata(
                provider="fake", started_at=_FLOW.NOW, finished_at=_FLOW.NOW
            ),
        ),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="runtime-v1",
        now=_FLOW.NOW,
    )
    for video_id in (_FLOW.VIDEO_ID, video_b):
        repository.advance_pipeline(
            video_id,
            expected_status=_FLOW.PipelineStatus.DISCOVERED,
            target_status=_FLOW.PipelineStatus.METADATA_READY,
            pipeline_version="runtime-v1",
            now=_FLOW.NOW,
        )
        repository.advance_pipeline(
            video_id,
            expected_status=_FLOW.PipelineStatus.METADATA_READY,
            target_status=_FLOW.PipelineStatus.TRANSCRIPT_READY,
            pipeline_version="runtime-v1",
            now=_FLOW.NOW,
        )
    repository.create_job(
        job_id="capability-job",
        scope_key=f"video:{_FLOW.VIDEO_ID}:SCORING",
        video_id=_FLOW.VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="runtime-v1",
        max_attempts=3,
        available_at=_FLOW.NOW,
        now=_FLOW.NOW,
    )
    claimed_a = repository.claim_next_job(
        owner=runtime._runtime_owner, lease_until=_FLOW.NOW + NOW_DELAY, now=_FLOW.NOW
    )
    assert claimed_a is not None and claimed_a.job_id == "capability-job"
    repository.fail_job(
        claimed_a.job_id,
        owner=runtime._runtime_owner,
        error_code=ErrorCode.CAPABILITY_UNAVAILABLE,
        error_message="H2B_PASS_AWAITING_H2C",
        retry_at=None,
        now=_FLOW.NOW,
    )
    repository.create_job(
        job_id="ordinary-job",
        scope_key=f"video:{video_b}:SCORING",
        video_id=video_b,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="runtime-v1",
        max_attempts=3,
        available_at=_FLOW.NOW,
        now=_FLOW.NOW,
    )
    claimed_b = repository.claim_next_job(
        owner=runtime._runtime_owner, lease_until=_FLOW.NOW + NOW_DELAY, now=_FLOW.NOW
    )
    assert claimed_b is not None and claimed_b.job_id == "ordinary-job"
    repository.fail_job(
        claimed_b.job_id,
        owner=runtime._runtime_owner,
        error_code=ErrorCode.LOCAL_RESOURCE,
        error_message="ordinary stage failure",
        retry_at=None,
        now=_FLOW.NOW,
    )

    runtime.retry(video=None, failed_only=False)

    # The CAPABILITY_UNAVAILABLE job itself is skipped: it is never rerun and
    # keeps its exact staged terminal state.
    saved_a = repository.get_job("capability-job")
    assert saved_a is not None
    assert saved_a.status is JobStatus.FAILED_FINAL
    assert saved_a.last_error_code == "CAPABILITY_UNAVAILABLE"
    assert saved_a.last_error_message == "H2B_PASS_AWAITING_H2C"
    # No manual rerun ("retry-" prefixed) job exists for the capability video,
    # while the ordinary eligible job retains its normal retry behavior.
    import sqlite3

    connection = sqlite3.connect(repository._database_path)
    try:
        retry_rows = connection.execute(
            "SELECT video_id FROM jobs WHERE job_id LIKE 'retry-%'"
        ).fetchall()
    finally:
        connection.close()
    assert [row[0] for row in retry_rows] == [video_b]


def test_repeated_retry_of_capability_terminal_stays_candidate_free(
    tmp_path: Path,
) -> None:
    runtime, job = _terminal_job(
        tmp_path,
        error_code="CAPABILITY_UNAVAILABLE",
        message="H2B_PASS_AWAITING_H2C",
    )

    for _ in range(3):
        outcome = runtime.retry(video=None, failed_only=False)
        assert outcome.safe_message == (
            "No final failed video job is available to retry."
        )

    assert runtime._repository.latest_video_job(
        _FLOW.VIDEO_ID, target_stage=ProcessingStage.SCORING
    ).job_id == job.job_id


# ---------------------------------------------------------------------------
# Direct persistence rejection of constructed aggregates (lexical lifetime)
# ---------------------------------------------------------------------------


def _constructed_aggregate(tmp_path: Path) -> tuple[Any, PhaseH2BValidatedRepairResult]:
    """Build a valid-shaped aggregate via the pure finalizer chain support."""

    support = _load_support(
        "_h2b_final_correction_finalizer_support",
        "test_task016c_phase_h2b_correction_finalizer.py",
    )
    chain = support._valid_chain()
    output = support._finalize(chain)
    from youtube_intel.h2_evidence import h2_canonical_bytes

    aggregate = PhaseH2BValidatedRepairResult(
        primary_trusted_context=chain["trusted_context"],
        primary_failure_evidence=chain["pfe"],
        failure_class=chain["pfe"].failure_class,
        repair_normalized_input=chain["rni"],
        repair_normalized_input_bytes=h2_canonical_bytes(chain["rni"]),
        rni_hash=chain["rni_hash"],
        repair_request_hash=chain["repair_request_hash"],
        repair_prompt="prompt_version: scoring-prompt-v2\nconstructed",
        repair_payload_bytes=b'{"prompt":"x"}',
        repair_payload_sha256=hashlib.sha256(b'{"prompt":"x"}').hexdigest(),
        repair_payload_length=len(b'{"prompt":"x"}'),
        repair_raw_utf8=chain["pfe"].primary_raw_utf8,
        repair_raw_sha256=chain["pfe"].primary_raw_sha256,
        repair_raw_length=chain["pfe"].primary_raw_utf8_length,
        repair_model_content="{not-json",
        repaired_candidate=chain["candidate"],
        repaired_candidate_hash=chain["judge_input"].candidate_hash,
        language_evidence=support._load_h2a_support().replay_language_validation(
            candidate=chain["candidate"], output_language="en"
        ),
        quality_input_hash=chain["judge_ctx"].quality_input_hash,
        deterministic_gate_status="PASS",
        judge_operation_input=chain["judge_ctx"].operation_input,
        judge_input=chain["judge_input"],
        judge_h1=chain["judge_ctx"].expected_h1,
        judge_h2=chain["judge_ctx"].expected_h2,
        judge_evidence=chain["judge_evidence"],
        judge_raw_utf8=chain["judge_raw"],
        judge_raw_sha256=hashlib.sha256(chain["judge_raw"].encode("utf-8")).hexdigest(),
        judge_raw_length=len(chain["judge_raw"].encode("utf-8")),
        judge_result=chain["judge_result"],
        attestation=chain["attestation"],
        finalizer_trusted_result=output.trusted_result,
        structured_result_bytes=output.structured_bytes,
        structured_result_sha256=output.structured_sha256,
        structured_result_length=output.structured_length,
        structured_result_schema_version=output.trusted_result.result.schema_version,
        structured_result_prompt_version=output.trusted_result.result.prompt_version,
        model=chain["settings"].model,
        model_digest=chain["settings"].expected_model_digest,
        prompt_version="scoring-prompt-v2",
        schema_version="score-result-v2",
        policy_version="content-quality-policy-v1",
        quality_prompt_version="content-quality-prompt-v1",
        quality_schema_version="content-quality-result-v1",
        temperature=chain["settings"].temperature,
        max_output_tokens=chain["settings"].max_output_tokens,
        max_description_chars=chain["settings"].max_description_chars,
    )
    runtime = _FLOW._runtime(tmp_path, _FLOW._FakeTransport([]))
    return runtime, aggregate


def test_direct_persistence_of_valid_aggregate_still_rejects(tmp_path: Path) -> None:
    runtime, aggregate = _constructed_aggregate(tmp_path)
    entry = runtime._trusted_persistence_entry(
        job_id="scoring-job", owner=runtime._runtime_owner, pipeline_version="runtime-v1"
    )

    with pytest.raises((ValueError, TypeError)):
        entry.persist_success(aggregate)  # type: ignore[arg-type]

    assert (
        runtime._repository.latest_artifact(
            _FLOW.VIDEO_ID, ArtifactKind.SCORING_STRUCTURED
        )
        is None
    )


def test_forged_aggregates_still_cannot_gain_persistence_authority(
    tmp_path: Path,
) -> None:
    import copy
    import pickle

    runtime, aggregate = _constructed_aggregate(tmp_path)
    entry = runtime._trusted_persistence_entry(
        job_id="scoring-job", owner=runtime._runtime_owner, pipeline_version="runtime-v1"
    )

    forged_new = object.__new__(PhaseH2BValidatedRepairResult)
    mutated = copy.copy(aggregate)
    object.__setattr__(mutated, "repair_request_hash", "f" * 64)
    structured_mutated = copy.copy(aggregate)
    object.__setattr__(structured_mutated, "structured_result_sha256", "e" * 64)
    for candidate in (forged_new, mutated, structured_mutated):
        with pytest.raises((ValueError, TypeError, AttributeError)):
            entry.persist_success(candidate)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        copy.deepcopy(aggregate)
    with pytest.raises(TypeError):
        pickle.dumps(aggregate)


# ---------------------------------------------------------------------------
# ErrorCode boundary consumers
# ---------------------------------------------------------------------------


def test_subtitle_boundary_maps_capability_unavailable_safely() -> None:
    from youtube_intel.providers.subtitles import _safe_boundary_error

    failure = _safe_boundary_error(
        AppError(
            code=ErrorCode.CAPABILITY_UNAVAILABLE,
            message="H2B_PASS_AWAITING_H2C",
            retryable=False,
            stage=ProcessingStage.TRANSCRIPT,
        ),
        subject="selected subtitle body",
        video_id=None,
    )
    assert failure.error.code is ErrorCode.CAPABILITY_UNAVAILABLE
    assert (
        failure.error.message
        == "selected subtitle body required capability unavailable in this build"
    )
    assert failure.error.retryable is False


def test_subtitle_boundary_local_resource_mapping_is_unchanged() -> None:
    from youtube_intel.providers.subtitles import _safe_boundary_error

    failure = _safe_boundary_error(
        AppError(
            code=ErrorCode.LOCAL_RESOURCE,
            message="disk",
            retryable=True,
            stage=ProcessingStage.TRANSCRIPT,
        ),
        subject="selected subtitle body",
        video_id=None,
    )
    assert failure.error.code is ErrorCode.LOCAL_RESOURCE
    assert failure.error.message == "selected subtitle body local resource failed"


def test_transcript_boundary_maps_capability_unavailable_safely() -> None:
    from youtube_intel.transcripts import _adapter_boundary_error

    mapped = _adapter_boundary_error(
        AppError(
            code=ErrorCode.CAPABILITY_UNAVAILABLE,
            message="H2B_PASS_AWAITING_H2C",
            retryable=False,
            stage=ProcessingStage.TRANSCRIPT,
        ),
        operation="track enumeration",
        video_id="video-1",
    )
    assert mapped.code is ErrorCode.CAPABILITY_UNAVAILABLE
    assert mapped.message == (
        "subtitle adapter required capability unavailable in this build "
        "during track enumeration"
    )
    assert mapped.retryable is False


def test_transcript_boundary_local_resource_mapping_is_unchanged() -> None:
    from youtube_intel.transcripts import _adapter_boundary_error

    mapped = _adapter_boundary_error(
        AppError(
            code=ErrorCode.LOCAL_RESOURCE,
            message="disk",
            retryable=True,
            stage=ProcessingStage.TRANSCRIPT,
        ),
        operation="body read",
        video_id="video-1",
    )
    assert mapped.code is ErrorCode.LOCAL_RESOURCE
    assert mapped.message == "subtitle adapter local resource failed during body read"
