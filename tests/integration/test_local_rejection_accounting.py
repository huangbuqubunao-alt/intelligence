"""Offline response failures must remain durable, honest and non-replayable."""
from __future__ import annotations

import io
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from conftest import _load_module

from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.config import LocalScoringSettings
from youtube_intel.distillation import (
    KnownLocalDistillationResponseError,
    LocalDistillationPreDispatchError,
    OllamaLocalDistillationTransport,
    validate_local_grounding_response,
)
from youtube_intel.local_content import LOCAL_SOURCE_ID
from youtube_intel.local_distillation_profile import PROFILE_ID, resolve_profile
from youtube_intel.state import SQLiteStateRepository, StateStoreError

timed = _load_module("test_local_intelligence_timed")
proof = _load_module("test_local_text_input_proof")
MODEL = resolve_profile(PROFILE_ID).model


def _response(**changes):
    return {"model": MODEL, "done": True, "done_reason": "length",
        "prompt_eval_count": 1075, "eval_count": 6144,
        "message": {"content": '{"result":'}, **changes}


def _workspace(tmp_path, monkeypatch, *, response=None, raw=None, error=None):
    repository, provider, cid, ids, transport, _ = timed._local(tmp_path)
    transport.actual_provider, transport.actual_model = "ollama", MODEL
    transport.local_profile_id = PROFILE_ID
    service = timed.support._service(repository, transport)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID,
        video_id=cid, evidence_ids=ids, manual_command_id="rejected-local-response")
    wire = OllamaLocalDistillationTransport(settings=LocalScoringSettings(model=MODEL, expected_model_digest=resolve_profile(PROFILE_ID).model_digest), local_profile_id=PROFILE_ID)

    def generate(value):
        transport.calls += 1
        if error is not None:
            raise error
        if raw is not None:
            payload = wire._request("/api/chat", method="POST", body={})
        else:
            payload = response
        return validate_local_grounding_response(payload, value, duration_ms=123)

    if raw is not None:
        monkeypatch.setattr("youtube_intel.distillation.urllib.request.urlopen",
            lambda *_a, **_k: io.BytesIO(raw))
    monkeypatch.setattr(transport, "generate", generate)
    return repository, provider, cid, transport, service, reservation


def _assert_no_new_evidence_or_insight(repository, provider, before):
    after = proof._tables(repository), proof._files(provider.data_root)
    assert after[1] == before[1]
    assert repository.list_current_intelligence_ids() == ()
    assert {k: v for k, v in after[0].items()
        if k not in {"distillation_execution_checkpoints", "distillation_resource_usage"}} == {
        k: v for k, v in before[0].items()
        if k not in {"distillation_execution_checkpoints", "distillation_resource_usage"}}


@pytest.mark.parametrize("change", [
    {}, {"done": False}, {"done_reason": "stop"}, {"model": "other-real-model"},
    {"prompt_eval_count": None}, {"prompt_eval_count": True}, {"prompt_eval_count": -1},
    {"eval_count": None}, {"eval_count": True}, {"eval_count": -1},
    pytest.param({"prompt_eval_count": 2**63}, id="input-overflow"),
    pytest.param({"eval_count": 2**63}, id="output-overflow"),
    pytest.param({"prompt_eval_count": 2**63 - 1, "eval_count": 2**63 - 1}, id="signed64-paired-boundary"),
    pytest.param({"prompt_eval_count": 2**63 - 1, "eval_count": 1}, id="signed64-input-boundary"),
])
def test_known_local_failure_records_observed_identity_and_reliable_usage(tmp_path, monkeypatch, change):
    response = _response(**change)
    repository, provider, cid, transport, service, reservation = _workspace(tmp_path, monkeypatch, response=response)
    before = proof._tables(repository), proof._files(provider.data_root)
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "REJECTED_OUTPUT" and result.invocation_count == 1
    usage = repository.get_distillation_resource_usage(reservation.execution_id)
    assert usage.actual_provider == "ollama" and usage.actual_model == response["model"]
    reliable_pair = all(type(response[k]) is int and 0 <= response[k] <= 2**63 - 1
        for k in ("prompt_eval_count", "eval_count"))
    assert (usage.input_tokens, usage.output_tokens) == (
        (response["prompt_eval_count"], response["eval_count"]) if reliable_pair else (None, None))
    assert usage.cost_microunits is None and usage.duration_ms == 123
    assert usage.outcome == "LOCAL_RESPONSE_INCOMPLETE_OR_TRUNCATED"
    _assert_no_new_evidence_or_insight(repository, provider, before)
    with pytest.raises(StateStoreError):
        repository.cancel_waiting_model_execution(reservation.execution_id, video_id=cid, now=timed.support.NOW)
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(provider.data_root)
    assert timed.support._service(restarted, transport).continue_reserved_distillation(reservation.execution_id) == result
    assert transport.calls == 1


