"""TASK-016C Phase B deterministic safety gate tests (RED-before-GREEN)."""

from __future__ import annotations

import pytest

from youtube_intel.domain import (
    ContentQualityConfidence,
    ContentQualityDecisionSource,
    ContentQualityResult,
    ContentQualityStatus,
    DeterministicGateReason,
)
from youtube_intel.quality import DeterministicContentQualityGate

VALID_HASH = "a" * 64


@pytest.fixture
def gate() -> DeterministicContentQualityGate:
    return DeterministicContentQualityGate()


def _gate_result(
    gate: DeterministicContentQualityGate,
    content: str,
) -> ContentQualityResult | None:
    return gate.evaluate(
        content=content,
        candidate_hash=VALID_HASH,
        quality_input_hash=VALID_HASH,
        scoring_request_hash=VALID_HASH,
    )


class TestEmptyContent:
    def test_raw_empty_rejects(self, gate: DeterministicContentQualityGate) -> None:
        result = _gate_result(gate, "")
        assert result is not None
        assert result.status is ContentQualityStatus.REJECT
        assert result.reason is DeterministicGateReason.EMPTY_CONTENT

    def test_ascii_whitespace_only_rejects(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "   \t\n\r\v\f  ")
        assert result is not None
        assert result.reason is DeterministicGateReason.EMPTY_CONTENT

    def test_space_only_rejects(self, gate: DeterministicContentQualityGate) -> None:
        result = _gate_result(gate, "     ")
        assert result is not None
        assert result.reason is DeterministicGateReason.EMPTY_CONTENT

    def test_trim_boundary_accepts(self, gate: DeterministicContentQualityGate) -> None:
        result = _gate_result(gate, "  a  ")
        assert result is None


class TestControlCharacterInvalid:
    def test_lf_accepted(self, gate: DeterministicContentQualityGate) -> None:
        result = _gate_result(gate, "line one\nline two")
        assert result is None

    def test_tab_accepted(self, gate: DeterministicContentQualityGate) -> None:
        result = _gate_result(gate, "col1\tcol2")
        assert result is None

    def test_null_rejects(self, gate: DeterministicContentQualityGate) -> None:
        result = _gate_result(gate, "hello\x00world")
        assert result is not None
        assert result.reason is DeterministicGateReason.CONTROL_CHARACTER_INVALID

    def test_vertical_tab_rejects(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "hello\vworld")
        assert result is not None
        assert result.reason is DeterministicGateReason.CONTROL_CHARACTER_INVALID

    def test_carriage_return_rejects(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "hello\rworld")
        assert result is not None
        assert result.reason is DeterministicGateReason.CONTROL_CHARACTER_INVALID

    def test_form_feed_rejects(self, gate: DeterministicContentQualityGate) -> None:
        result = _gate_result(gate, "hello\fworld")
        assert result is not None
        assert result.reason is DeterministicGateReason.CONTROL_CHARACTER_INVALID

    def test_zwsp_rejects(self, gate: DeterministicContentQualityGate) -> None:
        result = _gate_result(gate, "hello\u200bworld")
        assert result is not None
        assert result.reason is DeterministicGateReason.CONTROL_CHARACTER_INVALID

    def test_bom_rejects(self, gate: DeterministicContentQualityGate) -> None:
        result = _gate_result(gate, "hello\ufeffworld")
        assert result is not None
        assert result.reason is DeterministicGateReason.CONTROL_CHARACTER_INVALID

    def test_leading_control_rejects(self, gate: DeterministicContentQualityGate) -> None:
        result = _gate_result(gate, "\x01hello")
        assert result is not None
        assert result.reason is DeterministicGateReason.CONTROL_CHARACTER_INVALID

    def test_trailing_control_rejects(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "hello\x1f")
        assert result is not None
        assert result.reason is DeterministicGateReason.CONTROL_CHARACTER_INVALID

    def test_mixed_lf_and_cr_rejects(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "line one\nline two\r")
        assert result is not None
        assert result.reason is DeterministicGateReason.CONTROL_CHARACTER_INVALID


class TestExactRepetition:
    def test_adjacent_same_rejects(self, gate: DeterministicContentQualityGate) -> None:
        result = _gate_result(gate, "A\nA")
        assert result is not None
        assert result.reason is DeterministicGateReason.EXACT_REPETITION

    def test_adjacent_different_accepts(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "A\nB")
        assert result is None

    def test_non_adjacent_same_accepts(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "A\nB\nA")
        assert result is None

    def test_case_sensitive_no_reject(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "Same\nsame")
        assert result is None

    def test_empty_segment_removal_rejects(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "A\n\nA")
        assert result is not None
        assert result.reason is DeterministicGateReason.EXACT_REPETITION

    def test_ascii_trim_then_reject(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "  A\nA  ")
        assert result is not None
        assert result.reason is DeterministicGateReason.EXACT_REPETITION

    def test_multiple_adjacent_rejects(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "A\nA\nA")
        assert result is not None
        assert result.reason is DeterministicGateReason.EXACT_REPETITION

    def test_single_segment_accepts(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "A")
        assert result is None

    def test_whitespace_only_segments_are_not_empty(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        # "exact-empty removal" removes only the empty string segment;
        # whitespace-only segments are preserved and prevent adjacent equality.
        result = _gate_result(gate, "A\n   \nA")
        assert result is None


class TestStructuralAndBoundary:
    def test_identifier_phrase_continues(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "API Gateway")
        assert result is None

    def test_technical_phrase_continues(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "TensorFlow 2.x + PyTorch")
        assert result is None

    def test_entity_phrase_continues(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "OpenAI GPT-4")
        assert result is None

    def test_multiline_valid_transcript_continues(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "first idea\nsecond idea\nthird idea")
        assert result is None


class TestGateResultContract:
    def test_reject_result_has_deterministic_source(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "")
        assert result is not None
        assert result.decision_source is ContentQualityDecisionSource.DETERMINISTIC_GATE
        assert result.status is ContentQualityStatus.REJECT
        assert result.decision_confidence is ContentQualityConfidence.HIGH
        assert result.grounding_confidence is ContentQualityConfidence.LOW
        assert result.usefulness_confidence is ContentQualityConfidence.LOW
        assert result.signals == ()
        assert result.evidence_ids == ()
        assert result.judge_provider is None
        assert result.judge_model is None
        assert result.judge_model_digest is None

    def test_hashes_propagate(self, gate: DeterministicContentQualityGate) -> None:
        result = _gate_result(gate, "")
        assert result is not None
        assert result.candidate_hash == VALID_HASH
        assert result.quality_input_hash == VALID_HASH
        assert result.scoring_request_hash == VALID_HASH

    def test_valid_content_returns_none(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        result = _gate_result(gate, "This content is acceptable.")
        assert result is None


class TestMutationKillers:
    """Tests designed to kill likely implementation mutants."""

    def test_removing_control_validation_fails(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        """If control validation is removed, \x00 would be accepted."""
        result = _gate_result(gate, "\x00")
        assert result is not None
        assert result.reason is DeterministicGateReason.CONTROL_CHARACTER_INVALID

    def test_fuzzy_comparison_fails(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        """If fuzzy/lower-case comparison is used, Same/same would reject."""
        result = _gate_result(gate, "Same\nsame")
        assert result is None

    def test_casefold_comparison_fails(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        """If casefold is used, TÜRK/türk would reject."""
        result = _gate_result(gate, "TÜRK\ntürk")
        assert result is None

    def test_removing_exact_empty_filter_fails(
        self,
        gate: DeterministicContentQualityGate,
    ) -> None:
        """If empty segments are not removed, A\n\nA would be accepted."""
        result = _gate_result(gate, "A\n\nA")
        assert result is not None
        assert result.reason is DeterministicGateReason.EXACT_REPETITION
