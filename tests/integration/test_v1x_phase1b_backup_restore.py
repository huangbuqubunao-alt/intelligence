"""Archives must preserve and reverify the complete Deep Analysis graph."""

import hashlib
import io
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.backup_restore import (
    _REQUIRED_TABLES,
    DEEP_ANALYSIS_AUTHORITY_TABLES,
    BackupRestoreError,
    BackupRestoreService,
)
from youtube_intel.deep_analysis_persistence import DeepAnalysisPersistenceStore
from youtube_intel.note_v2 import build_note_v2
from youtube_intel.state import SQLiteStateRepository

authority = _load_module("test_v1x_phase1b_authority")


def backup(tmp_path: Path):
    repository = authority.seed(tmp_path)
    view = authority.service(repository).run(content_id=authority.VIDEO)
    other = authority.seed_other(tmp_path, repository)
    foreign = authority.service(repository).run(content_id=other)
    service = BackupRestoreService(database=tmp_path / "state.sqlite3", data_root=tmp_path / "data")
    result = service.create_backup()
    archive, _ = service.backup_download(result.backup_id)
    return repository, service, archive.read_bytes(), view, foreign


def alter_archive(tmp_path: Path, raw: bytes, change) -> bytes:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = {info.filename: archive.read(info) for info in archive.infolist()}
    staged = tmp_path / "attacked-snapshot.sqlite3"
    staged.write_bytes(members["database/state.sqlite"])
    with sqlite3.connect(staged) as connection:
        connection.row_factory = sqlite3.Row
        change(connection)
    members["database/state.sqlite"] = staged.read_bytes()
    manifest = json.loads(members["manifest.json"])
    manifest["database"]["sha256"] = hashlib.sha256(members["database/state.sqlite"]).hexdigest()
    manifest["database"]["size_bytes"] = len(members["database/state.sqlite"])
    members["manifest.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return output.getvalue()


def test_required_table_coverage_tracks_da_authority_and_future_memberships(tmp_path: Path) -> None:
    repository = authority.seed(tmp_path)
    assert {"deep_analysis_persisted_results", "deep_analysis_evidence", "evidence", "evidence_text_bindings",
            "timed_transcripts", "timed_transcript_cues", "artifacts", "videos"} == DEEP_ANALYSIS_AUTHORITY_TABLES
    assert DEEP_ANALYSIS_AUTHORITY_TABLES <= _REQUIRED_TABLES
    with repository._connect() as connection:
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        da_tables = {t for t in tables if t.startswith("deep_analysis_")}
        dependents = {t for t in tables if any(fk[2] == "deep_analysis_persisted_results"
                     for fk in connection.execute(f'PRAGMA foreign_key_list("{t}")'))}
        assert da_tables | dependents <= _REQUIRED_TABLES


def test_valid_archive_restores_same_verified_claims_and_note(tmp_path: Path) -> None:
    _, service, archive, view, _ = backup(tmp_path)
    preview = service.stage_restore(archive)
    service.confirm_restore(preview.restore_id)
    service.recover_and_apply_pending_restore()
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert repository.initialize(now=authority.NOW).version == 33
    restored = authority.service(repository).read(content_id=authority.VIDEO)
    assert restored.as_dict() == view.as_dict()
    result = DeepAnalysisPersistenceStore(repository).read_persisted_deep_analysis_result(result_identity=view.result_identity)
    assert result is not None
    assert build_note_v2(result).evidence_references
    assert not service.restore_pending
    assert service.readiness()["last_restore"]["state"] == "APPLIED"


@pytest.mark.parametrize("attack", [
    "missing_result", "missing_membership", "missing_membership_table", "missing_evidence", "missing_membership_constraints",
    "dangling_membership", "unlinked_claim", "unreferenced_membership", "cross_content",
    "tampered_json", "unsupported_schema", "unsupported_policy", "corrupted_provenance", "corrupted_attempt",
])
def test_corrupt_archive_cannot_overwrite_valid_state(tmp_path: Path, attack: str) -> None:
    repository, service, archive, view, foreign = backup(tmp_path)
    def change(connection):
        if attack == "missing_result":
            connection.execute("DELETE FROM deep_analysis_persisted_results WHERE result_identity=?", (view.result_identity,))
        elif attack == "missing_membership":
            connection.execute("DELETE FROM deep_analysis_evidence WHERE result_identity=?", (view.result_identity,))
        elif attack == "missing_membership_table":
            connection.execute("DROP TABLE deep_analysis_evidence")
        elif attack == "corrupted_attempt":
            attempts = json.loads(connection.execute("SELECT fallback_attempts_json FROM deep_analysis_persisted_results WHERE result_identity=?", (view.result_identity,)).fetchone()[0])
            attempts[0]["provider_id"] = "forged-provider"
            connection.execute("UPDATE deep_analysis_persisted_results SET fallback_attempts_json=? WHERE result_identity=?", (json.dumps(attempts), view.result_identity))
        elif attack == "missing_membership_constraints":
            connection.execute("ALTER TABLE deep_analysis_evidence RENAME TO saved_membership")
            connection.execute("CREATE TABLE deep_analysis_evidence (result_identity TEXT, evidence_id TEXT, created_at TEXT)")
            connection.execute("INSERT INTO deep_analysis_evidence SELECT * FROM saved_membership")
            connection.execute("DROP TABLE saved_membership")
        elif attack == "missing_evidence":
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='evidence'").fetchall():
                connection.execute(f'DROP TRIGGER "{row[0]}"')
            connection.execute("DELETE FROM evidence WHERE evidence_id=?", (view.roles[0].evidence_ids[0],))
        elif attack == "dangling_membership":
            connection.execute("INSERT INTO deep_analysis_evidence VALUES (?, ?, ?)", (view.result_identity, "f"*64, authority.NOW.isoformat()))
        elif attack in {"unlinked_claim", "unreferenced_membership", "cross_content"}:
            original = connection.execute("SELECT evidence_id FROM evidence WHERE video_id=? AND lineage_kind='ORIGINAL_TRANSCRIPT' LIMIT 1", (authority.VIDEO,)).fetchone()[0]
            ref = foreign.roles[0].evidence_ids[0] if attack == "cross_content" else original
            if attack != "unlinked_claim":
                connection.execute("INSERT INTO deep_analysis_evidence VALUES (?, ?, ?)", (view.result_identity, ref, authority.NOW.isoformat()))
            if attack != "unreferenced_membership":
                authority.reseal(connection, view.result_identity, lambda p: p["claims"][0].update(evidence_refs=[ref]))
        elif attack == "tampered_json":
            authority.reseal(connection, view.result_identity, lambda p: p["claims"][0].update(text="This source has a fabricated conclusion."))
        else:
            column, value = {"unsupported_schema": ("persistence_version", "unknown"),
                             "unsupported_policy": ("validation_policy_identity", "a"*64),
                             "corrupted_provenance": ("provider_id", "forged")}[attack]
            connection.execute(f"UPDATE deep_analysis_persisted_results SET {column}=? WHERE result_identity=?", (value, view.result_identity))
    corrupted = alter_archive(tmp_path, archive, change)
    database = tmp_path / "state.sqlite3"
    before_db = hashlib.sha256(database.read_bytes()).hexdigest()
    before_data = {p.relative_to(tmp_path / "data"): p.read_bytes() for p in (tmp_path / "data").rglob("*") if p.is_file()}
    with pytest.raises(BackupRestoreError):
        service.stage_restore(corrupted)
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before_db
    assert {p.relative_to(tmp_path / "data"): p.read_bytes() for p in (tmp_path / "data").rglob("*") if p.is_file()} == before_data
    assert authority.service(repository).read(content_id=authority.VIDEO).as_dict() == view.as_dict()
    assert not service.restore_pending
