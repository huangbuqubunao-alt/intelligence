"""Explicit offline fixtures; proof persistence never qualifies a real model."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import replace

import pytest
from conftest import _load_module

from youtube_intel.distillation import verify_local_text_input_proof
from youtube_intel.state import MigrationError, SQLiteStateRepository, StateStoreError

text = _load_module("test_local_intelligence_text")
NOW = text.support.NOW


def _tables(repository):
    with repository._connect() as connection:
        return {name: sorted([tuple(row) for row in connection.execute('SELECT * FROM "' + name + '"')], key=repr)
            for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _files(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*") if p.is_file()}


def test_schema39_has_exact_fifteen_fields_and_immutable_proof(tmp_path):
    repository, provider, cid, ids, _refs, transport, service = text._workspace(tmp_path)
    reservation = service.reserve_distillation_execution(source_id=text.LOCAL_SOURCE_ID,
        video_id=cid, evidence_ids=ids, manual_command_id="proof")
    with repository._connect() as connection:
        proof = verify_local_text_input_proof(repository, connection, reservation.execution_id, require_current=True)
        columns = list(connection.execute("PRAGMA table_info(local_text_input_proofs)"))
        assert tuple(row[1] for row in columns) == tuple(proof.__dataclass_fields__)
        assert len(columns) == 15
        assert {row[1] for row in columns if not row[3]} == {"source_policy_revision_id"}
        foreign_keys = {(r[3], r[2], r[4]) for r in connection.execute("PRAGMA foreign_key_list(local_text_input_proofs)")}
        assert foreign_keys == {
            ("execution_id", "distillation_execution_checkpoints", "execution_id"),
            ("source_id", "source_subscriptions", "source_id"),
            ("video_id", "content_source_snapshots", "content_id"),
            ("original_summary_artifact_id", "artifacts", "artifact_id"),
            ("global_policy_revision_id", "source_policy_revisions", "revision_id"),
            ("source_policy_revision_id", "source_policy_revisions", "revision_id"),
        }
        for statement in ("UPDATE local_text_input_proofs SET input_hash=input_hash", "DELETE FROM local_text_input_proofs"):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(statement)
        input_value, context = json.loads(proof.input_json), json.loads(proof.context_json)
        assert [e["evidence_id"] for e in input_value["evidence"]] == sorted(ids)
        assert all(e["excerpt"] for e in input_value["evidence"])
        assert input_value["profile"]["think"] is True
        assert context["summary_id"] == repository.current_local_summary_pointer(cid).artifact_id
        assert context["summary_evidence"] and context["summary_reconstruction"]
    assert transport.calls == 0
    assert not any("proof" in p for p in _files(provider.data_root))


def test_proof_validation_failure_rolls_back_checkpoint_and_sidecar_atomically(tmp_path, monkeypatch):
    import youtube_intel.distillation as distillation
    repository, provider, cid, ids, _refs, transport, service = text._workspace(tmp_path)
    first = service.reserve_distillation_execution(source_id=text.LOCAL_SOURCE_ID,
        video_id=cid, evidence_ids=ids, manual_command_id="accepted-offline")
    assert service.continue_reserved_distillation(first.execution_id).status.value == "SUCCEEDED_NO_NEW_INTELLIGENCE"
    before = _tables(repository), _files(provider.data_root)
    def fail(*_args, **_kwargs):
        raise StateStoreError("injected proof validation failure")
    monkeypatch.setattr(distillation, "verify_local_text_input_proof", fail)
    with pytest.raises(StateStoreError, match="injected"):
        service.reserve_distillation_execution(source_id=text.LOCAL_SOURCE_ID,
            video_id=cid, evidence_ids=ids, manual_command_id="rejected-offline")
    assert (_tables(repository), _files(provider.data_root)) == before
    assert transport.calls == 1


def test_migration39_failure_preserves38_all_rows_and_data(tmp_path, monkeypatch):
    migrations = SQLiteStateRepository(tmp_path / "unused.sqlite")._load_migrations()
    with monkeypatch.context() as patch:
        patch.setattr(SQLiteStateRepository, "_load_migrations", lambda _: tuple(m for m in migrations if m.version <= 38))
        repository, provider, _cid, _ids, _refs, transport, _service = text._workspace(tmp_path)
    before = _tables(repository), _files(provider.data_root)
    migration39 = next(migration for migration in migrations if migration.version == 39)
    broken = replace(migration39, sql=migration39.sql + "\nSELECT injected_unknown_function();")
    monkeypatch.setattr(repository, "_load_migrations", lambda: (*tuple(m for m in migrations if m.version < 39), broken))
    with pytest.raises(MigrationError):
        repository.initialize(now=NOW)
    assert (_tables(repository), _files(provider.data_root)) == before
    with repository._connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 38
    monkeypatch.setattr(repository, "_load_migrations", lambda: migrations)
    assert repository.initialize(now=NOW).version == 42
    after = _tables(repository)
    assert {k: v for k, v in after.items() if k in before[0] and k != "schema_migrations"} == {
        k: v for k, v in before[0].items() if k != "schema_migrations"}
    assert after["local_text_input_proofs"] == []
    assert _files(provider.data_root) == before[1] and transport.calls == 0


@pytest.mark.parametrize("version", [34, 35, 36, 37, 38])
def test_legacy_backup_restore_then_normal_startup39_preserves_all_domain_rows_and_data(tmp_path, monkeypatch, version):
    from youtube_intel.backup_restore import BackupRestoreService
    migrations = SQLiteStateRepository(tmp_path / "unused.sqlite")._load_migrations()
    with monkeypatch.context() as patch:
        patch.setattr(SQLiteStateRepository, "_load_migrations", lambda _: tuple(m for m in migrations if m.version <= version))
        repository, provider, _cid, _ids, _refs, _transport, _service = text._workspace(tmp_path)
    before = _tables(repository), _files(provider.data_root)
    backup = BackupRestoreService(database=repository._database_path, data_root=provider.data_root)
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    preview = backup.stage_restore(package.read_bytes())
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    assert (_tables(repository), _files(provider.data_root)) == before
    assert repository.initialize(now=NOW).version == 42
    after = _tables(repository)
    assert {k: v for k, v in after.items() if k in before[0] and k != "schema_migrations"} == {
        k: v for k, v in before[0].items() if k != "schema_migrations"}
    assert after["local_text_input_proofs"] == []
    assert _files(provider.data_root) == before[1]


@pytest.mark.parametrize("revision_id", ["generic-local-revision",
    "generic:revision:distillation:distillation:local-text-v2:unrelated",
    "revision:distillation:distillation:local-text-v2extra:unrelated"])
def test_generic_local_text_revision_without_distillation_association_stays_readable(tmp_path, revision_id):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
    from youtube_intel.state import DependencyEdgeWrite, DependencyRelation
    trusted = _load_module("test_task019_trusted_intelligence_read")
    repository, _provider, _cid, ids, _refs, transport, _service = text._workspace(tmp_path)
    repository.create_intelligence(intelligence_id="generic-local-fixture", now=NOW)
    repository.append_intelligence_revision(intelligence_id="generic-local-fixture",
        revision=trusted._write(revision_id, ids[0]), now=NOW)
    repository.create_dependency_edge(DependencyEdgeWrite(edge_id="generic-local-edge",
        dependent_revision_id=revision_id, relation=DependencyRelation.EVIDENCE_SUPPORT,
        input_evidence_id=ids[0], input_revision_id=None), now=NOW)
    assert AuthoritativeIntelligenceReader(repository).read_current("generic-local-fixture").evidence_ids == (ids[0],)
    assert repository.get_distillation_card(revision_id) is None
    backup = BackupRestoreService(database=repository._database_path, data_root=_provider.data_root)
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    assert backup.stage_restore(package.read_bytes()).restore_id
    assert transport.calls == 0


@pytest.mark.parametrize("gate", ["cancelled", "unknown"])
def test_schema39_terminal_proof_backup_restore_and_restart_do_not_redispatch(tmp_path, monkeypatch, gate):
    from youtube_intel.backup_restore import BackupRestoreService
    repository, provider, cid, ids, _refs, transport, service = text._workspace(tmp_path)
    if gate == "cancelled":
        transport.actual_provider, transport.actual_model, transport.available = "ollama", "qwen3:8b", False
        service = text.support._service(repository, transport)
    else:
        def unknown(_):
            transport.calls += 1
            raise RuntimeError("offline unknown outcome")
        monkeypatch.setattr(transport, "generate", unknown)
    reservation = service.reserve_distillation_execution(source_id=text.LOCAL_SOURCE_ID,
        video_id=cid, evidence_ids=ids, manual_command_id="terminal")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == ("WAITING_MODEL" if gate == "cancelled" else "AMBIGUOUS")
    if gate == "cancelled":
        repository.cancel_waiting_model_execution(reservation.execution_id, video_id=cid, now=NOW)
    before = _tables(repository), _files(provider.data_root)
    backup = BackupRestoreService(database=repository._database_path, data_root=provider.data_root)
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    preview = backup.stage_restore(package.read_bytes())
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    assert (_tables(repository), _files(provider.data_root)) == before
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(provider.data_root)
    resumed = text.support._service(restarted, transport).continue_reserved_distillation(reservation.execution_id)
    assert resumed.status.value == ("CANCELLED" if gate == "cancelled" else "AMBIGUOUS")
    with restarted._connect() as connection:
        verify_local_text_input_proof(restarted, connection, reservation.execution_id)
    assert transport.calls == (0 if gate == "cancelled" else 1)


def test_original_input_retains_preferences_and_policy_after_valid_changes(tmp_path):
    from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
    from youtube_intel.source_policy import SourcePolicyApplicationService
    from youtube_intel.state import (
        DistillationStyle,
        PreferenceHorizon,
        PreferenceProvenance,
        PreferenceScope,
        PreferenceState,
        PreferenceWrite,
    )
    repository, _provider, cid, ids, refs, transport, service = text._workspace(tmp_path)
    repository.create_preference(PreferenceWrite(preference_id="original-preference", horizon=PreferenceHorizon.LONG_TERM,
        provenance=PreferenceProvenance.EXPLICIT, scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None, statement="Retain qualifications and original evidence.", starts_at=None, expires_at=None),
        activation_event_id="activate-original", now=NOW)
    transport.raw = json.dumps(text._positive(refs))
    reservation = service.reserve_distillation_execution(source_id=text.LOCAL_SOURCE_ID,
        video_id=cid, evidence_ids=ids, manual_command_id="policy-history")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "SUCCEEDED"
    with repository._connect() as connection:
        proof = verify_local_text_input_proof(repository, connection, reservation.execution_id)
    repository.retire_preference(preference_id="original-preference", state_event_id="retire-original",
        state=PreferenceState.DELETED, now=NOW)
    SourcePolicyApplicationService(repository, now=lambda: NOW).update_global(command_id="later-policy",
        initial_history_count=1, per_run_max_new_videos=3, focus_rules=("new focus",), ignore_rules=(),
        distillation_style=DistillationStyle.TECHNICAL_DETAIL_FIRST)
    reader = AuthoritativeIntelligenceReader(repository)
    assert reader.read_current_card(result.intelligence_id).preference_ids == ("original-preference",)
    with repository._connect() as connection:
        assert verify_local_text_input_proof(repository, connection, reservation.execution_id) == proof
        with pytest.raises(StateStoreError, match="current original input facts changed"):
            verify_local_text_input_proof(repository, connection, reservation.execution_id, require_current=True)


@pytest.mark.parametrize("damage", [
    "proof", "card", "ledger", "projection", "proof+card", "proof+ledger",
    "card+ledger", "proof+card+ledger", "proof+checkpoint", "proof+card+checkpoint",
    "proof+ledger+checkpoint", "proof+card+ledger+checkpoint",
])
def test_schema39_forged_archive_with_rehashed_database_is_rejected_before_live_replacement(tmp_path, damage):
    import io
    import zipfile

    from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
    repository, provider, cid, ids, refs, transport, service = text._workspace(tmp_path)
    transport.raw = json.dumps(text._positive(refs))
    reservation = service.reserve_distillation_execution(source_id=text.LOCAL_SOURCE_ID,
        video_id=cid, evidence_ids=ids, manual_command_id="forged-archive")
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "SUCCEEDED"
    from youtube_intel.saved_intelligence import (
        SavedIntelligenceService,
        SaveIntelligence,
    )
    SavedIntelligenceService(repository, now=lambda: NOW).save(SaveIntelligence(intelligence_id=result.intelligence_id))
    backup = BackupRestoreService(database=repository._database_path, data_root=provider.data_root)
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    with zipfile.ZipFile(package) as archive:
        members = {item.filename: archive.read(item) for item in archive.infolist()}
        entries = {item.filename: item for item in archive.infolist()}
    forged_database = tmp_path / "forged-only.sqlite"
    forged_database.write_bytes(members["database/state.sqlite"])
    tables = {"proof": "local_text_input_proofs", "card": "distillation_cards",
        "ledger": "distillation_resource_usage", "checkpoint": "distillation_execution_checkpoints",
        "projection": "local_text_input_proofs"}
    with sqlite3.connect(forged_database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        for missing in damage.split("+"):
            table = tables[missing]
            triggers = connection.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,)).fetchall()
            for name, _sql in triggers:
                connection.execute('DROP TRIGGER "' + name + '"')
            if missing == "projection":
                value = json.loads(connection.execute("SELECT input_json FROM local_text_input_proofs").fetchone()[0])
                value["profile"]["digest"] = "sha256:" + "0" * 64
                connection.execute("UPDATE local_text_input_proofs SET input_json=?", (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),))
            elif missing == "checkpoint" and "ledger" not in damage:
                # A retained ledger has an FK to its checkpoint. Remove only
                # the checkpoint's result association, preserving FK validity.
                connection.execute("UPDATE distillation_execution_checkpoints SET status='REJECTED_OUTPUT',intelligence_id=NULL,revision_id=NULL")
            else:
                connection.execute('DELETE FROM "' + table + '"')
            for _name, sql in triggers:
                connection.execute(sql)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
    connection.execute("PRAGMA journal_mode=DELETE").fetchone()
    connection.close()
    members["database/state.sqlite"] = forged_database.read_bytes()
    manifest = json.loads(members["manifest.json"])
    manifest["database"]["sha256"] = hashlib.sha256(members["database/state.sqlite"]).hexdigest()
    manifest["database"]["size_bytes"] = len(members["database/state.sqlite"])
    members["manifest.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(entries[name], payload)
    before = _tables(repository), _files(provider.data_root)
    with pytest.raises(BackupRestoreError, match="Local text input proof failed"):
        backup.stage_restore(stream.getvalue())
    assert (_tables(repository), _files(provider.data_root)) == before
    assert backup.restore_pending is False
    # Reopen the same closed malicious database: all ordinary read consumers
    # must reject too, including a previously saved relation after restart.
    forged = SQLiteStateRepository(forged_database)
    forged.bind_source_storage(provider.data_root)
    _assert_text_consumers_closed(forged, result.intelligence_id, result.revision_id)
    assert transport.calls == 1


def _assert_text_consumers_closed(repository, intelligence_id, revision_id):
    from youtube_intel.intelligence_read import (
        AuthoritativeIntelligenceReader,
        IntelligenceReadRejected,
    )
    from youtube_intel.saved_intelligence import (
        SavedIntelligenceService,
        SaveIntelligence,
    )
    from youtube_intel.topic import (
        TopicApplicationService,
        TopicAssociationKind,
        TopicReadRejected,
    )
    reader = AuthoritativeIntelligenceReader(repository)
    for read in (lambda: reader.read_current(intelligence_id),
        lambda: reader.read_current_card(intelligence_id),
        lambda: reader.read_recorded_card(intelligence_id, revision_id)):
        with pytest.raises(IntelligenceReadRejected):
            read()
    saved = SavedIntelligenceService(repository, now=lambda: NOW)
    with pytest.raises(IntelligenceReadRejected):
        saved.save(SaveIntelligence(intelligence_id=intelligence_id))
    assert saved.list_saved().items[0].verified is None
    topics = TopicApplicationService(repository, now=lambda: NOW)
    topic = topics.create_topic(command_id="association-loss", name="Association loss fixture")
    with pytest.raises(TopicReadRejected):
        topics.associate_intelligence(topic_id=topic.topic_id, intelligence_id=intelligence_id,
            kind=TopicAssociationKind.NEW_INFORMATION)
    assert repository.list_topic_memberships(topic.topic_id) == ()


@pytest.mark.parametrize("version", ["2", "3", "999"])
def test_explicit_text_revision_without_any_association_is_closed_including_future_versions(tmp_path, version):
    import io
    import zipfile

    from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
    from youtube_intel.state import DependencyEdgeWrite, DependencyRelation
    trusted = _load_module("test_task019_trusted_intelligence_read")
    repository, provider, _cid, ids, _refs, transport, _service = text._workspace(tmp_path)
    backup = BackupRestoreService(database=repository._database_path, data_root=provider.data_root)
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    with zipfile.ZipFile(package) as archive:
        entries = archive.infolist()
        members = {entry.filename: archive.read(entry) for entry in entries}
    forged_database = tmp_path / "future-only.sqlite"
    forged_database.write_bytes(members["database/state.sqlite"])
    live = repository
    before = _tables(live), _files(provider.data_root)
    repository = SQLiteStateRepository(forged_database)
    repository.bind_source_storage(provider.data_root)
    revision_id = f"revision:distillation:distillation:local-text-v{version}:" + ":".join(["a" * 64] * 3)
    repository.create_intelligence(intelligence_id="explicit-text-fixture", now=NOW)
    repository.append_intelligence_revision(intelligence_id="explicit-text-fixture",
        revision=trusted._write(revision_id, ids[0]), now=NOW)
    repository.create_dependency_edge(DependencyEdgeWrite(edge_id="explicit-text-edge",
        dependent_revision_id=revision_id, relation=DependencyRelation.EVIDENCE_SUPPORT,
        input_evidence_id=ids[0], input_revision_id=None), now=NOW)
    repository.save_intelligence_relation(intelligence_id="explicit-text-fixture",
        expected_revision_id=revision_id, now=NOW)
    _assert_text_consumers_closed(repository, "explicit-text-fixture", revision_id)
    with pytest.raises(BackupRestoreError, match="Local text input proof failed"):
        BackupRestoreService(database=repository._database_path, data_root=provider.data_root).create_backup()
    with repository._connect() as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert tuple(connection.execute("PRAGMA integrity_check").fetchone()) == ("ok",)
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
        connection.execute("PRAGMA journal_mode=DELETE").fetchone()
    connection.close()
    members["database/state.sqlite"] = forged_database.read_bytes()
    manifest = json.loads(members["manifest.json"])
    manifest["database"]["sha256"] = hashlib.sha256(members["database/state.sqlite"]).hexdigest()
    manifest["database"]["size_bytes"] = len(members["database/state.sqlite"])
    members["manifest.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in entries:
            archive.writestr(entry, members[entry.filename])
    with pytest.raises(BackupRestoreError, match="Local text input proof failed"):
        backup.stage_restore(stream.getvalue())
    assert (_tables(live), _files(provider.data_root)) == before
    assert backup.restore_pending is False
    assert transport.calls == 0


def test_utf8_projection_limit_rejects_without_truncation_reservation_or_invocation(tmp_path):
    from youtube_intel.state import (
        PreferenceHorizon,
        PreferenceProvenance,
        PreferenceScope,
        PreferenceWrite,
    )
    repository, provider, cid, ids, _refs, transport, service = text._workspace(tmp_path)
    # Each real persisted preference satisfies the existing 2048-character bound.
    # Together their full preference + personalization projections exceed 512 KiB
    # in UTF-8 despite being much smaller by Python character count.
    for index in range(40):
        repository.create_preference(PreferenceWrite(preference_id=f"bounded-{index}",
            horizon=PreferenceHorizon.LONG_TERM, provenance=PreferenceProvenance.EXPLICIT,
            scope=PreferenceScope.GLOBAL_CONTENT, target_id=None, statement="🙂" * 1800,
            starts_at=None, expires_at=None), activation_event_id=f"bounded-active-{index}", now=NOW)
    before = _tables(repository), _files(provider.data_root)
    with pytest.raises(ValueError, match="UTF-8 bounds"):
        service.reserve_distillation_execution(source_id=text.LOCAL_SOURCE_ID,
            video_id=cid, evidence_ids=ids, manual_command_id="bounded-input")
    assert (_tables(repository), _files(provider.data_root)) == before
    assert transport.calls == 0