@pytest.mark.parametrize("response,raw", [
    (_response(model=None), None), (_response(model=""), None),
    (_response(model=True), None), (_response(model="  "), None),
    (None, b"{"), (None, b"[]"), (None, b"\xff"), (None, b"x" * 1_000_001),
], ids=["no-model", "empty-model", "bool-model", "blank-model", "json", "array", "utf8", "oversize"])
def test_unidentified_local_failure_is_durable_unknown_without_invented_model(tmp_path, monkeypatch, response, raw):
    repository, provider, cid, transport, service, reservation = _workspace(tmp_path, monkeypatch, response=response, raw=raw)
    before = proof._tables(repository), proof._files(provider.data_root)
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "AMBIGUOUS" and result.invocation_count == 1
    usage = repository.get_distillation_resource_usage(reservation.execution_id)
    assert usage.actual_provider is None and usage.actual_model is None
    assert usage.input_tokens is None and usage.output_tokens is None and usage.cost_microunits is None
    assert usage.outcome == "TRANSPORT_OUTCOME_UNKNOWN"
    _assert_no_new_evidence_or_insight(repository, provider, before)
    with pytest.raises(StateStoreError):
        repository.cancel_waiting_model_execution(reservation.execution_id, video_id=cid, now=timed.support.NOW)
    assert BackupRestoreService(database=repository._database_path, data_root=provider.data_root).readiness()["ready"]
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(provider.data_root)
    assert timed.support._service(restarted, transport).continue_reserved_distillation(reservation.execution_id) == result
    assert transport.calls == 1


@pytest.mark.parametrize("unknown", [False, True])
def test_rejection_or_unknown_backup_restore_keeps_all_rows_data_and_no_replay(tmp_path, monkeypatch, unknown):
    repository, provider, _cid, transport, service, reservation = _workspace(
        tmp_path, monkeypatch, response=_response(model=None) if unknown else _response())
    assert not BackupRestoreService(database=repository._database_path, data_root=provider.data_root).readiness()["ready"]
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == ("AMBIGUOUS" if unknown else "REJECTED_OUTPUT")
    backup = BackupRestoreService(database=repository._database_path, data_root=provider.data_root)
    assert backup.readiness()["ready"]
    before = proof._tables(repository), proof._files(provider.data_root)
    archive, _ = backup.backup_download(backup.create_backup().backup_id)
    stage = backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(stage.restore_id)
    backup.recover_and_apply_pending_restore()
    assert (proof._tables(repository), proof._files(provider.data_root)) == before
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(provider.data_root)
    assert timed.support._service(restarted, transport).continue_reserved_distillation(reservation.execution_id) == result
    assert transport.calls == 1


def test_other_pending_task_still_blocks_backup_after_local_rejection(tmp_path, monkeypatch):
    repository, provider, cid, _transport, service, reservation = _workspace(tmp_path, monkeypatch, response=_response())
    other_content = provider.import_bytes("other.txt", b"Independent local content retains its own pending task.\n")
    ids = repository.list_canonical_coverage_evidence_ids(other_content.content_id)
    other = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID,
        video_id=other_content.content_id, evidence_ids=ids, manual_command_id="other-user-command")
    assert other.execution_id != reservation.execution_id
    assert service.continue_reserved_distillation(reservation.execution_id).status.value == "REJECTED_OUTPUT"
    assert repository.get_distillation_execution(other.execution_id).status == "PENDING"
    assert not BackupRestoreService(database=repository._database_path, data_root=provider.data_root).readiness()["ready"]


