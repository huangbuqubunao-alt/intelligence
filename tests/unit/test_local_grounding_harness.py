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


def _manifest_resource_fixture(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace

    from youtube_intel import local_model_capacity as capacity
    from youtube_intel.distillation import build_local_distillation_request
    from youtube_intel.local_distillation_profile import digest

    manifests = _load_module("test_capacity_host_manifest")
    wrapper, parent, reference, binary, payloads = manifests.fixture_installation(tmp_path, monkeypatch)
    harness = _harness()
    profile = capacity.resolve_profile(capacity.PROFILE_ID)
    monkeypatch.setattr(harness, "resolve_profile", lambda _: profile)
    monkeypatch.setattr(harness, "available_memory_bytes", lambda: 20 * capacity.GIB)
    request = build_local_distillation_request(support._input())
    (tmp_path / "prepared.json").write_text(json.dumps({"request": request}))
    runtime_path, proof_path = tmp_path / "runtime.json", tmp_path / "capacity.json"
    runtime = {"runtime": profile.runtime, "model_cache_root": str(parent.parent.parent), "required_available_memory_bytes": sum(capacity.BLOBS.values()) + 2 * capacity.GIB}
    proof = {"status": "INDEPENDENTLY_VERIFIED", "request_hash": digest(request), "model_digest": profile.model_digest,
        "num_ctx": 16384, "num_predict": 6144, "complete_prompt_token_upper_bound": profile.complete_input_token_upper_bound(request),
        "capacity_contract": "qwen35-byte-vocabulary-chat-system-user-88-plus2-v1", "max_request_bytes": 12288, "max_content_bytes": 8192,
        "full_input_preserved": True, "method": "QWEN35_COMPLETE_BYTE_VOCABULARY_UPPER_BOUND", "template_hash": "a" * 64,
        "tokenizer_hash": "b" * 64, "code_hash": "c" * 64, "profile_hash": "d" * 64, "reviewer_id": "fixture-reviewer", "producer_id": "fixture-producer"}
    runtime_path.write_text(json.dumps(runtime))
    proof_path.write_text(json.dumps(proof))
    # A resource-check fixture is not an execute permit or production authority.
    permit = SimpleNamespace(case_id="real-deepthink-en", runtime_proof_hash=harness.file_hash(runtime_path), capacity_proof_hash=harness.file_hash(proof_path), request_hash=digest(request), binding={"code_hash": "c" * 64, "profile_hash": "d" * 64})
    freeze = {"runtime_proof_path": str(runtime_path), "capacity_proof_paths": {permit.case_id: str(proof_path)}}
    return harness, freeze, permit, wrapper, parent, reference, binary, payloads


def test_resource_preflight_reuses_complete_fixed_installation_without_provider_io(tmp_path, monkeypatch):
    harness, freeze, permit, *_ = _manifest_resource_fixture(tmp_path, monkeypatch)
    from youtube_intel import local_model_capacity as capacity
    monkeypatch.setattr(capacity, "processes", lambda *_: pytest.fail("resource byte check is not model/process preparation"))
    harness.verify_resources(tmp_path, freeze, permit)
    assert harness.describe()["production_qualified"] is False


@pytest.mark.parametrize("damage", ["wrapper", "parent", "reference", "payload", "binary", "memory", "runtime-proof", "capacity-proof", "permit-hash"])
def test_resource_preflight_preserves_byte_resource_and_proof_rejections(tmp_path, monkeypatch, damage):
    harness, freeze, permit, wrapper, parent, reference, binary, payloads = _manifest_resource_fixture(tmp_path, monkeypatch)
    if damage in {"wrapper", "parent", "payload", "binary"}:
        path = {"wrapper": wrapper, "parent": parent, "payload": payloads[1], "binary": binary}[damage]
        path.write_bytes(b"x" * path.stat().st_size)
    elif damage == "reference":
        reference.rename(reference.parent / "old-link")
        reference.symlink_to("../../../../blobs/sha256-" + "a" * 64)
    elif damage == "memory":
        monkeypatch.setattr(harness, "available_memory_bytes", lambda: 0)
    elif damage == "runtime-proof":
        Path(freeze["runtime_proof_path"]).write_text("{}")
    elif damage == "capacity-proof":
        Path(freeze["capacity_proof_paths"][permit.case_id]).write_text("{}")
    elif damage == "permit-hash":
        permit.runtime_proof_hash = "0" * 64
    with pytest.raises((ValueError, OSError)):
        harness.verify_resources(tmp_path, freeze, permit)


@pytest.mark.parametrize("profile_id", ["local-grounding-qwen35-9b-runtime-0.40.6-v3", "local-grounding-qwen35-9b-lossless-rle-runtime-0.40.6-v2"])
def test_current_harness_has_finite_complete_case_matrix_and_no_grant(profile_id):
    from youtube_intel.local_distillation_qualification import LONG_CURRENT
    harness = _harness()
    description = harness.describe(profile_id)
    assert description["profile_id"] == profile_id
    assert description["production_qualified"] is False and description["real_model_calls"] == 0
    if profile_id == LONG_CURRENT:
        assert list(description["case_order"]["YT_TIMED"])[-2:] == ["long-full-en", "long-full-zh"]
        assert len(description["case_order"]["YT_TIMED"]) == 12
    else:
        assert len(description["case_order"]["LOCAL_TEXT"]) == 8
    with pytest.raises(ValueError):
        harness.describe(profile_id + "-arbitrary")


@pytest.mark.parametrize("damage", [None, "byte-substitute", "overflow", "schema", "template", "request", "same-reviewer", "full-input"])
def test_current_harness_frozen_capacity_is_exact_native_and_never_a_caller_ready(damage):
    import hashlib
    from types import SimpleNamespace

    from youtube_intel.distillation import (
        bind_local_profile,
        build_local_distillation_request,
    )
    from youtube_intel.local_distillation_profile import (
        CURRENT_RUNTIME_PROFILE_ID,
        digest,
    )
    from youtube_intel.local_distillation_qualification import (
        qualification_binding,
        qualification_projection,
    )
    from youtube_intel.local_native_capacity import render_qwen35_prompt
    value = bind_local_profile(support._input(), CURRENT_RUNTIME_PROFILE_ID)
    request = build_local_distillation_request(value)
    binding = qualification_binding(qualification_projection(CURRENT_RUNTIME_PROFILE_ID, "YT_TIMED"))
    permit = SimpleNamespace(binding=binding, request_hash=digest(request))
    capacity = {"status": "INDEPENDENTLY_VERIFIED", "capacity_contract": "QWEN35_NATIVE_FULL_PROMPT_N_PLUS_P_PLUS2_V1",
        "method": "PINNED_CURRENT_NATIVE_TOKEN_SEQUENCE", "request_hash": permit.request_hash,
        "model_digest": binding["model_digest"], "num_ctx": 16384, "num_predict": 8192,
        "complete_prompt_token_count": 100, "rendered_prompt_hash": hashlib.sha256(render_qwen35_prompt(request).encode()).hexdigest(),
        "schema_hash": digest(request["format"]), "code_hash": binding["code_hash"], "profile_hash": binding["profile_hash"],
        "full_input_preserved": True, "native_token_sequence_hash": "a" * 64, "template_hash": "b" * 64,
        "tokenizer_hash": "c" * 64, "reviewer_id": "independent", "producer_id": "producer"}
    if damage:
        if damage == "byte-substitute":
            capacity.pop("complete_prompt_token_count")
            capacity["complete_prompt_token_upper_bound"] = 100
        else:
            key, value = {"overflow": ("complete_prompt_token_count", 8191), "schema": ("schema_hash", "d" * 64),
                "template": ("template_hash", "unknown"), "request": ("request_hash", "d" * 64),
                "same-reviewer": ("reviewer_id", "producer"), "full-input": ("full_input_preserved", False)}[damage]
            capacity[key] = value
        with pytest.raises(ValueError):
            _harness().verify_current_capacity_document(capacity, {"request": request}, permit)
    else:
        _harness().verify_current_capacity_document(capacity, {"request": request}, permit)


def test_current_long_harness_prepares_full_durable_source_without_native_or_generation(tmp_path, monkeypatch):
    from youtube_intel.local_distillation_qualification import (
        LONG_ACTUAL as LONG_CURRENT,
    )
    lifecycle = _load_module("test_long_completion_lifecycle")
    audit = tmp_path.resolve() / "long-full-en"
    workspace = audit.parent / (audit.name + ".workspace")
    workspace.mkdir(mode=0o700)
    repo, data, sid, vid, service, transport, lease = lifecycle.ready_fixture(workspace, full=True)
    lease.release()
    harness = _harness()
    # Source is synthetic engineering (abcdefghijk), never a genuine long-full
    # semantic receipt; later package validation requires the actual fixed ID.
    service._output_language_for_video = lambda _: "en"
    result = harness.prepare_case(service, case_id="long-full-en", source_id=sid, video_id=vid,
        audit_root=audit, data_root=data, database=repo._database_path, profile_id=LONG_CURRENT)
    assert result["binding"]["profile_id"] == LONG_CURRENT
    assert result["evidence_count"] == 114 and result["cue_count"] == 2406
    assert result["request"]["options"]["num_ctx"] == 32768
    assert repo.get_distillation_execution(result["execution_id"]).invocation_count == 0
    assert transport.calls == 0 and result["production_qualified"] is False


@pytest.mark.parametrize("ledger_unreadable", [False, True])
def test_actual_unknown_failure_still_leaves_durable_unmodified_observation(tmp_path, ledger_unreadable):
    from types import SimpleNamespace
    harness = _harness()
    class Repository:
        def get_distillation_execution(self, eid):
            assert eid == "claimed-once"
            if ledger_unreadable:
                raise ValueError("actual corrupt ledger fixture")
            from youtube_intel.state import DistillationExecutionRecord
            return DistillationExecutionRecord(execution_id=eid, source_id="s", video_id="v", reason="MANUAL_CONTENT:test",
                use_case="test", selected_provider="ollama", selected_model="actual-model", output_language="en",
                status="PENDING", invocation_count=1, budget_state="DISPATCH_CLAIMED", intelligence_id=None,
                revision_id=None, created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
                updated_at=__import__("datetime").datetime.now(__import__("datetime").UTC))
    class Service:
        _repository = Repository()
        def continue_qualification_reserved_distillation(self, eid):
            raise OSError("authentic unknown fixture")
    transport = SimpleNamespace(last_grounding_post_attempted=True, last_grounding_final=None,
        last_grounding_raw_hash=None, last_grounding_response_error=None, last_grounding_completion=None)
    permit = SimpleNamespace(case_id="local-timed-en", execution_id="claimed-once", permit_hash="a" * 64, request_hash="b" * 64)
    with pytest.raises(OSError, match="authentic unknown fixture"):
        harness.execute_observed_case(Service(), transport, permit, tmp_path)
    result = harness.read_object(tmp_path / "result.json")
    assert result["outcome"] is None and result["execution_error_type"] == "OSError"
    if ledger_unreadable:
        assert result["persisted_execution"] is None
        assert result["persisted_execution_read_error_type"] == "ValueError"
    else:
        assert result["persisted_execution"]["status"] == "PENDING"
        assert result["persisted_execution"]["invocation_count"] == 1
    assert result["generation_post_attempted_locally"] is True
    assert result["production_qualified"] is False
    assert result["semantic_acceptance"] == "PENDING_INDEPENDENT_REVIEW"
