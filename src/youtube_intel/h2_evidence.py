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
from dataclasses import dataclass
from enum import Enum
from typing import Final, Literal, NoReturn, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from youtube_intel.config import (
    LocalScoringSettings,
    _validate_loopback_http_base_url,
)
from youtube_intel.domain import (
    ContentQualityDecisionSource,
    ContentQualityInput,
    ContentQualityResult,
    ContentQualityStatus,
    QualityJudgeAttemptRole,
    QualityJudgeOperationInput,
    QualityPassAttestation,
    ScoreResult,
    ScoringCandidate,
    ScoringEvidenceSource,
    ScoringInput,
    ScoringLanguageValidation,
    detect_scoring_language_violation,
)
from youtube_intel.h2_jcs import jcs_loads_strict, jcs_serialize, jcs_sha256
from youtube_intel.providers.ollama import (
    _QUALITY_JUDGE_OPERATION,
    _QUALITY_JUDGE_PROVIDER,
    _QUALITY_POLICY_VERSION,
    _QUALITY_PROMPT_VERSION,
    _QUALITY_SCHEMA_VERSION,
    _SCORE_RESULT_FORMAT,
    ParserDiagnosticCode,
    diagnose_scoring_parse_failure,
    parse_scoring_candidate,
    seal_judge_raw_capture,
    seal_primary_raw_capture,
    verify_judge_model_content,
)
from youtube_intel.quality import (
    TrustedScoreResult,
    build_content_quality_input,
    build_content_quality_input_hash,
    build_judge_h1_h2,
    build_scoring_candidate_hash,
)
from youtube_intel.scoring import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    _canonical_json_bytes,
    build_scoring_request_identity,
)
from youtube_intel.state import build_provider_request_hash

__all__ = [
    "CandidateEvidence",
    "H2CSettingsProvenance",
    "H2_ELIGIBLE_PARSER_CODES",
    "JudgeEvidence",
    "JudgeTrustedContext",
    "LanguageValidationEvidence",
    "NotApplicableEvidence",
    "ParserFailureEvidence",
    "PhaseH2BValidatedRepairResult",
    "PrimaryFailureClass",
    "PrimaryFailureEvidence",
    "PrimaryTrustedContext",
    "RepairCandidateEvidence",
    "RepairCompositeEnvelope",
    "RepairFinalizerBinding",
    "RepairNormalizedInput",
    "RepairPersistenceGraphIdentityV2",
    "RepairProviderEvidence",
    "RepairQualityEvidence",
    "RepairTrustedConfig",
    "build_h2c_settings_provenance",
    "build_judge_evidence",
    "build_judge_trusted_context",
    "build_primary_failure_evidence_hash",
    "build_primary_trusted_context",
    "build_repair_normalized_input",
    "build_repair_request_hash",
    "build_repair_trusted_config",
    "canonical_primary_scoring_input_hash",
    "derive_primary_judge_trusted_context",
    "derive_repair_judge_trusted_context",
    "h2_canonical_bytes",
    "h2_canonical_sha256",
    "repair_normalized_input_hash",
    "repair_persistence_graph_hash",
    "replay_language_validation",
    "replay_primary_parser_failure",
    "verify_h2_sealed_bytes",
    "verify_judge_evidence_replay",
    "verify_language_evidence_replay",
    "verify_parser_evidence_replay",
    "verify_primary_failure_evidence",
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


# Parser diagnostic codes that may form H2 repair-eligible SCHEMA_OR_PARSE_INVALID
# evidence.  These all occur only AFTER the received-raw seam has proved a
# trustworthy, protocol-complete provider/model-content capture.  The pre-capture
# codes (RAW_UTF8_INVALID, RAW_BYTES_LIMIT_EXCEEDED, OUTER_JSON_INVALID,
# OUTER_TOP_LEVEL_TYPE_INVALID, MODEL_RESPONSE_MISSING,
# MODEL_RESPONSE_TYPE_INVALID) are deliberately excluded: each fails before that
# seam succeeds and stays on UNKNOWN_PROVIDER_STATE semantics.
H2_ELIGIBLE_PARSER_CODES: Final[frozenset[ParserDiagnosticCode]] = frozenset(
    {
        ParserDiagnosticCode.MODEL_RESPONSE_LENGTH_EXCEEDED,
        ParserDiagnosticCode.MODEL_JSON_INVALID,
        ParserDiagnosticCode.MODEL_TOP_LEVEL_TYPE_INVALID,
        ParserDiagnosticCode.MODEL_FIELD_SET_INVALID,
        ParserDiagnosticCode.CANDIDATE_SCHEMA_INVALID,
    }
)


def canonical_primary_scoring_input_hash(scoring_input: ScoringInput) -> str:
    """Hash the PRIMARY scoring input with the frozen PRIMARY identity serializer.

    The PRIMARY scoring input is PRIMARY identity material: it is canonically
    serialized with the existing frozen ``_canonical_json_bytes`` (a
    ``json.dumps`` sort-keys serializer) and is never reserialized under H2 JCS.
    """

    return hashlib.sha256(
        _canonical_json_bytes(scoring_input.model_dump(mode="json"))
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class PrimaryTrustedContext:
    """Immutable expected PRIMARY provenance used for deterministic verification.

    This is plain expected input/provenance data derived from the validated
    scoring input and the frozen PRIMARY identity builders.  It is not a
    capability, token, sentinel, receipt, or registry entry: it grants no REPAIR
    admission, no dispatch, and no persistence.  It is only compared against
    sealed evidence.
    """

    scoring_input: ScoringInput
    request_hash: str
    normalized_input_hash: str
    provider: str
    model: str
    model_digest: str
    prompt_version: str
    schema_version: str
    output_language: str
    temperature: float
    max_output_tokens: int
    max_description_chars: int
    scoring_input_sha256: str


def build_primary_trusted_context(
    *,
    scoring_input: ScoringInput,
    model: str,
    model_digest: str,
    temperature: float,
    max_output_tokens: int,
    max_description_chars: int,
) -> PrimaryTrustedContext:
    """Derive the expected trusted PRIMARY context from validated scoring material.

    The PRIMARY request/normalized-input hashes are rebuilt through the unchanged
    ``build_scoring_request_identity``; the scoring-input hash uses the frozen
    PRIMARY identity serializer.  No H2 JCS is applied to PRIMARY identity
    material.
    """

    if type(scoring_input) is not ScoringInput:
        msg = "scoring_input must be an exact validated ScoringInput"
        raise ValueError(msg)
    identity = build_scoring_request_identity(
        scoring_input=scoring_input,
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_description_chars=max_description_chars,
    )
    return PrimaryTrustedContext(
        scoring_input=scoring_input,
        request_hash=identity.request_hash,
        normalized_input_hash=identity.normalized_input_hash,
        provider="ollama",
        model=model,
        model_digest=model_digest,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        output_language=scoring_input.output_language,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_description_chars=max_description_chars,
        scoring_input_sha256=canonical_primary_scoring_input_hash(scoring_input),
    )


@dataclass(frozen=True, slots=True)
class JudgeTrustedContext:
    """Immutable expected Judge provenance used for deterministic comparison.

    This is plain expected data derived from trusted runtime inputs (the trusted
    scoring/repair context and the exact candidate being judged).  It is not a
    token, authority, receipt, admission ticket, sentinel, registry key,
    continuation, or persistence capability: it grants no dispatch and no
    persistence.  It is only compared against sealed Judge evidence.
    """

    role: str
    candidate_hash: str
    scoring_request_hash: str
    quality_input_hash: str
    provider: str
    model: str
    model_digest: str
    policy_version: str
    prompt_version: str
    operation_schema_version: str
    operation: str
    operation_input: QualityJudgeOperationInput
    expected_h1: str
    expected_h2: str


def build_judge_trusted_context(
    *,
    role: str,
    judge_input: ContentQualityInput,
    provider: str,
    model: str,
    model_digest: str,
    policy_version: str,
    prompt_version: str,
    operation_schema_version: str,
) -> JudgeTrustedContext:
    """Assemble a ``JudgeTrustedContext`` data object from supplied values.

    LOW-LEVEL DATA-TYPE BUILDER — NOT THE AUTHORITATIVE COMPOSITION PATH.  This
    helper only constructs the data object from the values it is given; it does
    not itself establish trust.  The authoritative PRIMARY composition is
    ``derive_primary_judge_trusted_context``, which derives every expected value
    from already-trusted runtime inputs (the trusted PRIMARY context, the trusted
    candidate, and the validated settings) and is what the authoritative PFE/RNI
    verifiers use.  An externally built ``JudgeTrustedContext`` cannot be passed to
    those authoritative verifiers and therefore cannot establish trust on its own.
    The frozen Judge policy/prompt/schema/operation literals and provider are
    enforced here against the existing frozen constants.
    """

    if role not in ("PRIMARY", "REPAIR"):
        msg = f"role must be PRIMARY or REPAIR, got {role!r}"
        raise ValueError(msg)
    if provider != _QUALITY_JUDGE_PROVIDER:
        msg = "trusted Judge provider must be the frozen local Judge provider"
        raise ValueError(msg)
    if policy_version != _QUALITY_POLICY_VERSION:
        msg = "trusted Judge policy_version must be the frozen policy version"
        raise ValueError(msg)
    if prompt_version != _QUALITY_PROMPT_VERSION:
        msg = "trusted Judge prompt_version must be the frozen prompt version"
        raise ValueError(msg)
    if operation_schema_version != _QUALITY_SCHEMA_VERSION:
        msg = "trusted Judge operation_schema_version must be the frozen schema version"
        raise ValueError(msg)
    if type(judge_input) is not ContentQualityInput:
        msg = "judge_input must be an exact validated ContentQualityInput"
        raise ValueError(msg)

    quality_input_hash = build_content_quality_input_hash(judge_input)
    operation_input = QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": judge_input.scoring_request_hash,
            "attempt_role": role,
            "candidate_hash": judge_input.candidate_hash,
            "quality_input_hash": quality_input_hash,
            "policy_version": policy_version,
            "prompt_version": prompt_version,
            "schema_version": operation_schema_version,
            "judge_provider": provider,
            "judge_model": model,
            "judge_model_digest": model_digest,
        }
    )
    expected_h1, expected_h2 = build_judge_h1_h2(operation_input)
    return JudgeTrustedContext(
        role=role,
        candidate_hash=judge_input.candidate_hash,
        scoring_request_hash=judge_input.scoring_request_hash,
        quality_input_hash=quality_input_hash,
        provider=provider,
        model=model,
        model_digest=model_digest,
        policy_version=policy_version,
        prompt_version=prompt_version,
        operation_schema_version=operation_schema_version,
        operation=_QUALITY_JUDGE_OPERATION,
        operation_input=operation_input,
        expected_h1=expected_h1,
        expected_h2=expected_h2,
    )


