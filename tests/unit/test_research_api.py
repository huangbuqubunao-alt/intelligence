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
