"""TASK-016C Phase A domain contract tests (RED-before-GREEN)."""

from __future__ import annotations

import json
import warnings
from typing import Any

import pytest
from pydantic import ValidationError

from youtube_intel.domain import (
    _MAX_EVIDENCE_EXCERPT_LENGTH,
    _MAX_EVIDENCE_REGISTRY_ITEMS,
    _MAX_EVIDENCE_REGISTRY_TOTAL_CHARS,
    ContentQualityConfidence,
    ContentQualityDecisionSource,
    ContentQualityInput,
    ContentQualityReason,
    ContentQualityResult,
    ContentQualitySignal,
    ContentQualityStatus,
    DeterministicGateReason,
    QualityJudgeAttemptRole,
    QualityJudgeOperationInput,
    ScoreDimensions,
    ScoringCandidate,
    ScoringEvidence,
    ScoringEvidenceSource,
    validate_content_quality_result,
    validate_content_quality_result_json,
    validate_scoring_candidate,
    validate_scoring_candidate_json,
)

VALID_HASH = "a" * 64
OTHER_HASH = "b" * 64
MODEL_DIGEST = "sha256:" + ("c" * 64)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _candidate(**kwargs: Any) -> ScoringCandidate:
    data: dict[str, Any] = {
        "score": 7.5,
        "reason": "The video explains the product workflow clearly.",
        "topics": ("product", "workflow"),
        "should_summarize": True,
    }
    data.update(kwargs)
    return ScoringCandidate.model_validate(data)


def _evidence(**kwargs: Any) -> ScoringEvidence:
    data: dict[str, Any] = {
        "evidence_id": "e1",
        "source": ScoringEvidenceSource.TRANSCRIPT_HEAD,
        "excerpt": "The video explains the product workflow clearly.",
    }
    data.update(kwargs)
    return ScoringEvidence.model_validate(data)


def _content_quality_input(**kwargs: Any) -> ContentQualityInput:
    data: dict[str, Any] = {
        "scoring_request_hash": VALID_HASH,
        "candidate_hash": VALID_HASH,
        "output_language": "en",
        "reason": "The video explains the product workflow clearly.",
        "topics": ("product", "workflow"),
        "evidence_registry": (_evidence(),),
        "policy_version": "content-quality-policy-v1",
    }
    data.update(kwargs)
    return ContentQualityInput.model_validate(data)


def _pass_result(**kwargs: Any) -> ContentQualityResult:
    data: dict[str, Any] = {
        "schema_version": "content-quality-result-v1",
        "policy_version": "content-quality-policy-v1",
        "prompt_version": "content-quality-prompt-v1",
        "status": ContentQualityStatus.PASS,
        "decision_source": ContentQualityDecisionSource.LOCAL_JUDGE,
        "decision_confidence": ContentQualityConfidence.HIGH,
        "grounding_confidence": ContentQualityConfidence.MEDIUM,
        "usefulness_confidence": ContentQualityConfidence.MEDIUM,
        "signals": (
            ContentQualitySignal.MINIMAL_CLAIM_PRESENT,
            ContentQualitySignal.GROUNDING_PRESENT,
        ),
        "reason": None,
        "evidence_ids": ("e1",),
        "candidate_hash": VALID_HASH,
        "quality_input_hash": VALID_HASH,
        "scoring_request_hash": VALID_HASH,
        "judge_provider": "ollama",
        "judge_model": "qwen3:8b",
        "judge_model_digest": MODEL_DIGEST,
    }
    data.update(kwargs)
    return ContentQualityResult.model_validate(data)


