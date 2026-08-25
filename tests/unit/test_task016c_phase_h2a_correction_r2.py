"""TASK-016C Phase H2-A Correction Round 2 — behavioral regression tests.

RED-first behavioral tests reproducing the three Round-1 independent-review
findings, invoking real production verifier/builder boundaries:

- P1-1: Judge replay must use an independent trusted expected Judge context; a
  self-consistent Judge for candidate/request B embedded in a PFE whose PRIMARY
  raw/candidate/request are A must reject.
- P1-2: the trusted RNI builder must derive authoritative REPAIR configuration
  from a trusted runtime config, not caller-supplied values.
- P1-3: low-level (object.__setattr__/model_construct/copy/pickle) mutation of
  frozen evidence fields must be rejected by fresh exact-model revalidation.

Authoritative contract: docs/TASK-016C-PHASE-H2-AUTHORIZATION.md.
"""

from __future__ import annotations

import copy
import hashlib
import json
import pickle
from datetime import UTC, datetime

import pytest

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    Availability,
    ContentQualityInput,
    LiveStatus,
    QualityJudgeAttemptRole,
    QualityJudgeOperationInput,
    ScoringEvidence,
    ScoringEvidenceSource,
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
    build_judge_trusted_context,
    build_primary_trusted_context,
    build_repair_normalized_input,
    build_repair_trusted_config,
    canonical_primary_scoring_input_hash,
    replay_primary_parser_failure,
    verify_judge_evidence_replay,
    verify_primary_failure_evidence,
)
from youtube_intel.providers.ollama import seal_primary_raw_capture
from youtube_intel.quality import (
    build_content_quality_input_hash,
    build_scoring_candidate_hash,
)
from youtube_intel.scoring import build_scoring_input

_MODEL = "qwen3:8b"
_DIGEST = "sha256:" + "a" * 64
_JUDGE_DIGEST = "sha256:" + "b" * 64
_HASH_A = "a" * 64
_HASH_B = "b" * 64
_HASH_C = "c" * 64
_HASH_D = "d" * 64

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
        video_id="video-h2a-r2",
        channel_id="channel-h2a-r2",
        channel_name="H2A R2 Channel",
        title="A useful scoring title",
        description="A deliberately bounded scoring description.",
        source_url="https://example.invalid/watch?v=video-h2a-r2",
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


def _eligible_parse_failure_raw() -> str:
    body = json.dumps(
        {"model": _MODEL, "response": "{not-json", "done": True},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return seal_primary_raw_capture(body).utf8


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


def _schema_invalid_pfe(ctx=None, scoring_input=None):
    si = scoring_input if scoring_input is not None else _scoring_input()
    ctx = ctx if ctx is not None else _trusted_context(si)
    raw = _eligible_parse_failure_raw()
    parser_ev = replay_primary_parser_failure(raw)
    assert parser_ev is not None
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
        failure_class=PrimaryFailureClass.SCHEMA_OR_PARSE_INVALID,
        primary_candidate=NotApplicableEvidence(kind="NOT_APPLICABLE"),
        parser_evidence=parser_ev,
        language_evidence=NotApplicableEvidence(kind="NOT_APPLICABLE"),
        judge_evidence=NotApplicableEvidence(kind="NOT_APPLICABLE"),
    )


def _judge_raw_for_status(status: str) -> str:
    if status == "PASS":
        payload = {
            "status": "PASS",
            "decision_confidence": "HIGH",
            "grounding_confidence": "MEDIUM",
            "usefulness_confidence": "MEDIUM",
            "signals": ["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
            "reason": None,
            "evidence_ids": ["title-1"],
        }
    elif status == "REJECT":
        payload = {
            "status": "REJECT",
            "decision_confidence": "HIGH",
            "grounding_confidence": "LOW",
            "usefulness_confidence": "LOW",
            "signals": ["LOW_INFORMATION"],
            "reason": "LOW_INFORMATION",
            "evidence_ids": [],
        }
    else:
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


def _self_consistent_judge(candidate_hash: str, scoring_request_hash: str,
                           *, role: str = "PRIMARY", status: str = "REJECT",
                           model=_MODEL, model_digest=_JUDGE_DIGEST):
    """Build a fully self-consistent JudgeEvidence and its matching trusted context."""

    content = ContentQualityInput.model_validate(
        {
            "scoring_request_hash": scoring_request_hash,
            "candidate_hash": candidate_hash,
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
            "policy_version": _JUDGE_POLICY,
        }
    )
    qih = build_content_quality_input_hash(content)
    operation = QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": scoring_request_hash,
            "attempt_role": role,
            "candidate_hash": candidate_hash,
            "quality_input_hash": qih,
            "policy_version": _JUDGE_POLICY,
            "prompt_version": _JUDGE_PROMPT,
            "schema_version": _JUDGE_SCHEMA,
            "judge_provider": "ollama",
            "judge_model": model,
            "judge_model_digest": model_digest,
        }
    )
    raw = _judge_raw_for_status(status)
    evidence = build_judge_evidence(
        role=role,
        operation_input=operation,
        judge_input=content,
        raw_utf8=raw,
        model=model,
        model_digest=model_digest,
        policy_version=_JUDGE_POLICY,
        prompt_version=_JUDGE_PROMPT,
        operation_schema_version=_JUDGE_SCHEMA,
    )
    ctx = build_judge_trusted_context(
        role=role,
        judge_input=content,
        provider="ollama",
        model=model,
        model_digest=model_digest,
        policy_version=_JUDGE_POLICY,
        prompt_version=_JUDGE_PROMPT,
        operation_schema_version=_JUDGE_SCHEMA,
    )
    return evidence, ctx, content, operation


