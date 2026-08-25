"""TASK-016C Phase H2-A — typed evidence schemas, canonical primitives, replay.

RED-first tests for ``youtube_intel.h2_evidence``:

- Test B: existing PRIMARY/Judge identity non-regression and serializer isolation.
- Test C: ``RepairNormalizedInput`` shape, bindings, and canonical identity hash.
- Test D (evidence): independent ``primary_raw_sha256`` / ``primary_raw_utf8_length``
  substitution rejection.
- Test E: parser failure evidence replay over the shared parser.
- Test F: frozen TASK-016B language replay (no second validator).
- Test H (evidence): ``JudgeEvidence`` identity/raw/result replay and role split.

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
    ContentQualityStatus,
    LiveStatus,
    QualityJudgeAttemptRole,
    QualityJudgeOperationInput,
    ScoringCandidate,
    ScoringEvidence,
    ScoringEvidenceSource,
    VideoMetadata,
)
from youtube_intel.h2_evidence import (
    JudgeEvidence,
    LanguageValidationEvidence,
    NotApplicableEvidence,
    ParserFailureEvidence,
    PrimaryFailureClass,
    PrimaryFailureEvidence,
    RepairNormalizedInput,
    build_judge_evidence,
    build_primary_failure_evidence_hash,
    build_repair_normalized_input,
    build_repair_request_hash,
    h2_canonical_bytes,
    h2_canonical_sha256,
    repair_normalized_input_hash,
    replay_language_validation,
    replay_primary_parser_failure,
    verify_h2_sealed_bytes,
    verify_judge_evidence_replay,
    verify_language_evidence_replay,
    verify_parser_evidence_replay,
    verify_primary_failure_evidence,
)
from youtube_intel.h2_jcs import jcs_serialize, jcs_sha256
from youtube_intel.providers.ollama import (
    ParserDiagnosticCode,
    seal_primary_raw_capture,
    verify_judge_model_content,
)
from youtube_intel.quality import (
    build_content_quality_input_hash,
    build_judge_h1_h2,
    build_scoring_candidate_hash,
)
from youtube_intel.scoring import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    build_scoring_input,
    build_scoring_request_identity,
)
from youtube_intel.state import build_provider_request_hash

_MODEL = "qwen3:8b"
_DIGEST = "sha256:" + "a" * 64
_JUDGE_DIGEST = "sha256:" + "b" * 64
_HASH_A = "a" * 64
_HASH_B = "b" * 64
_HASH_C = "c" * 64
_HASH_D = "d" * 64

_EN_REASON = "This response explains a concrete product strategy with useful trade-offs."


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _settings(*, temperature: float = 0.0, max_description_chars: int = 32) -> LocalScoringSettings:
    return LocalScoringSettings(
        model=_MODEL,
        expected_model_digest=_DIGEST,
        temperature=temperature,
        max_output_tokens=1200,
        max_transcript_chars=64,
        max_description_chars=max_description_chars,
    )


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id="video-h2a",
        channel_id="channel-h2a",
        channel_name="H2A Channel",
        title="A useful scoring title",
        description="A deliberately bounded scoring description.",
        source_url="https://example.invalid/watch?v=video-h2a",
        published_at=datetime(2026, 8, 18, tzinfo=UTC),
        duration_seconds=120,
        default_language="en",
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _scoring_input(*, output_language: str = "en", temperature: float = 0.0):
    return build_scoring_input(
        video=_video(),
        transcript_text="This transcript contains enough text for a stable sample.",
        language="en",
        output_language=output_language,
        settings=_settings(temperature=temperature),
    )


def _identity(scoring_input, *, temperature: float = 0.0):
    return build_scoring_request_identity(
        scoring_input=scoring_input,
        model=_MODEL,
        temperature=temperature,
        max_output_tokens=1200,
        max_description_chars=32,
    )


def _candidate(*, reason: str = _EN_REASON, score: float = 8.0) -> ScoringCandidate:
    return ScoringCandidate.model_validate(
        {
            "score": score,
            "reason": reason,
            "topics": ["product strategy"],
            "should_summarize": True,
        }
    )


def _valid_rni(**overrides):
    scoring_input = _scoring_input()
    identity = _identity(scoring_input)
    kwargs = {
        "job_id": "job-h2a",
        "scoring_input": scoring_input,
        "primary_request_hash": identity.request_hash,
        "primary_normalized_input_hash": identity.normalized_input_hash,
        "primary_failure_class": PrimaryFailureClass.SCHEMA_OR_PARSE_INVALID,
        "primary_failure_evidence_hash": _HASH_B,
        "primary_raw_sha256": _HASH_C,
        "repair_model": _MODEL,
        "repair_model_digest": _DIGEST,
        "temperature": 0.0,
        "max_output_tokens": 1200,
        "max_description_chars": 32,
    }
    kwargs.update(overrides)
    return build_repair_normalized_input(**kwargs)


def _schema_invalid_raw() -> str:
    body = json.dumps(
        {"model": _MODEL, "response": "{not-json", "done": True},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return seal_primary_raw_capture(body).utf8


def _multibyte_raw() -> str:
    # Schema-invalid (score out of range) but containing multibyte Chinese text so
    # the character count differs from the strict-UTF-8 byte count.
    inner = json.dumps(
        {
            "score": 99,
            "reason": "包含中文的理由说明，用于构造字节与字符数差异",
            "topics": ["topic"],
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


def _schema_invalid_pfe() -> PrimaryFailureEvidence:
    scoring_input = _scoring_input()
    identity = _identity(scoring_input)
    raw = _schema_invalid_raw()
    parser_ev = replay_primary_parser_failure(raw)
    assert parser_ev is not None
    return PrimaryFailureEvidence(
        schema_version="task016c-primary-failure-evidence-v1",
        primary_attempt_identity="local-scoring",
        primary_request_hash=identity.request_hash,
        primary_normalized_input_hash=identity.normalized_input_hash,
        primary_provider="ollama",
        primary_model=_MODEL,
        primary_model_digest=_DIGEST,
        primary_prompt_version=PROMPT_VERSION,
        primary_schema_version=SCHEMA_VERSION,
        primary_output_language="en",
        primary_temperature=0.0,
        primary_max_output_tokens=1200,
        primary_max_description_chars=32,
        primary_scoring_input=scoring_input,
        primary_scoring_input_sha256=h2_canonical_sha256(scoring_input),
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


def _judge_materials(*, attempt_role=QualityJudgeAttemptRole.PRIMARY, raw_status: str = "PASS"):
    content = ContentQualityInput.model_validate(
        {
            "scoring_request_hash": _HASH_A,
            "candidate_hash": _HASH_A,
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
            "scoring_request_hash": _HASH_A,
            "attempt_role": attempt_role,
            "candidate_hash": _HASH_A,
            "quality_input_hash": qih,
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v1",
            "schema_version": "content-quality-result-v1",
            "judge_provider": "ollama",
            "judge_model": _MODEL,
            "judge_model_digest": _JUDGE_DIGEST,
        }
    )
    raw = _judge_raw_for_status(raw_status)
    return operation, content, raw


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


def _valid_judge_evidence(
    *,
    role: str = "PRIMARY",
    raw_status: str = "PASS",
) -> JudgeEvidence:
    attempt_role = (
        QualityJudgeAttemptRole.PRIMARY if role == "PRIMARY" else QualityJudgeAttemptRole.REPAIR
    )
    operation, content, raw = _judge_materials(attempt_role=attempt_role, raw_status=raw_status)
    return build_judge_evidence(
        role=role,
        operation_input=operation,
        judge_input=content,
        raw_utf8=raw,
        model=_MODEL,
        model_digest=_JUDGE_DIGEST,
        policy_version="content-quality-policy-v1",
        prompt_version="content-quality-prompt-v1",
        operation_schema_version="content-quality-result-v1",
    )


# ---------------------------------------------------------------------------
# Test B — existing identity non-regression and serializer isolation
# ---------------------------------------------------------------------------


def test_h2_jcs_is_a_distinct_serializer_from_the_frozen_canonical_json() -> None:
    value = {"temperature": 1.5e-6, "big": 1e20}
    frozen = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    assert jcs_serialize(value) != frozen
    assert jcs_serialize(value) == b'{"big":100000000000000000000,"temperature":0.0000015}'


def test_primary_normalized_input_hash_uses_frozen_serializer_not_jcs() -> None:
    temperature = 1.5e-6
    scoring_input = _scoring_input(temperature=temperature)
    identity = _identity(scoring_input, temperature=temperature)
    video = scoring_input.video
    sample = scoring_input.sample
    structure = {
        "metadata": [
            video.video_id,
            video.title,
            video.channel_name,
            video.published_at.astimezone(UTC).isoformat(),
            video.duration_seconds,
            video.default_language,
            scoring_input.language,
            video.description[:32],
        ],
        "transcript_content_hash": sample.source_content_hash,
        "sample": {
            "head": sample.head,
            "body": sample.body,
            "tail": sample.tail,
            "selected_char_count": sample.selected_char_count,
            "sampling_version": sample.sampling_version,
        },
        "language": scoring_input.language,
        "output_language": scoring_input.output_language,
        "model": _MODEL,
        "temperature": temperature,
        "max_output_tokens": 1200,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
    }
    frozen_hash = hashlib.sha256(
        json.dumps(structure, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
    ).hexdigest()
    assert identity.normalized_input_hash == frozen_hash
    # The H2 JCS serialization of the same structure must differ, proving the
    # PRIMARY identity is not computed under JCS.
    assert identity.normalized_input_hash != jcs_sha256(structure)


def test_primary_request_hash_builder_is_unchanged() -> None:
    scoring_input = _scoring_input()
    identity = _identity(scoring_input)
    expected = build_provider_request_hash(
        operation="local-scoring",
        normalized_input_hash=identity.normalized_input_hash,
        provider="ollama",
        model=_MODEL,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
    )
    assert identity.request_hash == expected


def test_judge_h1_h2_use_frozen_serializer_not_jcs() -> None:
    operation, _, _ = _judge_materials()
    h1, h2 = build_judge_h1_h2(operation)
    frozen = json.dumps(
        operation.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    assert h1 == hashlib.sha256(frozen).hexdigest()
    assert h2 == build_provider_request_hash(
        operation="local-content-quality-v1",
        normalized_input_hash=h1,
        provider=operation.judge_provider,
        model=operation.judge_model,
        prompt_version=operation.prompt_version,
        schema_version=operation.schema_version,
    )


# ---------------------------------------------------------------------------
# Test C — RepairNormalizedInput
# ---------------------------------------------------------------------------


def test_rni_valid_exact_object_and_deterministic_hash() -> None:
    rni = _valid_rni()
    assert rni.schema_version == "task016c-repair-normalized-input-v1"
    assert rni.role == "REPAIR"
    assert rni.operation == "local-scoring-repair-v1"
    assert rni.video_id == "video-h2a"
    assert repair_normalized_input_hash(rni) == repair_normalized_input_hash(_valid_rni())
    assert repair_normalized_input_hash(rni) == jcs_sha256(rni.model_dump(mode="json"))


def test_rni_request_hash_via_unchanged_builder() -> None:
    rni = _valid_rni()
    expected = build_provider_request_hash(
        operation="local-scoring-repair-v1",
        normalized_input_hash=repair_normalized_input_hash(rni),
        provider="ollama",
        model=_MODEL,
        prompt_version="scoring-prompt-v2",
        schema_version="score-result-v2",
    )
    assert build_repair_request_hash(rni) == expected
    assert build_repair_request_hash(rni) != _identity(_scoring_input()).request_hash


def test_rni_missing_field_rejects() -> None:
    payload = _valid_rni().model_dump(mode="json")
    del payload["primary_raw_sha256"]
    with pytest.raises(ValueError):
        RepairNormalizedInput.model_validate(payload)


def test_rni_unknown_field_rejects() -> None:
    payload = _valid_rni().model_dump(mode="json")
    payload["unexpected"] = 1
    with pytest.raises(ValueError):
        RepairNormalizedInput.model_validate(payload)


def test_rni_wrong_role_rejects() -> None:
    payload = _valid_rni().model_dump(mode="json")
    payload["role"] = "PRIMARY"
    with pytest.raises(ValueError):
        RepairNormalizedInput.model_validate(payload)


def test_rni_wrong_schema_version_rejects() -> None:
    payload = _valid_rni().model_dump(mode="json")
    payload["schema_version"] = "task016c-repair-normalized-input-v2"
    with pytest.raises(ValueError):
        RepairNormalizedInput.model_validate(payload)


def test_rni_negative_max_description_chars_rejects() -> None:
    with pytest.raises(ValueError):
        _valid_rni(max_description_chars=-1)


def test_rni_max_description_chars_zero_is_a_value() -> None:
    rni = _valid_rni(max_description_chars=0)
    assert rni.max_description_chars == 0
    canonical = h2_canonical_bytes(rni)
    assert b'"max_description_chars":0' in canonical


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("operation", "local-scoring"),
        ("primary_attempt_identity", "local-scoring-repair-v1"),
        ("repair_provider", "cloud-llm"),
        ("repair_prompt_version", "scoring-prompt-v1"),
        ("repair_schema_version", "score-result-v1"),
    ],
)
def test_rni_frozen_literal_substitution_rejects(field_name: str, bad_value: str) -> None:
    payload = _valid_rni().model_dump(mode="json")
    payload[field_name] = bad_value
    with pytest.raises(ValueError):
        RepairNormalizedInput.model_validate(payload)


@pytest.mark.parametrize(
    "override",
    [
        {"primary_request_hash": _HASH_D},
        {"primary_normalized_input_hash": _HASH_D},
        {"primary_failure_evidence_hash": _HASH_D},
        {"primary_raw_sha256": _HASH_D},
    ],
)
def test_rni_primary_binding_change_changes_hash(override: dict) -> None:
    base = _valid_rni()
    changed = _valid_rni(**override)
    assert repair_normalized_input_hash(base) != repair_normalized_input_hash(changed)


def test_rni_provider_model_change_changes_hash() -> None:
    base = _valid_rni()
    changed = _valid_rni(repair_model="other-model:1b")
    assert repair_normalized_input_hash(base) != repair_normalized_input_hash(changed)


def test_rni_scoring_input_change_changes_hash() -> None:
    base = _valid_rni()
    other_input = _scoring_input(output_language="zh-CN")
    changed = _valid_rni(scoring_input=other_input)
    assert repair_normalized_input_hash(base) != repair_normalized_input_hash(changed)


def test_rni_scoring_input_sha256_is_h2_canonical() -> None:
    rni = _valid_rni()
    assert rni.scoring_input_sha256 == h2_canonical_sha256(rni.scoring_input)


def test_rni_non_canonical_preimage_rejects_on_sealed_verification() -> None:
    rni = _valid_rni()
    non_canonical = json.dumps(rni.model_dump(mode="json"), indent=2).encode("utf-8")
    with pytest.raises(ValueError):
        verify_h2_sealed_bytes(non_canonical, RepairNormalizedInput)


def test_rni_sealed_canonical_round_trip() -> None:
    rni = _valid_rni()
    sealed = h2_canonical_bytes(rni)
    restored, digest = verify_h2_sealed_bytes(sealed, RepairNormalizedInput)
    assert restored == rni
    assert digest == repair_normalized_input_hash(rni)


def test_rni_derived_hash_mismatch_is_rejected() -> None:
    rni = _valid_rni()
    claimed = "0" * 64
    assert claimed != repair_normalized_input_hash(rni)


# ---------------------------------------------------------------------------
# Test D (evidence) — PRIMARY raw hash / length independent substitution
# ---------------------------------------------------------------------------


def test_primary_raw_sha256_substitution_rejected() -> None:
    pfe = _schema_invalid_pfe()
    forged = PrimaryFailureEvidence.model_validate(
        {**pfe.model_dump(mode="python"), "primary_raw_sha256": _HASH_D}
    )
    with pytest.raises(ValueError):
        verify_primary_failure_evidence(forged)


def test_primary_raw_utf8_length_substitution_rejected_multibyte() -> None:
    scoring_input = _scoring_input()
    identity = _identity(scoring_input)
    raw = _multibyte_raw()
    raw_bytes = raw.encode("utf-8")
    assert len(raw) != len(raw_bytes)  # multibyte fixture requirement
    parser_ev = replay_primary_parser_failure(raw)
    assert parser_ev is not None
    pfe = PrimaryFailureEvidence(
        schema_version="task016c-primary-failure-evidence-v1",
        primary_attempt_identity="local-scoring",
        primary_request_hash=identity.request_hash,
        primary_normalized_input_hash=identity.normalized_input_hash,
        primary_provider="ollama",
        primary_model=_MODEL,
        primary_model_digest=_DIGEST,
        primary_prompt_version=PROMPT_VERSION,
        primary_schema_version=SCHEMA_VERSION,
        primary_output_language="en",
        primary_temperature=0.0,
        primary_max_output_tokens=1200,
        primary_max_description_chars=32,
        primary_scoring_input=scoring_input,
        primary_scoring_input_sha256=h2_canonical_sha256(scoring_input),
        primary_raw_capture_kind="OLLAMA_GENERATE_HTTP_BODY_V1",
        primary_raw_utf8=raw,
        # Correct hash but wrong (character-count) byte length.
        primary_raw_utf8_length=len(raw),
        primary_raw_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        failure_class=PrimaryFailureClass.SCHEMA_OR_PARSE_INVALID,
        primary_candidate=NotApplicableEvidence(kind="NOT_APPLICABLE"),
        parser_evidence=parser_ev,
        language_evidence=NotApplicableEvidence(kind="NOT_APPLICABLE"),
        judge_evidence=NotApplicableEvidence(kind="NOT_APPLICABLE"),
    )
    with pytest.raises(ValueError):
        verify_primary_failure_evidence(pfe)


def test_primary_failure_evidence_valid_verifies() -> None:
    pfe = _schema_invalid_pfe()
    verify_primary_failure_evidence(pfe)
    assert build_primary_failure_evidence_hash(pfe) == h2_canonical_sha256(pfe)


# ---------------------------------------------------------------------------
# Test E — parser failure evidence replay
# ---------------------------------------------------------------------------


def test_parser_replay_seals_stable_diagnostic_code() -> None:
    raw = _schema_invalid_raw()
    evidence = replay_primary_parser_failure(raw)
    assert evidence is not None
    assert evidence.diagnostic_code is ParserDiagnosticCode.MODEL_JSON_INVALID
    assert evidence.raw_sha256 == hashlib.sha256(raw.encode("utf-8")).hexdigest()
    verify_parser_evidence_replay(evidence, raw_utf8=raw)


def test_parser_replay_returns_none_on_successful_parse() -> None:
    inner = json.dumps(
        {"score": 8, "reason": _EN_REASON, "topics": ["t"], "should_summarize": True}
    )
    body = json.dumps(
        {"model": _MODEL, "response": inner, "done": True},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    raw = seal_primary_raw_capture(body).utf8
    assert replay_primary_parser_failure(raw) is None


def test_parser_replay_rejects_forged_diagnostic_code() -> None:
    raw = _schema_invalid_raw()
    evidence = replay_primary_parser_failure(raw)
    assert evidence is not None
    forged = ParserFailureEvidence.model_validate(
        {**evidence.model_dump(mode="python"), "diagnostic_code": "OUTER_JSON_INVALID"}
    )
    with pytest.raises(ValueError):
        verify_parser_evidence_replay(forged, raw_utf8=raw)


def test_parser_replay_rejects_when_raw_actually_parses() -> None:
    inner = json.dumps(
        {"score": 8, "reason": _EN_REASON, "topics": ["t"], "should_summarize": True}
    )
    body = json.dumps(
        {"model": _MODEL, "response": inner, "done": True},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    raw = seal_primary_raw_capture(body).utf8
    forged = ParserFailureEvidence(
        schema_version="task016c-parser-failure-evidence-v1",
        kind="PARSER_FAILURE",
        raw_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        diagnostic_code=ParserDiagnosticCode.MODEL_JSON_INVALID,
    )
    with pytest.raises(ValueError):
        verify_parser_evidence_replay(forged, raw_utf8=raw)


# ---------------------------------------------------------------------------
# Test F — frozen TASK-016B language replay
# ---------------------------------------------------------------------------


def test_language_valid_replay() -> None:
    candidate = _candidate()  # English reason
    evidence = replay_language_validation(candidate=candidate, output_language="en")
    assert evidence.result == "VALID"
    assert evidence.validator_contract == "task016b-scoring-language-validator-v1"
    assert evidence.candidate_sha256 == build_scoring_candidate_hash(candidate)
    verify_language_evidence_replay(evidence, candidate=candidate, output_language="en")


def test_language_invalid_detection_replay() -> None:
    # An unambiguous wrong-script reason for the configured output language.
    candidate = _candidate(reason="这是一个完全用中文撰写的理由说明，没有任何英文内容。")
    evidence = replay_language_validation(candidate=candidate, output_language="en")
    assert evidence.result == "INVALID"
    verify_language_evidence_replay(evidence, candidate=candidate, output_language="en")


def test_language_candidate_hash_mismatch_rejected() -> None:
    candidate = _candidate()
    evidence = replay_language_validation(candidate=candidate, output_language="en")
    forged = LanguageValidationEvidence.model_validate(
        {**evidence.model_dump(mode="python"), "candidate_sha256": _HASH_D}
    )
    with pytest.raises(ValueError):
        verify_language_evidence_replay(forged, candidate=candidate, output_language="en")


def test_language_invalid_forgery_where_validator_passes_rejected() -> None:
    candidate = _candidate()  # validator returns VALID for English/en
    evidence = replay_language_validation(candidate=candidate, output_language="en")
    assert evidence.result == "VALID"
    forged = LanguageValidationEvidence.model_validate(
        {**evidence.model_dump(mode="python"), "result": "INVALID"}
    )
    with pytest.raises(ValueError):
        verify_language_evidence_replay(forged, candidate=candidate, output_language="en")


def test_language_bad_validator_provenance_rejected() -> None:
    candidate = _candidate()
    evidence = replay_language_validation(candidate=candidate, output_language="en")
    payload = {**evidence.model_dump(mode="python"), "validator_contract": "some-other-validator-v9"}
    # The exact typed schema rejects an unknown validator contract literal.
    with pytest.raises(ValueError):
        LanguageValidationEvidence.model_validate(payload)


def test_language_unknown_result_rejected_at_construction() -> None:
    with pytest.raises(ValueError):
        LanguageValidationEvidence(
            schema_version="task016c-language-validation-evidence-v1",
            kind="LANGUAGE_VALIDATION",
            candidate_sha256=_HASH_A,
            output_language="en",
            validator_contract="task016b-scoring-language-validator-v1",
            result="SOMETIMES",
        )


# ---------------------------------------------------------------------------
# Test H (evidence) — JudgeEvidence replay, identity, raw, and role split
# ---------------------------------------------------------------------------


def test_judge_evidence_valid_verifies() -> None:
    evidence = _valid_judge_evidence(role="PRIMARY", raw_status="PASS")
    assert evidence.derived_result.status is ContentQualityStatus.PASS
    verify_judge_evidence_replay(evidence)


def test_judge_evidence_reject_and_uncertain_replay() -> None:
    for status in ("REJECT", "UNCERTAIN"):
        evidence = _valid_judge_evidence(role="PRIMARY", raw_status=status)
        assert evidence.derived_result.status is ContentQualityStatus(status)
        verify_judge_evidence_replay(evidence)


@pytest.mark.parametrize(
    ("sealed_status", "raw_status"),
    [
        ("REJECT", "PASS"),
        ("REJECT", "UNCERTAIN"),
        ("UNCERTAIN", "PASS"),
        ("UNCERTAIN", "REJECT"),
    ],
)
def test_judge_label_mismatch_raw_replay_rejected(sealed_status: str, raw_status: str) -> None:
    operation, content, raw = _judge_materials(raw_status=raw_status)
    forged_result = verify_judge_model_content(
        _judge_raw_for_status(sealed_status),
        operation_input=operation,
        content_input=content,
    )
    assert forged_result.status is ContentQualityStatus(sealed_status)
    h1, h2 = build_judge_h1_h2(operation)
    raw_bytes = raw.encode("utf-8")
    evidence = JudgeEvidence(
        evidence_schema_version="task016c-judge-evidence-v1",
        role="PRIMARY",
        judge_h1=h1,
        judge_h2=h2,
        provider="ollama",
        model=_MODEL,
        model_digest=_JUDGE_DIGEST,
        policy_version="content-quality-policy-v1",
        prompt_version="content-quality-prompt-v1",
        operation_schema_version="content-quality-result-v1",
        operation="local-content-quality-v1",
        operation_input=operation,
        judge_input=content,
        judge_input_sha256=build_content_quality_input_hash(content),
        raw_capture_kind="EXTRACTED_OLLAMA_RESPONSE_TEXT_V1",
        raw_utf8=raw,
        raw_utf8_length=len(raw_bytes),
        raw_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        derived_result=forged_result,
    )
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(evidence)


def test_judge_forged_h1_rejected() -> None:
    evidence = _valid_judge_evidence()
    forged = JudgeEvidence.model_validate(
        {**evidence.model_dump(mode="python"), "judge_h1": _HASH_D}
    )
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(forged)


def test_judge_forged_h2_rejected() -> None:
    evidence = _valid_judge_evidence()
    forged = JudgeEvidence.model_validate(
        {**evidence.model_dump(mode="python"), "judge_h2": _HASH_D}
    )
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(forged)


def test_judge_raw_hash_mismatch_rejected() -> None:
    evidence = _valid_judge_evidence()
    forged = JudgeEvidence.model_validate(
        {**evidence.model_dump(mode="python"), "raw_sha256": _HASH_D}
    )
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(forged)


def test_judge_raw_byte_length_mismatch_rejected() -> None:
    evidence = _valid_judge_evidence()
    forged = JudgeEvidence.model_validate(
        {**evidence.model_dump(mode="python"), "raw_utf8_length": evidence.raw_utf8_length + 1}
    )
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(forged)


def test_primary_role_evidence_substituted_into_repair_rejected() -> None:
    primary_evidence = _valid_judge_evidence(role="PRIMARY", raw_status="PASS")
    relabelled = JudgeEvidence.model_validate(
        {**primary_evidence.model_dump(mode="python"), "role": "REPAIR"}
    )
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(relabelled)


def test_repair_role_evidence_substituted_into_primary_rejected() -> None:
    repair_evidence = _valid_judge_evidence(role="REPAIR", raw_status="PASS")
    relabelled = JudgeEvidence.model_validate(
        {**repair_evidence.model_dump(mode="python"), "role": "PRIMARY"}
    )
    with pytest.raises(ValueError):
        verify_judge_evidence_replay(relabelled)


def test_repair_role_evidence_is_role_distinct_identity() -> None:
    primary = _valid_judge_evidence(role="PRIMARY", raw_status="PASS")
    repair = _valid_judge_evidence(role="REPAIR", raw_status="PASS")
    assert primary.judge_h1 != repair.judge_h1
    assert primary.judge_h2 != repair.judge_h2
    verify_judge_evidence_replay(repair)


def test_judge_evidence_sealed_round_trip() -> None:
    evidence = _valid_judge_evidence()
    sealed = h2_canonical_bytes(evidence)
    restored, digest = verify_h2_sealed_bytes(sealed, JudgeEvidence)
    assert restored == evidence
    assert digest == hashlib.sha256(sealed).hexdigest()
