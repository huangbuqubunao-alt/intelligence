"""The harness defaults to preparation; no fixture authorizes a real call."""
from __future__ import annotations

import importlib.util
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from conftest import _load_module

support = _load_module("test_local_grounding_profile")


def _harness():
    path = Path(__file__).parents[2] / "scripts/qualify_local_grounding_v1.py"
    spec = importlib.util.spec_from_file_location("grounding_harness", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_harness_projection_is_exact_production_builder_and_never_calls(monkeypatch):
    from youtube_intel.distillation import build_local_distillation_request
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: pytest.fail("no provider IO in preparation"))
    harness = _harness()
    projection = harness.request_projection(support._input())
    assert projection["request"] == build_local_distillation_request(support._input())
    assert harness.describe()["production_qualified"] is False
    assert harness.describe()["execution_authority"] == "NONE"


def test_harness_refuses_missing_unfrozen_or_fixture_execution_package(tmp_path, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: pytest.fail("unreviewed execution must make zero calls"))
    harness = _harness()
    with pytest.raises((ValueError, OSError)):
        harness.validate_execution_package(tmp_path, tmp_path / "permit.json", tmp_path / "freeze.json")


def test_once_claim_survives_restart_and_never_overwrites(tmp_path):
    harness = _harness()
    path = tmp_path / "generation.started.json"
    harness.write_once(path, {"request_hash": "a" * 64})
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        harness.write_once(path, {"request_hash": "b" * 64})
    assert path.read_bytes() == before


@pytest.mark.parametrize("change", [{"content_provider": "LOCAL"}, {"wire_version": "local-text-distillation-v2"},
    {"input_json": "{}"}, {"context_json": "{}"}, {"local_content_context_hash": "a" * 64},
    {"local_profile_id": "future"}, {"local_profile_hash": "a" * 64}])
def test_historical_research_export_refuses_nondefault_or_local_input(change):
    from scripts import qualify_readiness_qwen35_intelligence as research
    with pytest.raises(ValueError):
        research.historical_timed_input_projection(replace(support.legacy._input(), **change))


@pytest.mark.parametrize("change", [{"locator_type": "TEXT_RANGE"}, {"start_offset": 0}, {"end_offset": 1},
    {"start_line": 1}, {"end_line": 1}, {"source_content_hash": "a" * 64}])
def test_historical_research_export_refuses_range_evidence(change):
    from scripts import qualify_readiness_qwen35_intelligence as research
    value = support.legacy._input()
    with pytest.raises(ValueError):
        research.historical_timed_input_projection(replace(value, evidence=(replace(value.evidence[0], **change),)))


def test_historical_export_is_explicitly_separate_from_current_proof_export():
    from scripts import qualify_readiness_qwen35_intelligence as research
    from youtube_intel.distillation import verified_distillation_input_projection
    value = support.legacy._input()
    current = verified_distillation_input_projection(value)
    assert "wire_version" in current and "locator_type" in current["evidence"][0]
    assert "local_profile_id" not in current and "local_profile_hash" not in current
    historical = research.historical_timed_input_projection(value)
    assert set(historical) == set(asdict(value)) - {"wire_version", "input_json", "context_json", "local_profile_id", "local_profile_hash"}
    assert set(historical["evidence"][0]) == {"evidence_id", "start_ms", "end_ms", "excerpt", "excerpt_hash", "timed_transcript_id", "timed_transcript_hash"}


def test_historical_export_refuses_future_fields(monkeypatch):
    from scripts import qualify_readiness_qwen35_intelligence as research
    value = support.legacy._input()
    monkeypatch.setattr(research, "asdict", lambda _: {**asdict(value), "future": None})
    with pytest.raises(ValueError):
        research.historical_timed_input_projection(value)