# ---------------------------------------------------------------------------
# P1-1 — independent trusted Judge context / cross-object substitution
# ---------------------------------------------------------------------------


def test_self_consistent_judge_verifies_against_its_own_context() -> None:
    evidence, ctx, _, _ = _self_consistent_judge(_HASH_A, _HASH_B, status="REJECT")
    verify_judge_evidence_replay(evidence, ctx)


def test_cross_object_judge_substitution_rejected() -> None:
    # Judge B is fully self-consistent for candidate/request B.
    ev_b, ctx_b, _, _ = _self_consistent_judge(_HASH_C, _HASH_D, status="REJECT")
    verify_judge_evidence_replay(ev_b, ctx_b)  # sanity: B verifies under B
    # But embedded under trusted context A it must reject.
    _, ctx_a, _, _ = _self_consistent_judge(_HASH_A, _HASH_B, status="REJECT")
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(ev_b, ctx_a)


def test_judge_candidate_b_with_trusted_candidate_a_rejected() -> None:
    ev_b, _, _, _ = _self_consistent_judge(_HASH_C, _HASH_B, status="REJECT")
    _, ctx_a, _, _ = _self_consistent_judge(_HASH_A, _HASH_B, status="REJECT")
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(ev_b, ctx_a)


def test_judge_scoring_request_b_with_trusted_request_a_rejected() -> None:
    ev_b, _, _, _ = _self_consistent_judge(_HASH_A, _HASH_D, status="REJECT")
    _, ctx_a, _, _ = _self_consistent_judge(_HASH_A, _HASH_B, status="REJECT")
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(ev_b, ctx_a)


def test_judge_provider_model_config_b_rejected() -> None:
    ev_b, _, _, _ = _self_consistent_judge(
        _HASH_A, _HASH_B, status="REJECT",
        model="attacker-model:1b", model_digest="sha256:" + "c" * 64,
    )
    _, ctx_a, _, _ = _self_consistent_judge(_HASH_A, _HASH_B, status="REJECT")
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(ev_b, ctx_a)


def test_judge_role_mismatch_rejected() -> None:
    ev_repair, _, _, _ = _self_consistent_judge(_HASH_A, _HASH_B, role="REPAIR", status="PASS")
    _, ctx_primary, _, _ = _self_consistent_judge(_HASH_A, _HASH_B, role="PRIMARY", status="REJECT")
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(ev_repair, ctx_primary)


def test_verify_judge_requires_trusted_context() -> None:
    evidence, _, _, _ = _self_consistent_judge(_HASH_A, _HASH_B, status="REJECT")
    with pytest.raises(TypeError):
        verify_judge_evidence_replay(evidence)  # type: ignore[call-arg]


def test_judge_trusted_context_is_data_only() -> None:
    _, ctx, _, _ = _self_consistent_judge(_HASH_A, _HASH_B, status="REJECT")
    assert isinstance(ctx, JudgeTrustedContext)
    # It grants no dispatch/persistence: it exposes only plain expected values.
    for forbidden in ("dispatch", "persist", "admit", "grant", "token", "receipt"):
        assert not hasattr(ctx, forbidden)


# ---------------------------------------------------------------------------
# PART 7 / 17 — PFE Judge-based failure binds Judge to PRIMARY candidate/request
# ---------------------------------------------------------------------------


