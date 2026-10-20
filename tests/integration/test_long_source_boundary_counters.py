"""Persistent long-source boundary counters, independent of pure codec tests."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import replace

import pytest
from conftest import _load_module

from youtube_intel.local_distillation_profile import canonical
from youtube_intel.long_distillation_persistence import PREFIX, PROOFS, _proof_digest
from youtube_intel.state import MigrationError, SQLiteStateRepository, StateStoreError

long = _load_module("test_long_input_wait_lifecycle")
contract = _load_module("test_long_completion_storage_contract")


def test_duplicate_plus_omission_cannot_satisfy_complete_source_python_or_sql(tmp_path):
    repository, _root, sid, vid, service, _app, _transport = long.workspace(
        tmp_path, 21
    )
    ids = service.reservation_evidence_ids(vid)
    with pytest.raises(StateStoreError, match="complete Evidence"):
        service.reserve_distillation_execution(
            source_id=sid,
            video_id=vid,
            evidence_ids=(ids[0], ids[0], *ids[2:]),
            manual_command_id="duplicate-omission",
        )
    c, proof, checkpoint = contract.pending(repository, service, sid, vid)
    try:
        checkpoint.update(
            execution_id=PREFIX + "e" * 64,
            status="PENDING",
            invocation_count=0,
            budget_state="RESERVED_NOT_DISPATCHED",
        )
        contract.insert(c, "distillation_execution_checkpoints", checkpoint)
        side = json.loads(proof["semantic_snapshot_wire"])
        side["value"]["evidence"][1] = side["value"]["evidence"][0]
        proof.update(
            execution_id=checkpoint["execution_id"],
            semantic_snapshot_wire=canonical(side).decode(),
        )
        proof["semantic_snapshot_hash"] = hashlib.sha256(canonical(side)).hexdigest()
        proof["proof_hash"] = _proof_digest(proof)
        with pytest.raises(sqlite3.IntegrityError, match="complete reserved"):
            contract.insert(c, PROOFS, proof)
    finally:
        c.rollback()
        c.close()


@pytest.mark.parametrize(
    "damage", ["cue_hash", "cue_missing", "binding_hash", "canonical_file"]
)
def test_real_persisted_source_corruption_rejects_before_any_reservation(
    tmp_path, damage
):
    repository, root, sid, vid, service, _app, transport = long.workspace(tmp_path, 21)
    ids = service.reservation_evidence_ids(vid)
    if damage == "canonical_file":
        (root / "canonical.txt").write_bytes(b"corrupt complete source")
    else:
        table = (
            "evidence_text_bindings"
            if damage == "binding_hash"
            else "timed_transcript_cues"
        )
        with repository._connect() as c:
            # Simulate an externally corrupted snapshot; restore exact schema
            # so rejection depends on authority, not absent immutable triggers.
            triggers = c.execute(
                "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
                (table,),
            ).fetchall()
            for name, _ in triggers:
                c.execute('DROP TRIGGER "' + name + '"')
            if damage == "cue_hash":
                c.execute(
                    "UPDATE timed_transcript_cues SET cue_text_hash=? WHERE cue_index=0",
                    ("0" * 64,),
                )
            elif damage == "cue_missing":
                c.execute("DELETE FROM timed_transcript_cues WHERE cue_index=0")
            else:
                c.execute(
                    "UPDATE evidence_text_bindings SET excerpt_hash=?", ("0" * 64,)
                )
            for _, sql in triggers:
                c.execute(sql)
    with pytest.raises((StateStoreError, ValueError)):
        service.reserve_distillation_execution(
            source_id=sid, video_id=vid, evidence_ids=ids, manual_command_id="corrupt"
        )
    with repository._connect() as c:
        assert (
            c.execute(
                "SELECT count(*) FROM distillation_execution_checkpoints"
            ).fetchone()[0]
            == 0
        )
        assert c.execute(f"SELECT count(*) FROM {PROOFS}").fetchone()[0] == 0
    assert transport.calls == 0


def test_m041_failure_rolls_back_all_schema40_rows_and_data(tmp_path, monkeypatch):
    migrations = SQLiteStateRepository(tmp_path / "unused")._load_migrations()
    with monkeypatch.context() as patch:
        patch.setattr(
            SQLiteStateRepository,
            "_load_migrations",
            lambda _: tuple(m for m in migrations if m.version <= 40),
        )
        repository, root, _sid, _vid, _service, _app, _transport = long.workspace(
            tmp_path, 2
        )
    before = long._inventory(repository, root)
    migration = next(m for m in migrations if m.version == 41)
    broken = replace(
        migration, sql=migration.sql + "\nSELECT injected_migration41_failure();"
    )
    monkeypatch.setattr(
        repository,
        "_load_migrations",
        lambda: (*tuple(m for m in migrations if m.version < 41), broken),
    )
    with pytest.raises(MigrationError):
        repository.initialize(now=long.NOW)
    assert long._inventory(repository, root) == before
    with repository._connect() as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 40
        assert not c.execute(
            "SELECT 1 FROM sqlite_master WHERE name=?", (PROOFS,)
        ).fetchone()
