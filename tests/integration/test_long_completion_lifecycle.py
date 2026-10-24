"""ENGINEERING_ONLY long completion lifecycle; no real qualification or models."""

import json

import pytest
from conftest import _load_module

from youtube_intel.local_distillation_profile import (
    ACTUAL_RUNTIME_PROFILE_ID as CURRENT_RUNTIME_PROFILE_ID,
)
from youtube_intel.long_distillation_persistence import PROOFS
from youtube_intel.long_distillation_profile import (
    ACTUAL_RUNTIME_PROFILE_ID as LONG_CURRENT,
)
from youtube_intel.long_distillation_profile import PROFILE_ID as LONG_OLD

wait = _load_module("test_long_input_wait_lifecycle")


def test_historical_wait_proof_and_current_runtime_proof_have_independent_builders(tmp_path):
    repository, _root, sid, vid, service, _app, transport = wait.workspace(tmp_path, 21)
    old = service.reserve_distillation_execution(
        source_id=sid, video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="historical",
    )
    with repository._connect() as connection:
        before = tuple(connection.execute(f"SELECT * FROM {PROOFS} WHERE execution_id=?", (old.execution_id,)).fetchone())
    # Fixture-only configured route selection; not eligibility or runtime proof.
    service._local_profile_id = CURRENT_RUNTIME_PROFILE_ID
    transport.local_profile_id = CURRENT_RUNTIME_PROFILE_ID
    current = service.reserve_distillation_execution(
        source_id=sid, video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="current",
    )
    with repository._connect() as connection:
        profiles = {row["execution_id"]: json.loads(row["profile_wire"])["profile_id"] for row in connection.execute(f"SELECT * FROM {PROOFS}")}
        assert tuple(connection.execute(f"SELECT * FROM {PROOFS} WHERE execution_id=?", (old.execution_id,)).fetchone()) == before
    assert profiles == {old.execution_id: LONG_OLD, current.execution_id: LONG_CURRENT}
    assert repository.get_distillation_execution(old.execution_id).status == "WAITING_MODEL"
    assert repository.get_distillation_execution(current.execution_id).status == "WAITING_MODEL"
    assert transport.calls == 0


def ready_fixture(tmp_path, *, full=False):
    """Explicit ENGINEERING_ONLY qualification and held application lease."""
    from youtube_intel.local_model_capacity import ApplicationHeavyLease

    repo, root, sid, vid, service, _app, transport = (complete_source_workspace(tmp_path) if full else wait.workspace(tmp_path, 21))
    service._local_profile_id = CURRENT_RUNTIME_PROFILE_ID
    transport.local_profile_id = CURRENT_RUNTIME_PROFILE_ID
    lease = ApplicationHeavyLease(repository=repo, data_root=root)
    assert lease.acquire()
    transport.long_profile_qualified = lambda profile_id, language, now: profile_id == LONG_CURRENT and language in {"en", "zh-CN"}
    transport.armed_long_for_claim = lambda execution_id, prepared: lease.valid()
    return repo, root, sid, vid, service, transport, lease


def test_dedicated_new_manual_pending_claim_creates_no_fake_zero_usage(tmp_path):
    from youtube_intel.long_distillation_execution import (
        claim_long,
        rebuild_long,
        reserve_pending,
    )

    repo, _root, sid, vid, service, transport, lease = ready_fixture(tmp_path)
    try:
        eid = reserve_pending(service, source_id=sid, video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="one-shot")
        assert repo.get_distillation_execution(eid).status == "PENDING"
        with repo._connect() as connection:
            prepared = rebuild_long(repo, connection, eid).prepared
            assert not connection.execute("SELECT 1 FROM distillation_resource_usage WHERE execution_id=?", (eid,)).fetchone()
        claim = claim_long(service, eid, prepared)
        assert claim.execution_id == eid
        record = repo.get_distillation_execution(eid)
        assert record.invocation_count == 1 and record.budget_state == "DISPATCH_CLAIMED"
        assert transport.calls == 0
        with repo._connect() as connection:
            assert not connection.execute("SELECT 1 FROM distillation_resource_usage WHERE execution_id=?", (eid,)).fetchone()
    finally:
        lease.release()


