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
)
from youtube_intel.state import build_provider_request_hash

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
