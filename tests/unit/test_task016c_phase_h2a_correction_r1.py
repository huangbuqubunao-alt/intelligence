"""TASK-016C Phase H2-A Correction Round 1 — behavioral regression tests.

RED-first behavioral tests reproducing every independent-review finding.  All tests
invoke real production verifier/capture/builder paths (never mere string
comparisons):

- P1-1: protocol-invalid PRIMARY evidence must not be repair-eligible.
- P1-2: JudgeEvidence metadata must be fully bound to operation_input.
- P1-3: PrimaryFailureEvidence provenance must bind to a trusted context.
- P2-4: exact JSON integer typing (StrictInt) rejects bool/float/str.
- P2-5: PRIMARY outer JSON capture rejects duplicate keys.

Authoritative contract: docs/TASK-016C-PHASE-H2-AUTHORIZATION.md.
"""

from __future__ import annotations

import hashlib
import json
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
    H2_ELIGIBLE_PARSER_CODES,
    JudgeEvidence,
    NotApplicableEvidence,
    ParserDiagnosticCode,
    ParserFailureEvidence,
    PrimaryFailureClass,
    PrimaryFailureEvidence,
    RepairNormalizedInput,
    build_judge_evidence,
    build_judge_trusted_context,
    build_primary_trusted_context,
    build_repair_normalized_input,
    canonical_primary_scoring_input_hash,
    replay_primary_parser_failure,
    verify_judge_evidence_replay,
    verify_primary_failure_evidence,
)
from youtube_intel.providers.ollama import (
    diagnose_scoring_parse_failure,
    seal_primary_raw_capture,
)
from youtube_intel.quality import build_content_quality_input_hash
from youtube_intel.scoring import build_scoring_input

_MODEL = "qwen3:8b"
_DIGEST = "sha256:" + "a" * 64
_JUDGE_DIGEST = "sha256:" + "b" * 64
_HASH_B = "b" * 64
_HASH_C = "c" * 64
_HASH_D = "d" * 64
_EN_REASON = "This response explains a concrete product strategy with useful trade-offs."


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
        video_id="video-h2a-r1",
        channel_id="channel-h2a-r1",
        channel_name="H2A R1 Channel",
        title="A useful scoring title",
        description="A deliberately bounded scoring description.",
        source_url="https://example.invalid/watch?v=video-h2a-r1",
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


def _raw_with_inner(inner: object | str) -> str:
    inner_text = inner if isinstance(inner, str) else json.dumps(inner, ensure_ascii=False)
    body = json.dumps(
        {"model": _MODEL, "response": inner_text, "done": True},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return seal_primary_raw_capture(body).utf8


def _eligible_parse_failure_raw() -> str:
    # Valid outer protocol, string response, but the inner scoring model response
    # fails the frozen parser/schema (invalid inner JSON).
    return _raw_with_inner("{not-json")


def _schema_invalid_pfe(ctx=None, scoring_input=None, *, raw=None):
    si = scoring_input if scoring_input is not None else _scoring_input()
    ctx = ctx if ctx is not None else _trusted_context(si)
    raw_body = raw if raw is not None else _eligible_parse_failure_raw()
    parser_ev = replay_primary_parser_failure(raw_body)
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
        primary_raw_utf8=raw_body,
        primary_raw_utf8_length=len(raw_body.encode("utf-8")),
        primary_raw_sha256=hashlib.sha256(raw_body.encode("utf-8")).hexdigest(),
        failure_class=PrimaryFailureClass.SCHEMA_OR_PARSE_INVALID,
        primary_candidate=NotApplicableEvidence(kind="NOT_APPLICABLE"),
        parser_evidence=parser_ev,
        language_evidence=NotApplicableEvidence(kind="NOT_APPLICABLE"),
        judge_evidence=NotApplicableEvidence(kind="NOT_APPLICABLE"),
    )


def _forge_pfe(ctx, si, field, value, *, raw=None):
    base = _schema_invalid_pfe(ctx, si, raw=raw)
    return PrimaryFailureEvidence.model_validate(
        {**base.model_dump(mode="python"), field: value}
    )


# ---------------------------------------------------------------------------
# PART 1A / PART 2 — protocol-invalid PRIMARY evidence is not repair-eligible
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "{bad",
        '{"response":7}',
        "[1]",
    ],
)
def test_protocol_invalid_raw_cannot_be_schema_or_parse_invalid(raw: str) -> None:
    # The parser mapper may emit a pre-capture diagnostic code, but that code is
    # not H2-eligible, and the raw never passes the capture gate.
    code = diagnose_scoring_parse_failure(raw)
    assert code is not None
    assert code not in H2_ELIGIBLE_PARSER_CODES
    with pytest.raises(ValueError):
        seal_primary_raw_capture(raw.encode("utf-8"))


