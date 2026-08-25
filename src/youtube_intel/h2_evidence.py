"""TASK-016C Phase H2-A — H2 evidence foundations.

This module implements the H2-A evidence-foundation layer frozen by
``docs/TASK-016C-PHASE-H2-AUTHORIZATION.md``:

- the typed/versioned ``task016c-*`` H2 evidence schemas (data only, never
  authority);
- ``RepairNormalizedInput`` and its canonical H2 identity hashing;
- ``PrimaryFailureEvidence`` and the closed failure-class combination matrix;
- parser / language / Judge evidence replay foundations;
- the canonical validation/hashing primitives:
  ``typed object -> H2 Canonical JSON v1 bytes -> SHA-256`` and
  ``sealed bytes -> strict parse -> typed validation -> JCS reserialize ->
  exact byte equality -> hash verification``.

Everything here is pure and memory-only.  This module does **not** enable
REPAIR dispatch, REPAIR_JUDGE dispatch, public REPAIR admission, persistence,
or any repair capability object.  The frozen PRIMARY / Judge identity builders
are carried as already-derived string fields and are never recomputed under
H2 Canonical JSON v1.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Final, Literal, NoReturn, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from youtube_intel.domain import (
    ContentQualityDecisionSource,
    ContentQualityInput,
    ContentQualityResult,
    ContentQualityStatus,
    QualityJudgeOperationInput,
    ScoringCandidate,
    ScoringInput,
    ScoringLanguageValidation,
    detect_scoring_language_violation,
)
from youtube_intel.h2_jcs import jcs_loads_strict, jcs_serialize, jcs_sha256
from youtube_intel.providers.ollama import (
    ParserDiagnosticCode,
    diagnose_scoring_parse_failure,
    seal_judge_raw_capture,
    verify_judge_model_content,
)
from youtube_intel.quality import (
    build_content_quality_input_hash,
    build_judge_h1_h2,
    build_scoring_candidate_hash,
)
from youtube_intel.state import build_provider_request_hash

__all__ = [
    "CandidateEvidence",
    "JudgeEvidence",
    "LanguageValidationEvidence",
    "NotApplicableEvidence",
    "ParserFailureEvidence",
    "PrimaryFailureClass",
    "PrimaryFailureEvidence",
    "RepairNormalizedInput",
    "build_primary_failure_evidence_hash",
    "build_repair_normalized_input",
    "build_repair_request_hash",
    "h2_canonical_bytes",
    "h2_canonical_sha256",
    "repair_normalized_input_hash",
    "replay_language_validation",
    "replay_primary_parser_failure",
    "verify_h2_sealed_bytes",
    "verify_judge_evidence_replay",
]

_H2_FROZEN: Final = ConfigDict(extra="forbid", frozen=True)
_SHA256_HEX: Final = r"^[0-9a-f]{64}$"
_MODEL_DIGEST: Final = r"^sha256:[0-9a-f]{64}$"

REPAIR_NORMALIZED_INPUT_SCHEMA: Final = "task016c-repair-normalized-input-v1"
PRIMARY_FAILURE_EVIDENCE_SCHEMA: Final = "task016c-primary-failure-evidence-v1"
PARSER_FAILURE_EVIDENCE_SCHEMA: Final = "task016c-parser-failure-evidence-v1"
LANGUAGE_VALIDATION_EVIDENCE_SCHEMA: Final = "task016c-language-validation-evidence-v1"
JUDGE_EVIDENCE_SCHEMA: Final = "task016c-judge-evidence-v1"
CANDIDATE_EVIDENCE_SCHEMA: Final = "task016c-candidate-evidence-v1"

_REPAIR_OPERATION: Final = "local-scoring-repair-v1"
_PRIMARY_ATTEMPT_IDENTITY: Final = "local-scoring"
_LANGUAGE_VALIDATOR_CONTRACT: Final = "task016b-scoring-language-validator-v1"
_JUDGE_RAW_CAPTURE_KIND: Final = "EXTRACTED_OLLAMA_RESPONSE_TEXT_V1"
_PRIMARY_RAW_CAPTURE_KIND: Final = "OLLAMA_GENERATE_HTTP_BODY_V1"
_JUDGE_RAW_MAX_BYTES: Final = 20_000
_PRIMARY_RAW_MAX_BYTES: Final = 1_000_000

_T = TypeVar("_T", bound=BaseModel)


class PrimaryFailureClass(str, Enum):
    """The closed H2 REPAIR-eligible PRIMARY failure classes."""

    SCHEMA_OR_PARSE_INVALID = "SCHEMA_OR_PARSE_INVALID"
    LANGUAGE_INVALID = "LANGUAGE_INVALID"
    JUDGE_REJECT = "JUDGE_REJECT"
    JUDGE_UNCERTAIN = "JUDGE_UNCERTAIN"


# ---------------------------------------------------------------------------
# Canonical validation / hashing primitives
# ---------------------------------------------------------------------------


def h2_canonical_bytes(model: BaseModel) -> bytes:
    """Serialize a validated H2 evidence object to H2 Canonical JSON v1 bytes."""

    return jcs_serialize(model.model_dump(mode="json"))


def h2_canonical_sha256(model: BaseModel) -> str:
    """Return the lowercase SHA-256 of the object's canonical bytes."""

    return jcs_sha256(model.model_dump(mode="json"))


