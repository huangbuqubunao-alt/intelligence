"""Single approved capacity diagnosis contracts, never live model qualification."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from scripts import qualify_readiness_qwen35_intelligence as research
from youtube_intel.distillation import (
    KnownLocalDistillationResponseError,
    OllamaLocalDistillationTransport,
    VerifiedDistillationInput,
    VerifiedEvidenceInput,
)

CAPACITY = "readiness-qwen35-9b-thinking-capacity6144-single-v3"

@pytest.fixture
def capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("PROFILE_ID", "PROFILE_PATH", "FREEZE_PATH", "OPTIONS", "CASE_ROOT", "THINK"):
        monkeypatch.setattr(research, name, getattr(research, name))
    research.select_profile(CAPACITY)


def actual_input() -> VerifiedDistillationInput:
    value = research.read_object(research.CAPACITY_BASELINE_ROOT / "verified-input.json")
    value["evidence"] = tuple(VerifiedEvidenceInput(**entry) for entry in value["evidence"])
    for key in ("personalization", "source_focus_rules", "source_ignore_rules"):
        value[key] = tuple(value[key])
    return VerifiedDistillationInput(**value)


def test_capacity_changes_only_budget_and_never_claims_qualification(capacity: None) -> None:
    profile = research.load_profile()
    previous = research.read_object(research.DOCS / "QWEN35_RESEARCH_PROFILE_V2.json")
    assert profile["case_order"] == previous["case_order"][:1]
    assert profile["policy"] == previous["policy"]
    assert profile["production_qualified"] is False
    assert profile["request_parameters"] == {**previous["request_parameters"], "num_predict": 6144}
    assert research.CASE_ROOT.name == CAPACITY
    research.select_profile(research.V2_PROFILE_ID)
    assert research.OPTIONS["num_predict"] == 4096


@pytest.mark.parametrize("case", research.CASE_IDS[1:])
@pytest.mark.parametrize("action", ["prepare", "execute", "load"])
def test_unapproved_cases_reject_before_any_io(capacity: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, action: str) -> None:
    monkeypatch.setattr(research, "CASE_ROOT", tmp_path / "cases")
    monkeypatch.setattr(research, "validate_freeze", lambda: pytest.fail("No freeze IO before rejecting case"))
    monkeypatch.setattr(research, "read_object", lambda *a: pytest.fail("No receipt IO before rejecting case"))
    with pytest.raises(ValueError, match="single"):
        if action == "prepare":
            research.prepare_case(case)
        elif action == "execute":
            research.execute_case(case, tmp_path / "absent.json")
        else:
            research.load_case(case)
    assert not tuple(tmp_path.iterdir())


def test_projection_is_exact_old_actual_request_except_predict(capacity: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OllamaLocalDistillationTransport, "_request", lambda *a, **k: pytest.fail("Projection must not access provider"))
    old = research.read_object(research.CAPACITY_BASELINE_ROOT / "request.json")
    projection = research.capacity_request_projection(actual_input())
    assert projection == {**old, "options": {**old["options"], "num_predict": 6144}}
    assert projection["messages"] == old["messages"]
    assert projection["format"] == old["format"]
    with pytest.raises(ValueError, match="projection"):
        research.capacity_request_projection(replace(actual_input(), video_title="Different source input"))


@pytest.mark.parametrize("failure", ["budget", "length", "empty", "timeout", "none"])
def test_capacity_one_attempt_preserves_response_and_stops(capacity: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    calls = []
    def fake(self, path, *, method, body=None):
        calls.append(path)
        assert path == "/api/chat" and body["options"]["num_predict"] == 6144
        if failure == "timeout":
            raise TimeoutError("synthetic unknown 300s completion")
        return {"model": research.MODEL, "done": True, "done_reason": "length" if failure == "length" else "stop", "eval_count": 6144 if failure == "budget" else 4096, "message": {"content": "" if failure == "empty" else "{}", "thinking": "opaque fixture never interpreted"}}
    monkeypatch.setattr(OllamaLocalDistillationTransport, "_request", fake)
    transport = research.Qwen35ResearchTransport(root=tmp_path, execute_authorized=True)
    if failure == "none":
        result = transport.generate(actual_input())
        assert result.output_tokens == 4096
    else:
        with pytest.raises(TimeoutError if failure == "timeout" else KnownLocalDistillationResponseError):
            transport.generate(actual_input())
    assert len(calls) == 1 and (tmp_path / "generation.started.json").exists()
    assert (tmp_path / "response.json").exists() is (failure != "timeout")
    restarted = research.Qwen35ResearchTransport(root=tmp_path, execute_authorized=True)
    with pytest.raises(RuntimeError, match="once"):
        restarted.generate(actual_input())
    assert len(calls) == 1
    assert not transport.is_authorized_for_normal_production(actual_input())


def test_capacity_preparation_seals_original_input_data_and_fresh_execution(capacity: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(research, "CASE_ROOT", tmp_path / "cases")
    monkeypatch.setattr(research, "validate_freeze", lambda: {})
    monkeypatch.setattr(OllamaLocalDistillationTransport, "_request", lambda *a, **k: pytest.fail("No prepare network"))
    prepared = research.prepare_case("real-deepthink-en")
    old = research.read_object(research.CAPACITY_BASELINE_ROOT / "prepared.json")
    assert prepared["execution_id"] != old["execution_id"]
    assert prepared["verified_input_sha256"] == old["verified_input_sha256"]
    assert prepared["prepared_data_hashes"] == old["prepared_data_hashes"]
    assert prepared["baseline_request_sha256"] == research.sha256(research.CAPACITY_BASELINE_ROOT / "request.json")
    root = research.CASE_ROOT / "real-deepthink-en"
    assert prepared["request_projection_sha256"] == research.sha256(root / "request-projection.json")
    assert not (root / "generation.started.json").exists() and not (root / "execution-permit.json").exists()
    assert prepared["production_qualified"] is False
    with pytest.raises(FileExistsError):
        research.prepare_case("real-deepthink-en")


def test_capacity_cannot_execute_without_root_permit(capacity: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(research, "CASE_ROOT", tmp_path / "cases")
    with pytest.raises(FileNotFoundError):
        research.execute_case("real-deepthink-en", tmp_path / "absent-permit.json")
    assert not tuple(tmp_path.iterdir())


@pytest.mark.parametrize("changed", ["policy", "model", "seed", "case_order", "timeout"])
def test_capacity_cannot_change_frozen_scope(capacity: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: str) -> None:
    profile = research.read_object(research.PROFILE_PATH)
    if changed == "policy":
        profile["policy"]["all_positive_claims_independently_semantically_reviewed"] = False
    elif changed == "model":
        profile["actual_model"] = "qwen3:8b"
    elif changed == "seed":
        profile["request_parameters"]["seed"] += 1
    elif changed == "case_order":
        profile["case_order"] += research.read_object(research.DOCS / "QWEN35_RESEARCH_PROFILE_V2.json")["case_order"][1:]
    else:
        profile["capacity_single"]["request_timeout_seconds"] = 600
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile))
    monkeypatch.setattr(research, "PROFILE_PATH", path)
    with pytest.raises(ValueError):
        research.load_profile()


@pytest.mark.parametrize("tamper", ["none", "cases", "count", "baseline", "projection", "exclusive", "unknown", "prior"])
def test_capacity_external_root_receipt_is_exact(capacity: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str) -> None:
    monkeypatch.setattr(research, "CASE_ROOT", tmp_path / "cases")
    monkeypatch.setattr(research, "validate_freeze", lambda: {})
    root = research.CASE_ROOT / "real-deepthink-en"
    root.mkdir(parents=True)
    (root / "prepared.json").write_text("{}")
    (root / "request-projection.json").write_text(json.dumps(research.capacity_expected_request()))
    runtime = research.read_object(research.DOCS / "QWEN35_RUNTIME_STATIC_PROVENANCE.json")
    permit = {
        "status": "APPROVED_ISOLATED_GENERATION", "case": "real-deepthink-en",
        "pre_output_review": "APPROVE", "root_start_authorized": True,
        "installed_manifest_verified": True, "all_installed_blob_hashes_verified": True,
        "runtime_parameters_verified": True, "installed_runtime": "0.40.1",
        "actual_provider": "ollama", "actual_model": research.MODEL,
        "manifest_digest": research.DIGEST, "profile": CAPACITY,
        "production_qualified": False, "cloud_authorized": False,
        "harness_sha256": research.sha256(Path(research.__file__)),
        "profile_sha256": research.sha256(research.PROFILE_PATH),
        "freeze_sha256": research.sha256(research.FREEZE_PATH),
        "prepared_sha256": research.sha256(root / "prepared.json"),
        "post_install_free_bytes": 15 * 1024**3, "prior_semantic_reviews": [],
        "exclusive_heavyweight_execution_confirmed": True,
        "no_unresolved_prior_heavyweight_execution": True,
        "runtime_parameters_verified_meaning": runtime["runtime_parameters_verified_meaning"],
        "runtime_static_provenance_sha256": research.sha256(research.DOCS / "QWEN35_RUNTIME_STATIC_PROVENANCE.json"),
        "installation_receipt_sha256": research.sha256(research.DOCS / "MODEL_REPLACEMENT_INSTALL_RECEIPT.json"),
        "single_case_only": True, "maximum_generations": 1,
        "authorized_case_ids": ["real-deepthink-en"],
        "request_projection_sha256": research.sha256(root / "request-projection.json"),
        "baseline_request_sha256": research.sha256(research.CAPACITY_BASELINE_ROOT / "request.json"),
    }
    mutations = {
        "cases": ("authorized_case_ids", list(research.CASE_IDS)),
        "count": ("maximum_generations", True), "baseline": ("baseline_request_sha256", "0" * 64),
        "projection": ("request_projection_sha256", "0" * 64),
        "exclusive": ("exclusive_heavyweight_execution_confirmed", False),
        "unknown": ("no_unresolved_prior_heavyweight_execution", False),
        "prior": ("prior_semantic_reviews", [{"case": "real-deepthink-zh-cn", "verdict": "PASS"}]),
    }
    if tamper in mutations:
        key, value = mutations[tamper]
        permit[key] = value
    path = tmp_path / "root-permit.json"
    path.write_text(json.dumps(permit))
    if tamper == "none":
        assert research.validate_execution_permit(path, "real-deepthink-en") == permit
    else:
        with pytest.raises(ValueError):
            research.validate_execution_permit(path, "real-deepthink-en")
    assert not (root / "generation.started.json").exists()


def test_capacity_cli_cannot_restart_retired_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    monkeypatch.setattr(sys, "argv", ["research", "--profile", research.V2_PROFILE_ID, "--case", "real-deepthink-en", "--prepare-only"])
    monkeypatch.setattr(research, "prepare_case", lambda *a, **k: pytest.fail("No old experiment preparation"))
    with pytest.raises(SystemExit):
        research.main()