@pytest.mark.parametrize(
    "raw",
    [
        "{bad",
        '{"response":7}',
        "[1]",
    ],
)
def test_verifier_rejects_pfe_built_around_protocol_invalid_raw(raw: str) -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    code = diagnose_scoring_parse_failure(raw)
    assert code is not None
    assert code not in H2_ELIGIBLE_PARSER_CODES
    parser_ev = _parser_evidence_for(raw, code)
    # The eligibility matrix rejects a pre-capture diagnostic code at construction:
    # such a body never became trustworthy received raw evidence.
    with pytest.raises(ValueError):
        PrimaryFailureEvidence(
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
    # The capture gate independently refuses to promote this raw.
    with pytest.raises(ValueError):
        seal_primary_raw_capture(raw.encode("utf-8"))


def _parser_evidence_for(raw: str, code: ParserDiagnosticCode) -> ParserFailureEvidence:
    return ParserFailureEvidence(
        schema_version="task016c-parser-failure-evidence-v1",
        kind="PARSER_FAILURE",
        raw_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        diagnostic_code=code,
    )


def test_eligible_schema_or_parse_invalid_control_case() -> None:
    # Positive control: a protocol-complete body whose inner scoring response fails
    # the frozen parser IS eligible SCHEMA_OR_PARSE_INVALID when it replays exactly.
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _schema_invalid_pfe(ctx, si)
    assert pfe.parser_evidence.diagnostic_code in H2_ELIGIBLE_PARSER_CODES
    verify_primary_failure_evidence(pfe, ctx, _settings())


# ---------------------------------------------------------------------------
# PART 3 / PART 5(duplicate) — duplicate outer JSON keys rejected at capture
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        b'{"response":"first","response":"second"}',
        b'{"response":7,"response":"second"}',
        b'{"model":"m","model":"n","response":"x"}',
    ],
)
def test_capture_rejects_duplicate_outer_keys(body: bytes) -> None:
    with pytest.raises(ValueError):
        seal_primary_raw_capture(body)


def test_duplicate_key_raw_cannot_verify_as_pfe() -> None:
    raw = '{"response":7,"response":"second"}'
    si = _scoring_input()
    ctx = _trusted_context(si)
    code = diagnose_scoring_parse_failure(raw)
    assert code is not None
    pfe = PrimaryFailureEvidence(
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
        parser_evidence=_parser_evidence_for(raw, code),
        language_evidence=NotApplicableEvidence(kind="NOT_APPLICABLE"),
        judge_evidence=NotApplicableEvidence(kind="NOT_APPLICABLE"),
    )
    with pytest.raises(ValueError):
        verify_primary_failure_evidence(pfe, ctx, _settings())


# ---------------------------------------------------------------------------
# PART 5 / PART 7 — PRIMARY provenance forgery rejected against trusted context
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("primary_request_hash", _HASH_D),
        ("primary_normalized_input_hash", _HASH_D),
        ("primary_provider", "attacker-provider"),
        ("primary_model", "attacker-model"),
        ("primary_model_digest", "sha256:" + "c" * 64),
        ("primary_prompt_version", "scoring-prompt-v1"),
        ("primary_schema_version", "score-result-v1"),
        ("primary_temperature", 0.5),
        ("primary_max_output_tokens", 999),
        ("primary_max_description_chars", 999),
    ],
)
def test_pfe_provenance_forgery_rejected(field: str, value: object) -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    forged = _forge_pfe(ctx, si, field, value)
    with pytest.raises(ValueError):
        verify_primary_failure_evidence(forged, ctx, _settings())


def test_pfe_attempt_identity_forgery_rejected_at_construction() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    base = _schema_invalid_pfe(ctx, si)
    payload = {**base.model_dump(mode="python"), "primary_attempt_identity": "local-scoring-repair-v1"}
    with pytest.raises(ValueError):
        PrimaryFailureEvidence.model_validate(payload)


def test_pfe_output_language_forgery_rejected_at_construction() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    base = _schema_invalid_pfe(ctx, si)
    payload = {**base.model_dump(mode="python"), "primary_output_language": "fr"}
    with pytest.raises(ValueError):
        PrimaryFailureEvidence.model_validate(payload)


def test_pfe_scoring_input_substitution_rejected() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    other_input = _scoring_input(output_language="zh-CN")
    forged = _forge_pfe(ctx, si, "primary_scoring_input", other_input)
    with pytest.raises(ValueError):
        verify_primary_failure_evidence(forged, ctx, _settings())


# ---------------------------------------------------------------------------
# PART 6 — primary_scoring_input_sha256 rederivation (frozen serializer)
# ---------------------------------------------------------------------------