def _reject_result(**kwargs: Any) -> ContentQualityResult:
    data: dict[str, Any] = {
        "schema_version": "content-quality-result-v1",
        "policy_version": "content-quality-policy-v1",
        "prompt_version": "content-quality-prompt-v1",
        "status": ContentQualityStatus.REJECT,
        "decision_source": ContentQualityDecisionSource.LOCAL_JUDGE,
        "decision_confidence": ContentQualityConfidence.HIGH,
        "grounding_confidence": ContentQualityConfidence.LOW,
        "usefulness_confidence": ContentQualityConfidence.LOW,
        "signals": (ContentQualitySignal.IDENTIFIER_ONLY,),
        "reason": ContentQualityReason.IDENTIFIER_ONLY,
        "evidence_ids": (),
        "candidate_hash": VALID_HASH,
        "quality_input_hash": VALID_HASH,
        "scoring_request_hash": VALID_HASH,
        "judge_provider": "ollama",
        "judge_model": "qwen3:8b",
        "judge_model_digest": MODEL_DIGEST,
    }
    data.update(kwargs)
    return ContentQualityResult.model_validate(data)


def _uncertain_result(**kwargs: Any) -> ContentQualityResult:
    data: dict[str, Any] = {
        "schema_version": "content-quality-result-v1",
        "policy_version": "content-quality-policy-v1",
        "prompt_version": "content-quality-prompt-v1",
        "status": ContentQualityStatus.UNCERTAIN,
        "decision_source": ContentQualityDecisionSource.LOCAL_JUDGE,
        "decision_confidence": ContentQualityConfidence.LOW,
        "grounding_confidence": ContentQualityConfidence.LOW,
        "usefulness_confidence": ContentQualityConfidence.LOW,
        "signals": (ContentQualitySignal.GROUNDING_INSUFFICIENT,),
        "reason": ContentQualityReason.GROUNDING_INSUFFICIENT,
        "evidence_ids": (),
        "candidate_hash": VALID_HASH,
        "quality_input_hash": VALID_HASH,
        "scoring_request_hash": VALID_HASH,
        "judge_provider": "ollama",
        "judge_model": "qwen3:8b",
        "judge_model_digest": MODEL_DIGEST,
    }
    data.update(kwargs)
    return ContentQualityResult.model_validate(data)


def _gate_reject_result(**kwargs: Any) -> ContentQualityResult:
    data: dict[str, Any] = {
        "schema_version": "content-quality-result-v1",
        "policy_version": "content-quality-policy-v1",
        "prompt_version": "content-quality-prompt-v1",
        "status": ContentQualityStatus.REJECT,
        "decision_source": ContentQualityDecisionSource.DETERMINISTIC_GATE,
        "decision_confidence": ContentQualityConfidence.HIGH,
        "grounding_confidence": ContentQualityConfidence.LOW,
        "usefulness_confidence": ContentQualityConfidence.LOW,
        "signals": (),
        "reason": DeterministicGateReason.EMPTY_CONTENT,
        "evidence_ids": (),
        "candidate_hash": VALID_HASH,
        "quality_input_hash": VALID_HASH,
        "scoring_request_hash": VALID_HASH,
        "judge_provider": None,
        "judge_model": None,
        "judge_model_digest": None,
    }
    data.update(kwargs)
    return ContentQualityResult.model_validate(data)


def _quality_judge_operation_input(**kwargs: Any) -> QualityJudgeOperationInput:
    data: dict[str, Any] = {
        "scoring_request_hash": VALID_HASH,
        "attempt_role": QualityJudgeAttemptRole.PRIMARY,
        "candidate_hash": VALID_HASH,
        "quality_input_hash": VALID_HASH,
        "policy_version": "content-quality-policy-v1",
        "prompt_version": "content-quality-prompt-v1",
        "schema_version": "content-quality-result-v1",
        "judge_provider": "ollama",
        "judge_model": "qwen3:8b",
        "judge_model_digest": MODEL_DIGEST,
    }
    data.update(kwargs)
    return QualityJudgeOperationInput.model_validate(data)


# ---------------------------------------------------------------------------
# ScoringCandidate compatibility
# ---------------------------------------------------------------------------


