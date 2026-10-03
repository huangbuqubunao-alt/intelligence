"""Complete local API workflow and stable localized-client error codes."""

import json

import pytest
from conftest import _load_module

from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService

authority = _load_module("test_v1x_phase1b_authority")


def app(tmp_path):
    repo = authority.seed(tmp_path)
    return LocalApiApplication(repo, ProductOrchestrationService(repo), now=lambda: authority.NOW)


def test_create_open_list_and_capability(tmp_path):
    application = app(tmp_path)
    _, capability = application.handle("GET", "/api/v1/research/capability")
    assert capability["capability"]["mode"] == "DETERMINISTIC_LIBRARY_PACKET"
    assert capability["capability"]["provider_dispatch"] is False
    _, options = application.handle("GET", "/api/v1/research/scope?query=Phone")
    assert options["content"][0]["content_id"] == authority.VIDEO
    _, empty = application.handle("GET", "/api/v1/research")
    assert empty["research"] == []
    status, created = application.handle("POST", "/api/v1/research", json.dumps({"question": "sentence1", "content_ids": [authority.VIDEO]}).encode())
    assert status == 201
    research_id = created["research"]["packet"]["research_id"]
    _, opened = application.handle("GET", f"/api/v1/research/{research_id}")
    assert opened == created
    _, listing = application.handle("GET", "/api/v1/research")
    assert len(listing["research"]) == 1
    assert listing["research"][0]["research_id"] == research_id
    assert "evidence" not in listing["research"][0]


@pytest.mark.parametrize("payload,code", [
    ({"question": "\ud800", "content_ids": ["a"]}, "RESEARCH_INVALID_QUESTION"),
    ({"question": "valid", "content_ids": ["\udfff"]}, "RESEARCH_INVALID_SCOPE"),
    ({"question": "", "content_ids": ["a"]}, "RESEARCH_INVALID_QUESTION"),
    ({"question": "  ", "content_ids": ["a"]}, "RESEARCH_INVALID_QUESTION"),
    ({"question": "x" * 2001, "content_ids": ["a"]}, "RESEARCH_INVALID_QUESTION"),
    ({"question": "hello", "content_ids": []}, "RESEARCH_EMPTY_SCOPE"),
    ({"question": "hello", "content_ids": ["missing"]}, "RESEARCH_SCOPE_NOT_FOUND"),
    ({"question": "hello", "content_ids": ["a"], "topic_id": "compatibility"}, "RESEARCH_INVALID_SCOPE"),
    ({"question": "hello", "content_ids": ["a"], "authorize_cloud": True}, "RESEARCH_INVALID_SCOPE"),
])
def test_validation_codes(tmp_path, payload, code):
    with pytest.raises(ApiError) as rejected:
        app(tmp_path).handle("POST", "/api/v1/research", json.dumps(payload).encode())
    assert rejected.value.code == code


def test_api_rejects_unsupported_topic_source_history_and_diff(tmp_path):
    application = app(tmp_path)
    for suffix in ["history", "diff", "topics/compatibility", "sources/name", "bad-id"]:
        with pytest.raises(ApiError) as rejected:
            application.handle("GET", "/api/v1/research/" + suffix)
        assert rejected.value.status == 404


def test_history_api_exact_packet_wrong_owner_and_codes(tmp_path):
    application = app(tmp_path)
    payload = json.dumps({"question": "sentence1", "content_ids": [authority.VIDEO]}).encode()
    _, first = application.handle("POST", "/api/v1/research", payload)
    identity = first["research"]["packet"]["research_id"]
    revision = first["research"]["result_identity"]
    path = f"/api/v1/research/{identity}/history"
    assert application.handle("GET", path)[1]["revisions"] == []
    _, current = application.handle("POST", "/api/v1/research", payload)
    status, history = application.handle("GET", path)
    assert status == 200
    assert history["revisions"][0]["revision_id"] == revision
    assert application.handle("GET", f"{path}/{revision}")[1] == {**first, "is_current": False}
    assert application.handle("GET", f"{path}/{current["research"]["result_identity"]}")[1]["is_current"] is True
    assert application.handle("GET", f"/api/v1/research/{identity}")[1] == current
    for url, code, status in [
        (f"{path}/{'f' * 64}", "RESEARCH_REVISION_NOT_FOUND", 404),
        (f"/api/v1/research/{'f' * 64}/history/{revision}", "RESEARCH_REVISION_NOT_FOUND", 404),
        (path + "?cursor=bad", "RESEARCH_INVALID_CURSOR", 422),
        (path + "?cursor=1&cursor=2", "RESEARCH_INVALID_CURSOR", 422),
        (path + "?offset=1", "RESEARCH_INVALID_CURSOR", 422),
        (f"{path}/{revision}?cursor=bad", "RESEARCH_INVALID_CURSOR", 422),
        (f"/api/v1/research/{identity}/diff", "RESEARCH_NOT_FOUND", 404),
    ]:
        with pytest.raises(ApiError) as rejected:
            application.handle("GET", url)
        assert rejected.value.code == code and rejected.value.status == status