def _build_quality_input(
    *,
    scoring_input: ScoringInput,
    candidate: ScoringCandidate,
    candidate_hash: str,
) -> ContentQualityInput:
    """Deterministically build the content-quality input from trusted inputs.

    This mirrors the canonical runtime construction: the candidate supplies the
    reason/topics, while the scoring input supplies the request hash, output
    language, title, and bounded canonical transcript sample. No caller-provided
    Judge input is accepted.
    """

    return build_content_quality_input(
        scoring_input=scoring_input,
        candidate=candidate,
        candidate_hash=candidate_hash,
    )


def derive_primary_judge_trusted_context(
    *,
    primary_trusted_context: PrimaryTrustedContext,
    trusted_candidate: ScoringCandidate,
    validated_settings: LocalScoringSettings,
) -> tuple[JudgeTrustedContext, ContentQualityInput]:
    """Derive the expected PRIMARY Judge context from already-trusted inputs.

    This is the runtime-owned, deterministic composition boundary.  It derives
    the judge input, candidate/scoring-request/quality-input hashes, provider/
    model/digest, frozen policy/prompt/schema/operation literals, and expected
    H1/H2 from the trusted PRIMARY context, the trusted candidate (re-derived
    from the trusted PRIMARY raw), and the validated runtime settings.  It never
    accepts an independent caller override for any expected Judge value, and it
    never trusts a caller-supplied ``JudgeTrustedContext``.

    The Judge provider/model/digest are taken from the validated settings (the
    canonical runtime configuration source) and must agree with the trusted
    PRIMARY context; a mismatch indicates inconsistent runtime state and rejects.
    """

    if type(primary_trusted_context) is not PrimaryTrustedContext:
        msg = "primary_trusted_context must be an exact PrimaryTrustedContext"
        raise ValueError(msg)
    if type(trusted_candidate) is not ScoringCandidate:
        msg = "trusted_candidate must be an exact ScoringCandidate"
        raise ValueError(msg)
    if type(validated_settings) is not LocalScoringSettings:
        msg = "validated_settings must be an exact validated LocalScoringSettings"
        raise ValueError(msg)

    provider = _QUALITY_JUDGE_PROVIDER
    model = validated_settings.model
    model_digest = validated_settings.expected_model_digest
    if model != primary_trusted_context.model:
        msg = "validated settings model mismatches the trusted PRIMARY context"
        raise ValueError(msg)
    if model_digest != primary_trusted_context.model_digest:
        msg = "validated settings model digest mismatches the trusted PRIMARY context"
        raise ValueError(msg)

    scoring_input = primary_trusted_context.scoring_input
    candidate_hash = build_scoring_candidate_hash(trusted_candidate)
    judge_input = _build_quality_input(
        scoring_input=scoring_input,
        candidate=trusted_candidate,
        candidate_hash=candidate_hash,
    )
    quality_input_hash = build_content_quality_input_hash(judge_input)
    operation_input = QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": scoring_input.request_hash,
            "attempt_role": QualityJudgeAttemptRole.PRIMARY.value,
            "candidate_hash": candidate_hash,
            "quality_input_hash": quality_input_hash,
            "policy_version": _QUALITY_POLICY_VERSION,
            "prompt_version": _QUALITY_PROMPT_VERSION,
            "schema_version": _QUALITY_SCHEMA_VERSION,
            "judge_provider": provider,
            "judge_model": model,
            "judge_model_digest": model_digest,
        }
    )
    expected_h1, expected_h2 = build_judge_h1_h2(operation_input)
    ctx = JudgeTrustedContext(
        role="PRIMARY",
        candidate_hash=candidate_hash,
        scoring_request_hash=scoring_input.request_hash,
        quality_input_hash=quality_input_hash,
        provider=provider,
        model=model,
        model_digest=model_digest,
        policy_version=_QUALITY_POLICY_VERSION,
        prompt_version=_QUALITY_PROMPT_VERSION,
        operation_schema_version=_QUALITY_SCHEMA_VERSION,
        operation=_QUALITY_JUDGE_OPERATION,
        operation_input=operation_input,
        expected_h1=expected_h1,
        expected_h2=expected_h2,
    )
    return ctx, judge_input