def verify_h2_sealed_bytes(sealed: bytes, model_type: type[_T]) -> tuple[_T, str]:
    """Revalidate sealed H2 evidence bytes into the exact typed schema.

    The flow is exactly: sealed bytes -> strict parse (rejecting duplicate keys)
    -> typed validation (rejecting unknown fields / enums / missing fields) ->
    H2 canonical reserialization -> byte-for-byte equality with the seal ->
    SHA-256.  Semantically equivalent but non-canonical spellings are rejected
    because their reserialization differs from the seal.
    """

    decoded = jcs_loads_strict(sealed)
    model = model_type.model_validate(decoded)
    reserialized = jcs_serialize(model.model_dump(mode="json"))
    if reserialized != bytes(sealed):
        msg = "sealed H2 evidence bytes are not canonical for the typed object"
        raise ValueError(msg)
    return model, hashlib.sha256(bytes(sealed)).hexdigest()


# ---------------------------------------------------------------------------
# Tagged evidence objects
# ---------------------------------------------------------------------------


class NotApplicableEvidence(BaseModel):
    """Exactly ``{"kind":"NOT_APPLICABLE"}``; one string field, no others."""

    model_config = _H2_FROZEN
    kind: Literal["NOT_APPLICABLE"]


class CandidateEvidence(BaseModel):
    """A validated scoring candidate plus its unchanged existing hash."""

    model_config = _H2_FROZEN
    schema_version: Literal["task016c-candidate-evidence-v1"]
    kind: Literal["CANDIDATE"]
    candidate: ScoringCandidate
    candidate_sha256: str = Field(pattern=_SHA256_HEX)


class ParserFailureEvidence(BaseModel):
    """A deterministic parser-failure diagnostic; no exception text."""

    model_config = _H2_FROZEN
    schema_version: Literal["task016c-parser-failure-evidence-v1"]
    kind: Literal["PARSER_FAILURE"]
    raw_sha256: str = Field(pattern=_SHA256_HEX)
    diagnostic_code: ParserDiagnosticCode


class LanguageValidationEvidence(BaseModel):
    """The frozen TASK-016B language validator's result for a candidate."""

    model_config = _H2_FROZEN
    schema_version: Literal["task016c-language-validation-evidence-v1"]
    kind: Literal["LANGUAGE_VALIDATION"]
    candidate_sha256: str = Field(pattern=_SHA256_HEX)
    output_language: Literal["zh-CN", "en"]
    validator_contract: Literal["task016b-scoring-language-validator-v1"]
    result: Literal["VALID", "INVALID", "UNCERTAIN"]


class JudgeEvidence(BaseModel):
    """One exact Judge evidence schema shared by both PRIMARY and REPAIR roles."""

    model_config = _H2_FROZEN
    evidence_schema_version: Literal["task016c-judge-evidence-v1"]
    role: Literal["PRIMARY", "REPAIR"]
    judge_h1: str = Field(pattern=_SHA256_HEX)
    judge_h2: str = Field(pattern=_SHA256_HEX)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    model_digest: str = Field(pattern=_MODEL_DIGEST)
    policy_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    operation_schema_version: str = Field(min_length=1)
    operation: Literal["local-content-quality-v1"]
    operation_input: QualityJudgeOperationInput
    judge_input: ContentQualityInput
    judge_input_sha256: str = Field(pattern=_SHA256_HEX)
    raw_capture_kind: Literal["EXTRACTED_OLLAMA_RESPONSE_TEXT_V1"]
    raw_utf8: str
    raw_utf8_length: int = Field(ge=0, le=20_000)
    raw_sha256: str = Field(pattern=_SHA256_HEX)
    derived_result: ContentQualityResult

    @model_validator(mode="after")
    def _derived_result_is_local_judge(self) -> "JudgeEvidence":
        if self.derived_result.decision_source is not ContentQualityDecisionSource.LOCAL_JUDGE:
            msg = "JudgeEvidence derived_result must have decision_source=LOCAL_JUDGE"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# PrimaryFailureEvidence and the failure-class combination matrix
