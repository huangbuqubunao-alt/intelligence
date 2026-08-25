"""TASK-016C Phase H2-A — H2 Canonical JSON v1 (RFC 8785 / JCS) serializer tests.

RED-first tests for the internal, dependency-free JCS serializer used only by the
new ``task016c-*`` H2 evidence/preimage objects.  These tests assert exact UTF-8
bytes for every normative number vector from RFC 8785 Section 3.2.2.3 / Appendix B
and verify key ordering, escaping, and rejection of non-canonical inputs.

Python ``json.dumps`` float formatting is explicitly NOT authoritative here.
"""

from __future__ import annotations

import math

import pytest

from youtube_intel.h2_jcs import (
    jcs_loads_strict,
    jcs_serialize,
    jcs_sha256,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, b"0"),
        (-0.0, b"0"),
        (1, b"1"),
        (-1, b"-1"),
        (1.5, b"1.5"),
        (1.5e-6, b"0.0000015"),
        (1e-6, b"0.000001"),
        (9.999999999999997e-7, b"9.999999999999997e-7"),
        (1e-7, b"1e-7"),
        (1e20, b"100000000000000000000"),
        (1e21, b"1e+21"),
        (-1e21, b"-1e+21"),
        (333333333.33333329, b"333333333.3333333"),
    ],
)
def test_normative_number_vectors_exact_bytes(value: object, expected: bytes) -> None:
    assert jcs_serialize(value) == expected


@pytest.mark.parametrize(
    "value",
    [math.nan, math.inf, -math.inf],
)
def test_non_finite_numbers_reject(value: float) -> None:
    with pytest.raises(ValueError):
        jcs_serialize(value)


def test_key_ordering_is_lexicographic_utf16() -> None:
    value = {"b": 1, "a": 2, "aa": 3, "B": 4}
    # UTF-16 code-unit order: 'B'(0x42) < 'a'(0x61) < 'aa' < 'b'(0x62)
    assert jcs_serialize(value) == b'{"B":4,"a":2,"aa":3,"b":1}'


def test_astral_key_orders_by_utf16_code_units() -> None:
    # U+10000 encodes as surrogate pair (0xD800,0xDC00); it must sort after
    # BMP code units in the 0xE000+ range only if code-unit order says so.
    # 0xD800 < 0xE000, so the astral key sorts BEFORE the U+E000 key.
    astral = "\U00010000"
    pua = "\ue000"
    value = {pua: 1, astral: 2}
    assert jcs_serialize(value) == ('{"' + astral + '":2,"' + pua + '":1}').encode(
        "utf-8"
    )


def test_no_insignificant_whitespace() -> None:
    assert jcs_serialize({"a": [1, 2], "b": {"c": True}}) == b'{"a":[1,2],"b":{"c":true}}'


def test_literals_lower_case() -> None:
    assert jcs_serialize({"t": True, "f": False, "n": None}) == b'{"f":false,"n":null,"t":true}'


def test_string_escaping_quote_and_backslash() -> None:
    # A lone double quote serializes to "\""  -> bytes: 22 5c 22 22
    assert jcs_serialize('"') == b'"\\""'
    # A lone backslash serializes to "\\"  -> bytes: 22 5c 5c 22
    assert jcs_serialize("\\") == b'"\\\\"'


def test_string_escaping_short_control_sequences() -> None:
    assert jcs_serialize("\u0008") == b'"\\b"'
    assert jcs_serialize("\u0009") == b'"\\t"'
    assert jcs_serialize("\u000a") == b'"\\n"'
    assert jcs_serialize("\u000c") == b'"\\f"'
    assert jcs_serialize("\u000d") == b'"\\r"'


def test_string_escaping_other_control_sequences_use_lowercase_unicode() -> None:
    assert jcs_serialize("\u0000") == b'"\\u0000"'
    assert jcs_serialize("\u001f") == b'"\\u001f"'
    assert jcs_serialize("\u0001") == b'"\\u0001"'


def test_string_escaping_never_escapes_solidus_and_passes_through_unicode() -> None:
    assert jcs_serialize("/") == b'"/"'
    assert jcs_serialize("a/b") == b'"a/b"'
    # Non-ASCII scalar values are emitted unescaped, encoded as strict UTF-8.
    assert jcs_serialize("é中") == b'"\xc3\xa9\xe4\xb8\xad"'


def test_arrays_retain_order() -> None:
    assert jcs_serialize([3, 1, 2]) == b"[3,1,2]"


def test_reject_non_json_types() -> None:
    with pytest.raises(ValueError):
        jcs_serialize({"a": object()})
    with pytest.raises(ValueError):
        jcs_serialize({"a": {1, 2}})


def test_reject_lone_surrogate_via_strict_utf8() -> None:
    with pytest.raises(ValueError):
        jcs_serialize("\ud800")


def test_loads_strict_rejects_duplicate_keys() -> None:
    with pytest.raises(ValueError):
        jcs_loads_strict(b'{"a":1,"a":2}')


def test_loads_strict_rejects_nan_and_infinity_tokens() -> None:
    for bad in (b"NaN", b"Infinity", b"-Infinity"):
        with pytest.raises(ValueError):
            jcs_loads_strict(b'{"x":' + bad + b"}")


def test_loads_strict_round_trips_canonical_object() -> None:
    sealed = b'{"a":[1,2],"b":"x","c":1.5}'
    assert jcs_serialize(jcs_loads_strict(sealed)) == sealed


def test_non_canonical_spelling_rejected_on_reserialize() -> None:
    # Semantically equivalent but non-canonical numeric spelling.
    non_canonical = b'{"a":1.50}'
    parsed = jcs_loads_strict(non_canonical)
    assert jcs_serialize(parsed) != non_canonical
    assert jcs_serialize(parsed) == b'{"a":1.5}'


def test_non_canonical_whitespace_rejected_on_reserialize() -> None:
    non_canonical = b'{"a": 2}'
    parsed = jcs_loads_strict(non_canonical)
    assert jcs_serialize(parsed) != non_canonical


def test_sha256_is_lowercase_hex_of_serialized_bytes() -> None:
    import hashlib

    value = {"schema_version": "task016c-x", "n": 1}
    expected = hashlib.sha256(jcs_serialize(value)).hexdigest()
    assert jcs_sha256(value) == expected
    assert jcs_sha256(value) == jcs_sha256({"n": 1, "schema_version": "task016c-x"})
