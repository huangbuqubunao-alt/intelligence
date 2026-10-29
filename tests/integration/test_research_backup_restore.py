"""Research is core authority; corrupt archives must never replace live data."""

import hashlib
import json

import pytest
from conftest import _load_module

from youtube_intel.backup_restore import (
    _REQUIRED_TABLES,
    BackupRestoreError,
    BackupRestoreService,
)
from youtube_intel.research_contract import CONTRACT, canonical, digest
from youtube_intel.research_lite import RESEARCH_AUTHORITY_TABLES, ResearchLiteService
from youtube_intel.state import SQLiteStateRepository

support = _load_module("test_research_lite")
archive_support = _load_module("test_v1x_phase1b_backup_restore")


def backup(tmp_path):
    repo = support.authority.seed(tmp_path)
    result = support.run(repo)
    support.run(repo)
    service = BackupRestoreService(database=tmp_path / "state.sqlite3", data_root=tmp_path / "data")
    created = service.create_backup()
    path, _ = service.backup_download(created.backup_id)
    return repo, result, service, path.read_bytes()


def test_valid_restore_keeps_current_research_and_all_executions(tmp_path):
    repo, first, service, raw = backup(tmp_path)
    current = ResearchLiteService(repo).read(first.packet.research_id)
    staged = service.stage_restore(raw)
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()
    restored = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert restored.initialize(now=support.authority.NOW).version == 44
    assert ResearchLiteService(restored).read(first.packet.research_id).as_dict() == current.as_dict()
    assert RESEARCH_AUTHORITY_TABLES <= _REQUIRED_TABLES
    with restored._connect() as db:
        assert db.execute("SELECT count(*) FROM research_results").fetchone()[0] == 2
        discovered = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'research_%'")}
        assert discovered <= _REQUIRED_TABLES


@pytest.mark.parametrize("attack", ["payload", "missing_table", "pointer", "regressed_pointer", "missing_result", "schema", "missing_trigger", "resealed_provenance"])
def test_corrupt_research_archive_preserves_valid_state(tmp_path, attack):
    repo, first, service, raw = backup(tmp_path)

    def mutate(db):
        triggers = db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='research_results'").fetchall()
        for row in triggers:
            db.execute(f'DROP TRIGGER "{row[0]}"')
        if attack == "payload":
            db.execute("UPDATE research_results SET payload_json='{}'")
        elif attack == "missing_table":
            db.execute("DROP TABLE research_results")
        elif attack == "pointer":
            db.execute("UPDATE research_items SET current_result_identity=?", ("f" * 64,))
        elif attack == "regressed_pointer":
            db.execute("UPDATE research_items SET current_result_identity=?", (first.result_identity,))
        elif attack == "missing_result":
            db.execute("DELETE FROM research_results WHERE result_identity=?", (first.result_identity,))
        elif attack == "resealed_provenance":
            for row in db.execute("SELECT result_identity,research_id,execution_id,payload_json FROM research_results").fetchall():
                payload = json.loads(row[3])
                payload["evidence"][0]["excerpt"] = "Fabricated transcript quote"
                payload["evidence"][0]["excerpt_hash"] = hashlib.sha256(b"Fabricated transcript quote").hexdigest()
                payload_hash = digest(payload)
                identity = digest({"contract": CONTRACT, "research_id": row[1], "execution_id": row[2], "payload_hash": payload_hash})
                db.execute("UPDATE research_results SET result_identity=?,payload_json=?,payload_hash=? WHERE result_identity=?", (identity, canonical(payload), payload_hash, row[0]))
                db.execute("UPDATE research_items SET current_result_identity=? WHERE current_result_identity=?", (identity, row[0]))
        elif attack == "schema":
            db.execute("PRAGMA user_version=30")
        if attack not in {"missing_trigger", "missing_table"}:
            for row in triggers:
                db.execute(row[1])
        # missing_trigger is already represented by dropping immutability.

    corrupt = archive_support.alter_archive(tmp_path, raw, mutate)
    before = hashlib.sha256((tmp_path / "state.sqlite3").read_bytes()).hexdigest()
    current = ResearchLiteService(repo).read(first.packet.research_id).as_dict()
    with pytest.raises(BackupRestoreError):
        service.stage_restore(corrupt)
    assert hashlib.sha256((tmp_path / "state.sqlite3").read_bytes()).hexdigest() == before
    assert ResearchLiteService(repo).read(first.packet.research_id).as_dict() == current
    assert not service.restore_pending


def test_three_revision_history_restores_exact_packets_and_order(tmp_path):
    repo = support.authority.seed(tmp_path)
    results = [support.run(repo) for _ in range(3)]
    identity = results[0].packet.research_id
    research = ResearchLiteService(repo)
    history = research.history(identity)
    service = BackupRestoreService(database=tmp_path / "state.sqlite3", data_root=tmp_path / "data")
    created = service.create_backup()
    path, _ = service.backup_download(created.backup_id)
    staged = service.stage_restore(path.read_bytes())
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()
    restored = ResearchLiteService(SQLiteStateRepository(tmp_path / "state.sqlite3"))
    assert restored.history(identity) == history
    assert restored.read(identity).as_dict() == results[-1].as_dict()
    for result in results:
        actual = restored.read_revision(identity, result.result_identity)
        assert actual.as_dict() == result.as_dict()
        for ref in actual.packet.evidence:
            assert repo.resolve_verified_evidence_text(ref.evidence_id).excerpt == ref.excerpt


def test_corrupt_only_old_revision_archive_is_rejected_preserving_valid_current(tmp_path):
    repo, first, service, raw = backup(tmp_path)
    current = ResearchLiteService(repo).read(first.packet.research_id)
    def mutate(db):
        trigger = db.execute("SELECT sql FROM sqlite_master WHERE name='research_results_immutable_update'").fetchone()[0]
        db.execute("DROP TRIGGER research_results_immutable_update")
        db.execute("UPDATE research_results SET payload_json='{}' WHERE result_identity=?", (first.result_identity,))
        db.execute(trigger)
    corrupt = archive_support.alter_archive(tmp_path, raw, mutate)
    before = hashlib.sha256((tmp_path / "state.sqlite3").read_bytes()).hexdigest()
    with pytest.raises(BackupRestoreError):
        service.stage_restore(corrupt)
    assert hashlib.sha256((tmp_path / "state.sqlite3").read_bytes()).hexdigest() == before
    assert ResearchLiteService(repo).read(first.packet.research_id).as_dict() == current.as_dict()
