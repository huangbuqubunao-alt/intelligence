"""Explicit identities and stable, safe Diff machine errors."""

import json

import pytest
from conftest import _load_module

from youtube_intel.local_api import ApiError

support = _load_module("test_research_api")


def fixture(tmp_path):
    app = support.app(tmp_path)
    body = json.dumps({"question": "sentence1", "content_ids": [support.authority.VIDEO]}).encode()
    a, b = [app.handle("POST", "/api/v1/research", body)[1]["research"] for _ in range(2)]
    path = f'/api/v1/research/{a["packet"]["research_id"]}/diff'
    return app, path, a["result_identity"], b["result_identity"]


def test_explicit_diff_api_and_reverse_direction(tmp_path):
    app, path, a, b = fixture(tmp_path)
    for base, target in [(a, b), (b, a), (a, a)]:
        status, response = app.handle("GET", f"{path}?base_revision={base}&target_revision={target}")
        assert status == 200
        diff = response["diff"]
        assert diff["base"]["revision_id"] == base
        assert diff["target"]["revision_id"] == target
        assert diff["contract"] == "research-diff-v1" and diff["no_material_changes"]
        assert "payload_json" not in json.dumps(response)


@pytest.mark.parametrize("query", ["", "?base_revision=", "?base_revision=a&target_revision=b", "?base_revision={a}&target_revision={b}&target_revision={b}", "?base_revision={a}&target_revision={b}&current=true", "?base_revision=%27%3BDROP+TABLE+research_items&target_revision={b}"])
def test_malformed_or_ambiguous_diff_request_is_rejected(tmp_path, query):
    app, path, a, b = fixture(tmp_path)
    with pytest.raises(ApiError) as rejected:
        app.handle("GET", path + query.format(a=a, b=b))
    assert rejected.value.code == "RESEARCH_DIFF_INVALID_REQUEST"
    assert rejected.value.status == 422


@pytest.mark.parametrize("side", ["base", "target"])
def test_missing_revision_has_specific_error(tmp_path, side):
    app, path, a, b = fixture(tmp_path)
    base, target = ("f" * 64, b) if side == "base" else (a, "f" * 64)
    with pytest.raises(ApiError) as rejected:
        app.handle("GET", f"{path}?base_revision={base}&target_revision={target}")
    assert rejected.value.code == f"RESEARCH_DIFF_{side.upper()}_NOT_FOUND"
    assert rejected.value.status == 404


@pytest.mark.parametrize("side", ["base", "target"])
def test_api_rejects_cross_item_and_corrupt_authority(tmp_path, side):
    app, path, a, b = fixture(tmp_path)
    body = json.dumps({"question": "different question", "content_ids": [support.authority.VIDEO]}).encode()
    other = app.handle("POST", "/api/v1/research", body)[1]["research"]["result_identity"]
    base, target = (other, b) if side == "base" else (a, other)
    with pytest.raises(ApiError) as rejected:
        app.handle("GET", f"{path}?base_revision={base}&target_revision={target}")
    assert rejected.value.code == "RESEARCH_DIFF_WRONG_RESEARCH" and rejected.value.status == 409
    import sqlite3
    with sqlite3.connect(tmp_path / "state.sqlite3") as db:
        db.execute("DROP TRIGGER research_results_immutable_update")
        db.execute("UPDATE research_results SET payload_json='{}' WHERE result_identity=?", (a if side == "base" else b,))
    with pytest.raises(ApiError) as rejected:
        app.handle("GET", f"{path}?base_revision={a}&target_revision={b}")
    assert rejected.value.code == "RESEARCH_DIFF_UNTRUSTED_REVISION" and rejected.value.status == 409


def test_missing_research_is_distinct(tmp_path):
    app, _, a, b = fixture(tmp_path)
    with pytest.raises(ApiError) as rejected:
        app.handle("GET", f"/api/v1/research/{'f' * 64}/diff?base_revision={a}&target_revision={b}")
    assert rejected.value.code == "RESEARCH_NOT_FOUND" and rejected.value.status == 404
