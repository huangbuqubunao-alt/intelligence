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
from typing import Final, NoReturn, TypeVar

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
    ScoreResult,
    ScoringCandidate,
    ScoringInput,
)
from youtube_intel.scoring import build_scoring_request_identity
from youtube_intel.state import build_provider_request_hash

_JUDGE_PROVIDER: Final[str] = "ollama"
_QUALITY_JUDGE_OPERATION: Final[str] = "local-content-quality-v1"
_QUALITY_POLICY_VERSION: Final[str] = "content-quality-policy-v1"
_QUALITY_SCHEMA_VERSION: Final[str] = "content-quality-result-v1"
_QUALITY_PROMPT_VERSION: Final[str] = "content-quality-prompt-v1"
_SCORING_SCHEMA_VERSION: Final[str] = "scoring-schema-v1"
_SCORING_PROMPT_VERSION: Final[str] = "scoring-prompt-v1"


class _QualityProvenanceAuthoritySentinel:
    """Private sentinel; only ``runtime.py`` can mint an authority."""

    __slots__ = ()


_QUALITY_PROVENANCE_AUTHORITY_SENTINEL = _QualityProvenanceAuthoritySentinel()


class _TrustedScoringContextSentinel:
    """Private sentinel; only runtime composition can mint scoring authority."""

    __slots__ = ()


_TRUSTED_SCORING_CONTEXT_SENTINEL = _TrustedScoringContextSentinel()


class _TrustedScoreResultSentinel:
    """Private sentinel; only TrustedScoringFinalizer can mint wrappers."""

    __slots__ = ()


_TRUSTED_SCORE_RESULT_SENTINEL = _TrustedScoreResultSentinel()