@pytest.mark.parametrize("change", ["qualification", "lease", "budget", "request"])
def test_long_claim_rechecks_preconditions_without_an_invocation_or_zero_usage(tmp_path, change):
    from dataclasses import replace

    from youtube_intel.long_distillation_execution import (
        claim_long,
        rebuild_long,
        reserve_pending,
    )
    from youtube_intel.state import StateStoreError

    repo, root, sid, vid, service, transport, lease = ready_fixture(tmp_path)
    try:
        eid = reserve_pending(service, source_id=sid, video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="changed")
        with repo._connect() as connection:
            prepared = rebuild_long(repo, connection, eid).prepared
        before = wait._inventory(repo, root)
        if change == "qualification":
            transport.long_profile_qualified = lambda *args: False
        elif change == "lease":
            lease.release()
        elif change == "budget":
            service._budget = wait.support._FakeBudget(False)
        else:
            prepared = replace(prepared, request_wire=prepared.request_wire + b" ")
        with pytest.raises(StateStoreError):
            claim_long(service, eid, prepared)
        assert wait._inventory(repo, root) == before
        assert repo.get_distillation_execution(eid).invocation_count == 0
        assert transport.calls == 0
    finally:
        lease.release()


def test_long_claim_cannot_promote_an_old_wait_or_cancelled_attempt(tmp_path):
    from youtube_intel.long_distillation_execution import claim_long, rebuild_long
    from youtube_intel.state import StateStoreError

    repo, root, sid, vid, service, _transport, lease = ready_fixture(tmp_path)
    try:
        old = service.reserve_distillation_execution(source_id=sid, video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="old-wait")
        with repo._connect() as connection:
            prepared = rebuild_long(repo, connection, old.execution_id).prepared
        before = wait._inventory(repo, root)
        with pytest.raises(StateStoreError):
            claim_long(service, old.execution_id, prepared)
        assert wait._inventory(repo, root) == before
        repo.cancel_waiting_model_execution(old.execution_id, video_id=vid, now=wait.NOW)
        before = wait._inventory(repo, root)
        with pytest.raises(StateStoreError):
            claim_long(service, old.execution_id, prepared)
        assert wait._inventory(repo, root) == before
        assert repo.get_distillation_execution(old.execution_id).status == "CANCELLED"
    finally:
        lease.release()


