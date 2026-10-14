"""Offline fixtures only: these tests never qualify a real local model."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.local_content import LOCAL_SOURCE_ID, LocalContentProvider
from youtube_intel.state import SQLiteStateRepository

support = _load_module("test_task022_personalized_distillation")


def _workspace(tmp_path: Path, filename="notes.txt"):
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=support.NOW)
    provider = LocalContentProvider(repository, tmp_path / "data", now=lambda: support.NOW)
    imported = provider.import_bytes(filename, "材料🙂 e\u0301第一行。\nSecond line reports a tentative result.\n第三行保留条件。".encode())
    assert imported.status == "READY"
    ids = repository.list_canonical_coverage_evidence_ids(imported.content_id)
    refs = []
    for eid in ids:
        text = repository.resolve_verified_evidence_text(eid)
        refs.append({"evidence_id": eid, "locator_type": "TEXT_RANGE", "start_ms": None, "end_ms": None,
                     "start_offset": text.start_offset, "end_offset": text.end_offset,
                     "start_line": text.start_line, "end_line": text.end_line,
                     "source_content_hash": text.source_content_hash,
                     "canonical_text_hash": text.timed_transcript_hash, "excerpt_hash": text.excerpt_hash})
    transport = support._FakeTransport(json.dumps({"wire_version": "local-text-distillation-v1", "result": "NO_NEW_INTELLIGENCE", "evidence": refs}))
    return repository, provider, imported.content_id, ids, refs, transport, support._service(repository, transport)


@pytest.mark.parametrize("filename", ["notes.txt", "notes.md"])
def test_text_manual_no_new_uses_real_codepoints_and_null_times(tmp_path, filename):
    repository, _provider, cid, ids, refs, transport, service = _workspace(tmp_path, filename)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="text-fixture")
    assert reservation.execution_id.startswith("distillation:local-text-v1:")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "SUCCEEDED_NO_NEW_INTELLIGENCE"
    assert transport.calls == 1
    value = transport.commands[0]
    assert value.wire_version == "local-text-distillation-v1"
    assert all(e.locator_type == "TEXT_RANGE" and e.start_ms is None and e.end_ms is None for e in value.evidence)
    assert value.evidence[0].start_offset == refs[0]["start_offset"]
    assert repository.get_verified_timed_transcript(video_id=cid) is None
    artifact = repository.get_artifact(repository.get_evidence(ids[0]).artifact_id)
    canonical = (_provider.data_root / artifact.relative_path).read_text()
    assert "🙂" in canonical and "e\u0301" in canonical
    assert len(canonical.encode()) > len(canonical)
    for item in value.evidence:
        assert canonical[item.start_offset:item.end_offset] == item.excerpt
        assert item.start_line == 1 + canonical[:item.start_offset].count("\n")
        assert item.end_line == 1 + canonical[:item.end_offset - 1].count("\n")
    assert service.continue_reserved_distillation(reservation.execution_id) == result
    assert transport.calls == 1


def _positive(refs):
    return {"wire_version": "local-text-distillation-v1", "result": "INTELLIGENCE",
        "core_conclusion": "The source reports a tentative result, requiring further verification.",
        "user_relevant_information": [], "important_new_information": [], "meaningful_details": [],
        "filtered_noise": [], "claim_kind": "EVIDENCE_BACKED_STATEMENT",
        "evidence": [{**ref, "stance": "supporting"} for ref in refs]}


def test_text_positive_card_persistent_reader_and_api(tmp_path):
    from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
    from youtube_intel.local_api import LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService
    repository, provider, cid, ids, refs, transport, service = _workspace(tmp_path)
    transport.raw = json.dumps(_positive(refs))
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="positive-fixture")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "SUCCEEDED"
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(provider.data_root)
    card = AuthoritativeIntelligenceReader(restarted).read_current_card(result.intelligence_id)
    assert card.video_id == cid
    assert card.verified.evidence_ids == tuple(sorted(ids))
    app = LocalApiApplication(restarted, ProductOrchestrationService(restarted, now=lambda: support.NOW),
        data_root=provider.data_root, now=lambda: support.NOW)
    detail = app.handle("GET", f"/api/v1/intelligence/{result.intelligence_id}")[1]["intelligence"]["card"]
    assert detail["source_url"] is None and detail["original_video_url"] is None
    assert detail["evidence_links"][0]["locator_type"] == "TEXT_RANGE"
    assert detail["evidence_links"][0]["start_ms"] is None
    assert detail["evidence_links"][0]["start_line"] >= 1


@pytest.mark.parametrize("field,bad", [("start_ms", 0), ("end_ms", 0), ("start_offset", -1),
    ("end_offset", 100000), ("start_offset", True), ("start_line", 0), ("end_line", 1000),
    ("locator_type", "TIMED_MEDIA"), ("source_content_hash", "0" * 64),
    ("canonical_text_hash", "0" * 64), ("excerpt_hash", "0" * 64), ("evidence_id", "foreign")])
@pytest.mark.parametrize("positive", [True, False])
def test_text_wire_rejects_fabricated_binding(tmp_path, field, bad, positive):
    repository, _provider, cid, ids, refs, transport, service = _workspace(tmp_path)
    payload = _positive(refs) if positive else {"wire_version": "local-text-distillation-v1", "result": "NO_NEW_INTELLIGENCE", "evidence": refs}
    payload["evidence"][0][field] = bad
    transport.raw = json.dumps(payload)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="invalid-fixture")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "REJECTED_OUTPUT" and transport.calls == 1
    assert repository.list_current_intelligence_ids() == ()


@pytest.mark.parametrize("damage", ["missing", "duplicate", "legacy", "version", "mixed"])
def test_text_no_new_requires_exact_version_and_complete_coverage(tmp_path, damage):
    _repo, _provider, cid, ids, refs, transport, service = _workspace(tmp_path)
    payload = json.loads(transport.raw)
    if damage == "missing":
        payload["evidence"].pop()
    elif damage == "duplicate":
        payload["evidence"][1] = payload["evidence"][0]
    elif damage == "legacy":
        del payload["wire_version"]
    elif damage == "version":
        payload["wire_version"] = "local-text-distillation-v2"
    else:
        payload["evidence"][0] = {"evidence_id": refs[0]["evidence_id"], "start_ms": 0, "end_ms": 1}
    transport.raw = json.dumps(payload)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="invalid-coverage")
    assert service.continue_reserved_distillation(reservation.execution_id).status.value == "REJECTED_OUTPUT"
    assert transport.calls == 1


@pytest.mark.parametrize("damage", ["source", "canonical", "summary", "link", "summary_pointer"])
@pytest.mark.parametrize("positive", [True, False])
def test_text_final_cas_rejects_changes(tmp_path, monkeypatch, damage, positive):
    repository, provider, cid, ids, refs, transport, service = _workspace(tmp_path)
    if positive:
        transport.raw = json.dumps(_positive(refs))
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="cas")
    generate = transport.generate
    def mutate(value):
        result = generate(value)
        with repository._connect() as connection:
            snapshot = connection.execute("SELECT * FROM content_source_snapshots WHERE content_id=?", (cid,)).fetchone()
            if damage == "link":
                connection.execute("DELETE FROM source_video_links WHERE source_id=? AND video_id=?", (LOCAL_SOURCE_ID, cid))
            elif damage == "summary_pointer":
                connection.execute("DELETE FROM current_content_summaries WHERE video_id=?", (cid,))
            else:
                aid = snapshot["snapshot_artifact_id"] if damage == "source" else (
                    snapshot["canonical_artifact_id"] if damage == "canonical" else repository.current_local_summary_pointer(cid).artifact_id)
                artifact = repository.get_artifact(aid)
                path = provider.data_root / artifact.relative_path
                path.write_bytes(path.read_bytes() + b" ")
        return result
    monkeypatch.setattr(transport, "generate", mutate)
    assert service.continue_reserved_distillation(reservation.execution_id).status.value == "REJECTED_OUTPUT"
    assert repository.list_current_intelligence_ids() == ()
    assert transport.calls == 1


@pytest.mark.parametrize("damage", ["prefix", "input_hash", "context_hash", "status", "revision", "ledger", "missing", "duplicate"])
def test_text_reader_requires_exact_unique_execution_and_ledger(tmp_path, monkeypatch, damage):
    from dataclasses import replace

    from youtube_intel.intelligence_read import (
        AuthoritativeIntelligenceReader,
        IntelligenceReadRejected,
    )
    repository, _provider, cid, ids, refs, transport, service = _workspace(tmp_path)
    transport.raw = json.dumps(_positive(refs))
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="reader")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "SUCCEEDED"
    execution = repository.get_distillation_execution(reservation.execution_id)
    if damage == "ledger":
        ledger = repository.get_distillation_resource_usage(reservation.execution_id)
        monkeypatch.setattr(repository, "get_distillation_resource_usage", lambda _: replace(ledger, actual_model="foreign"))
    elif damage in {"missing", "duplicate"}:
        if damage == "missing":
            monkeypatch.setattr(repository, "get_distillation_execution", lambda _: None)
        else:
            # Independent normal execution mapped to the same revision in an adversarial DB.
            # The clone is confined to this temporary test database.
            with repository._connect() as connection:
                connection.execute("INSERT INTO distillation_execution_checkpoints (execution_id,source_id,video_id,reason,use_case,selected_provider,selected_model,status,budget_state,invocation_count,intelligence_id,revision_id,created_at,updated_at,output_language) SELECT 'duplicate-fixture',source_id,video_id,reason,use_case,selected_provider,selected_model,status,budget_state,invocation_count,intelligence_id,revision_id,created_at,updated_at,output_language FROM distillation_execution_checkpoints WHERE execution_id=?", (execution.execution_id,))
    else:
        changes = {"status": "AMBIGUOUS"} if damage == "status" else {"revision_id": "foreign"} if damage == "revision" else {}
        if damage in {"prefix", "input_hash", "context_hash"}:
            parts = execution.execution_id.split(":")
            parts[{"prefix": 1, "input_hash": 2, "context_hash": 3}[damage]] = "foreign" if damage == "prefix" else "0" * 64
            changes = {"execution_id": ":".join(parts)}
        monkeypatch.setattr(repository, "get_distillation_execution", lambda _: replace(execution, **changes))
    with pytest.raises(IntelligenceReadRejected):
        AuthoritativeIntelligenceReader(repository).read_current_card(result.intelligence_id)
    with pytest.raises(IntelligenceReadRejected):
        AuthoritativeIntelligenceReader(repository).read_current(result.intelligence_id)
    from youtube_intel.saved_intelligence import (
        SavedIntelligenceService,
        SaveIntelligence,
    )
    from youtube_intel.topic import (
        TopicApplicationService,
        TopicAssociationKind,
        TopicReadRejected,
    )
    saved = SavedIntelligenceService(repository, now=lambda: support.NOW)
    with pytest.raises(IntelligenceReadRejected):
        saved.save(SaveIntelligence(intelligence_id=result.intelligence_id))
    # An existing saved relation must become unavailable after the same damage.
    repository.save_intelligence_relation(intelligence_id=result.intelligence_id,
        expected_revision_id=result.revision_id, now=support.NOW)
    assert saved.list_saved().items[0].verified is None
    topics = TopicApplicationService(repository, now=lambda: support.NOW)
    topic = topics.create_topic(command_id="invalid-topic", name="Invalid text fixture")
    with pytest.raises(TopicReadRejected):
        topics.associate_intelligence(topic_id=topic.topic_id, intelligence_id=result.intelligence_id,
            kind=TopicAssociationKind.NEW_INFORMATION)
    assert repository.list_topic_memberships(topic.topic_id) == ()


@pytest.mark.parametrize("positive", [True, False])
def test_text_save_topic_backup_restore_all_tables_and_data(tmp_path, positive):
    import hashlib

    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
    from youtube_intel.saved_intelligence import (
        SavedIntelligenceService,
        SaveIntelligence,
    )
    from youtube_intel.topic import TopicApplicationService, TopicAssociationKind
    repository, provider, cid, ids, refs, transport, service = _workspace(tmp_path)
    if positive:
        transport.raw = json.dumps(_positive(refs))
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="backup")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == ("SUCCEEDED" if positive else "SUCCEEDED_NO_NEW_INTELLIGENCE")
    if positive:
        saved = SavedIntelligenceService(repository, now=lambda: support.NOW)
        saved.save(SaveIntelligence(intelligence_id=result.intelligence_id))
        topics = TopicApplicationService(repository, now=lambda: support.NOW)
        topic = topics.create_topic(command_id="text-topic", name="Text fixture topic")
        membership = topics.associate_intelligence(topic_id=topic.topic_id,
            intelligence_id=result.intelligence_id, kind=TopicAssociationKind.NEW_INFORMATION)
        assert membership.revision_id == result.revision_id
        assert membership.evidence_ids == tuple(sorted(ids))
        assert saved.list_saved().items[0].verified.revision_id == result.revision_id
    backup = BackupRestoreService(database=repository._database_path, data_root=provider.data_root)
    assert backup.readiness()["ready"]
    def tables():
        with repository._connect() as connection:
            return {name: sorted([tuple(row) for row in connection.execute('SELECT * FROM "' + name + '"')], key=repr)
                for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
    def files():
        return {path.relative_to(provider.data_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in provider.data_root.rglob("*") if path.is_file()}
    before = tables(), files()
    created = backup.create_backup()
    archive, _ = backup.backup_download(created.backup_id)
    staged = backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert (tables(), files()) == before
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(provider.data_root)
    assert support._service(restarted, transport).continue_reserved_distillation(reservation.execution_id) == result
    assert transport.calls == 1
    if positive:
        assert AuthoritativeIntelligenceReader(restarted).read_current_card(result.intelligence_id).video_id == cid
        assert SavedIntelligenceService(restarted).list_saved().items[0].verified.revision_id == result.revision_id


def test_independent_text_profile_prepare_has_no_execution_or_old_receipt_authority(tmp_path, monkeypatch):
    from dataclasses import replace

    from scripts.prepare_readiness_local_text import prepare_case, prepare_profile
    from youtube_intel.config import LocalScoringSettings
    from youtube_intel.distillation import (
        LocalTextDistillationProfile,
        OllamaLocalDistillationTransport,
    )
    repository, _provider, cid, ids, _refs, fixture, _service = _workspace(tmp_path)
    fixture.actual_provider, fixture.actual_model = "ollama", LocalTextDistillationProfile.MODEL
    service = support._service(repository, fixture)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="freeze")
    _, value = service._reserved_command_from_record(repository.get_distillation_execution(reservation.execution_id))
    prepared = prepare_case(value)
    assert prepared["verified_input_hash"] == reservation.execution_id.split(":")[2]
    assert fixture.calls == 0
    assert prepared["real_model_calls"] == 0
    assert prepare_profile()["production_qualified"] is False
    assert prepare_profile()["execution_authority"] == "NONE"
    assert prepared["request_projection"]["format"] != OllamaLocalDistillationTransport._SCHEMA
    assert not hasattr(LocalTextDistillationProfile, "generate")
    old = OllamaLocalDistillationTransport(settings=LocalScoringSettings(model="qwen3:8b",
        expected_model_digest=OllamaLocalDistillationTransport._DIGEST), production_qualified=True)
    calls = []
    monkeypatch.setattr(old, "_request", lambda *args, **kwargs: calls.append("runtime") or {})
    value = replace(value, selected_provider="ollama", selected_model="qwen3:8b")
    assert not old.is_authorized_for(value)
    assert not old.is_authorized_for_normal_production(value)
    assert not old.is_authorized_for_qualification(value)
    with pytest.raises(RuntimeError):
        old.generate(value)
    assert calls == []


@pytest.mark.parametrize("gate", ["model", "budget", "unknown"])
def test_text_wait_cancel_restart_and_unknown_are_never_redispatched(tmp_path, monkeypatch, gate):
    from youtube_intel.state import StateStoreError
    repository, provider, cid, ids, _refs, transport, service = _workspace(tmp_path)
    if gate == "model":
        transport.actual_provider, transport.actual_model, transport.available = "ollama", "qwen3:8b", False
        service = support._service(repository, transport)
    elif gate == "budget":
        service = support._service(repository, transport, support._FakeBudget(False))
    else:
        def unknown(value):
            transport.calls += 1
            raise RuntimeError("offline unknown fixture")
        monkeypatch.setattr(transport, "generate", unknown)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="gate")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == {"model": "WAITING_MODEL", "budget": "WAITING_BUDGET", "unknown": "AMBIGUOUS"}[gate]
    if gate == "model":
        repository.cancel_waiting_model_execution(reservation.execution_id, video_id=cid, now=support.NOW)
    elif gate == "budget":
        with pytest.raises(StateStoreError):
            repository.cancel_waiting_model_execution(reservation.execution_id, video_id=cid, now=support.NOW)
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(provider.data_root)
    resumed = support._service(restarted, transport).continue_reserved_distillation(reservation.execution_id)
    assert resumed.status.value == ("CANCELLED" if gate == "model" else result.status.value)
    assert transport.calls == (1 if gate == "unknown" else 0)


def test_text_double_click_has_one_execution_and_invocation(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    _repo, _provider, cid, ids, _refs, transport, service = _workspace(tmp_path)
    def reserve(_):
        return service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
            evidence_ids=ids, manual_command_id="same-click").execution_id
    with ThreadPoolExecutor(max_workers=2) as pool:
        execution_ids = list(pool.map(reserve, range(2)))
    assert execution_ids[0] == execution_ids[1]
    assert service.continue_reserved_distillation(execution_ids[0]).status.value == "SUCCEEDED_NO_NEW_INTELLIGENCE"
    assert transport.calls == 1


def test_text_cloud_api_and_service_block_before_payload_credential_or_dispatch(tmp_path, monkeypatch):
    from youtube_intel.local_api import ApiError, LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService
    repository, provider, cid, ids, _refs, transport, service = _workspace(tmp_path)
    app = LocalApiApplication(repository, ProductOrchestrationService(repository, now=lambda: support.NOW),
        data_root=provider.data_root, distillation_service=service, cloud_distillation_service=service,
        cloud_intelligence_qualified=True, cloud_credential_available=True, now=lambda: support.NOW)
    assert app.handle("GET", f"/api/v1/videos/{cid}")[1]["manual_intelligence_eligible"]
    for action in ("review", "confirm"):
        with pytest.raises(ApiError) as rejected:
            app.handle("POST", f"/api/v1/videos/{cid}/cloud-intelligence/{action}", b"{}")
        assert rejected.value.code == "LOCAL_PROVIDER_CAPABILITY_UNAVAILABLE"
    transport.actual_provider, transport.actual_model = "openai", "gpt-4.1"
    cloud = support._service(repository, transport)
    payloads = []
    monkeypatch.setattr(cloud, "_compose_verified_input", lambda value: payloads.append(value))
    with pytest.raises(ValueError):
        cloud.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
            evidence_ids=ids, manual_command_id="cloud")
    assert payloads == [] and transport.calls == 0
    assert repository.latest_distillation_execution_for_video(cid) is None


def test_text_history_keeps_its_sealed_context_after_valid_summary_refresh(tmp_path):
    from youtube_intel.extractive_summary import ExtractiveSummaryService
    from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
    from youtube_intel.source_authority import sha256, text_evidence_id
    from youtube_intel.state import format_utc_datetime
    repository, provider, cid, ids, refs, transport, service = _workspace(tmp_path)
    transport.raw = json.dumps(_positive(refs))
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="history")
    result = service.continue_reserved_distillation(reservation.execution_id)
    original_context = repository.manual_local_text_context_hash(LOCAL_SOURCE_ID, cid)
    original_revision = repository.get_intelligence_revision(result.revision_id)
    pointer = repository.current_local_summary_pointer(cid)
    # A genuine new source-bound extraction changes the deterministic Summary.
    # Changing a language label on the same artifact would violate m022.
    record = repository.get_evidence(ids[0])
    artifact = repository.get_artifact(record.artifact_id)
    canonical = (provider.data_root / artifact.relative_path).read_text()
    end = canonical.rfind("\n")
    excerpt = canonical[:end]
    eid = text_evidence_id(content_id=cid, artifact_id=artifact.artifact_id,
        start_offset=0, end_offset=end, lineage_kind="EXTRACTION")
    with repository._connect() as connection:
        connection.execute("INSERT INTO evidence(evidence_id,video_id,artifact_id,locator_type,start_offset,end_offset,lineage_kind,role,language,availability,created_at,source_excerpt) VALUES(?,?,?,'TEXT_RANGE',0,?,'EXTRACTION','PRIMARY_ORIGINAL','und','AVAILABLE',?,?)",
            (eid, cid, artifact.artifact_id, end, format_utc_datetime(support.NOW), excerpt))
        connection.execute("INSERT INTO evidence_source_ranges VALUES(?,?,?,?,?,?)",
            (eid, artifact.artifact_id, excerpt, sha256(excerpt.encode()), sha256(canonical.encode()), refs[0]["source_content_hash"]))
    assert repository.resolve_verified_evidence_text(eid).excerpt == excerpt
    summaries = ExtractiveSummaryService(repository, provider.data_root)
    refreshed = summaries.create(cid, now=support.NOW)
    assert refreshed != pointer.artifact_id
    summaries.read(cid, refreshed)
    assert repository.manual_local_text_context_hash(LOCAL_SOURCE_ID, cid) != original_context
    reader = AuthoritativeIntelligenceReader(repository)
    assert reader.read_current_card(result.intelligence_id).video_id == cid
    assert reader.read_recorded_card(result.intelligence_id, result.revision_id).video_id == cid
    assert repository.get_intelligence_revision(result.revision_id) == original_revision


@pytest.mark.parametrize("language", ["en", "zh-CN"])
def test_text_output_language_remains_bound_across_restart(tmp_path, language):
    repository, provider, cid, ids, refs, transport, service = _workspace(tmp_path)
    service._output_language_for_video = lambda _: language
    positive = _positive(refs)
    if language == "zh-CN":
        positive["core_conclusion"] = "原文报告了初步结果，仍需进一步核验。"
    transport.raw = json.dumps(positive)
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="output-language")
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(provider.data_root)
    next_service = support._service(restarted, transport)
    next_service._output_language_for_video = lambda _: "zh-CN" if language == "en" else "en"
    result = next_service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "SUCCEEDED"
    assert transport.commands[0].output_language == language


def test_text_wrong_source_cross_content_and_duplicate_json_keys_are_closed(tmp_path):
    repository, provider, cid, ids, refs, transport, service = _workspace(tmp_path)
    foreign_source, _ = support._source_and_video(repository)
    repository.link_source_video(foreign_source, cid, discovered_at=support.NOW)
    with pytest.raises(ValueError):
        service.reserve_distillation_execution(source_id=foreign_source, video_id=cid,
            evidence_ids=ids, manual_command_id="foreign-source")
    other = provider.import_bytes("other.md", b"Another Content has independent source authority.\n")
    foreign_eid = repository.list_canonical_coverage_evidence_ids(other.content_id)[0]
    with pytest.raises(ValueError):
        service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
            evidence_ids=(foreign_eid,), manual_command_id="foreign-content")
    reservation = service.reserve_distillation_execution(source_id=LOCAL_SOURCE_ID, video_id=cid,
        evidence_ids=ids, manual_command_id="duplicate-json")
    transport.raw = transport.raw.replace('"wire_version":', '"wire_version":"wrong-version","wire_version":', 1)
    assert service.continue_reserved_distillation(reservation.execution_id).status.value == "REJECTED_OUTPUT"
    assert transport.calls == 1
