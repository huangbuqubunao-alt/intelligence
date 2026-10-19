"""Synthetic historical-card parity; no production admission or real data."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from youtube_intel import long_card_canonical as canonical

TEXT_LISTS = (
    "user_relevant_information",
    "important_new_information",
    "meaningful_details",
    "filtered_noise",
)


def payload():
    return {
        "result": "INTELLIGENCE",
        "core_conclusion": '原文 e\u0301 é 😀\nquoted "\\ text',
        "user_relevant_information": ["A source opinion; uncertain."],
        "important_new_information": [],
        "meaningful_details": ["one\ttwo\u0000three"],
        "filtered_noise": [],
        "claim_kind": "OPINION",
        "evidence": [
            {"evidence_id": "证据-z/\n😀", "start_ms": 10, "end_ms": 20,
             "stance": "supporting"},
            {"evidence_id": " evidence-A\\\" ", "start_ms": 0, "end_ms": 9,
             "stance": "conditional"},
        ],
    }


def wire(value):
    return json.dumps(value, ensure_ascii=False).encode()


def historical_parser(value):
    # Invoke the real persistence oracle with a minimal in-memory repository.
    from youtube_intel.distillation import (
        OllamaLocalDistillationTransport,
        PersonalizedDistillationService,
    )

    refs = {r["evidence_id"]: r for r in value["evidence"]}
    repository = SimpleNamespace(get_evidence=lambda eid: SimpleNamespace(
        video_id="synthetic", start_ms=refs[eid]["start_ms"],
        end_ms=refs[eid]["end_ms"],
    ))
    service = PersonalizedDistillationService.__new__(PersonalizedDistillationService)
    service._repository = repository
    service._local_profile_id = None
    command = SimpleNamespace(
        source_id="source", video_id="synthetic", preference_ids=(),
        source_policy_revision_id=None, selected_provider="ollama",
        selected_model=OllamaLocalDistillationTransport._MODEL,
    )
    verified = SimpleNamespace(
        wire_version=None, local_profile_id=None, selected_provider="ollama",
        selected_model=command.selected_model, evidence_ids=tuple(refs),
    )
    return service._parse_candidate(wire(value).decode(), command, verified)


def test_exact_existing_parser_bytes_hash_and_original_id_order():
    value = payload()
    result = canonical.canonicalize_long_card(wire(value))
    old = historical_parser(value)
    assert result.canonical_content == old.canonical_content
    assert result.content_hash == hashlib.sha256(old.canonical_content).hexdigest()
    projected = json.loads(result.canonical_content)
    assert "result" not in projected
    assert projected["evidence"] == sorted(value["evidence"], key=lambda r: r["evidence_id"])
    assert projected == {**{k: v for k, v in value.items() if k != "result"},
                         "evidence": projected["evidence"]}
    assert result.canonical_content.isascii()
    assert b"\\ud83d\\ude00" in result.canonical_content
    with pytest.raises(FrozenInstanceError):
        result.canonical_content = b"changed"


def test_mapping_and_positive_reference_order_do_not_change_hash_but_text_order_does():
    value = payload()
    expected = canonical.canonicalize_long_card(wire(value))
    value = dict(reversed(list(value.items())))
    value["evidence"] = [dict(reversed(list(r.items()))) for r in value["evidence"][::-1]]
    assert canonical.canonicalize_long_card(wire(value)) == expected
    value["core_conclusion"] = value["core_conclusion"].replace("e\u0301", "é")
    assert canonical.canonicalize_long_card(wire(value)).content_hash != expected.content_hash
    value = payload()
    value["meaningful_details"] = ["first", "second"]
    first = canonical.canonicalize_long_card(wire(value))
    value["meaningful_details"].reverse()
    assert canonical.canonicalize_long_card(wire(value)).content_hash != first.content_hash


def test_decoded_wire_remains_distinct_and_all_card_fields_bind_identity():
    value = payload()
    decoded_wire = wire(value)
    result = canonical.canonicalize_long_card(decoded_wire)
    assert result.content_hash != hashlib.sha256(decoded_wire).hexdigest()
    for field in ("core_conclusion", *TEXT_LISTS):
        changed = payload()
        changed[field] = "changed" if field == "core_conclusion" else ["changed"]
        assert canonical.canonicalize_long_card(wire(changed)).content_hash != result.content_hash
    for field, replacement in (("evidence_id", "different"), ("start_ms", 11),
                               ("end_ms", 21), ("stance", "contradicting")):
        changed = payload()
        changed["evidence"][1][field] = replacement
        if field == "start_ms":
            changed["evidence"][1]["end_ms"] = 30
        assert canonical.canonicalize_long_card(wire(changed)).content_hash != result.content_hash
    changed = payload()
    changed["claim_kind"] = "PREDICTION"
    assert canonical.canonicalize_long_card(wire(changed)).content_hash != result.content_hash
    assert decoded_wire == wire(payload())


@pytest.mark.parametrize("bad", [None, True, 1, 1.0, "{}", {}, [], bytearray(b"{}"), memoryview(b"{}")])
def test_only_exact_immutable_bytes_are_accepted(bad):
    with pytest.raises(ValueError):
        canonical.canonicalize_long_card(bad)


def test_cycles_and_unsupported_objects_are_rejected_at_wire_boundary():
    cycle = []
    cycle.append(cycle)
    for value in (cycle, object(), {"x": {1, 2}}):
        with pytest.raises(ValueError):
            canonical.canonicalize_long_card(value)


@pytest.mark.parametrize("bad", [b"", b"{}", b"[]", b"null", b"true", b"1", b"1.2",
                                 b"not JSON", b"{} {}", b"\xff", b"\xef\xbb\xbf{}",
                                 b'{"result":"INTELLIGENCE","result":"INTELLIGENCE"}',
                                 b"[" * 2000 + b"0" + b"]" * 2000])
def test_malformed_or_wrong_branch_wire_rejected(bad):
    with pytest.raises(ValueError):
        canonical.canonicalize_long_card(bad)


@pytest.mark.parametrize("fragment", [b"NaN", b"Infinity", b"-Infinity", b"1e999", b"true", b"1.0", b"null", b'"1"'])
def test_unsupported_numbers_rejected(fragment):
    raw = wire(payload()).replace(b'"start_ms": 10', b'"start_ms": ' + fragment)
    with pytest.raises(ValueError):
        canonical.canonicalize_long_card(raw)


def test_duplicate_keys_at_each_object_and_invalid_unicode_rejected():
    raw = wire(payload())
    duplicate = [raw.replace(b'"result":', b'"result":"INTELLIGENCE","result":', 1),
                 raw.replace(b'"start_ms":', b'"start_ms":10,"start_ms":', 1)]
    for bad in duplicate + [json.dumps({**payload(), "core_conclusion": "\ud800"}).encode(),
                            raw.replace(b'"evidence_id":', b'"\\ud800":0,"evidence_id":', 1)]:
        with pytest.raises(ValueError):
            canonical.canonicalize_long_card(bad)


@pytest.mark.parametrize("field", ["result", "core_conclusion", "claim_kind", "evidence", *TEXT_LISTS])
def test_missing_fields_rejected(field):
    value = payload()
    del value[field]
    with pytest.raises(ValueError):
        canonical.canonicalize_long_card(wire(value))


@pytest.mark.parametrize("change", [
    {"extra": "no"}, {"source_id": "cannot invent provenance"},
    {"wire_version": "local-text-v1"}, {"result": "NO_NEW_INTELLIGENCE"},
    {"result": True}, {"claim_kind": "UNCLASSIFIED"}, {"claim_kind": []},
    {"core_conclusion": " leading"}, {"core_conclusion": "trailing "},
    {"core_conclusion": "  "}, {"core_conclusion": ""}, {"core_conclusion": None},
    {"evidence": []}, {"evidence": {}}, {"meaningful_details": "wrong"},
    {"meaningful_details": [False]}, {"meaningful_details": [""]},
    {"meaningful_details": [" a"]},
])
def test_wrong_card_shape_rejected(change):
    with pytest.raises(ValueError):
        canonical.canonicalize_long_card(wire({**payload(), **change}))


@pytest.mark.parametrize("change", [
    {"extra": 1}, {"evidence_id": ""}, {"evidence_id": 1},
    {"stance": "unknown"}, {"stance": []}, {"start_ms": -1},
    {"end_ms": 10}, {"end_ms": 9}, {"start_ms": True}, {"end_ms": False},
    {"start_ms": 0.0}, {"end_ms": None}, {"end_ms": 2**63},
])
def test_wrong_reference_shape_rejected(change):
    value = payload()
    value["evidence"][0].update(change)
    with pytest.raises(ValueError):
        canonical.canonicalize_long_card(wire(value))


def test_duplicate_references_missing_fields_and_no_support_rejected():
    for kind in ("duplicate", "missing", "no-support"):
        value = payload()
        if kind == "duplicate":
            value["evidence"].append(dict(value["evidence"][0]))
        elif kind == "missing":
            del value["evidence"][0]["stance"]
        else:
            value["evidence"][0]["stance"] = "contradicting"
        with pytest.raises(ValueError):
            canonical.canonicalize_long_card(wire(value))


@pytest.mark.parametrize("field,maximum", [("core_conclusion", 4000), *[(f, 2000) for f in TEXT_LISTS]])
def test_prose_real_character_maximum_and_plus_one(field, maximum):
    value = payload()
    value[field] = "😀" * maximum if field == "core_conclusion" else ["😀" * maximum]
    canonical.canonicalize_long_card(wire(value))
    value[field] = "😀" * (maximum + 1) if field == "core_conclusion" else ["😀" * (maximum + 1)]
    with pytest.raises(ValueError):
        canonical.canonicalize_long_card(wire(value))


@pytest.mark.parametrize("field", TEXT_LISTS)
def test_text_list_real_maximum_and_plus_one(field):
    value = payload()
    value[field] = ["same"] * 20
    assert json.loads(canonical.canonicalize_long_card(wire(value)).canonical_content)[field] == ["same"] * 20
    value[field].append("extra")
    with pytest.raises(ValueError):
        canonical.canonicalize_long_card(wire(value))


def test_evidence_real_maximum_id_maximum_and_plus_one_and_integer_endpoints():
    value = payload()
    value["evidence"] = [
        {"evidence_id": chr(0x10000 + i) * 512, "start_ms": 2**63 - 2,
         "end_ms": 2**63 - 1, "stance": "supporting"} for i in range(20)
    ]
    assert len(json.loads(canonical.canonicalize_long_card(wire(value)).canonical_content)["evidence"]) == 20
    value["evidence"].append({**value["evidence"][0], "evidence_id": "extra"})
    with pytest.raises(ValueError):
        canonical.canonicalize_long_card(wire(value))
    value["evidence"].pop()
    value["evidence"][0]["evidence_id"] += "a"
    with pytest.raises(ValueError):
        canonical.canonicalize_long_card(wire(value))


def test_real_wire_byte_maximum_plus_one_without_patching_limits():
    raw = wire(payload())
    maximum = raw + b" " * (canonical.MAX_INPUT_BYTES - len(raw))
    assert len(maximum) == 1_000_000
    assert canonical.canonicalize_long_card(maximum) == canonical.canonicalize_long_card(raw)
    with pytest.raises(ValueError):
        canonical.canonicalize_long_card(maximum + b" ")


def test_complete_schema_maximum_ascii_expansion_is_accepted():
    value = payload()
    value["core_conclusion"] = "😀" * 4000
    for field in TEXT_LISTS:
        value[field] = ["😀" * 2000] * 20
    value["claim_kind"] = "EVIDENCE_BACKED_STATEMENT"
    value["evidence"] = [
        {"evidence_id": chr(0x10000 + i) * 512, "start_ms": 2**63 - 2,
         "end_ms": 2**63 - 1, "stance": "contradicting"} for i in range(20)
    ]
    value["evidence"][0]["stance"] = "supporting"
    result = canonical.canonicalize_long_card(wire(value))
    # Full maximum textual capacity: astral characters use 12 ASCII bytes.
    assert len(result.canonical_content) == 2_093_375
    assert len(result.canonical_content) > 2_000_000
    assert len(result.canonical_content) == len(historical_parser(value).canonical_content)
    assert result.canonical_content == historical_parser(value).canonical_content
    assert len(result.canonical_content) <= canonical.MAX_CANONICAL_BYTES == 3_000_000


def test_raw_del_ascii_escape_parity_uses_shape_bound_not_three_times_wire():
    value = payload()
    value["core_conclusion"] = "\x7f" * 4000
    for field in TEXT_LISTS:
        value[field] = ["\x7f" * 2000] * 20
    raw = wire(value)
    assert b"\x7f" in raw
    result = canonical.canonicalize_long_card(raw)
    assert result.canonical_content == historical_parser(value).canonical_content
    assert b"\\u007f" in result.canonical_content
    assert len(result.canonical_content) > 3 * len(raw)
    assert len(result.canonical_content) < canonical.MAX_CANONICAL_BYTES