def test_long_claim_cas_is_single_invocation_even_with_two_fixture_ready_contenders(tmp_path):
    import threading

    from youtube_intel.long_distillation_execution import (
        claim_long,
        rebuild_long,
        reserve_pending,
    )
    from youtube_intel.state import StateStoreError

    repo, _root, sid, vid, service, transport, lease = ready_fixture(tmp_path)
    try:
        eid = reserve_pending(service, source_id=sid, video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="race")
        with repo._connect() as connection:
            prepared = rebuild_long(repo, connection, eid).prepared
        # ENGINEERING_ONLY readiness seam isolates the database CAS race. Actual
        # native session thread/lease checks are separate mandatory negatives.
        transport.armed_long_for_claim = lambda *args: True
        barrier = threading.Barrier(2)
        claimed, rejected = [], []
        def contender():
            barrier.wait(timeout=5)
            try:
                claimed.append(claim_long(service, eid, prepared))
            except StateStoreError as error:
                rejected.append(str(error))
        threads = [threading.Thread(target=contender) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        assert not any(thread.is_alive() for thread in threads)
        assert len(claimed) == len(rejected) == 1
        assert repo.get_distillation_execution(eid).invocation_count == 1
        with pytest.raises(StateStoreError):
            claim_long(service, eid, prepared)
        assert transport.calls == 0
    finally:
        lease.release()


@pytest.mark.parametrize("kind", ["INTELLIGENCE", "NO_NEW_INTELLIGENCE", "REJECTED"])
def test_dedicated_completion_persists_three_truthful_atomic_outcomes(tmp_path, kind):
    from youtube_intel.long_distillation_execution import (
        claim_long,
        complete_long,
        rebuild_long,
        reserve_pending,
    )
    from youtube_intel.long_distillation_persistence import RECEIPTS, verify_execution

    storage = _load_module("test_long_completion_storage_contract")
    repo, _root, sid, vid, service, _transport, lease = ready_fixture(tmp_path)
    try:
        eid = reserve_pending(service, source_id=sid, video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="complete-" + kind)
        with repo._connect() as c:
            rebuilt = rebuild_long(repo, c, eid)
        claim = claim_long(service, eid, rebuilt.prepared)
        fixture = storage.receipt(rebuilt.proof, kind)
        raw = {"model": service._selected_model, "done": True, "done_reason": "stop",
            "prompt_eval_count": 10, "eval_count": 20,
            "message": {"content": fixture["public_wire"]}}
        complete_long(service, claim, raw, duration_ms=12)
        with repo._connect() as c:
            verify_execution(repo, c, eid)
            stored = dict(c.execute(f"SELECT * FROM {RECEIPTS} WHERE execution_id=?", (eid,)).fetchone())
            assert stored["result_kind"] == kind
            assert stored["public_wire"] == fixture["public_wire"]
            assert stored["decoded_wire"] == fixture["decoded_wire"]
            assert c.execute("PRAGMA foreign_key_check").fetchall() == []
            assert c.execute("SELECT count(*) FROM distillation_resource_usage WHERE execution_id=?", (eid,)).fetchone()[0] == (kind != "NO_NEW_INTELLIGENCE")
        status = {"INTELLIGENCE": "SUCCEEDED", "NO_NEW_INTELLIGENCE": "SUCCEEDED_NO_NEW_INTELLIGENCE", "REJECTED": "REJECTED_OUTPUT"}[kind]
        assert repo.get_distillation_execution(eid).status == status
        usage = repo.get_distillation_resource_usage(eid)
        assert (usage.input_tokens, usage.output_tokens, usage.duration_ms) == (10, 20, 12)
        assert usage.invocation_count == 1
    finally:
        lease.release()


def finish_fixture(tmp_path, kind="INTELLIGENCE", *, full=False):
    from youtube_intel.long_distillation_execution import (
        claim_long,
        complete_long,
        rebuild_long,
        reserve_pending,
    )

    storage = _load_module("test_long_completion_storage_contract")
    repo, root, sid, vid, service, transport, lease = ready_fixture(tmp_path, full=full)
    try:
        eid = reserve_pending(service, source_id=sid, video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="closure-" + kind)
        with repo._connect() as c:
            rebuilt = rebuild_long(repo, c, eid)
        claim = claim_long(service, eid, rebuilt.prepared)
        fixture = storage.receipt(rebuilt.proof, kind)
        complete_long(service, claim, {"model": service._selected_model, "done": True, "done_reason": "stop",
            "prompt_eval_count": 10, "eval_count": 20, "message": {"content": fixture["public_wire"]}}, duration_ms=12)
    finally:
        lease.release()
    return repo, root, sid, vid, service, transport, eid


@pytest.mark.parametrize("kind", ["INTELLIGENCE", "NO_NEW_INTELLIGENCE", "REJECTED"])
def test_three_completed_branches_restart_and_exact_all_sql_data_backup_restore(tmp_path, kind):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
    from youtube_intel.saved_intelligence import (
        SavedIntelligenceService,
        SaveIntelligence,
    )
    from youtube_intel.state import SQLiteStateRepository
    from youtube_intel.topic import TopicApplicationService, TopicAssociationKind

    repo, root, _sid, _vid, _service, transport, eid = finish_fixture(tmp_path, kind, full=True)
    with repo._connect() as connection:
        proof = connection.execute(f"SELECT semantic_snapshot_wire FROM {PROOFS} WHERE execution_id=?", (eid,)).fetchone()
        packet = json.loads(json.loads(proof[0])["codec"]["canonical_wire"])
        assert len(packet["evidence"]) == 114
        assert sum(len(run["cues"]) for row in packet["evidence"] for run in row["runs"]) == 2406
    if kind == "INTELLIGENCE":
        intelligence_id = "intelligence:distillation:" + eid
        revision_id = "revision:distillation:" + eid
        reader = AuthoritativeIntelligenceReader(repo)
        assert reader.read_current(intelligence_id).revision_id == revision_id
        assert reader.read_current_card(intelligence_id).core_conclusion == "Fixture claim."
        assert reader.read_recorded_card(intelligence_id, revision_id).verified.evidence_ids
        saved = SavedIntelligenceService(repo, now=lambda: wait.NOW)
        saved.save(SaveIntelligence(intelligence_id=intelligence_id))
        assert saved.list_saved().items[0].verified is not None
        topics = TopicApplicationService(repo, now=lambda: wait.NOW)
        topic = topics.create_topic(command_id="long-topic", name="Engineering fixture")
        topics.associate_intelligence(topic_id=topic.topic_id, intelligence_id=intelligence_id,
            kind=TopicAssociationKind.NEW_INFORMATION)
        assert repo.list_topic_memberships(topic.topic_id)
    before = wait._inventory(repo, root)
    backup = BackupRestoreService(database=repo._database_path, data_root=root)
    assert backup.readiness()["ready"]
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    preview = backup.stage_restore(package.read_bytes())
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    assert wait._inventory(repo, root) == before
    restarted = SQLiteStateRepository(repo._database_path)
    restarted.bind_source_storage(root)
    assert restarted.get_distillation_execution(eid).invocation_count == 1
    assert restarted.get_distillation_resource_usage(eid).output_tokens == 20
    if kind == "INTELLIGENCE":
        assert AuthoritativeIntelligenceReader(restarted).read_current_card(intelligence_id).core_conclusion == "Fixture claim."
    assert transport.calls == 0  # Synthetic engineering only; never model quality.


@pytest.mark.parametrize("kind,point", [
    *(("INTELLIGENCE", n) for n in range(1, 11)),
    *(("NO_NEW_INTELLIGENCE", n) for n in range(1, 4)),
    *(("REJECTED", n) for n in range(1, 4)),
    *((kind, point) for kind in ("INTELLIGENCE", "NO_NEW_INTELLIGENCE", "REJECTED") for point in ("commit-before", "commit-after")),
])
def test_fault_at_every_completion_write_and_commit_never_exposes_partial_authority(tmp_path, monkeypatch, kind, point):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.long_distillation_execution import (
        claim_long,
        complete_long,
        rebuild_long,
        reserve_pending,
    )
    from youtube_intel.long_distillation_persistence import verify_execution

    storage = _load_module("test_long_completion_storage_contract")
    repo, root, sid, vid, service, _transport, lease = ready_fixture(tmp_path)
    original_connect = repo._connect
    try:
        eid = reserve_pending(service, source_id=sid, video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="fault")
        with repo._connect() as c:
            rebuilt = rebuild_long(repo, c, eid)
        claim = claim_long(service, eid, rebuilt.prepared)
        fixture = storage.receipt(rebuilt.proof, kind)
        raw = {"model": service._selected_model, "done": True, "done_reason": "stop",
            "prompt_eval_count": 10, "eval_count": 20, "message": {"content": fixture["public_wire"]}}
        before = wait._inventory(repo, root)
        class FailingConnection:
            def __init__(self, connection):
                self.connection, self.count = connection, 0
            def __getattr__(self, name):
                return getattr(self.connection, name)
            def execute(self, sql, *args):
                if sql.lstrip().split()[0].upper() in {"INSERT", "UPDATE"}:
                    self.count += 1
                    if self.count == point:
                        raise RuntimeError("injected completion write")
                return self.connection.execute(sql, *args)
            def commit(self):
                if point == "commit-before":
                    raise RuntimeError("injected before commit")
                self.connection.commit()
                if point == "commit-after":
                    raise RuntimeError("injected after durable commit")
        with monkeypatch.context() as patch:
            patch.setattr(repo, "_connect", lambda: FailingConnection(original_connect()))
            with pytest.raises(RuntimeError, match="injected"):
                complete_long(service, claim, raw, duration_ms=12)
        if point == "commit-after":
            assert repo.get_distillation_execution(eid).status != "PENDING"
        else:
            assert wait._inventory(repo, root) == before
            assert repo.get_distillation_execution(eid).status == "PENDING"
            assert repo.get_distillation_execution(eid).invocation_count == 1
            assert not BackupRestoreService(database=repo._database_path, data_root=root).readiness()["ready"]
        with repo._connect() as c:
            verify_execution(repo, c, eid)
            assert not c.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        lease.release()


@pytest.mark.parametrize("change", ["missing-model", "wrong-model", "length", "done-false", "token-cap", "input-cap", "malformed", "foreign-evidence", "missing-tokens", "zero-input", "zero-output"])
def test_authentic_negative_response_preserves_observations_without_fake_card(tmp_path, change):
    from youtube_intel.long_distillation_execution import (
        claim_long,
        complete_long,
        rebuild_long,
        reserve_pending,
    )
    from youtube_intel.long_distillation_persistence import RECEIPTS
    from youtube_intel.state import StateStoreError

    storage = _load_module("test_long_completion_storage_contract")
    repo, root, sid, vid, service, _transport, lease = ready_fixture(tmp_path)
    try:
        eid = reserve_pending(service, source_id=sid, video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="response")
        with repo._connect() as c:
            rebuilt = rebuild_long(repo, c, eid)
        claim = claim_long(service, eid, rebuilt.prepared)
        fixture = storage.receipt(rebuilt.proof)
        raw = {"model": service._selected_model, "done": True, "done_reason": "stop",
            "prompt_eval_count": 10, "eval_count": 20, "message": {"content": fixture["public_wire"]}}
        if change == "missing-model":
            raw.pop("model")
        elif change == "wrong-model":
            raw["model"] = "foreign-model"
        elif change == "length":
            raw["done_reason"] = "length"
        elif change == "done-false":
            raw["done"] = False
        elif change == "token-cap":
            raw["eval_count"] = 6144
        elif change == "input-cap":
            raw["prompt_eval_count"] = 26623
        elif change == "zero-input":
            raw["prompt_eval_count"] = 0
        elif change == "zero-output":
            raw["eval_count"] = 0
        elif change == "malformed":
            raw["message"] = {"content": "invalid authentic raw final"}
        elif change == "foreign-evidence":
            value = json.loads(raw["message"]["content"])
            value["evidence"][0]["evidence_id"] = "E9999"
            raw["message"] = {"content": json.dumps(value)}
        else:
            raw.pop("eval_count")
        before = wait._inventory(repo, root)
        if change == "missing-model":
            with pytest.raises(StateStoreError, match="unknown"):
                complete_long(service, claim, raw, duration_ms=12)
            assert wait._inventory(repo, root) == before
            assert repo.get_distillation_execution(eid).status == "PENDING"
        else:
            complete_long(service, claim, raw, duration_ms=12)
            assert repo.get_distillation_execution(eid).status == "REJECTED_OUTPUT"
            assert repo.list_distillation_cards() == ()
            with repo._connect() as c:
                receipt = c.execute(f"SELECT * FROM {RECEIPTS} WHERE execution_id=?", (eid,)).fetchone()
                assert receipt["public_wire"] == raw["message"]["content"]
                metadata = json.loads(receipt["completion_json"])
                assert metadata["actual_model"] == raw["model"]
                assert metadata["done"] == raw["done"]
                assert metadata["done_reason"] == raw["done_reason"]
                if change == "missing-tokens":
                    assert metadata["input_tokens"] is None and metadata["output_tokens"] is None
                else:
                    assert metadata["output_tokens"] == raw["eval_count"]
    finally:
        lease.release()


def complete_source_workspace(tmp_path):
    """Portable synthetic 114-span/2406-cue source via real repository writers."""
    import hashlib

    repo = wait.SQLiteStateRepository(tmp_path / "state.sqlite3")
    repo.initialize(now=wait.NOW)
    sid, vid = wait.support._source_and_video(repo, "abcdefghijk")
    root = tmp_path / "data"
    root.mkdir()
    repo.bind_source_storage(root)
    cues = tuple(wait.TimedTranscriptCueWrite(i * 1000, i * 1000 + 900, f"Source fact {i}.") for i in range(2406))
    wire = "\n".join(c.text for c in cues).encode()
    (root / "canonical.txt").write_bytes(wire)
    repo.upsert_artifact(wait.ArtifactWrite(artifact_id="canonical-long", artifact_key="canonical-long", video_id=vid,
        job_id=None, kind=wait.ArtifactKind.TRANSCRIPT_CANONICAL, storage_root=wait.StorageRoot.DATA,
        relative_path="canonical.txt", content_hash=hashlib.sha256(wire).hexdigest(), provider="fixture", model=None,
        producer_version="fixture-v1", retention_class=wait.RetentionClass.LONG_LIVED, expires_at=None), now=wait.NOW)
    timed = wait.TimedTranscriptWrite.from_cues(video_id=vid, canonical_artifact_id="canonical-long", cues=cues)
    repo.create_timed_transcript(timed, now=wait.NOW)
    for index in range(114):
        start, stop = 2406 * index // 114, 2406 * (index + 1) // 114
        evidence = wait.EvidenceWrite(
            evidence_id=wait.build_evidence_id(video_id=vid, artifact_id="canonical-long", start_ms=cues[start].start_ms,
                end_ms=cues[stop - 1].end_ms, lineage_kind=wait.EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
                role=wait.EvidenceRole.PRIMARY_ORIGINAL), video_id=vid, artifact_id="canonical-long",
            start_ms=cues[start].start_ms, end_ms=cues[stop - 1].end_ms,
            lineage_kind=wait.EvidenceLineageKind.ORIGINAL_TRANSCRIPT, role=wait.EvidenceRole.PRIMARY_ORIGINAL,
            language="en", availability=wait.EvidenceAvailability.AVAILABLE)
        repo.create_evidence_with_text_binding(evidence, wait.EvidenceTextBindingWrite.from_timed_transcript(
            evidence=evidence, timed_transcript_id=timed.timed_transcript_id, start_cue_index=start, end_cue_index=stop,
            excerpt="\n".join(c.text for c in cues[start:stop])), now=wait.NOW)
    wait.ExtractiveSummaryService(repo, root).create(vid, now=wait.NOW)
    transport = wait.support._FakeTransport("ENGINEERING_ONLY", available=False,
        actual_provider="ollama", actual_model=wait.resolve_profile(wait.FIXED_RUNTIME_PROFILE_ID).model)
    transport.local_profile_id = CURRENT_RUNTIME_PROFILE_ID
    service = wait.PersonalizedDistillationService(repo, wait.support.SourcePolicyApplicationService(repo, now=lambda: wait.NOW),
        transport, wait.support._FakeBudget(True), now=lambda: wait.NOW)
    return repo, root, sid, vid, service, None, transport


def damage_database(path, sql, parameters=(), *, standalone=False):
    """Simulate an attacker modifying an isolated DB while retaining exact DDL."""
    import sqlite3

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        triggers = connection.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'").fetchall()
        for name, _statement in triggers:
            connection.execute('DROP TRIGGER "' + name + '"')
        for statement in sql:
            connection.execute(statement, parameters)
        for _name, statement in triggers:
            connection.execute(statement)
    if standalone:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
        connection.execute("PRAGMA journal_mode=DELETE").fetchone()
    connection.close()


DAMAGES = {
    "receipt": ["DELETE FROM long_distillation_completion_receipts"],
    "card": ["DELETE FROM distillation_cards"],
    "receipt+card+usage": ["DELETE FROM long_distillation_completion_receipts", "DELETE FROM distillation_cards", "DELETE FROM distillation_resource_usage"],
    "all-execution-authority": ["DELETE FROM long_distillation_completion_receipts", "DELETE FROM long_distillation_input_proofs", "DELETE FROM distillation_resource_usage", "DELETE FROM distillation_execution_checkpoints"],
    "dependency": ["DELETE FROM dependency_edges WHERE dependent_revision_id LIKE 'revision:distillation:distillation:long-timed%'"],
    "stance": ["UPDATE intelligence_revision_evidence SET stance='contradicting' WHERE revision_id LIKE 'revision:distillation:distillation:long-timed%'"],
    "preference": ["UPDATE distillation_cards SET preference_ids_json='[\"foreign\"]'"],
    "conclusion": ["UPDATE distillation_cards SET core_conclusion='altered'"],
    "selected-model": ["UPDATE distillation_resource_usage SET selected_model='foreign'"],
    "pointer": ["UPDATE intelligences SET current_revision_id=NULL"],
}


@pytest.mark.parametrize("damage", tuple(DAMAGES))
def test_coordinated_damage_cannot_downgrade_current_history_save_topic_usage_or_backup(tmp_path, damage):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.intelligence_read import (
        AuthoritativeIntelligenceReader,
        IntelligenceReadRejected,
    )
    from youtube_intel.long_distillation_persistence import verify_database
    from youtube_intel.saved_intelligence import (
        SavedIntelligenceService,
        SaveIntelligence,
    )
    from youtube_intel.state import StateStoreError
    from youtube_intel.topic import (
        TopicApplicationService,
        TopicAssociationKind,
        TopicReadRejected,
    )

    repo, root, _sid, _vid, _service, _transport, eid = finish_fixture(tmp_path)
    iid, rid = "intelligence:distillation:" + eid, "revision:distillation:" + eid
    saved = SavedIntelligenceService(repo, now=lambda: wait.NOW)
    saved.save(SaveIntelligence(intelligence_id=iid))
    topics = TopicApplicationService(repo, now=lambda: wait.NOW)
    topic = topics.create_topic(command_id="tamper-topic", name="Engineering fixture")
    damage_database(repo._database_path, DAMAGES[damage])
    with repo._connect() as c, pytest.raises((StateStoreError, ValueError, KeyError)):
        verify_database(repo, c)
    reader = AuthoritativeIntelligenceReader(repo)
    for read in (lambda: reader.read_current(iid), lambda: reader.read_current_card(iid), lambda: reader.read_recorded_card(iid, rid)):
        with pytest.raises(IntelligenceReadRejected):
            read()
    with pytest.raises(IntelligenceReadRejected):
        saved.save(SaveIntelligence(intelligence_id=iid))
    assert saved.list_saved().items[0].verified is None
    with pytest.raises(TopicReadRejected):
        topics.associate_intelligence(topic_id=topic.topic_id, intelligence_id=iid, kind=TopicAssociationKind.NEW_INFORMATION)
    if damage != "all-execution-authority":
        with pytest.raises(StateStoreError):
            repo.get_distillation_resource_usage(eid)
    assert not BackupRestoreService(database=repo._database_path, data_root=root).readiness()["ready"]


@pytest.mark.parametrize("damage", ["receipt+card+usage", "all-execution-authority", "preference", "stance"])
def test_completed_rehashed_zip_rejects_coordinated_damage_without_changing_live_pair(tmp_path, damage):
    import hashlib
    import io
    import zipfile

    from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService

    repo, root, _sid, _vid, _service, _transport, _eid = finish_fixture(tmp_path)
    backup = BackupRestoreService(database=repo._database_path, data_root=root)
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    with zipfile.ZipFile(package) as archive:
        members = {item.filename: archive.read(item) for item in archive.infolist()}
        entries = {item.filename: item for item in archive.infolist()}
    path = tmp_path / "attacker.sqlite"
    path.write_bytes(members["database/state.sqlite"])
    damage_database(path, DAMAGES[damage], standalone=True)
    members["database/state.sqlite"] = path.read_bytes()
    manifest = json.loads(members["manifest.json"])
    manifest["database"]["sha256"] = hashlib.sha256(members["database/state.sqlite"]).hexdigest()
    manifest["database"]["size_bytes"] = len(members["database/state.sqlite"])
    members["manifest.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(entries[name], payload)
    before = wait._inventory(repo, root)
    with pytest.raises(BackupRestoreError):
        backup.stage_restore(out.getvalue())
    assert wait._inventory(repo, root) == before
    assert not backup.restore_pending


@pytest.mark.parametrize("kind,retained", [("INTELLIGENCE", "usage"), ("NO_NEW_INTELLIGENCE", "zero"), ("REJECTED", "usage"), ("INTELLIGENCE", "case-card")])
def test_orphan_reserved_authority_is_rejected_even_without_any_execution_checkpoint(tmp_path, kind, retained):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.long_distillation_persistence import verify_database
    from youtube_intel.state import StateStoreError

    repo, root, _sid, _vid, _service, _transport, _eid = finish_fixture(tmp_path, kind)
    commands = ["DELETE FROM long_distillation_completion_receipts", "DELETE FROM long_distillation_input_proofs", "DELETE FROM distillation_execution_checkpoints"]
    if retained != "usage":
        commands.append("DELETE FROM distillation_resource_usage")
    if retained == "case-card":
        commands += ["DELETE FROM intelligence_revisions", "DELETE FROM intelligence_revision_evidence", "DELETE FROM intelligence_state_history", "DELETE FROM dependency_edges", "DELETE FROM intelligences", "UPDATE distillation_cards SET revision_id=upper(revision_id)"]
    damage_database(repo._database_path, commands)
    with repo._connect() as c, pytest.raises((StateStoreError, ValueError, KeyError)):
        verify_database(repo, c)
    assert not BackupRestoreService(database=repo._database_path, data_root=root).readiness()["ready"]


def test_completed_no_new_does_not_remain_unknown_application_heavy_work(tmp_path):
    from youtube_intel.local_model_capacity import unresolved_local_work

    repo, _root, _sid, _vid, _service, _transport, _eid = finish_fixture(tmp_path, "NO_NEW_INTELLIGENCE")
    assert not unresolved_local_work(repo)


def test_later_generic_revision_still_revalidates_original_long_completion(tmp_path):
    from youtube_intel.intelligence_read import (
        AuthoritativeIntelligenceReader,
        IntelligenceReadRejected,
    )
    from youtube_intel.state import (
        DependencyEdgeWrite,
        DependencyRelation,
        IntelligenceClaimKind,
        IntelligenceInterpretationKind,
        IntelligenceRevisionWrite,
        IntelligenceState,
    )

    repo, _root, _sid, _vid, _service, _transport, eid = finish_fixture(tmp_path)
    iid, original = "intelligence:distillation:" + eid, "revision:distillation:" + eid
    reader = AuthoritativeIntelligenceReader(repo)
    evidence_ids = reader.read_current(iid).evidence_ids
    revision = repo.append_intelligence_revision(intelligence_id=iid, revision=IntelligenceRevisionWrite(
        revision_id="revision:engineering:later", interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
        claim_kind=IntelligenceClaimKind.FACT, content_hash="1" * 64, state=IntelligenceState.CONFIRMED,
        reason="Engineering later interpretation", evidence_ids=evidence_ids), now=wait.NOW)
    for index, evidence_id in enumerate(evidence_ids):
        repo.create_dependency_edge(DependencyEdgeWrite(edge_id="later-edge-" + str(index),
            dependent_revision_id=revision.revision_id, relation=DependencyRelation.EVIDENCE_SUPPORT,
            input_evidence_id=evidence_id, input_revision_id=None), now=wait.NOW)
    assert reader.read_current(iid).revision_id == revision.revision_id
    assert reader.read_recorded_card(iid, original).core_conclusion == "Fixture claim."
    damage_database(repo._database_path, ["DELETE FROM distillation_cards"])
    with pytest.raises(IntelligenceReadRejected):
        reader.read_current(iid)