def derive_repair_judge_trusted_context(
    *,
    repair_request_hash: str,
    trusted_candidate: ScoringCandidate,
    scoring_input: ScoringInput,
    validated_settings: LocalScoringSettings,
) -> tuple[JudgeTrustedContext, ContentQualityInput]:
    """Derive the expected REPAIR Judge context from already-trusted inputs.

    REPAIR analog of ``derive_primary_judge_trusted_context``.  Every expected
    value is derived internally from the trusted repaired candidate, the
    original trusted scoring input, the validated runtime settings, and the
    frozen Judge policy/prompt/schema/operation literals; no caller-supplied
    ``JudgeTrustedContext`` is accepted.  The Judge input/operation
    ``scoring_request_hash`` is exactly the role-distinct REPAIR request hash
    (``local-scoring-repair-v1``) per the frozen RepairQualityEvidence binding;
    the PRIMARY scoring request hash cannot occupy any REPAIR Judge binding.
    """

    if type(trusted_candidate) is not ScoringCandidate:
        msg = "trusted_candidate must be an exact ScoringCandidate"
        raise ValueError(msg)
    if type(scoring_input) is not ScoringInput:
        msg = "scoring_input must be an exact validated ScoringInput"
        raise ValueError(msg)
    if type(validated_settings) is not LocalScoringSettings:
        msg = "validated_settings must be an exact validated LocalScoringSettings"
        raise ValueError(msg)
    if (
        not isinstance(repair_request_hash, str)
        or len(repair_request_hash) != 64
        or any(character not in "0123456789abcdef" for character in repair_request_hash)
    ):
        msg = "repair_request_hash must be a lowercase 64-character SHA-256 hex value"
        raise ValueError(msg)

    provider = _QUALITY_JUDGE_PROVIDER
    model = validated_settings.model
    model_digest = validated_settings.expected_model_digest
    candidate_hash = build_scoring_candidate_hash(trusted_candidate)
    judge_input = ContentQualityInput.model_validate(
        {
            "scoring_request_hash": repair_request_hash,
            "candidate_hash": candidate_hash,
            "output_language": scoring_input.output_language,
            "reason": trusted_candidate.reason,
            "topics": list(trusted_candidate.topics),
            "evidence_registry": [
                {
                    "evidence_id": "title-1",
                    "source": ScoringEvidenceSource.TITLE.value,
                    "excerpt": scoring_input.video.title,
                }
            ],
        }
    )
    quality_input_hash = build_content_quality_input_hash(judge_input)
    operation_input = QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": repair_request_hash,
            "attempt_role": QualityJudgeAttemptRole.REPAIR.value,
            "candidate_hash": candidate_hash,
            "quality_input_hash": quality_input_hash,
            "policy_version": _QUALITY_POLICY_VERSION,
            "prompt_version": _QUALITY_PROMPT_VERSION,
            "schema_version": _QUALITY_SCHEMA_VERSION,
            "judge_provider": provider,
            "judge_model": model,
            "judge_model_digest": model_digest,
        }
    )
    expected_h1, expected_h2 = build_judge_h1_h2(operation_input)
    ctx = JudgeTrustedContext(
        role="REPAIR",
        candidate_hash=candidate_hash,
        scoring_request_hash=repair_request_hash,
        quality_input_hash=quality_input_hash,
        provider=provider,
        model=model,
        model_digest=model_digest,
        policy_version=_QUALITY_POLICY_VERSION,
        prompt_version=_QUALITY_PROMPT_VERSION,
        operation_schema_version=_QUALITY_SCHEMA_VERSION,
        operation=_QUALITY_JUDGE_OPERATION,
        operation_input=operation_input,
        expected_h1=expected_h1,
        expected_h2=expected_h2,
    )
    return ctx, judge_input


@dataclass(frozen=True, slots=True)
class RepairTrustedConfig:
    """Immutable expected REPAIR configuration derived from trusted settings.

    This is plain expected configuration DATA — already trusted configured
    values.  It is not repair authority: it grants no REPAIR admission, no
    provider dispatch, no Judge dispatch, and no persistence.
    """

    provider: Literal["ollama"]
    model: str
    model_digest: str
    prompt_version: Literal["scoring-prompt-v2", "scoring-prompt-v3"]
    schema_version: Literal["score-result-v2"]
    temperature: float
    max_output_tokens: int
    max_description_chars: int
    operation: Literal["local-scoring-repair-v1"]


def build_repair_trusted_config(settings: LocalScoringSettings) -> RepairTrustedConfig:
    """Derive the trusted REPAIR configuration from validated runtime settings.

    The authoritative REPAIR provider/model/digest/temperature/limits come from
    the current validated ``LocalScoringSettings``; the repair prompt/schema and
    operation literals are the frozen values.  No caller-supplied arbitrary
    strings are accepted.
    """

    if type(settings) is not LocalScoringSettings:
        msg = "settings must be an exact validated LocalScoringSettings"
        raise ValueError(msg)
    return RepairTrustedConfig(
        provider="ollama",
        model=settings.model,
        model_digest=settings.expected_model_digest,
        prompt_version=PROMPT_VERSION,
        schema_version="score-result-v2",
        temperature=settings.temperature,
        max_output_tokens=settings.max_output_tokens,
        max_description_chars=settings.max_description_chars,
        operation="local-scoring-repair-v1",
    )


