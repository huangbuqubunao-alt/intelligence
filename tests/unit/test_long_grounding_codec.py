"""Synthetic, offline codec cases; these confer no model qualification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from youtube_intel import long_grounding_codec as codec
from youtube_intel.long_grounding_codec import (
    EvidenceSpan,
    decode_output,
    encode_grounding,
    expand_grounding,
)
from youtube_intel.state import (
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    VerifiedEvidenceText,
    VerifiedTimedTranscript,
    VerifiedTimedTranscriptCue,
)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def fixture(texts=("same", "same", "same", "tail"), cuts=(2, 4)):
    written = TimedTranscriptWrite.from_cues(
        video_id="synthetic-video",
        canonical_artifact_id="canonical-a",
        cues=tuple(
            TimedTranscriptCueWrite(i * 10, i * 10 + 9, text)
            for i, text in enumerate(texts)
        ),
    )
    timed = VerifiedTimedTranscript(
        written.timed_transcript_id,
        written.video_id,
        written.canonical_artifact_id,
        written.timed_transcript_hash,
        tuple(
            VerifiedTimedTranscriptCue(i, c.start_ms, c.end_ms, c.text, c.text_hash)
            for i, c in enumerate(written.cues)
        ),
    )
    spans, first = [], 0
    for number, last in enumerate(cuts):
        cues = timed.cues[first:last]
        excerpt = "\n".join(c.text for c in cues)
        item = VerifiedEvidenceText(
            f"runtime-evidence-{number}",
            timed.video_id,
            timed.timed_transcript_id,
            timed.timed_transcript_hash,
            cues[0].start_ms,
            cues[-1].end_ms,
            excerpt,
            digest(excerpt),
        )
        spans.append(EvidenceSpan(item, first, last))
        first = last
    return timed, tuple(spans)


def encode(timed=None, spans=None, **changes):
    if timed is None:
        timed, spans = fixture()
    return encode_grounding(
        source_id="source-a",
        content_provider="YOUTUBE",
        source_content_hash="a" * 64,
        canonical_text_hash="b" * 64,
        transcript=timed,
        evidence=spans,
        **changes,
    )


def payload(*, positive=False):
    result = {
        "result": "NO_NEW_INTELLIGENCE",
        "evidence": [
            {"evidence_id": "E1", "start_ms": 0, "end_ms": 19},
            {"evidence_id": "E2", "start_ms": 20, "end_ms": 39},
        ],
    }
    if positive:
        result.update(
            result="INTELLIGENCE",
            core_conclusion="A source guess; not a guarantee. 中\n文",
            user_relevant_information=["Relevance"],
            important_new_information=[],
            meaningful_details=["uncertain\tmeasurement"],
            filtered_noise=[],
            claim_kind="PREDICTION",
        )
        for ref, stance in zip(result["evidence"], ("supporting", "conditional")):
            ref["stance"] = stance
    return result


def wire(value):
    return json.dumps(value, ensure_ascii=False).encode()


def test_roundtrip_preserves_every_cue_and_excerpt_and_rle_never_crosses_evidence():
    timed, spans = fixture()
    encoded = encode(timed, spans)
    expanded = expand_grounding(encoded)
    assert expanded.transcript == timed
    assert expanded.evidence == spans
    rows = json.loads(encoded.canonical_wire)["evidence"]
    assert [len(row["runs"]) for row in rows] == [1, 2]
    assert rows[0]["runs"][0]["cues"] == [
        [0, 0, 9, digest("same")],
        [1, 10, 19, digest("same")],
    ]
    assert encoded.input_hash == hashlib.sha256(encoded.canonical_wire).hexdigest()
    assert encode(timed, spans) == encoded


def test_hash_binds_evidence_grouping_source_identity_and_canonical_order():
    timed, spans = fixture()
    assert encode(timed, spans).input_hash != encode(*fixture(cuts=(1, 4))).input_hash
    assert (
        encode(timed, spans).input_hash
        != encode(
            timed,
            tuple(
                replace(
                    s,
                    evidence=replace(
                        s.evidence, evidence_id="qa-" + s.evidence.evidence_id
                    ),
                )
                for s in spans
            ),
        ).input_hash
    )
    with pytest.raises(ValueError):
        encode(timed, spans[::-1])


@pytest.mark.parametrize(
    "texts",
    [
        ("  x ", "x", "x\n", "tail\t"),
        ("é", "e\u0301", "中😀\n\t\x00", "tail\r\n"),
        ("same", "same ", "same", "same"),
    ],
)
def test_no_trim_normalization_control_character_loss_or_fuzzy_rle(texts):
    timed, spans = fixture(texts)
    assert expand_grounding(encode(timed, spans)).transcript == timed
    assert expand_grounding(encode(timed, spans)).evidence == spans


@pytest.mark.parametrize(
    "failure",
    [
        "missing",
        "repeated",
        "gap",
        "overlap",
        "index",
        "time-bool",
        "time-overlap",
        "cue-hash",
        "transcript-hash",
        "transcript-id",
        "evidence-hash",
        "evidence-time",
        "foreign",
        "text-range",
        "extra-locator",
    ],
)
def test_rejects_inconsistent_or_ambiguous_inputs(failure):
    timed, spans = fixture()
    if failure == "missing":
        spans = spans[:-1]
    elif failure == "repeated":
        spans = (spans[0], replace(spans[1], evidence=spans[0].evidence))
    elif failure == "gap":
        spans = (replace(spans[0], end_cue_index=1), spans[1])
    elif failure == "overlap":
        spans = (spans[0], replace(spans[1], start_cue_index=1))
    elif failure in {"index", "time-bool", "time-overlap", "cue-hash"}:
        changes = {
            "index": {"cue_index": 1},
            "time-bool": {"start_ms": False},
            "time-overlap": {"end_ms": 11},
            "cue-hash": {"text_hash": "f" * 64},
        }[failure]
        timed = replace(
            timed, cues=(replace(timed.cues[0], **changes), *timed.cues[1:])
        )
    elif failure == "transcript-hash":
        timed = replace(timed, timed_transcript_hash="f" * 64)
    elif failure == "transcript-id":
        timed = replace(timed, timed_transcript_id="foreign")
    else:
        changes = {
            "evidence-hash": {"excerpt_hash": "f" * 64},
            "evidence-time": {"start_ms": 1},
            "foreign": {"video_id": "other"},
            "text-range": {"locator_type": "TEXT_RANGE"},
            "extra-locator": {"start_offset": 0},
        }[failure]
        spans = (
            replace(spans[0], evidence=replace(spans[0].evidence, **changes)),
            spans[1],
        )
    with pytest.raises(ValueError):
        encode(timed, spans)


def test_rejects_mutable_input_containers_and_keeps_output_values_independent():
    timed, spans = fixture()
    with pytest.raises(ValueError):
        encode(timed, list(spans))
    with pytest.raises(ValueError):
        encode(replace(timed, cues=list(timed.cues)), spans)
    encoded = encode(timed, spans)
    result = decode_output(wire(payload()), encoded)
    value = result.decoded_value
    value["evidence"].clear()
    assert len(result.decoded_value["evidence"]) == 2
    assert expand_grounding(encoded).evidence == spans


@pytest.mark.parametrize("positive", [False, True])
def test_decode_replaces_ids_only_and_preserves_original_wire_separately(positive):
    model_value = payload(positive=positive)
    raw = b" \n" + wire(model_value) + b"\n"
    decoded = decode_output(raw, encode())
    expected = json.loads(raw)
    for i, ref in enumerate(expected["evidence"]):
        ref["evidence_id"] = f"runtime-evidence-{i}"
    assert decoded.decoded_value == expected
    assert decoded.public_wire == raw
    assert decoded.public_wire_hash == hashlib.sha256(raw).hexdigest()
    assert decoded.decoded_hash == hashlib.sha256(decoded.decoded_wire).hexdigest()
    assert decoded.input_hash == encode().input_hash


@pytest.mark.parametrize(
    "failure",
    [
        "E01",
        "unknown",
        "runtime-id",
        "duplicate",
        "missing",
        "reorder",
        "extra-ref",
        "extra-field",
        "bool-time",
        "wrong-time",
        "float-time",
        "null",
        "empty",
        "wrong-branch",
        "zero-stance",
    ],
)
def test_no_new_is_complete_exact_unique_and_in_canonical_order_before_expansion(
    failure,
):
    value = payload()
    refs = value["evidence"]
    if failure in {"E01", "unknown", "runtime-id"}:
        refs[0]["evidence_id"] = {
            "E01": "E01",
            "unknown": "E3",
            "runtime-id": "runtime-evidence-0",
        }[failure]
    elif failure == "duplicate":
        refs[1] = dict(refs[0])
    elif failure == "missing":
        refs.pop()
    elif failure == "reorder":
        refs.reverse()
    elif failure == "extra-ref":
        refs.append(dict(refs[0]))
    elif failure == "extra-field":
        value["extra"] = "bad"
    elif failure in {"bool-time", "wrong-time", "float-time"}:
        refs[0]["start_ms"] = {"bool-time": False, "wrong-time": 1, "float-time": 0.0}[
            failure
        ]
    elif failure == "null":
        value["evidence"] = None
    elif failure == "empty":
        refs.clear()
    elif failure == "wrong-branch":
        value["result"] = "INTELLIGENCE"
    elif failure == "zero-stance":
        refs[0]["stance"] = "supporting"
    with pytest.raises(ValueError):
        decode_output(wire(value), encode())


@pytest.mark.parametrize(
    "failure",
    [
        "no-support",
        "unknown-stance",
        "unclassified",
        "no-evidence",
        "extra-field",
        "missing-field",
        "blank",
        "trim",
        "list-type",
        "many-texts",
        "long-text",
    ],
)
def test_intelligence_retains_existing_shape_and_claim_support_boundaries(failure):
    value = payload(positive=True)
    if failure == "no-support":
        value["evidence"][0]["stance"] = "contradicting"
    elif failure == "unknown-stance":
        value["evidence"][0]["stance"] = "unknown"
    elif failure == "unclassified":
        value["claim_kind"] = "UNCLASSIFIED"
    elif failure == "no-evidence":
        value["evidence"] = []
    elif failure == "extra-field":
        value["language"] = "en"
    elif failure == "missing-field":
        value.pop("filtered_noise")
    elif failure == "blank":
        value["core_conclusion"] = " "
    elif failure == "trim":
        value["core_conclusion"] = " claim "
    elif failure == "list-type":
        value["meaningful_details"] = "detail"
    elif failure == "many-texts":
        value["meaningful_details"] = ["detail"] * 21
    elif failure == "long-text":
        value["core_conclusion"] = "x" * 4001
    with pytest.raises(ValueError):
        decode_output(wire(value), encode())


@pytest.mark.parametrize(
    "raw",
    [
        b"\xff",
        b"{} {}",
        b"```json\n{}\n```",
        b'{"result":"NO_NEW_INTELLIGENCE","result":"INTELLIGENCE"}',
        b'{"evidence":NaN}',
        b'{"evidence":Infinity}',
        b'{"evidence":-Infinity}',
        b'"\\ud800"',
        b"[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]",
    ],
)
def test_strict_json_rejects_invalid_utf8_duplicates_nonfinite_surrogates_and_nesting(
    raw,
):
    with pytest.raises(ValueError):
        decode_output(raw, encode())


def test_frozen_packet_cannot_be_replaced_by_noncanonical_or_tampered_bytes():
    encoded = encode()
    for body in (
        b"{}",
        b" " + encoded.canonical_wire,
        encoded.canonical_wire.replace(b'"alias":"E1"', b'"alias":"E01"'),
    ):
        with pytest.raises(ValueError):
            expand_grounding(replace(encoded, canonical_wire=body))


def test_explicit_source_and_wire_resource_limits():
    with pytest.raises(ValueError):
        decode_output(b" " * 1_000_001, encode())
    timed, spans = fixture(("x" * 4001, "b", "c", "d"))
    with pytest.raises(ValueError):
        encode(timed, spans)
    timed, spans = fixture()
    with pytest.raises(ValueError):
        encode_grounding(
            source_id="s" * 513,
            content_provider="YOUTUBE",
            source_content_hash="a" * 64,
            canonical_text_hash="b" * 64,
            transcript=timed,
            evidence=spans,
        )


def test_complete_long_synthetic_source_has_no_twenty_evidence_truncation():
    # Match the known source's dimensions without reading its text or model data.
    texts = tuple(f"synthetic {i // 4} é e\u0301 😀\t\x00" for i in range(2406))
    cuts = tuple((2406 * i) // 114 for i in range(1, 115))
    timed, spans = fixture(texts, cuts)
    encoded = encode(timed, spans)
    expanded = expand_grounding(encoded)
    assert expanded.transcript == timed
    assert expanded.evidence == spans
    rows = json.loads(encoded.canonical_wire)["evidence"]
    assert [row["alias"] for row in rows] == [f"E{i}" for i in range(1, 115)]
    refs = [
        {
            "evidence_id": f"E{i}",
            "start_ms": s.evidence.start_ms,
            "end_ms": s.evidence.end_ms,
        }
        for i, s in enumerate(spans, 1)
    ]
    decoded = decode_output(
        wire({"result": "NO_NEW_INTELLIGENCE", "evidence": refs}), encoded
    )
    assert [r["evidence_id"] for r in decoded.decoded_value["evidence"]] == [
        s.evidence.evidence_id for s in spans
    ]


def test_bytes_remain_frozen_after_caller_owned_object_mutation():
    timed, spans = fixture()
    encoded = encode(timed, spans)
    original_wire, original_hash = encoded.canonical_wire, encoded.input_hash
    original = expand_grounding(encoded)
    # Frozen dataclasses can be bypassed by hostile callers; stored bytes must
    # still never alias the original objects or a returned mutable JSON value.
    object.__setattr__(timed.cues[0], "text", "changed")
    object.__setattr__(spans[0].evidence, "evidence_id", "changed")
    assert encoded.canonical_wire == original_wire
    assert encoded.input_hash == original_hash
    assert expand_grounding(encoded) == original


@pytest.mark.parametrize(
    "field",
    ["source_id", "content_provider", "source_content_hash", "canonical_text_hash"],
)
def test_packet_hash_binds_each_source_identity(field):
    timed, spans = fixture()
    values = dict(
        source_id="source-a",
        content_provider="YOUTUBE",
        source_content_hash="a" * 64,
        canonical_text_hash="b" * 64,
        transcript=timed,
        evidence=spans,
    )
    changed = {
        "source_id": "source-b",
        "content_provider": "LOCAL",
        "source_content_hash": "c" * 64,
        "canonical_text_hash": "d" * 64,
    }
    assert (
        encode_grounding(**values).input_hash
        != encode_grounding(**{**values, field: changed[field]}).input_hash
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "version",
        "field",
        "run-field",
        "row-field",
        "time",
        "index",
        "hash",
        "excerpt-hash",
        "source-hash",
        "boolean-index",
        "boolean-time",
        "missing-cue",
        "repeated-cue",
        "split-run",
    ],
)
def test_expansion_rejects_noncanonical_or_inconsistent_packet(mutation):
    packet = json.loads(encode().canonical_wire)
    row = packet["evidence"][0]
    run = row["runs"][0]
    if mutation == "version":
        packet["codec_version"] = "local-grounding-complete-evidence-v1"
    elif mutation == "field":
        packet["unknown"] = 1
    elif mutation == "run-field":
        run["unknown"] = 1
    elif mutation == "row-field":
        row["unknown"] = 1
    elif mutation == "time":
        run["cues"][0][1] = 1
    elif mutation == "index":
        run["cues"][0][0] = 1
    elif mutation == "hash":
        run["cues"][0][3] = "f" * 64
    elif mutation == "excerpt-hash":
        row["excerpt_hash"] = "f" * 64
    elif mutation == "source-hash":
        row["source_content_hash"] = "f" * 64
    elif mutation == "boolean-index":
        row["start_cue_index"] = False
    elif mutation == "boolean-time":
        row["start_ms"] = False
    elif mutation == "missing-cue":
        run["cues"].pop()
    elif mutation == "repeated-cue":
        run["cues"].append(run["cues"][0])
    elif mutation == "split-run":
        row["runs"] = [
            {"text": run["text"], "cues": [marker]} for marker in run["cues"]
        ]
    canonical = json.dumps(
        packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    with pytest.raises(ValueError):
        expand_grounding(codec.EncodedGrounding(canonical))


@pytest.mark.parametrize(
    "bound",
    [
        "MAX_CUES",
        "MAX_EVIDENCE",
        "MAX_EXCERPT_CHARS",
        "MAX_CANONICAL_CHARS",
        "MAX_CANONICAL_BYTES",
        "MAX_INPUT_BYTES",
    ],
)
def test_encode_and_expand_explicitly_reject_each_resource_limit(monkeypatch, bound):
    packet = encode()
    monkeypatch.setattr(codec, bound, 1)
    with pytest.raises(ValueError):
        encode()
    with pytest.raises(ValueError):
        expand_grounding(packet)


@pytest.mark.parametrize(
    "number", [-1, True, False, 0.0, float("nan"), float("inf"), -(float("inf")), 2**63]
)
def test_each_integer_input_boundary_rejects_type_confusion_and_overflow(number):
    timed, spans = fixture()
    for field in ("cue_index", "start_ms", "end_ms"):
        changed = replace(
            timed, cues=(replace(timed.cues[0], **{field: number}), *timed.cues[1:])
        )
        with pytest.raises(ValueError):
            encode(changed, spans)
    for field in ("start_cue_index", "end_cue_index"):
        with pytest.raises(ValueError):
            encode(timed, (replace(spans[0], **{field: number}), spans[1]))
    for field in ("start_ms", "end_ms"):
        changed = replace(
            spans[0], evidence=replace(spans[0].evidence, **{field: number})
        )
        with pytest.raises(ValueError):
            encode(timed, (changed, spans[1]))


@pytest.mark.parametrize("positive", [False, True])
def test_duplicate_nested_keys_and_overflowing_float_are_rejected(positive):
    raw = wire(payload(positive=positive))
    assert b'"start_ms": 0' in raw
    with pytest.raises(ValueError):
        decode_output(
            raw.replace(b'"start_ms": 0', b'"start_ms": 0,"start_ms": 0'), encode()
        )
    with pytest.raises(ValueError):
        decode_output(raw.replace(b'"start_ms": 0', b'"start_ms": 1e999'), encode())


@pytest.mark.parametrize("count", [20, 21])
def test_positive_reference_boundary_stays_at_accepted_twenty(count):
    timed, spans = fixture(tuple(f"text {i}" for i in range(21)), tuple(range(1, 22)))
    packet = encode(timed, spans)
    value = payload(positive=True)
    value["evidence"] = [
        {
            "evidence_id": f"E{i}",
            "start_ms": span.evidence.start_ms,
            "end_ms": span.evidence.end_ms,
            "stance": "supporting",
        }
        for i, span in enumerate(spans[:count], 1)
    ]
    if count > 20:
        with pytest.raises(ValueError):
            decode_output(wire(value), packet)
    else:
        assert (
            len(decode_output(wire(value), packet).decoded_value["evidence"]) == count
        )


def test_decoded_output_expansion_has_its_own_byte_bound(monkeypatch):
    timed, spans = fixture()
    spans = tuple(
        replace(s, evidence=replace(s.evidence, evidence_id=f"{i}-" + "x" * 500))
        for i, s in enumerate(spans)
    )
    packet = encode(timed, spans)
    raw = wire(payload())
    decoded = decode_output(raw, packet)
    assert len(decoded.decoded_wire) > len(raw)
    monkeypatch.setattr(codec, "MAX_OUTPUT_BYTES", len(decoded.decoded_wire) - 1)
    with pytest.raises(ValueError, match="expanded output"):
        decode_output(raw, packet)


@pytest.mark.parametrize(
    "value", [None, True, "", "f" * 63, "g" * 64, "A" * 64, "\ud800"]
)
def test_source_hash_types_spelling_length_and_utf8_are_strict(value):
    timed, spans = fixture()
    for field in ("source_content_hash", "canonical_text_hash"):
        values = dict(
            source_id="source-a",
            content_provider="YOUTUBE",
            source_content_hash="a" * 64,
            canonical_text_hash="b" * 64,
            transcript=timed,
            evidence=spans,
        )
        with pytest.raises(ValueError):
            encode_grounding(**{**values, field: value})


@pytest.mark.parametrize("positive", [False, True])
def test_reference_extra_fields_missing_fields_and_nonobject_rejected(positive):
    for invalid in (None, [], "E1", 0, {"evidence_id": "E1"}):
        value = payload(positive=positive)
        value["evidence"][0] = invalid
        with pytest.raises(ValueError):
            decode_output(wire(value), encode())
    value = payload(positive=positive)
    value["evidence"][0]["excerpt"] = "unapproved"
    with pytest.raises(ValueError):
        decode_output(wire(value), encode())


def test_positive_subset_order_and_all_stances_prose_are_preserved_verbatim():
    timed, spans = fixture(("first", "second", "third"), (1, 2, 3))
    value = payload(positive=True)
    value["evidence"] = [
        {
            "evidence_id": f"E{i}",
            "start_ms": spans[i - 1].evidence.start_ms,
            "end_ms": spans[i - 1].evidence.end_ms,
            "stance": stance,
        }
        for i, stance in ((3, "contradicting"), (1, "supporting"), (2, "conditional"))
    ]
    expected = json.loads(wire(value))
    for ref, i in zip(expected["evidence"], (2, 0, 1)):
        ref["evidence_id"] = spans[i].evidence.evidence_id
    result = decode_output(wire(value), encode(timed, spans))
    assert result.decoded_value == expected
    value["evidence"] = [value["evidence"][1]]
    assert (
        len(decode_output(wire(value), encode(timed, spans)).decoded_value["evidence"])
        == 1
    )


def test_codec_version_is_hashed_in_unique_canonical_packet():
    packet = encode()
    value = json.loads(packet.canonical_wire)
    assert value["codec_version"] == "long-grounding-lossless-timed-v1"
    assert packet.canonical_wire == json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert packet.input_hash == hashlib.sha256(packet.canonical_wire).hexdigest()