# ---------------------------------------------------------------------------


class PrimaryFailureEvidence(BaseModel):
    """Complete typed wire contract proving one eligible PRIMARY failure."""

    model_config = _H2_FROZEN
    schema_version: Literal["task016c-primary-failure-evidence-v1"]
    primary_attempt_identity: Literal["local-scoring"]
    primary_request_hash: str = Field(pattern=_SHA256_HEX)
    primary_normalized_input_hash: str = Field(pattern=_SHA256_HEX)
    primary_provider: str = Field(min_length=1)
    primary_model: str = Field(min_length=1)
    primary_model_digest: str = Field(pattern=_MODEL_DIGEST)
    primary_prompt_version: str = Field(min_length=1)
    primary_schema_version: str = Field(min_length=1)
    primary_output_language: Literal["zh-CN", "en"]
    primary_temperature: float = Field(ge=0, le=2, allow_inf_nan=False)
    primary_max_output_tokens: int = Field(gt=0)
    primary_max_description_chars: int = Field(ge=0)
    primary_scoring_input: ScoringInput
    primary_scoring_input_sha256: str = Field(pattern=_SHA256_HEX)
    primary_raw_capture_kind: Literal["OLLAMA_GENERATE_HTTP_BODY_V1"]
    primary_raw_utf8: str
    primary_raw_utf8_length: int = Field(ge=0, le=1_000_000)
    primary_raw_sha256: str = Field(pattern=_SHA256_HEX)
    failure_class: PrimaryFailureClass
    primary_candidate: CandidateEvidence | NotApplicableEvidence
    parser_evidence: ParserFailureEvidence | NotApplicableEvidence
    language_evidence: LanguageValidationEvidence | NotApplicableEvidence
    judge_evidence: JudgeEvidence | NotApplicableEvidence

    @model_validator(mode="after")
    def _failure_class_combination(self) -> "PrimaryFailureEvidence":
        _validate_failure_class_combination(self)
        return self


def _validate_failure_class_combination(evidence: PrimaryFailureEvidence) -> None:
    """Enforce the closed failure-class -> applicable-evidence matrix."""

    failure_class = evidence.failure_class
    candidate = evidence.primary_candidate
    parser = evidence.parser_evidence
    language = evidence.language_evidence
    judge = evidence.judge_evidence

    def _reject(detail: str) -> NoReturn:
        msg = f"failure_class {failure_class.value} evidence mismatch: {detail}"
        raise ValueError(msg)

    if failure_class is PrimaryFailureClass.SCHEMA_OR_PARSE_INVALID:
        if not isinstance(candidate, NotApplicableEvidence):
            _reject("primary_candidate must be NOT_APPLICABLE")
        if not isinstance(parser, ParserFailureEvidence):
            _reject("parser_evidence must be PARSER_FAILURE")
        if not isinstance(language, NotApplicableEvidence):
            _reject("language_evidence must be NOT_APPLICABLE")
        if not isinstance(judge, NotApplicableEvidence):
            _reject("judge_evidence must be NOT_APPLICABLE")
        return

    if failure_class is PrimaryFailureClass.LANGUAGE_INVALID:
        if not isinstance(candidate, CandidateEvidence):
            _reject("primary_candidate must be CANDIDATE")
        if not isinstance(parser, NotApplicableEvidence):
            _reject("parser_evidence must be NOT_APPLICABLE")
        if not isinstance(language, LanguageValidationEvidence):
            _reject("language_evidence must be LANGUAGE_VALIDATION")
        if not isinstance(judge, NotApplicableEvidence):
            _reject("judge_evidence must be NOT_APPLICABLE")
        if language.result != "INVALID":
            _reject("language_evidence result must be INVALID")
        return

    if failure_class in {
        PrimaryFailureClass.JUDGE_REJECT,
        PrimaryFailureClass.JUDGE_UNCERTAIN,
    }:
        if not isinstance(candidate, CandidateEvidence):
            _reject("primary_candidate must be CANDIDATE")
        if not isinstance(parser, NotApplicableEvidence):
            _reject("parser_evidence must be NOT_APPLICABLE")
        if not isinstance(language, NotApplicableEvidence):
            _reject("language_evidence must be NOT_APPLICABLE")
        if not isinstance(judge, JudgeEvidence):
            _reject("judge_evidence must be JUDGE_EVIDENCE")
        if judge.role != "PRIMARY":
            _reject("judge_evidence role must be PRIMARY")
        expected_status = (
            ContentQualityStatus.REJECT
            if failure_class is PrimaryFailureClass.JUDGE_REJECT
            else ContentQualityStatus.UNCERTAIN
        )
        if judge.derived_result.status is not expected_status:
            _reject(f"judge_evidence derived_result.status must be {expected_status.value}")
        return

    msg = f"unknown failure_class {failure_class!r}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# RepairNormalizedInput