def test_concurrent_failure_completion_is_idempotent_and_cannot_repeat_invocation(tmp_path, monkeypatch):
    repository, _provider, _cid, transport, service, reservation = _workspace(tmp_path, monkeypatch, response=_response())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.continue_reserved_distillation(reservation.execution_id), range(2)))
    assert all(r.invocation_count == 1 and r.status.value == "REJECTED_OUTPUT" for r in results)
    assert transport.calls == 1
    assert repository.get_distillation_resource_usage(reservation.execution_id).invocation_count == 1


def test_validator_never_accesses_thinking_when_preserving_rejected_observations():
    profile = _load_module("test_local_grounding_profile")
    class PublicOnly(dict):
        def get(self, key, default=None):
            assert key != "thinking"
            return super().get(key, default)
    response = _response(message=PublicOnly(content="{"))
    with pytest.raises(KnownLocalDistillationResponseError) as rejected:
        validate_local_grounding_response(response, profile._input(), duration_ms=1)
    assert rejected.value.result.actual_model == MODEL


def test_no_identity_error_itself_never_claims_a_result():
    assert KnownLocalDistillationResponseError("LOCAL_RESPONSE_INVALID").result is None


@pytest.mark.parametrize("failure", [TimeoutError("offline timeout"), LocalDistillationPreDispatchError("offline readiness lost")])
def test_existing_timeout_and_predispatch_unknown_remain_nonreplayable(tmp_path, monkeypatch, failure):
    repository, provider, cid, transport, service, reservation = _workspace(tmp_path, monkeypatch, error=failure)
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "AMBIGUOUS" and result.invocation_count == 1
    usage = repository.get_distillation_resource_usage(reservation.execution_id)
    assert usage.actual_model is None and usage.actual_provider is None
    assert usage.outcome == ("RESERVED_DISPATCH_OUTCOME_UNKNOWN" if isinstance(failure, LocalDistillationPreDispatchError)
        else "TRANSPORT_OUTCOME_UNKNOWN")
    with pytest.raises(StateStoreError):
        repository.cancel_waiting_model_execution(reservation.execution_id, video_id=cid, now=timed.support.NOW)
    assert service.continue_reserved_distillation(reservation.execution_id) == result
    assert transport.calls == 1
    backup = BackupRestoreService(database=repository._database_path, data_root=provider.data_root)
    before = proof._tables(repository), proof._files(provider.data_root)
    archive, _ = backup.backup_download(backup.create_backup().backup_id)
    stage = backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(stage.restore_id)
    backup.recover_and_apply_pending_restore()
    assert (proof._tables(repository), proof._files(provider.data_root)) == before
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(provider.data_root)
    assert timed.support._service(restarted, transport).continue_reserved_distillation(reservation.execution_id) == result
    assert transport.calls == 1


@pytest.mark.parametrize("raw,reason", [
    (b"{", "LOCAL_RESPONSE_INVALID"),
    (json.dumps(_response()).encode(), "LOCAL_RESPONSE_INCOMPLETE_OR_TRUNCATED"),
])
def test_real_transport_retains_precise_failure_diagnostic_without_thinking(monkeypatch, raw, reason):
    profile = _load_module("test_local_grounding_profile")
    wire = OllamaLocalDistillationTransport(settings=LocalScoringSettings(model=MODEL,
        expected_model_digest=resolve_profile(PROFILE_ID).model_digest), local_profile_id=PROFILE_ID)
    wire._capacity_session = SimpleNamespace(consume=lambda *_: None)
    wire._prepared_execution = "offline-fixture"
    monkeypatch.setattr(wire, "is_authorized_for", lambda _: True)
    calls = []
    def respond(*_a, **_k):
        calls.append("local fake wire")
        return io.BytesIO(raw)
    monkeypatch.setattr("youtube_intel.distillation.urllib.request.urlopen", respond)
    with pytest.raises(KnownLocalDistillationResponseError):
        wire.generate(profile._input())
    assert wire.last_grounding_response_error == reason
    assert wire.last_grounding_post_attempted is True and len(calls) == 1