def test_scoring_candidate_accepts_float_score() -> None:
    candidate = _candidate(score=7.5)
    assert candidate.score == 7.5


def test_scoring_candidate_allows_none_dimensions() -> None:
    candidate = _candidate(dimensions=None)
    assert candidate.dimensions is None


def test_scoring_candidate_keeps_score_result_business_fields() -> None:
    dims = ScoreDimensions(technical=8.0, business=None)
    candidate = _candidate(
        score=7.5,
        reason="Useful product insight.",
        topics=("product",),
        should_summarize=True,
        dimensions=dims,
    )
    assert candidate.score == 7.5
    assert candidate.reason == "Useful product insight."
    assert candidate.topics == ("product",)
    assert candidate.should_summarize is True
    assert candidate.dimensions is not None
    assert candidate.dimensions.technical == 8.0


def test_scoring_candidate_rejects_nan_score() -> None:
    with pytest.raises(ValidationError):
        _candidate(score=float("nan"))


@pytest.mark.parametrize("score", [float("inf"), float("-inf")])
def test_scoring_candidate_rejects_infinite_score(score: float) -> None:
    with pytest.raises(ValidationError):
        _candidate(score=score)


# ---------------------------------------------------------------------------
# ContentQualityResult PASS matrix
# ---------------------------------------------------------------------------


def test_pass_legal_sample() -> None:
    result = _pass_result()
    assert result.status is ContentQualityStatus.PASS


def test_pass_missing_required_signal_rejected() -> None:
    with pytest.raises(ValidationError):
        _pass_result(signals=(ContentQualitySignal.GROUNDING_PRESENT,))


def test_pass_confidence_threshold_insufficient_rejected() -> None:
    with pytest.raises(ValidationError):
        _pass_result(grounding_confidence=ContentQualityConfidence.LOW)


def test_pass_with_rejection_reason_rejected() -> None:
    with pytest.raises(ValidationError):
        _pass_result(reason=ContentQualityReason.IDENTIFIER_ONLY)


# ---------------------------------------------------------------------------
# ContentQualityResult REJECT matrix
# ---------------------------------------------------------------------------


def test_reject_without_reason_rejected() -> None:
    with pytest.raises(ValidationError):
        _reject_result(reason=None)


def test_reject_using_uncertain_only_reason_rejected() -> None:
    with pytest.raises(ValidationError):
        _reject_result(
            reason=ContentQualityReason.JUDGE_UNAVAILABLE,
            signals=(ContentQualitySignal.JUDGE_UNAVAILABLE,),
        )


# ---------------------------------------------------------------------------
# ContentQualityResult UNCERTAIN matrix
# ---------------------------------------------------------------------------


def test_uncertain_legal_sample() -> None:
    result = _uncertain_result()
    assert result.status is ContentQualityStatus.UNCERTAIN


def test_uncertain_using_deterministic_reject_only_reason_rejected() -> None:
    with pytest.raises(ValidationError):
        _uncertain_result(
            reason=ContentQualityReason.IDENTIFIER_ONLY,
            signals=(ContentQualitySignal.IDENTIFIER_ONLY,),
        )


# ---------------------------------------------------------------------------
# Canonical collections
# ---------------------------------------------------------------------------


def test_duplicate_signals_are_normalized() -> None:
    result = _pass_result(
        signals=(
            ContentQualitySignal.MINIMAL_CLAIM_PRESENT,
            ContentQualitySignal.MINIMAL_CLAIM_PRESENT,
            ContentQualitySignal.GROUNDING_PRESENT,
        )
    )
    assert result.signals == (
        ContentQualitySignal.GROUNDING_PRESENT,
        ContentQualitySignal.MINIMAL_CLAIM_PRESENT,
    )