# ---------------------------------------------------------------------------


class RepairNormalizedInput(BaseModel):
    """The exact REPAIR normalized-input wire object (H2 canonical identity)."""

    model_config = _H2_FROZEN
    schema_version: Literal["task016c-repair-normalized-input-v1"]
    role: Literal["REPAIR"]
    operation: Literal["local-scoring-repair-v1"]
    job_id: str = Field(min_length=1)
    video_id: str = Field(min_length=1)
    scoring_input: ScoringInput
    scoring_input_sha256: str = Field(pattern=_SHA256_HEX)
    primary_attempt_identity: Literal["local-scoring"]
    primary_request_hash: str = Field(pattern=_SHA256_HEX)
    primary_normalized_input_hash: str = Field(pattern=_SHA256_HEX)
    primary_failure_class: PrimaryFailureClass
    primary_failure_evidence_hash: str = Field(pattern=_SHA256_HEX)
    primary_raw_sha256: str = Field(pattern=_SHA256_HEX)
    repair_provider: Literal["ollama"]
    repair_model: str = Field(min_length=1)
    repair_model_digest: str = Field(pattern=_MODEL_DIGEST)
    repair_prompt_version: Literal["scoring-prompt-v2"]
    repair_schema_version: Literal["score-result-v2"]
    output_language: Literal["zh-CN", "en"]
    temperature: float = Field(ge=0, le=2, allow_inf_nan=False)
    max_output_tokens: int = Field(gt=0)
    max_description_chars: int = Field(ge=0)


def build_repair_normalized_input(
    *,
    job_id: str,
    scoring_input: ScoringInput,
    primary_request_hash: str,
    primary_normalized_input_hash: str,
    primary_failure_class: PrimaryFailureClass,
    primary_failure_evidence_hash: str,
    primary_raw_sha256: str,
    repair_model: str,
    repair_model_digest: str,
    temperature: float,
    max_output_tokens: int,
    max_description_chars: int,
) -> RepairNormalizedInput:
    """Build the exact typed REPAIR normalized-input object.

    The caller supplies the already-derived frozen PRIMARY identity hashes and
    the sealed PRIMARY failure bindings; this builder never recomputes those
    under H2 Canonical JSON.  It only derives the H2-canonical
    ``scoring_input_sha256`` from the embedded validated input.
    """

    return RepairNormalizedInput(
        schema_version=REPAIR_NORMALIZED_INPUT_SCHEMA,
        role="REPAIR",
        operation=_REPAIR_OPERATION,
        job_id=job_id,
        video_id=scoring_input.video.video_id,
        scoring_input=scoring_input,
        scoring_input_sha256=h2_canonical_sha256(scoring_input),
        primary_attempt_identity=_PRIMARY_ATTEMPT_IDENTITY,
        primary_request_hash=primary_request_hash,
        primary_normalized_input_hash=primary_normalized_input_hash,
        primary_failure_class=primary_failure_class,
        primary_failure_evidence_hash=primary_failure_evidence_hash,
        primary_raw_sha256=primary_raw_sha256,
        repair_provider="ollama",
        repair_model=repair_model,
        repair_model_digest=repair_model_digest,
        repair_prompt_version="scoring-prompt-v2",
        repair_schema_version="score-result-v2",
        output_language=scoring_input.output_language,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_description_chars=max_description_chars,
    )


