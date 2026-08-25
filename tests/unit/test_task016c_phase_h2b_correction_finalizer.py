"""TASK-016C Phase H2-B correction — RepairTrustedScoringFinalizer RED tests.

Frozen correction objectives (Round 4 authorization, sections 20 and 23-32 of
the correction mandate): the separate ``RepairTrustedScoringFinalizer`` lives in
``quality.py``, fresh-revalidates every input (low-level construction bypasses
are re-run through strict validation), independently reruns the accepted
deterministic Content Quality gate, replays the REPAIR Judge raw, re-verifies
the attestation against the current runtime authority, enforces the dual
binding (PRIMARY semantic score identity + REPAIR transport provenance), and
only then produces the exact ``TrustedScoreResult`` plus the sealed structured
bytes/SHA-256/length through the unchanged frozen serializer.

Judge PASS, attestation, or any caller-provided claim can never rescue a
deterministic gate rejection or an identity mismatch.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    ContentQualityStatus,
    ScoringCandidate,
)
from youtube_intel.h2_evidence import (
    PrimaryFailureEvidence,
    RepairNormalizedInput,
    build_judge_evidence,
    build_primary_trusted_context,
    build_repair_normalized_input,
    build_repair_request_hash,
    derive_repair_judge_trusted_context,
    repair_normalized_input_hash,
    verify_primary_failure_evidence,
)
from youtube_intel.providers.ollama import verify_judge_model_content
from youtube_intel.quality import (
    _JUDGE_PROVIDER,
    _QUALITY_JUDGE_OPERATION,
    _QUALITY_POLICY_VERSION,
    _QUALITY_PROMPT_VERSION,
    _QUALITY_PROVENANCE_AUTHORITY_SENTINEL,
    _QUALITY_SCHEMA_VERSION,
    _SCORING_PROMPT_VERSION,
    _SCORING_SCHEMA_VERSION,
    _TRUSTED_SCORING_CONTEXT_SENTINEL,
    DeterministicContentQualityGate,
    QualityProvenanceAuthority,
    RepairFinalizationInvalid,
    RepairFinalizerOutput,
    RepairTrustedScoringFinalizer,
    TrustedScoreResult,
    TrustedScoringContext,
    _mint_quality_provenance_authority,
    _mint_trusted_scoring_context,
    build_content_quality_input_hash,
    build_quality_pass_attestation,
    build_scoring_candidate_hash,
)
from youtube_intel.scoring import _sealed_trusted_score_result_serializer

_MODEL = "qwen3:8b"
_DIGEST = "sha256:" + "a" * 64
_EN_REASON = "This repaired response explains a concrete product strategy clearly."
_CONTROL_REASON = (
    "This repaired response explains a concrete product strategy clearly.\u000b"
    "It adds one more complete sentence afterwards for grounding."
)
_REPETITION_REASON = (
    "This repaired response explains a concrete product strategy clearly.\n"
    "This repaired response explains a concrete product strategy clearly."
)


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


def _settings() -> LocalScoringSettings:
    return LocalScoringSettings(
        model=_MODEL,
        expected_model_digest=_DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_transcript_chars=64,
        max_description_chars=32,
    )


def _authority() -> QualityProvenanceAuthority:
    return _mint_quality_provenance_authority(
        sentinel=_QUALITY_PROVENANCE_AUTHORITY_SENTINEL,
        judge_provider=_JUDGE_PROVIDER,
        judge_model=_MODEL,
        judge_model_digest=_DIGEST,
        scoring_schema_version=_SCORING_SCHEMA_VERSION,
        scoring_prompt_version=_SCORING_PROMPT_VERSION,
        quality_policy_version=_QUALITY_POLICY_VERSION,
        quality_schema_version=_QUALITY_SCHEMA_VERSION,
        quality_prompt_version=_QUALITY_PROMPT_VERSION,
        judge_operation=_QUALITY_JUDGE_OPERATION,
    )


def _scoring_context() -> TrustedScoringContext:
    return _mint_trusted_scoring_context(
        sentinel=_TRUSTED_SCORING_CONTEXT_SENTINEL,
        scoring_provider=_JUDGE_PROVIDER,
        scoring_model=_MODEL,
        scoring_model_digest=_DIGEST,
        output_language="en",
        scoring_schema_version=_SCORING_SCHEMA_VERSION,
        scoring_prompt_version=_SCORING_PROMPT_VERSION,
        scoring_operation="local-scoring",
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
    )


def _judge_pass_raw() -> str:
    return json.dumps(
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


def _valid_chain(reason: str = _EN_REASON) -> dict[str, Any]:
    """Build one complete self-consistent REPAIR finalization input chain."""

    support = _load_h2a_support()
    scoring_input = support._scoring_input()
    settings = _settings()
    trusted_context = build_primary_trusted_context(
        scoring_input=scoring_input,
        model=_MODEL,
        model_digest=_DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
    )
    pfe: PrimaryFailureEvidence = support._schema_invalid_pfe(
        trusted_context, scoring_input
    )
    verify_primary_failure_evidence(pfe, trusted_context, settings)
    rni = build_repair_normalized_input(
        job_id="correction-job",
        primary_trusted_context=trusted_context,
        failure_evidence=pfe,
        validated_settings=settings,
    )
    rni_hash = repair_normalized_input_hash(rni)
    repair_request_hash = build_repair_request_hash(rni)
    candidate = ScoringCandidate.model_validate(
        {"score": 8, "reason": reason, "topics": ["product"], "should_summarize": True}
    )
    judge_ctx, judge_input = derive_repair_judge_trusted_context(
        repair_request_hash=repair_request_hash,
        trusted_candidate=candidate,
        scoring_input=scoring_input,
        validated_settings=settings,
    )
    judge_raw = _judge_pass_raw()
    judge_result = verify_judge_model_content(
        judge_raw,
        operation_input=judge_ctx.operation_input,
        content_input=judge_input,
    )
    assert judge_result.status is ContentQualityStatus.PASS
    judge_evidence = build_judge_evidence(
        role="REPAIR",
        operation_input=judge_ctx.operation_input,
        judge_input=judge_input,
        raw_utf8=judge_raw,
        model=_MODEL,
        model_digest=_DIGEST,
        policy_version=_QUALITY_POLICY_VERSION,
        prompt_version=_QUALITY_PROMPT_VERSION,
        operation_schema_version=_QUALITY_SCHEMA_VERSION,
    )
    authority = _authority()
    attestation = build_quality_pass_attestation(
        quality_result=judge_result,
        operation_input=judge_ctx.operation_input,
        quality_input=judge_input,
        authority=authority,
    )
    return {
        "scoring_input": scoring_input,
        "trusted_context": trusted_context,
        "pfe": pfe,
        "rni": rni,
        "rni_hash": rni_hash,
        "repair_request_hash": repair_request_hash,
        "candidate": candidate,
        "judge_ctx": judge_ctx,
        "judge_input": judge_input,
        "judge_raw": judge_raw,
        "judge_result": judge_result,
        "judge_evidence": judge_evidence,
        "authority": authority,
        "attestation": attestation,
        "settings": settings,
    }


def _finalize(chain: dict[str, Any], **overrides: Any) -> RepairFinalizerOutput:
    inputs: dict[str, Any] = {
        "candidate": chain["candidate"],
        "scoring_input": chain["scoring_input"],
        "repair_normalized_input": chain["rni"],
        "rni_hash": chain["rni_hash"],
        "repair_request_hash": chain["repair_request_hash"],
        "quality_input": chain["judge_input"],
        "quality_result": chain["judge_result"],
        "quality_operation": chain["judge_ctx"].operation_input,
        "judge_evidence": chain["judge_evidence"],
        "attestation": chain["attestation"],
        "quality_authority": chain["authority"],
        "scoring_context": _scoring_context(),
        "validated_settings": chain["settings"],
    }
    inputs.update(overrides)
    return RepairTrustedScoringFinalizer().finalize(**inputs)


# ---------------------------------------------------------------------------
# Valid chain -> TrustedScoreResult + sealed structured evidence
# ---------------------------------------------------------------------------


def test_valid_repair_chain_yields_trusted_result_and_sealed_structured_evidence() -> None:
    chain = _valid_chain()

    output = _finalize(chain)

    assert type(output) is RepairFinalizerOutput
    assert type(output.trusted_result) is TrustedScoreResult
    # Dual binding: the semantic score remains bound to the PRIMARY request.
    assert (
        output.trusted_result.result.request_hash
        == chain["trusted_context"].request_hash
    )
    assert output.trusted_result.result.request_hash != chain["repair_request_hash"]
    assert output.trusted_result.result.score == chain["candidate"].score
    assert output.trusted_result.result.reason == chain["candidate"].reason
    # Sealed structured evidence is exact and self-consistent.
    assert output.structured_length == len(output.structured_bytes)
    assert output.structured_sha256 == hashlib.sha256(output.structured_bytes).hexdigest()
    assert output.structured_bytes == _sealed_trusted_score_result_serializer(
        output.trusted_result
    )
    reparsed = json.loads(output.structured_bytes.decode("utf-8"))
    assert reparsed["request_hash"] == chain["trusted_context"].request_hash


def test_trusted_score_result_wrapper_is_not_copyable_or_assignable() -> None:
    chain = _valid_chain()
    output = _finalize(chain)

    # Ordinary assignment and copy/deepcopy/pickle are refused by the opaque
    # wrapper.  object.__setattr__ inside the same process is not a boundary:
    # persistence/H2-C replay revalidate rather than trust the wrapper.
    with pytest.raises(TypeError):
        output.trusted_result.result = None  # type: ignore[misc]
    with pytest.raises(TypeError):
        copy.copy(output.trusted_result)
    with pytest.raises(TypeError):
        copy.deepcopy(output.trusted_result)
    with pytest.raises(TypeError):
        __import__("pickle").dumps(output.trusted_result)


# ---------------------------------------------------------------------------
# Independent deterministic gate replay
# ---------------------------------------------------------------------------


def test_pure_gate_empty_content_regression() -> None:
    # Pure-function regression only: the accepted gate still returns
    # EMPTY_CONTENT for direct empty/whitespace input.  This is NOT a claim
    # that EMPTY_CONTENT is reachable as a post-schema H2-B REPAIR runtime
    # gate-terminal reason.
    gate = DeterministicContentQualityGate()
    for content in ("", "   ", "\t\n"):
        result = gate.evaluate(
            content=content,
            candidate_hash="a" * 64,
            quality_input_hash="a" * 64,
            scoring_request_hash="a" * 64,
        )
        assert result is not None
        assert result.reason.value == "EMPTY_CONTENT"


@pytest.mark.parametrize(
    "reason",
    [_CONTROL_REASON, _REPETITION_REASON],
    ids=["control-character", "exact-repetition"],
)
def test_finalizer_gate_replay_rejects_despite_judge_pass_and_attestation(
    reason: str,
) -> None:
    # The runtime gate would reject this candidate, but the Judge chain is a
    # completely valid-looking PASS with a valid attestation: the finalizer must
    # still independently rerun the gate and reject.
    chain = _valid_chain(reason=reason)

    sanity = DeterministicContentQualityGate().evaluate(
        content=reason,
        candidate_hash=build_scoring_candidate_hash(chain["candidate"]),
        quality_input_hash=build_content_quality_input_hash(chain["judge_input"]),
        scoring_request_hash=chain["repair_request_hash"],
    )
    assert sanity is not None  # gate-invalid candidate by construction

    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain)


def test_low_level_empty_reason_candidate_is_rejected_by_fresh_schema_revalidation() -> None:
    chain = _valid_chain()
    # Forge a candidate whose reason is whitespace-only by bypassing the
    # constructor; fresh schema revalidation must reject before gate input
    # exists.  A freshly schema-valid candidate can never reach post-schema
    # EMPTY_CONTENT, so this is the frozen-order finalizer defense.
    forged = object.__new__(ScoringCandidate)
    object.__setattr__(forged, "score", 8)
    object.__setattr__(forged, "reason", "   ")
    object.__setattr__(forged, "topics", ("product",))
    object.__setattr__(forged, "should_summarize", True)
    object.__setattr__(forged, "dimensions", None)

    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, candidate=forged)


def test_model_construct_candidate_bypass_is_rejected() -> None:
    chain = _valid_chain()
    constructed = ScoringCandidate.model_construct(
        score=8,
        reason="   ",
        topics=("product",),
        should_summarize=True,
        dimensions=None,
    )
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, candidate=constructed)


# ---------------------------------------------------------------------------
# Identity / provenance attacks
# ---------------------------------------------------------------------------


def test_primary_request_hash_substituted_as_repair_provenance_is_rejected() -> None:
    chain = _valid_chain()
    primary_hash = chain["trusted_context"].request_hash
    # Rebuild the Judge chain under the PRIMARY hash so the caller values are
    # internally consistent, then hand the finalizer PRIMARY identity as the
    # REPAIR request identity.
    alt = _valid_chain()
    alt_ctx, alt_input = derive_repair_judge_trusted_context(
        repair_request_hash=primary_hash,
        trusted_candidate=alt["candidate"],
        scoring_input=alt["scoring_input"],
        validated_settings=alt["settings"],
    )
    alt_raw = _judge_pass_raw()
    alt_result = verify_judge_model_content(
        alt_raw, operation_input=alt_ctx.operation_input, content_input=alt_input
    )
    alt_evidence = build_judge_evidence(
        role="REPAIR",
        operation_input=alt_ctx.operation_input,
        judge_input=alt_input,
        raw_utf8=alt_raw,
        model=_MODEL,
        model_digest=_DIGEST,
        policy_version=_QUALITY_POLICY_VERSION,
        prompt_version=_QUALITY_PROMPT_VERSION,
        operation_schema_version=_QUALITY_SCHEMA_VERSION,
    )
    alt_attestation = build_quality_pass_attestation(
        quality_result=alt_result,
        operation_input=alt_ctx.operation_input,
        quality_input=alt_input,
        authority=alt["authority"],
    )

    with pytest.raises(RepairFinalizationInvalid):
        _finalize(
            chain,
            candidate=alt["candidate"],
            repair_request_hash=primary_hash,
            quality_input=alt_input,
            quality_result=alt_result,
            quality_operation=alt_ctx.operation_input,
            judge_evidence=alt_evidence,
            attestation=alt_attestation,
        )


def test_wrong_repair_request_identity_is_rejected() -> None:
    chain = _valid_chain()
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, repair_request_hash="f" * 64)


def test_wrong_rni_hash_is_rejected() -> None:
    chain = _valid_chain()
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, rni_hash="e" * 64)


def test_mutated_rni_is_rejected_by_fresh_revalidation() -> None:
    chain = _valid_chain()
    rni: RepairNormalizedInput = chain["rni"]
    mutated = copy.deepcopy(rni)
    object.__setattr__(mutated, "temperature", 1.5)  # bypass frozen guard
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, repair_normalized_input=mutated)


def test_primary_role_judge_evidence_is_rejected() -> None:
    chain = _valid_chain()
    # Relabel the REPAIR Judge evidence as PRIMARY via low-level mutation.
    forged_evidence = copy.deepcopy(chain["judge_evidence"])
    object.__setattr__(forged_evidence, "role", "PRIMARY")
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, judge_evidence=forged_evidence)


def test_non_pass_judge_result_is_rejected_even_when_raw_parses() -> None:
    chain = _valid_chain()
    uncertain_raw = json.dumps(
        {
            "status": "UNCERTAIN",
            "decision_confidence": "LOW",
            "grounding_confidence": "LOW",
            "usefulness_confidence": "LOW",
            "signals": ["GROUNDING_INSUFFICIENT"],
            "reason": "GROUNDING_INSUFFICIENT",
            "evidence_ids": [],
        }
    )
    uncertain_result = verify_judge_model_content(
        uncertain_raw,
        operation_input=chain["judge_ctx"].operation_input,
        content_input=chain["judge_input"],
    )
    assert uncertain_result.status is ContentQualityStatus.UNCERTAIN
    uncertain_evidence = build_judge_evidence(
        role="REPAIR",
        operation_input=chain["judge_ctx"].operation_input,
        judge_input=chain["judge_input"],
        raw_utf8=uncertain_raw,
        model=_MODEL,
        model_digest=_DIGEST,
        policy_version=_QUALITY_POLICY_VERSION,
        prompt_version=_QUALITY_PROMPT_VERSION,
        operation_schema_version=_QUALITY_SCHEMA_VERSION,
    )
    uncertain_attestation = None
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(
            chain,
            quality_result=uncertain_result,
            judge_evidence=uncertain_evidence,
            attestation=uncertain_attestation,
        )


# ---------------------------------------------------------------------------
# Forged attestation and capability attacks
# ---------------------------------------------------------------------------


def test_forged_attestation_mutation_is_rejected() -> None:
    chain = _valid_chain()
    forged_attestation = copy.deepcopy(chain["attestation"])
    object.__setattr__(forged_attestation, "scoring_request_hash", "d" * 64)
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, attestation=forged_attestation)


def test_object_new_attestation_shell_is_rejected() -> None:
    from youtube_intel.domain import QualityPassAttestation

    chain = _valid_chain()
    shell = object.__new__(QualityPassAttestation)
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, attestation=shell)


def test_spoofed_authority_is_rejected() -> None:
    chain = _valid_chain()
    spoofed = object.__new__(QualityProvenanceAuthority)
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, quality_authority=spoofed)


def test_spoofed_scoring_context_is_rejected() -> None:
    chain = _valid_chain()
    spoofed = object.__new__(TrustedScoringContext)
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, scoring_context=spoofed)


def test_substituted_settings_model_is_rejected() -> None:
    chain = _valid_chain()
    substituted = LocalScoringSettings(
        model="other-model:1b",
        expected_model_digest="sha256:" + "9" * 64,
        temperature=0.0,
        max_output_tokens=1200,
        max_transcript_chars=64,
        max_description_chars=32,
    )
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, validated_settings=substituted)


def test_judge_input_substitution_from_another_repair_identity_is_rejected() -> None:
    chain = _valid_chain()
    other = _valid_chain(reason="Another repaired response with several practical details inside.")
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, quality_input=other["judge_input"])


def test_candidate_replaced_from_another_chain_is_rejected() -> None:
    chain = _valid_chain()
    other_reason = (
        "The repaired response restates the concrete product strategy with "
        "several practical trade-offs and clear implementation details."
    )
    other = _valid_chain(reason=other_reason)
    with pytest.raises(RepairFinalizationInvalid):
        _finalize(chain, candidate=other["candidate"])