def test_noncanonical_signals_are_sorted() -> None:
    result = _pass_result(
        signals=(
            ContentQualitySignal.GROUNDING_PRESENT,
            ContentQualitySignal.MINIMAL_CLAIM_PRESENT,
        )
    )
    assert result.signals == (
        ContentQualitySignal.GROUNDING_PRESENT,
        ContentQualitySignal.MINIMAL_CLAIM_PRESENT,
    )


def test_duplicate_evidence_ids_rejected() -> None:
    with pytest.raises(ValidationError):
        _pass_result(evidence_ids=("e1", "e1"))


def test_evidence_ids_are_canonically_ordered() -> None:
    result = _pass_result(evidence_ids=("e3", "e1", "e2"))
    assert result.evidence_ids == ("e1", "e2", "e3")


def test_invalid_evidence_identity_rejected() -> None:
    with pytest.raises(ValidationError):
        _pass_result(evidence_ids=("",))


# ---------------------------------------------------------------------------
# Enum and field validation
# ---------------------------------------------------------------------------


def test_invalid_confidence_enum_rejected() -> None:
    with pytest.raises(ValidationError):
        ContentQualityResult.model_validate(
            {
                **_pass_result().model_dump(mode="python"),
                "decision_confidence": "INVALID",
            }
        )


# ---------------------------------------------------------------------------
# Untrusted construction protection
# ---------------------------------------------------------------------------


def test_model_copy_update_bypass_is_rejected() -> None:
    result = _pass_result()
    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        result.model_copy(update={"score": 5.0})


def test_deprecated_copy_update_bypass_is_revalidated() -> None:
    result = _pass_result()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        unchecked = result.copy(update={"status": "REJECT"})
    with pytest.raises(ValidationError):
        validate_content_quality_result(unchecked)


def test_model_construct_bypass_is_revalidated() -> None:
    payload = _pass_result().model_dump(mode="python")
    payload["status"] = "REJECT"
    unchecked = ContentQualityResult.model_construct(**payload)
    with pytest.raises(ValidationError):
        validate_content_quality_result(unchecked)


def test_mapping_restore_is_revalidated() -> None:
    mapping = dict(_pass_result().model_dump(mode="python"))
    # PASS must not contain any negative signal.
    mapping["signals"] = ["IDENTIFIER_ONLY"]
    with pytest.raises(ValidationError):
        validate_content_quality_result(mapping)


def test_json_restore_is_revalidated() -> None:
    mapping = _pass_result().model_dump(mode="json")
    # REJECT must include a reason.
    mapping["status"] = "REJECT"
    mapping["signals"] = ["IDENTIFIER_ONLY"]
    mapping["grounding_confidence"] = "LOW"
    mapping["usefulness_confidence"] = "LOW"
    raw = json.dumps(mapping)
    with pytest.raises(ValidationError):
        validate_content_quality_result_json(raw)


def test_trusted_revalidation_rejects_malformed_unchecked_content_quality_result() -> None:
    unchecked = ContentQualityResult.model_construct(
        schema_version="content-quality-result-v1",
        policy_version="content-quality-policy-v1",
        prompt_version="content-quality-prompt-v1",
        status=ContentQualityStatus.PASS,
        decision_source=ContentQualityDecisionSource.LOCAL_JUDGE,
        decision_confidence=ContentQualityConfidence.HIGH,
        grounding_confidence=ContentQualityConfidence.LOW,
        usefulness_confidence=ContentQualityConfidence.LOW,
        signals=(ContentQualitySignal.MINIMAL_CLAIM_PRESENT,),
        reason=None,
        evidence_ids=("e1",),
        candidate_hash=VALID_HASH,
        quality_input_hash=VALID_HASH,
        scoring_request_hash=VALID_HASH,
        judge_provider="ollama",
        judge_model="qwen3:8b",
        judge_model_digest=MODEL_DIGEST,
    )
    with pytest.raises(ValidationError):
        validate_content_quality_result(unchecked)


