"""Neutral local wire discriminator preserves strict admission and provenance."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest
from conftest import _load_module

from youtube_intel.distillation import OllamaLocalDistillationTransport

support = _load_module("test_task022_personalized_distillation")


def _workspace(tmp_path):
    repository = support._repository(tmp_path)
    source, video = support._source_and_video(repository)
    evidence = support._evidence(repository, video)
    service = support._service(repository, support._FakeTransport(support._raw(evidence)))
    command = replace(support._command(source, video, evidence),
        selected_provider="ollama", selected_model="qwen3:8b")
    verified = service._compose_verified_input(command)
    return service, command, verified, evidence


def test_local_schema_has_explicit_symmetric_wire_branch_markers():
    positive, zero = OllamaLocalDistillationTransport._SCHEMA["anyOf"]
    assert positive["properties"]["result"]["enum"] == ["INTELLIGENCE"]
    assert zero["properties"]["result"]["enum"] == ["NO_NEW_INTELLIGENCE"]
    for branch in (positive, zero):
        assert branch["required"][0] == "result"
        assert branch["additionalProperties"] is False


def test_verified_local_positive_branch_decodes_without_changing_content(tmp_path):
    service, command, verified, evidence = _workspace(tmp_path)
    old_raw = support._raw(evidence)
    tagged = {"result": "INTELLIGENCE", **json.loads(old_raw)}
    wire = json.dumps(tagged)
    candidate = service._parse_candidate(wire, command, verified)
    legacy = service._parse_candidate(old_raw, command, verified)
    assert candidate == legacy
    assert json.loads(wire) == tagged


@pytest.mark.parametrize("marker", ["NO_NEW_INTELLIGENCE", "UNKNOWN", None, True])
def test_mixed_or_unknown_local_branch_is_rejected(tmp_path, marker):
    service, command, verified, evidence = _workspace(tmp_path)
    tagged = {"result": marker, **json.loads(support._raw(evidence))}
    with pytest.raises(ValueError):
        service._parse_candidate(json.dumps(tagged), command, verified)


def test_local_marker_does_not_expand_cloud_wire_contract(tmp_path):
    service, command, verified, evidence = _workspace(tmp_path)
    tagged = {"result": "INTELLIGENCE", **json.loads(support._raw(evidence))}
    with pytest.raises(ValueError):
        service._parse_candidate(json.dumps(tagged),
            replace(command, selected_provider="openai", selected_model="gpt-4.1"),
            replace(verified, selected_provider="openai", selected_model="gpt-4.1"))


def test_explicit_positive_does_not_repair_fabricated_evidence(tmp_path):
    service, command, verified, _evidence = _workspace(tmp_path)
    tagged = {"result": "INTELLIGENCE", **json.loads(support._raw("invented-evidence"))}
    with pytest.raises(ValueError):
        service._parse_candidate(json.dumps(tagged), command, verified)
