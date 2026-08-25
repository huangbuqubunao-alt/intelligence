"""TASK-016C Phase H2-A — pure Judge raw-to-result replay verifier tests.

RED-first tests for ``verify_judge_model_content``, the pure internal verifier
that maps exact extracted Judge model content plus frozen Judge operation
input/provenance to a ``ContentQualityResult``.  It must perform no provider
call, filesystem write, or SQLite write, and it must share the exact same
deterministic interpretation logic as the live Judge path.

Authoritative contract: docs/TASK-016C-PHASE-H2-AUTHORIZATION.md (Judge raw,
outcome split, and JudgeEvidence; pure verifier conceptual contract).
"""

from __future__ import annotations

import json

import pytest

from youtube_intel.domain import (
    ContentQualityDecisionSource,
    ContentQualityInput,
    ContentQualityReason,
    ContentQualityResult,
    ContentQualityStatus,
    QualityJudgeAttemptRole,
    QualityJudgeOperationInput,
    ScoringEvidence,
    ScoringEvidenceSource,
)
from youtube_intel.providers.ollama import verify_judge_model_content

VALID_HASH = "a" * 64
DIGEST = "sha256:" + "b" * 64


def _operation_input(
    *,
    attempt_role: QualityJudgeAttemptRole = QualityJudgeAttemptRole.PRIMARY,
    scoring_request_hash: str = VALID_HASH,
    candidate_hash: str = VALID_HASH,
) -> QualityJudgeOperationInput:
    return QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": scoring_request_hash,
            "attempt_role": attempt_role,
            "candidate_hash": candidate_hash,
            "quality_input_hash": VALID_HASH,
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v1",
            "schema_version": "content-quality-result-v1",
            "judge_provider": "ollama",
            "judge_model": "qwen3:8b",
            "judge_model_digest": DIGEST,
        }
    )


def _content_input() -> ContentQualityInput:
    return ContentQualityInput.model_validate(
        {
            "scoring_request_hash": VALID_HASH,
            "candidate_hash": VALID_HASH,
            "output_language": "en",
            "reason": "A concise candidate reason",
            "topics": ("topic-a",),
            "evidence_registry": (
                ScoringEvidence(
                    evidence_id="title-1",
                    source=ScoringEvidenceSource.TITLE,
                    excerpt="excerpt for title-1",
                ),
            ),
            "policy_version": "content-quality-policy-v1",
        }
    )


def _pass_raw() -> str:
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


def _reject_raw() -> str:
    return json.dumps(
        {
            "status": "REJECT",
            "decision_confidence": "HIGH",
            "grounding_confidence": "LOW",
            "usefulness_confidence": "LOW",
            "signals": ["LOW_INFORMATION"],
            "reason": "LOW_INFORMATION",
            "evidence_ids": [],
        }
    )


def _uncertain_raw() -> str:
    return json.dumps(
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


def test_verify_pass_replay() -> None:
    result = verify_judge_model_content(
        _pass_raw(),
        operation_input=_operation_input(),
        content_input=_content_input(),
    )
    assert isinstance(result, ContentQualityResult)
    assert result.status is ContentQualityStatus.PASS
    assert result.decision_source is ContentQualityDecisionSource.LOCAL_JUDGE


def test_verify_reject_replay() -> None:
    result = verify_judge_model_content(
        _reject_raw(),
        operation_input=_operation_input(),
        content_input=_content_input(),
    )
    assert result.status is ContentQualityStatus.REJECT
    assert result.decision_source is ContentQualityDecisionSource.LOCAL_JUDGE


def test_verify_uncertain_replay() -> None:
    result = verify_judge_model_content(
        _uncertain_raw(),
        operation_input=_operation_input(),
        content_input=_content_input(),
    )
    assert result.status is ContentQualityStatus.UNCERTAIN
    assert result.reason is ContentQualityReason.GROUNDING_INSUFFICIENT


def test_verify_unparseable_raw_is_semantic_invalid_response_uncertain() -> None:
    result = verify_judge_model_content(
        "{not-json",
        operation_input=_operation_input(),
        content_input=_content_input(),
    )
    assert result.status is ContentQualityStatus.UNCERTAIN
    assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE


def test_verify_unknown_evidence_id_is_invalid_response_uncertain() -> None:
    raw = json.dumps(
        {
            "status": "PASS",
            "decision_confidence": "HIGH",
            "grounding_confidence": "MEDIUM",
            "usefulness_confidence": "MEDIUM",
            "signals": ["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
            "reason": None,
            "evidence_ids": ["not-in-registry"],
        }
    )
    result = verify_judge_model_content(
        raw,
        operation_input=_operation_input(),
        content_input=_content_input(),
    )
    assert result.status is ContentQualityStatus.UNCERTAIN
    assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE


def test_verify_schema_invalid_raw_is_invalid_response_uncertain() -> None:
    # A PASS claim that fails the frozen PASS matrix must not be promoted.
    raw = json.dumps(
        {
            "status": "PASS",
            "decision_confidence": "LOW",
            "grounding_confidence": "LOW",
            "usefulness_confidence": "LOW",
            "signals": [],
            "reason": None,
            "evidence_ids": [],
        }
    )
    result = verify_judge_model_content(
        raw,
        operation_input=_operation_input(),
        content_input=_content_input(),
    )
    assert result.status is ContentQualityStatus.UNCERTAIN
    assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE


def test_verify_is_deterministic() -> None:
    first = verify_judge_model_content(
        _pass_raw(),
        operation_input=_operation_input(),
        content_input=_content_input(),
    )
    second = verify_judge_model_content(
        _pass_raw(),
        operation_input=_operation_input(),
        content_input=_content_input(),
    )
    assert first == second


def test_verify_binds_result_to_operation_input() -> None:
    operation = _operation_input(candidate_hash="c" * 64, scoring_request_hash="d" * 64)
    content = ContentQualityInput.model_validate(
        {
            "scoring_request_hash": "d" * 64,
            "candidate_hash": "c" * 64,
            "output_language": "en",
            "reason": "A concise candidate reason",
            "topics": ("topic-a",),
            "evidence_registry": (
                ScoringEvidence(
                    evidence_id="title-1",
                    source=ScoringEvidenceSource.TITLE,
                    excerpt="excerpt for title-1",
                ),
            ),
            "policy_version": "content-quality-policy-v1",
        }
    )
    result = verify_judge_model_content(
        _pass_raw(),
        operation_input=operation,
        content_input=content,
    )
    assert result.candidate_hash == "c" * 64
    assert result.scoring_request_hash == "d" * 64
    assert result.judge_model == "qwen3:8b"
    assert result.judge_model_digest == DIGEST


def test_verify_rejects_non_exact_operation_input() -> None:
    class _Spoof(QualityJudgeOperationInput):
        pass

    spoof = _Spoof.model_validate(_operation_input().model_dump(mode="python"))
    with pytest.raises(ValueError):
        verify_judge_model_content(
            _pass_raw(),
            operation_input=spoof,
            content_input=_content_input(),
        )


def test_verify_rejects_non_exact_content_input() -> None:
    class _Spoof(ContentQualityInput):
        pass

    spoof = _Spoof.model_validate(_content_input().model_dump(mode="python"))
    with pytest.raises(ValueError):
        verify_judge_model_content(
            _pass_raw(),
            operation_input=_operation_input(),
            content_input=spoof,
        )


def test_verify_empty_raw_is_invalid_response_uncertain() -> None:
    result = verify_judge_model_content(
        "",
        operation_input=_operation_input(),
        content_input=_content_input(),
    )
    assert result.status is ContentQualityStatus.UNCERTAIN
    assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE
