"""TASK-016C Phase H2-A — PRIMARY/Judge raw capture seams and parser replay.

RED-first tests for the private received-raw outcome seams added to the Ollama
provider adapter and the pure parser diagnostic mapper that reproduces the
existing ``parse_scoring_candidate`` fail-closed behavior with closed
``diagnostic_code`` values.

Authoritative contract: docs/TASK-016C-PHASE-H2-AUTHORIZATION.md
(PRIVATE PRIMARY received-raw outcome seam; Parser and language evidence;
Judge raw, outcome split).  Exception messages are never authority: only the
typed diagnostic codes and the raw/hash/length bindings are asserted here.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from youtube_intel.providers.ollama import (
    JudgeRawCapture,
    ParserDiagnosticCode,
    PrimaryRawCapture,
    diagnose_scoring_parse_failure,
    parse_scoring_candidate,
    seal_judge_raw_capture,
    seal_primary_raw_capture,
)

_MAX_PRIMARY_RAW_BYTES = 1_000_000
_MAX_JUDGE_RAW_BYTES = 20_000


def _generate_body(inner: object | str, *, extra: dict[str, object] | None = None) -> bytes:
    inner_text = (
        inner
        if isinstance(inner, str)
        else json.dumps(inner, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    payload: dict[str, object] = {"model": "qwen3:8b", "response": inner_text, "done": True}
    if extra:
        payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


_VALID_CANDIDATE = {
    "score": 8,
    "reason": "A clear and useful explanation of the topic.",
    "topics": ["topic"],
    "should_summarize": True,
}


# ---------------------------------------------------------------------------
# PRIMARY raw capture seam
# ---------------------------------------------------------------------------


def test_primary_raw_successful_bounded_capture() -> None:
    body = _generate_body(_VALID_CANDIDATE)
    capture = seal_primary_raw_capture(body)
    assert isinstance(capture, PrimaryRawCapture)
    assert capture.utf8 == body.decode("utf-8")
    assert capture.byte_length == len(body)
    assert capture.sha256 == hashlib.sha256(body).hexdigest()


def test_primary_raw_preserves_whitespace_and_multibyte_bytes() -> None:
    candidate = dict(_VALID_CANDIDATE)
    candidate["reason"] = "  leading and trailing 中文 reason  "
    body = _generate_body(candidate)
    capture = seal_primary_raw_capture(body)
    assert capture.utf8 == body.decode("utf-8")
    assert "中文" in capture.utf8
    assert capture.byte_length == len(capture.utf8.encode("utf-8"))
    # Byte length differs from character length because of multibyte text.
    assert capture.byte_length != len(capture.utf8)


def test_primary_raw_exact_inclusive_max_bound_is_accepted() -> None:
    base = _generate_body(_VALID_CANDIDATE)
    # Pad the inner response with a filler field to reach exactly the bound.
    padding_target = _MAX_PRIMARY_RAW_BYTES - len(base)
    assert padding_target > 0
    candidate = dict(_VALID_CANDIDATE)
    candidate["reason"] = "A" * (padding_target + len(_VALID_CANDIDATE["reason"]))
    body = _generate_body(candidate)
    assert len(body) == _MAX_PRIMARY_RAW_BYTES
    capture = seal_primary_raw_capture(body)
    assert capture.byte_length == _MAX_PRIMARY_RAW_BYTES


def test_primary_raw_over_limit_rejects() -> None:
    oversized = json.dumps(
        {"response": "x" * (_MAX_PRIMARY_RAW_BYTES + 1)},
        ensure_ascii=False,
    ).encode("utf-8")
    assert len(oversized) > _MAX_PRIMARY_RAW_BYTES
    with pytest.raises(ValueError):
        seal_primary_raw_capture(oversized)


def test_primary_raw_strict_utf8_decode_failure_rejects() -> None:
    with pytest.raises(ValueError):
        seal_primary_raw_capture(b"\xff\xfe\xfd not utf-8")


def test_primary_raw_outer_json_invalid_rejects() -> None:
    with pytest.raises(ValueError):
        seal_primary_raw_capture(b"{not-json")


def test_primary_raw_outer_not_object_rejects() -> None:
    with pytest.raises(ValueError):
        seal_primary_raw_capture(b"[1,2,3]")


def test_primary_raw_missing_response_rejects() -> None:
    with pytest.raises(ValueError):
        seal_primary_raw_capture(b'{"model":"m","done":true}')


def test_primary_raw_non_string_response_rejects() -> None:
    with pytest.raises(ValueError):
        seal_primary_raw_capture(b'{"response":123}')


def test_primary_raw_empty_response_is_valid_capture() -> None:
    body = b'{"response":""}'
    capture = seal_primary_raw_capture(body)
    assert capture.utf8 == '{"response":""}'


def test_primary_raw_valid_body_but_scoring_parse_invalid_is_trusted_raw() -> None:
    # Outer protocol is complete and response is a string, but the inner model
    # JSON is invalid: the raw is still trustworthy (schema/parse failure path).
    body = _generate_body("{not-inner-json")
    capture = seal_primary_raw_capture(body)
    assert capture.sha256 == hashlib.sha256(body).hexdigest()
    # The parser then classifies this deterministically.
    assert diagnose_scoring_parse_failure(capture.utf8) is ParserDiagnosticCode.MODEL_JSON_INVALID


def test_primary_raw_reencode_matches_authoritative_bytes() -> None:
    body = _generate_body(_VALID_CANDIDATE)
    capture = seal_primary_raw_capture(body)
    reencoded = capture.utf8.encode("utf-8", errors="strict")
    assert reencoded == body
    assert len(reencoded) == capture.byte_length


# ---------------------------------------------------------------------------
# Judge raw capture seam
# ---------------------------------------------------------------------------


def test_judge_raw_normal_utf8_capture() -> None:
    content = "the judge says hello"
    capture = seal_judge_raw_capture(content)
    assert isinstance(capture, JudgeRawCapture)
    assert capture.utf8 == content
    assert capture.byte_length == len(content.encode("utf-8"))
    assert capture.sha256 == hashlib.sha256(content.encode("utf-8")).hexdigest()


def test_judge_raw_preserves_whitespace() -> None:
    content = "  padded \n\t content  "
    capture = seal_judge_raw_capture(content)
    assert capture.utf8 == content


def test_judge_raw_empty_content_is_valid() -> None:
    capture = seal_judge_raw_capture("")
    assert capture.utf8 == ""
    assert capture.byte_length == 0
    assert capture.sha256 == hashlib.sha256(b"").hexdigest()


def test_judge_raw_exactly_20000_bytes_accepted() -> None:
    content = "a" * _MAX_JUDGE_RAW_BYTES
    capture = seal_judge_raw_capture(content)
    assert capture.byte_length == _MAX_JUDGE_RAW_BYTES


def test_judge_raw_20001_bytes_rejected() -> None:
    content = "a" * (_MAX_JUDGE_RAW_BYTES + 1)
    with pytest.raises(ValueError):
        seal_judge_raw_capture(content)


def test_judge_raw_multibyte_char_vs_byte_bound() -> None:
    # <= 20,000 characters but > 20,000 UTF-8 bytes must be rejected because the
    # trust bound is the encoded byte length, not the character count.
    content = "中" * 7_000  # 7,000 chars, 21,000 UTF-8 bytes
    assert len(content) <= _MAX_JUDGE_RAW_BYTES
    assert len(content.encode("utf-8")) > _MAX_JUDGE_RAW_BYTES
    with pytest.raises(ValueError):
        seal_judge_raw_capture(content)


def test_judge_raw_lone_surrogate_rejected_not_uncertain() -> None:
    with pytest.raises(ValueError):
        seal_judge_raw_capture("\ud800")


# ---------------------------------------------------------------------------
# Parser diagnostic mapper and equivalence with parse_scoring_candidate
# ---------------------------------------------------------------------------


def test_diagnose_success_returns_none() -> None:
    raw = _generate_body(_VALID_CANDIDATE).decode("utf-8")
    assert diagnose_scoring_parse_failure(raw) is None
    # And the shared parser succeeds on the same input.
    parse_scoring_candidate(raw)


def test_diagnose_raw_utf8_invalid() -> None:
    assert diagnose_scoring_parse_failure("\ud800") is ParserDiagnosticCode.RAW_UTF8_INVALID


def test_diagnose_raw_bytes_limit_exceeded() -> None:
    raw = "x" * (_MAX_PRIMARY_RAW_BYTES + 1)
    assert diagnose_scoring_parse_failure(raw) is ParserDiagnosticCode.RAW_BYTES_LIMIT_EXCEEDED


def test_diagnose_outer_json_invalid() -> None:
    assert diagnose_scoring_parse_failure("{bad") is ParserDiagnosticCode.OUTER_JSON_INVALID


def test_diagnose_outer_top_level_type_invalid() -> None:
    assert (
        diagnose_scoring_parse_failure("[1,2]") is ParserDiagnosticCode.OUTER_TOP_LEVEL_TYPE_INVALID
    )


def test_diagnose_model_response_missing() -> None:
    assert (
        diagnose_scoring_parse_failure('{"model":"m"}')
        is ParserDiagnosticCode.MODEL_RESPONSE_MISSING
    )


def test_diagnose_model_response_type_invalid() -> None:
    assert (
        diagnose_scoring_parse_failure('{"response":123}')
        is ParserDiagnosticCode.MODEL_RESPONSE_TYPE_INVALID
    )


def test_diagnose_model_response_length_exceeded() -> None:
    raw = json.dumps({"response": "x" * 20_001}, ensure_ascii=False)
    assert (
        diagnose_scoring_parse_failure(raw)
        is ParserDiagnosticCode.MODEL_RESPONSE_LENGTH_EXCEEDED
    )


def test_diagnose_model_json_invalid() -> None:
    raw = _generate_body("{not-json").decode("utf-8")
    assert diagnose_scoring_parse_failure(raw) is ParserDiagnosticCode.MODEL_JSON_INVALID


def test_diagnose_model_top_level_type_invalid() -> None:
    raw = _generate_body("[1,2]").decode("utf-8")
    assert diagnose_scoring_parse_failure(raw) is ParserDiagnosticCode.MODEL_TOP_LEVEL_TYPE_INVALID


def test_diagnose_model_field_set_invalid() -> None:
    bad = dict(_VALID_CANDIDATE)
    bad["unexpected_field"] = 1
    raw = _generate_body(bad).decode("utf-8")
    assert diagnose_scoring_parse_failure(raw) is ParserDiagnosticCode.MODEL_FIELD_SET_INVALID


def test_diagnose_candidate_schema_invalid() -> None:
    bad = dict(_VALID_CANDIDATE)
    bad["score"] = 99  # outside 0..10
    raw = _generate_body(bad).decode("utf-8")
    assert diagnose_scoring_parse_failure(raw) is ParserDiagnosticCode.CANDIDATE_SCHEMA_INVALID


@pytest.mark.parametrize(
    "raw",
    [
        "\ud800",
        "x" * (_MAX_PRIMARY_RAW_BYTES + 1),
        "{bad",
        "[1,2]",
        '{"model":"m"}',
        '{"response":123}',
        json.dumps({"response": "x" * 20_001}, ensure_ascii=False),
        _generate_body("{not-json").decode("utf-8"),
        _generate_body("[1,2]").decode("utf-8"),
        _generate_body({**_VALID_CANDIDATE, "unexpected": 1}).decode("utf-8"),
        _generate_body({**_VALID_CANDIDATE, "score": 99}).decode("utf-8"),
        _generate_body(_VALID_CANDIDATE).decode("utf-8"),
        _generate_body("").decode("utf-8"),
    ],
)
def test_diagnose_equivalence_with_shared_parser(raw: str) -> None:
    """The mapper agrees with parse_scoring_candidate on success vs failure."""

    code = diagnose_scoring_parse_failure(raw)
    try:
        parse_scoring_candidate(raw)
    except ValueError:
        parser_failed = True
    else:
        parser_failed = False
    assert (code is not None) == parser_failed
