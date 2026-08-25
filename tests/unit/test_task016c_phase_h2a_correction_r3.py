"""TASK-016C Phase H2-A Correction Round 3 — runtime-owned trust composition.

RED-first behavioral tests reproducing the three Round-2 independent-review
findings.  The trust model corrected here is:

    ALREADY TRUSTED RUNTIME INPUTS
        -> RUNTIME-OWNED / DETERMINISTIC COMPOSITION
        -> EXPECTED DATA
        -> EVIDENCE REPLAY

No authoritative verifier/builder may establish trust merely because a caller
supplied a ``JudgeTrustedContext`` or ``RepairTrustedConfig`` instance.  The
authoritative PFE/RNI composition derives the expected Judge context and the
REPAIR configuration internally from the validated runtime settings and the
trusted PRIMARY context.

Findings reproduced:
- P1-1: expected Judge context must be DERIVED from trusted runtime state, not
  supplied as an attacker-built JudgeTrustedContext.
- P1-2: a directly constructed RepairTrustedConfig must not establish RNI trust.
- P1-3: Judge-based PFE must enter the trusted RNI builder without a
  caller-selected Judge context.

Authoritative contract: docs/TASK-016C-PHASE-H2-AUTHORIZATION.md.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from datetime import UTC, datetime

import pytest

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    VideoMetadata,
)
from youtube_intel.h2_evidence import (
    CandidateEvidence,
    JudgeTrustedContext,
    NotApplicableEvidence,
    PrimaryFailureClass,
    PrimaryFailureEvidence,
    RepairTrustedConfig,
    build_judge_evidence,
    build_primary_trusted_context,
    build_repair_normalized_input,
    build_scoring_candidate_hash,
    canonical_primary_scoring_input_hash,
    derive_primary_judge_trusted_context,
    verify_primary_failure_evidence,
)
from youtube_intel.providers.ollama import (
    parse_scoring_candidate,
    seal_primary_raw_capture,
)
from youtube_intel.scoring import build_scoring_input

_MODEL = "qwen3:8b"
_DIGEST = "sha256:" + "a" * 64
_HASH_C = "c" * 64

_JUDGE_POLICY = "content-quality-policy-v1"
_JUDGE_PROMPT = "content-quality-prompt-v1"
_JUDGE_SCHEMA = "content-quality-result-v1"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _settings(*, model=_MODEL, digest=_DIGEST, temperature=0.0,
              max_output_tokens=1200, max_description_chars=32) -> LocalScoringSettings:
    return LocalScoringSettings(
        model=model,
        expected_model_digest=digest,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_transcript_chars=64,
        max_description_chars=max_description_chars,
    )


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id="video-h2a-r3",
        channel_id="channel-h2a-r3",
        channel_name="H2A R3 Channel",
        title="A useful scoring title",
        description="A deliberately bounded scoring description.",
        source_url="https://example.invalid/watch?v=video-h2a-r3",
        published_at=datetime(2026, 8, 18, tzinfo=UTC),
        duration_seconds=120,
        default_language="en",
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _scoring_input(*, output_language: str = "en"):
    return build_scoring_input(
        video=_video(),
        transcript_text="This transcript contains enough text for a stable sample.",
        language="en",
        output_language=output_language,
        settings=_settings(),
    )


def _trusted_context(scoring_input=None):
    si = scoring_input if scoring_input is not None else _scoring_input()
    return build_primary_trusted_context(
        scoring_input=si,
        model=_MODEL,
        model_digest=_DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
    )


def _valid_candidate_raw() -> str:
    inner = json.dumps(
        {
            "score": 8,
            "reason": "This response explains a concrete product strategy with useful trade-offs.",
            "topics": ["product strategy"],
            "should_summarize": True,
        },
        ensure_ascii=False,
    )
    body = json.dumps(
        {"model": _MODEL, "response": inner, "done": True},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return seal_primary_raw_capture(body).utf8


def _judge_raw_for_status(status: str) -> str:
    if status == "REJECT":
        payload = {
            "status": "REJECT",
            "decision_confidence": "HIGH",
            "grounding_confidence": "LOW",
            "usefulness_confidence": "LOW",
            "signals": ["LOW_INFORMATION"],
            "reason": "LOW_INFORMATION",
            "evidence_ids": [],
        }
    else:  # UNCERTAIN
        payload = {
            "status": "UNCERTAIN",
            "decision_confidence": "LOW",
            "grounding_confidence": "LOW",
            "usefulness_confidence": "LOW",
            "signals": ["GROUNDING_INSUFFICIENT"],
            "reason": "GROUNDING_INSUFFICIENT",
            "evidence_ids": [],
        }
    return json.dumps(payload)


def _judge_based_pfe(ctx, si, *, judge_status: str, judge_evidence=None):
    """Build a Judge-based PFE whose candidate is parsed from the trusted raw."""

    raw = _valid_candidate_raw()
    candidate = parse_scoring_candidate(raw)
    candidate_hash = build_scoring_candidate_hash(candidate)
    if judge_evidence is None:
        judge_ctx, judge_input = derive_primary_judge_trusted_context(
            primary_trusted_context=ctx,
            trusted_candidate=candidate,
            validated_settings=_settings(),
        )
        judge_evidence = build_judge_evidence(
            role="PRIMARY",
            operation_input=judge_ctx.operation_input,
            judge_input=judge_input,
            raw_utf8=_judge_raw_for_status(judge_status),
            model=judge_ctx.model,
            model_digest=judge_ctx.model_digest,
            policy_version=judge_ctx.policy_version,
            prompt_version=judge_ctx.prompt_version,
            operation_schema_version=judge_ctx.operation_schema_version,
        )
    failure_class = (
        PrimaryFailureClass.JUDGE_REJECT
        if judge_status == "REJECT"
        else PrimaryFailureClass.JUDGE_UNCERTAIN
    )
    return PrimaryFailureEvidence(
        schema_version="task016c-primary-failure-evidence-v1",
        primary_attempt_identity="local-scoring",
        primary_request_hash=ctx.request_hash,
        primary_normalized_input_hash=ctx.normalized_input_hash,
        primary_provider=ctx.provider,
        primary_model=ctx.model,
        primary_model_digest=ctx.model_digest,
        primary_prompt_version=ctx.prompt_version,
        primary_schema_version=ctx.schema_version,
        primary_output_language=ctx.output_language,
        primary_temperature=ctx.temperature,
        primary_max_output_tokens=ctx.max_output_tokens,
        primary_max_description_chars=ctx.max_description_chars,
        primary_scoring_input=si,
        primary_scoring_input_sha256=canonical_primary_scoring_input_hash(si),
        primary_raw_capture_kind="OLLAMA_GENERATE_HTTP_BODY_V1",
        primary_raw_utf8=raw,
        primary_raw_utf8_length=len(raw.encode("utf-8")),
        primary_raw_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        failure_class=failure_class,
        primary_candidate=CandidateEvidence(
            schema_version="task016c-candidate-evidence-v1",
            kind="CANDIDATE",
            candidate=candidate,
            candidate_sha256=candidate_hash,
        ),
        parser_evidence=NotApplicableEvidence(kind="NOT_APPLICABLE"),
        language_evidence=NotApplicableEvidence(kind="NOT_APPLICABLE"),
        judge_evidence=judge_evidence,
    )


# ---------------------------------------------------------------------------
# P1-1 — expected Judge context is derived, not caller-supplied
# ---------------------------------------------------------------------------


def test_derive_primary_judge_context_is_deterministic_from_trusted_inputs() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    candidate = parse_scoring_candidate(_valid_candidate_raw())
    a, _ = derive_primary_judge_trusted_context(
        primary_trusted_context=ctx, trusted_candidate=candidate, validated_settings=_settings()
    )
    b, _ = derive_primary_judge_trusted_context(
        primary_trusted_context=ctx, trusted_candidate=candidate, validated_settings=_settings()
    )
    assert a.expected_h1 == b.expected_h1
    assert a.expected_h2 == b.expected_h2
    assert a.model == _MODEL
    assert a.model_digest == _DIGEST
    assert a.role == "PRIMARY"


def test_derive_primary_judge_context_rejects_attacker_settings() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    candidate = parse_scoring_candidate(_valid_candidate_raw())
    attacker_settings = _settings(model="attacker-model:1b", digest="sha256:" + "c" * 64)
    # The derived context must reflect the attacker settings ONLY if the caller
    # passes them; but the authoritative path passes the real runtime settings.
    # Here we assert the derivation is tied to the settings it is given, and that
    # mismatched settings against the trusted PRIMARY context are rejected.
    with pytest.raises(ValueError):
        derive_primary_judge_trusted_context(
            primary_trusted_context=ctx,
            trusted_candidate=candidate,
            validated_settings=attacker_settings,
        )


def test_pfe_authoritative_path_derives_judge_context_internally() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _judge_based_pfe(ctx, si, judge_status="REJECT")
    # No judge_trusted_context argument exists on the authoritative verifier.
    verify_primary_failure_evidence(pfe, ctx, _settings())


def test_pfe_authoritative_verifier_has_no_judge_context_parameter() -> None:
    sig = inspect.signature(verify_primary_failure_evidence)
    assert "judge_trusted_context" not in sig.parameters


def test_pfe_rejects_self_consistent_judge_b_for_primary_a() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    candidate_a = parse_scoring_candidate(_valid_candidate_raw())
    # Attacker builds a fully self-consistent Judge B for a different candidate
    # and request, using attacker model/digest.
    from youtube_intel.domain import ContentQualityInput, QualityJudgeOperationInput
    from youtube_intel.quality import build_content_quality_input_hash

    content_b = ContentQualityInput.model_validate(
        {
            "scoring_request_hash": _HASH_C,
            "candidate_hash": _HASH_C,
            "output_language": "en",
            "reason": "A concise candidate reason",
            "topics": ("topic-b",),
            "evidence_registry": (
                {
                    "evidence_id": "title-1",
                    "source": "TITLE",
                    "excerpt": "excerpt for title-1",
                },
            ),
        }
    )
    qih_b = build_content_quality_input_hash(content_b)
    operation_b = QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": _HASH_C,
            "attempt_role": "PRIMARY",
            "candidate_hash": _HASH_C,
            "quality_input_hash": qih_b,
            "policy_version": _JUDGE_POLICY,
            "prompt_version": _JUDGE_PROMPT,
            "schema_version": _JUDGE_SCHEMA,
            "judge_provider": "ollama",
            "judge_model": "attacker-model:1b",
            "judge_model_digest": "sha256:" + "c" * 64,
        }
    )
    judge_b = build_judge_evidence(
        role="PRIMARY",
        operation_input=operation_b,
        judge_input=content_b,
        raw_utf8=_judge_raw_for_status("REJECT"),
        model="attacker-model:1b",
        model_digest="sha256:" + "c" * 64,
        policy_version=_JUDGE_POLICY,
        prompt_version=_JUDGE_PROMPT,
        operation_schema_version=_JUDGE_SCHEMA,
    )
    # Attach self-consistent Judge B to PFE A.
    pfe_a = _judge_based_pfe(ctx, si, judge_status="REJECT", judge_evidence=judge_b)
    # The authoritative path derives expected context A internally and rejects B.
    with pytest.raises(ValueError):
        verify_primary_failure_evidence(pfe_a, ctx, _settings())
    del candidate_a


def test_attacker_judge_trusted_context_cannot_be_injected() -> None:
    # The authoritative verifier takes exactly (evidence, trusted_context,
    # validated_settings); there is no parameter through which an attacker
    # JudgeTrustedContext could be injected.
    params = list(inspect.signature(verify_primary_failure_evidence).parameters)
    assert params == ["evidence", "trusted_context", "validated_settings"]
    # A directly constructed attacker JudgeTrustedContext is just data and cannot
    # be passed to the authoritative path.
    assert isinstance(JudgeTrustedContext, type)


# ---------------------------------------------------------------------------
# P1-2 / P1-3 — trusted RNI builder derives config from validated settings
# ---------------------------------------------------------------------------


def test_rni_builder_signature_has_no_repair_config_or_judge_context() -> None:
    sig = inspect.signature(build_repair_normalized_input)
    assert "trusted_repair_config" not in sig.parameters
    assert "judge_trusted_context" not in sig.parameters
    assert "validated_settings" in sig.parameters


def test_rni_builder_rejects_direct_repair_trusted_config_argument() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _judge_based_pfe(ctx, si, judge_status="REJECT")
    attacker_cfg = RepairTrustedConfig(
        provider="ollama",
        model="attacker-model:1b",
        model_digest="sha256:" + "c" * 64,
        prompt_version="scoring-prompt-v2",
        schema_version="score-result-v2",
        temperature=1.5,
        max_output_tokens=1,
        max_description_chars=0,
        operation="local-scoring-repair-v1",
    )
    with pytest.raises(TypeError):
        build_repair_normalized_input(
            job_id="job-h2a",
            primary_trusted_context=ctx,
            failure_evidence=pfe,
            validated_settings=_settings(),
            trusted_repair_config=attacker_cfg,  # type: ignore[call-arg]
        )


def test_trusted_rni_always_reflects_validated_settings() -> None:
    # The authoritative builder derives every REPAIR config field from the
    # validated settings it is given; no attacker value can enter because there
    # is no config parameter. Vary the settings and confirm the RNI tracks them.
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _judge_based_pfe(ctx, si, judge_status="REJECT")
    settings = _settings(temperature=0.5, max_output_tokens=777, max_description_chars=10)
    rni = build_repair_normalized_input(
        job_id="job-h2a",
        primary_trusted_context=ctx,
        failure_evidence=pfe,
        validated_settings=settings,
    )
    assert rni.repair_provider == "ollama"
    assert rni.repair_model == settings.model
    assert rni.repair_model_digest == settings.expected_model_digest
    assert rni.temperature == settings.temperature
    assert rni.max_output_tokens == settings.max_output_tokens
    assert rni.max_description_chars == settings.max_description_chars
    assert rni.repair_prompt_version == "scoring-prompt-v2"
    assert rni.repair_schema_version == "score-result-v2"
    assert rni.operation == "local-scoring-repair-v1"


def test_judge_reject_pfe_enters_trusted_rni_builder() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _judge_based_pfe(ctx, si, judge_status="REJECT")
    rni = build_repair_normalized_input(
        job_id="job-h2a",
        primary_trusted_context=ctx,
        failure_evidence=pfe,
        validated_settings=_settings(),
    )
    assert rni.primary_failure_class is PrimaryFailureClass.JUDGE_REJECT
    assert rni.repair_model == _MODEL
    assert rni.primary_request_hash == ctx.request_hash


def test_judge_uncertain_pfe_enters_trusted_rni_builder() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _judge_based_pfe(ctx, si, judge_status="UNCERTAIN")
    rni = build_repair_normalized_input(
        job_id="job-h2a",
        primary_trusted_context=ctx,
        failure_evidence=pfe,
        validated_settings=_settings(),
    )
    assert rni.primary_failure_class is PrimaryFailureClass.JUDGE_UNCERTAIN


def test_rni_builder_rejects_pfe_a_with_judge_b() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    from youtube_intel.domain import ContentQualityInput, QualityJudgeOperationInput
    from youtube_intel.quality import build_content_quality_input_hash

    content_b = ContentQualityInput.model_validate(
        {
            "scoring_request_hash": _HASH_C,
            "candidate_hash": _HASH_C,
            "output_language": "en",
            "reason": "A concise candidate reason",
            "topics": ("topic-b",),
            "evidence_registry": (
                {"evidence_id": "title-1", "source": "TITLE", "excerpt": "excerpt for title-1"},
            ),
        }
    )
    operation_b = QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": _HASH_C,
            "attempt_role": "PRIMARY",
            "candidate_hash": _HASH_C,
            "quality_input_hash": build_content_quality_input_hash(content_b),
            "policy_version": _JUDGE_POLICY,
            "prompt_version": _JUDGE_PROMPT,
            "schema_version": _JUDGE_SCHEMA,
            "judge_provider": "ollama",
            "judge_model": _MODEL,
            "judge_model_digest": _DIGEST,
        }
    )
    judge_b = build_judge_evidence(
        role="PRIMARY",
        operation_input=operation_b,
        judge_input=content_b,
        raw_utf8=_judge_raw_for_status("REJECT"),
        model=_MODEL,
        model_digest=_DIGEST,
        policy_version=_JUDGE_POLICY,
        prompt_version=_JUDGE_PROMPT,
        operation_schema_version=_JUDGE_SCHEMA,
    )
    pfe_a = _judge_based_pfe(ctx, si, judge_status="REJECT", judge_evidence=judge_b)
    with pytest.raises(ValueError):
        build_repair_normalized_input(
            job_id="job-h2a",
            primary_trusted_context=ctx,
            failure_evidence=pfe_a,
            validated_settings=_settings(),
        )


def test_rni_builder_requires_validated_settings_exact_type() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _judge_based_pfe(ctx, si, judge_status="REJECT")
    with pytest.raises(ValueError):
        build_repair_normalized_input(
            job_id="job-h2a",
            primary_trusted_context=ctx,
            failure_evidence=pfe,
            validated_settings={"model": _MODEL},  # type: ignore[arg-type]
        )