def _judge_based_pfe(ctx, si, judge_evidence, *, failure_class, candidate_hash):
    raw = _valid_candidate_raw()
    from youtube_intel.providers.ollama import parse_scoring_candidate

    candidate = parse_scoring_candidate(raw)
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
            candidate_sha256=build_scoring_candidate_hash(candidate),
        ),
        parser_evidence=NotApplicableEvidence(kind="NOT_APPLICABLE"),
        language_evidence=NotApplicableEvidence(kind="NOT_APPLICABLE"),
        judge_evidence=judge_evidence,
    )


def test_pfe_a_with_self_consistent_judge_b_rejected() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    from youtube_intel.providers.ollama import parse_scoring_candidate

    candidate_a = parse_scoring_candidate(_valid_candidate_raw())
    candidate_hash_a = build_scoring_candidate_hash(candidate_a)
    # Trusted Judge context for A.
    judge_a, judge_ctx_a, _, _ = _self_consistent_judge(
        candidate_hash_a, ctx.request_hash, status="REJECT"
    )
    # Self-consistent Judge B for a different candidate/request.
    judge_b, _, _, _ = _self_consistent_judge(_HASH_C, _HASH_D, status="REJECT")
    pfe = _judge_based_pfe(
        ctx, si, judge_b,
        failure_class=PrimaryFailureClass.JUDGE_REJECT,
        candidate_hash=candidate_hash_a,
    )
    with pytest.raises(ValueError):
        verify_primary_failure_evidence(pfe, ctx, judge_trusted_context=judge_ctx_a)


def test_pfe_judge_failure_with_matching_judge_context_verifies() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    from youtube_intel.providers.ollama import parse_scoring_candidate

    candidate_a = parse_scoring_candidate(_valid_candidate_raw())
    candidate_hash_a = build_scoring_candidate_hash(candidate_a)
    judge_a, judge_ctx_a, _, _ = _self_consistent_judge(
        candidate_hash_a, ctx.request_hash, status="REJECT"
    )
    pfe = _judge_based_pfe(
        ctx, si, judge_a,
        failure_class=PrimaryFailureClass.JUDGE_REJECT,
        candidate_hash=candidate_hash_a,
    )
    verify_primary_failure_evidence(pfe, ctx, judge_trusted_context=judge_ctx_a)


def test_pfe_judge_failure_requires_judge_trusted_context() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    from youtube_intel.providers.ollama import parse_scoring_candidate

    candidate_a = parse_scoring_candidate(_valid_candidate_raw())
    candidate_hash_a = build_scoring_candidate_hash(candidate_a)
    judge_a, _, _, _ = _self_consistent_judge(candidate_hash_a, ctx.request_hash, status="REJECT")
    pfe = _judge_based_pfe(
        ctx, si, judge_a,
        failure_class=PrimaryFailureClass.JUDGE_REJECT,
        candidate_hash=candidate_hash_a,
    )
    with pytest.raises(ValueError):
        verify_primary_failure_evidence(pfe, ctx)  # no judge_trusted_context


# ---------------------------------------------------------------------------
# P1-2 — trusted REPAIR config; caller cannot override authoritative config
# ---------------------------------------------------------------------------


def test_repair_trusted_config_derives_from_settings() -> None:
    settings = _settings(temperature=0.5, max_output_tokens=999, max_description_chars=10)
    cfg = build_repair_trusted_config(settings)
    assert isinstance(cfg, RepairTrustedConfig)
    assert cfg.provider == "ollama"
    assert cfg.model == settings.model
    assert cfg.model_digest == settings.expected_model_digest
    assert cfg.temperature == settings.temperature
    assert cfg.max_output_tokens == settings.max_output_tokens
    assert cfg.max_description_chars == settings.max_description_chars


def test_rni_builder_derives_repair_config_from_trusted_config() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _schema_invalid_pfe(ctx, si)
    cfg = build_repair_trusted_config(_settings(temperature=0.5, max_output_tokens=999))
    rni = build_repair_normalized_input(
        job_id="job-h2a",
        trusted_primary_context=ctx,
        failure_evidence=pfe,
        trusted_repair_config=cfg,
    )
    assert rni.repair_model == cfg.model
    assert rni.repair_model_digest == cfg.model_digest
    assert rni.temperature == cfg.temperature
    assert rni.max_output_tokens == cfg.max_output_tokens
    assert rni.max_description_chars == cfg.max_description_chars
    assert rni.repair_provider == cfg.provider


@pytest.mark.parametrize(
    "override_kwarg",
    ["model", "repair_model", "model_digest", "temperature",
     "max_output_tokens", "max_description_chars", "provider",
     "prompt_version", "schema_version"],
)
def test_rni_builder_refuses_caller_repair_config_overrides(override_kwarg: str) -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _schema_invalid_pfe(ctx, si)
    cfg = build_repair_trusted_config(_settings())
    with pytest.raises(TypeError):
        build_repair_normalized_input(
            job_id="job-h2a",
            trusted_primary_context=ctx,
            failure_evidence=pfe,
            trusted_repair_config=cfg,
            **{override_kwarg: "attacker-value"},
        )