def repair_normalized_input_hash(rni: RepairNormalizedInput) -> str:
    """Return the canonical H2 SHA-256 identity of a validated RNI."""

    return h2_canonical_sha256(rni)


def build_repair_request_hash(rni: RepairNormalizedInput) -> str:
    """Derive the REPAIR ProviderCall request hash via the unchanged builder."""

    return build_provider_request_hash(
        operation=_REPAIR_OPERATION,
        normalized_input_hash=repair_normalized_input_hash(rni),
        provider=rni.repair_provider,
        model=rni.repair_model,
        prompt_version=rni.repair_prompt_version,
        schema_version=rni.repair_schema_version,
    )


def build_primary_failure_evidence_hash(evidence: PrimaryFailureEvidence) -> str:
    """Return the canonical H2 SHA-256 of a validated PrimaryFailureEvidence."""

    return h2_canonical_sha256(evidence)


# ---------------------------------------------------------------------------
# Replay foundations
# ---------------------------------------------------------------------------


def replay_primary_parser_failure(raw_utf8: str) -> ParserFailureEvidence | None:
    """Replay the shared parser over exact PRIMARY raw and seal the diagnostic.

    Returns ``ParserFailureEvidence`` when the exact raw deterministically fails
    parsing, or ``None`` when it parses successfully (disproving any claimed
    schema/parse failure).  The diagnostic code is reproduced by the pure
    current-parser mapper; no exception message is used as authority.
    """

    code = diagnose_scoring_parse_failure(raw_utf8)
    if code is None:
        return None
    raw_sha = hashlib.sha256(raw_utf8.encode("utf-8", errors="strict")).hexdigest()
    return ParserFailureEvidence(
        schema_version=PARSER_FAILURE_EVIDENCE_SCHEMA,
        kind="PARSER_FAILURE",
        raw_sha256=raw_sha,
        diagnostic_code=code,
    )


def verify_parser_evidence_replay(
    evidence: ParserFailureEvidence,
    *,
    raw_utf8: str,
) -> None:
    """Re-run the shared parser over the exact raw and require the sealed code.

    Parser success or a different diagnostic code rejects; the sealed evidence is
    only accepted when the pure current-parser mapper independently reproduces it.
    """

    expected = replay_primary_parser_failure(raw_utf8)
    if expected is None:
        msg = "PRIMARY raw parses successfully; parser failure evidence is disproved"
        raise ValueError(msg)
    if expected.diagnostic_code is not evidence.diagnostic_code:
        msg = "parser diagnostic_code does not match the replayed raw"
        raise ValueError(msg)
    if expected.raw_sha256 != evidence.raw_sha256:
        msg = "parser_evidence raw_sha256 does not match the replayed raw"
        raise ValueError(msg)


def replay_language_validation(
    *,
    candidate: ScoringCandidate,
    output_language: Literal["zh-CN", "en"],
) -> LanguageValidationEvidence:
    """Replay the frozen TASK-016B language validator for a candidate.

    This reuses ``detect_scoring_language_violation`` directly; it never writes a
    second language algorithm.  The validator emits no finer deterministic reason
    code than ``VALID``/``INVALID``/``UNCERTAIN``, which is the only diagnostic
    authority sealed here.  The candidate hash is derived through the unchanged
    ``build_scoring_candidate_hash``.
    """

    result = detect_scoring_language_violation(candidate.reason, output_language)
    result_literal: Literal["VALID", "INVALID", "UNCERTAIN"]
    if result is ScoringLanguageValidation.VALID:
        result_literal = "VALID"
    elif result is ScoringLanguageValidation.INVALID:
        result_literal = "INVALID"
    else:
        result_literal = "UNCERTAIN"
    return LanguageValidationEvidence(
        schema_version=LANGUAGE_VALIDATION_EVIDENCE_SCHEMA,
        kind="LANGUAGE_VALIDATION",
        candidate_sha256=build_scoring_candidate_hash(candidate),
        output_language=output_language,
        validator_contract=_LANGUAGE_VALIDATOR_CONTRACT,
        result=result_literal,
    )


