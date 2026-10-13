"""Explicit local media Intelligence admission; no model/network execution."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.distillation import (
    CloudDistillationAuthorization,
    CloudDistillationPreDispatchError,
    OpenAICloudDistillationTransport,
)
from youtube_intel.local_content import LOCAL_SOURCE_ID, LocalContentProvider
from youtube_intel.state import SQLiteStateRepository, StateStoreError

support = _load_module("test_task022_personalized_distillation")
media = _load_module("test_offline_transcription_jobs")


def _local(tmp_path: Path):
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=support.NOW)
    provider = LocalContentProvider(repository, tmp_path / "data", now=lambda: support.NOW,
                                    transcriber=media.Executor())
    imported = provider.import_bytes("voice.wav", media.audio_bytes())
    assert imported.status == "READY"
    assert repository.get_verified_timed_transcript(video_id=imported.content_id)
    assert repository.current_local_summary_pointer(imported.content_id)
    evidence = repository.list_canonical_coverage_evidence_ids(imported.content_id)
    raw = json.dumps({"result": "NO_NEW_INTELLIGENCE", "evidence": [
        {"evidence_id": eid, "start_ms": repository.resolve_verified_evidence_text(eid).start_ms,
         "end_ms": repository.resolve_verified_evidence_text(eid).end_ms} for eid in evidence]})
    transport = support._FakeTransport(raw)
    return repository, provider, imported.content_id, evidence, transport, support._service(repository, transport)


def test_local_timed_manual_no_new_is_durable(tmp_path: Path):
    repository, _provider, cid, evidence, transport, service = _local(tmp_path)
    repository.update_source_subscription(LOCAL_SOURCE_ID, enabled=False, now=support.NOW)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=evidence, manual_command_id="ordinary-user")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "SUCCEEDED_NO_NEW_INTELLIGENCE"
    assert result.invocation_count == 1 and transport.calls == 1
    assert service.continue_reserved_distillation(reservation.execution_id) == result
    assert transport.calls == 1


def test_local_never_reserves_automatic_intelligence(tmp_path: Path, monkeypatch):
    _repository, _provider, cid, evidence, transport, service = _local(tmp_path)
    from types import SimpleNamespace

    from youtube_intel.state import FilterOutcome
    monkeypatch.setattr(_repository, "current_filter_decision", lambda *args: SimpleNamespace(outcome=FilterOutcome.RELEVANT))
    with pytest.raises(ValueError):
        service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid, evidence_ids=evidence)
    assert transport.calls == 0


def test_cloud_transport_rejects_local_before_payload_or_credential():
    verified = replace(support._verified_input_for_cloud_test(), content_provider="LOCAL")
    calls = []
    transport = OpenAICloudDistillationTransport(
        authorization=CloudDistillationAuthorization(cloud_enabled=True, provider="openai", model="gpt-4.1",
            credential_available=True, provider_available=True,
            qualification_input_hash=verified.semantic_hash, qualification_max_calls=1),
        credential_resolver=lambda: calls.append("credential") or "fixture",
        wire_transport=lambda *args: calls.append("invoke") or {})
    with pytest.raises(CloudDistillationPreDispatchError):
        transport.generate(verified)
    with pytest.raises(CloudDistillationPreDispatchError):
        transport._request(verified)
    assert calls == []


def _app(repository, provider, service, **kwargs):
    from youtube_intel.local_api import LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService
    return LocalApiApplication(repository, ProductOrchestrationService(repository, now=lambda: support.NOW),
        data_root=provider.data_root, distillation_service=service, now=lambda: support.NOW, **kwargs)


def test_api_local_timed_detail_manual_and_cloud_routes(tmp_path: Path, monkeypatch):
    repository, provider, cid, _evidence, transport, service = _local(tmp_path)
    app = _app(repository, provider, service, cloud_distillation_service=service,
               cloud_intelligence_qualified=True, cloud_credential_available=True)
    assert app.handle("GET", f"/api/v1/videos/{cid}")[1]["manual_intelligence_eligible"] is True
    for action in ("review", "confirm"):
        from youtube_intel.local_api import ApiError
        with pytest.raises(ApiError) as rejected:
            app.handle("POST", f"/api/v1/videos/{cid}/cloud-intelligence/{action}", b'{}')
        assert rejected.value.status == 409 and rejected.value.code == "LOCAL_PROVIDER_CAPABILITY_UNAVAILABLE"
    assert transport.calls == 0
    status, payload = app.handle("POST", f"/api/v1/videos/{cid}/intelligence", b'{"command_id":"local-user"}')
    assert status == 202 and payload["execution"]["status"] == "SUCCEEDED_NO_NEW_INTELLIGENCE"
    assert transport.calls == 1


@pytest.mark.parametrize("damage", ["source", "canonical", "summary", "timed", "link", "summary_pointer"])
@pytest.mark.parametrize("positive", [False, True])
def test_local_final_admission_rechecks_source_and_summary(tmp_path: Path, monkeypatch, damage, positive):
    repository, provider, cid, evidence, transport, service = _local(tmp_path)
    context = repository.manual_local_timed_context_hash(LOCAL_SOURCE_ID, cid)
    assert context
    if positive:
        resolved = repository.resolve_verified_evidence_text(evidence[0])
        transport.raw = support._raw(evidence[0], start_ms=resolved.start_ms, end_ms=resolved.end_ms)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=evidence, manual_command_id="mutation-during-execution")
    original = transport.generate
    def mutated(value):
        result = original(value)
        if damage in {"source", "canonical", "summary"}:
            with repository._connect() as connection:
                snapshot = connection.execute("SELECT * FROM content_source_snapshots WHERE content_id=?", (cid,)).fetchone()
            aid = snapshot["snapshot_artifact_id"] if damage == "source" else (
                snapshot["canonical_artifact_id"] if damage == "canonical" else repository.current_local_summary_pointer(cid).artifact_id)
            artifact = repository.get_artifact(aid)
            path = provider.data_root / artifact.relative_path
            path.write_bytes(path.read_bytes() + b" ")
        elif damage == "timed":
            monkeypatch.setattr(repository, "get_verified_timed_transcript", lambda **kwargs: None)
        elif damage == "link":
            with repository._connect() as connection:
                connection.execute("DELETE FROM source_video_links WHERE source_id=? AND video_id=?", (LOCAL_SOURCE_ID, cid))
        else:
            from youtube_intel.extractive_summary import (
                PROVIDER,
                ExtractiveSummaryService,
            )
            from youtube_intel.source_authority import sha256, write_managed
            from youtube_intel.state import (
                ArtifactKind,
                ArtifactWrite,
                RetentionClass,
                StorageRoot,
            )
            summaries = ExtractiveSummaryService(repository, provider.data_root)
            alternative = summaries._result(cid, use_timed_candidates=False)
            payload = alternative.model_dump_json().encode()
            artifact_id = f"summary/{alternative.request_hash}/structured"
            relative = f"transcripts/summaries/{alternative.request_hash}.json"
            write_managed(provider.data_root, relative, payload)
            repository.upsert_artifact(ArtifactWrite(artifact_id=artifact_id, artifact_key=artifact_id,
                video_id=cid, job_id=None, kind=ArtifactKind.ANALYSIS_STRUCTURED, storage_root=StorageRoot.DATA,
                relative_path=relative, content_hash=sha256(payload), provider=PROVIDER, model=alternative.model,
                producer_version="extractive-summary-v1", retention_class=RetentionClass.LONG_LIVED, expires_at=None), now=support.NOW)
            summaries.read(cid, artifact_id)
            assert artifact_id != repository.current_local_summary_pointer(cid).artifact_id
            repository.promote_current_local_summary(video_id=cid, artifact_id=artifact_id, output_language="en", now=support.NOW)
        return result
    monkeypatch.setattr(transport, "generate", mutated)
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "REJECTED_OUTPUT"
    assert transport.calls == 1
    assert repository.list_current_intelligence_ids() == ()
    assert service.continue_reserved_distillation(reservation.execution_id) == result
    assert transport.calls == 1


def test_local_reservation_rejects_text_foreign_source_and_unbound_storage(tmp_path: Path):
    repository, provider, cid, evidence, transport, service = _local(tmp_path)
    other, _ = support._source_and_video(repository)
    repository.link_source_video(other, cid, discovered_at=support.NOW)
    with pytest.raises(ValueError):
        service.reserve_distillation_execution(source_id=other, video_id=cid, evidence_ids=evidence, manual_command_id="foreign")
    text = provider.import_bytes("notes.txt", b"The local text remains a real text range.\n")
    with pytest.raises(ValueError):
        service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=text.content_id,
            evidence_ids=repository.list_canonical_coverage_evidence_ids(text.content_id), manual_command_id="text")
    restarted = SQLiteStateRepository(repository._database_path)
    assert restarted.manual_local_timed_context_hash(LOCAL_SOURCE_ID, cid) is None
    assert transport.calls == 0


@pytest.mark.parametrize("provider,model,cls", [
    ("openai", "gpt-4.1", "OpenAICloudDistillationTransport"),
    ("nvidia_nim", "moonshotai/kimi-k3", "NvidiaNimCloudDistillationTransport"),
    ("moonshot", "kimi-k2.6", "MoonshotK26CloudDistillationTransport"),
    ("moonshot", "kimi-k2.6", "MoonshotK26NonThinkingCloudDistillationTransport"),
])
@pytest.mark.parametrize("marker", ["LOCAL", "default-YOUTUBE"])
def test_all_cloud_transports_refuse_local_before_credentials_and_payload(provider, model, cls, marker):
    import youtube_intel.distillation as distillation
    verified = replace(support._verified_input_for_cloud_test(), selected_provider=provider,
        selected_model=model, video_id="local-" + "a" * 64,
        content_provider="LOCAL" if marker == "LOCAL" else "YOUTUBE")
    calls = []
    transport = getattr(distillation, cls)(
        authorization=CloudDistillationAuthorization(cloud_enabled=True, provider=provider, model=model,
            credential_available=True, provider_available=True,
            qualification_input_hash=verified.semantic_hash, qualification_max_calls=1),
        credential_resolver=lambda: calls.append("credential") or "fixture",
        wire_transport=lambda *args: calls.append("invoke") or {})
    assert not transport.is_authorized_for(verified)
    with pytest.raises(CloudDistillationPreDispatchError):
        transport.generate(verified)
    with pytest.raises(CloudDistillationPreDispatchError):
        transport._request(verified)
    assert calls == []


def test_cloud_service_refuses_local_before_composing_payload(tmp_path: Path, monkeypatch):
    repository, _provider, cid, evidence, transport, _service = _local(tmp_path)
    transport.actual_provider, transport.actual_model = "openai", "gpt-4.1"
    service = support._service(repository, transport)
    calls = []
    monkeypatch.setattr(service, "_compose_verified_input", lambda value: calls.append("payload"))
    with pytest.raises(ValueError):
        service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
            evidence_ids=evidence, manual_command_id="local-cloud")
    assert calls == [] and transport.calls == 0
    assert repository.latest_distillation_execution_for_video(cid) is None


@pytest.mark.parametrize("gate", ["model", "budget"])
def test_local_wait_gates_restart_and_model_cancel(tmp_path: Path, gate):
    repository, provider, cid, evidence, transport, service = _local(tmp_path)
    transport.actual_provider, transport.actual_model = "ollama", "qwen3:8b"
    service = support._service(repository, transport)
    if gate == "model":
        transport.available = False
    else:
        service = support._service(repository, transport, support._FakeBudget(False))
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=evidence, manual_command_id="waiting")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == ("WAITING_MODEL" if gate == "model" else "WAITING_BUDGET")
    assert result.invocation_count == 0 and transport.calls == 0
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(provider.data_root)
    if gate == "model":
        cancelled = repository.cancel_waiting_model_execution(reservation.execution_id, video_id=cid, now=support.NOW)
        assert restarted.get_distillation_execution(reservation.execution_id).status == "CANCELLED"
        assert repository.cancel_waiting_model_execution(reservation.execution_id, video_id=cid, now=support.NOW) == cancelled
    else:
        with pytest.raises(StateStoreError):
            repository.cancel_waiting_model_execution(reservation.execution_id, video_id=cid, now=support.NOW)
    assert support._service(restarted, transport).continue_reserved_distillation(reservation.execution_id).invocation_count == 0
    assert transport.calls == 0


def test_local_unknown_execution_is_not_redispatched(tmp_path: Path, monkeypatch):
    repository, provider, cid, evidence, transport, service = _local(tmp_path)
    def unknown(_value):
        transport.calls += 1
        raise RuntimeError("isolated unknown fixture")
    monkeypatch.setattr(transport, "generate", unknown)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=evidence, manual_command_id="unknown")
    assert service.continue_reserved_distillation(reservation.execution_id).status.value == "AMBIGUOUS"
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(provider.data_root)
    assert support._service(restarted, transport).continue_reserved_distillation(reservation.execution_id).status.value == "AMBIGUOUS"
    assert transport.calls == 1


def test_local_concurrent_manual_reservation_has_one_identity(tmp_path: Path):
    from concurrent.futures import ThreadPoolExecutor
    repository, _provider, cid, evidence, transport, service = _local(tmp_path)
    def reserve(_):
        return service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
            evidence_ids=evidence, manual_command_id="same-click").execution_id
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(reserve, range(2)))
    assert ids[0] == ids[1]
    assert service.continue_reserved_distillation(ids[0]).status.value == "SUCCEEDED_NO_NEW_INTELLIGENCE"
    assert transport.calls == 1


def test_old_video_qualification_does_not_qualify_local_content(tmp_path: Path):
    from youtube_intel.config import LocalScoringSettings
    from youtube_intel.distillation import OllamaLocalDistillationTransport
    _repository, _provider, cid, evidence, _transport, service = _local(tmp_path)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=evidence, manual_command_id="qualification-is-separate")
    _, value = service._reserved_command_from_record(service._repository.get_distillation_execution(reservation.execution_id))
    transport = OllamaLocalDistillationTransport(settings=LocalScoringSettings(model="qwen3:8b", expected_model_digest=OllamaLocalDistillationTransport._DIGEST), production_qualified=True)
    value = replace(value, selected_provider="ollama", selected_model=transport.actual_model)
    assert transport.is_authorized_for_normal_production(replace(value, content_provider="YOUTUBE"))
    assert not transport.is_authorized_for_normal_production(value)


def test_local_positive_card_has_real_timing_content_identity_without_external_links(tmp_path: Path):
    repository, provider, cid, evidence, transport, service = _local(tmp_path)
    resolved = repository.resolve_verified_evidence_text(evidence[0])
    transport.raw = support._raw(evidence[0], start_ms=resolved.start_ms, end_ms=resolved.end_ms)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=evidence, manual_command_id="positive-card")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "SUCCEEDED" and transport.calls == 1
    app = _app(repository, provider, service)
    status, detail = app.handle("GET", f"/api/v1/intelligence/{result.intelligence_id}")
    assert status == 200
    card = detail["intelligence"]["card"]
    assert card["source_url"] is None and card["original_video_url"] is None
    assert card["video_id"] == cid and card["source_id"] == LOCAL_SOURCE_ID
    assert card["evidence_links"][0]["start_ms"] == 125
    assert card["evidence_links"][0]["end_ms"] == 1750
    assert app.handle("GET", f"/api/v1/videos/{card['video_id']}")[1]["video"]["video_id"] == cid
    assert repository.resolve_verified_evidence_text(card["evidence_links"][0]["evidence_id"]).excerpt == resolved.excerpt


def test_existing_video_receipt_leaves_local_waiting_without_runtime_request(tmp_path: Path, monkeypatch):
    from youtube_intel.config import LocalScoringSettings
    from youtube_intel.distillation import (
        OllamaLocalDistillationTransport,
        PersonalizedDistillationService,
    )
    from youtube_intel.source_policy import SourcePolicyApplicationService
    repository, _provider, cid, evidence, _transport, _service = _local(tmp_path)
    transport = OllamaLocalDistillationTransport(settings=LocalScoringSettings(model="qwen3:8b",
        expected_model_digest=OllamaLocalDistillationTransport._DIGEST), production_qualified=True)
    calls = []
    monkeypatch.setattr(transport, "_request", lambda *args, **kwargs: calls.append("runtime-http") or {})
    service = PersonalizedDistillationService(repository, SourcePolicyApplicationService(repository, now=lambda: support.NOW),
        transport, support._FakeBudget(True), now=lambda: support.NOW)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=evidence, manual_command_id="old-receipt")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "WAITING_MODEL" and result.invocation_count == 0
    assert calls == []


def test_reserved_local_context_change_is_rejected_before_invocation(tmp_path: Path):
    repository, provider, cid, evidence, transport, service = _local(tmp_path)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=evidence, manual_command_id="before-dispatch")
    pointer = repository.current_local_summary_pointer(cid)
    artifact = repository.get_artifact(pointer.artifact_id)
    path = provider.data_root / artifact.relative_path
    path.write_bytes(path.read_bytes() + b" ")
    assert service.continue_reserved_distillation(reservation.execution_id).status.value == "REJECTED_EVIDENCE"
    assert transport.calls == 0


@pytest.mark.parametrize("cancel", [False, True])
def test_local_terminal_backup_restore_preserves_all_tables_and_data(tmp_path: Path, cancel):
    import hashlib

    from youtube_intel.backup_restore import BackupRestoreService
    repository, provider, cid, evidence, transport, service = _local(tmp_path)
    if cancel:
        transport.actual_provider, transport.actual_model, transport.available = "ollama", "qwen3:8b", False
        service = support._service(repository, transport)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=evidence, manual_command_id="backup-roundtrip")
    service.continue_reserved_distillation(reservation.execution_id)
    backup = BackupRestoreService(database=repository._database_path, data_root=provider.data_root)
    if cancel:
        assert not backup.readiness()["ready"]
        repository.cancel_waiting_model_execution(reservation.execution_id, video_id=cid, now=support.NOW)
    assert backup.readiness()["ready"]
    def tables():
        with repository._connect() as connection:
            return {name: sorted([tuple(row) for row in connection.execute('SELECT * FROM "' + name + '"')], key=repr)
                for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
    def files():
        return {path.relative_to(provider.data_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in provider.data_root.rglob("*") if path.is_file()}
    original_tables, original_files = tables(), files()
    created = backup.create_backup()
    archive, _ = backup.backup_download(created.backup_id)
    staged = backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert tables() == original_tables
    assert files() == original_files
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(provider.data_root)
    assert restarted.manual_local_timed_context_hash(LOCAL_SOURCE_ID, cid)
    result = support._service(restarted, transport).continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == ("CANCELLED" if cancel else "SUCCEEDED_NO_NEW_INTELLIGENCE")
    assert transport.calls == (0 if cancel else 1)


@pytest.mark.parametrize("action", ["review", "authorize", "continue"])
def test_historical_local_cloud_reservation_never_builds_payload_or_claims_dispatch(tmp_path: Path, monkeypatch, action):
    from youtube_intel.state import DistillationExecutionWrite
    repository, _provider, cid, _evidence, transport, _service = _local(tmp_path)
    transport.actual_provider, transport.actual_model = "openai", "gpt-4.1"
    service = support._service(repository, transport)
    execution_id = "historical-local-cloud-fixture"
    repository.reserve_distillation_execution(DistillationExecutionWrite(execution_id=execution_id,
        source_id=LOCAL_SOURCE_ID, video_id=cid, reason="MANUAL_CONTENT:historical",
        use_case="PERSONALIZED_INTELLIGENCE", selected_provider="openai", selected_model="gpt-4.1"), now=support.NOW)
    payload_reads = []
    monkeypatch.setattr(repository, "resolve_verified_evidence_text", lambda value: payload_reads.append(value))
    if action == "continue":
        result = service.continue_reserved_distillation(execution_id)
        assert result.status.value == "REJECTED_EVIDENCE" and result.invocation_count == 0
    else:
        method = service.review_reserved_cloud_execution if action == "review" else service.authorize_reserved_cloud_execution
        with pytest.raises(ValueError):
            method(execution_id)
    assert payload_reads == [] and transport.calls == 0
    assert repository.get_distillation_execution(execution_id).invocation_count == 0
    with repository._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM distillation_openai_cloud_authorizations").fetchone()[0] == 0