def test_trusted_revalidation_rejects_malformed_unchecked_scoring_candidate() -> None:
    unchecked = ScoringCandidate.model_construct(
        score=float("nan"),
        reason="The video explains the product workflow clearly.",
        topics=("product",),
        should_summarize=True,
    )
    with pytest.raises(ValidationError):
        validate_scoring_candidate(unchecked)


# ---------------------------------------------------------------------------
# Quality judge operation skeleton
# ---------------------------------------------------------------------------


def test_quality_judge_attempt_role_primary() -> None:
    op = _quality_judge_operation_input(attempt_role=QualityJudgeAttemptRole.PRIMARY)
    assert op.attempt_role is QualityJudgeAttemptRole.PRIMARY


def test_quality_judge_attempt_role_repair() -> None:
    op = _quality_judge_operation_input(attempt_role=QualityJudgeAttemptRole.REPAIR)
    assert op.attempt_role is QualityJudgeAttemptRole.REPAIR


def test_quality_judge_operation_input_stable_schema() -> None:
    op = _quality_judge_operation_input()
    assert op.scoring_request_hash == VALID_HASH
    assert op.candidate_hash == VALID_HASH
    assert op.quality_input_hash == VALID_HASH
    assert op.policy_version == "content-quality-policy-v1"
    assert op.prompt_version == "content-quality-prompt-v1"
    assert op.schema_version == "content-quality-result-v1"
    assert op.judge_provider == "ollama"
    assert op.judge_model == "qwen3:8b"
    assert op.judge_model_digest == MODEL_DIGEST


def test_scoring_candidate_model_copy_update_rejected() -> None:
    candidate = _candidate()
    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        candidate.model_copy(update={"score": 5.0})


def test_scoring_candidate_json_restore() -> None:
    candidate = _candidate()
    raw = candidate.model_dump_json()
    restored = validate_scoring_candidate_json(raw)
    assert restored == candidate


def test_scoring_candidate_mapping_restore() -> None:
    candidate = _candidate()
    mapping = candidate.model_dump(mode="python")
    restored = validate_scoring_candidate(mapping)
    assert restored == candidate


# ---------------------------------------------------------------------------
# P1-1 ContentQualityResult REJECT matrix corrections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reason", list(DeterministicGateReason))
def test_gate_reject_legal_all_deterministic_reasons(
    reason: DeterministicGateReason,
) -> None:
    result = _gate_reject_result(reason=reason)
    assert result.status is ContentQualityStatus.REJECT
    assert result.decision_source is ContentQualityDecisionSource.DETERMINISTIC_GATE
    assert result.signals == ()
    assert result.evidence_ids == ()
    assert result.judge_provider is None


def test_gate_reject_does_not_require_judge_signal() -> None:
    # If the implementation wrongly falls through to the Judge rejection matrix,
    # it would demand a signal matching the reason. Gate rejections have no signals.
    result = _gate_reject_result(
        reason=DeterministicGateReason.EMPTY_CONTENT,
        signals=(),
    )
    assert result.reason is DeterministicGateReason.EMPTY_CONTENT
    assert result.signals == ()


def test_judge_reject_grounding_insufficient_legal_high_usefulness() -> None:
    result = _reject_result(
        reason=ContentQualityReason.GROUNDING_INSUFFICIENT,
        signals=(ContentQualitySignal.GROUNDING_INSUFFICIENT,),
        grounding_confidence=ContentQualityConfidence.LOW,
        usefulness_confidence=ContentQualityConfidence.HIGH,
    )
    assert result.status is ContentQualityStatus.REJECT


@pytest.mark.parametrize(
    "usefulness",
    [
        ContentQualityConfidence.LOW,
        ContentQualityConfidence.MEDIUM,
        ContentQualityConfidence.HIGH,
    ],
)
def test_judge_reject_grounding_insufficient_legal_usefulness_boundaries(
    usefulness: ContentQualityConfidence,
) -> None:
    result = _reject_result(
        reason=ContentQualityReason.GROUNDING_INSUFFICIENT,
        signals=(ContentQualitySignal.GROUNDING_INSUFFICIENT,),
        grounding_confidence=ContentQualityConfidence.LOW,
        usefulness_confidence=usefulness,
    )
    assert result.reason is ContentQualityReason.GROUNDING_INSUFFICIENT


