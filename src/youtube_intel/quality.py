"""Deterministic content-quality safety gate (TASK-016C Phase B).

The gate is intentionally narrow: it can only reject content for one of three
deterministic reasons.  Structurally valid content that does not match any of
these patterns returns ``None`` so that later phases (Local Judge, Finalizer,
etc.) can continue evaluation.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from typing import Final, TypeVar

from pydantic import BaseModel

from youtube_intel.domain import (
    ContentQualityConfidence,
    ContentQualityDecisionSource,
    ContentQualityInput,
    ContentQualityResult,
    ContentQualityStatus,
    DeterministicGateReason,
    QualityJudgeOperationInput,
    QualityPassAttestation,
    TrustedQualityProvenance,
)
from youtube_intel.state import build_provider_request_hash

_JUDGE_PROVIDER: Final[str] = "ollama"
_QUALITY_JUDGE_OPERATION: Final[str] = "local-content-quality-v1"
_JUDGE_MODEL: Final[str] = "qwen3:8b"
_JUDGE_MODEL_DIGEST: Final[str] = "sha256:" + "b" * 64
_SCORING_SCHEMA_VERSION: Final[str] = "scoring-schema-v1"
_SCORING_PROMPT_VERSION: Final[str] = "scoring-prompt-v1"

_ASCII_WHITESPACE: Final[str] = " \t\n\r\v\f"

_CONTROL_ALLOWED: Final[frozenset[str]] = frozenset({"\t", "\n"})

_CONTROL_DISALLOWED_CODEPOINTS: Final[frozenset[int]] = frozenset(
    {0x0000, 0x200B, 0xFEFF}
)


class DeterministicContentQualityGate:
    """Pure-local deterministic gate for EMPTY_CONTENT, CONTROL_CHARACTER_INVALID,
    and EXACT_REPETITION.
    """

    def evaluate(
        self,
        *,
        content: str,
        candidate_hash: str,
        quality_input_hash: str,
        scoring_request_hash: str,
    ) -> ContentQualityResult | None:
        """Return a deterministic REJECT result, or ``None`` to continue."""

        reason = self._classify(content)
        if reason is None:
            return None

        return ContentQualityResult.model_validate(
            {
                "schema_version": "content-quality-result-v1",
                "policy_version": "content-quality-policy-v1",
                "prompt_version": "content-quality-prompt-v1",
                "status": ContentQualityStatus.REJECT.value,
                "decision_source": ContentQualityDecisionSource.DETERMINISTIC_GATE.value,
                "decision_confidence": ContentQualityConfidence.HIGH.value,
                "grounding_confidence": ContentQualityConfidence.LOW.value,
                "usefulness_confidence": ContentQualityConfidence.LOW.value,
                "signals": (),
                "reason": reason.value,
                "evidence_ids": (),
                "candidate_hash": candidate_hash,
                "quality_input_hash": quality_input_hash,
                "scoring_request_hash": scoring_request_hash,
                "judge_provider": None,
                "judge_model": None,
                "judge_model_digest": None,
            }
        )

    def _classify(self, content: str) -> DeterministicGateReason | None:
        # Order is load-bearing: raw control characters (CR/VT/FF/NULL/etc.)
        # must be detected before ASCII-whitespace-only content is classified
        # as empty, so rejection provenance is deterministic.
        if content == "":
            return DeterministicGateReason.EMPTY_CONTENT

        if self._has_invalid_control_character(content):
            return DeterministicGateReason.CONTROL_CHARACTER_INVALID

        if content.strip(_ASCII_WHITESPACE) == "":
            return DeterministicGateReason.EMPTY_CONTENT

        if self._has_exact_repetition(content):
            return DeterministicGateReason.EXACT_REPETITION

        return None

    def _has_invalid_control_character(self, content: str) -> bool:
        """Scan raw content for disallowed control characters.

        LF and TAB are allowed; other Cc characters, NULL, U+200B and U+FEFF
        are rejected.
        """

        for char in content:
            codepoint = ord(char)
            if codepoint in _CONTROL_DISALLOWED_CODEPOINTS:
                return True
            if char in _CONTROL_ALLOWED:
                continue
            if unicodedata.category(char) == "Cc":
                return True
        return False

    def _has_exact_repetition(self, content: str) -> bool:
        """Detect adjacent exact-codepoint repetition after ASCII trim/LF split.

        The algorithm is intentionally literal:

        1. Strip ASCII whitespace from both ends.
        2. Split on LF.
        3. Drop empty segments.
        4. If any remaining segment equals the next one, reject.

        No lowercase, casefold, Unicode normalization, or fuzzy matching is
        performed.
        """

        trimmed = content.strip(_ASCII_WHITESPACE)
        segments = [segment for segment in trimmed.split("\n") if segment]
        for previous, current in zip(segments, segments[1:]):
            if previous == current:
                return True
        return False


# ---------------------------------------------------------------------------
# Local Judge identity (TASK-016C Phase C)
# ---------------------------------------------------------------------------


_T = TypeVar("_T", bound=BaseModel)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _revalidated_fields(model: type[_T], instance: object) -> _T:
    """Return a fresh validated instance reconstructed from raw ``__dict__``.

    This intentionally bypasses any subclass property overrides or overridden
    ``model_dump`` methods by reading the underlying field dictionary and
    running it through the exact base-class validators.
    """
    if type(instance) is not model:
        msg = f"expected exact type {model.__name__}, got {type(instance).__name__}"
        raise ValueError(msg)
    raw_fields = dict(instance.__dict__)
    return model.model_validate(raw_fields)


def build_judge_h1_h2(
    operation_input: QualityJudgeOperationInput,
) -> tuple[str, str]:
    """Build the two-layer Judge identity for a validated operation input.

    H1 is the SHA-256 of canonical JSON for the fully validated
    ``QualityJudgeOperationInput``.  H2 is derived only through the unchanged
    existing ``build_provider_request_hash`` using ``local-content-quality-v1``
    as the operation and H1 as the normalized input hash.

    The function rejects subclasses and instances that bypassed Pydantic
    validation (for example via ``model_construct``).  It reconstructs the
    input from its raw field dictionary so that overridden ``model_dump``
    methods or property overrides cannot influence the identity.

    H1 and H2 are not interchangeable and are expected to differ.
    """

    validated = _revalidated_fields(QualityJudgeOperationInput, operation_input)
    canonical = _canonical_json(validated.model_dump(mode="json"))
    h1 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    h2 = build_provider_request_hash(
        operation="local-content-quality-v1",
        normalized_input_hash=h1,
        provider=validated.judge_provider,
        model=validated.judge_model,
        prompt_version=validated.prompt_version,
        schema_version=validated.schema_version,
    )
    return h1, h2


def build_content_quality_input_hash(content_input: ContentQualityInput) -> str:
    """Return the canonical SHA-256 identity of a validated content input."""

    validated = _revalidated_fields(ContentQualityInput, content_input)
    canonical = _canonical_json(validated.model_dump(mode="json"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Phase D: canonical result hash and PASS attestation
# ---------------------------------------------------------------------------


def _reconstruct(
    model: type[_T],
    value: _T | Mapping[str, object] | str | bytes | bytearray,
) -> _T:
    """Reconstruct and fully revalidate from an untrusted source.

    Rejects subclasses, ``model_construct`` instances, and any non-mapping
    non-JSON input.  For ``BaseModel`` instances the raw ``__dict__`` is
    re-validated so overridden ``model_dump``/property overrides cannot
    influence the result.
    """

    if isinstance(value, BaseModel):
        return _revalidated_fields(model, value)
    if isinstance(value, Mapping):
        return model.model_validate(dict(value))
    if isinstance(value, (str, bytes, bytearray)):
        return model.model_validate_json(value)
    msg = (
        f"expected {model.__name__}, Mapping, or JSON; "
        f"got {type(value).__name__}"
    )
    raise ValueError(msg)


def build_content_quality_result_hash(
    result: ContentQualityResult | Mapping[str, object] | str | bytes | bytearray,
) -> str:
    """Return the canonical SHA-256 hash of a fully validated ``ContentQualityResult``.

    The result is treated as untrusted: it is reconstructed from its raw
    ``__dict__`` (or Mapping/JSON) and fully re-validated before hashing.
    Signals are normalised by enum value and Evidence IDs by stable ID
    (sort + deduplicate) inside the model validators.
    """

    validated = _reconstruct(ContentQualityResult, result)
    canonical = _canonical_json(validated.model_dump(mode="json"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify_pass_eligibility(
    result: ContentQualityResult,
    content_input: ContentQualityInput,
) -> None:
    """Verify the result is a PASS whose Evidence IDs resolve in the registry."""

    if result.status is not ContentQualityStatus.PASS:
        msg = "only ContentQualityResult(PASS) can be attested"
        raise ValueError(msg)
    if not result.evidence_ids:
        msg = "PASS requires at least one evidence_id"
        raise ValueError(msg)
    registry_ids = frozenset(
        evidence.evidence_id for evidence in content_input.evidence_registry
    )
    for eid in result.evidence_ids:
        if eid not in registry_ids:
            msg = f"evidence_id {eid!r} not in supplied evidence registry"
            raise ValueError(msg)


def _verify_cross_bindings(
    result: ContentQualityResult,
    op_input: QualityJudgeOperationInput,
    content_input: ContentQualityInput,
) -> None:
    """Verify all identity bindings across result, operation input, and input."""

    expected_qih = build_content_quality_input_hash(content_input)
    _bindings: list[tuple[str, object, object]] = [
        ("candidate_hash", result.candidate_hash, op_input.candidate_hash),
        ("candidate_hash", result.candidate_hash, content_input.candidate_hash),
        (
            "quality_input_hash",
            result.quality_input_hash,
            op_input.quality_input_hash,
        ),
        ("quality_input_hash", result.quality_input_hash, expected_qih),
        (
            "scoring_request_hash",
            result.scoring_request_hash,
            op_input.scoring_request_hash,
        ),
        (
            "scoring_request_hash",
            result.scoring_request_hash,
            content_input.scoring_request_hash,
        ),
        ("judge_provider", result.judge_provider, op_input.judge_provider),
        ("judge_model", result.judge_model, op_input.judge_model),
        (
            "judge_model_digest",
            result.judge_model_digest,
            op_input.judge_model_digest,
        ),
        ("policy_version", result.policy_version, op_input.policy_version),
        ("prompt_version", result.prompt_version, op_input.prompt_version),
        ("schema_version", result.schema_version, op_input.schema_version),
    ]
    for field_name, left, right in _bindings:
        if left != right:
            msg = (
                f"{field_name} mismatch: "
                f"quality_result={left!r}, trusted={right!r}"
            )
            raise ValueError(msg)


def _build_current_quality_provenance() -> TrustedQualityProvenance:
    """Build the current trusted quality provenance from fixed application config.

    This factory is the only supported path to ``TrustedQualityProvenance``.
    All fields are module-level constants owned by the application; callers
    cannot supply, override, or substitute any provenance value.
    """

    return TrustedQualityProvenance.model_validate(
        {
            "judge_provider": _JUDGE_PROVIDER,
            "judge_model": _JUDGE_MODEL,
            "judge_model_digest": _JUDGE_MODEL_DIGEST,
            "scoring_schema_version": _SCORING_SCHEMA_VERSION,
            "scoring_prompt_version": _SCORING_PROMPT_VERSION,
        }
    )


def _verify_trusted_provenance(
    result: ContentQualityResult,
    op_input: QualityJudgeOperationInput,
    trusted: TrustedQualityProvenance,
) -> None:
    """Verify Judge and scoring provenance match the current authorized config."""

    _trusted_bindings: list[tuple[str, object, object]] = [
        ("judge_provider", result.judge_provider, trusted.judge_provider),
        ("judge_model", result.judge_model, trusted.judge_model),
        (
            "judge_model_digest",
            result.judge_model_digest,
            trusted.judge_model_digest,
        ),
        ("judge_provider", op_input.judge_provider, trusted.judge_provider),
        ("judge_model", op_input.judge_model, trusted.judge_model),
        (
            "judge_model_digest",
            op_input.judge_model_digest,
            trusted.judge_model_digest,
        ),
        (
            "scoring_schema_version",
            _SCORING_SCHEMA_VERSION,
            trusted.scoring_schema_version,
        ),
        (
            "scoring_prompt_version",
            _SCORING_PROMPT_VERSION,
            trusted.scoring_prompt_version,
        ),
    ]
    for field_name, actual, expected in _trusted_bindings:
        if actual != expected:
            msg = (
                f"{field_name} does not match trusted current provenance: "
                f"actual={actual!r}, trusted={expected!r}"
            )
            raise ValueError(msg)


def build_quality_pass_attestation(
    *,
    quality_result: (
        ContentQualityResult
        | Mapping[str, object]
        | str
        | bytes
        | bytearray
    ),
    operation_input: (
        QualityJudgeOperationInput
        | Mapping[str, object]
        | str
        | bytes
        | bytearray
    ),
    quality_input: (
        ContentQualityInput | Mapping[str, object] | str | bytes | bytearray
    ),
) -> QualityPassAttestation:
    """Trusted application-side constructor for ``quality-pass-attestation-v1``.

    Reconstructs and fully re-validates every input before constructing the
    attestation.  The current trusted provenance is generated internally from
    fixed application constants; callers cannot supply, override, or substitute
    any provenance value.  Fails closed on any malformed value, binding
    mismatch, or provenance that does not match the current authorized
    configuration.
    """

    result = _reconstruct(ContentQualityResult, quality_result)
    op_input = _reconstruct(QualityJudgeOperationInput, operation_input)
    content_input = _reconstruct(ContentQualityInput, quality_input)
    trusted = _build_current_quality_provenance()

    _verify_pass_eligibility(result, content_input)
    _verify_cross_bindings(result, op_input, content_input)
    _verify_trusted_provenance(result, op_input, trusted)

    result_hash = build_content_quality_result_hash(result)
    _, h2 = build_judge_h1_h2(op_input)

    # PASS matrix guarantees non-None Judge identity for LOCAL_JUDGE.
    assert result.judge_provider is not None
    assert result.judge_model is not None
    assert result.judge_model_digest is not None

    payload: dict[str, object] = {
        "attestation_schema": "quality-pass-attestation-v1",
        "status": ContentQualityStatus.PASS.value,
        "candidate_hash": result.candidate_hash,
        "quality_input_hash": result.quality_input_hash,
        "quality_result_hash": result_hash,
        "scoring_request_hash": result.scoring_request_hash,
        "policy_version": result.policy_version,
        "scoring_schema_version": trusted.scoring_schema_version,
        "scoring_prompt_version": trusted.scoring_prompt_version,
        "quality_schema_version": result.schema_version,
        "quality_prompt_version": result.prompt_version,
        "judge_provider": result.judge_provider,
        "judge_model": result.judge_model,
        "judge_model_digest": result.judge_model_digest,
        "judge_operation": _QUALITY_JUDGE_OPERATION,
        "judge_request_hash": h2,
        "attempt_role": op_input.attempt_role.value,
        "decision_confidence": result.decision_confidence.value,
        "grounding_confidence": result.grounding_confidence.value,
        "usefulness_confidence": result.usefulness_confidence.value,
        "evidence_ids": list(result.evidence_ids),
    }

    canonical = _canonical_json(payload)
    attestation_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    payload["attestation_hash"] = attestation_hash

    return QualityPassAttestation.model_validate(payload)


def _compute_attestation_hash(attestation: QualityPassAttestation) -> str:
    """Recompute the canonical attestation_hash from a validated attestation."""

    payload = attestation.model_dump(mode="json")
    payload.pop("attestation_hash")
    canonical = _canonical_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_quality_pass_attestation(
    attestation: (
        QualityPassAttestation | Mapping[str, object] | str | bytes | bytearray
    ),
    *,
    quality_result: (
        ContentQualityResult
        | Mapping[str, object]
        | str
        | bytes
        | bytearray
    ),
    operation_input: (
        QualityJudgeOperationInput
        | Mapping[str, object]
        | str
        | bytes
        | bytearray
    ),
    quality_input: (
        ContentQualityInput | Mapping[str, object] | str | bytes | bytearray
    ),
) -> QualityPassAttestation:
    """Reconstruct and fully verify an alleged attestation; fail closed.

    The alleged attestation is treated as untrusted.  Its ``attestation_hash``
    is recomputed and compared, then a fresh trusted attestation is built from
    the same inputs and the current trusted provenance derived from fixed
    application constants, and compared field-by-field.  A historical or
    attacker-selected configuration cannot verify under the current trusted
    configuration.
    """

    alleged = _reconstruct(QualityPassAttestation, attestation)

    expected_hash = _compute_attestation_hash(alleged)
    if expected_hash != alleged.attestation_hash:
        msg = "attestation_hash does not match canonical payload"
        raise ValueError(msg)

    fresh = build_quality_pass_attestation(
        quality_result=quality_result,
        operation_input=operation_input,
        quality_input=quality_input,
    )

    if alleged != fresh:
        msg = "attestation does not match trusted reconstruction"
        raise ValueError(msg)

    return fresh
