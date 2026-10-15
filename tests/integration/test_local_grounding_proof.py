"""Offline transport proves provenance compatibility, never model quality."""
from __future__ import annotations

import json

import pytest
from conftest import _load_module

from youtube_intel.distillation import (
    LocalTextDistillationProfile,
    build_local_distillation_request,
    verify_local_text_input_proof,
)
from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
from youtube_intel.local_distillation_profile import PROFILE_ID, resolve_profile

text = _load_module("test_local_intelligence_text")
_legacy_workspace = text._workspace


def _workspace(tmp_path):
    repository, provider, cid, ids, refs, transport, _ = _legacy_workspace(tmp_path)
    transport.actual_provider = "ollama"
    transport.actual_model = resolve_profile(PROFILE_ID).model
    transport.local_profile_id = PROFILE_ID
    return repository, provider, cid, ids, refs, transport, text.support._service(repository, transport)


def test_new_text_execution_binds_profile_and_remains_readable_without_qualification(tmp_path):
    repository, _provider, cid, ids, refs, transport, service = _workspace(tmp_path)
    transport.raw = json.dumps(text._positive(refs))
    reservation = service.reserve_distillation_execution(source_id=text.LOCAL_SOURCE_ID,
        video_id=cid, evidence_ids=ids, manual_command_id="grounding-proof")
    with repository._connect() as connection:
        proof = verify_local_text_input_proof(repository, connection, reservation.execution_id, require_current=True)
    value = json.loads(proof.input_json)
    assert value["profile"]["local_profile_id"] == PROFILE_ID
    assert proof.profile_hash != LocalTextDistillationProfile.identity_hash()
    assert proof.profile_hash == value["profile"]["profile_hash"]
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "SUCCEEDED"
    assert transport.calls == 1
    verified = transport.commands[0]
    assert verified.local_profile_id == PROFILE_ID and verified.local_profile_hash == proof.profile_hash
    request = build_local_distillation_request(verified)
    assert request["format"] == LocalTextDistillationProfile.schema()
    assert AuthoritativeIntelligenceReader(repository).read_current_card(result.intelligence_id).video_id == cid


def test_old_and_new_text_reservations_are_distinct_and_both_proofs_verify(tmp_path):
    repository, _provider, cid, ids, _refs, transport, service = text._workspace(tmp_path)
    old = service.reserve_distillation_execution(source_id=text.LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="old")
    assert service.continue_reserved_distillation(old.execution_id).status.value == "SUCCEEDED_NO_NEW_INTELLIGENCE"
    transport.actual_provider, transport.actual_model, transport.local_profile_id = "ollama", resolve_profile(PROFILE_ID).model, PROFILE_ID
    new_service = text.support._service(repository, transport)
    new = new_service.reserve_distillation_execution(source_id=text.LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="new")
    assert old.execution_id != new.execution_id
    with repository._connect() as connection:
        old_proof = verify_local_text_input_proof(repository, connection, old.execution_id)
        new_proof = verify_local_text_input_proof(repository, connection, new.execution_id)
    assert old_proof.profile_hash == LocalTextDistillationProfile.identity_hash()
    assert new_proof.profile_hash != old_proof.profile_hash


@pytest.mark.parametrize("damage", ["profile-id", "profile-hash", "missing-context"])
def test_new_text_preparation_rejects_untrusted_profile_changes(tmp_path, damage):
    from dataclasses import replace
    repository, _provider, cid, ids, _refs, _transport, service = _workspace(tmp_path)
    reservation = service.reserve_distillation_execution(source_id=text.LOCAL_SOURCE_ID,
        video_id=cid, evidence_ids=ids, manual_command_id="tamper")
    record = repository.get_distillation_execution(reservation.execution_id)
    _, value = service._reserved_command_from_record(record)
    changes = {"profile-id": {"local_profile_id": "future"}, "profile-hash": {"local_profile_hash": "0" * 64},
        "missing-context": {"local_content_context_hash": None}}
    with pytest.raises(ValueError):
        build_local_distillation_request(replace(value, **changes[damage]))


@pytest.mark.parametrize("damage", ["proof", "card", "ledger", "projection", "proof+card", "proof+ledger",
    "card+ledger", "proof+card+ledger", "proof+checkpoint", "proof+card+checkpoint",
    "proof+ledger+checkpoint", "proof+card+ledger+checkpoint"])
def test_new_profile_reuses_complete_forged_backup_and_reverse_read_matrix(tmp_path, monkeypatch, damage):
    """Same security assertions as the accepted 39 matrix, with the new profile."""
    original = _load_module("test_local_text_input_proof")
    monkeypatch.setattr(original.text, "_workspace", _workspace)
    original.test_schema39_forged_archive_with_rehashed_database_is_rejected_before_live_replacement(tmp_path, damage)


@pytest.mark.parametrize("positive", [False, True])
def test_new_timed_profile_uses_ordinary_service_markers_and_sealed_identity(tmp_path, positive):
    timed = _load_module("test_local_intelligence_timed")
    repository, _provider, cid, ids, transport, _ = timed._local(tmp_path)
    transport.actual_provider, transport.actual_model = "ollama", resolve_profile(PROFILE_ID).model
    transport.local_profile_id = PROFILE_ID
    if positive:
        evidence = repository.resolve_verified_evidence_text(ids[0])
        payload = json.loads(timed.support._raw(ids[0], start_ms=evidence.start_ms, end_ms=evidence.end_ms))
        transport.raw = json.dumps({"result": "INTELLIGENCE", **payload})
    service = timed.support._service(repository, transport)
    reservation = service.reserve_distillation_execution(source_id=timed.LOCAL_SOURCE_ID,
        video_id=cid, evidence_ids=ids, manual_command_id="new-timed-profile")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == ("SUCCEEDED" if positive else "SUCCEEDED_NO_NEW_INTELLIGENCE")
    assert transport.calls == result.invocation_count == 1
    value = transport.commands[0]
    assert value.local_profile_id == PROFILE_ID and value.wire_version is None
    from youtube_intel.distillation import local_profile_projection
    assert local_profile_projection(value)["scope"] == "LOCAL_TIMED"
    assert build_local_distillation_request(value)["think"] is True