def test_judge_reject_grounding_insufficient_rejects_non_low_grounding() -> None:
    with pytest.raises(ValidationError):
        _reject_result(
            reason=ContentQualityReason.GROUNDING_INSUFFICIENT,
            signals=(ContentQualitySignal.GROUNDING_INSUFFICIENT,),
            grounding_confidence=ContentQualityConfidence.MEDIUM,
            usefulness_confidence=ContentQualityConfidence.HIGH,
        )


def test_judge_reject_grounding_insufficient_rejects_grounding_present_signal() -> None:
    with pytest.raises(ValidationError):
        _reject_result(
            reason=ContentQualityReason.GROUNDING_INSUFFICIENT,
            signals=(
                ContentQualitySignal.GROUNDING_INSUFFICIENT,
                ContentQualitySignal.GROUNDING_PRESENT,
            ),
            grounding_confidence=ContentQualityConfidence.LOW,
            usefulness_confidence=ContentQualityConfidence.HIGH,
        )


def test_judge_content_reject_rejects_non_low_usefulness() -> None:
    with pytest.raises(ValidationError):
        _reject_result(
            reason=ContentQualityReason.IDENTIFIER_ONLY,
            signals=(ContentQualitySignal.IDENTIFIER_ONLY,),
            grounding_confidence=ContentQualityConfidence.LOW,
            usefulness_confidence=ContentQualityConfidence.MEDIUM,
        )


def test_gate_reject_with_judge_reason_rejected() -> None:
    with pytest.raises(ValidationError):
        _gate_reject_result(reason=ContentQualityReason.IDENTIFIER_ONLY)  # type: ignore[arg-type]


def test_judge_reject_with_gate_reason_rejected() -> None:
    with pytest.raises(ValidationError):
        _reject_result(reason=DeterministicGateReason.EMPTY_CONTENT)  # type: ignore[arg-type]


def test_uncertain_with_deterministic_reason_rejected() -> None:
    with pytest.raises(ValidationError):
        _uncertain_result(
            reason=DeterministicGateReason.EMPTY_CONTENT,  # type: ignore[arg-type]
            signals=(ContentQualitySignal.GROUNDING_INSUFFICIENT,),
        )


def test_gate_reject_with_judge_identity_rejected() -> None:
    with pytest.raises(ValidationError):
        _gate_reject_result(
            judge_provider="ollama",
            judge_model="qwen3:8b",
            judge_model_digest=MODEL_DIGEST,
        )


# ---------------------------------------------------------------------------
# P1-2 Evidence registry contract
# ---------------------------------------------------------------------------


def test_evidence_registry_canonical_ordering() -> None:
    inp = _content_quality_input(
        evidence_registry=(_evidence(evidence_id="e2"), _evidence(evidence_id="e1")),
    )
    assert [e.evidence_id for e in inp.evidence_registry] == ["e1", "e2"]


def test_evidence_registry_rejects_duplicate_id() -> None:
    with pytest.raises(ValidationError):
        _content_quality_input(
            evidence_registry=(_evidence(evidence_id="e1"), _evidence(evidence_id="e1")),
        )


def test_evidence_registry_rejects_count_above_max() -> None:
    registry = tuple(_evidence(evidence_id=f"e{i}") for i in range(101))
    with pytest.raises(ValidationError):
        _content_quality_input(evidence_registry=registry)


