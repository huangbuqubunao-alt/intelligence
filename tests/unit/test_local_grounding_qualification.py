"""Qualification fixtures exercise rejection only, never qualify a model."""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from conftest import _load_module

from youtube_intel.config import LocalScoringSettings
from youtube_intel.distillation import (
    OllamaLocalDistillationTransport,
    local_profile_projection,
)
from youtube_intel.local_distillation_profile import PROFILE_ID, resolve_profile
from youtube_intel.local_distillation_qualification import (
    CASE_LANGUAGES,
    LocalQualificationAuthority,
    QualificationRecord,
    qualification_binding,
    read_reviewed_qualifications,
)

support = _load_module("test_local_grounding_profile")
NOW = datetime(2026, 10, 15, tzinfo=UTC)


def test_empty_reviewed_package_and_arbitrary_fixture_records_are_closed():
    projection = local_profile_projection(support._input())
    assert not read_reviewed_qualifications().permits(projection, "en", now=NOW)
    for value in ({}, {"version": "local-distillation-qualification-v1", "records": [
        {"mode": "FIXTURE_CONTRACT", "passed": True}]}, {"version": "future", "records": []}):
        assert not read_reviewed_qualifications(json.dumps(value).encode()).permits(projection, "en", now=NOW)


@pytest.mark.parametrize("raw", [b"null", b"[]", b"{", b'{"version":"local-distillation-qualification-v1","version":"future","records":[]}', b"x" * 262145])
def test_invalid_package_never_grants_authority(raw):
    assert read_reviewed_qualifications(raw).states(now=NOW) == ()


def test_binding_covers_runtime_code_profile_scope_schema_and_not_qualification_data():
    projection = local_profile_projection(support._input())
    binding = qualification_binding(projection)
    assert binding["profile_hash"] == support._input().local_profile_hash
    assert binding["runtime"] == "0.40.1" and binding["scope"] == "YT_TIMED"
    assert len(binding["code_hash"]) == 64 and len(binding["schema_hash"]) == 64
    assert qualification_binding({**projection, "scope": "LOCAL_TIMED"}) != binding


def test_boolean_does_not_enable_new_profile_or_inherit_legacy_scope():
    profile = resolve_profile(PROFILE_ID)
    transport = OllamaLocalDistillationTransport(settings=LocalScoringSettings(model=profile.model,
        expected_model_digest=profile.model_digest), production_qualified=True, local_profile_id=PROFILE_ID)
    value = support._input()
    assert not transport.is_authorized_for_normal_production(value)
    assert not transport.is_authorized_for_qualification(value)
    assert not transport.is_authorized_for(replace(value, local_profile_hash="0" * 64))
    assert not LocalQualificationAuthority().permits(local_profile_projection(value), "en", now=NOW)


@pytest.mark.parametrize("change", [{"done": False}, {"done": None}, {"done_reason": "length"},
    {"done_reason": None}, {"prompt_eval_count": None}, {"prompt_eval_count": 16384}, {"eval_count": 6144},
    {"eval_count": None}, {"eval_count": True}, {"model": "qwen3:8b"}])
def test_new_response_requires_complete_untruncated_identity_and_counts(change):
    from youtube_intel.distillation import (
        KnownLocalDistillationResponseError,
        validate_local_grounding_response,
    )
    response = {"model": resolve_profile(PROFILE_ID).model, "done": True, "done_reason": "stop",
        "prompt_eval_count": 100, "eval_count": 50, "message": {"content": "{}"}}
    with pytest.raises(KnownLocalDistillationResponseError):
        validate_local_grounding_response({**response, **change}, support._input(), duration_ms=1)


def _seal(record):
    from youtube_intel.local_distillation_profile import digest
    for case in record["cases"]:
        case["source_manifest_hash"] = digest(case["source_manifest"])
        case["review"]["review_hash"] = digest({k: v for k, v in case["review"].items() if k != "review_hash"})
        case["receipt_hash"] = digest({k: v for k, v in case.items() if k != "receipt_hash"})
    record["case_manifest_hash"] = digest([{k: c[k] for k in ("case_id", "output_language", "scope",
        "input_hash", "context_hash", "request_hash", "source_manifest_hash")} for c in record["cases"]])
    record["record_hash"] = digest({k: v for k, v in record.items() if k != "record_hash"})
    return record