class QualityProvenanceAuthority:
    """Opaque, runtime-minted authority for quality attestation provenance.

    This object is **not** a Pydantic DTO and cannot be constructed by callers.
    It is created only by ``runtime.py`` from the already-loaded ``AppConfig``,
    after configuration validation.  It carries the current Judge provider,
    model, digest, scoring versions, quality policy/schema/prompt versions and
    Judge operation identity that ``build_quality_pass_attestation`` and
    ``verify_quality_pass_attestation`` bind to.

    The sentinel guard prevents accidental or routine caller construction; it
    does not claim to resist arbitrary code already executing in the same
    Python process.
    """

    __slots__ = (
        "_judge_provider",
        "_judge_model",
        "_judge_model_digest",
        "_scoring_schema_version",
        "_scoring_prompt_version",
        "_quality_policy_version",
        "_quality_schema_version",
        "_quality_prompt_version",
        "_judge_operation",
    )

    def __init__(
        self,
        *,
        sentinel: object,
        judge_provider: str,
        judge_model: str,
        judge_model_digest: str,
        scoring_schema_version: str,
        scoring_prompt_version: str,
        quality_policy_version: str,
        quality_schema_version: str,
        quality_prompt_version: str,
        judge_operation: str,
    ) -> None:
        if sentinel is not _QUALITY_PROVENANCE_AUTHORITY_SENTINEL:
            msg = (
                "QualityProvenanceAuthority can only be minted by runtime "
                "composition; callers cannot construct it directly"
            )
            raise ValueError(msg)
        self._judge_provider = judge_provider
        self._judge_model = judge_model
        self._judge_model_digest = judge_model_digest
        self._scoring_schema_version = scoring_schema_version
        self._scoring_prompt_version = scoring_prompt_version
        self._quality_policy_version = quality_policy_version
        self._quality_schema_version = quality_schema_version
        self._quality_prompt_version = quality_prompt_version
        self._judge_operation = judge_operation

    @property
    def judge_provider(self) -> str:
        return self._judge_provider

    @property
    def judge_model(self) -> str:
        return self._judge_model

    @property
    def judge_model_digest(self) -> str:
        return self._judge_model_digest

    @property
    def scoring_schema_version(self) -> str:
        return self._scoring_schema_version

    @property
    def scoring_prompt_version(self) -> str:
        return self._scoring_prompt_version

    @property
    def quality_policy_version(self) -> str:
        return self._quality_policy_version

    @property
    def quality_schema_version(self) -> str:
        return self._quality_schema_version

    @property
    def quality_prompt_version(self) -> str:
        return self._quality_prompt_version

    @property
    def judge_operation(self) -> str:
        return self._judge_operation

    def __repr__(self) -> str:
        return (
            f"QualityProvenanceAuthority("
            f"judge_provider={self._judge_provider!r}, "
            f"judge_model={self._judge_model!r}, "
            f"judge_model_digest={self._judge_model_digest!r}, "
            f"scoring_schema_version={self._scoring_schema_version!r}, "
            f"scoring_prompt_version={self._scoring_prompt_version!r}, "
            f"quality_policy_version={self._quality_policy_version!r}, "
            f"quality_schema_version={self._quality_schema_version!r}, "
            f"quality_prompt_version={self._quality_prompt_version!r}, "
            f"judge_operation={self._judge_operation!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, QualityProvenanceAuthority):
            return NotImplemented
        return (
            self._judge_provider == other._judge_provider
            and self._judge_model == other._judge_model
            and self._judge_model_digest == other._judge_model_digest
            and self._scoring_schema_version == other._scoring_schema_version
            and self._scoring_prompt_version == other._scoring_prompt_version
            and self._quality_policy_version == other._quality_policy_version
            and self._quality_schema_version == other._quality_schema_version
            and self._quality_prompt_version == other._quality_prompt_version
            and self._judge_operation == other._judge_operation
        )

    def __hash__(self) -> int:
        return hash(
            (
                self._judge_provider,
                self._judge_model,
                self._judge_model_digest,
                self._scoring_schema_version,
                self._scoring_prompt_version,
                self._quality_policy_version,
                self._quality_schema_version,
                self._quality_prompt_version,
                self._judge_operation,
            )
        )

    def __copy__(self) -> "QualityProvenanceAuthority":
        msg = "QualityProvenanceAuthority cannot be copied"
        raise TypeError(msg)

    def __deepcopy__(self, memo: object) -> "QualityProvenanceAuthority":
        msg = "QualityProvenanceAuthority cannot be copied"
        raise TypeError(msg)

    def __reduce__(self) -> NoReturn:
        msg = "QualityProvenanceAuthority cannot be serialized"
        raise TypeError(msg)

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        msg = "QualityProvenanceAuthority cannot be serialized"
        raise TypeError(msg)


# Sentinel-backed factory exposed privately to runtime composition.
def _mint_quality_provenance_authority(
    *,
    judge_provider: str,
    judge_model: str,
    judge_model_digest: str,
    scoring_schema_version: str,
    scoring_prompt_version: str,
    quality_policy_version: str,
    quality_schema_version: str,
    quality_prompt_version: str,
    judge_operation: str,
    sentinel: object,
) -> QualityProvenanceAuthority:
    return QualityProvenanceAuthority(
        sentinel=sentinel,
        judge_provider=judge_provider,
        judge_model=judge_model,
        judge_model_digest=judge_model_digest,
        scoring_schema_version=scoring_schema_version,
        scoring_prompt_version=scoring_prompt_version,
        quality_policy_version=quality_policy_version,
        quality_schema_version=quality_schema_version,
        quality_prompt_version=quality_prompt_version,
        judge_operation=judge_operation,
    )


class TrustedScoringContext:
    """Opaque current scoring provenance minted only by RuntimeOperations."""

    __slots__ = (
        "_scoring_provider",
        "_scoring_model",
        "_scoring_model_digest",
        "_output_language",
        "_scoring_schema_version",
        "_scoring_prompt_version",
        "_scoring_operation",
        "_temperature",
        "_max_output_tokens",
        "_max_description_chars",
        "_sealed",
    )

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("TrustedScoringContext cannot be subclassed")

    def __init__(
        self,
        *,
        sentinel: object,
        scoring_provider: str,
        scoring_model: str,
        scoring_model_digest: str,
        output_language: str,
        scoring_schema_version: str,
        scoring_prompt_version: str,
        scoring_operation: str,
        temperature: float,
        max_output_tokens: int,
        max_description_chars: int,
    ) -> None:
        if sentinel is not _TRUSTED_SCORING_CONTEXT_SENTINEL:
            raise ValueError("TrustedScoringContext can only be minted by runtime")
        self._scoring_provider = scoring_provider
        self._scoring_model = scoring_model
        self._scoring_model_digest = scoring_model_digest
        self._output_language = output_language
        self._scoring_schema_version = scoring_schema_version
        self._scoring_prompt_version = scoring_prompt_version
        self._scoring_operation = scoring_operation
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._max_description_chars = max_description_chars
        self._sealed = True

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("TrustedScoringContext is immutable")
        object.__setattr__(self, name, value)

    @property
    def scoring_provider(self) -> str:
        return self._scoring_provider

    @property
    def scoring_model(self) -> str:
        return self._scoring_model

    @property
    def scoring_model_digest(self) -> str:
        return self._scoring_model_digest

    @property
    def output_language(self) -> str:
        return self._output_language

    @property
    def scoring_schema_version(self) -> str:
        return self._scoring_schema_version

    @property
    def scoring_prompt_version(self) -> str:
        return self._scoring_prompt_version

    @property
    def scoring_operation(self) -> str:
        return self._scoring_operation

    @property
    def temperature(self) -> float:
        return self._temperature

    @property
    def max_output_tokens(self) -> int:
        return self._max_output_tokens

    @property
    def max_description_chars(self) -> int:
        return self._max_description_chars

    def __copy__(self) -> NoReturn:
        raise TypeError("TrustedScoringContext cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("TrustedScoringContext cannot be copied")

    def __reduce__(self) -> NoReturn:
        raise TypeError("TrustedScoringContext cannot be serialized")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("TrustedScoringContext cannot be serialized")


def _mint_trusted_scoring_context(
    *,
    scoring_provider: str,
    scoring_model: str,
    scoring_model_digest: str,
    output_language: str,
    scoring_schema_version: str,
    scoring_prompt_version: str,
    scoring_operation: str,
    temperature: float,
    max_output_tokens: int,
    max_description_chars: int,
    sentinel: object,
) -> TrustedScoringContext:
    """Private runtime-only minting seam, protected by the module sentinel."""

    return TrustedScoringContext(
        sentinel=sentinel,
        scoring_provider=scoring_provider,
        scoring_model=scoring_model,
        scoring_model_digest=scoring_model_digest,
        output_language=output_language,
        scoring_schema_version=scoring_schema_version,
        scoring_prompt_version=scoring_prompt_version,
        scoring_operation=scoring_operation,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_description_chars=max_description_chars,
    )


class TrustedScoreResult:
    """Opaque Finalizer output; a bare ScoreResult is never trusted pipeline data."""

    __slots__ = ("_result", "_sealed")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("TrustedScoreResult cannot be subclassed")

    def __init__(self, *, sentinel: object, result: ScoreResult) -> None:
        if sentinel is not _TRUSTED_SCORE_RESULT_SENTINEL:
            raise ValueError("TrustedScoreResult can only be minted by finalizer")
        self._result = result
        self._sealed = True

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("TrustedScoreResult is immutable")
        object.__setattr__(self, name, value)

    @property
    def result(self) -> ScoreResult:
        return self._result

    def __copy__(self) -> NoReturn:
        raise TypeError("TrustedScoreResult cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("TrustedScoreResult cannot be copied")

    def __reduce__(self) -> NoReturn:
        raise TypeError("TrustedScoreResult cannot be serialized")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("TrustedScoreResult cannot be serialized")


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


def _verify_trusted_provenance(
    result: ContentQualityResult,
    op_input: QualityJudgeOperationInput,
    authority: QualityProvenanceAuthority,
) -> None:
    """Verify Judge, scoring and quality provenance match the runtime authority."""

    _trusted_bindings: list[tuple[str, object, object]] = [
        ("judge_provider", result.judge_provider, authority.judge_provider),
        ("judge_model", result.judge_model, authority.judge_model),
        (
            "judge_model_digest",
            result.judge_model_digest,
            authority.judge_model_digest,
        ),
        ("judge_provider", op_input.judge_provider, authority.judge_provider),
        ("judge_model", op_input.judge_model, authority.judge_model),
        (
            "judge_model_digest",
            op_input.judge_model_digest,
            authority.judge_model_digest,
        ),
        (
            "quality_schema_version",
            result.schema_version,
            authority.quality_schema_version,
        ),
        (
            "quality_prompt_version",
            result.prompt_version,
            authority.quality_prompt_version,
        ),
        (
            "quality_policy_version",
            result.policy_version,
            authority.quality_policy_version,
        ),
        (
            "quality_schema_version",
            op_input.schema_version,
            authority.quality_schema_version,
        ),
        (
            "quality_prompt_version",
            op_input.prompt_version,
            authority.quality_prompt_version,
        ),
        (
            "quality_policy_version",
            op_input.policy_version,
            authority.quality_policy_version,
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
    authority: QualityProvenanceAuthority,
) -> QualityPassAttestation:
    """Trusted application-side constructor for ``quality-pass-attestation-v1``.

    Reconstructs and fully re-validates every input before constructing the
    attestation.  The current trusted provenance is taken from the runtime-minted
    ``authority``; callers cannot supply, override, or substitute any provenance
    value.  Fails closed on any malformed value, binding mismatch, or provenance
    that does not match the current authorized configuration.
    """

    if type(authority) is not QualityProvenanceAuthority:
        msg = (
            f"authority must be a runtime-minted QualityProvenanceAuthority, "
            f"got {type(authority).__name__}"
        )
        raise TypeError(msg)

    result = _reconstruct(ContentQualityResult, quality_result)
    op_input = _reconstruct(QualityJudgeOperationInput, operation_input)
    content_input = _reconstruct(ContentQualityInput, quality_input)

    _verify_pass_eligibility(result, content_input)
    _verify_cross_bindings(result, op_input, content_input)
    _verify_trusted_provenance(result, op_input, authority)

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
        "policy_version": authority.quality_policy_version,
        "scoring_schema_version": authority.scoring_schema_version,
        "scoring_prompt_version": authority.scoring_prompt_version,
        "quality_schema_version": authority.quality_schema_version,
        "quality_prompt_version": authority.quality_prompt_version,
        "judge_provider": result.judge_provider,
        "judge_model": result.judge_model,
        "judge_model_digest": result.judge_model_digest,
        "judge_operation": authority.judge_operation,
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
    authority: QualityProvenanceAuthority,
) -> QualityPassAttestation:
    """Reconstruct and fully verify an alleged attestation; fail closed.

    The alleged attestation is treated as untrusted.  Its ``attestation_hash``
    is recomputed and compared, then a fresh trusted attestation is built from
    the same inputs and the current runtime-minted ``authority``, and compared
    field-by-field.  A historical or attacker-selected configuration cannot
    verify under a different current trusted configuration.
    """

    if type(authority) is not QualityProvenanceAuthority:
        msg = (
            f"authority must be a runtime-minted QualityProvenanceAuthority, "
            f"got {type(authority).__name__}"
        )
        raise TypeError(msg)

    alleged = _reconstruct(QualityPassAttestation, attestation)

    expected_hash = _compute_attestation_hash(alleged)
    if expected_hash != alleged.attestation_hash:
        msg = "attestation_hash does not match canonical payload"
        raise ValueError(msg)

    fresh = build_quality_pass_attestation(
        quality_result=quality_result,
        operation_input=operation_input,
        quality_input=quality_input,
        authority=authority,
    )

    if alleged != fresh:
        msg = "attestation does not match trusted reconstruction"
        raise ValueError(msg)

    return fresh


# ---------------------------------------------------------------------------
# Phase E: trusted scoring finalization (pure memory only)
# ---------------------------------------------------------------------------


def build_scoring_candidate_hash(
    candidate: ScoringCandidate | Mapping[str, object] | str | bytes | bytearray,
) -> str:
    """Return a canonical hash for a fully revalidated scoring candidate."""

    validated = _reconstruct(ScoringCandidate, candidate)
    canonical = _canonical_json(validated.model_dump(mode="json"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require_exact_capability(
    value: object,
    expected_type: type[QualityProvenanceAuthority] | type[TrustedScoringContext],
) -> None:
    if type(value) is not expected_type:
        msg = (
            f"expected runtime-minted {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )
        raise TypeError(msg)


def _verify_scoring_context(
    *,
    context: TrustedScoringContext,
    authority: QualityProvenanceAuthority,
    scoring_input: ScoringInput,
) -> None:
    """Verify current scoring and Judge provenance are one runtime configuration."""

    if context.scoring_provider != _JUDGE_PROVIDER:
        raise ValueError("trusted scoring provider is not supported")
    if context.output_language != scoring_input.output_language:
        raise ValueError("scoring input output_language mismatches trusted context")
    if context.scoring_schema_version != authority.scoring_schema_version:
        raise ValueError("scoring schema version mismatches quality authority")
    if context.scoring_prompt_version != authority.scoring_prompt_version:
        raise ValueError("scoring prompt version mismatches quality authority")

    # Phase E has one runtime-owned local model configuration.  A later phase
    # may deliberately split scorer and Judge models, but must amend this
    # explicit binding rather than silently weakening provenance verification.
    bindings = (
        ("model", context.scoring_model, authority.judge_model),
        ("model digest", context.scoring_model_digest, authority.judge_model_digest),
    )
    for name, actual, expected in bindings:
        if actual != expected:
            raise ValueError(f"trusted scoring {name} mismatches quality authority")


class TrustedScoringFinalizer:
    """The sole Phase-E constructor of opaque trusted scoring output.

    The finalizer is deliberately side-effect free.  It rebuilds each
    caller-provided model, validates both runtime-owned capabilities before
    reading their fields, verifies identity/provenance/attestation bindings,
    then wraps one freshly validated ``ScoreResult``.  It does not create an
    Artifact, cache entry, ProviderCall completion, or filesystem effect.
    """

    def finalize(
        self,
        *,
        candidate: ScoringCandidate | Mapping[str, object] | str | bytes | bytearray,
        scoring_input: ScoringInput | Mapping[str, object] | str | bytes | bytearray,
        quality_input: (
            ContentQualityInput | Mapping[str, object] | str | bytes | bytearray
        ),
        quality_result: (
            ContentQualityResult | Mapping[str, object] | str | bytes | bytearray
        ),
        quality_operation: (
            QualityJudgeOperationInput
            | Mapping[str, object]
            | str
            | bytes
            | bytearray
        ),
        attestation: (
            QualityPassAttestation | Mapping[str, object] | str | bytes | bytearray
        ),
        quality_authority: QualityProvenanceAuthority,
        scoring_context: TrustedScoringContext,
    ) -> TrustedScoreResult:
        """Create trusted output only if all current, complete bindings match."""

        # Capabilities are checked before any capability property is read.
        _require_exact_capability(quality_authority, QualityProvenanceAuthority)
        _require_exact_capability(scoring_context, TrustedScoringContext)

        validated_candidate = _reconstruct(ScoringCandidate, candidate)
        validated_input = _reconstruct(ScoringInput, scoring_input)
        validated_quality_input = _reconstruct(ContentQualityInput, quality_input)
        validated_quality_result = _reconstruct(ContentQualityResult, quality_result)
        validated_operation = _reconstruct(QualityJudgeOperationInput, quality_operation)

        _verify_scoring_context(
            context=scoring_context,
            authority=quality_authority,
            scoring_input=validated_input,
        )
        identity = build_scoring_request_identity(
            scoring_input=validated_input,
            model=scoring_context.scoring_model,
            temperature=scoring_context.temperature,
            max_output_tokens=scoring_context.max_output_tokens,
            max_description_chars=scoring_context.max_description_chars,
        )
        if identity.request_hash != validated_input.request_hash:
            raise ValueError("scoring request hash mismatches canonical identity")

        candidate_hash = build_scoring_candidate_hash(validated_candidate)
        expected_quality_input_hash = build_content_quality_input_hash(
            validated_quality_input
        )
        bindings = (
            ("candidate_hash", validated_quality_input.candidate_hash, candidate_hash),
            ("candidate_hash", validated_quality_result.candidate_hash, candidate_hash),
            ("candidate_hash", validated_operation.candidate_hash, candidate_hash),
            (
                "quality_input_hash",
                validated_quality_result.quality_input_hash,
                expected_quality_input_hash,
            ),
            (
                "quality_input_hash",
                validated_operation.quality_input_hash,
                expected_quality_input_hash,
            ),
            (
                "scoring_request_hash",
                validated_quality_input.scoring_request_hash,
                identity.request_hash,
            ),
            (
                "scoring_request_hash",
                validated_quality_result.scoring_request_hash,
                identity.request_hash,
            ),
            (
                "scoring_request_hash",
                validated_operation.scoring_request_hash,
                identity.request_hash,
            ),
            ("output_language", validated_quality_input.output_language, scoring_context.output_language),
            ("candidate reason", validated_quality_input.reason, validated_candidate.reason),
            ("candidate topics", validated_quality_input.topics, validated_candidate.topics),
        )
        for name, actual, expected in bindings:
            if actual != expected:
                raise ValueError(f"{name} mismatches trusted finalization input")

        verified_attestation = verify_quality_pass_attestation(
            attestation,
            quality_result=validated_quality_result,
            operation_input=validated_operation,
            quality_input=validated_quality_input,
            authority=quality_authority,
        )
        if verified_attestation.scoring_request_hash != identity.request_hash:
            raise ValueError("quality attestation mismatches canonical scoring identity")

        result = ScoreResult.model_validate(
            {
                "schema_version": scoring_context.scoring_schema_version,
                "score": validated_candidate.score,
                "reason": validated_candidate.reason,
                "topics": validated_candidate.topics,
                "should_summarize": validated_candidate.should_summarize,
                "dimensions": validated_candidate.dimensions,
                "provider": scoring_context.scoring_provider,
                "model": scoring_context.scoring_model,
                "prompt_version": scoring_context.scoring_prompt_version,
                "request_hash": identity.request_hash,
                "output_language": scoring_context.output_language,
            }
        )
        return TrustedScoreResult(
            sentinel=_TRUSTED_SCORE_RESULT_SENTINEL,
            result=result,
        )