def test_primary_scoring_input_sha256_forgery_rejected() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    forged = _forge_pfe(ctx, si, "primary_scoring_input_sha256", _HASH_D)
    with pytest.raises(ValueError):
        verify_primary_failure_evidence(forged, ctx, _settings())


def test_primary_scoring_input_sha256_uses_frozen_serializer_not_jcs() -> None:
    si = _scoring_input()
    # The frozen PRIMARY identity serializer is json.dumps sort-keys, not H2 JCS.
    frozen_bytes = json.dumps(
        si.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    expected = hashlib.sha256(frozen_bytes).hexdigest()
    assert canonical_primary_scoring_input_hash(si) == expected
    ctx = _trusted_context(si)
    assert ctx.scoring_input_sha256 == expected


# ---------------------------------------------------------------------------
# PART 8 / PART 9 — RNI derives from trusted context; forged PFE rejected
# ---------------------------------------------------------------------------


def test_rni_builder_rejects_forged_pfe() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    forged_pfe = _forge_pfe(ctx, si, "primary_request_hash", _HASH_D)
    with pytest.raises(ValueError):
        build_repair_normalized_input(
            job_id="job-h2a",
            primary_trusted_context=ctx,
            failure_evidence=forged_pfe,
            validated_settings=_settings(),
        )


def test_rni_builder_rejects_mismatched_scoring_input() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _schema_invalid_pfe(ctx, si)
    other_input = _scoring_input(output_language="zh-CN")
    other_ctx = _trusted_context(other_input)
    with pytest.raises(ValueError):
        build_repair_normalized_input(
            job_id="job-h2a",
            primary_trusted_context=other_ctx,
            failure_evidence=pfe,
            validated_settings=_settings(),
        )


def test_rni_builder_derives_authoritative_bindings() -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _schema_invalid_pfe(ctx, si)
    settings = _settings()
    rni = build_repair_normalized_input(
        job_id="job-h2a",
        primary_trusted_context=ctx,
        failure_evidence=pfe,
        validated_settings=settings,
    )
    assert rni.primary_request_hash == ctx.request_hash
    assert rni.primary_normalized_input_hash == ctx.normalized_input_hash
    assert rni.primary_attempt_identity == "local-scoring"
    assert rni.primary_failure_class is pfe.failure_class
    assert rni.primary_raw_sha256 == pfe.primary_raw_sha256
    assert rni.repair_model == settings.model
    assert rni.repair_model_digest == settings.expected_model_digest


# ---------------------------------------------------------------------------
# PART 10 / PART 11 — JudgeEvidence metadata bound to operation_input
# ---------------------------------------------------------------------------


def _judge_fixture(raw_status: str = "PASS"):
    content = ContentQualityInput.model_validate(
        {
            "scoring_request_hash": _HASH_B,
            "candidate_hash": _HASH_B,
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
    qih = build_content_quality_input_hash(content)
    operation = QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": _HASH_B,
            "attempt_role": QualityJudgeAttemptRole.PRIMARY,
            "candidate_hash": _HASH_B,
            "quality_input_hash": qih,
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v3",
            "schema_version": "content-quality-result-v1",
            "judge_provider": "ollama",
            "judge_model": _MODEL,
            "judge_model_digest": _JUDGE_DIGEST,
        }
    )
    raw = _judge_raw_for_status(raw_status)
    evidence = build_judge_evidence(
        role="PRIMARY",
        operation_input=operation,
        judge_input=content,
        raw_utf8=raw,
        model=_MODEL,
        model_digest=_JUDGE_DIGEST,
        policy_version="content-quality-policy-v1",
        prompt_version="content-quality-prompt-v3",
        operation_schema_version="content-quality-result-v1",
    )
    judge_ctx = build_judge_trusted_context(
        role="PRIMARY",
        judge_input=content,
        provider="ollama",
        model=_MODEL,
        model_digest=_JUDGE_DIGEST,
        policy_version="content-quality-policy-v1",
        prompt_version="content-quality-prompt-v3",
        operation_schema_version="content-quality-result-v1",
    )
    return operation, content, evidence, judge_ctx


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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider", "attacker-provider"),
        ("model", "attacker-model"),
        ("model_digest", "sha256:" + "c" * 64),
        ("policy_version", "content-quality-policy-v2"),
            ("prompt_version", "content-quality-prompt-v4"),
        ("operation_schema_version", "content-quality-result-v2"),
    ],
)
def test_judge_metadata_forgery_rejected(field: str, value: str) -> None:
    _, _, evidence, judge_ctx = _judge_fixture()
    forged = JudgeEvidence.model_validate(
        {**evidence.model_dump(mode="python"), field: value}
    )
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(forged, judge_ctx)