def _audit_fixture():
    """Structurally consistent invented audit; reader(raw=...) cannot mint authority."""
    from youtube_intel.local_distillation_profile import digest
    projection = local_profile_projection(support._input())
    binding = qualification_binding(projection)
    record = {"version": "local-distillation-qualification-v1", "binding": binding,
        "generated_at": "2026-10-15T00:00:00Z", "expires_at": "2026-10-16T00:00:00Z",
        "freeze_hash": "a" * 64, "harness_hash": "b" * 64, "cases": []}
    for index, (name, language) in enumerate(CASE_LANGUAGES["YT_TIMED"].items()):
        request_hash = digest(name)
        source = "a" if name.startswith("holdout-a-") else "b" if name.startswith("holdout-b-") else name
        record["cases"].append({"case_id": name, "output_language": language, "scope": "YT_TIMED", "mode": "LIVE_MODEL",
            "producer_id": "fixture-producer", "execution_id": "fixture-" + name,
            "input_hash": request_hash, "context_hash": "c" * 64, "request_hash": request_hash,
            "profile_hash": binding["profile_hash"], "code_hash": binding["code_hash"],
            "freeze_hash": record["freeze_hash"], "harness_hash": record["harness_hash"],
            "model_digest": binding["model_digest"], "runtime": binding["runtime"],
            "permit_hash": "d" * 64, "capacity_proof_hash": "e" * 64, "runtime_proof_hash": "f" * 64,
            "raw_hash": "1" * 64, "final_hash": "2" * 64,
            "source_manifest": {"origin": "PUBLIC_SNAPSHOT", "source_id": source, "snapshot_hash": digest(source),
                "summary_hash": "3" * 64, "evidence_hash": "4" * 64, "policy_hash": "5" * 64,
                "input_hash": request_hash, "context_hash": "c" * 64, "request_hash": request_hash,
                "unseen_for_profile": True, "selector_id": "independent-fixture-selector"},
            "generation_count": 1, "ledger_invocation_count": 1, "done": True, "done_reason": "stop",
            "prompt_tokens": 900, "output_tokens": 100,
            "completed_at": f"2026-10-14T23:{index:02}:00Z",
            "review": {"reviewer_id": "fixture-reviewer", "case_id": name, "input_hash": request_hash,
                "request_hash": request_hash, "final_hash": "2" * 64, "verdict": "PASS",
                "reviewed_at": f"2026-10-14T23:{index:02}:30Z"}})
    return _seal(record)


def test_even_complete_caller_audit_bytes_never_mint_package_authority():
    projection = local_profile_projection(support._input())
    record = _audit_fixture()
    # Positive structural control is separate from the sealed production authority.
    assert QualificationRecord.model_validate(record).permits(projection, "en", NOW)
    authority = read_reviewed_qualifications(json.dumps({"version": "local-distillation-qualification-v1", "records": [record]}).encode())
    assert authority.permits(projection, "en", now=NOW) is False
    assert read_reviewed_qualifications().permits(projection, "en", now=NOW) is False


@pytest.mark.parametrize("damage", ["future", "expired", "too-old", "code", "scope", "model", "runtime", "profile", "case-missing",
    "case-duplicate", "case-extra", "case-order", "fixture", "twice", "ledger", "length", "tokens", "unknown-completion", "review-fail",
    "same-reviewer", "review-input", "receipt", "old-freeze", "old-code", "seen-holdout", "fixture-holdout", "same-source"])
def test_strict_record_negative_matrix_rejects_resealed_changes(damage):
    record = _audit_fixture()
    case = record["cases"][0]
    if damage == "future":
        record["generated_at"] = "2026-10-15T00:00:01Z"
    elif damage == "expired":
        record["expires_at"] = "2026-10-15T00:00:00Z"
    elif damage == "too-old":
        record["expires_at"] = "2027-10-15T00:00:00Z"
    elif damage in {"code", "scope", "model", "runtime", "profile"}:
        record["binding"][{"code": "code_hash", "profile": "profile_hash"}.get(damage, damage)] = "wrong"
    elif damage == "case-missing":
        record["cases"].pop()
    elif damage == "case-duplicate":
        record["cases"][1] = record["cases"][0]
    elif damage == "case-extra":
        record["cases"].append(dict(case))
    elif damage == "case-order":
        record["cases"].reverse()
    elif damage == "fixture":
        case["mode"] = "FIXTURE_CONTRACT"
    elif damage in {"twice", "ledger", "tokens"}:
        case[{"twice": "generation_count", "ledger": "ledger_invocation_count", "tokens": "output_tokens"}[damage]] = 6144 if damage == "tokens" else 2
    elif damage == "length":
        case["done_reason"] = "length"
    elif damage == "unknown-completion":
        case["done"] = False
    elif damage == "review-fail":
        case["review"]["verdict"] = "FAIL"
    elif damage == "same-reviewer":
        case["review"]["reviewer_id"] = case["producer_id"]
    elif damage == "review-input":
        case["review"]["input_hash"] = "0" * 64
    elif damage == "receipt":
        case["raw_hash"] = "bad-hash"
    elif damage == "old-freeze":
        case["freeze_hash"] = "0" * 64
    elif damage == "old-code":
        case["code_hash"] = "0" * 64
    elif damage == "seen-holdout":
        record["cases"][4]["source_manifest"]["unseen_for_profile"] = False
    elif damage == "fixture-holdout":
        record["cases"][4]["source_manifest"]["origin"] = "SYNTHETIC_CONTROL"
    else:
        for item in record["cases"][6:8]:
            item["source_manifest"]["source_id"] = "a"
            item["source_manifest"]["snapshot_hash"] = record["cases"][4]["source_manifest"]["snapshot_hash"]
    assert not QualificationRecord.model_validate(_seal(record)).permits(local_profile_projection(support._input()), "en", NOW)