def verify_language_evidence_replay(
    evidence: LanguageValidationEvidence,
    *,
    candidate: ScoringCandidate,
    output_language: Literal["zh-CN", "en"],
) -> None:
    """Rebuild language evidence from the frozen validator and require equality.

    A candidate/hash mismatch, a different replayed result, an incorrect
    validator contract, or an unknown result rejects.
    """

    if evidence.validator_contract != _LANGUAGE_VALIDATOR_CONTRACT:
        msg = "language_evidence validator_contract is not the frozen TASK-016B contract"
        raise ValueError(msg)
    if evidence.output_language != output_language:
        msg = "language_evidence output_language does not match the scoring context"
        raise ValueError(msg)
    expected = replay_language_validation(candidate=candidate, output_language=output_language)
    if expected.candidate_sha256 != evidence.candidate_sha256:
        msg = "language_evidence candidate_sha256 does not match the replayed candidate"
        raise ValueError(msg)
    if expected.result != evidence.result:
        msg = "language_evidence result does not match the frozen validator replay"
        raise ValueError(msg)


def _rederive_raw_binding(raw_utf8: str) -> tuple[int, str]:
    authoritative = raw_utf8.encode("utf-8", errors="strict")
    return len(authoritative), hashlib.sha256(authoritative).hexdigest()


def verify_primary_failure_evidence(evidence: PrimaryFailureEvidence) -> None:
    """Independently re-derive the PRIMARY raw bindings and replay the failure.

    Both ``primary_raw_sha256`` and ``primary_raw_utf8_length`` are recomputed
    from the exact authoritative ``primary_raw_utf8`` strict-UTF-8 bytes; a
    correct hash does not excuse an incorrect length and vice versa.  The
    class-specific evidence is then replayed and must independently re-prove the
    claimed failure class.  Raises ``ValueError`` on any mismatch.
    """

    try:
        byte_length, raw_sha = _rederive_raw_binding(evidence.primary_raw_utf8)
    except UnicodeEncodeError as exc:
        msg = "primary_raw_utf8 is not strict UTF-8"
        raise ValueError(msg) from exc
    if byte_length != evidence.primary_raw_utf8_length:
        msg = "primary_raw_utf8_length does not match the strict-UTF-8 byte count"
        raise ValueError(msg)
    if raw_sha != evidence.primary_raw_sha256:
        msg = "primary_raw_sha256 does not match the strict-UTF-8 bytes"
        raise ValueError(msg)

    failure_class = evidence.failure_class
    if failure_class is PrimaryFailureClass.SCHEMA_OR_PARSE_INVALID:
        parser = evidence.parser_evidence
        if type(parser) is not ParserFailureEvidence:
            msg = "SCHEMA_OR_PARSE_INVALID requires PARSER_FAILURE evidence"
            raise ValueError(msg)
        if parser.raw_sha256 != evidence.primary_raw_sha256:
            msg = "parser_evidence raw_sha256 must equal primary_raw_sha256"
            raise ValueError(msg)
        verify_parser_evidence_replay(parser, raw_utf8=evidence.primary_raw_utf8)
        return

    if failure_class is PrimaryFailureClass.LANGUAGE_INVALID:
        language = evidence.language_evidence
        if type(language) is not LanguageValidationEvidence:
            msg = "LANGUAGE_INVALID requires LANGUAGE_VALIDATION evidence"
            raise ValueError(msg)
        candidate_evidence = evidence.primary_candidate
        if type(candidate_evidence) is not CandidateEvidence:
            msg = "LANGUAGE_INVALID requires CANDIDATE evidence"
            raise ValueError(msg)
        candidate = candidate_evidence.candidate
        if build_scoring_candidate_hash(candidate) != candidate_evidence.candidate_sha256:
            msg = "candidate_sha256 does not match the canonical candidate"
            raise ValueError(msg)
        verify_language_evidence_replay(
            language,
            candidate=candidate,
            output_language=evidence.primary_output_language,
        )
        return

    if failure_class in {
        PrimaryFailureClass.JUDGE_REJECT,
        PrimaryFailureClass.JUDGE_UNCERTAIN,
    }:
        judge = evidence.judge_evidence
        if type(judge) is not JudgeEvidence:
            msg = "JUDGE failure requires JUDGE_EVIDENCE"
            raise ValueError(msg)
        candidate_evidence = evidence.primary_candidate
        if type(candidate_evidence) is not CandidateEvidence:
            msg = "JUDGE failure requires CANDIDATE evidence"
            raise ValueError(msg)
        if build_scoring_candidate_hash(
            candidate_evidence.candidate
        ) != candidate_evidence.candidate_sha256:
            msg = "candidate_sha256 does not match the canonical candidate"
            raise ValueError(msg)
        verify_judge_evidence_replay(judge)
        return

    msg = f"unknown failure_class {failure_class!r}"
    raise ValueError(msg)


