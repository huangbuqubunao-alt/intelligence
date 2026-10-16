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


def _owned_workspace(tmp_path, monkeypatch):
    from types import SimpleNamespace
    harness = _harness()
    audit = tmp_path.resolve() / "local-timed-en"
    root = audit.parent / (audit.name + ".workspace")
    root.mkdir(mode=0o700)
    database, data = root / "state.sqlite3", root / "data"
    database.write_bytes(b"fixture not a real database")
    data.mkdir()
    monkeypatch.setattr(harness.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr=""))
    return harness, audit, root, database, data


@pytest.mark.parametrize("failure", ["external-db", "symlink", "hardlink", "public-root", "active-holder", "missing-lsof", "restore"])
def test_once_workspace_refuses_foreign_active_and_unknown_ownership(tmp_path, monkeypatch, failure):
    import os
    from types import SimpleNamespace
    harness, audit, root, database, data = _owned_workspace(tmp_path, monkeypatch)
    witness = harness.owned_workspace(audit, "local-timed-en", database, data)
    assert witness["root"] == str(root)
    if failure == "external-db":
        database = tmp_path / "formal.sqlite3"
        database.write_bytes(b"must never be opened")
    elif failure == "symlink":
        other = root / "other"
        database.rename(other)
        database.symlink_to(other)
    elif failure == "hardlink":
        os.link(database, root / "alias")
    elif failure == "public-root":
        root.chmod(0o755)
    elif failure == "active-holder":
        monkeypatch.setattr(harness.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout="999999", stderr=""))
    elif failure == "missing-lsof":
        def missing(*a, **k):
            raise FileNotFoundError("fixture lsof absent")
        monkeypatch.setattr(harness.subprocess, "run", missing)
    elif failure == "restore":
        control = root / ".intelligence-backup-restore"
        control.mkdir()
        (control / "restore-state.json").write_text("{}")
    with pytest.raises((ValueError, OSError)):
        harness.owned_workspace(audit, "local-timed-en", database, data)


def test_once_workspace_identity_detects_database_replacement(tmp_path, monkeypatch):
    harness, audit, root, database, data = _owned_workspace(tmp_path, monkeypatch)
    witness = harness.owned_workspace(audit, "local-timed-en", database, data)
    replacement = root / "replacement"
    replacement.write_bytes(database.read_bytes())
    replacement.replace(database)
    assert harness.owned_workspace(audit, "local-timed-en", database, data) != witness


def test_prepare_refuses_external_database_before_any_reservation(tmp_path, monkeypatch):
    harness, audit, root, database, data = _owned_workspace(tmp_path, monkeypatch)
    class NeverService:
        def __getattr__(self, name):
            pytest.fail("ownership must precede service/database access")
    with pytest.raises(ValueError):
        harness.prepare_case(NeverService(), case_id="local-timed-en", source_id="s", video_id="v", audit_root=audit, data_root=data, database=tmp_path / "formal.sqlite3")


def test_dedicated_preparation_preserves_verified_input_without_provider_io(tmp_path, monkeypatch):
    from youtube_intel.config import LocalScoringSettings
    from youtube_intel.distillation import (
        OllamaLocalDistillationTransport,
        PersonalizedDistillationService,
        bind_local_profile,
    )
    from youtube_intel.local_content import LOCAL_SOURCE_ID, LocalContentProvider
    from youtube_intel.local_distillation_profile import PROFILE_ID, resolve_profile
    from youtube_intel.source_policy import SourcePolicyApplicationService
    from youtube_intel.state import SQLiteStateRepository
    timed = _load_module("test_local_intelligence_timed")
    harness, audit, root, database, data = _owned_workspace(tmp_path, monkeypatch)
    # Construct a fresh fixture using ordinary import/proof producers; no copy,
    # rewrite or truncation of a formal owner's database or frozen Evidence.
    database.write_bytes(b"")
    repository = SQLiteStateRepository(database)
    repository.initialize(now=timed.support.NOW)
    provider = LocalContentProvider(repository, data, now=lambda: timed.support.NOW, transcriber=timed.media.Executor())
    imported = provider.import_bytes("voice.wav", timed.media.audio_bytes())
    profile = resolve_profile(PROFILE_ID)
    wire = OllamaLocalDistillationTransport(settings=LocalScoringSettings(model=profile.model, expected_model_digest=profile.model_digest), local_profile_id=PROFILE_ID)
    service = PersonalizedDistillationService(repository, SourcePolicyApplicationService(repository, now=lambda: timed.support.NOW), wire, timed.support._FakeBudget(True), now=lambda: timed.support.NOW, output_language_for_video=lambda _: "en")
    _, original = service._reserved_command(source_id=LOCAL_SOURCE_ID, video_id=imported.content_id, evidence_ids=repository.list_canonical_coverage_evidence_ids(imported.content_id), output_language="en", reason="MANUAL_CONTENT:grounding-local-timed-en")
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: pytest.fail("preparation must not perform provider IO"))
    prepared = harness.prepare_case(service, case_id="local-timed-en", source_id=LOCAL_SOURCE_ID, video_id=imported.content_id, audit_root=audit, data_root=data, database=database)
    expected = bind_local_profile(original, PROFILE_ID)
    assert prepared["input_hash"] == expected.semantic_hash
    assert prepared["request"] == harness.request_projection(expected)["request"]
    assert prepared["verified_input"] == harness.verified_distillation_input_projection(expected)
    assert repository.get_distillation_execution(prepared["execution_id"]).invocation_count == 0
    assert prepared["workspace_ownership"] == harness.owned_workspace(audit, "local-timed-en", database, data)