def test_backend_scope_status_does_not_relabel_the_fast_scoring_model():
    from youtube_intel.runtime_composition import (
        build_production_local_distillation_transport,
        local_distillation_capabilities,
    )
    settings = LocalScoringSettings(model="qwen3:8b", expected_model_digest=support.legacy._DIGEST)
    transport = build_production_local_distillation_transport(settings)
    assert transport.actual_model == settings.model and transport.local_profile_id is None
    states = local_distillation_capabilities()
    assert len(states) == 6 and all(s["status"] == "NOT_QUALIFIED" for s in states)
    assert {s["scope"] for s in states} == {"YT_TIMED", "LOCAL_TIMED", "LOCAL_TEXT"}


def test_once_transport_uses_production_request_and_never_reads_thinking(tmp_path, monkeypatch):
    from datetime import timedelta

    from youtube_intel.distillation import build_local_distillation_request
    from youtube_intel.local_distillation_profile import digest
    from youtube_intel.local_distillation_qualification import LocalExecutionPermit
    value = support._input()
    profile = resolve_profile(PROFILE_ID)
    now = datetime.now(UTC)
    data = {"version": "local-grounding-once-permit-v1", "case_id": "real-deepthink-en", "execution_id": "offline-case",
        "input_hash": value.semantic_hash, "context_hash": "a" * 64,
        "request_hash": digest(build_local_distillation_request(value)),
        "binding": qualification_binding(local_profile_projection(value)),
        "source_manifest_hash": "b" * 64, "capacity_proof_hash": "c" * 64, "runtime_proof_hash": "d" * 64,
        "harness_hash": "e" * 64, "freeze_hash": "f" * 64, "prior_review_hashes": [],
        "issued_at": (now - timedelta(seconds=1)).isoformat(), "expires_at": (now + timedelta(minutes=1)).isoformat()}
    permit = LocalExecutionPermit.model_validate({**data, "permit_hash": digest(data)})
    from youtube_intel.distillation import bind_local_profile
    timed = bind_local_profile(replace(value, content_provider="LOCAL", local_content_context_hash="a" * 64), PROFILE_ID)
    wrong_scope = {**data, "case_id": "local-txt-en", "prior_review_hashes": ["1" * 64, "2" * 64],
        "binding": qualification_binding(local_profile_projection(timed)),
        "request_hash": digest(build_local_distillation_request(timed))}
    wrong = LocalExecutionPermit.model_validate({**wrong_scope, "permit_hash": digest(wrong_scope)})
    assert not wrong.matches(local_profile_projection(timed), timed.semantic_hash,
        digest(build_local_distillation_request(timed)), "en")
    claims, requests = [], []
    capacity_support = _load_module("test_local_model_capacity")
    session, metadata_send, metadata_calls, _ = capacity_support._session(tmp_path, monkeypatch)
    class OpaqueMessage(dict):
        def get(self, key, *args):
            assert key != "thinking"
            return super().get(key, *args)
    class OfflineWire(OllamaLocalDistillationTransport):
        def _request(self, path, *, method, body=None):
            if path != "/api/chat" or body.get("messages") == []:
                return metadata_send(path, method=method, body=body)
            assert path == "/api/chat" and method == "POST"
            requests.append(body)
            return {"model": profile.model, "done": True, "done_reason": "stop",
                "prompt_eval_count": 100, "eval_count": 30, "message": OpaqueMessage(content="{}")}
    transport = OfflineWire(settings=LocalScoringSettings(model=profile.model, expected_model_digest=profile.model_digest),
        local_profile_id=PROFILE_ID, qualification_permit=permit, before_dispatch=lambda _v, request: claims.append(request))
    assert transport.is_authorized_for_normal_production(value) is False
    # A permit plus pure capacity fit still cannot bypass current host readiness.
    assert transport.is_authorized_for_qualification(value) is True
    with pytest.raises(RuntimeError):
        transport.generate(value)
    assert requests == claims == []
    transport._capacity_session = session
    assert transport.prepare_execution(permit.execution_id, value, qualification=True)
    assert transport.ready_for_claim(permit.execution_id, value)
    assert transport.arm_for_claim(permit.execution_id, value)
    metadata_before = list(metadata_calls)
    assert transport.generate(value).raw == "{}"
    assert metadata_calls == metadata_before
    assert claims == requests == [build_local_distillation_request(value)]
    with pytest.raises(RuntimeError):
        transport.generate(value)
    assert len(requests) == 1
    transport.release_readiness()