def test_evidence_registry_rejects_total_chars_above_max() -> None:
    """The total-character bound must be independently provable.

    The previous version of this test used 101 entries at the per-item excerpt
    maximum. That input already violates the count bound, so removing the
    total-character check would not make the old test fail. Here we use exactly
    the count limit (100 items) and exceed the total-character limit only via
    the per-item excerpt maximum plus the unavoidable evidence_id characters.
    """
    registry = tuple(
        _evidence(
            evidence_id=f"e{i}",
            excerpt="x" * _MAX_EVIDENCE_EXCERPT_LENGTH,
        )
        for i in range(_MAX_EVIDENCE_REGISTRY_ITEMS)
    )
    total = sum(len(e.evidence_id) + len(e.excerpt) for e in registry)

    assert len(registry) == _MAX_EVIDENCE_REGISTRY_ITEMS
    assert total > _MAX_EVIDENCE_REGISTRY_TOTAL_CHARS
    with pytest.raises(ValidationError, match="total characters"):
        _content_quality_input(evidence_registry=registry)


def test_evidence_registry_old_total_chars_test_depended_on_count_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove the previous total-character test could not isolate the two checks.

    The old test built 101 max-length entries. Even if the total-character bound
    is effectively removed (monkey-patched to a huge value), that input is still
    rejected by the count bound. Therefore the old test did not prove that a
    total-character bound exists.
    """
    old_registry = tuple(
        _evidence(
            evidence_id=f"e{i:03d}",
            excerpt="x" * _MAX_EVIDENCE_EXCERPT_LENGTH,
        )
        for i in range(_MAX_EVIDENCE_REGISTRY_ITEMS + 1)
    )

    monkeypatch.setattr(
        "youtube_intel.domain._MAX_EVIDENCE_REGISTRY_TOTAL_CHARS",
        _MAX_EVIDENCE_REGISTRY_TOTAL_CHARS * 100,
    )
    with pytest.raises(ValidationError, match="at most 100 items"):
        _content_quality_input(evidence_registry=old_registry)


def test_scoring_evidence_rejects_id_above_max_length() -> None:
    with pytest.raises(ValidationError):
        _evidence(evidence_id="x" * 101)


def test_result_evidence_ids_reject_id_above_max_length() -> None:
    with pytest.raises(ValidationError):
        _pass_result(evidence_ids=("x" * 101,))


def test_result_evidence_ids_canonicalize_and_reject_duplicates() -> None:
    with pytest.raises(ValidationError):
        _pass_result(evidence_ids=("e3", "e1", "e3", "e2"))


def test_result_evidence_ids_are_canonically_ordered() -> None:
    result = _pass_result(evidence_ids=("e3", "e1", "e2"))
    assert result.evidence_ids == ("e1", "e2", "e3")


def test_equal_registry_semantics_have_identical_canonical_order() -> None:
    inp_a = _content_quality_input(
        evidence_registry=(_evidence(evidence_id="e2"), _evidence(evidence_id="e1")),
    )
    inp_b = _content_quality_input(
        evidence_registry=(_evidence(evidence_id="e1"), _evidence(evidence_id="e2")),
    )
    assert inp_a.evidence_registry == inp_b.evidence_registry


# ---------------------------------------------------------------------------
# P1 correction trusted revalidation coverage
# ---------------------------------------------------------------------------


def test_validate_content_quality_result_accepts_gate_reject() -> None:
    result = _gate_reject_result(reason=DeterministicGateReason.EXACT_REPETITION)
    raw = result.model_dump_json()
    restored = validate_content_quality_result_json(raw)
    assert restored == result


def test_validate_content_quality_result_accepts_grounding_reject() -> None:
    result = _reject_result(
        reason=ContentQualityReason.GROUNDING_INSUFFICIENT,
        signals=(ContentQualitySignal.GROUNDING_INSUFFICIENT,),
        grounding_confidence=ContentQualityConfidence.LOW,
        usefulness_confidence=ContentQualityConfidence.HIGH,
    )
    raw = result.model_dump_json()
    restored = validate_content_quality_result_json(raw)
    assert restored == result