def _fresh_revalidate_exact(model_type: type[_T], instance: object) -> _T:
    """Freshly revalidate an evidence object at a verifier boundary.

    Frozen construction is not trusted, because ``object.__setattr__``,
    ``model_construct``, and copy/pickle tricks can bypass constructor-time
    validation.  The instance's data is extracted and re-run through the exact
    strict model validation (unknown fields, Literals, StrictInt, and enums all
    enforced; no coercion).  The exact type is required.
    """

    if type(instance) is not model_type:
        msg = f"expected exact {model_type.__name__}, got {type(instance).__name__}"
        raise ValueError(msg)
    payload = cast(BaseModel, instance).model_dump(mode="json")
    return model_type.model_validate(payload)


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
    raw_utf8_length: StrictInt = Field(ge=0, le=20_000)
    raw_sha256: str = Field(pattern=_SHA256_HEX)
    derived_result: ContentQualityResult

    @model_validator(mode="after")
    def _derived_result_is_local_judge(self) -> "JudgeEvidence":
        if (
            self.derived_result.decision_source is not ContentQualityDecisionSource.LOCAL_JUDGE
        ):
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
    primary_max_output_tokens: StrictInt = Field(gt=0)
    primary_max_description_chars: StrictInt = Field(ge=0)
    primary_scoring_input: ScoringInput
    primary_scoring_input_sha256: str = Field(pattern=_SHA256_HEX)
    primary_raw_capture_kind: Literal["OLLAMA_GENERATE_HTTP_BODY_V1"]
    primary_raw_utf8: str
    primary_raw_utf8_length: StrictInt = Field(ge=0, le=1_000_000)
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
        if parser.diagnostic_code not in H2_ELIGIBLE_PARSER_CODES:
            _reject(
                "parser_evidence diagnostic_code is not an H2-eligible post-capture code"
            )
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
    repair_prompt_version: Literal["scoring-prompt-v2", "scoring-prompt-v3"]
    repair_schema_version: Literal["score-result-v2"]
    output_language: Literal["zh-CN", "en"]
    temperature: float = Field(ge=0, le=2, allow_inf_nan=False)
    max_output_tokens: StrictInt = Field(gt=0)
    max_description_chars: StrictInt = Field(ge=0)