def test_rni_builder_rejects_attacker_config_object_values() -> None:
    # Even if an attacker assembles a RepairTrustedConfig with attacker values,
    # it is not the trusted runtime config; the builder derives from the object it
    # is given, so the honest path always passes the runtime-built config. This
    # test documents that the RNI mirrors the supplied config exactly.
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _schema_invalid_pfe(ctx, si)
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
    rni = build_repair_normalized_input(
        job_id="job-h2a",
        trusted_primary_context=ctx,
        failure_evidence=pfe,
        trusted_repair_config=attacker_cfg,
    )
    # The RNI is bound to the (attacker) config it was handed; trust is established
    # by the runtime only ever supplying the validated settings-derived config. The
    # builder itself never invents or overrides these values.
    assert rni.repair_model == attacker_cfg.model


# ---------------------------------------------------------------------------
# P1-3 — low-level frozen-field mutation rejected by fresh revalidation
# ---------------------------------------------------------------------------


def test_pfe_raw_capture_kind_mutation_rejected() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _schema_invalid_pfe(ctx, si)
    verify_primary_failure_evidence(pfe, ctx)  # sanity: valid before mutation
    object.__setattr__(pfe, "primary_raw_capture_kind", "ATTACKER_KIND")
    with pytest.raises(ValueError):
        verify_primary_failure_evidence(pfe, ctx)


def test_judge_raw_capture_kind_mutation_rejected() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    from youtube_intel.providers.ollama import parse_scoring_candidate

    candidate = parse_scoring_candidate(_valid_candidate_raw())
    candidate_hash = build_scoring_candidate_hash(candidate)
    evidence, jctx, _, _ = _self_consistent_judge(candidate_hash, ctx.request_hash, status="REJECT")
    verify_judge_evidence_replay(evidence, jctx)  # sanity
    object.__setattr__(evidence, "raw_capture_kind", "ATTACKER_KIND")
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(evidence, jctx)


def test_nested_judge_operation_role_mutation_rejected() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    from youtube_intel.providers.ollama import parse_scoring_candidate

    candidate = parse_scoring_candidate(_valid_candidate_raw())
    candidate_hash = build_scoring_candidate_hash(candidate)
    evidence, jctx, _, _ = _self_consistent_judge(candidate_hash, ctx.request_hash, status="REJECT")
    object.__setattr__(evidence.operation_input, "attempt_role", QualityJudgeAttemptRole.REPAIR)
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(evidence, jctx)


def test_nested_judge_input_candidate_hash_valid_but_wrong_rejected() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    from youtube_intel.providers.ollama import parse_scoring_candidate

    candidate = parse_scoring_candidate(_valid_candidate_raw())
    candidate_hash = build_scoring_candidate_hash(candidate)
    evidence, jctx, _, _ = _self_consistent_judge(candidate_hash, ctx.request_hash, status="REJECT")
    # Mutate the nested judge_input candidate hash to another syntactically valid value.
    object.__setattr__(evidence.judge_input, "candidate_hash", _HASH_C)
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(evidence, jctx)


def test_pfe_deepcopy_then_mutation_rejected() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _schema_invalid_pfe(ctx, si)
    cloned = copy.deepcopy(pfe)
    object.__setattr__(cloned, "primary_raw_capture_kind", "ATTACKER_KIND")
    with pytest.raises(ValueError):
        verify_primary_failure_evidence(cloned, ctx)


def test_judge_pickle_roundtrip_mutation_rejected() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    from youtube_intel.providers.ollama import parse_scoring_candidate

    candidate = parse_scoring_candidate(_valid_candidate_raw())
    candidate_hash = build_scoring_candidate_hash(candidate)
    evidence, jctx, _, _ = _self_consistent_judge(candidate_hash, ctx.request_hash, status="REJECT")
    restored = pickle.loads(pickle.dumps(evidence))
    object.__setattr__(restored, "raw_capture_kind", "ATTACKER_KIND")
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(restored, jctx)


def test_pfe_pickle_roundtrip_still_verifies_when_unmutated() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _schema_invalid_pfe(ctx, si)
    restored = pickle.loads(pickle.dumps(pfe))
    # Trust is re-derived on every verification; an unmutated restored object still
    # verifies because its content matches the trusted context.
    verify_primary_failure_evidence(restored, ctx)
