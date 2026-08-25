"""TASK-016C Phase H2-B correction — authority and gate RED tests.

Frozen correction objectives (Round 4 authorization):

- the generic identity+closure dispatch authority
  (``_consume_runtime_role_and_dispatch``) is removed; ``ScoringDispatchAdmission``
  is state/policy enforcement only, with state-only REPAIR role consumption
  that accepts no caller callback and returns nothing;
- no caller-triggerable authoritative ``_h2b_execute_repair``-style ingress
  exists; the actual ``RuntimeOperations`` PRIMARY execution frame is the sole
  authoritative H2-B owner, so a forged self-consistent PFE cannot trigger a
  REPAIR even after a genuine PRIMARY consumption;
- the repaired candidate must pass the accepted deterministic Content Quality
  gate (``CONTROL_CHARACTER_INVALID`` / ``EXACT_REPETITION`` are reachable
  terminal rejects; empty/whitespace content fails schema/parse before the
  gate and ``EMPTY_CONTENT`` is unreachable post-schema);
- a successful H2-B carries the finalizer-produced ``TrustedScoreResult`` and
  sealed structured bytes/SHA-256/length; a deterministic finalizer failure
  terminalizes exactly once as ``REPAIR_FINALIZATION_INVALID``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import sys
import types
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from youtube_intel.domain import JobStatus
from youtube_intel.quality import (
    RepairFinalizationInvalid,
    TrustedScoreResult,
    build_content_quality_input_hash,
)
from youtube_intel.scoring import _sealed_trusted_score_result_serializer
from youtube_intel.scoring_admission import (
    ScoringDispatchAdmission,
    ScoringDispatchDenied,
    ScoringDispatchIdentity,
    ScoringDispatchRole,
)


def _load_flow_support() -> Any:
    support_path = Path(__file__).with_name("test_task016c_phase_h2b_repair_flow.py")
    specification = importlib.util.spec_from_file_location(
        "_h2b_correction_flow_support", support_path
    )
    assert specification is not None and specification.loader is not None
    support = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = support
    specification.loader.exec_module(support)
    return support


_FLOW = _load_flow_support()


def _annotation_accepts_callable(annotation: object) -> bool:
    origin = getattr(annotation, "__origin__", None)
    return origin is Callable or annotation is Callable


# ---------------------------------------------------------------------------
# Generic callback dispatch authority is gone (REPAIR and REPAIR_JUDGE)
# ---------------------------------------------------------------------------


def test_admission_surface_is_state_only_with_no_callback_dispatch() -> None:
    forbidden = (
        "_consume_runtime_role_and_dispatch",
        "consume_runtime_role_and_dispatch",
        "admit_and_dispatch",
        "consume_repair_and_dispatch",
        "consume_repair_dispatch",
        "dispatch_after_admission",
        "admit_then_run",
        "consume_role_and_dispatch",
    )
    for name in forbidden:
        assert not hasattr(ScoringDispatchAdmission, name), name

    # No admission operation may accept executable work (a Callable parameter):
    # the semantic surface is gone, not merely underscore-prefixed.
    for name in dir(ScoringDispatchAdmission):
        if name.startswith("__"):
            continue
        attribute = getattr(ScoringDispatchAdmission, name)
        if not isinstance(attribute, types.FunctionType):
            continue
        for parameter in inspect.signature(attribute).parameters.values():
            assert not _annotation_accepts_callable(parameter.annotation), (
                f"ScoringDispatchAdmission.{name} accepts executable work"
            )

    # The retained state-only REPAIR operations exist and return nothing.
    assert hasattr(ScoringDispatchAdmission, "consume_repair_role")
    assert hasattr(ScoringDispatchAdmission, "consume_repair_judge_role")


def test_no_repair_executor_or_h2c_ingress_exists_on_the_runtime() -> None:
    from youtube_intel.runtime import RuntimeOperations

    forbidden = (
        "_h2b_execute_repair",
        "execute_repair",
        "run_repair",
        "repair",
        "dispatch_repair",
        "repair_dispatch",
        "_primary_failure_continuation",
        "_admit_runtime_repair",
        "finalize_repair",
        "h2c_finalize",
        "mint_repair_success",
        "persist_validated_repair",
        "verify_h2b_result",
        "mint_phase_h_success",
        "persist_repair",
    )
    for name in forbidden:
        assert not hasattr(RuntimeOperations, name), name


# ---------------------------------------------------------------------------
# State-only REPAIR role consumption semantics
# ---------------------------------------------------------------------------


def _repair_identity(suffix: str = "a") -> ScoringDispatchIdentity:
    return ScoringDispatchIdentity(
        role=ScoringDispatchRole.REPAIR,
        operation="local-scoring-repair-v1",
        normalized_input_hash=suffix * 64,
        request_hash=suffix * 64,
    )


def _repair_judge_identity(suffix: str = "j") -> ScoringDispatchIdentity:
    return ScoringDispatchIdentity(
        role=ScoringDispatchRole.REPAIR_JUDGE,
        operation="local-content-quality-v1",
        normalized_input_hash=suffix * 64,
        request_hash=suffix * 64,
    )


def _primary_identity() -> ScoringDispatchIdentity:
    return ScoringDispatchIdentity(
        role=ScoringDispatchRole.PRIMARY,
        operation="local-scoring",
        normalized_input_hash="p" * 64,
        request_hash="p" * 64,
    )


def _live_runtime(tmp_path: Path) -> Any:
    runtime = _FLOW._runtime(tmp_path, _FLOW._FakeTransport([]))
    repository = runtime._repository
    repository.save_discovery_batch(
        _FLOW.DiscoveryBatch(
            channel_id=_FLOW.CHANNEL_ID,
            video_ids=(_FLOW.VIDEO_ID,),
            next_cursor=_FLOW.DiscoveryCursor(
                channel_id=_FLOW.CHANNEL_ID,
                last_checked_at=_FLOW.NOW,
                latest_published_at=_FLOW.NOW,
                latest_video_id=_FLOW.VIDEO_ID,
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
        _FLOW.VIDEO_ID,
        expected_status=_FLOW.PipelineStatus.DISCOVERED,
        target_status=_FLOW.PipelineStatus.METADATA_READY,
        pipeline_version="runtime-v1",
        now=_FLOW.NOW,
    )
    repository.advance_pipeline(
        _FLOW.VIDEO_ID,
        expected_status=_FLOW.PipelineStatus.METADATA_READY,
        target_status=_FLOW.PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="runtime-v1",
        now=_FLOW.NOW,
    )
    repository.create_job(
        job_id="scoring-job",
        scope_key=f"video:{_FLOW.VIDEO_ID}:SCORING",
        video_id=_FLOW.VIDEO_ID,
        job_type=_FLOW.JobType.VIDEO_STAGE,
        target_stage=_FLOW.ProcessingStage.SCORING,
        pipeline_version="runtime-v1",
        max_attempts=3,
        available_at=_FLOW.NOW,
        now=_FLOW.NOW,
    )
    claimed = repository.claim_next_job(
        owner=runtime._runtime_owner,
        lease_until=_FLOW.NOW + _FLOW.timedelta(minutes=5),
        now=_FLOW.NOW,
    )
    assert claimed is not None
    admission = runtime._scoring_admission_for(claimed.job_id)
    admission.admit(_primary_identity(), now=_FLOW.NOW)
    return runtime, admission


def test_consume_repair_role_is_state_only_and_requires_primary(tmp_path: Path) -> None:
    # Before PRIMARY consumption the REPAIR role is denied.
    early_runtime = _FLOW._runtime(tmp_path / "early", _FLOW._FakeTransport([]))
    early_admission = early_runtime._scoring_admission_for("missing-job")
    with pytest.raises(ScoringDispatchDenied):
        early_admission.consume_repair_role(_repair_identity(), now=datetime.now(UTC))

    _, admission = _live_runtime(tmp_path)
    # The state-only operation returns None and executes no caller work: there
    # is simply no callback parameter to supply.
    assert admission.consume_repair_role(_repair_identity(), now=_FLOW.NOW) is None
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_role(_repair_identity("b"), now=_FLOW.NOW)


def test_consume_repair_judge_role_requires_consumed_repair(tmp_path: Path) -> None:
    _, admission = _live_runtime(tmp_path)
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_judge_role(_repair_judge_identity(), now=_FLOW.NOW)
    admission.consume_repair_role(_repair_identity(), now=_FLOW.NOW)
    assert (
        admission.consume_repair_judge_role(_repair_judge_identity(), now=_FLOW.NOW)
        is None
    )
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_judge_role(_repair_judge_identity("k"), now=_FLOW.NOW)


def test_consume_repair_role_enforces_frozen_role_and_operation_literals(
    tmp_path: Path,
) -> None:
    _, admission = _live_runtime(tmp_path)
    wrong_role = ScoringDispatchIdentity(
        role=ScoringDispatchRole.PRIMARY,
        operation="local-scoring-repair-v1",
        normalized_input_hash="a" * 64,
        request_hash="a" * 64,
    )
    wrong_operation = ScoringDispatchIdentity(
        role=ScoringDispatchRole.REPAIR,
        operation="local-scoring",
        normalized_input_hash="a" * 64,
        request_hash="a" * 64,
    )
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_role(wrong_role, now=_FLOW.NOW)
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_role(wrong_operation, now=_FLOW.NOW)
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_judge_role(
            ScoringDispatchIdentity(
                role=ScoringDispatchRole.REPAIR_JUDGE,
                operation="local-scoring-repair-v1",
                normalized_input_hash="j" * 64,
                request_hash="j" * 64,
            ),
            now=_FLOW.NOW,
        )


def test_public_admit_still_rejects_repair_roles(tmp_path: Path) -> None:
    _, admission = _live_runtime(tmp_path)
    for identity in (_repair_identity(), _repair_judge_identity()):
        with pytest.raises(ScoringDispatchDenied):
            admission.admit(identity, now=_FLOW.NOW)


def test_concurrent_repair_consumption_has_one_winner_and_zero_contact(
    tmp_path: Path,
) -> None:
    runtime, _ = _live_runtime(tmp_path)

    def attempt() -> str:
        try:
            runtime._scoring_admission_for("scoring-job").consume_repair_role(
                _repair_identity("c"), now=_FLOW.NOW
            )
        except ScoringDispatchDenied:
            return "denied"
        return "consumed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = set(executor.map(lambda _: attempt(), (0, 1)))

    # Exactly one concurrent consumer wins the one-shot role; the loser is
    # denied.  No dispatch authority exists anywhere, so role consumption alone
    # can never cause external contact.
    assert results == {"consumed", "denied"}


# ---------------------------------------------------------------------------
# Forged PFE after a genuine PRIMARY consumption cannot trigger REPAIR
# ---------------------------------------------------------------------------


def test_forged_pfe_after_genuine_primary_cannot_trigger_repair(tmp_path: Path) -> None:
    # A deterministic-gate PRIMARY failure is consumed but NOT repair-eligible:
    # PRIMARY is genuinely consumed, REPAIR is not, and the job terminalizes.
    gate_reject_reason = (
        "This primary response repeats itself exactly for the gate to reject.\n"
        "This primary response repeats itself exactly for the gate to reject."
    )
    transport = _FLOW._FakeTransport(
        [_FLOW._tags(), _FLOW._outer(_FLOW._valid_candidate(reason=gate_reject_reason))]
    )
    runtime = _FLOW._runtime(tmp_path, transport)
    _FLOW._run_process(runtime)
    job = _FLOW._scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert transport.tags_calls == 1
    assert transport.generate_calls == 1
    assert runtime._last_h2b_validated_repair_result is None

    # Attacker constructs a self-consistent eligible PFE B unrelated to the
    # actual PRIMARY evidence, then attempts to use it to trigger repair.
    support = _load_h2a_support()
    from youtube_intel.h2_evidence import (
        build_primary_trusted_context,
        verify_primary_failure_evidence,
    )

    scoring_input = support._scoring_input()
    ctx = build_primary_trusted_context(
        scoring_input=scoring_input,
        model=_FLOW.MODEL,
        model_digest=_FLOW.DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
    )
    forged_pfe = support._schema_invalid_pfe(ctx, scoring_input)
    verify_primary_failure_evidence(
        forged_pfe, ctx, runtime._config.settings.local_scoring
    )

    # There is no authoritative H2-B ingress: no runtime method accepts a PFE
    # and performs provider contact, and the admission view cannot dispatch.
    assert not hasattr(runtime, "_h2b_execute_repair")
    admission = runtime._scoring_admission_for(job.job_id)
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_role(_repair_identity("f"), now=datetime.now(UTC))

    # Zero REPAIR external transport was caused by B.
    assert transport.tags_calls == 1
    assert transport.generate_calls == 1
    assert runtime._last_h2b_validated_repair_result is None


def _load_h2a_support() -> Any:
    support_path = Path(__file__).with_name("test_task016c_phase_h2a_evidence.py")
    specification = importlib.util.spec_from_file_location(
        "_h2b_correction_h2a_support", support_path
    )
    assert specification is not None and specification.loader is not None
    support = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = support
    specification.loader.exec_module(support)
    return support


# ---------------------------------------------------------------------------
# Deterministic Content Quality gate on the production REPAIR path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "repair_inner",
    [
        "",  # empty repaired content
        "   \t\n  ",  # whitespace-only repaired content
        "\t\n",  # tab/newline-only repaired content
        _FLOW._valid_candidate(reason="   "),  # stripped-empty candidate reason
    ],
    ids=["empty", "whitespace", "tab-newline", "stripped-empty-reason"],
)
def test_empty_repaired_content_is_schema_terminal_with_zero_judge(
    tmp_path: Path, repair_inner: str
) -> None:
    # Empty/whitespace required textual content fails schema/parse BEFORE the
    # deterministic gate: no language continuation, no gate progression, no
    # Judge, no second REPAIR, no persistence.
    transport = _FLOW._FakeTransport(
        _FLOW._repair_script(
            primary_inner="{not-json",
            repair_inner=repair_inner,
            judge_status="PASS",  # scripted but must never be contacted
        )
    )
    runtime = _FLOW._runtime(tmp_path, transport)

    _FLOW._run_process(runtime)

    job = _FLOW._scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "INVALID_RESPONSE"
    assert job.last_error_message == "REPAIR_SCHEMA_OR_PARSE_INVALID"
    assert transport.tags_calls == 2
    assert transport.generate_calls == 2  # zero Judge transport
    assert runtime._last_h2b_validated_repair_result is None
    assert len(runtime._repository.list_job_attempts(job.job_id)) == 1


@pytest.mark.parametrize(
    "reason,expected_message",
    [
        (
            "This repaired response explains a concrete product strategy clearly.\u000b"
            "It adds one more complete sentence afterwards for grounding.",
            "REPAIR_DETERMINISTIC_GATE_REJECT:CONTROL_CHARACTER_INVALID",
        ),
        (
            "This repaired response explains a concrete product strategy clearly.\n"
            "This repaired response explains a concrete product strategy clearly.",
            "REPAIR_DETERMINISTIC_GATE_REJECT:EXACT_REPETITION",
        ),
    ],
    ids=["control-character", "exact-repetition"],
)
def test_gate_reject_is_terminal_with_zero_judge_even_with_scripted_pass(
    tmp_path: Path, reason: str, expected_message: str
) -> None:
    # A forged/prebuilt Judge PASS cannot rescue a deterministic gate reject:
    # the scripted Judge responses are never consumed.
    transport = _FLOW._FakeTransport(
        _FLOW._repair_script(
            primary_inner="{not-json",
            repair_inner=_FLOW._valid_candidate(reason=reason),
            judge_status="PASS",
        )
    )
    runtime = _FLOW._runtime(tmp_path, transport)

    _FLOW._run_process(runtime)

    job = _FLOW._scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "INVALID_RESPONSE"
    assert job.last_error_message == expected_message
    assert transport.tags_calls == 2
    assert transport.generate_calls == 2  # zero REPAIR Judge contact
    assert runtime._last_h2b_validated_repair_result is None
    assert len(runtime._repository.list_job_attempts(job.job_id)) == 1
    # The scripted Judge transport entries were never invoked.
    assert len(transport._responses) == 2


def test_gate_pass_repair_reaches_judge_with_finalized_trusted_evidence(
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

    aggregate = runtime._last_h2b_validated_repair_result
    assert aggregate is not None
    assert transport.tags_calls == 3
    assert transport.generate_calls == 3

    # Deterministic gate PASS evidence.
    assert aggregate.deterministic_gate_status == "PASS"
    assert aggregate.quality_input_hash == build_content_quality_input_hash(
        aggregate.judge_input
    )
    assert aggregate.judge_input.scoring_request_hash == aggregate.repair_request_hash

    # Finalizer-produced TrustedScoreResult with the dual binding.
    trusted_result = aggregate.finalizer_trusted_result
    assert type(trusted_result) is TrustedScoreResult
    primary_context = aggregate.primary_trusted_context
    assert trusted_result.result.request_hash == primary_context.request_hash
    assert trusted_result.result.request_hash != aggregate.repair_request_hash
    assert trusted_result.result.score == aggregate.repaired_candidate.score

    # Sealed structured bytes/hash/length are exact and reproducible.
    assert aggregate.structured_result_length == len(aggregate.structured_result_bytes)
    assert aggregate.structured_result_sha256 == hashlib.sha256(
        aggregate.structured_result_bytes
    ).hexdigest()
    assert aggregate.structured_result_bytes == _sealed_trusted_score_result_serializer(
        trusted_result
    )
    assert aggregate.structured_result_schema_version == (
        trusted_result.result.schema_version
    )
    assert aggregate.structured_result_prompt_version == (
        trusted_result.result.prompt_version
    )
    # The RNI canonical bytes are bound alongside the hash.
    from youtube_intel.h2_evidence import h2_canonical_bytes

    assert aggregate.repair_normalized_input_bytes == h2_canonical_bytes(
        aggregate.repair_normalized_input
    )


def test_finalizer_failure_maps_to_repair_finalization_invalid_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import youtube_intel.runtime as runtime_module

    class _ExplodingFinalizer:
        def finalize(self, **_kwargs: object) -> object:
            raise RepairFinalizationInvalid("injected deterministic finalizer failure")

    monkeypatch.setattr(runtime_module, "RepairTrustedScoringFinalizer", _ExplodingFinalizer)

    transport = _FLOW._FakeTransport(
        _FLOW._repair_script(
            primary_inner="{not-json",
            repair_inner=_FLOW._valid_candidate(),
            judge_status="PASS",
        )
    )
    runtime = _FLOW._runtime(tmp_path, transport)

    _FLOW._run_process(runtime)

    job = _FLOW._scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "INVALID_RESPONSE"
    assert job.last_error_message == "REPAIR_FINALIZATION_INVALID"
    assert job.last_error_code != "UNKNOWN_PROVIDER_STATE"
    assert transport.tags_calls == 3
    assert transport.generate_calls == 3  # no second REPAIR/Judge
    assert runtime._last_h2b_validated_repair_result is None
    # fail_job exactly once: a single attempt row, no duplicate generic _fail.
    attempts = runtime._repository.list_job_attempts(job.job_id)
    assert len(attempts) == 1
    assert attempts[0].error_message == "REPAIR_FINALIZATION_INVALID"


# ---------------------------------------------------------------------------
# Candidate equality != provenance equality
# ---------------------------------------------------------------------------


def test_identical_repaired_candidates_keep_distinct_provenance(tmp_path: Path) -> None:
    def run(primary_inner: str) -> Any:
        transport = _FLOW._FakeTransport(
            _FLOW._repair_script(
                primary_inner=primary_inner,
                repair_inner=_FLOW._valid_candidate(),
                judge_status="PASS",
            )
        )
        runtime = _FLOW._runtime(tmp_path / primary_inner.replace("{", "o"), transport)
        _FLOW._run_process(runtime)
        aggregate = runtime._last_h2b_validated_repair_result
        assert aggregate is not None
        return aggregate

    first = run("{not-json")
    second = run("[1,2]")

    assert first.repaired_candidate == second.repaired_candidate
    assert first.repaired_candidate_hash == second.repaired_candidate_hash
    # Different PRIMARY failure evidence changes the RNI and every REPAIR
    # transport/Judge identity, so the evidence graphs remain distinct.
    assert first.primary_failure_evidence != second.primary_failure_evidence
    assert first.repair_request_hash != second.repair_request_hash
    assert first.rni_hash != second.rni_hash
    assert first.judge_h1 != second.judge_h1
    assert first.judge_h2 != second.judge_h2
    assert first.repair_payload_bytes != second.repair_payload_bytes


# ---------------------------------------------------------------------------
# Structured evidence mutation cannot become persistence authority
# ---------------------------------------------------------------------------


def test_mutated_structured_evidence_cannot_gain_persistence_authority(
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
    aggregate = runtime._last_h2b_validated_repair_result
    assert aggregate is not None
    entry = runtime._trusted_persistence_entry(
        job_id="scoring-job", owner=runtime._runtime_owner, pipeline_version="runtime-v1"
    )

    # Frozen slots dataclass: clone via shallow copy, then mutate one field at
    # a time; none of the mutations may become persistence authority.
    import copy as _copy

    for field_name, mutated_value in (
        ("structured_result_bytes", aggregate.structured_result_bytes + b" "),
        ("structured_result_sha256", "f" * 64),
        ("structured_result_length", aggregate.structured_result_length + 1),
        ("structured_result_schema_version", "forged-schema-v9"),
        ("repair_request_hash", "e" * 64),
    ):
        clone = _copy.copy(aggregate)
        object.__setattr__(clone, field_name, mutated_value)
        with pytest.raises((ValueError, TypeError, AttributeError)):
            entry.persist_success(clone)  # type: ignore[arg-type]

    # Direct persistence of the untouched corrected aggregate still rejects.
    with pytest.raises((ValueError, TypeError)):
        entry.persist_success(aggregate)  # type: ignore[arg-type]