@pytest.mark.parametrize("unknown", [False, True])
def test_harness_persists_exclusive_failure_result_with_precise_diagnostic(tmp_path, monkeypatch, unknown):
    support = _load_module("test_local_grounding_harness")
    harness = support._harness()
    repository, provider, _cid, transport, _service, reservation = _workspace(
        tmp_path, monkeypatch, response=_response(model=None) if unknown else _response())
    audit = tmp_path / "audit"
    audit.mkdir()
    transport.last_grounding_response_error = "LOCAL_RESPONSE_INCOMPLETE_OR_TRUNCATED"
    transport.last_grounding_post_attempted = True
    source = {"origin": "LOCAL_SNAPSHOT", "source_id": LOCAL_SOURCE_ID,
        **{key: "a" * 64 for key in ("snapshot_hash", "summary_hash", "evidence_hash", "policy_hash", "input_hash", "context_hash", "request_hash")},
        "unseen_for_profile": False, "selector_id": "offline-fixture"}
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(source))
    permit = SimpleNamespace(case_id="local-timed-en", execution_id=reservation.execution_id,
        source_manifest_hash=harness.digest(source), input_hash="a" * 64, context_hash="a" * 64,
        request_hash="a" * 64, permit_hash="b" * 64)
    prepared = {"database": str(repository._database_path), "data_root": str(provider.data_root),
        "output_language": "en", "source_id": LOCAL_SOURCE_ID}
    freeze = {"source_manifest_paths": {permit.case_id: str(source_path)}}
    monkeypatch.setattr(harness, "validate_execution_package", lambda *_: (prepared, permit, freeze))
    monkeypatch.setattr(harness, "verify_resources", lambda *_: None)
    monkeypatch.setattr(harness, "OllamaLocalDistillationTransport", lambda **_: transport)
    result = harness.execute_case(audit, tmp_path / "offline-permit", tmp_path / "offline-freeze")
    assert result["outcome"]["status"].value == ("AMBIGUOUS" if unknown else "REJECTED_OUTPUT")
    assert result["production_qualified"] is False and result["local_response_error"] == transport.last_grounding_response_error
    assert result["semantic_acceptance"] == "PENDING_INDEPENDENT_REVIEW"
    written = (audit / "result.json").read_bytes()
    assert json.loads(written)["local_response_error"] == "LOCAL_RESPONSE_INCOMPLETE_OR_TRUNCATED"
    with pytest.raises(FileExistsError):
        harness.execute_case(audit, tmp_path / "offline-permit", tmp_path / "offline-freeze")
    assert (audit / "result.json").read_bytes() == written and transport.calls == 1


@pytest.mark.parametrize("failure", ["malformed", "timeout", "readiness-lost"])
def test_reused_transport_never_attributes_previous_response_to_failed_attempt(monkeypatch, failure):
    import hashlib
    profile = _load_module("test_local_grounding_profile")
    wire = OllamaLocalDistillationTransport(settings=LocalScoringSettings(model=MODEL,
        expected_model_digest=resolve_profile(PROFILE_ID).model_digest), local_profile_id=PROFILE_ID)
    wire._capacity_session = SimpleNamespace(consume=lambda *_: None)
    wire._prepared_execution = "offline-fixture"
    monkeypatch.setattr(wire, "is_authorized_for", lambda _: True)
    response = _response(done_reason="stop", eval_count=50, prompt_eval_count=100, message={"content": "{}"})
    monkeypatch.setattr("youtube_intel.distillation.urllib.request.urlopen",
        lambda *_a, **_k: io.BytesIO(json.dumps(response).encode()))
    assert wire.generate(profile._input()).raw == "{}"
    assert wire.last_grounding_final == "{}" and wire.last_grounding_raw_hash
    if failure == "readiness-lost":
        def unavailable(*_):
            raise RuntimeError("offline readiness expired")
        wire._capacity_session.consume = unavailable
    elif failure == "timeout":
        def timeout(*_a, **_k):
            raise TimeoutError("offline generation timeout")
        monkeypatch.setattr("youtube_intel.distillation.urllib.request.urlopen", timeout)
    else:
        monkeypatch.setattr("youtube_intel.distillation.urllib.request.urlopen", lambda *_a, **_k: io.BytesIO(b"{"))
    with pytest.raises((KnownLocalDistillationResponseError, TimeoutError, LocalDistillationPreDispatchError)):
        wire.generate(profile._input())
    assert wire.last_grounding_final is None and wire.last_grounding_completion is None
    assert wire.last_grounding_raw_hash == (hashlib.sha256(b"{").hexdigest() if failure == "malformed" else None)
    assert wire.last_grounding_post_attempted is (failure != "readiness-lost")
