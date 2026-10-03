"""Research is core authority; corrupt archives must never replace live data."""

import hashlib

import pytest
from conftest import _load_module

from youtube_intel.backup_restore import (
    _REQUIRED_TABLES,
    BackupRestoreError,
    BackupRestoreService,
)
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
    assert restored.initialize(now=support.authority.NOW).version == 31
    assert ResearchLiteService(restored).read(first.packet.research_id).as_dict() == current.as_dict()
    assert RESEARCH_AUTHORITY_TABLES <= _REQUIRED_TABLES
    with restored._connect() as db:
        assert db.execute("SELECT count(*) FROM research_results").fetchone()[0] == 2
        discovered = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'research_%'")}
        assert discovered <= _REQUIRED_TABLES


@pytest.mark.parametrize("attack", ["payload", "missing_table", "pointer", "regressed_pointer", "missing_result", "schema", "missing_trigger"])
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
