"""Synthetic request freezes only: zero model/tokenizer/network qualification."""

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, asdict, replace

import pytest
from conftest import _load_module

from youtube_intel import long_distillation_profile as long
from youtube_intel.distillation import bind_local_profile, local_profile_for_scope
from youtube_intel.local_distillation_profile import (
    PROFILE_ID,
    canonical,
    resolve_profile,
)
from youtube_intel.long_card_canonical import canonicalize_long_card
from youtube_intel.long_grounding_codec import decode_output, encode_grounding
from youtube_intel.long_grounding_projection import prepare_long_projection

codec_cases = _load_module("test_long_grounding_codec")
projection_cases = _load_module("test_long_grounding_projection")
SNAPSHOTS = dict(
    source_snapshot=b' {"source":"all source fields","unknown":[true,null,1]} ',
    summary_snapshot=b'{"summary":{"all":[1,2,3]}}',
    policy_snapshot=b'{"policy":"all policy fields"}',
)


def fixture(count=2, cue_count=None):
    """Reuse accepted synthetic codec construction; never a real QA/holdout."""
    cue_count = cue_count or count
    texts = tuple("  é e\u0301 😀\t" if i % 3 else "same" for i in range(cue_count))
    cuts = tuple((i + 1) * cue_count // count for i in range(count))
    timed, spans = codec_cases.fixture(texts, cuts)
    packet = encode_grounding(
        source_id="source-a",
        content_provider="YOUTUBE",
        source_content_hash="a" * 64,
        canonical_text_hash="b" * 64,
        transcript=timed,
        evidence=spans,
    )
    _, value = projection_cases.fixture()
    from youtube_intel.distillation import VerifiedEvidenceInput

    value = replace(
        value,
        video_id=timed.video_id,
        evidence=tuple(
            VerifiedEvidenceInput(
                **{k: v for k, v in asdict(s.evidence).items() if k != "video_id"}
            )
            for s in spans
        ),
    )
    return packet, bind_local_profile(value, PROFILE_ID)


def prepare(packet=None, value=None, **snapshots):
    if packet is None:
        packet, value = fixture()
    return long.prepare_long_request(packet, value, **{**SNAPSHOTS, **snapshots})


def output(packet, positive=False, count=None):
    refs = [
        dict(evidence_id=r["alias"], start_ms=r["start_ms"], end_ms=r["end_ms"])
        for r in json.loads(packet.canonical_wire)["evidence"]
    ]
    if count is not None:
        refs = refs[:count]
    if not positive:
        return dict(result="NO_NEW_INTELLIGENCE", evidence=refs)
    payload = codec_cases.payload(positive=True)
    payload["evidence"] = [dict(r, stance="supporting") for r in refs]
    return payload


def matches(schema, value):
    """Independent small JSON Schema oracle for the emitted standard subset."""
    if "anyOf" in schema and not any(matches(s, value) for s in schema["anyOf"]):
        return False
    if "enum" in schema and not any(
        type(value) is type(x) and value == x for x in schema["enum"]
    ):
        return False
    kind = schema.get("type")
    expected = {"object": dict, "array": list, "string": str, "integer": int}
    if kind and type(value) is not expected[kind]:
        return False
    if kind == "object":
        if set(schema.get("required", [])) - value.keys():
            return False
        if (
            schema.get("additionalProperties") is False
            and value.keys() - schema["properties"].keys()
        ):
            return False
        return all(matches(schema["properties"][k], v) for k, v in value.items())
    if kind == "array":
        return schema.get("minItems", 0) <= len(value) <= schema.get(
            "maxItems", float("inf")
        ) and all(matches(schema["items"], v) for v in value)
    if kind == "string":
        return (
            schema.get("minLength", 0)
            <= len(value)
            <= schema.get("maxLength", float("inf"))
        )
    return True


def test_reproducible_complete_native_request_and_separate_identities():
    packet, value = fixture()
    before = asdict(value)
    prepared = prepare(packet, value)
    assert prepare(packet, value) == prepared
    request = prepared.request()
    profile = long.resolve_long_profile(long.PROFILE_ID)
    assert profile.profile_id == "local-grounding-qwen35-9b-lossless-rle-thinking-v1"
    assert prepared.profile_hash == profile.profile_hash
    assert set(request) == {
        "model",
        "messages",
        "format",
        "stream",
        "think",
        "options",
        "truncate",
        "shift",
    }
    assert request["model"] == resolve_profile(PROFILE_ID).model
    assert request["stream"] is False and request["think"] is True
    assert request["truncate"] is False and request["shift"] is False
    assert request["options"] == {
        **resolve_profile(PROFILE_ID).options(),
        "num_ctx": 32768,
    }
    actual = prepare_long_projection(packet, value, **SNAPSHOTS)
    assert prepared.projection == actual
    assert canonical(request["messages"]) == actual.messages_wire
    assert prepared.request_wire == canonical(request)
    assert prepared.request_hash == hashlib.sha256(prepared.request_wire).hexdigest()
    assert (
        prepared.schema_hash == hashlib.sha256(canonical(request["format"])).hexdigest()
    )
    assert prepared.source_semantic_hash == value.semantic_hash
    assert prepared.source_profile_id == PROFILE_ID
    assert prepared.source_profile_hash == value.local_profile_hash
    assert asdict(value) == before
    assert json.loads(actual.semantic_snapshot_wire)["value"] == json.loads(
        json.dumps(before)
    )
    descriptor = json.loads(profile.profile_wire)
    assert descriptor["model_digest"] == resolve_profile(PROFILE_ID).model_digest
    assert descriptor["runtime"] == "0.40.1" and descriptor["timeout_seconds"] == 300
    assert descriptor["capacity_status"] == "UNVERIFIED_CANDIDATE"
    assert descriptor["max_request_bytes"] == 8_000_000
    with pytest.raises(FrozenInstanceError):
        prepared.request_wire = b"{}"


def test_complete_114_evidence_2406_cues_preserve_every_byte_and_context_field():
    packet, value = fixture(114, 2406)
    result = prepare(packet, value)
    context = json.loads(result.projection.model_context_wire)
    rows = json.loads(packet.canonical_wire)["evidence"]
    assert len(context) == 9 and len(context["evidence"]) == 114
    assert sum(len(run["cues"]) for r in rows for run in r["runs"]) == 2406
    for i, (row, item) in enumerate(zip(context["evidence"], value.evidence), 1):
        assert row["evidence_id"] == f"E{i}"
        assert (
            "\n".join(r["text"] for r in row["runs"] for _ in range(r["repeat"]))
            == item.excerpt
        )
    assert result.projection.codec_input_hash == packet.input_hash
    side = json.loads(result.projection.semantic_snapshot_wire)
    for name, raw in SNAPSHOTS.items():
        saved = side["snapshots"][name.removesuffix("_snapshot")]
        assert saved == dict(wire=raw.decode(), hash=hashlib.sha256(raw).hexdigest())
    assert matches(result.request()["format"], output(packet))


@pytest.mark.parametrize("count", [1, 20, 21, 4102])
def test_reference_cardinality_alias_ranges_and_accepted_codec(count):
    packet, value = fixture(count)
    prepared = prepare(packet, value)
    schema = prepared.request()["format"]
    zero = output(packet)
    assert matches(schema, zero)
    decoded = decode_output(canonical(zero), packet)
    assert [r["evidence_id"] for r in decoded.decoded_value["evidence"]] == [
        e.evidence_id for e in value.evidence
    ]
    positive = output(packet, positive=True, count=min(count, 20))
    assert matches(schema, positive)
    assert canonicalize_long_card(
        decode_output(canonical(positive), packet).decoded_wire
    ).content_hash
    if count > 20:
        excessive = output(packet, positive=True, count=21)
        assert not matches(schema, excessive)
        with pytest.raises(ValueError):
            decode_output(canonical(excessive), packet)
    assert len(prepared.request_wire) <= long.MAX_REQUEST_BYTES


@pytest.mark.parametrize(
    "attack",
    ["unknown", "duplicate", "reorder", "range", "bool", "extra", "prose", "missing"],
)
def test_strict_schema_and_codec_reject_inconsistent_reference_or_zero_shape(attack):
    packet, value = fixture(21)
    schema = prepare(packet, value).request()["format"]
    payload = output(packet)
    if attack == "unknown":
        payload["evidence"][0]["evidence_id"] = "E22"
    elif attack == "duplicate":
        payload["evidence"][1] = payload["evidence"][0].copy()
    elif attack == "reorder":
        payload["evidence"].reverse()
    elif attack == "range":
        payload["evidence"][0]["end_ms"] += 1
    elif attack == "bool":
        payload["evidence"][0]["start_ms"] = False
    elif attack == "extra":
        payload["wire_version"] = "invented"
    elif attack == "prose":
        payload["core_conclusion"] = "not allowed"
    else:
        payload["evidence"].pop()
    if attack not in {"duplicate", "reorder"}:
        assert not matches(schema, payload)
    with pytest.raises(ValueError):
        decode_output(canonical(payload), packet)


def test_caller_mutation_cannot_change_profile_schema_or_subsequent_requests():
    packet, value = fixture()
    prepared = prepare(packet, value)
    original = prepared.request_wire
    original_profile = long.resolve_long_profile(long.PROFILE_ID).profile_wire
    request = prepared.request()
    request["options"]["num_ctx"] = 1
    request["format"]["anyOf"][0]["properties"]["core_conclusion"]["type"] = "integer"
    request["messages"][0]["content"] = "changed"
    assert (
        prepared.request_wire == original
        and prepare(packet, value).request_wire == original
    )
    assert long.resolve_long_profile(long.PROFILE_ID).profile_wire == original_profile
    object.__setattr__(value, "video_title", "later")
    assert prepared.request_wire == original


def test_original_schema_and_profile_goldens_unchanged_and_candidate_unregistered():
    original = copy.deepcopy(local_profile_for_scope(PROFILE_ID, "YT_TIMED"))
    prepare()
    assert local_profile_for_scope(PROFILE_ID, "YT_TIMED") == original
    assert resolve_profile(PROFILE_ID).options()["num_ctx"] == 16384
    with pytest.raises(ValueError):
        resolve_profile(long.PROFILE_ID)
    with pytest.raises(ValueError):
        long.resolve_long_profile(PROFILE_ID)


@pytest.mark.parametrize(
    "wire",
    [
        None,
        bytearray(b'{"x":1}'),
        b"",
        b"\xff",
        b'{"x":NaN}',
        b'{"x":1e999}',
        b'{"x":"\\ud800"}',
        b'{"x":1,"x":2}',
        b'{"x":' + b"[" * 10000 + b"0" + b"]" * 10000 + b"}",
        b'{"x":"' + b"x" * 1_000_000 + b'"}',
    ],
)
def test_invalid_snapshot_types_encoding_finiteness_depth_and_size_reject(wire):
    with pytest.raises(ValueError):
        prepare(summary_snapshot=wire)


@pytest.mark.parametrize(
    "field,invalid",
    [
        ("selected_model", "foreign"),
        ("selected_model", True),
        ("source_display_name", float("nan")),
        ("video_title", "\ud800"),
        ("personalization", ["mutable"]),
        ("semantic_hash", False),
    ],
)
def test_malicious_typed_input_rejected_without_resealing(field, invalid):
    packet, value = fixture()
    with pytest.raises(ValueError):
        prepare(packet, replace(value, **{field: invalid}))


def test_arbitrary_projection_or_packet_is_never_trusted():
    packet, value = fixture()
    projection = prepare_long_projection(packet, value, **SNAPSHOTS)
    for invalid in (
        projection,
        {},
        bytearray(packet.canonical_wire),
        replace(packet, canonical_wire=b"{}"),
    ):
        with pytest.raises(ValueError):
            prepare(invalid, value)


def test_semantic_side_changes_bind_freeze_without_changing_native_model_input():
    packet, value = fixture()
    original = prepare(packet, value)
    changed = prepare(
        packet,
        replace(value, semantic_hash="d" * 64),
        policy_snapshot=b'{"policy":"changed"}',
    )
    assert original.request_hash == changed.request_hash
    assert original.freeze_hash != changed.freeze_hash
    assert (
        original.projection.semantic_snapshot_hash
        != changed.projection.semantic_snapshot_hash
    )
    assert original.profile_hash == changed.profile_hash


def test_complete_request_bound_explicitly_rejects_without_returning_partial(
    monkeypatch,
):
    monkeypatch.setattr(long, "MAX_REQUEST_BYTES", 1)
    with pytest.raises(ValueError, match="request.*byte bound"):
        prepare()


def test_fixed_profile_request_schema_and_full_freeze_goldens():
    result = prepare()
    assert (
        result.profile_hash
        == "2fb51df81b7962b9f831e70720985656220e3be8d32dc92fb15ee755a6ef1a82"
    )
    assert (
        result.request_hash
        == "67e41a75862ad5df8c2a8404e240a7ea7f687d32aaeb5685d0053064df4c254f"
    )
    assert (
        result.schema_hash
        == "28b9b6292651ad89a29bae264948ef2939f7b8a53fb10ce996b2b2cbf31b87fc"
    )
    assert (
        result.freeze_hash
        == "d789559bb01f94895ab16460cb13887e4f0d4ac26ccad7063a63e2c2803108c8"
    )


def test_real_eight_million_byte_request_accepts_and_next_value_rejects():
    packet, value = fixture(4102)
    # Escaping quotes in model JSON and then message JSON makes each quote four
    # request bytes. Reach the real guard without changing any limit.
    at_limit = replace(value, personalization=('"' * 1_304_062,))
    result = prepare(packet, at_limit)
    assert len(result.request_wire) == 8_000_000
    assert len(result.projection.messages_wire) == 5_691_679
    assert result.request()["options"]["num_ctx"] == 32768
    with pytest.raises(ValueError, match="complete request byte bound"):
        prepare(packet, replace(value, personalization=('"' * 1_304_063,)))


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("video_title", "different title"),
        ("source_display_name", None),
        ("personalization", ("interest2",)),
        ("source_focus_rules", ("focus2",)),
        ("source_ignore_rules", ("ignore2",)),
        ("distillation_style", None),
        ("output_language", "zh-CN"),
    ],
)
def test_every_model_context_change_changes_native_request_and_full_freeze(
    field, replacement
):
    packet, value = fixture()
    original = prepare(packet, value)
    changed = prepare(packet, replace(value, **{field: replacement}))
    assert original.request_hash != changed.request_hash
    assert original.freeze_hash != changed.freeze_hash
    assert original.profile_hash == changed.profile_hash


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("local_profile_id", "retained-source-profile"),
        ("local_profile_hash", "d" * 64),
        ("local_content_context_hash", "e" * 64),
        ("input_json", '{"all":1}'),
        ("context_json", '{"all":2}'),
    ],
)
def test_all_original_non_model_semantic_fields_remain_side_bound(field, replacement):
    packet, value = fixture()
    original = prepare(packet, value)
    changed = prepare(packet, replace(value, **{field: replacement}))
    assert original.request_hash == changed.request_hash
    assert original.freeze_hash != changed.freeze_hash
    assert (
        json.loads(changed.projection.semantic_snapshot_wire)["value"][field]
        == replacement
    )