def build_repair_normalized_input(
    *,
    job_id: str,
    primary_trusted_context: PrimaryTrustedContext,
    failure_evidence: PrimaryFailureEvidence,
    validated_settings: LocalScoringSettings,
) -> RepairNormalizedInput:
    """Build the exact typed REPAIR normalized-input object from trusted inputs.

    This is the authoritative trusted composition path.  Its security root is the
    already-validated runtime/settings state, not any caller-constructed config or
    context object.  It verifies the sealed PRIMARY failure evidence against the
    trusted PRIMARY context and the validated settings (deriving the expected
    PRIMARY Judge context internally for Judge-based failures), derives the
    ``RepairTrustedConfig`` from the validated settings itself, and then derives
    every authoritative binding — PRIMARY attempt identity, PRIMARY
    request/normalized-input hashes, PRIMARY failure-evidence hash, PRIMARY raw
    hash, scoring-input provenance, and every REPAIR configuration field — from
    those trusted inputs.  The caller cannot independently supply the REPAIR
    model/digest/temperature/limits, the PRIMARY bindings, or a Judge context, so
    neither a forged PFE nor an attacker-selected ``RepairTrustedConfig`` can yield
    a trustworthy RNI.  Creating a ``RepairNormalizedInput`` is still data, not
    authority.
    """

    if type(primary_trusted_context) is not PrimaryTrustedContext:
        msg = "primary_trusted_context must be an exact PrimaryTrustedContext"
        raise ValueError(msg)
    if type(validated_settings) is not LocalScoringSettings:
        msg = "validated_settings must be an exact validated LocalScoringSettings"
        raise ValueError(msg)
    scoring_input = primary_trusted_context.scoring_input
    # Fail closed if the evidence does not independently re-prove the failure
    # under the trusted PRIMARY context and validated settings.
    verify_primary_failure_evidence(
        failure_evidence, primary_trusted_context, validated_settings
    )
    # Derive the authoritative REPAIR configuration from the validated settings.
    trusted_repair_config = build_repair_trusted_config(validated_settings)
    return RepairNormalizedInput(
        schema_version=REPAIR_NORMALIZED_INPUT_SCHEMA,
        role="REPAIR",
        operation=trusted_repair_config.operation,
        job_id=job_id,
        video_id=scoring_input.video.video_id,
        scoring_input=scoring_input,
        scoring_input_sha256=h2_canonical_sha256(scoring_input),
        primary_attempt_identity=_PRIMARY_ATTEMPT_IDENTITY,
        primary_request_hash=primary_trusted_context.request_hash,
        primary_normalized_input_hash=primary_trusted_context.normalized_input_hash,
        primary_failure_class=failure_evidence.failure_class,
        primary_failure_evidence_hash=build_primary_failure_evidence_hash(failure_evidence),
        primary_raw_sha256=failure_evidence.primary_raw_sha256,
        repair_provider=trusted_repair_config.provider,
        repair_model=trusted_repair_config.model,
        repair_model_digest=trusted_repair_config.model_digest,
        repair_prompt_version=trusted_repair_config.prompt_version,
        repair_schema_version=trusted_repair_config.schema_version,
        output_language=scoring_input.output_language,
        temperature=trusted_repair_config.temperature,
        max_output_tokens=trusted_repair_config.max_output_tokens,
        max_description_chars=trusted_repair_config.max_description_chars,
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
        msg = (
            "language_evidence validator_contract is not the frozen TASK-016B contract"
        )
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


def _verify_pfe_provenance(
    evidence: PrimaryFailureEvidence,
    trusted_context: PrimaryTrustedContext,
) -> None:
    """Bind every PRIMARY provenance field to the trusted expected context.

    None of these fields is trusted merely because it appears inside the
    evidence object; each must equal the independently derived trusted value.
    """

    scalar_bindings = (
        (evidence.primary_attempt_identity, _PRIMARY_ATTEMPT_IDENTITY, "primary_attempt_identity",
        ),
        (evidence.primary_request_hash, trusted_context.request_hash, "primary_request_hash",
        ),
        (
            evidence.primary_normalized_input_hash,
            trusted_context.normalized_input_hash,
            "primary_normalized_input_hash",
        ),
        (evidence.primary_provider, trusted_context.provider, "primary_provider"),
        (evidence.primary_model, trusted_context.model, "primary_model"),
        (evidence.primary_model_digest, trusted_context.model_digest, "primary_model_digest",
        ),
        (evidence.primary_prompt_version, trusted_context.prompt_version, "primary_prompt_version",
        ),
        (evidence.primary_schema_version, trusted_context.schema_version, "primary_schema_version",
        ),
        (
            evidence.primary_output_language,
            trusted_context.output_language,
            "primary_output_language",
        ),
        (evidence.primary_temperature, trusted_context.temperature, "primary_temperature",
        ),
        (
            evidence.primary_max_output_tokens,
            trusted_context.max_output_tokens,
            "primary_max_output_tokens",
        ),
        (
            evidence.primary_max_description_chars,
            trusted_context.max_description_chars,
            "primary_max_description_chars",
        ),
    )
    for actual, expected, field_name in scalar_bindings:
        if actual != expected:
            msg = f"{field_name} does not match the trusted PRIMARY context"
            raise ValueError(msg)
    if evidence.primary_scoring_input != trusted_context.scoring_input:
        msg = "primary_scoring_input does not match the trusted PRIMARY scoring input"
        raise ValueError(msg)
    if evidence.primary_scoring_input_sha256 != trusted_context.scoring_input_sha256:
        msg = (
            "primary_scoring_input_sha256 does not match the frozen-serializer "
            "hash rederived from the trusted PRIMARY scoring input"
        )
        raise ValueError(msg)


def _require_capturable_raw(evidence: PrimaryFailureEvidence) -> None:
    """Require the raw body to satisfy the authorized PRIMARY received-raw seam.

    This re-proves provider protocol completion: bounded body, strict UTF-8,
    outer JSON object with duplicate keys rejected, and a string ``response``.
    Any body that fails this gate never became trustworthy received raw evidence
    and stays on UNKNOWN_PROVIDER_STATE semantics; it cannot back eligible
    SCHEMA_OR_PARSE_INVALID (or any other) evidence.
    """

    try:
        seal_primary_raw_capture(evidence.primary_raw_utf8.encode("utf-8", errors="strict"))
    except ValueError as exc:
        msg = (
            "primary_raw_utf8 does not represent a capturable, protocol-complete "
            "PRIMARY raw body"
        )
        raise ValueError(msg) from exc


def _bind_candidate_to_raw(
    evidence: PrimaryFailureEvidence,
    candidate_evidence: CandidateEvidence,
) -> ScoringCandidate:
    """Require the embedded candidate to equal the canonical parse of the raw."""

    candidate = candidate_evidence.candidate
    try:
        parsed = parse_scoring_candidate(evidence.primary_raw_utf8)
    except ValueError as exc:
        msg = "primary_raw_utf8 does not parse to a scoring candidate"
        raise ValueError(msg) from exc
    if parsed != candidate:
        msg = (
            "embedded candidate does not match the canonical parse of primary_raw_utf8"
        )
        raise ValueError(msg)
    if build_scoring_candidate_hash(candidate) != candidate_evidence.candidate_sha256:
        msg = "candidate_sha256 does not match the canonical candidate"
        raise ValueError(msg)
    return candidate


def verify_primary_failure_evidence(
    evidence: PrimaryFailureEvidence,
    trusted_context: PrimaryTrustedContext,
    validated_settings: LocalScoringSettings,
) -> None:
    """Verify sealed PRIMARY failure evidence against trusted runtime inputs.

    Verification never succeeds merely because the evidence is self-consistent.
    Every authoritative PRIMARY provenance binding is compared against the
    trusted context; the raw hash and byte length are independently re-derived
    from the authoritative raw; the raw must pass the authorized capture gate;
    and the class-specific evidence must independently re-prove the claimed
    failure.  For Judge-based failures the expected PRIMARY Judge context is
    DERIVED internally from the trusted context, the trusted candidate (re-parsed
    from the trusted raw), and the validated runtime settings; no caller-supplied
    ``JudgeTrustedContext`` is accepted as authority.  Raises ``ValueError`` on any
    mismatch.
    """

    evidence = _fresh_revalidate_exact(PrimaryFailureEvidence, evidence)
    if type(trusted_context) is not PrimaryTrustedContext:
        msg = "trusted_context must be an exact PrimaryTrustedContext"
        raise ValueError(msg)
    if type(validated_settings) is not LocalScoringSettings:
        msg = "validated_settings must be an exact validated LocalScoringSettings"
        raise ValueError(msg)

    _verify_pfe_provenance(evidence, trusted_context)

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

    _require_capturable_raw(evidence)

    failure_class = evidence.failure_class
    if failure_class is PrimaryFailureClass.SCHEMA_OR_PARSE_INVALID:
        parser = evidence.parser_evidence
        if type(parser) is not ParserFailureEvidence:
            msg = "SCHEMA_OR_PARSE_INVALID requires PARSER_FAILURE evidence"
            raise ValueError(msg)
        if parser.diagnostic_code not in H2_ELIGIBLE_PARSER_CODES:
            msg = (
                "parser diagnostic_code is not an H2-eligible post-capture code; "
                "pre-capture failures stay UNKNOWN_PROVIDER_STATE"
            )
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
        candidate = _bind_candidate_to_raw(evidence, candidate_evidence)
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
        # Establish the exact PRIMARY candidate from the trusted raw parse path.
        candidate = _bind_candidate_to_raw(evidence, candidate_evidence)
        # Derive the expected PRIMARY Judge context internally from already
        # trusted runtime inputs; no caller-supplied Judge context is consumed.
        derived_judge_ctx, _ = derive_primary_judge_trusted_context(
            primary_trusted_context=trusted_context,
            trusted_candidate=candidate,
            validated_settings=validated_settings,
        )
        verify_judge_evidence_replay(judge, derived_judge_ctx)
        return

    msg = f"unknown failure_class {failure_class!r}"
    raise ValueError(msg)


def verify_judge_evidence_replay(
    evidence: JudgeEvidence,
    judge_trusted_context: JudgeTrustedContext,
) -> None:
    """Replay one sealed ``JudgeEvidence`` against an expected Judge context.

    LOW-LEVEL DATA-LEVEL REPLAY PRIMITIVE — NOT A SECURITY INGRESS.  This
    function deterministically compares the evidence against an expected
    ``JudgeTrustedContext`` and replays the raw.  Callers cannot use its result
    alone to establish PRIMARY repair eligibility: the authoritative PFE/RNI
    composition path (``verify_primary_failure_evidence`` /
    ``build_repair_normalized_input``) derives its ``JudgeTrustedContext``
    internally from trusted runtime inputs and never accepts a caller-supplied
    one.  Success requires comparison against the expected context;
    ``evidence.operation_input`` and ``evidence.judge_input`` can never
    authenticate each other on their own.  The evidence is first freshly
    revalidated (defeating low-level mutation), every metadata field and the
    operation literal/role must equal the expected metadata, the operation input
    must equal the expected operation input, H1/H2 must equal the expected H1/H2,
    the judge-input candidate/request/hash must equal the expected bindings, the
    raw hash/length are rederived, and the derived result is replayed.  Raises
    ``ValueError`` on any mismatch.
    """

    if type(judge_trusted_context) is not JudgeTrustedContext:
        msg = "judge_trusted_context must be an exact JudgeTrustedContext"
        raise ValueError(msg)
    ctx = judge_trusted_context
    evidence = _fresh_revalidate_exact(JudgeEvidence, evidence)

    # Every metadata field must equal the trusted expected metadata.
    metadata_bindings = (
        (evidence.provider, ctx.provider, "provider"),
        (evidence.model, ctx.model, "model"),
        (evidence.model_digest, ctx.model_digest, "model_digest"),
        (evidence.policy_version, ctx.policy_version, "policy_version"),
        (evidence.prompt_version, ctx.prompt_version, "prompt_version"),
        (
            evidence.operation_schema_version,
            ctx.operation_schema_version,
            "operation_schema_version",
        ),
    )
    for actual, expected, field_name in metadata_bindings:
        if actual != expected:
            msg = f"JudgeEvidence {field_name} does not match the trusted Judge context"
            raise ValueError(msg)
    if evidence.operation != ctx.operation:
        msg = "JudgeEvidence operation does not match the trusted Judge context"
        raise ValueError(msg)
    if evidence.role != ctx.role:
        msg = "JudgeEvidence role does not match the trusted Judge context role"
        raise ValueError(msg)

    # The operation input must equal the trusted expected operation input.
    if evidence.operation_input != ctx.operation_input:
        msg = "JudgeEvidence operation_input does not match the trusted operation input"
        raise ValueError(msg)

    # H1/H2 must equal the trusted expected identities.
    if evidence.judge_h1 != ctx.expected_h1:
        msg = "JudgeEvidence judge_h1 does not match the trusted expected H1"
        raise ValueError(msg)
    if evidence.judge_h2 != ctx.expected_h2:
        msg = "JudgeEvidence judge_h2 does not match the trusted expected H2"
        raise ValueError(msg)

    # The judge input must bind to the trusted candidate and scoring request.
    judge_input = evidence.judge_input
    if judge_input.candidate_hash != ctx.candidate_hash:
        msg = "JudgeEvidence judge_input.candidate_hash does not match the trusted candidate"
        raise ValueError(msg)
    if judge_input.scoring_request_hash != ctx.scoring_request_hash:
        msg = (
            "JudgeEvidence judge_input.scoring_request_hash does not match the "
            "trusted scoring request"
        )
        raise ValueError(msg)
    rederived_input_hash = build_content_quality_input_hash(judge_input)
    if rederived_input_hash != evidence.judge_input_sha256:
        msg = (
            "JudgeEvidence judge_input_sha256 does not match the canonical judge input"
        )
        raise ValueError(msg)
    if evidence.judge_input_sha256 != ctx.quality_input_hash:
        msg = "JudgeEvidence judge_input_sha256 does not match the trusted quality input hash"
        raise ValueError(msg)

    # Rederive the raw byte length and hash from the authoritative raw.
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

    # Replay the derived result against the trusted operation input.
    replayed = verify_judge_model_content(
        evidence.raw_utf8,
        operation_input=ctx.operation_input,
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


@dataclass(frozen=True, slots=True)
class PhaseH2BValidatedRepairResult:
    """IN-MEMORY EVIDENCE AGGREGATE ONLY — the untrusted H2-B output.

    This is the untrusted evidence aggregate produced by an actual admitted
    H2-B REPAIR/Judge PASS control flow.  It is untrusted input to a future
    H2-C independent replay.  Its type, frozen shape, private construction,
    immutability, or non-serialization confers NO trust, NO persistence
    authority, NO repair capability, and NO H2-C ingress.  Passing even a
    fully valid aggregate to ``TrustedPersistenceEntry.persist_success(...)``
    rejects, and H2-C (when separately authorized) must independently replay
    every security-significant claim rather than trust any field here.
    """

    # PRIMARY rederivable trusted input/provenance and failure evidence.
    primary_trusted_context: PrimaryTrustedContext
    primary_failure_evidence: PrimaryFailureEvidence
    failure_class: PrimaryFailureClass

    # Exact REPAIR normalized input and its canonical/request identity.
    repair_normalized_input: RepairNormalizedInput
    repair_normalized_input_bytes: bytes
    rni_hash: str
    repair_request_hash: str

    # Exact outbound REPAIR request/payload provenance.
    repair_prompt: str
    repair_payload_bytes: bytes
    repair_payload_sha256: str
    repair_payload_length: int

    # Authoritative REPAIR outer raw, extracted model content, and candidate.
    repair_raw_utf8: str
    repair_raw_sha256: str
    repair_raw_length: int
    repair_model_content: str
    repaired_candidate: ScoringCandidate
    repaired_candidate_hash: str

    # TASK-016B language evidence/result.
    language_evidence: LanguageValidationEvidence

    # Deterministic Content Quality gate PASS evidence/provenance.  The gate
    # input is the exact REPAIR ContentQualityInput (``judge_input``) bound to
    # the REPAIR request hash; these fields carry the hash and the successful
    # gate status sufficient for an independent gate replay.  No successful
    # REPAIR path ever carries an EMPTY_CONTENT gate result: empty/whitespace
    # content fails schema/parse before the gate.
    quality_input_hash: str
    deterministic_gate_status: str

    # REPAIR Judge identity, evidence, raw, and final PASS result.
    judge_operation_input: QualityJudgeOperationInput
    judge_input: ContentQualityInput
    judge_h1: str
    judge_h2: str
    judge_evidence: JudgeEvidence
    judge_raw_utf8: str
    judge_raw_sha256: str
    judge_raw_length: int
    judge_result: ContentQualityResult
    attestation: QualityPassAttestation

    # REPAIR-aware finalization evidence: the finalizer-produced trusted result
    # plus the exact sealed structured bytes/hash/length and the schema/version
    # metadata needed to reproduce them.  Even the finalizer-produced part
    # confers no trust on the aggregate as a whole: it remains untrusted
    # evidence data and not a persistence capability.
    finalizer_trusted_result: TrustedScoreResult
    structured_result_bytes: bytes
    structured_result_sha256: str
    structured_result_length: int
    structured_result_schema_version: str
    structured_result_prompt_version: str

    # Runtime/config provenance required by the frozen H2-C replay contract.
    model: str
    model_digest: str
    prompt_version: str
    schema_version: str
    policy_version: str
    quality_prompt_version: str
    quality_schema_version: str
    temperature: float
    max_output_tokens: int
    max_description_chars: int


# ---------------------------------------------------------------------------
# TASK-016C Phase H2-C — typed repair persistence evidence (data only)
# ---------------------------------------------------------------------------
#
# These are the closed H2-C envelope/evidence schemas frozen by the approved
# H2-C authorization amendments.  They are typed data contracts for the repair
# persistence graph; they grant no trust, authority, or capability by
# themselves.  The runtime replay re-derives every security-significant value
# from trusted roots and compares it against these representations.

H2C_SETTINGS_PROVENANCE_SCHEMA: Final = "task016c-h2c-settings-provenance-v1"
REPAIR_PROVIDER_EVIDENCE_SCHEMA_V2: Final = "task016c-repair-provider-evidence-v2"
REPAIR_CANDIDATE_EVIDENCE_SCHEMA: Final = "task016c-repair-candidate-evidence-v1"
REPAIR_QUALITY_EVIDENCE_SCHEMA: Final = "task016c-repair-quality-evidence-v1"
REPAIR_FINALIZER_BINDING_SCHEMA: Final = "task016c-repair-finalizer-binding-v1"
REPAIR_COMPOSITE_ENVELOPE_SCHEMA: Final = "trusted-scoring-repair-envelope-v1"
REPAIR_PERSISTENCE_GRAPH_SCHEMA_V2: Final = "task016c-repair-persistence-graph-v2"
REPAIR_RAW_PRODUCER_VERSION: Final = "scoring-raw-content-quality-repair-v1"
REPAIR_STRUCTURED_PRODUCER_VERSION: Final = (
    "scoring-structured-content-quality-repair-v1"
)

#: H2-C persistence admission ceilings (repair-only; nothing is truncated).
H2C_MAX_TRANSCRIPT_CHARS: Final = 131_072
H2C_MAX_OUTPUT_TOKENS: Final = 2_147_483_647
H2C_SETTINGS_PROVENANCE_MAX_BYTES: Final = 8_192
H2C_ENVELOPE_MAX_BYTES: Final = 33_554_432


class H2CSettingsProvenance(BaseModel):
    """Exact semantic settings provenance bound into every repaired envelope.

    Every identity-bearing current setting is bound verbatim: no trim, case,
    Unicode, URL, or default substitution happens during construction, and no
    field is nullable or defaulted.  The canonical provenance identity is the
    H2 JCS strict-UTF-8 serialization hashed with SHA-256.
    """

    model_config = _H2_FROZEN
    schema_version: Literal["task016c-h2c-settings-provenance-v1"]
    scoring_provider: Literal["ollama"]
    scoring_base_url: str = Field(min_length=1)
    scoring_model: str = Field(min_length=1)
    scoring_model_digest: str = Field(pattern=_MODEL_DIGEST)
    temperature: float = Field(ge=0, le=2, allow_inf_nan=False)
    max_output_tokens: StrictInt = Field(ge=1, le=2_147_483_647)
    max_transcript_chars: StrictInt = Field(ge=3, le=131_072)
    max_description_chars: StrictInt = Field(ge=0, le=20_000)
    output_language: Literal["zh-CN", "en"]
    summary_score_threshold: float = Field(ge=0, le=10, allow_inf_nan=False)
    scoring_operation: Literal["local-scoring"]
    scoring_prompt_version: Literal["scoring-prompt-v2", "scoring-prompt-v3"]
    scoring_schema_version: Literal["score-result-v2"]
    repair_operation: Literal["local-scoring-repair-v1"]
    repair_prompt_version: Literal["scoring-prompt-v2", "scoring-prompt-v3"]
    repair_schema_version: Literal["score-result-v2"]
    repair_stream: Literal[False]
    repair_think: Literal[False]
    repair_format_schema_sha256: str = Field(pattern=_SHA256_HEX)
    repair_num_predict: StrictInt = Field(ge=1, le=2_147_483_647)
    judge_operation: Literal["local-content-quality-v1"]
    judge_provider: Literal["ollama"]
    judge_base_url: str = Field(min_length=1)
    judge_model: str = Field(min_length=1)
    judge_model_digest: str = Field(pattern=_MODEL_DIGEST)
    quality_policy_version: Literal["content-quality-policy-v1"]
    quality_prompt_version: Literal[
        "content-quality-prompt-v1", "content-quality-prompt-v2", "content-quality-prompt-v3"
    ]
    quality_schema_version: Literal["content-quality-result-v1"]
    language_validator_contract: Literal["task016b-scoring-language-validator-v1"]

    @model_validator(mode="after")
    def _h2c_settings_provenance_bindings(self) -> "H2CSettingsProvenance":
        _validate_loopback_http_base_url(
            self.scoring_base_url, field_name="scoring_base_url"
        )
        _validate_loopback_http_base_url(
            self.judge_base_url, field_name="judge_base_url"
        )
        if self.judge_base_url != self.scoring_base_url:
            msg = "judge_base_url must equal scoring_base_url exactly"
            raise ValueError(msg)
        if self.scoring_model != self.scoring_model.strip():
            msg = "scoring_model must be a trimmed non-empty identifier"
            raise ValueError(msg)
        if self.judge_model != self.judge_model.strip():
            msg = "judge_model must be a trimmed non-empty identifier"
            raise ValueError(msg)
        if self.repair_num_predict != self.max_output_tokens:
            msg = "repair_num_predict must equal max_output_tokens exactly"
            raise ValueError(msg)
        return self


def build_h2c_settings_provenance(
    *,
    validated_settings: LocalScoringSettings,
    output_language: str,
    summary_score_threshold: float,
) -> H2CSettingsProvenance:
    """Derive the exact current-settings provenance from validated config roots.

    No caller-supplied provenance field is accepted: every value is taken from
    the validated runtime settings and the frozen literal contract.  The repair
    format schema hash is the SHA-256 of the frozen score-result-v2 schema's
    H2 JCS bytes.
    """

    if type(validated_settings) is not LocalScoringSettings:
        msg = "validated_settings must be an exact validated LocalScoringSettings"
        raise ValueError(msg)
    return H2CSettingsProvenance.model_validate(
        {
            "schema_version": H2C_SETTINGS_PROVENANCE_SCHEMA,
            "scoring_provider": "ollama",
            "scoring_base_url": validated_settings.base_url,
            "scoring_model": validated_settings.model,
            "scoring_model_digest": validated_settings.expected_model_digest,
            "temperature": validated_settings.temperature,
            "max_output_tokens": validated_settings.max_output_tokens,
            "max_transcript_chars": validated_settings.max_transcript_chars,
            "max_description_chars": validated_settings.max_description_chars,
            "output_language": output_language,
            "summary_score_threshold": summary_score_threshold,
            "scoring_operation": _PRIMARY_ATTEMPT_IDENTITY,
            "scoring_prompt_version": PROMPT_VERSION,
            "scoring_schema_version": SCHEMA_VERSION,
            "repair_operation": _REPAIR_OPERATION,
            "repair_prompt_version": PROMPT_VERSION,
            "repair_schema_version": SCHEMA_VERSION,
            "repair_stream": False,
            "repair_think": False,
            "repair_format_schema_sha256": hashlib.sha256(
                jcs_serialize(_SCORE_RESULT_FORMAT)
            ).hexdigest(),
            "repair_num_predict": validated_settings.max_output_tokens,
            "judge_operation": _QUALITY_JUDGE_OPERATION,
            "judge_provider": _QUALITY_JUDGE_PROVIDER,
            "judge_base_url": validated_settings.base_url,
            "judge_model": validated_settings.model,
            "judge_model_digest": validated_settings.expected_model_digest,
            "quality_policy_version": _QUALITY_POLICY_VERSION,
            "quality_prompt_version": _QUALITY_PROMPT_VERSION,
            "quality_schema_version": _QUALITY_SCHEMA_VERSION,
            "language_validator_contract": _LANGUAGE_VALIDATOR_CONTRACT,
        }
    )


class RepairProviderEvidence(BaseModel):
    """The exact 16-field v2 repair provider evidence nested in the envelope.

    v2 is required for every live H2-C repaired producer; the parent H2-B v1
    contract is unmodified and never emitted by H2-C.  The durable settings
    source is ``settings_provenance`` plus ``settings_provenance_sha256``, and
    the complete graph identity G binds that exact hash.
    """

    model_config = _H2_FROZEN
    schema_version: Literal["task016c-repair-provider-evidence-v2"]
    operation: Literal["local-scoring-repair-v1"]
    normalized_input: RepairNormalizedInput
    normalized_input_hash: str = Field(pattern=_SHA256_HEX)
    request_hash: str = Field(pattern=_SHA256_HEX)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    model_digest: str = Field(pattern=_MODEL_DIGEST)
    prompt_version: str = Field(min_length=1)
    operation_schema_version: str = Field(min_length=1)
    output_language: Literal["zh-CN", "en"]
    temperature: float = Field(allow_inf_nan=False)
    max_output_tokens: StrictInt = Field(gt=0)
    max_description_chars: StrictInt = Field(ge=0)
    settings_provenance: H2CSettingsProvenance
    settings_provenance_sha256: str = Field(pattern=_SHA256_HEX)


class RepairCandidateEvidence(BaseModel):
    """REPAIR raw, extracted content, candidate/hash, and language evidence."""

    model_config = _H2_FROZEN
    schema_version: Literal["task016c-repair-candidate-evidence-v1"]
    repair_raw_utf8: str
    repair_raw_sha256: str = Field(pattern=_SHA256_HEX)
    # The 1,000,000-byte ceiling is enforced by the bounded envelope admission
    # (H2C_REPLAY_INVALID:ENVELOPE_OVERSIZE), not by this typed field.
    repair_raw_length: StrictInt = Field(ge=0)
    repair_model_content: str
    candidate: ScoringCandidate
    candidate_sha256: str = Field(pattern=_SHA256_HEX)
    language_evidence: LanguageValidationEvidence


class RepairQualityEvidence(BaseModel):
    """Quality input/gate, Judge input/H1/H2/raw/evidence, and attestation."""

    model_config = _H2_FROZEN
    schema_version: Literal["task016c-repair-quality-evidence-v1"]
    quality_input: ContentQualityInput
    quality_input_hash: str = Field(pattern=_SHA256_HEX)
    deterministic_gate_status: Literal["PASS"]
    judge_operation_input: QualityJudgeOperationInput
    judge_h1: str = Field(pattern=_SHA256_HEX)
    judge_h2: str = Field(pattern=_SHA256_HEX)
    judge_raw_utf8: str
    judge_raw_sha256: str = Field(pattern=_SHA256_HEX)
    # The 20,000-byte ceiling is enforced by the bounded envelope admission.
    judge_raw_length: StrictInt = Field(ge=0)
    judge_evidence: JudgeEvidence
    quality_result: ContentQualityResult
    attestation: QualityPassAttestation


class RepairFinalizerBinding(BaseModel):
    """Trusted result, structured binding, and the P/R/J commitment."""

    model_config = _H2_FROZEN
    schema_version: Literal["task016c-repair-finalizer-binding-v1"]
    trusted_result: ScoreResult
    structured_result_sha256: str = Field(pattern=_SHA256_HEX)
    structured_result_length: StrictInt = Field(ge=0)
    structured_result_schema_version: Literal["score-result-v2"]
    structured_result_prompt_version: Literal["scoring-prompt-v2", "scoring-prompt-v3"]
    primary_request_hash: str = Field(pattern=_SHA256_HEX)
    repair_request_hash: str = Field(pattern=_SHA256_HEX)
    repair_judge_request_hash: str = Field(pattern=_SHA256_HEX)


class RepairCompositeEnvelope(BaseModel):
    """The root H2-JCS repair envelope with exactly six ordered logical fields.

    Raw captures are strict UTF-8 strings carried as JCS JSON strings (never
    base64).  The envelope contains neither G nor an artifact key/path nor
    graph identity bytes/digest, so neither E nor S requires G.
    """

    model_config = _H2_FROZEN
    envelope_schema: Literal["trusted-scoring-repair-envelope-v1"]
    primary_failure_evidence: PrimaryFailureEvidence
    repair_provider_evidence: RepairProviderEvidence
    repair_candidate_evidence: RepairCandidateEvidence
    repair_quality_evidence: RepairQualityEvidence
    finalizer_binding: RepairFinalizerBinding


class RepairPersistenceGraphIdentityV2(BaseModel):
    """The exact complete-graph persistence identity (v2) whose JCS hash is G.

    All fields are non-null, literal-bound, and none is defaulted, inferred, or
    supplied by an artifact path.  The Round 3 historical
    ``task016c-repair-persistence-graph-v1`` design is never emitted.
    """

    model_config = _H2_FROZEN
    schema_version: Literal["task016c-repair-persistence-graph-v2"]
    primary_request_hash: str = Field(pattern=_SHA256_HEX)
    repair_request_hash: str = Field(pattern=_SHA256_HEX)
    repair_judge_request_hash: str = Field(pattern=_SHA256_HEX)
    settings_provenance_sha256: str = Field(pattern=_SHA256_HEX)
    repair_envelope_sha256: str = Field(pattern=_SHA256_HEX)
    structured_result_sha256: str = Field(pattern=_SHA256_HEX)
    raw_producer_version: Literal["scoring-raw-content-quality-repair-v1"]
    structured_producer_version: Literal[
        "scoring-structured-content-quality-repair-v1"
    ]
    envelope_schema: Literal["trusted-scoring-repair-envelope-v1"]
    repair_provider_evidence_schema: Literal["task016c-repair-provider-evidence-v2"]
    quality_policy_version: Literal["content-quality-policy-v1"]
    quality_prompt_version: Literal[
        "content-quality-prompt-v1", "content-quality-prompt-v2", "content-quality-prompt-v3"
    ]
    quality_schema_version: Literal["content-quality-result-v1"]


def repair_persistence_graph_hash(
    identity: RepairPersistenceGraphIdentityV2,
) -> str:
    """Return G: the SHA-256 of the identity's H2 JCS strict UTF-8 bytes."""

    if type(identity) is not RepairPersistenceGraphIdentityV2:
        msg = "identity must be an exact RepairPersistenceGraphIdentityV2"
        raise ValueError(msg)
    return jcs_sha256(identity.model_dump(mode="json"))