def verify_judge_evidence_replay(evidence: JudgeEvidence) -> None:
    """Independently re-derive and verify one sealed ``JudgeEvidence``.

    Rebuilds Judge H1/H2 from the exact operation input, recomputes the
    canonical ``judge_input`` hash and the raw byte length/hash, and replays the
    shared pure verifier over the exact raw.  Every re-derived value must equal
    the sealed field; the stored enum/result alone is never authority.  Raises
    ``ValueError`` on any mismatch.
    """

    operation_input = evidence.operation_input
    judge_input = evidence.judge_input

    h1, h2 = build_judge_h1_h2(operation_input)
    if h1 != evidence.judge_h1:
        msg = "JudgeEvidence judge_h1 does not match the rebuilt operation input"
        raise ValueError(msg)
    if h2 != evidence.judge_h2:
        msg = "JudgeEvidence judge_h2 does not match the rebuilt request hash"
        raise ValueError(msg)

    if operation_input.attempt_role.value != evidence.role:
        msg = "JudgeEvidence role does not match operation_input.attempt_role"
        raise ValueError(msg)

    expected_input_hash = build_content_quality_input_hash(judge_input)
    if expected_input_hash != evidence.judge_input_sha256:
        msg = "JudgeEvidence judge_input_sha256 does not match the canonical input"
        raise ValueError(msg)
    if operation_input.quality_input_hash != evidence.judge_input_sha256:
        msg = "JudgeEvidence operation_input.quality_input_hash mismatches input hash"
        raise ValueError(msg)

    try:
        byte_length, raw_sha = _rederive_raw_binding(evidence.raw_utf8)
    except UnicodeEncodeError as exc:
        msg = "JudgeEvidence raw_utf8 is not strict UTF-8"
        raise ValueError(msg) from exc
    if byte_length != evidence.raw_utf8_length:
        msg = "JudgeEvidence raw_utf8_length does not match the strict-UTF-8 bytes"
        raise ValueError(msg)
    if raw_sha != evidence.raw_sha256:
        msg = "JudgeEvidence raw_sha256 does not match the strict-UTF-8 bytes"
        raise ValueError(msg)

    replayed = verify_judge_model_content(
        evidence.raw_utf8,
        operation_input=operation_input,
        content_input=judge_input,
    )
    if replayed != evidence.derived_result:
        msg = "JudgeEvidence derived_result does not equal the pure raw replay"
        raise ValueError(msg)


def build_judge_evidence(
    *,
    role: Literal["PRIMARY", "REPAIR"],
    operation_input: QualityJudgeOperationInput,
    judge_input: ContentQualityInput,
    raw_utf8: str,
    provider: str = "ollama",
    model: str,
    model_digest: str,
    policy_version: str,
    prompt_version: str,
    operation_schema_version: str,
) -> JudgeEvidence:
    """Construct one exact ``JudgeEvidence`` from trusted runtime material.

    The derived result and raw bindings are computed with the same pure replay
    logic used for verification, so a built evidence always verifies.
    """

    capture = seal_judge_raw_capture(raw_utf8)
    h1, h2 = build_judge_h1_h2(operation_input)
    derived_result = verify_judge_model_content(
        raw_utf8,
        operation_input=operation_input,
        content_input=judge_input,
    )
    return JudgeEvidence(
        evidence_schema_version=JUDGE_EVIDENCE_SCHEMA,
        role=role,
        judge_h1=h1,
        judge_h2=h2,
        provider=provider,
        model=model,
        model_digest=model_digest,
        policy_version=policy_version,
        prompt_version=prompt_version,
        operation_schema_version=operation_schema_version,
        operation="local-content-quality-v1",
        operation_input=operation_input,
        judge_input=judge_input,
        judge_input_sha256=build_content_quality_input_hash(judge_input),
        raw_capture_kind=_JUDGE_RAW_CAPTURE_KIND,
        raw_utf8=raw_utf8,
        raw_utf8_length=capture.byte_length,
        raw_sha256=capture.sha256,
        derived_result=derived_result,
    )