def test_judge_operation_input_changed_metadata_original_rejected() -> None:
    operation, content, evidence, judge_ctx = _judge_fixture()
    # Change operation_input's judge_model while evidence.model stays original.
    new_operation = QualityJudgeOperationInput.model_validate(
        {**operation.model_dump(mode="python"), "judge_model": "other-model:1b"}
    )
    forged = JudgeEvidence.model_validate(
        {**evidence.model_dump(mode="python"), "operation_input": new_operation.model_dump(mode="python")}
    )
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(forged, judge_ctx)


# ---------------------------------------------------------------------------
# PART 12 — candidate/request/input cross-binding
# ---------------------------------------------------------------------------


def test_judge_candidate_hash_substitution_rejected() -> None:
    operation, content, evidence, judge_ctx = _judge_fixture()
    # operation_input claims a different candidate_hash than judge_input carries.
    new_operation = QualityJudgeOperationInput.model_validate(
        {**operation.model_dump(mode="python"), "candidate_hash": _HASH_C}
    )
    forged = JudgeEvidence.model_validate(
        {**evidence.model_dump(mode="python"), "operation_input": new_operation.model_dump(mode="python")}
    )
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(forged, judge_ctx)


def test_judge_scoring_request_hash_substitution_rejected() -> None:
    operation, content, evidence, judge_ctx = _judge_fixture()
    new_operation = QualityJudgeOperationInput.model_validate(
        {**operation.model_dump(mode="python"), "scoring_request_hash": _HASH_C}
    )
    forged = JudgeEvidence.model_validate(
        {**evidence.model_dump(mode="python"), "operation_input": new_operation.model_dump(mode="python")}
    )
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(forged, judge_ctx)


def test_primary_judge_evidence_on_repair_operation_rejected() -> None:
    _, content, evidence, judge_ctx = _judge_fixture()
    repair_operation = QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": _HASH_B,
            "attempt_role": QualityJudgeAttemptRole.REPAIR,
            "candidate_hash": _HASH_B,
            "quality_input_hash": build_content_quality_input_hash(content),
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v3",
            "schema_version": "content-quality-result-v1",
            "judge_provider": "ollama",
            "judge_model": _MODEL,
            "judge_model_digest": _JUDGE_DIGEST,
        }
    )
    forged = JudgeEvidence.model_validate(
        {**evidence.model_dump(mode="python"), "operation_input": repair_operation.model_dump(mode="python")}
    )
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(forged, judge_ctx)


# ---------------------------------------------------------------------------
# PART 13 / PART 14 — strict JSON integer typing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_value", [True, False, 1.0, 0.0, "1"])
@pytest.mark.parametrize("field", ["max_output_tokens", "max_description_chars"])
def test_rni_exact_integer_fields_reject_non_integer_json(field: str, bad_value: object) -> None:
    payload = _valid_rni_payload()
    payload[field] = bad_value
    with pytest.raises(ValueError):
        RepairNormalizedInput.model_validate_json(json.dumps(payload))


def _valid_rni_payload() -> dict:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _schema_invalid_pfe(ctx, si)
    rni = build_repair_normalized_input(
        job_id="job-h2a",
        primary_trusted_context=ctx,
        failure_evidence=pfe,
        validated_settings=_settings(),
    )
    return rni.model_dump(mode="json")


@pytest.mark.parametrize("bad_value", [True, False, 1.0, 0.0, "1"])
def test_pfe_raw_length_exact_integer_rejects_non_integer_json(bad_value: object) -> None:
    si = _scoring_input()
    ctx = _trusted_context(si)
    pfe = _schema_invalid_pfe(ctx, si)
    payload = {**pfe.model_dump(mode="json"), "primary_raw_utf8_length": bad_value}
    with pytest.raises(ValueError):
        PrimaryFailureEvidence.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("bad_value", [True, False, 1.0, 0.0, "1"])
def test_judge_raw_length_exact_integer_rejects_non_integer_json(bad_value: object) -> None:
    _, _, evidence, _ = _judge_fixture()
    payload = {**evidence.model_dump(mode="json"), "raw_utf8_length": bad_value}
    with pytest.raises(ValueError):
        JudgeEvidence.model_validate_json(json.dumps(payload))


def test_rni_exact_integer_accepts_valid_zero_and_positive() -> None:
    payload = _valid_rni_payload()
    payload["max_description_chars"] = 0
    assert RepairNormalizedInput.model_validate_json(json.dumps(payload)).max_description_chars == 0
    payload["max_description_chars"] = 1
    assert RepairNormalizedInput.model_validate_json(json.dumps(payload)).max_description_chars == 1