@pytest.mark.parametrize("name", list(SNAPSHOTS))
def test_each_complete_snapshot_changes_only_semantic_freeze(name):
    original = prepare()
    raw = b' \n{"all":{"unknown":[null,false,1.25,"e\\u0301"]}}  '
    changed = prepare(**{name: raw})
    assert original.request_hash == changed.request_hash
    assert original.freeze_hash != changed.freeze_hash
    assert (
        json.loads(changed.projection.semantic_snapshot_wire)["snapshots"][
            name.removesuffix("_snapshot")
        ]["wire"].encode()
        == raw
    )


def test_preflight_bounds_before_projection_or_decode(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("projection must not run on unsafe bounded input")

    packet, value = fixture()
    monkeypatch.setattr(long.projection, "prepare_long_projection", forbidden)
    for invalid in (b"{" * 100_000, b"x" * 1_000_001, bytearray(b'{"x":1}')):
        with pytest.raises(ValueError):
            prepare(packet, value, source_snapshot=invalid)


def test_max_snapshot_bytes_depth_escaped_quotes_and_brackets_preserve_exactly():
    raw = b'{"x":"' + b"x" * (1_000_000 - 8) + b'"}'
    result = prepare(summary_snapshot=raw)
    assert (
        json.loads(result.projection.semantic_snapshot_wire)["snapshots"]["summary"][
            "wire"
        ].encode()
        == raw
    )
    at_depth = b'{"x":' + b"[" * 15 + b"0" + b"]" * 15 + b"}"
    prepare(summary_snapshot=at_depth)
    quoted = canonical({"x": '"\\' + "[{" * 100})
    assert (
        json.loads(prepare(policy_snapshot=quoted).projection.semantic_snapshot_wire)[
            "snapshots"
        ]["policy"]["wire"].encode()
        == quoted
    )


def test_builder_has_no_io_or_registry_and_never_grants_capacity(monkeypatch):
    import sqlite3
    import urllib.request

    def forbidden(*args, **kwargs):
        raise AssertionError("pure request preparation attempted IO")

    monkeypatch.setattr(sqlite3, "connect", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    prepared = prepare()
    for obj in (prepared, long.resolve_long_profile(long.PROFILE_ID)):
        for name in (
            "generate",
            "dispatch",
            "qualified",
            "complete_input_token_upper_bound",
            "permit",
        ):
            assert not hasattr(obj, name)


def test_legacy_shared_schema_mutation_after_freeze_cannot_change_new_requests(
    monkeypatch,
):
    from youtube_intel.distillation import OllamaLocalDistillationTransport

    packet, value = fixture()
    original = prepare(packet, value)
    changed = copy.deepcopy(OllamaLocalDistillationTransport._SCHEMA)
    changed["anyOf"][0]["properties"]["claim_kind"]["enum"] = ["invented"]
    monkeypatch.setattr(OllamaLocalDistillationTransport, "_SCHEMA", changed)
    assert prepare(packet, value) == original


@pytest.mark.parametrize(
    "attack",
    [
        "classification",
        "stance",
        "no-support",
        "extra",
        "core-long",
        "text-long",
        "text-count",
        "whitespace",
    ],
)
def test_positive_claim_semantics_and_shape_keep_original_codec_standard(attack):
    packet, value = fixture()
    payload = output(packet, positive=True)
    if attack == "classification":
        payload["claim_kind"] = "UNCLASSIFIED"
    elif attack == "stance":
        payload["evidence"][0]["stance"] = "unknown"
    elif attack == "no-support":
        for ref in payload["evidence"]:
            ref["stance"] = "conditional"
    elif attack == "extra":
        payload["wire_version"] = "invented"
    elif attack == "core-long":
        payload["core_conclusion"] = "x" * 4001
    elif attack == "text-long":
        payload["meaningful_details"] = ["x" * 2001]
    elif attack == "text-count":
        payload["meaningful_details"] = ["x"] * 21
    else:
        payload["core_conclusion"] = " padded "
    if attack not in {"no-support", "whitespace"}:
        assert not matches(prepare(packet, value).request()["format"], payload)
    with pytest.raises(ValueError):
        decode_output(canonical(payload), packet)
